#!/usr/bin/env python3
# Allow direct execution
import os
import sys
import threading
import unittest

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import abc
import contextlib
import enum
import functools
import http.server
import json
import random
import socket
import struct
import time
from socketserver import (
    BaseRequestHandler,
    StreamRequestHandler,
    ThreadingTCPServer,
)

from test.helper import http_server_port, verify_address_availability
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import ProxyError, TransportError
from yt_dlp.socks import (
    SOCKS4_REPLY_VERSION,
    SOCKS4_VERSION,
    SOCKS5_USER_AUTH_SUCCESS,
    SOCKS5_USER_AUTH_VERSION,
    SOCKS5_VERSION,
    Socks5AddressType,
    Socks5Auth,
)

SOCKS5_USER_AUTH_FAILURE = 0x1


class Socks4CD(enum.IntEnum):
    REQUEST_GRANTED = 90
    REQUEST_REJECTED_OR_FAILED = 91
    REQUEST_REJECTED_CANNOT_CONNECT_TO_IDENTD = 92
    REQUEST_REJECTED_DIFFERENT_USERID = 93


class Socks5Reply(enum.IntEnum):
    SUCCEEDED = 0x0
    GENERAL_FAILURE = 0x1
    CONNECTION_NOT_ALLOWED = 0x2
    NETWORK_UNREACHABLE = 0x3
    HOST_UNREACHABLE = 0x4
    CONNECTION_REFUSED = 0x5
    TTL_EXPIRED = 0x6
    COMMAND_NOT_SUPPORTED = 0x7
    ADDRESS_TYPE_NOT_SUPPORTED = 0x8


class SocksTestRequestHandler(BaseRequestHandler):

    def __init__(self, *args, socks_info=None, **kwargs):
        self.socks_info = socks_info
        super().__init__(*args, **kwargs)


class SocksProxyHandler(BaseRequestHandler):
    def __init__(self, request_handler_class, socks_server_kwargs, *args, **kwargs):
        self.socks_kwargs = socks_server_kwargs or {}
        self.request_handler_class = request_handler_class
        super().__init__(*args, **kwargs)


class Socks5ProxyHandler(StreamRequestHandler, SocksProxyHandler):

    # SOCKS5 protocol https://tools.ietf.org/html/rfc1928
    # SOCKS5 username/password authentication https://tools.ietf.org/html/rfc1929

    def handle(self):
        sleep = self.socks_kwargs.get('sleep')
        if sleep:
            time.sleep(sleep)
        version, nmethods = self.connection.recv(2)
        assert version == SOCKS5_VERSION
        methods = list(self.connection.recv(nmethods))

        auth = self.socks_kwargs.get('auth')

        if auth is not None and Socks5Auth.AUTH_USER_PASS not in methods:
            self.connection.sendall(struct.pack('!BB', SOCKS5_VERSION, Socks5Auth.AUTH_NO_ACCEPTABLE))
            self.server.close_request(self.request)
            return

        elif Socks5Auth.AUTH_USER_PASS in methods:
            self.connection.sendall(struct.pack('!BB', SOCKS5_VERSION, Socks5Auth.AUTH_USER_PASS))

            _, user_len = struct.unpack('!BB', self.connection.recv(2))
            username = self.connection.recv(user_len).decode()
            pass_len = ord(self.connection.recv(1))
            password = self.connection.recv(pass_len).decode()

            if username == auth[0] and password == auth[1]:
                self.connection.sendall(struct.pack('!BB', SOCKS5_USER_AUTH_VERSION, SOCKS5_USER_AUTH_SUCCESS))
            else:
                self.connection.sendall(struct.pack('!BB', SOCKS5_USER_AUTH_VERSION, SOCKS5_USER_AUTH_FAILURE))
                self.server.close_request(self.request)
                return

        elif Socks5Auth.AUTH_NONE in methods:
            self.connection.sendall(struct.pack('!BB', SOCKS5_VERSION, Socks5Auth.AUTH_NONE))
        else:
            self.connection.sendall(struct.pack('!BB', SOCKS5_VERSION, Socks5Auth.AUTH_NO_ACCEPTABLE))
            self.server.close_request(self.request)
            return

        version, command, _, address_type = struct.unpack('!BBBB', self.connection.recv(4))
        socks_info = {
            'version': version,
            'auth_methods': methods,
            'command': command,
            'client_address': self.client_address,
            'ipv4_address': None,
            'domain_address': None,
            'ipv6_address': None,
        }
        if address_type == Socks5AddressType.ATYP_IPV4:
            socks_info['ipv4_address'] = socket.inet_ntoa(self.connection.recv(4))
        elif address_type == Socks5AddressType.ATYP_DOMAINNAME:
            socks_info['domain_address'] = self.connection.recv(ord(self.connection.recv(1))).decode()
        elif address_type == Socks5AddressType.ATYP_IPV6:
            socks_info['ipv6_address'] = socket.inet_ntop(socket.AF_INET6, self.connection.recv(16))
        else:
            self.server.close_request(self.request)

        socks_info['port'] = struct.unpack('!H', self.connection.recv(2))[0]

        # dummy response, the returned IP is just a placeholder
        self.connection.sendall(struct.pack(
            '!BBBBIH', SOCKS5_VERSION, self.socks_kwargs.get('reply', Socks5Reply.SUCCEEDED), 0x0, 0x1, 0x7f000001, 40000))

        self.request_handler_class(self.request, self.client_address, self.server, socks_info=socks_info)


class Socks4ProxyHandler(StreamRequestHandler, SocksProxyHandler):

    # SOCKS4 protocol http://www.openssh.com/txt/socks4.protocol
    # SOCKS4A protocol http://www.openssh.com/txt/socks4a.protocol

    def _read_until_null(self):
        return b''.join(iter(functools.partial(self.connection.recv, 1), b'\x00'))

    def handle(self):
        sleep = self.socks_kwargs.get('sleep')
        if sleep:
            time.sleep(sleep)
        socks_info = {
            'version': SOCKS4_VERSION,
            'command': None,
            'client_address': self.client_address,
            'ipv4_address': None,
            'port': None,
            'domain_address': None,
        }
        version, command, dest_port, dest_ip = struct.unpack('!BBHI', self.connection.recv(8))
        socks_info['port'] = dest_port
        socks_info['command'] = command
        if version != SOCKS4_VERSION:
            self.server.close_request(self.request)
            return
        use_remote_dns = False
        if 0x0 < dest_ip <= 0xFF:
            use_remote_dns = True
        else:
            socks_info['ipv4_address'] = socket.inet_ntoa(struct.pack('!I', dest_ip))

        user_id = self._read_until_null().decode()
        if user_id != (self.socks_kwargs.get('user_id') or ''):
            self.connection.sendall(struct.pack(
                '!BBHI', SOCKS4_REPLY_VERSION, Socks4CD.REQUEST_REJECTED_DIFFERENT_USERID, 0x00, 0x00000000))
            self.server.close_request(self.request)
            return

        if use_remote_dns:
            socks_info['domain_address'] = self._read_until_null().decode()

        # dummy response, the returned IP is just a placeholder
        self.connection.sendall(
            struct.pack(
                '!BBHI', SOCKS4_REPLY_VERSION,
                self.socks_kwargs.get('cd_reply', Socks4CD.REQUEST_GRANTED), 40000, 0x7f000001))

        self.request_handler_class(self.request, self.client_address, self.server, socks_info=socks_info)


class IPv6ThreadingTCPServer(ThreadingTCPServer):
    address_family = socket.AF_INET6


class SocksHTTPTestRequestHandler(http.server.BaseHTTPRequestHandler, SocksTestRequestHandler):
    def do_GET(self):
        if self.path == '/socks_info':
            payload = json.dumps(self.socks_info.copy())
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload.encode())


class SocksWebSocketTestRequestHandler(SocksTestRequestHandler):
    def handle(self):
        import websockets.sync.server
        protocol = websockets.ServerProtocol()
        connection = websockets.sync.server.ServerConnection(socket=self.request, protocol=protocol, close_timeout=0)
        connection.handshake()
        for message in connection:
            if message == 'socks_info':
                connection.send(json.dumps(self.socks_info))
        connection.close()


@contextlib.contextmanager
def socks_server(socks_server_class, request_handler, bind_ip=None, **socks_server_kwargs):
    server = server_thread = None
    try:
        bind_address = bind_ip or '127.0.0.1'
        server_type = ThreadingTCPServer if '.' in bind_address else IPv6ThreadingTCPServer
        server = server_type(
            (bind_address, 0), functools.partial(socks_server_class, request_handler, socks_server_kwargs))
        server_port = http_server_port(server)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        if '.' not in bind_address:
            yield f'[{bind_address}]:{server_port}'
        else:
            yield f'{bind_address}:{server_port}'
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(2.0)


class SocksProxyTestContext(abc.ABC):
    REQUEST_HANDLER_CLASS = None

    def socks_server(self, server_class, *args, **kwargs):
        return socks_server(server_class, self.REQUEST_HANDLER_CLASS, *args, **kwargs)

    @abc.abstractmethod
    def socks_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs) -> dict:
        """return a dict of socks_info"""


class HTTPSocksTestProxyContext(SocksProxyTestContext):
    REQUEST_HANDLER_CLASS = SocksHTTPTestRequestHandler

    def socks_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs):
        request = Request(f'http://{target_domain or "127.0.0.1"}:{target_port or "40000"}/socks_info', **req_kwargs)
        handler.validate(request)
        return json.loads(handler.send(request).read().decode())


class WebSocketSocksTestProxyContext(SocksProxyTestContext):
    REQUEST_HANDLER_CLASS = SocksWebSocketTestRequestHandler

    def socks_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs):
        request = Request(f'ws://{target_domain or "127.0.0.1"}:{target_port or "40000"}', **req_kwargs)
        handler.validate(request)
        ws = handler.send(request)
        ws.send('socks_info')
        socks_info = ws.recv()
        ws.close()
        return json.loads(socks_info)


CTX_MAP = {
    'http': HTTPSocksTestProxyContext,
    'ws': WebSocketSocksTestProxyContext,
}


@pytest.fixture(scope='module')
def ctx(request):
    return CTX_MAP[request.param]()


@pytest.mark.parametrize(
    'handler,ctx', [
        ('Urllib', 'http'),
        ('Requests', 'http'),
        ('Websockets', 'ws'),
        ('CurlCFFI', 'http'),
    ], indirect=True)
@pytest.mark.handler_flaky('CurlCFFI', reason='segfaults')
class TestSocks4Proxy:
    def test_socks4_no_auth(self, handler, ctx):
        with handler() as rh:
            with ctx.socks_server(Socks4ProxyHandler) as server_address:
                response = ctx.socks_info_request(
                    rh, proxies={'all': f'socks4://{server_address}'})
                assert response['version'] == 4

    def test_socks4_auth(self, handler, ctx):
        with handler() as rh:
            with ctx.socks_server(Socks4ProxyHandler, user_id='user') as server_address:
                with pytest.raises(ProxyError):
                    ctx.socks_info_request(rh, proxies={'all': f'socks4://{server_address}'})
                response = ctx.socks_info_request(
                    rh, proxies={'all': f'socks4://user:@{server_address}'})
                assert response['version'] == 4

    def test_socks4a_ipv4_target(self, handler, ctx):
        with ctx.socks_server(Socks4ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks4a://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['version'] == 4
                assert (response['ipv4_address'] == '127.0.0.1') != (response['domain_address'] == '127.0.0.1')

    def test_socks4a_domain_target(self, handler, ctx):
        with ctx.socks_server(Socks4ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks4a://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='localhost')
                assert response['version'] == 4
                assert response['ipv4_address'] is None
                assert response['domain_address'] == 'localhost'

    def test_ipv4_client_source_address(self, handler, ctx):
        with ctx.socks_server(Socks4ProxyHandler) as server_address:
            source_address = f'127.0.0.{random.randint(5, 255)}'
            verify_address_availability(source_address)
            with handler(proxies={'all': f'socks4://{server_address}'},
                         source_address=source_address) as rh:
                response = ctx.socks_info_request(rh)
                assert response['client_address'][0] == source_address
                assert response['version'] == 4

    @pytest.mark.parametrize('reply_code', [
        Socks4CD.REQUEST_REJECTED_OR_FAILED,
        Socks4CD.REQUEST_REJECTED_CANNOT_CONNECT_TO_IDENTD,
        Socks4CD.REQUEST_REJECTED_DIFFERENT_USERID,
    ])
    def test_socks4_errors(self, handler, ctx, reply_code):
        with ctx.socks_server(Socks4ProxyHandler, cd_reply=reply_code) as server_address:
            with handler(proxies={'all': f'socks4://{server_address}'}) as rh:
                with pytest.raises(ProxyError):
                    ctx.socks_info_request(rh)

    def test_ipv6_socks4_proxy(self, handler, ctx):
        with ctx.socks_server(Socks4ProxyHandler, bind_ip='::1') as server_address:
            with handler(proxies={'all': f'socks4://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['client_address'][0] == '::1'
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['version'] == 4

    def test_timeout(self, handler, ctx):
        with ctx.socks_server(Socks4ProxyHandler, sleep=2) as server_address:
            with handler(proxies={'all': f'socks4://{server_address}'}, timeout=0.5) as rh:
                with pytest.raises(TransportError):
                    ctx.socks_info_request(rh)


@pytest.mark.parametrize(
    'handler,ctx', [
        ('Urllib', 'http'),
        ('Requests', 'http'),
        ('Websockets', 'ws'),
        ('CurlCFFI', 'http'),
    ], indirect=True)
@pytest.mark.handler_flaky('CurlCFFI', reason='segfaults')
class TestSocks5Proxy:

    def test_socks5_no_auth(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh)
                assert response['auth_methods'] == [0x0]
                assert response['version'] == 5

    def test_socks5_user_pass(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler, auth=('test', 'testpass')) as server_address:
            with handler() as rh:
                with pytest.raises(ProxyError):
                    ctx.socks_info_request(rh, proxies={'all': f'socks5://{server_address}'})

                response = ctx.socks_info_request(
                    rh, proxies={'all': f'socks5://test:testpass@{server_address}'})

                assert response['auth_methods'] == [Socks5Auth.AUTH_NONE, Socks5Auth.AUTH_USER_PASS]
                assert response['version'] == 5

    def test_socks5_ipv4_target(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['version'] == 5

    def test_socks5_domain_target(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='localhost')
                assert (response['ipv4_address'] == '127.0.0.1') != (response['ipv6_address'] == '::1')
                assert response['version'] == 5

    def test_socks5h_domain_target(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks5h://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='localhost')
                assert response['ipv4_address'] is None
                assert response['domain_address'] == 'localhost'
                assert response['version'] == 5

    def test_socks5h_ip_target(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks5h://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['domain_address'] is None
                assert response['version'] == 5

    def test_socks5_ipv6_destination(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='[::1]')
                assert response['ipv6_address'] == '::1'
                assert response['version'] == 5

    def test_ipv6_socks5_proxy(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler, bind_ip='::1') as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = ctx.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['client_address'][0] == '::1'
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['version'] == 5

    # XXX: is there any feasible way of testing IPv6 source addresses?
    # Same would go for non-proxy source_address test...
    def test_ipv4_client_source_address(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler) as server_address:
            source_address = f'127.0.0.{random.randint(5, 255)}'
            verify_address_availability(source_address)
            with handler(proxies={'all': f'socks5://{server_address}'}, source_address=source_address) as rh:
                response = ctx.socks_info_request(rh)
                assert response['client_address'][0] == source_address
                assert response['version'] == 5

    @pytest.mark.parametrize('reply_code', [
        Socks5Reply.GENERAL_FAILURE,
        Socks5Reply.CONNECTION_NOT_ALLOWED,
        Socks5Reply.NETWORK_UNREACHABLE,
        Socks5Reply.HOST_UNREACHABLE,
        Socks5Reply.CONNECTION_REFUSED,
        Socks5Reply.TTL_EXPIRED,
        Socks5Reply.COMMAND_NOT_SUPPORTED,
        Socks5Reply.ADDRESS_TYPE_NOT_SUPPORTED,
    ])
    def test_socks5_errors(self, handler, ctx, reply_code):
        with ctx.socks_server(Socks5ProxyHandler, reply=reply_code) as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                with pytest.raises(ProxyError):
                    ctx.socks_info_request(rh)

    def test_timeout(self, handler, ctx):
        with ctx.socks_server(Socks5ProxyHandler, sleep=2) as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}, timeout=1) as rh:
                with pytest.raises(TransportError):
                    ctx.socks_info_request(rh)


if __name__ == '__main__':
    unittest.main()

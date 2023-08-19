#!/usr/bin/env python3
import abc
import contextlib
import functools
import json
# Allow direct execution
import os
import sys
import threading
import unittest

import pytest

from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import ProxyError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import random
import subprocess
import urllib.request
from socketserver import StreamRequestHandler, ThreadingTCPServer, BaseRequestHandler
import struct
import socket
import http.server
from test.helper import FakeYDL, get_params, is_download_test, http_server_port
from test.test_networking import handler
from yt_dlp.socks import SOCKS4_VERSION, Socks4Command
SOCKS_NEGOTIATION_NONE = 0x0
SOCKS_NEGOTIATION_USER_PASS = 0x2

SOCKS_VERSION_SOCKS5 = 0x5
SOCKS_VERSION_SOCKS4 = 0x4


class SocksTestRequestHandler(BaseRequestHandler):

    def __init__(self, *args, socks_info=None, **kwargs):
        self.socks_info = socks_info
        super().__init__(*args, **kwargs)


class Socks5ProxyServer(StreamRequestHandler):

    # SOCKS5 protocol https://tools.ietf.org/html/rfc1928
    # SOCKS5 username/password authentication https://tools.ietf.org/html/rfc1929

    def __init__(self, request_handler_class, socks_server_kwargs, *args, **kwargs):
        if socks_server_kwargs is None:
            socks_server_kwargs = {}
        self.auth = socks_server_kwargs.get('auth')
        self.request_handler_class = request_handler_class
        super().__init__(*args, **kwargs)

    def handle(self):
        version, nmethods = struct.unpack("!BB", self.connection.recv(2))
        assert version == SOCKS_VERSION_SOCKS5  # SOCKS5
        methods = []
        for i in range(nmethods):
            methods.append(ord(self.connection.recv(1)))

        # if we have a username and password, but the client doesn't support it, close the connection
        if self.auth is not None and SOCKS_NEGOTIATION_USER_PASS not in methods:
            self.connection.sendall(struct.pack("!BB", SOCKS_VERSION_SOCKS5, 0xFF))
            self.server.close_request(self.request)
            return

        elif SOCKS_NEGOTIATION_USER_PASS in methods:
            self.connection.sendall(struct.pack("!BB", SOCKS_VERSION_SOCKS5, SOCKS_NEGOTIATION_USER_PASS))

            # Now verify creds
            version, user_len = struct.unpack("!BB", self.connection.recv(2))
            username = self.connection.recv(user_len).decode()
            pass_len = ord(self.connection.recv(1))
            password = self.connection.recv(pass_len).decode()

            if username == self.auth[0] and password == self.auth[1]:
                self.connection.sendall(struct.pack("!BB", 0x1, 0x0))  # success
            else:
                self.connection.sendall(struct.pack("!BB", 0x1, 0x1))  # failure
                self.server.close_request(self.request)
                return

        elif SOCKS_NEGOTIATION_NONE in methods:
            self.connection.sendall(struct.pack("!BB", SOCKS_VERSION_SOCKS5, SOCKS_NEGOTIATION_NONE))
        else:
            self.connection.sendall(struct.pack("!BB", SOCKS_VERSION_SOCKS5, 0xFF))
            self.server.close_request(self.request)
            return

        version, command, _, address_type = struct.unpack("!BBBB", self.connection.recv(4))
        socks_info = {
            'version': version,
            'auth_methods': methods,
            'command': command,
            'client_address': self.client_address,
            'ipv4_address': None,
            'domain_address': None,
            'ipv6_address': None,
        }
        if address_type == 0x1:
            socks_info['ipv4_address'] = socket.inet_ntoa(self.connection.recv(4))
        elif address_type == 0x3:
            socks_info['domain_address'] = self.connection.recv(ord(self.connection.recv(1))).decode()
        elif address_type == 0x4:
            socks_info['ipv6_address'] = socket.inet_ntop(socket.AF_INET6, self.connection.recv(16))
        else:
            self.server.close_request(self.request)
        socks_info['port'] = struct.unpack('!H', self.connection.recv(2))[0]

        # TODO: test error mapping here
        self.connection.sendall(
            struct.pack("!BBBBBBBB", SOCKS_VERSION_SOCKS5, 0x0, 0x0, 0x1, 0x7f, 0x0, 0x0, 0x1))

        self.connection.sendall(struct.pack("!H", 40000))

        self.request_handler_class(
            self.request,
            self.client_address,
            self.server,
            socks_info=socks_info
            )


class Socks4ProxyServer(StreamRequestHandler):

    # SOCKS4 protocol http://www.openssh.com/txt/socks4.protocol
    # SOCKS4A protocol http://www.openssh.com/txt/socks4a.protocol

    def __init__(self, request_handler_class, socks_server_kwargs, *args, **kwargs):
        if socks_server_kwargs is None:
            socks_server_kwargs = {}
        self.userid = socks_server_kwargs.get('user_id') or ''
        self.request_handler_class = request_handler_class
        super().__init__(*args, **kwargs)

    def _read_until_null(self):
        # good enough for testing
        data = b''
        while True:
            raw = self.connection.recv(1)
            if raw == b'\x00':
                break
            data += raw
        return data

    def handle(self):

        socks_info = {
            'version': SOCKS_VERSION_SOCKS4,
            'command': None,
            'client_address': self.client_address,
            'ipv4_address': None,
            'port': None,
            'domain_address': None,
        }
        version, command, dest_port, dest_ip = struct.unpack("!BBHI", self.connection.recv(8))
        socks_info['port'] = dest_port
        socks_info['command'] = command
        if version != SOCKS4_VERSION:
            self.server.close_request(self.request)
            return
        use_remote_dns = False
        if 0x0 < dest_ip <= 0xFF:
            use_remote_dns = True
        else:
            socks_info['ipv4_address'] = socket.inet_ntoa(struct.pack("!I", dest_ip))

        user_id = self._read_until_null().decode()
        if user_id != self.userid:
            self.connection.sendall(struct.pack("!BBHI", 0, 93, 0x00, 0x00000000))
            self.server.close_request(self.request)
            return

        if use_remote_dns:
            socks_info['domain_address'] = self._read_until_null().decode()

        # TODO: test error mapping here
        self.connection.sendall(struct.pack("!BBHI", 0, 90, 40000, 0x7f000001))
        self.request_handler_class(
            self.request,
            self.client_address,
            self.server,
            socks_info=socks_info
        )


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


@contextlib.contextmanager
def socks_server(socks_server_class, request_handler, bind_ip=None, **socks_server_kwargs):
    server = server_thread = None
    try:
        bind_address = bind_ip or '127.0.0.1'
        server_type = ThreadingTCPServer if '.' in bind_address else IPv6ThreadingTCPServer
        server = server_type(
            (bind_address, 0), functools.partial(
                socks_server_class, request_handler , socks_server_kwargs))
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


class SocksTestProxyBase:
    SOCKS_SERVER_CLASS = None
    REQUEST_HANDLER_CLASS = None

    def socks_server(self, *args, **kwargs):
        return socks_server(self.SOCKS_SERVER_CLASS, self.REQUEST_HANDLER_CLASS, *args, **kwargs)

    @abc.abstractmethod
    def socks_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs) -> dict:
        """return a dict of socks_info"""


class HTTPSocksTestProxyBase(SocksTestProxyBase):
    REQUEST_HANDLER_CLASS = SocksHTTPTestRequestHandler

    def socks_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs):
        request = Request(f'http://{target_domain or "127.0.0.1"}:{target_port or "40000"}/socks_info', **req_kwargs)
        handler.validate(request)
        return json.loads(handler.send(request).read().decode())


class Socks4ProxyTests(SocksTestProxyBase):
    SOCKS_SERVER_CLASS = Socks4ProxyServer

    def test_socks4_auth(self, handler):
        with handler() as rh:
            with self.socks_server() as server_address:
                response = self.socks_info_request(
                    rh, proxies={'all': f'socks4://{server_address}'})
                assert response['version'] == 4

            with self.socks_server(user_id='user') as server_address:
                response = self.socks_info_request(
                    rh, proxies={'all': f'socks4://user:@{server_address}'})
                assert response['version'] == 4

    @pytest.mark.skip('socks4a implementation currently broken when destination is not a domain name')
    def test_socks4a_ipv4(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks4a://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['version'] == 4
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['domain_address'] is None

    def test_socks4a_domain(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks4a://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='localhost')
                assert response['version'] == 4
                assert response['ipv4_address'] is None
                assert response['domain_address'] == 'localhost'

    @pytest.mark.skip('source_address is not yet supported for socks4 proxies')
    def test_ipv4_client_source_address(self, handler):
        with self.socks_server() as server_address:
            source_address = f'127.0.0.{random.randint(5, 255)}'
            with handler(proxies={'all': f'socks4://{server_address}'},
                         source_address=source_address) as rh:
                response = self.socks_info_request(rh)
                assert response['client_address'][0] == source_address
                assert response['version'] == 4


class Socks5ProxyTests(SocksTestProxyBase):
    SOCKS_SERVER_CLASS = Socks5ProxyServer

    def test_socks5_no_auth(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = self.socks_info_request(rh)
                assert response['auth_methods'] == [0x0]
                assert response['version'] == 5

    def test_socks5_user_pass(self, handler):
        with self.socks_server(auth=('test', 'testpass')) as server_address:
            with handler() as rh:
                with pytest.raises(ProxyError):
                    self.socks_info_request(rh, proxies={'all': f'socks5://{server_address}'})

                response = self.socks_info_request(
                    rh, proxies={'all': f'socks5://test:testpass@{server_address}'})

                assert response['auth_methods'] == [0x0, 0x2]
                assert response['version'] == 5

    def test_socks5_ipv4_target(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['version'] == 5

    def test_socks5_domain_target(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='localhost')
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['version'] == 5

    def test_socks5h_domain_target(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks5h://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='localhost')
                assert response['ipv4_address'] is None
                assert response['domain_address'] == 'localhost'
                assert response['version'] == 5

    def test_socks5h_ip_target(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks5h://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['domain_address'] is None
                assert response['version'] == 5

    @pytest.mark.skip('IPv6 destination addresses are not yet supported')
    def test_socks5_ipv6_destination(self, handler):
        with self.socks_server() as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='[::1]')
                assert response['ipv6_address'] == '::1'
                assert response['port'] == 80
                assert response['version'] == 5

    @pytest.mark.skip('IPv6 socks5 proxies are not yet supported')
    def test_ipv6_socks5_proxy(self, handler):
        with self.socks_server(bind_ip='::1') as server_address:
            with handler(proxies={'all': f'socks5://{server_address}'}) as rh:
                response = self.socks_info_request(rh, target_domain='127.0.0.1')
                assert response['client_address'][0] == '::1'
                assert response['ipv4_address'] == '127.0.0.1'
                assert response['version'] == 5

    # XXX: is there any feasible way of testing IPv6 source addresses?
    # Same would go for non-proxy source_address test...
    @pytest.mark.skip('source_address is not yet supported for socks5 proxies')
    def test_ipv4_client_source_address(self, handler):
        with self.socks_server() as server_address:
            source_address = f'127.0.0.{random.randint(5, 255)}'
            with handler(proxies={'all': f'socks5://{server_address}'}, source_address=source_address) as rh:
                response = self.socks_info_request(rh)
                assert response['client_address'][0] == source_address
                assert response['version'] == 5


# This is split up like this to support testing protocols other than HTTP
@pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
class TestHTTPSocks5Proxy(HTTPSocksTestProxyBase, Socks5ProxyTests):
    pass


@pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
class TestHTTPSocks4Proxy(HTTPSocksTestProxyBase, Socks4ProxyTests):
    pass


if __name__ == '__main__':
    unittest.main()

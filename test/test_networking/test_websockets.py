#!/usr/bin/env python3
import enum
# Allow direct execution
import os
import sys
from queue import Queue

import pytest
from websockets.datastructures import Headers

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import functools
import json
import gzip
import http.client
import http.cookiejar
import http.server
import io
import pathlib
import random
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.request
import warnings
import zlib
from email.message import Message
from http.cookiejar import CookieJar

from test.helper import FakeYDL, http_server_port
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.dependencies import brotli, requests, urllib3, websockets
from yt_dlp.networking import (
    HEADRequest,
    PUTRequest,
    Request,
    RequestDirector,
    RequestHandler,
    Response,
)
from yt_dlp.networking._urllib import UrllibRH
from yt_dlp.networking.exceptions import (
    CertificateVerifyError,
    HTTPError,
    IncompleteRead,
    NoSupportingHandlers,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
    UnsupportedRequest,
)
from yt_dlp.utils._utils import _YDLLogger as FakeLogger
from yt_dlp.utils.networking import HTTPHeaderDict
from .conftest import validate_and_send
import websockets.sync
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def websocket_handler(websocket):
    for message in websocket:
        if message == 'headers':
            return websocket.send(json.dumps(dict(websocket.request.headers)))
        elif message == 'path':
            return websocket.send(websocket.request.path)
        elif message == 'source_address':
            return websocket.send(websocket.remote_address[0])
        else:
            return websocket.send(message)


def process_request(self, request):
    if request.path.startswith('/gen_'):
        status = http.HTTPStatus(int(request.path[5:]))
        if 300 <= status.value <= 300:
            return websockets.http11.Response(
                status.value, status.phrase, websockets.datastructures.Headers([('Location', '/')]), b'')
        return self.protocol.reject(status.value, status.phrase)
    return self.protocol.accept(request)


def create_websocket_server(**ws_kwargs):
    import websockets.sync.server
    wsd = websockets.sync.server.serve(websocket_handler, '127.0.0.1', 0, process_request=process_request, **ws_kwargs)
    ws_port = wsd.socket.getsockname()[1]
    ws_server_thread = threading.Thread(target=wsd.serve_forever)
    ws_server_thread.daemon = True
    ws_server_thread.start()
    return ws_server_thread, ws_port


def create_ws_websocket_server():
    return create_websocket_server()


def create_wss_websocket_server():
    certfn = os.path.join(TEST_DIR, '../testcert.pem')
    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sslctx.load_cert_chain(certfn, None)
    return create_websocket_server(ssl_context=sslctx)


@pytest.mark.skipif(not websockets, reason='websockets must be installed to test websocket request handlers')
class TestWebsSocketRequestHandlerConformance:
    @classmethod
    def setup_class(cls):
        cls.ws_thread, cls.ws_port = create_ws_websocket_server()
        cls.ws_base_url = f'ws://127.0.0.1:{cls.ws_port}'

        cls.wss_thread, cls.wss_port = create_wss_websocket_server()
        cls.wss_base_url = f'wss://127.0.0.1:{cls.wss_port}'

        cls.bad_wss_thread, cls.bad_wss_port = create_websocket_server(ssl_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER))
        cls.bad_wss_host = f'wss://127.0.0.1:{cls.bad_wss_port}'

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_basic_websockets(self, handler):
        with handler() as rh:
            ws = validate_and_send(rh, Request(self.ws_base_url))
            assert 'upgrade' in ws.headers
            assert ws.status == 101
            ws.send('foo')
            assert ws.recv() == 'foo'
            ws.close()

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_verify_cert(self, handler):
        with handler() as rh:
            with pytest.raises(CertificateVerifyError):
                validate_and_send(rh, Request(self.wss_base_url))

        with handler(verify=False) as rh:
            ws = validate_and_send(rh, Request(self.wss_base_url))
            assert ws.status == 101
            ws.close()

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_ssl_error(self, handler):
        with handler(verify=False) as rh:
            with pytest.raises(SSLError, match='sslv3 alert handshake failure') as exc_info:
                validate_and_send(rh, Request(self.bad_wss_host))
            assert not issubclass(exc_info.type, CertificateVerifyError)

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    @pytest.mark.parametrize('path,expected', [
        # Unicode characters should be encoded with uppercase percent-encoding
        ('/中文', '/%E4%B8%AD%E6%96%87'),
        # don't normalize existing percent encodings
        ('/%c7%9f', '/%c7%9f'),
    ])
    def test_percent_encode(self, handler, path, expected):
        with handler() as rh:
            ws = validate_and_send(rh, Request(f'{self.ws_base_url}{path}'))
            ws.send('path')
            assert ws.recv() == expected
            assert ws.status == 101
            ws.close()

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_remove_dot_segments(self, handler):
        with handler() as rh:
            # This isn't a comprehensive test,
            # but it should be enough to check whether the handler is removing dot segments
            ws = validate_and_send(rh, Request(f'{self.ws_base_url}/a/b/./../../test'))
            assert ws.status == 101
            ws.send('path')
            assert ws.recv() == '/test'
            ws.close()

    # We are restricted to known HTTP status codes in http.HTTPStatus
    # Redirects are not supported for websockets
    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    @pytest.mark.parametrize('status', (200, 204, 301, 302, 303, 400, 500, 511))
    def test_raise_http_error(self, handler, status):
        with handler() as rh:
            with pytest.raises(HTTPError):
                validate_and_send(rh, Request(f'{self.ws_base_url}/gen_{status}'))

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    @pytest.mark.parametrize('params,extensions', [
        ({'timeout': 0.00001}, {}),
        ({}, {'timeout': 0.00001}),
    ])
    def test_timeout(self, handler, params, extensions):
        with handler(**params) as rh:
            with pytest.raises(TransportError):
                validate_and_send(rh, Request(self.ws_base_url, extensions=extensions))

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_cookies(self, handler):
        cookiejar = YoutubeDLCookieJar()
        cookiejar.set_cookie(http.cookiejar.Cookie(
            version=0, name='test', value='ytdlp', port=None, port_specified=False,
            domain='127.0.0.1', domain_specified=True, domain_initial_dot=False, path='/',
            path_specified=True, secure=False, expires=None, discard=False, comment=None,
            comment_url=None, rest={}))

        with handler(cookiejar=cookiejar) as rh:
            ws = validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            assert json.loads(ws.recv())['cookie'] == 'test=ytdlp'
            ws.close()

        with handler() as rh:
            ws = validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            assert 'cookie' not in json.loads(ws.recv())

            ws = validate_and_send(rh, Request(self.ws_base_url, extensions={'cookiejar': cookiejar}))
            ws.send('headers')
            assert json.loads(ws.recv())['cookie'] == 'test=ytdlp'
            ws.close()

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_source_address(self, handler):
        source_address = f'127.0.0.{random.randint(5, 255)}'
        with handler(source_address=source_address) as rh:
            ws = validate_and_send(rh, Request(self.ws_base_url))
            ws.send('source_address')
            assert source_address == ws.recv()
            ws.close()

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_response_url(self, handler):
        with handler() as rh:
            url = f'{self.ws_base_url}/something'
            ws = validate_and_send(rh, Request(url))
            assert ws.url == url
            ws.close()

    @pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
    def test_request_headers(self, handler):
        with handler(headers=HTTPHeaderDict({'test1': 'test', 'test2': 'test2'})) as rh:
            # Global Headers
            ws = validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            headers = HTTPHeaderDict(json.loads(ws.recv()))
            assert headers['test1'] == 'test'
            ws.close()

            # Per request headers, merged with global
            ws = validate_and_send(rh, Request(
                self.ws_base_url, headers={'test2': 'changed', 'test3': 'test3'}))
            ws.send('headers')
            headers = HTTPHeaderDict(json.loads(ws.recv()))
            assert headers['test1'] == 'test'
            assert headers['test2'] == 'changed'
            assert headers['test3'] == 'test3'
            ws.close()

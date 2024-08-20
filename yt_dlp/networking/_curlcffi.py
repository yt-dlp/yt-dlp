from __future__ import annotations

import io
import math
import re
import urllib.parse

from ._helper import InstanceStoreMixin, select_proxy
from .common import (
    Features,
    Request,
    Response,
    register_preference,
    register_rh,
)
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    IncompleteRead,
    ProxyError,
    SSLError,
    TransportError,
)
from .impersonate import ImpersonateRequestHandler, ImpersonateTarget
from ..dependencies import curl_cffi, certifi
from ..utils import int_or_none

if curl_cffi is None:
    raise ImportError('curl_cffi is not installed')


curl_cffi_version = tuple(map(int, re.split(r'[^\d]+', curl_cffi.__version__)[:3]))

if curl_cffi_version != (0, 5, 10) and not ((0, 7, 0) <= curl_cffi_version < (0, 8, 0)):
    curl_cffi._yt_dlp__version = f'{curl_cffi.__version__} (unsupported)'
    raise ImportError('Only curl_cffi versions 0.5.10, 0.7.X are supported')

import curl_cffi.requests
from curl_cffi.const import CurlECode, CurlOpt


class CurlCFFIResponseReader(io.IOBase):
    def __init__(self, response: curl_cffi.requests.Response):
        self._response = response
        self._iterator = response.iter_content()
        self._buffer = b''
        self.bytes_read = 0

    def readable(self):
        return True

    def read(self, size=None):
        exception_raised = True
        try:
            while self._iterator and (size is None or len(self._buffer) < size):
                chunk = next(self._iterator, None)
                if chunk is None:
                    self._iterator = None
                    break
                self._buffer += chunk
                self.bytes_read += len(chunk)

            if size is None:
                size = len(self._buffer)
            data = self._buffer[:size]
            self._buffer = self._buffer[size:]

            # "free" the curl instance if the response is fully read.
            # curl_cffi doesn't do this automatically and only allows one open response per thread
            if not self._iterator and not self._buffer:
                self.close()
            exception_raised = False
            return data
        finally:
            if exception_raised:
                self.close()

    def close(self):
        if not self.closed:
            self._response.close()
            self._buffer = b''
        super().close()


class CurlCFFIResponseAdapter(Response):
    fp: CurlCFFIResponseReader

    def __init__(self, response: curl_cffi.requests.Response):
        super().__init__(
            fp=CurlCFFIResponseReader(response),
            headers=response.headers,
            url=response.url,
            status=response.status_code)

    def read(self, amt=None):
        try:
            return self.fp.read(amt)
        except curl_cffi.requests.errors.RequestsError as e:
            if e.code == CurlECode.PARTIAL_FILE:
                content_length = int_or_none(e.response.headers.get('Content-Length'))
                raise IncompleteRead(
                    partial=self.fp.bytes_read,
                    expected=content_length - self.fp.bytes_read if content_length is not None else None,
                    cause=e) from e
            raise TransportError(cause=e) from e


@register_rh
class CurlCFFIRH(ImpersonateRequestHandler, InstanceStoreMixin):
    RH_NAME = 'curl_cffi'
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_IMPERSONATE_TARGET_MAP = {
        **({
            ImpersonateTarget('chrome', '124', 'macos', '14'): curl_cffi.requests.BrowserType.chrome124,
            ImpersonateTarget('chrome', '123', 'macos', '14'): curl_cffi.requests.BrowserType.chrome123,
            ImpersonateTarget('chrome', '120', 'macos', '14'): curl_cffi.requests.BrowserType.chrome120,
            ImpersonateTarget('chrome', '119', 'macos', '14'): curl_cffi.requests.BrowserType.chrome119,
            ImpersonateTarget('chrome', '116', 'windows', '10'): curl_cffi.requests.BrowserType.chrome116,
        } if curl_cffi_version >= (0, 7, 0) else {}),
        ImpersonateTarget('chrome', '110', 'windows', '10'): curl_cffi.requests.BrowserType.chrome110,
        ImpersonateTarget('chrome', '107', 'windows', '10'): curl_cffi.requests.BrowserType.chrome107,
        ImpersonateTarget('chrome', '104', 'windows', '10'): curl_cffi.requests.BrowserType.chrome104,
        ImpersonateTarget('chrome', '101', 'windows', '10'): curl_cffi.requests.BrowserType.chrome101,
        ImpersonateTarget('chrome', '100', 'windows', '10'): curl_cffi.requests.BrowserType.chrome100,
        ImpersonateTarget('chrome', '99', 'windows', '10'): curl_cffi.requests.BrowserType.chrome99,
        ImpersonateTarget('edge', '101', 'windows', '10'): curl_cffi.requests.BrowserType.edge101,
        ImpersonateTarget('edge', '99', 'windows', '10'): curl_cffi.requests.BrowserType.edge99,
        **({
            ImpersonateTarget('safari', '17.0', 'macos', '14'): curl_cffi.requests.BrowserType.safari17_0,
        } if curl_cffi_version >= (0, 7, 0) else {}),
        ImpersonateTarget('safari', '15.5', 'macos', '12'): curl_cffi.requests.BrowserType.safari15_5,
        ImpersonateTarget('safari', '15.3', 'macos', '11'): curl_cffi.requests.BrowserType.safari15_3,
        ImpersonateTarget('chrome', '99', 'android', '12'): curl_cffi.requests.BrowserType.chrome99_android,
        **({
            ImpersonateTarget('safari', '17.2', 'ios', '17.2'): curl_cffi.requests.BrowserType.safari17_2_ios,
        } if curl_cffi_version >= (0, 7, 0) else {}),
    }

    def _create_instance(self, cookiejar=None):
        return curl_cffi.requests.Session(cookies=cookiejar)

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('impersonate', None)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)
        # CurlCFFIRH ignores legacy ssl options currently.
        # Impersonation generally uses a looser SSL configuration than urllib/requests.
        extensions.pop('legacy_ssl', None)

    def send(self, request: Request) -> Response:
        target = self._get_request_target(request)
        try:
            response = super().send(request)
        except HTTPError as e:
            e.response.extensions['impersonate'] = target
            raise
        response.extensions['impersonate'] = target
        return response

    def _send(self, request: Request):
        max_redirects_exceeded = False
        session: curl_cffi.requests.Session = self._get_instance(
            cookiejar=self._get_cookiejar(request) if 'cookie' not in request.headers else None)

        if self.verbose:
            session.curl.setopt(CurlOpt.VERBOSE, 1)

        proxies = self._get_proxies(request)
        if 'no' in proxies:
            session.curl.setopt(CurlOpt.NOPROXY, proxies['no'])
            proxies.pop('no', None)

        # curl doesn't support per protocol proxies, so we select the one that matches the request protocol
        proxy = select_proxy(request.url, proxies=proxies)
        if proxy:
            session.curl.setopt(CurlOpt.PROXY, proxy)
            scheme = urllib.parse.urlparse(request.url).scheme.lower()
            if scheme != 'http':
                # Enable HTTP CONNECT for HTTPS urls.
                # Don't use CONNECT for http for compatibility with urllib behaviour.
                # See: https://curl.se/libcurl/c/CURLOPT_HTTPPROXYTUNNEL.html
                session.curl.setopt(CurlOpt.HTTPPROXYTUNNEL, 1)

            # curl_cffi does not currently set these for proxies
            session.curl.setopt(CurlOpt.PROXY_CAINFO, certifi.where())

            if not self.verify:
                session.curl.setopt(CurlOpt.PROXY_SSL_VERIFYPEER, 0)
                session.curl.setopt(CurlOpt.PROXY_SSL_VERIFYHOST, 0)

        headers = self._get_impersonate_headers(request)

        if self._client_cert:
            session.curl.setopt(CurlOpt.SSLCERT, self._client_cert['client_certificate'])
            client_certificate_key = self._client_cert.get('client_certificate_key')
            client_certificate_password = self._client_cert.get('client_certificate_password')
            if client_certificate_key:
                session.curl.setopt(CurlOpt.SSLKEY, client_certificate_key)
            if client_certificate_password:
                session.curl.setopt(CurlOpt.KEYPASSWD, client_certificate_password)

        timeout = self._calculate_timeout(request)

        # set CURLOPT_LOW_SPEED_LIMIT and CURLOPT_LOW_SPEED_TIME to act as a read timeout. [1]
        # This is required only for 0.5.10 [2]
        # Note: CURLOPT_LOW_SPEED_TIME is in seconds, so we need to round up to the nearest second. [3]
        # [1] https://unix.stackexchange.com/a/305311
        # [2] https://github.com/yifeikong/curl_cffi/issues/156
        # [3] https://curl.se/libcurl/c/CURLOPT_LOW_SPEED_TIME.html
        session.curl.setopt(CurlOpt.LOW_SPEED_LIMIT, 1)  # 1 byte per second
        session.curl.setopt(CurlOpt.LOW_SPEED_TIME, math.ceil(timeout))

        try:
            curl_response = session.request(
                method=request.method,
                url=request.url,
                headers=headers,
                data=request.data,
                verify=self.verify,
                max_redirects=5,
                timeout=(timeout, timeout),
                impersonate=self._SUPPORTED_IMPERSONATE_TARGET_MAP.get(
                    self._get_request_target(request)),
                interface=self.source_address,
                stream=True,
            )
        except curl_cffi.requests.errors.RequestsError as e:
            if e.code == CurlECode.PEER_FAILED_VERIFICATION:
                raise CertificateVerifyError(cause=e) from e

            elif e.code == CurlECode.SSL_CONNECT_ERROR:
                raise SSLError(cause=e) from e

            elif e.code == CurlECode.TOO_MANY_REDIRECTS:
                max_redirects_exceeded = True
                curl_response = e.response

            elif (
                e.code == CurlECode.PROXY
                or (e.code == CurlECode.RECV_ERROR and 'CONNECT' in str(e))
            ):
                raise ProxyError(cause=e) from e
            else:
                raise TransportError(cause=e) from e

        response = CurlCFFIResponseAdapter(curl_response)

        if not 200 <= response.status < 300:
            raise HTTPError(response, redirect_loop=max_redirects_exceeded)

        return response


@register_preference(CurlCFFIRH)
def curl_cffi_preference(rh, request):
    return -100

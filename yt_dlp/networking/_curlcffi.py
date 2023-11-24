import io
import math

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
from .impersonate import ImpersonateRequestHandler
from ..dependencies import curl_cffi
from ..utils import int_or_none

if curl_cffi is None:
    raise ImportError('curl_cffi is not installed')

import curl_cffi.requests
from curl_cffi.const import CurlECode, CurlOpt


class CurlCFFIResponseReader(io.IOBase):
    def __init__(self, response: curl_cffi.requests.Response):
        self._response = response
        self._buffer = b''
        self._eof = False
        self.bytes_read = 0

    def readable(self):
        return True

    def read(self, size=None):
        exception_raised = True
        try:
            while not self._eof and (size is None or len(self._buffer) < size):
                chunk = next(self._response.iter_content(), None)
                if chunk is None:
                    self._eof = True
                    break
                self._buffer += chunk
                self.bytes_read += len(self._buffer)

            if size is None:
                data = self._buffer
                self._buffer = b''
            else:
                data = self._buffer[:size]
                self._buffer = self._buffer[size:]

            # "free" the curl instance if the response is fully read.
            # curl_cffi doesn't do this automatically and only allows one open response per thread
            if self._eof and len(self._buffer) == 0:
                self.close()
            exception_raised = False
            return data
        finally:
            if exception_raised and not self.closed:
                self.close()

    def close(self):
        self._response.close()
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
            raise


@register_rh
class CurlCFFIRH(ImpersonateRequestHandler, InstanceStoreMixin):
    RH_NAME = 'curl_cffi'
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP = {
        ('chrome', '110', 'windows', '10'): curl_cffi.requests.BrowserType.chrome110,
        ('chrome', '107', 'windows', '10'): curl_cffi.requests.BrowserType.chrome107,
        ('chrome', '104', 'windows', '10'): curl_cffi.requests.BrowserType.chrome104,
        ('chrome', '101', 'windows', '10'): curl_cffi.requests.BrowserType.chrome101,
        ('chrome', '99', 'windows', '10'): curl_cffi.requests.BrowserType.chrome99,
        ('chrome', '99', 'android', '12'): curl_cffi.requests.BrowserType.chrome99_android,
        ('edge', '101', 'windows', '10'): curl_cffi.requests.BrowserType.edge101,
        ('edge', '99', 'windows', '10'): curl_cffi.requests.BrowserType.edge99,
        ('safari', '15.5', 'macos', '12.4'): curl_cffi.requests.BrowserType.safari15_5,
        ('safari', '15.3', 'macos', '11.6.4'): curl_cffi.requests.BrowserType.safari15_3,
    }

    def _create_instance(self, cookiejar=None):
        return curl_cffi.requests.Session(cookies=cookiejar)

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('impersonate', None)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)

    def _send(self, request: Request):
        max_redirects_exceeded = False
        cookiejar = request.extensions.get('cookiejar') or self.cookiejar
        session: curl_cffi.requests.Session = self._get_instance(
            cookiejar=cookiejar if 'cookie' not in request.headers else None)

        if self.verbose:
            session.curl.setopt(CurlOpt.VERBOSE, 1)

        proxies = (request.proxies or self.proxies).copy()
        if 'no' in proxies:
            session.curl.setopt(CurlOpt.NOPROXY, proxies['no'].encode())
            proxies.pop('no', None)

        # curl doesn't support per protocol proxies, so we select the one that matches the request protocol
        proxy = select_proxy(request.url, proxies=proxies)
        if proxy:
            session.curl.setopt(CurlOpt.PROXY, proxy.encode())
            if proxy.startswith('https'):
                # enable HTTP CONNECT for https urls
                session.curl.setopt(CurlOpt.HTTPPROXYTUNNEL, 1)

        headers = self._get_impersonate_headers(request)

        if self._client_cert:
            session.curl.setopt(CurlOpt.SSLCERT, self._client_cert['client_certificate'].encode())
            client_certificate_key = self._client_cert.get('client_certificate_key')
            client_certificate_password = self._client_cert.get('client_certificate_password')
            if client_certificate_key:
                session.curl.setopt(CurlOpt.SSLKEY, client_certificate_key.encode())
            if client_certificate_password:
                session.curl.setopt(CurlOpt.KEYPASSWD, client_certificate_password.encode())

        timeout = float(request.extensions.get('timeout') or self.timeout)

        # set CURLOPT_LOW_SPEED_LIMIT and CURLOPT_LOW_SPEED_TIME to act as a read timeout. [1]
        # curl_cffi does not currently do this [2]
        # Note that CURLOPT_LOW_SPEED_TIME is in seconds, so we need to round up to the nearest second [3]
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
                timeout=timeout,
                impersonate=self._get_mapped_target(request),
                interface=self.source_address,
                stream=True
            )
        except curl_cffi.requests.errors.RequestsError as e:
            if e.code == CurlECode.PEER_FAILED_VERIFICATION:
                raise CertificateVerifyError(cause=e) from e

            elif e.code == CurlECode.SSL_CONNECT_ERROR:
                raise SSLError(cause=e) from e

            elif e.code == CurlECode.TOO_MANY_REDIRECTS:
                max_redirects_exceeded = True
                curl_response = e.response

            elif e.code == CurlECode.PARTIAL_FILE:
                partial = e.response.content
                content_length = int_or_none(e.response.headers.get('Content-Length'))
                raise IncompleteRead(
                    partial=len(partial),
                    expected=content_length - len(partial) if content_length is not None else None,
                    cause=e) from e
            elif e.code == CurlECode.PROXY:
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

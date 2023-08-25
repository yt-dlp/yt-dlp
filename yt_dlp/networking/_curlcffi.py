import io
import re
from enum import IntEnum

from .common import Features, Request, Response, register_rh, register_preference
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    IncompleteRead,
    SSLError,
    TransportError,
)
from .impersonate import ImpersonateRequestHandler
from ._helper import InstanceStoreMixin, select_proxy
from ..cookies import LenientSimpleCookie
from ..dependencies import curl_cffi
from ..utils import int_or_none, traverse_obj

if curl_cffi is None:
    raise ImportError('curl_cffi is not installed')

import curl_cffi.requests
from curl_cffi import ffi
from curl_cffi.const import CurlInfo, CurlOpt, CurlECode


@register_rh
class CurlCFFIRH(ImpersonateRequestHandler, InstanceStoreMixin):
    RH_NAME = 'curl_cffi'
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_IMPERSONATE_TARGETS = curl_cffi.requests.BrowserType._member_names_

    def _create_instance(self, cookiejar=None):
        return curl_cffi.requests.Session(cookies=cookiejar)

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('impersonate', None)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)

    def _send(self, request: Request):
        # XXX: curl_cffi reads the whole response at once into memory
        # Streaming is not yet supported.
        # See: https://github.com/yifeikong/curl_cffi/issues/26
        max_redirects_exceeded = False
        cookiejar = request.extensions.get('cookiejar') or self.cookiejar
        session: CurlCFFISession = self._get_instance(
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

        headers = self._get_impersonate_headers(request)

        if self._client_cert:
            session.curl.setopt(CurlOpt.SSLCERT, self._client_cert['client_certificate'].encode())
            client_certificate_key = self._client_cert.get('client_certificate_key')
            client_certificate_password = self._client_cert.get('client_certificate_password')
            if client_certificate_key:
                session.curl.setopt(CurlOpt.SSLKEY, client_certificate_key.encode())
            if client_certificate_password:
                session.curl.setopt(CurlOpt.KEYPASSWD, client_certificate_password.encode())
        try:
            curl_response = session.request(
                method=request.method,
                url=request.url,
                headers=headers,
                data=request.data,
                verify=self.verify,
                max_redirects=5,
                timeout=request.extensions.get('timeout') or self.timeout,
                impersonate=self._get_impersonate_target(request),
                interface=self.source_address,
            )
        except curl_cffi.requests.errors.RequestsError as e:
            if e.code in (CurlECode.PEER_FAILED_VERIFICATION, CurlECode.OBSOLETE51):
                # Error code 51 used to be this in curl <7.62.0
                # See: https://curl.se/libcurl/c/libcurl-errors.html
                raise CertificateVerifyError(cause=e) from e

            elif e.code == CurlECode.SSL_CONNECT_ERROR:
                raise SSLError(cause=e) from e

            elif e.code == CurlECode.TOO_MANY_REDIRECTS:
                # The response isn't exposed on too many redirects.
                # We are creating a dummy response here, but it's
                # not ideal since it only contains initial request data
                max_redirects_exceeded = True
                curl_response = curl_cffi.requests.models.Response(
                    curl=session.curl,
                    request=curl_cffi.requests.models.Request(
                        url=request.url,
                        headers=curl_cffi.requests.headers.Headers(request.headers),
                        method=request.method,
                    ))

                # We can try extract *some* data from curl
                curl_response.url = session.curl.getinfo(CurlInfo.EFFECTIVE_URL).decode()
                curl_response.status_code = session.curl.getinfo(CurlInfo.RESPONSE_CODE)

            elif e.code == CurlECode.PARTIAL_FILE:
                raise IncompleteRead(
                    # TODO
                    # XXX: do we need partial to have the content?
                    partial=[''] * int(session.curl.getinfo(CurlInfo.SIZE_DOWNLOAD)),
                    expected=session.curl.getinfo(CurlInfo.CONTENT_LENGTH_DOWNLOAD),
                    cause=e) from e
            else:
                raise TransportError(cause=e) from e

        response = Response(
            io.BytesIO(curl_response.content),
            headers=curl_response.headers,
            url=curl_response.url,
            status=curl_response.status_code)

        if not 200 <= response.status < 300:
            raise HTTPError(response, redirect_loop=max_redirects_exceeded)

        return response


@register_preference(CurlCFFIRH)
def curl_cffi_preference(rh, request):
    return -100


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
from curl_cffi.const import CurlInfo, CurlOpt


class CurlCFFISession(curl_cffi.requests.Session):

    def _set_curl_options(self, curl, method: str, url: str, *args, **kwargs):

        res = super()._set_curl_options(curl, method, url, *args, **kwargs)
        data = traverse_obj(kwargs, 'data') or traverse_obj(args, 1)

        # Attempt to align curl redirect handling with ours
        curl.setopt(CurlOpt.CUSTOMREQUEST, ffi.NULL)

        if data and method != 'POST':
            # Don't strip data on 301,302,303 redirects for PUT etc.
            curl.setopt(CurlOpt.POSTREDIR, 1 | 2 | 4)  # CURL_REDIR_POST_ALL

        if method not in ('GET', 'POST'):
            curl.setopt(CurlOpt.CUSTOMREQUEST, method.encode())

        return res


def get_error_code(error: curl_cffi.curl.CurlError):
    return int_or_none(re.search(r'ErrCode:\s+(\d+)', str(error)).group(1))


@register_rh
class CurlCFFIRH(ImpersonateRequestHandler, InstanceStoreMixin):
    RH_NAME = 'curl_cffi'
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_IMPERSONATE_TARGETS = curl_cffi.requests.BrowserType._member_names_

    def _create_instance(self):
        return CurlCFFISession()

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('impersonate', None)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)

    def _generate_set_cookie(self, cookiejar):
        for cookie in cookiejar:
            encoder = LenientSimpleCookie()
            values = []
            _, value = encoder.value_encode(cookie.value)
            values.append(f'{cookie.name}={value}')
            if cookie.domain:
                values.append(f'Domain={cookie.domain}')
            if cookie.path:
                values.append(f'Path={cookie.path}')
            if cookie.secure:
                values.append('Secure')
            if cookie.expires:
                values.append(f'Expires={cookie.expires}')
            if cookie.version:
                values.append(f'Version={cookie.version}')
            yield '; '.join(values)

    def _send(self, request: Request):
        # XXX: curl_cffi reads the whole response at once into memory
        # Streaming is not yet supported.
        # See: https://github.com/yifeikong/curl_cffi/issues/26
        max_redirects_exceeded = False
        session: CurlCFFISession = self._get_instance()

        if self.verbose:
            session.curl.setopt(CurlOpt.VERBOSE, 1)

        cookiejar = request.extensions.get('cookiejar') or self.cookiejar

        # Reset the internal curl cookie store to ensure consistency with our cookiejar
        # (only needed until we have a way of extracting all cookies from curl)
        # See: https://curl.se/libcurl/c/CURLOPT_COOKIELIST.html
        session.curl.setopt(CurlOpt.COOKIELIST, b'ALL')
        session.cookies.clear()
        for cookie_str in self._generate_set_cookie(cookiejar):
            session.curl.setopt(CurlOpt.COOKIELIST, ('set-cookie: ' + cookie_str).encode())
        if self.source_address is not None:
            session.curl.setopt(CurlOpt.INTERFACE, self.source_address.encode())

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
            )
        except curl_cffi.requests.errors.RequestsError as e:
            error_code = get_error_code(e)
            if error_code in (CurlECode.PEER_FAILED_VERIFICATION, CurlECode.OBSOLETE51):
                # Error code 51 used to be this in curl <7.62.0
                # See: https://curl.se/libcurl/c/libcurl-errors.html
                raise CertificateVerifyError(cause=e) from e

            elif error_code == CurlECode.SSL_CONNECT_ERROR:
                raise SSLError(cause=e) from e

            elif error_code == CurlECode.TOO_MANY_REDIRECTS:
                # The response isn't exposed on too many redirects.
                # We are creating a dummy response here, but it's
                # not ideal since it only contains initial request data
                max_redirects_exceeded = True
                curl_response = curl_cffi.requests.cookies.Response(
                    curl=session.curl,
                    request=curl_cffi.requests.cookies.Request(
                        url=request.url,
                        headers=curl_cffi.requests.headers.Headers(request.headers),
                        method=request.method,
                    ))

                # We can try extract *some* data from curl
                curl_response.url = session.curl.getinfo(CurlInfo.EFFECTIVE_URL).decode()
                curl_response.status_code = session.curl.getinfo(CurlInfo.RESPONSE_CODE)

            elif error_code == CurlECode.PARTIAL_FILE:
                raise IncompleteRead(
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

        # XXX: this won't apply cookies from intermediate responses in a redirect chain
        # curl_cffi doesn't support CurlInfo.COOKIELIST yet which we need to reliably read cookies
        # See: https://github.com/yifeikong/curl_cffi/issues/4
        for cookie in session.cookies.jar:
            cookiejar.set_cookie(cookie)

        if not 200 <= response.status < 300:
            raise HTTPError(response, redirect_loop=max_redirects_exceeded)

        return response


@register_preference(CurlCFFIRH)
def curl_cffi_preference(rh, request):
    return -100


# https://curl.se/libcurl/c/libcurl-errors.html
class CurlECode(IntEnum):
    OK = 0
    UNSUPPORTED_PROTOCOL = 1
    FAILED_INIT = 2
    URL_MALFORMAT = 3
    NOT_BUILT_IN = 4
    COULDNT_RESOLVE_PROXY = 5
    COULDNT_RESOLVE_HOST = 6
    COULDNT_CONNECT = 7
    WEIRD_SERVER_REPLY = 8
    REMOTE_ACCESS_DENIED = 9
    FTP_ACCEPT_FAILED = 10
    FTP_WEIRD_PASS_REPLY = 11
    FTP_ACCEPT_TIMEOUT = 12
    FTP_WEIRD_PASV_REPLY = 13
    FTP_WEIRD_227_FORMAT = 14
    FTP_CANT_GET_HOST = 15
    HTTP2 = 16
    FTP_COULDNT_SET_TYPE = 17
    PARTIAL_FILE = 18
    FTP_COULDNT_RETR_FILE = 19
    OBSOLETE20 = 20
    QUOTE_ERROR = 21
    HTTP_RETURNED_ERROR = 22
    WRITE_ERROR = 23
    OBSOLETE24 = 24
    UPLOAD_FAILED = 25
    READ_ERROR = 26
    OUT_OF_MEMORY = 27
    OPERATION_TIMEDOUT = 28
    OBSOLETE29 = 29
    FTP_PORT_FAILED = 30
    FTP_COULDNT_USE_REST = 31
    OBSOLETE32 = 32
    RANGE_ERROR = 33
    HTTP_POST_ERROR = 34
    SSL_CONNECT_ERROR = 35
    BAD_DOWNLOAD_RESUME = 36
    FILE_COULDNT_READ_FILE = 37
    LDAP_CANNOT_BIND = 38
    LDAP_SEARCH_FAILED = 39
    OBSOLETE40 = 40
    FUNCTION_NOT_FOUND = 41
    ABORTED_BY_CALLBACK = 42
    BAD_FUNCTION_ARGUMENT = 43
    OBSOLETE44 = 44
    INTERFACE_FAILED = 45
    OBSOLETE46 = 46
    TOO_MANY_REDIRECTS = 47
    UNKNOWN_OPTION = 48
    SETOPT_OPTION_SYNTAX = 49
    OBSOLETE50 = 50
    OBSOLETE51 = 51
    GOT_NOTHING = 52
    SSL_ENGINE_NOTFOUND = 53
    SSL_ENGINE_SETFAILED = 54
    SEND_ERROR = 55
    RECV_ERROR = 56
    OBSOLETE57 = 57
    SSL_CERTPROBLEM = 58
    SSL_CIPHER = 59
    PEER_FAILED_VERIFICATION = 60
    BAD_CONTENT_ENCODING = 61
    OBSOLETE62 = 62
    FILESIZE_EXCEEDED = 63
    USE_SSL_FAILED = 64
    SEND_FAIL_REWIND = 65
    SSL_ENGINE_INITFAILED = 66
    LOGIN_DENIED = 67
    TFTP_NOTFOUND = 68
    TFTP_PERM = 69
    REMOTE_DISK_FULL = 70
    TFTP_ILLEGAL = 71
    TFTP_UNKNOWNID = 72
    REMOTE_FILE_EXISTS = 73
    TFTP_NOSUCHUSER = 74
    OBSOLETE75 = 75
    OBSOLETE76 = 76
    SSL_CACERT_BADFILE = 77
    REMOTE_FILE_NOT_FOUND = 78
    SSH = 79
    SSL_SHUTDOWN_FAILED = 80
    AGAIN = 81
    SSL_CRL_BADFILE = 82
    SSL_ISSUER_ERROR = 83
    FTP_PRET_FAILED = 84
    RTSP_CSEQ_ERROR = 85
    RTSP_SESSION_ERROR = 86
    FTP_BAD_FILE_LIST = 87
    CHUNK_FAILED = 88
    NO_CONNECTION_AVAILABLE = 89
    SSL_PINNEDPUBKEYNOTMATCH = 90
    SSL_INVALIDCERTSTATUS = 91
    HTTP2_STREAM = 92
    RECURSIVE_API_CALL = 93
    AUTH_ERROR = 94
    HTTP3 = 95
    QUIC_CONNECT_ERROR = 96
    PROXY = 97
    SSL_CLIENTCERT = 98
    UNRECOVERABLE_POLL = 99

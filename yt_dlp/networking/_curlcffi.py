import io
import os
import re
import tempfile
import urllib.request
from enum import IntEnum
from urllib.response import addinfourl

from .common import RequestHandler, Request, Response, register, Features
from .director import Preference, register_preference
from .exceptions import CertificateVerifyError, RequestError, SSLError, HTTPError, IncompleteRead, TransportError
from .utils import InstanceStoreMixin, select_proxy
from ..cookies import YoutubeDLCookieJar, LenientSimpleCookie
from ..utils import int_or_none, traverse_obj

from ..dependencies import curl_cffi

if curl_cffi is None:
    raise ImportError('curl_cffi is not installed')

from curl_cffi import requests as crequests, ffi


class CurlCFFISession(crequests.Session):

    def __init__(
        self,
        verbose=False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.verbose = verbose

    @property
    def curl(self):
        # due to how curl_cffi handles threading
        curl = super().curl
        if self.verbose:
            curl.setopt(curl_cffi.curl.CurlOpt.VERBOSE, 1)
        return curl

    def _set_curl_options(self, curl, method: str, url: str, *args, **kwargs):

        res = super()._set_curl_options(curl, method, url, *args, **kwargs)
        data = traverse_obj(kwargs, 'data') or traverse_obj(args, 1)

        # Attempt to align curl redirect handling with ours
        curl.setopt(curl_cffi.curl.CurlOpt.CUSTOMREQUEST, ffi.NULL)

        if data and method != 'POST':
            # Don't strip data on 301,302,303 redirects for PUT etc.
            curl.setopt(curl_cffi.curl.CurlOpt.POSTREDIR, 1 | 2 | 4)  # CURL_REDIR_POST_ALL

        if method not in ('GET', 'POST'):
            curl.setopt(curl_cffi.curl.CurlOpt.CUSTOMREQUEST, method.encode())

        return res


def get_error_code(error: curl_cffi.curl.CurlError):
    return int_or_none(re.search(r'ErrCode:\s+(\d+)', str(error)).group(1))


@register
class CurlCFFIRH(RequestHandler, InstanceStoreMixin):
    RH_NAME = 'curl_cffi'
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')

    def _create_instance(self):
        session_opts = {}

        if self.verbose:
            session_opts['verbose'] = True

        session = CurlCFFISession(**session_opts)
        return session

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

        # TODO: curl_cffi only sets cookie header for initial request
        # TODO: see if we can avoid reading the whole response into memory
        max_redirects_exceeded = False
        session: CurlCFFISession = self._get_instance()
        cookiejar = request.extensions.get('cookiejar') or self.cookiejar

        # Reset the internal curl cookie store to ensure consistency with our cookiejar
        # See: https://curl.se/libcurl/c/CURLOPT_COOKIELIST.html
        # XXX: does this actually work?
        session.curl.setopt(curl_cffi.curl.CurlOpt.COOKIELIST, b'ALL')
        session.cookies.clear()
        for cookie_str in self._generate_set_cookie(cookiejar):
            session.curl.setopt(curl_cffi.curl.CurlOpt.COOKIELIST, ('set-cookie: ' + cookie_str).encode())

        # XXX: if we need to change http version
        # session.curl.setopt(curl_cffi.curl.CurlOpt.HTTP_VERSION, 2)
        if self.source_address is not None:
            session.curl.setopt(curl_cffi.curl.CurlOpt.INTERFACE, self.source_address.encode())

        proxies = (request.proxies or self.proxies).copy()
        if 'no' in proxies:
            session.curl.setopt(curl_cffi.curl.CurlOpt.NOPROXY, proxies['no'].encode())
            proxies.pop('no', None)
        if 'all' in proxies:
            session.curl.setopt(curl_cffi.curl.CurlOpt.PROXY, proxies['all'].encode())
        else:
            # curl doesn't support per protocol proxies, so we select the one that matches the request protocol
            proxy = select_proxy(request.url, proxies=proxies)
            if proxy:
                session.curl.setopt(curl_cffi.curl.CurlOpt.PROXY, proxy.encode())
        try:
            curl_response = session.request(
                method=request.method,
                url=request.url,
                headers=self._merge_headers(request.headers),
                data=request.data,
                verify=self.verify,
                max_redirects=5,
                timeout=request.extensions.get('timeout') or self.timeout,
            )
        except crequests.errors.RequestsError as e:
            error_code = get_error_code(e)
            if error_code in (CurlECode.CURLE_PEER_FAILED_VERIFICATION, CurlECode.CURLE_OBSOLETE51):
                # Error code 51 used to be this in curl <7.62.0
                # See: https://curl.se/libcurl/c/libcurl-errors.html
                raise CertificateVerifyError(cause=e) from e

            elif error_code == CurlECode.CURLE_SSL_CONNECT_ERROR:
                raise SSLError(cause=e) from e

            elif error_code == CurlECode.CURLE_TOO_MANY_REDIRECTS:
                # TODO: curl_cffi doesn't expose a response on too many redirects
                # We are creating a dummy response here but it's
                # not ideal since it only contains initial request data
                max_redirects_exceeded = True
                curl_response = crequests.cookies.Response(
                    curl=session.curl,
                    request=crequests.cookies.Request(
                        url=request.url,
                        headers=crequests.headers.Headers(request.headers),
                        method=request.method,
                    ))

                # We can try extract *some* data from curl
                curl_response.url = session.curl.getinfo(curl_cffi.curl.CurlInfo.EFFECTIVE_URL).decode()
                curl_response.status_code = session.curl.getinfo(curl_cffi.curl.CurlInfo.RESPONSE_CODE)
            elif error_code == CurlECode.CURLE_PARTIAL_FILE:
                raise IncompleteRead(
                    # TODO: do we need partial to have the content?
                    partial=[''] * int(session.curl.getinfo(curl_cffi.curl.CurlInfo.SIZE_DOWNLOAD)),
                    expected=session.curl.getinfo(curl_cffi.curl.CurlInfo.CONTENT_LENGTH_DOWNLOAD),
                    cause=e) from e
            else:
                raise TransportError(cause=e) from e

        response = CurlCFFIResponseAdapter(
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


class CurlCFFIResponseAdapter(Response):
    pass


@register_preference
class CurlCFFIPrefernce(Preference):
    _RH_KEY = CurlCFFIRH.RH_KEY

    def _get_preference(self, request: Request, handler: RequestHandler) -> int:
        if not request.extensions.get('impersonate'):
            return 1000
        else:
            return 1000


# https://curl.se/libcurl/c/libcurl-errors.html
class CurlECode(IntEnum):
    CURLE_OK = 0
    CURLE_UNSUPPORTED_PROTOCOL = 1
    CURLE_FAILED_INIT = 2
    CURLE_URL_MALFORMAT = 3
    CURLE_NOT_BUILT_IN = 4
    CURLE_COULDNT_RESOLVE_PROXY = 5
    CURLE_COULDNT_RESOLVE_HOST = 6
    CURLE_COULDNT_CONNECT = 7
    CURLE_WEIRD_SERVER_REPLY = 8
    CURLE_REMOTE_ACCESS_DENIED = 9
    CURLE_FTP_ACCEPT_FAILED = 10
    CURLE_FTP_WEIRD_PASS_REPLY = 11
    CURLE_FTP_ACCEPT_TIMEOUT = 12
    CURLE_FTP_WEIRD_PASV_REPLY = 13
    CURLE_FTP_WEIRD_227_FORMAT = 14
    CURLE_FTP_CANT_GET_HOST = 15
    CURLE_HTTP2 = 16
    CURLE_FTP_COULDNT_SET_TYPE = 17
    CURLE_PARTIAL_FILE = 18
    CURLE_FTP_COULDNT_RETR_FILE = 19
    CURLE_OBSOLETE20 = 20
    CURLE_QUOTE_ERROR = 21
    CURLE_HTTP_RETURNED_ERROR = 22
    CURLE_WRITE_ERROR = 23
    CURLE_OBSOLETE24 = 24
    CURLE_UPLOAD_FAILED = 25
    CURLE_READ_ERROR = 26
    CURLE_OUT_OF_MEMORY = 27
    CURLE_OPERATION_TIMEDOUT = 28
    CURLE_OBSOLETE29 = 29
    CURLE_FTP_PORT_FAILED = 30
    CURLE_FTP_COULDNT_USE_REST = 31
    CURLE_OBSOLETE32 = 32
    CURLE_RANGE_ERROR = 33
    CURLE_HTTP_POST_ERROR = 34
    CURLE_SSL_CONNECT_ERROR = 35
    CURLE_BAD_DOWNLOAD_RESUME = 36
    CURLE_FILE_COULDNT_READ_FILE = 37
    CURLE_LDAP_CANNOT_BIND = 38
    CURLE_LDAP_SEARCH_FAILED = 39
    CURLE_OBSOLETE40 = 40
    CURLE_FUNCTION_NOT_FOUND = 41
    CURLE_ABORTED_BY_CALLBACK = 42
    CURLE_BAD_FUNCTION_ARGUMENT = 43
    CURLE_OBSOLETE44 = 44
    CURLE_INTERFACE_FAILED = 45
    CURLE_OBSOLETE46 = 46
    CURLE_TOO_MANY_REDIRECTS = 47
    CURLE_UNKNOWN_OPTION = 48
    CURLE_SETOPT_OPTION_SYNTAX = 49
    CURLE_OBSOLETE50 = 50
    CURLE_OBSOLETE51 = 51
    CURLE_GOT_NOTHING = 52
    CURLE_SSL_ENGINE_NOTFOUND = 53
    CURLE_SSL_ENGINE_SETFAILED = 54
    CURLE_SEND_ERROR = 55
    CURLE_RECV_ERROR = 56
    CURLE_OBSOLETE57 = 57
    CURLE_SSL_CERTPROBLEM = 58
    CURLE_SSL_CIPHER = 59
    CURLE_PEER_FAILED_VERIFICATION = 60
    CURLE_BAD_CONTENT_ENCODING = 61
    CURLE_OBSOLETE62 = 62
    CURLE_FILESIZE_EXCEEDED = 63
    CURLE_USE_SSL_FAILED = 64
    CURLE_SEND_FAIL_REWIND = 65
    CURLE_SSL_ENGINE_INITFAILED = 66
    CURLE_LOGIN_DENIED = 67
    CURLE_TFTP_NOTFOUND = 68
    CURLE_TFTP_PERM = 69
    CURLE_REMOTE_DISK_FULL = 70
    CURLE_TFTP_ILLEGAL = 71
    CURLE_TFTP_UNKNOWNID = 72
    CURLE_REMOTE_FILE_EXISTS = 73
    CURLE_TFTP_NOSUCHUSER = 74
    CURLE_OBSOLETE75 = 75
    CURLE_OBSOLETE76 = 76
    CURLE_SSL_CACERT_BADFILE = 77
    CURLE_REMOTE_FILE_NOT_FOUND = 78
    CURLE_SSH = 79
    CURLE_SSL_SHUTDOWN_FAILED = 80
    CURLE_AGAIN = 81
    CURLE_SSL_CRL_BADFILE = 82
    CURLE_SSL_ISSUER_ERROR = 83
    CURLE_FTP_PRET_FAILED = 84
    CURLE_RTSP_CSEQ_ERROR = 85
    CURLE_RTSP_SESSION_ERROR = 86
    CURLE_FTP_BAD_FILE_LIST = 87
    CURLE_CHUNK_FAILED = 88
    CURLE_NO_CONNECTION_AVAILABLE = 89
    CURLE_SSL_PINNEDPUBKEYNOTMATCH = 90
    CURLE_SSL_INVALIDCERTSTATUS = 91
    CURLE_HTTP2_STREAM = 92
    CURLE_RECURSIVE_API_CALL = 93
    CURLE_AUTH_ERROR = 94
    CURLE_HTTP3 = 95
    CURLE_QUIC_CONNECT_ERROR = 96
    CURLE_PROXY = 97
    CURLE_SSL_CLIENTCERT = 98
    CURLE_UNRECOVERABLE_POLL = 99

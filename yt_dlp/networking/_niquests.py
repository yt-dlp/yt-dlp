import functools
import logging
import re
import socket
import warnings

from ..dependencies import brotli, niquests, niquests_urllib3 as urllib3, certifi
from ..utils import bug_reports_message, int_or_none, variadic
from ..utils.networking import normalize_url

if niquests is None:
    raise ImportError('niquests module is not installed')

if urllib3 is None:
    raise ImportError('urllib3-future module is not installed')

urllib3_version = tuple(int_or_none(x, default=0) for x in urllib3.__version__.split('.'))

if urllib3_version < (2, 1, 900):
    raise ImportError('Only urllib3-future >= 2.1.900 is supported')

if niquests.__build__ < 0x030000:
    raise ImportError('Only niquests >= 3.0.0 is supported')

from ._helper import (
    InstanceStoreMixin,
    add_accept_encoding_header,
    create_connection,
    create_socks_proxy_socket,
    get_redirect_method,
    make_socks_proxy_opts,
)
from .common import (
    Features,
    RequestHandler,
    Response,
    register_preference,
    register_rh,
)
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    IncompleteRead,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
)
from ..socks import ProxyError as SocksProxyError

SUPPORTED_ENCODINGS = [
    'gzip', 'deflate'
]

if brotli is not None:
    SUPPORTED_ENCODINGS.append('br')

"""
Override urllib3's behavior to not convert lower-case percent-encoded characters
to upper-case during url normalization process.

RFC3986 defines that the lower or upper case percent-encoded hexidecimal characters are equivalent
and normalizers should convert them to uppercase for consistency [1].

However, some sites may have an incorrect implementation where they provide
a percent-encoded url that is then compared case-sensitively.[2]

While this is a very rare case, since urllib does not do this normalization step, it
is best to avoid it in requests too for compatability reasons.

1: https://tools.ietf.org/html/rfc3986#section-2.1
2: https://github.com/streamlink/streamlink/pull/4003
"""


class Urllib3PercentREOverride:
    def __init__(self, r: re.Pattern):
        self.re = r

    # pass through all other attribute calls to the original re
    def __getattr__(self, item):
        return self.re.__getattribute__(item)

    def subn(self, repl, string, *args, **kwargs):
        return string, self.re.subn(repl, string, *args, **kwargs)[1]


if hasattr(urllib3.util.url, '_PERCENT_RE'):  # urllib3 >= 2.0.0
    urllib3.util.url._PERCENT_RE = Urllib3PercentREOverride(urllib3.util.url._PERCENT_RE)
else:
    warnings.warn('Failed to patch PERCENT_RE in urllib3 (does the attribute exist?)' + bug_reports_message())


class RequestsResponseAdapter(Response):
    def __init__(self, res: niquests.models.Response):
        super().__init__(
            fp=res.raw, headers=res.headers, url=res.url,
            status=res.status_code, reason=res.reason)

        self._requests_response = res

    def read(self, amt: int = None):
        try:
            # Interact with urllib3 response directly.
            return self.fp.read(amt, decode_content=True)

        # See urllib3.response.HTTPResponse.read() for exceptions raised on read
        except urllib3.exceptions.SSLError as e:
            raise SSLError(cause=e) from e

        except urllib3.exceptions.ProtocolError as e:
            # IncompleteRead is always contained within ProtocolError
            # See urllib3.response.HTTPResponse._error_catcher()
            if isinstance(e, urllib3.exceptions.IncompleteRead):
                ir_err = e
            else:
                ir_err = next(
                    (err for err in (e.__context__, e.__cause__, *variadic(e.args))
                     if isinstance(err, urllib3.exceptions.IncompleteRead)), None)
            if ir_err is not None:
                # `urllib3.exceptions.IncompleteRead` uses an `int` for its `partial` property.
                partial = ir_err.partial if isinstance(ir_err.partial, int) else len(ir_err.partial)
                raise IncompleteRead(partial=partial, expected=ir_err.expected) from e

            raise TransportError(cause=e) from e

        except urllib3.exceptions.HTTPError as e:
            # catch-all for any other urllib3 response exceptions
            raise TransportError(cause=e) from e


class RequestsHTTPAdapter(niquests.adapters.HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self._pm_args = {}

        if "source_address" in kwargs:
            if kwargs["source_address"] is not None:
                kwargs["source_address"] = (kwargs["source_address"], 0)

        self._proxy_ssl_context = None

        if "proxy_ssl_context" in kwargs:
            self._proxy_ssl_context = kwargs["proxy_ssl_context"]
            kwargs.pop("proxy_ssl_context")

        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        return super().init_poolmanager(*args, **kwargs, **self._pm_args)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        extra_kwargs = {}
        if not proxy.lower().startswith('socks') and self._proxy_ssl_context:
            extra_kwargs['proxy_ssl_context'] = self._proxy_ssl_context
        # hmm... the dev-socks server isn't happy with... Happy Eyeballs.
        # It makes the server unstable due to the concurrent conn attempts.
        if self._happy_eyeballs:
            self._happy_eyeballs = False
        return super().proxy_manager_for(proxy, **proxy_kwargs, **self._pm_args, **extra_kwargs)


class RequestsSession(niquests.sessions.Session):
    """
    Ensure unified redirect method handling with our urllib redirect handler.
    """

    def rebuild_method(self, prepared_request, response):
        new_method = get_redirect_method(prepared_request.method, response.status_code)

        # HACK: requests removes headers/body on redirect unless code was a 307/308.
        if new_method == prepared_request.method:
            response._real_status_code = response.status_code
            response.status_code = 308

        prepared_request.method = new_method

        # Requests fails to resolve dot segments on absolute redirect locations
        # See: https://github.com/yt-dlp/yt-dlp/issues/9020
        prepared_request.url = normalize_url(prepared_request.url)

    def rebuild_auth(self, prepared_request, response):
        # HACK: undo status code change from rebuild_method, if applicable.
        # rebuild_auth runs after requests would remove headers/body based on status code
        if hasattr(response, '_real_status_code'):
            response.status_code = response._real_status_code
            del response._real_status_code
        return super().rebuild_auth(prepared_request, response)


class Urllib3LoggingFilter(logging.Filter):

    def filter(self, record):
        # Ignore HTTP request messages since HTTPConnection prints those
        if record.msg == '%s://%s:%s "%s %s %s" %s %s':
            return False
        return True


class Urllib3LoggingHandler(logging.Handler):
    """Redirect urllib3 logs to our logger"""

    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger

    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                self._logger.error(msg)
            else:
                self._logger.stdout(msg)

        except Exception:
            self.handleError(record)


@register_rh
class NiquestsRH(RequestHandler, InstanceStoreMixin):

    """Niquests RequestHandler
    https://github.com/jawah/niquests
    """
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_ENCODINGS = tuple(SUPPORTED_ENCODINGS)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    RH_NAME = 'niquests'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Forward urllib3 debug messages to our logger
        logger = logging.getLogger('urllib3')
        self.__logging_handler = Urllib3LoggingHandler(logger=self._logger)
        self.__logging_handler.setFormatter(logging.Formatter('requests: %(message)s'))
        self.__logging_handler.addFilter(Urllib3LoggingFilter())
        logger.addHandler(self.__logging_handler)
        # TODO: Use a logger filter to suppress pool reuse warning instead
        logger.setLevel(logging.ERROR)

        if self.verbose:
            # Setting this globally is not ideal, but is easier than hacking with urllib3.
            # It could technically be problematic for scripts embedding yt-dlp.
            # However, it is unlikely debug traffic is used in that context in a way this will cause problems.
            urllib3.connection.HTTPConnection.debuglevel = 1
            logger.setLevel(logging.DEBUG)
        # this is expected if we are using --no-check-certificate
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def close(self):
        self._clear_instances()
        # Remove the logging handler that contains a reference to our logger
        # See: https://github.com/yt-dlp/yt-dlp/issues/8922
        logging.getLogger('urllib3').removeHandler(self.__logging_handler)

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)

    def _create_instance(self, cookiejar):
        certs = self._client_cert
        session = RequestsSession()

        session.verify = self.verify

        if self.verify and not self.prefer_system_certs and certifi is not None:
            session.verify = certifi.where()

        session.trust_env = False  # no need, we already load proxies from env
        session.cookies = cookiejar
        session.headers.setdefault("Connection", "keep-alive")

        has_client_cert = "client_certificate" in certs
        has_client_key = "client_certificate_key" in certs
        has_password = "client_certificate_password" in certs

        if len(list(filter(lambda _: _ is True, [has_client_cert, has_client_key, has_password]))) > 1:
            session.cert = (
                certs["client_certificate"],
                certs["client_certificate_key"] if has_client_key else None,
                certs["client_certificate_password"] if has_password else None,
            )
        elif has_client_cert:
            session.cert = certs["client_certificate"]

        session.adapters.clear()

        # we want to override the default adapter in order to leverage our proxy implt
        http_adapter = RequestsHTTPAdapter(source_address=self.source_address, max_retries=False, happy_eyeballs=True)

        session.mount("http://", http_adapter)
        session.mount("https://", http_adapter)

        return session

    def _send(self, request):
        headers = self._merge_headers(request.headers)
        add_accept_encoding_header(headers, SUPPORTED_ENCODINGS)

        max_redirects_exceeded = False

        session = self._get_instance(cookiejar=self._get_cookiejar(request))

        try:
            requests_res = session.request(
                method=request.method,
                url=request.url,
                data=request.data,
                headers=headers,
                timeout=self._calculate_timeout(request),
                proxies=self._get_proxies(request),
                allow_redirects=True,
                stream=True
            )

        except niquests.exceptions.TooManyRedirects as e:
            max_redirects_exceeded = True
            requests_res = e.response

        except niquests.exceptions.SSLError as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                raise CertificateVerifyError(cause=e) from e
            raise SSLError(cause=e) from e

        except niquests.exceptions.ProxyError as e:
            raise ProxyError(cause=e) from e

        except (niquests.exceptions.ConnectionError, niquests.exceptions.Timeout) as e:
            raise TransportError(cause=e) from e

        except urllib3.exceptions.HTTPError as e:
            # Catch any urllib3 exceptions that may leak through
            raise TransportError(cause=e) from e

        except niquests.exceptions.RequestException as e:
            # Miscellaneous Requests exceptions. May not necessary be network related e.g. InvalidURL
            raise RequestError(cause=e) from e

        res = RequestsResponseAdapter(requests_res)

        if not 200 <= res.status < 300:
            raise HTTPError(res, redirect_loop=max_redirects_exceeded)

        return res


@register_preference(NiquestsRH)
def requests_preference(rh, request):
    return 200


# Use our socks proxy implementation with requests to avoid an extra dependency.
class SocksHTTPConnection(urllib3.connection.HTTPConnection):
    def __init__(self, _socks_options, *args, **kwargs):  # must use _socks_options to pass PoolKey checks
        self._proxy_args = _socks_options
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        try:
            return create_connection(
                address=(self._proxy_args['addr'], self._proxy_args['port']),
                timeout=self.timeout,
                source_address=self.source_address,
                _create_socket_func=functools.partial(
                    create_socks_proxy_socket, (self.host, self.port), self._proxy_args))
        except (socket.timeout, TimeoutError) as e:
            raise urllib3.exceptions.ConnectTimeoutError(
                self, f'Connection to {self.host} timed out. (connect timeout={self.timeout})') from e
        except SocksProxyError as e:
            raise urllib3.exceptions.ProxyError(str(e), e) from e
        except OSError as e:
            raise urllib3.exceptions.NewConnectionError(
                self, f'Failed to establish a new connection: {e}') from e


class SocksHTTPSConnection(SocksHTTPConnection, urllib3.connection.HTTPSConnection):
    pass


class SocksHTTPConnectionPool(urllib3.HTTPConnectionPool):
    ConnectionCls = SocksHTTPConnection


class SocksHTTPSConnectionPool(urllib3.HTTPSConnectionPool):
    ConnectionCls = SocksHTTPSConnection


class SocksProxyManager(urllib3.PoolManager):

    def __init__(self, socks_proxy, username=None, password=None, num_pools=10, headers=None, **connection_pool_kw):
        connection_pool_kw['_socks_options'] = make_socks_proxy_opts(socks_proxy)
        super().__init__(num_pools, headers, **connection_pool_kw)
        self.pool_classes_by_scheme = {
            'http': SocksHTTPConnectionPool,
            'https': SocksHTTPSConnectionPool
        }


niquests.adapters.SOCKSProxyManager = SocksProxyManager

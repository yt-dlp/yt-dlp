import errno

from ..compat import (
    compat_http_client,
    compat_urllib_parse_urlparse,
    compat_urllib_parse
)

from .common import (
    get_std_headers,
    HTTPResponse,
    BackendAdapter,
    Request
)
from .socksproxy import (
    sockssocket,
    ProxyError as SocksProxyError
)
from .utils import (
    make_ssl_context,
    socks_create_proxy_args
)

from ..utils import (
    IncompleteRead,
    ConnectionReset,
    ReadTimeoutError,
    TransportError,
    ConnectionTimeoutError,
    SSLError,
    HTTPError,
    ProxyError,
    RequestError
)

import urllib3
from urllib3.util.url import parse_url
import urllib3.connection

SUPPORTED_ENCODINGS = [
    'gzip', 'deflate'
]


class Urllib3ResponseAdapter(HTTPResponse):
    def __init__(self, res):
        self._res = res
        self._url = res.geturl()
        if self._url:
            url_parsed = compat_urllib_parse_urlparse(self._url)
            if isinstance(url_parsed, compat_urllib_parse.ParseResultBytes):
                url_parsed = url_parsed.decode()
            if url_parsed.hostname is None:
                # hack
                netloc = f'{res.connection.host}:{res.connection.port}'
                url_parsed = url_parsed._replace(
                    netloc=netloc,
                    scheme='https')
            self._url = url_parsed.geturl()

        super().__init__(
            headers=res.headers, status=res.status,
            http_version=res.version)

    def geturl(self):
        return self._url

    def read(self, amt: int = None):
        try:
            return self._res.read(amt)
        except urllib3.exceptions.IncompleteRead as e:
            raise IncompleteRead(e.partial, self.geturl(), cause=e, expected=e.expected) from e
        except urllib3.exceptions.SSLError as e:
            raise SSLError(self.geturl(), cause=e) from e
        except urllib3.exceptions.ReadTimeoutError as e:
            raise ReadTimeoutError(self.geturl(), cause=e) from e
        except urllib3.exceptions.ProtocolError as e:
            original_cause = e.__cause__
            if isinstance(original_cause, compat_http_client.IncompleteRead) or 'incomplete read' in str(e).lower():
                if original_cause:
                    partial, expected = original_cause.partial, original_cause.expected
                else:
                    # TODO: capture incomplete read detail with regex
                    raise NotImplementedError

                raise IncompleteRead(partial, self.geturl(), cause=e, expected=expected) from e
            elif isinstance(original_cause, ConnectionResetError) or 'connection reset' in str(e).lower():
                raise ConnectionReset(self.geturl(), e, cause=e) from e
            elif isinstance(original_cause, OSError):
                if original_cause.errno == errno.ECONNRESET:
                    raise ConnectionReset(self.geturl(), cause=e) from e
                if original_cause.errno == errno.ETIMEDOUT:
                    raise ReadTimeoutError(self.geturl(), cause=e) from e

            raise TransportError(self.geturl(), e, cause=e) from e

    def close(self):
        super().close()
        return self._res.close()

    def tell(self) -> int:
        return self._res.tell()


class Urllib3BackendAdapter(BackendAdapter):
    SUPPORTED_SCHEMES = ['http', 'https']

    def _initialize(self):
        self.pools = {}
        if not self._is_force_disabled:
            if self.print_traffic:
                urllib3.add_stderr_logger()
        urllib3.disable_warnings()

    @property
    def _is_force_disabled(self):
        if 'no-urllib3' in self.ydl.params.get('compat_opts', []):
            return True
        return False

    def _create_pm(self, proxy=None):
        pm_args = {'ssl_context': make_ssl_context(self.ydl.params)}
        source_address = self.ydl.params.get('source_address')
        if source_address:
            pm_args['source_address'] = (source_address, 0)

        if proxy:
            if proxy.startswith('socks'):
                pm = SocksProxyManager(socks_proxy=proxy, **pm_args)
            else:
                pm = urllib3.ProxyManager(
                    proxy_url=proxy, proxy_ssl_context=pm_args.get('ssl_context'), **pm_args)
        else:
            pm = urllib3.PoolManager(**pm_args)
        return pm

    def get_pool(self, proxy=None):
        return self.pools.setdefault(proxy or '__noproxy__', self._create_pm(proxy))

    def can_handle(self, request: Request, **req_kwargs) -> bool:
        if self._is_force_disabled:
            self.write_debug('Not using urllib3 backend as no-urllib3 compat opt is set.', only_once=True)
            return False
        return super().can_handle(request, **req_kwargs)

    def _real_handle(self, request: Request, **kwargs) -> HTTPResponse:
        self.cookiejar.add_cookie_header(request)

        # TODO: implement custom redirect mixin for unified redirect handling
        # Remove headers not meant to be forwarded to different host
        retries = urllib3.Retry(
            remove_headers_on_redirect=request.unredirected_headers.keys(),
            raise_on_redirect=False, other=0, read=0, connect=0)
        all_headers = get_std_headers(SUPPORTED_ENCODINGS)
        all_headers.replace_headers(request.headers)
        all_headers.replace_headers(request.unredirected_headers)
        if not request.compression:
            del all_headers['accept-encoding']

        proxy = request.proxy
        if proxy:
            # urllib sets proxy scheme to url scheme if it is not set
            proxy_parsed = parse_url(proxy)
            if proxy_parsed.scheme is None:
                proxy = proxy_parsed._replace(scheme=parse_url(request.url).scheme).url
        try:
            try:
                urllib3_res = self.get_pool(proxy).urlopen(
                    method=request.method,
                    url=request.url,
                    request_url=request.url,  # TODO: needed for redirect compat
                    headers=dict(all_headers),
                    body=request.data,
                    preload_content=False,
                    timeout=request.timeout,
                    retries=retries,
                    redirect=True
                )

            except urllib3.exceptions.MaxRetryError as r:
                raise r.reason

        # TODO: these all need A LOT of work
        # TODO: this is recent
        # except urllib3.exceptions.NameResolutionError as e:
        #     # TODO: better regex
        #     mobj = re.match(r"Failed to resolve '(?P<host>[^']+)' \((?P<reason>[^)]*)", str(e))
        #     raise ResolveHostError(host=mobj.group('host'), cause=e) from e

        except urllib3.exceptions.ReadTimeoutError as e:
            raise ReadTimeoutError(e.url, msg=str(e), cause=e) from e
        except urllib3.exceptions.ConnectTimeoutError as e:
            raise ConnectionTimeoutError(msg=str(e), cause=e) from e
        except urllib3.exceptions.SSLError as e:
            raise SSLError(cause=e, msg=str(e)) from e

        except urllib3.exceptions.IncompleteRead as e:
            raise IncompleteRead(partial=e.partial, expected=e.expected, cause=e) from e

        except urllib3.exceptions.ProxyError as e:
            raise ProxyError(msg=str(e), cause=e) from e  # will likely need to handle this differently
        except urllib3.exceptions.ProtocolError as e:
            raise TransportError(msg=str(e), cause=e) from e

        except urllib3.exceptions.RequestError as e:
            raise RequestError(msg=str(e), url=e.url) from e

        except urllib3.exceptions.HTTPError as e:
            raise RequestError(msg=str(e)) from e

        res = Urllib3ResponseAdapter(urllib3_res)
        if not (
                (200 <= res.status < 300)
                or (res.status in (301, 302, 303, 307, 308) and request.get_method() in ('GET', 'HEAD'))
                or (res.status in (301, 302, 303) and request.get_method() == 'POST')
        ):
            raise HTTPError(res, res.url)

        if self.cookiejar:
            self.cookiejar.extract_cookies(res, request)

        return res


# Since we already have a socks proxy implementation,
# we can use that with urllib3 instead of requiring an extra dependency.
class SocksHTTPConnection(urllib3.connection.HTTPConnection):
    def __init__(self, _socks_options, *args, **kwargs):  # must use _socks_options to pass PoolKey checks
        self._proxy_args = _socks_options
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        sock = sockssocket()
        sock.setproxy(**self._proxy_args)
        if type(self.timeout) in (int, float):
            sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))

        # TODO
        except TimeoutError as e:
            raise urllib3.exceptions.ConnectTimeoutError from e
        except SocksProxyError as e:
            raise urllib3.exceptions.ProxyError from e
        except OSError as e:
            raise urllib3.exceptions.NewConnectionError from e

        return sock


class SocksHTTPSConnection(SocksHTTPConnection, urllib3.connection.HTTPSConnection):
    pass


class SocksHTTPConnectionPool(urllib3.HTTPConnectionPool):
    ConnectionCls = SocksHTTPConnection


class SocksHTTPSConnectionPool(urllib3.HTTPSConnectionPool):
    ConnectionCls = SocksHTTPSConnection


class SocksProxyManager(urllib3.PoolManager):

    def __init__(self, socks_proxy, **connection_pool_kw):
        connection_pool_kw['_socks_options'] = socks_create_proxy_args(socks_proxy)
        super().__init__(**connection_pool_kw)
        self.pool_classes_by_scheme = {
            'http': SocksHTTPConnectionPool,
            'https': SocksHTTPSConnectionPool
        }

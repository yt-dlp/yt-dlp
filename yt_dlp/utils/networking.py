from __future__ import annotations

import collections
import collections.abc
import random
import typing
import urllib.parse
import urllib.request

if typing.TYPE_CHECKING:
    T = typing.TypeVar('T')

from ._utils import NO_DEFAULT, remove_start, format_field
from .traversal import traverse_obj


def random_user_agent():
    _USER_AGENT_TPL = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36'
    _CHROME_VERSIONS = (
        '90.0.4430.212',
        '90.0.4430.24',
        '90.0.4430.70',
        '90.0.4430.72',
        '90.0.4430.85',
        '90.0.4430.93',
        '91.0.4472.101',
        '91.0.4472.106',
        '91.0.4472.114',
        '91.0.4472.124',
        '91.0.4472.164',
        '91.0.4472.19',
        '91.0.4472.77',
        '92.0.4515.107',
        '92.0.4515.115',
        '92.0.4515.131',
        '92.0.4515.159',
        '92.0.4515.43',
        '93.0.4556.0',
        '93.0.4577.15',
        '93.0.4577.63',
        '93.0.4577.82',
        '94.0.4606.41',
        '94.0.4606.54',
        '94.0.4606.61',
        '94.0.4606.71',
        '94.0.4606.81',
        '94.0.4606.85',
        '95.0.4638.17',
        '95.0.4638.50',
        '95.0.4638.54',
        '95.0.4638.69',
        '95.0.4638.74',
        '96.0.4664.18',
        '96.0.4664.45',
        '96.0.4664.55',
        '96.0.4664.93',
        '97.0.4692.20',
    )
    return _USER_AGENT_TPL % random.choice(_CHROME_VERSIONS)


class HTTPHeaderDict(dict):
    """
    Store and access keys case-insensitively.
    The constructor can take multiple dicts, in which keys in the latter are prioritised.

    Retains a case sensitive mapping of the headers, which can be accessed via `.sensitive()`.
    """
    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> typing.Self:
        obj = dict.__new__(cls, *args, **kwargs)
        obj.__sensitive_map = {}
        return obj

    def __init__(self, /, *args, **kwargs):
        super().__init__()
        self.__sensitive_map = {}

        for dct in filter(None, args):
            self.update(dct)
        if kwargs:
            self.update(kwargs)

    def sensitive(self, /) -> dict[str, str]:
        return {
            self.__sensitive_map[key]: value
            for key, value in self.items()
        }

    def __contains__(self, key: str, /) -> bool:
        return super().__contains__(key.title() if isinstance(key, str) else key)

    def __delitem__(self, key: str, /) -> None:
        key = key.title()
        del self.__sensitive_map[key]
        super().__delitem__(key)

    def __getitem__(self, key, /) -> str:
        return super().__getitem__(key.title())

    def __ior__(self, other, /):
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, dict):
            self.update(other)
            return
        return NotImplemented

    def __or__(self, other, /) -> typing.Self:
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, dict):
            return type(self)(self.sensitive(), other)
        return NotImplemented

    def __ror__(self, other, /) -> typing.Self:
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, dict):
            return type(self)(other, self.sensitive())
        return NotImplemented

    def __setitem__(self, key: str, value, /) -> None:
        if isinstance(value, bytes):
            value = value.decode('latin-1')
        key_title = key.title()
        self.__sensitive_map[key_title] = key
        super().__setitem__(key_title, str(value).strip())

    def clear(self, /) -> None:
        self.__sensitive_map.clear()
        super().clear()

    def copy(self, /) -> typing.Self:
        return type(self)(self.sensitive())

    @typing.overload
    def get(self, key: str, /) -> str | None: ...

    @typing.overload
    def get(self, key: str, /, default: T) -> str | T: ...

    def get(self, key, /, default=NO_DEFAULT):
        key = key.title()
        if default is NO_DEFAULT:
            return super().get(key)
        return super().get(key, default)

    @typing.overload
    def pop(self, key: str, /) -> str: ...

    @typing.overload
    def pop(self, key: str, /, default: T) -> str | T: ...

    def pop(self, key, /, default=NO_DEFAULT):
        key = key.title()
        if default is NO_DEFAULT:
            self.__sensitive_map.pop(key)
            return super().pop(key)
        self.__sensitive_map.pop(key, default)
        return super().pop(key, default)

    def popitem(self) -> tuple[str, str]:
        self.__sensitive_map.popitem()
        return super().popitem()

    @typing.overload
    def setdefault(self, key: str, /) -> str: ...

    @typing.overload
    def setdefault(self, key: str, /, default) -> str: ...

    def setdefault(self, key, /, default=None) -> str:
        key = key.title()
        if key in self.__sensitive_map:
            return super().__getitem__(key)

        self[key] = default or ''
        return self[key]

    def update(self, other, /, **kwargs) -> None:
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, collections.abc.Mapping):
            for key, value in other.items():
                self[key] = value

        elif hasattr(other, 'keys'):
            for key in other.keys():  # noqa: SIM118
                self[key] = other[key]

        else:
            for key, value in other:
                self[key] = value

        for key, value in kwargs.items():
            self[key] = value


std_headers = HTTPHeaderDict({
    'User-Agent': random_user_agent(),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
})


def clean_proxies(proxies: dict, headers: HTTPHeaderDict):
    req_proxy = headers.pop('Ytdl-Request-Proxy', None)
    if req_proxy:
        proxies.clear()  # XXX: compat: Ytdl-Request-Proxy takes preference over everything, including NO_PROXY
        proxies['all'] = req_proxy
    for proxy_key, proxy_url in proxies.items():
        if proxy_url == '__noproxy__':
            proxies[proxy_key] = None
            continue
        if proxy_key == 'no':  # special case
            continue
        if proxy_url is not None:
            # Ensure proxies without a scheme are http.
            try:
                proxy_scheme = urllib.request._parse_proxy(proxy_url)[0]
            except ValueError:
                # Ignore invalid proxy URLs. Sometimes these may be introduced through environment
                # variables unrelated to proxy settings - e.g. Colab `COLAB_LANGUAGE_SERVER_PROXY`.
                # If the proxy is going to be used, the Request Handler proxy validation will handle it.
                continue
            if proxy_scheme is None:
                proxies[proxy_key] = 'http://' + remove_start(proxy_url, '//')

            replace_scheme = {
                'socks5': 'socks5h',  # compat: socks5 was treated as socks5h
                'socks': 'socks4',  # compat: non-standard
            }
            if proxy_scheme in replace_scheme:
                proxies[proxy_key] = urllib.parse.urlunparse(
                    urllib.parse.urlparse(proxy_url)._replace(scheme=replace_scheme[proxy_scheme]))


def clean_headers(headers: HTTPHeaderDict):
    if 'Youtubedl-No-Compression' in headers:  # compat
        del headers['Youtubedl-No-Compression']
        headers['Accept-Encoding'] = 'identity'
    headers.pop('Ytdl-socks-proxy', None)


def remove_dot_segments(path):
    # Implements RFC3986 5.2.4 remote_dot_segments
    # Pseudo-code: https://tools.ietf.org/html/rfc3986#section-5.2.4
    # https://github.com/urllib3/urllib3/blob/ba49f5c4e19e6bca6827282feb77a3c9f937e64b/src/urllib3/util/url.py#L263
    output = []
    segments = path.split('/')
    for s in segments:
        if s == '.':
            continue
        elif s == '..':
            if output:
                output.pop()
        else:
            output.append(s)
    if not segments[0] and (not output or output[0]):
        output.insert(0, '')
    if segments[-1] in ('.', '..'):
        output.append('')
    return '/'.join(output)


def escape_rfc3986(s):
    """Escape non-ASCII characters as suggested by RFC 3986"""
    return urllib.parse.quote(s, b"%/;:@&=+$,!~*'()?#[]")


def normalize_url(url):
    """Normalize URL as suggested by RFC 3986"""
    url_parsed = urllib.parse.urlparse(url)
    return url_parsed._replace(
        netloc=url_parsed.netloc.encode('idna').decode('ascii'),
        path=escape_rfc3986(remove_dot_segments(url_parsed.path)),
        params=escape_rfc3986(url_parsed.params),
        query=escape_rfc3986(url_parsed.query),
        fragment=escape_rfc3986(url_parsed.fragment),
    ).geturl()


def select_proxy(url, proxies):
    """Unified proxy selector for all backends"""
    url_components = urllib.parse.urlparse(url)
    if 'no' in proxies:
        hostport = url_components.hostname + format_field(url_components.port, None, ':%s')
        if urllib.request.proxy_bypass_environment(hostport, {'no': proxies['no']}):
            return
        elif urllib.request.proxy_bypass(hostport):  # check system settings
            return

    return traverse_obj(proxies, url_components.scheme or 'http', 'all')

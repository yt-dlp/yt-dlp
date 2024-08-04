import collections
import random
import urllib.parse
import urllib.request

from ._utils import remove_start


def random_user_agent():
    _USER_AGENT_TPL = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36'
    _CHROME_VERSIONS = (
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
        '97.0.4692.71',
        '97.0.4692.99',
        '98.0.4758.80',
        '98.0.4758.102',
        '99.0.4844.51',
        '99.0.4844.74',
        '99.0.4844.82',
        '99.0.4844.84',
        '100.0.4896.60',
        '100.0.4896.75',
        '100.0.4896.88',
        '100.0.4896.127',
        '101.0.0.0',
        '102.0.0.0',
        '103.0.0.0',
        '104.0.0.0',
        '105.0.0.0',
        '106.0.0.0',
        '107.0.0.0',
        '108.0.0.0',
        '109.0.0.0',
        '110.0.0.0',
        '111.0.0.0',
        '112.0.0.0',
        '113.0.0.0',
        '114.0.0.0',
        '115.0.0.0',
        '116.0.0.0',
    )
    return _USER_AGENT_TPL % random.choice(_CHROME_VERSIONS)


class HTTPHeaderDict(collections.UserDict, dict):
    """
    Store and access keys case-insensitively.
    The constructor can take multiple dicts, in which keys in the latter are prioritised.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        for dct in args:
            if dct is not None:
                self.update(dct)
        self.update(kwargs)

    def __setitem__(self, key, value):
        if isinstance(value, bytes):
            value = value.decode('latin-1')
        super().__setitem__(key.title(), str(value).strip())

    def __getitem__(self, key):
        return super().__getitem__(key.title())

    def __delitem__(self, key):
        super().__delitem__(key.title())

    def __contains__(self, key):
        return super().__contains__(key.title() if isinstance(key, str) else key)


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

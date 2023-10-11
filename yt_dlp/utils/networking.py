import collections
import random
import urllib.parse
import urllib.request

from ._utils import remove_start


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
        super().__setitem__(key.title(), str(value))

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
                'socks': 'socks4'  # compat: non-standard
            }
            if proxy_scheme in replace_scheme:
                proxies[proxy_key] = urllib.parse.urlunparse(
                    urllib.parse.urlparse(proxy_url)._replace(scheme=replace_scheme[proxy_scheme]))


def clean_headers(headers: HTTPHeaderDict):
    if 'Youtubedl-No-Compression' in headers:  # compat
        del headers['Youtubedl-No-Compression']
        headers['Accept-Encoding'] = 'identity'


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
        fragment=escape_rfc3986(url_parsed.fragment)
    ).geturl()

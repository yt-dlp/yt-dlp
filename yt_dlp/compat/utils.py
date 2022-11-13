from .compat_utils import passthrough_module

passthrough_module(__name__, 'utils')
del passthrough_module

from ..dependencies import certifi, websockets
import urllib.request
import urllib.parse


def YoutubeDLCookieJar(*args, **kwargs):
    from ..cookies import YoutubeDLCookieJar
    return YoutubeDLCookieJar(*args, **kwargs)


def PUTRequest(*args, **kwargs):
    from ..networking._urllib import PUTRequest
    return PUTRequest(*args, **kwargs)


def HEADRequest(url, *args, **kwargs):
    from ..networking._urllib import HEADRequest
    return HEADRequest(url, *args, **kwargs)


def update_Request(*args, **kwargs):
    from ..networking._urllib import update_Request
    return update_Request(*args, **kwargs)


def request_to_url(req):
    if isinstance(req, urllib.request.Request):
        return req.get_full_url()
    else:
        return req


def handle_youtubedl_headers(headers):
    filtered_headers = headers

    if 'Youtubedl-no-compression' in filtered_headers:
        filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'accept-encoding'}
        del filtered_headers['Youtubedl-no-compression']

    return filtered_headers


def random_user_agent():
    from ..networking.utils import random_user_agent
    return random_user_agent()


# TODO: compat (doesn't exist)
SUPPORTED_ENCODINGS = []

# TODO: compat (moved to networking.utils)
std_headers = {}


def sanitized_Request(url, *args, **kwargs):
    from ..utils import extract_basic_auth, escape_url, sanitize_url
    url, auth_header = extract_basic_auth(escape_url(sanitize_url(url)))
    if auth_header is not None:
        headers = args[1] if len(args) >= 2 else kwargs.setdefault('headers', {})
        headers['Authorization'] = auth_header
    return urllib.request.Request(url, *args, **kwargs)


has_certifi = bool(certifi)
has_websockets = bool(websockets)

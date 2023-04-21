from .compat_utils import passthrough_module
from ..dependencies import certifi, websockets

passthrough_module(__name__, 'utils')
del passthrough_module


def handle_youtubedl_headers(headers):
    filtered_headers = headers

    if 'Youtubedl-no-compression' in filtered_headers:
        filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'accept-encoding'}
        del filtered_headers['Youtubedl-no-compression']

    return filtered_headers


has_certifi = bool(certifi)
has_websockets = bool(websockets)


def load_plugins(name, suffix, namespace):
    from ..plugins import load_plugins
    ret = load_plugins(name, suffix)
    namespace.update(ret)
    return ret

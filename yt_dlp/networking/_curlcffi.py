from .common import RequestHandler, Request, Response, register
from .director import Preference, register_preference

from ..dependencies import curl_cffi

if curl_cffi is None:
    raise ImportError('curl_cffi is not installed')


@register
class CurlCFFIRH(RequestHandler):
    RH_NAME = 'curl-impersonate (curl_cffi)'

    def _send(self, request: Request):
        pass


@register_preference
class CurlCFFIPrefernce(Preference):
    RH_KEY = CurlCFFIRH.RH_KEY

    def _get_preference(self, request: Request, handler: RequestHandler) -> int:
        if not request.extensions.get('impersonate'):
            return -1000
        else:
            return 1000

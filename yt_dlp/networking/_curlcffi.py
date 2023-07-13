from .common import RequestHandler, Request, Response, register

from ..dependencies import curl_cffi

if curl_cffi is None:
    raise ImportError('curl_cffi is not installed')


@register
class CurlCFFIRH(RequestHandler):
    RH_NAME = 'curl-impersonate (cffi)'

    def _send(self, request: Request):
        pass


import abc

from .common import Response, RequestHandler
from .exceptions import TransportError


class WebSocketResponse(Response):

    def send(self, *args):
        raise NotImplementedError

    def recv(self, *args):
        raise NotImplementedError


class WebSocketException(TransportError):
    pass


class WebSocketRequestHandler(RequestHandler, abc.ABC):
    pass

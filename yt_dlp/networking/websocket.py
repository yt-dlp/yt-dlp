import abc

from .common import Response, RequestHandler


class WebSocketResponse(Response):

    def send(self, *args):
        raise NotImplementedError

    def recv(self, *args):
        raise NotImplementedError


class WebSocketRequestHandler(RequestHandler, abc.ABC):
    pass

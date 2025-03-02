from __future__ import annotations

import abc
import urllib.parse

from .common import RequestHandler, Response, register_preference


class WebSocketResponse(Response):

    def send(self, message: bytes | str):
        """
        Send a message to the server.

        @param message: The message to send. A string (str) is sent as a text frame, bytes is sent as a binary frame.
        """
        raise NotImplementedError

    def recv(self):
        raise NotImplementedError


class WebSocketRequestHandler(RequestHandler, abc.ABC):
    pass


@register_preference(WebSocketRequestHandler)
def websocket_preference(_, request):
    if urllib.parse.urlparse(request.url).scheme in ('ws', 'wss'):
        return 200
    return 0

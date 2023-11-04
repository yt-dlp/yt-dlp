from __future__ import annotations

import abc

from .common import Response, RequestHandler


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

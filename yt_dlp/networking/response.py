import io
import warnings
from email.message import Message
from http import HTTPStatus
from typing import Mapping


class Response(io.IOBase):
    """
    Abstract base class for HTTP response adapters.

    Interface partially backwards-compatible with addinfourl and http.client.HTTPResponse.

    @param raw: Original response.
    @param url: URL that this is a response of.
    @param headers: response headers.
    @param status: Response HTTP status code. Default is 200 OK.
    @param reason: HTTP status reason. Will use built-in reasons based on status code if not provided.
    """

    def __init__(
            self, raw,
            url: str,
            headers: Mapping[str, str],
            status: int = 200,
            reason: str = None):

        self.raw = raw
        self.headers: Message = Message()
        for name, value in (headers or {}).items():
            self.headers.add_header(name, value)
        self.status = status
        self.reason = reason
        self.url = url
        if not reason:
            try:
                self.reason = HTTPStatus(status).phrase
            except ValueError:
                pass

    def readable(self):
        return True

    def read(self, amt: int = None) -> bytes:
        return self.raw.read(amt)

    def tell(self) -> int:
        return self.raw.tell()

    def close(self):
        self.raw.close()
        return super().close()

    def get_header(self, name, default=None):
        """Get header for name.
        If there are multiple matching headers, return all seperated by comma."""
        headers = self.headers.get_all(name)
        if not headers:
            return default
        if name.title() == 'Set-Cookie':
            # Special case, only get the first one
            # https://www.rfc-editor.org/rfc/rfc9110.html#section-5.3-4.1
            return headers[0]
        return ', '.join(headers)

    # The following methods are for compatability reasons and are deprecated
    @property
    def code(self):
        warnings.warn("code is deprecated, use status", DeprecationWarning, stacklevel=2)
        return self.status

    def getcode(self):
        warnings.warn("getcode() is deprecated, use status", DeprecationWarning, stacklevel=2)
        return self.status

    def geturl(self):
        warnings.warn("geturl() is deprecated, use url", DeprecationWarning, stacklevel=2)
        return self.url

    def info(self):
        warnings.warn("info() is deprecated, use headers", DeprecationWarning, stacklevel=2)
        return self.headers

    def getheader(self, name, default=None):
        warnings.warn("getheader() is deprecated, use headers", DeprecationWarning, stacklevel=2)
        return self.get_header(name, default)

"""PUBLIC API"""

from __future__ import annotations

import abc
import copy
import dataclasses
import enum
import functools
import typing
import urllib.parse

from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.extractor.youtube.pot._provider import (
    IEContentProvider,
    IEContentProviderError,
    register_preference_generic,
    register_provider_generic,
)
from yt_dlp.extractor.youtube.pot._registry import _pot_providers, _ptp_preferences
from yt_dlp.networking import Request, Response
from yt_dlp.utils import traverse_obj
from yt_dlp.utils.networking import HTTPHeaderDict

__all__ = [
    'ExternalRequestFeature',
    'PoTokenContext',
    'PoTokenProvider',
    'PoTokenProviderError',
    'PoTokenProviderRejectedRequest',
    'PoTokenRequest',
    'PoTokenResponse',
    'provider_bug_report_message',
    'register_preference',
    'register_provider',
]


class PoTokenContext(enum.Enum):
    GVS = 'gvs'
    PLAYER = 'player'


@dataclasses.dataclass
class PoTokenRequest:
    # YouTube parameters
    context: PoTokenContext
    innertube_context: InnertubeContext
    innertube_host: str | None = None
    session_index: str | None = None
    player_url: str | None = None
    is_authenticated: bool = False
    video_webpage: str | None = None
    internal_client_name: str | None = None

    # Content binding parameters
    visitor_data: str | None = None
    data_sync_id: str | None = None
    video_id: str | None = None

    # Networking parameters
    request_cookiejar: YoutubeDLCookieJar = dataclasses.field(default_factory=YoutubeDLCookieJar)
    request_proxy: str | None = None
    request_headers: HTTPHeaderDict = dataclasses.field(default_factory=HTTPHeaderDict)
    request_timeout: float | None = None
    request_source_address: str | None = None
    request_verify_tls: bool = True

    # Generate a new token, do not used a cached token
    # The token should still be cached for future requests
    bypass_cache: bool = False

    def copy(self):
        return dataclasses.replace(
            self,
            request_headers=HTTPHeaderDict(self.request_headers),
            innertube_context=copy.deepcopy(self.innertube_context),
        )


@dataclasses.dataclass
class PoTokenResponse:
    po_token: str
    expires_at: int | None = None


class PoTokenProviderRejectedRequest(IEContentProviderError):
    """Reject the PoTokenRequest (cannot handle the request)"""


class PoTokenProviderError(IEContentProviderError):
    """An error occurred while fetching a PO Token"""


class ExternalRequestFeature(enum.Enum):
    PROXY_SCHEME_HTTP = enum.auto()
    PROXY_SCHEME_HTTPS = enum.auto()
    PROXY_SCHEME_SOCKS4 = enum.auto()
    PROXY_SCHEME_SOCKS4A = enum.auto()
    PROXY_SCHEME_SOCKS5 = enum.auto()
    PROXY_SCHEME_SOCKS5H = enum.auto()
    SOURCE_ADDRESS = enum.auto()
    DISABLE_TLS_VERIFICATION = enum.auto()


class PoTokenProvider(IEContentProvider, abc.ABC, suffix='PTP'):

    # Set to None to disable the check
    _SUPPORTED_CONTEXTS: tuple[PoTokenContext] | None = ()

    # Innertube Client Name.
    # For example, "WEB", "ANDROID", "TVHTML5".
    # For a list of WebPO client names, see yt_dlp.extractor.youtube.pot.utils.WEBPO_CLIENTS.
    # Also see yt_dlp.extractor.youtube._base.INNERTUBE_CLIENTS
    #  for a list of client names currently supported by the YouTube extractor.
    _SUPPORTED_CLIENTS: tuple[str] | None = ()

    # If making external requests to websites (i.e. to youtube.com)
    #  using another library or service (i.e., not _request_webpage),
    #  add the request features that are supported.
    # If only using _request_webpage to make external requests, set this to None.
    _SUPPORTED_EXTERNAL_REQUEST_FEATURES: tuple[ExternalRequestFeature] | None = ()

    def __validate_request(self, request: PoTokenRequest):
        if not self.is_available():
            raise PoTokenProviderRejectedRequest(f'{self.PROVIDER_NAME} is not available')

        # Validate request using built-in settings
        if (
            self._SUPPORTED_CONTEXTS is not None
            and request.context not in self._SUPPORTED_CONTEXTS
        ):
            raise PoTokenProviderRejectedRequest(
                f'PO Token Context "{request.context}" is not supported by {self.PROVIDER_NAME}')

        if self._SUPPORTED_CLIENTS is not None:
            client_name = traverse_obj(
                request.innertube_context, ('client', 'clientName'))
            if client_name not in self._SUPPORTED_CLIENTS:
                raise PoTokenProviderRejectedRequest(
                    f'Client "{client_name}" is not supported by {self.PROVIDER_NAME}. '
                    f'Supported clients: {", ".join(self._SUPPORTED_CLIENTS) or "none"}')

        self.__validate_external_request_features(request)

    @functools.cached_property
    def _supported_proxy_schemes(self):
        return {
            scheme: feature
            for scheme, feature in {
                'http': ExternalRequestFeature.PROXY_SCHEME_HTTP,
                'https': ExternalRequestFeature.PROXY_SCHEME_HTTPS,
                'socks4': ExternalRequestFeature.PROXY_SCHEME_SOCKS4,
                'socks4a': ExternalRequestFeature.PROXY_SCHEME_SOCKS4A,
                'socks5': ExternalRequestFeature.PROXY_SCHEME_SOCKS5,
                'socks5h': ExternalRequestFeature.PROXY_SCHEME_SOCKS5H,
            }.items()
            if feature in (self._SUPPORTED_EXTERNAL_REQUEST_FEATURES or [])
        }

    def __validate_external_request_features(self, request: PoTokenRequest):
        if self._SUPPORTED_EXTERNAL_REQUEST_FEATURES is None:
            return

        if request.request_proxy:
            scheme = urllib.parse.urlparse(request.request_proxy).scheme
            if scheme.lower() not in self._supported_proxy_schemes:
                raise PoTokenProviderRejectedRequest(
                    f'External requests by "{self.PROVIDER_NAME}" provider do not '
                    f'support proxy scheme "{scheme}". Supported proxy schemes: '
                    f'{", ".join(self._supported_proxy_schemes) or "none"}')

        if (
            request.request_source_address
            and ExternalRequestFeature.SOURCE_ADDRESS not in self._SUPPORTED_EXTERNAL_REQUEST_FEATURES
        ):
            raise PoTokenProviderRejectedRequest(
                f'External requests by "{self.PROVIDER_NAME}" provider '
                f'do not support setting source address')

        if (
            not request.request_verify_tls
            and ExternalRequestFeature.DISABLE_TLS_VERIFICATION not in self._SUPPORTED_EXTERNAL_REQUEST_FEATURES
        ):
            raise PoTokenProviderRejectedRequest(
                f'External requests by "{self.PROVIDER_NAME}" provider '
                f'do not support ignoring TLS certificate failures')

    def request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        self.__validate_request(request)
        return self._real_request_pot(request)

    @abc.abstractmethod
    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        """To be implemented by subclasses"""
        pass

    # Helper functions

    def _request_webpage(self, request: Request, pot_request: PoTokenRequest | None = None, note=None, **kwargs) -> Response:
        """Make a request using the internal HTTP Client.
        Use this instead of calling requests, urllib3 or other HTTP client libraries directly!

        YouTube cookies will be automatically applied if this request is made to YouTube.

        @param request: The request to make
        @param pot_request: The PoTokenRequest to use. Request parameters will be merged from it.
        @param note: Custom log message to display when making the request. Set to `False` to disable logging.

        Tips:
        - Disable proxy (e.g. if calling local service): Request(..., proxies={'all': None})
        - Set request timeout:  Request(..., extensions={'timeout': 5.0})
        """
        req = request.copy()

        # Merge some ctx request settings into the request
        # Most of these will already be used by the configured ydl instance,
        # however, the YouTube extractor may override some.
        if pot_request is not None:
            req.headers = HTTPHeaderDict(pot_request.request_headers, req.headers)
            req.proxies = req.proxies or ({'all': pot_request.request_proxy} if pot_request.request_proxy else {})

            if pot_request.request_cookiejar is not None:
                req.extensions['cookiejar'] = req.extensions.get('cookiejar', pot_request.request_cookiejar)

        if note is not False:
            self.logger.info(str(note) if note else 'Requesting webpage')
        return self.ie._downloader.urlopen(req)


def register_provider(provider: type[PoTokenProvider]):
    """Register a PoTokenProvider class"""
    return register_provider_generic(
        provider=provider,
        base_class=PoTokenProvider,
        registry=_pot_providers.value,
    )


def provider_bug_report_message(provider: IEContentProvider, before=';'):
    msg = provider.BUG_REPORT_MESSAGE

    before = before.rstrip()
    if not before or before.endswith(('.', '!', '?')):
        msg = msg[0].title() + msg[1:]

    return f'{before} {msg}' if before else msg


def register_preference(*providers: type[PoTokenProvider]) -> typing.Callable[[Preference], Preference]:
    """Register a preference for a PoTokenProvider"""
    return register_preference_generic(
        PoTokenProvider,
        _ptp_preferences.value,
        *providers,
    )


if typing.TYPE_CHECKING:
    Preference = typing.Callable[[PoTokenProvider, PoTokenRequest], int]
    __all__.append('Preference')

    # Barebones innertube context. There may be more fields.
    class ClientInfo(typing.TypedDict, total=False):
        hl: str | None
        gl: str | None
        remoteHost: str | None
        deviceMake: str | None
        deviceModel: str | None
        visitorData: str | None
        userAgent: str | None
        clientName: str
        clientVersion: str
        osName: str | None
        osVersion: str | None

    class InnertubeContext(typing.TypedDict, total=False):
        client: ClientInfo
        request: dict
        user: dict

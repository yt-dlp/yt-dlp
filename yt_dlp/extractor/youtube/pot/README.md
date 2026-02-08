# YoutubeIE PO Token Provider Framework

As part of the YouTube extractor, we have a framework for providing PO Tokens programmatically. This can be used by plugins.

Refer to the [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) for more information on PO Tokens.

> [!TIP]
> If publishing a PO Token Provider plugin to GitHub, add the [yt-dlp-pot-provider](https://github.com/topics/yt-dlp-pot-provider) topic to your repository to help users find it.


## Public APIs

- `yt_dlp.extractor.youtube.pot.cache`
- `yt_dlp.extractor.youtube.pot.provider`
- `yt_dlp.extractor.youtube.pot.utils`

Everything else is internal-only and no guarantees are made about the API stability.

> [!WARNING]
> We will try our best to maintain stability with the public APIs.
> However, due to the nature of extractors and YouTube, we may need to remove or change APIs in the future.
> If you are using these APIs outside yt-dlp plugins, please account for this by importing them safely.

## PO Token Provider

`yt_dlp.extractor.youtube.pot.provider`

```python
from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenRequest,
    PoTokenContext,
    PoTokenProvider,
    PoTokenResponse,
    PoTokenProviderError,
    PoTokenProviderRejectedRequest,
    register_provider,
    register_preference,
    ExternalRequestFeature,
)
from yt_dlp.networking.common import Request
from yt_dlp.extractor.youtube.pot.utils import get_webpo_content_binding
from yt_dlp.utils import traverse_obj
from yt_dlp.networking.exceptions import RequestError
import json


@register_provider
class MyPoTokenProviderPTP(PoTokenProvider):  # Provider class name must end with "PTP"
    PROVIDER_VERSION = '0.2.1'
    # Define a unique display name for the provider
    PROVIDER_NAME = 'my-provider'
    BUG_REPORT_LOCATION = 'https://issues.example.com/report'

    # -- Validation shortcuts. Set these to None to disable. --

    # Innertube Client Name.
    # For example, "WEB", "ANDROID", "TVHTML5".
    # For a list of WebPO client names, 
    #  see yt_dlp.extractor.youtube.pot.utils.WEBPO_CLIENTS.
    # Also see yt_dlp.extractor.youtube._base.INNERTUBE_CLIENTS 
    #  for a list of client names currently supported by the YouTube extractor.
    _SUPPORTED_CLIENTS = ('WEB', 'TVHTML5')

    _SUPPORTED_CONTEXTS = (
        PoTokenContext.GVS,
    )

    # If your provider makes external requests to websites (i.e. to youtube.com) 
    #  using another library or service (i.e., not _request_webpage),
    # set the request features that are supported here.
    # If only using _request_webpage to make external requests, set this to None.
    _SUPPORTED_EXTERNAL_REQUEST_FEATURES = (
        ExternalRequestFeature.PROXY_SCHEME_HTTP, 
        ExternalRequestFeature.SOURCE_ADDRESS, 
        ExternalRequestFeature.DISABLE_TLS_VERIFICATION
    )

    def is_available(self) -> bool:
        """
        Check if the provider is available (e.g. all required dependencies are available)
        This is used to determine if the provider should be used and to provide debug information.

        IMPORTANT: This method SHOULD NOT make any network requests or perform any expensive operations.

        Since this is called multiple times, we recommend caching the result.
        """
        return True

    def close(self):
        # Optional close hook, called when YoutubeDL is closed.
        pass

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        # ℹ️ If you need to validate the request before making the request to the external source.
        # Raise yt_dlp.extractor.youtube.pot.provider.PoTokenProviderRejectedRequest if the request is not supported.
        if request.is_authenticated:
            raise PoTokenProviderRejectedRequest(
                'This provider does not support authenticated requests'
            )

        # ℹ️ Settings are pulled from extractor args passed to yt-dlp with the key `youtubepot-<PROVIDER_KEY>`.
        # For this example, the extractor arg would be:
        # `--extractor-args "youtubepot-mypotokenprovider:url=https://custom.example.com/get_pot"`
        external_provider_url = self._configuration_arg(
            'url', default=['https://provider.example.com/get_pot'])[0]
        
        # See below for logging guidelines
        self.logger.trace(f'Using external provider URL: {external_provider_url}')
        
        # You should use the internal HTTP client to make requests where possible,
        # as it will handle cookies and other networking settings passed to yt-dlp.
        try:
            # See docstring in _request_webpage method for request tips
            response = self._request_webpage(
                Request(external_provider_url, data=json.dumps({
                    'content_binding': get_webpo_content_binding(request),
                    'proxy': request.request_proxy,
                    'headers': request.request_headers,
                    'source_address': request.request_source_address,
                    'verify_tls': request.request_verify_tls,
                    # Important: If your provider has its own caching, please respect `bypass_cache`.
                    # This may be used in the future to request a fresh PO Token if required.
                    'do_not_cache': request.bypass_cache,
                }).encode(), proxies={'all': None}), 
                pot_request=request, 
                note=(
                  f'Requesting {request.context.value} PO Token '
                  f'for {request.internal_client_name} client from external provider'),
            )

        except RequestError as e:
            # ℹ️ If there is an error, raise PoTokenProviderError.
            # You can specify whether it is expected or not. If it is unexpected, 
            #  the log will include a link to the bug report location (BUG_REPORT_LOCATION).
            raise PoTokenProviderError(
                'Networking error while fetching to get PO Token from external provider',
                expected=True
            ) from e

        # Note: PO Token is expected to be base64url encoded
        po_token = traverse_obj(response, 'po_token')
        if not po_token:
            raise PoTokenProviderError(
                'Bad PO Token Response from external provider',
                expected=False
            )

        return PoTokenResponse(
            po_token=po_token,
            # Optional, add a custom expiration timestamp for the token. Use for caching.
            # By default, yt-dlp will use the default ttl from a registered cache spec (see below)
            # Set to 0 or -1 to not cache this response.
            expires_at=None,
        )


# If there are multiple PO Token Providers that can handle the same PoTokenRequest,
# you can define a preference function to increase/decrease the priority of providers.

@register_preference(MyPoTokenProviderPTP)
def my_provider_preference(provider: PoTokenProvider, request: PoTokenRequest) -> int:
    return 50
```

## Logging Guidelines

- Use the `self.logger` object to log messages.
- When making HTTP requests or any other expensive operation, use `self.logger.info` to log a message to standard non-verbose output.
  - This lets users know what is happening when a time-expensive operation is taking place.
  - It is recommended to include the PO Token context and internal client name in the message if possible.
  - For example, `self.logger.info(f'Requesting {request.context.value} PO Token for {request.internal_client_name} client from external provider')`.
- Use `self.logger.debug` to log a message to the verbose output (`--verbose`).
  - For debugging information visible to users posting verbose logs.
  - Try to not log too much, prefer using trace logging for detailed debug messages.
- Use `self.logger.trace` to log a message to the PO Token debug output (`--extractor-args "youtube:pot_trace=true"`). 
  - Log as much as you like here as needed for debugging your provider.
- Avoid logging PO Tokens or any sensitive information to debug or info output.

## Debugging

- Use `-v --extractor-args "youtube:pot_trace=true"` to enable PO Token debug output.

## Caching

> [!WARNING]
> The following describes more advance features that most users/developers will not need to use.

> [!IMPORTANT]
> yt-dlp currently has a built-in LRU Memory Cache Provider and a cache spec provider for WebPO Tokens. 
> You should only need to implement cache providers if you want an external cache, or a cache spec if you are handling non-WebPO Tokens.

### Cache Providers

`yt_dlp.extractor.youtube.pot.cache`

```python
from yt_dlp.extractor.youtube.pot.cache import (
    PoTokenCacheProvider,
    register_preference,
    register_provider
)

from yt_dlp.extractor.youtube.pot.provider import PoTokenRequest


@register_provider
class MyCacheProviderPCP(PoTokenCacheProvider):  # Provider class name must end with "PCP"
    PROVIDER_VERSION = '0.1.0'
    # Define a unique display name for the provider
    PROVIDER_NAME = 'my-cache-provider'
    BUG_REPORT_LOCATION = 'https://issues.example.com/report'

    def is_available(self) -> bool:
        """
        Check if the provider is available (e.g. all required dependencies are available)
        This is used to determine if the provider should be used and to provide debug information.

        IMPORTANT: This method SHOULD NOT make any network requests or perform any expensive operations.

        Since this is called multiple times, we recommend caching the result.
        """
        return True

    def get(self, key: str):
        # ℹ️ Similar to PO Token Providers, Cache Providers and Cache Spec Providers 
        # are passed down extractor args matching key youtubepot-<PROVIDER_KEY>.
        some_setting = self._configuration_arg('some_setting', default=['default_value'])[0]
        return self.my_cache.get(key)

    def store(self, key: str, value: str, expires_at: int):
        # ⚠ expires_at MUST be respected. 
        # Cache entries should not be returned if they have expired.
        self.my_cache.store(key, value, expires_at)

    def delete(self, key: str):
        self.my_cache.delete(key)

    def close(self):
        # Optional close hook, called when the YoutubeDL instance is closed.
        pass

# If there are multiple PO Token Cache Providers available, you can 
# define a preference function to increase/decrease the priority of providers. 

# IMPORTANT: Providers should be in preference of cache lookup time. 
# For example, a memory cache should have a higher preference than a disk cache. 

# VERY IMPORTANT: yt-dlp has a built-in memory cache with a priority of 10000. 
# Your cache provider should be lower than this.


@register_preference(MyCacheProviderPCP)
def my_cache_preference(provider: PoTokenCacheProvider, request: PoTokenRequest) -> int:
    return 50
```

### Cache Specs

`yt_dlp.extractor.youtube.pot.cache`

These are used to provide information on how to cache a particular PO Token Request. 
You might have a different cache spec for different kinds of PO Tokens.

```python
from yt_dlp.extractor.youtube.pot.cache import (
    PoTokenCacheSpec,
    PoTokenCacheSpecProvider,
    CacheProviderWritePolicy,
    register_spec,
)
from yt_dlp.utils import traverse_obj
from yt_dlp.extractor.youtube.pot.provider import PoTokenRequest


@register_spec
class MyCacheSpecProviderPCSP(PoTokenCacheSpecProvider):  # Provider class name must end with "PCSP"
    PROVIDER_VERSION = '0.1.0'
    # Define a unique display name for the provider
    PROVIDER_NAME = 'mycachespec'
    BUG_REPORT_LOCATION = 'https://issues.example.com/report'

    def generate_cache_spec(self, request: PoTokenRequest):

        client_name = traverse_obj(request.innertube_context, ('client', 'clientName'))
        if client_name != 'ANDROID':
            # ℹ️ If the request is not supported by the cache spec, return None
            return None

        # Generate a cache spec for the request
        return PoTokenCacheSpec(
            # Key bindings to uniquely identify the request. These are used to generate a cache key.
            key_bindings={
                'client_name': client_name,
                'content_binding': 'unique_content_binding',
                'ip': traverse_obj(request.innertube_context, ('client', 'remoteHost')),
                'source_address': request.request_source_address,
                'proxy': request.request_proxy,
            },
            # Default Cache TTL in seconds
            default_ttl=21600,

            # Optional: Specify a write policy.
            # WRITE_FIRST will write to the highest priority provider only, 
            #  whereas WRITE_ALL will write to all providers.
            # WRITE_FIRST may be useful if the PO Token is short-lived 
            #  and there is no use writing to all providers.
            write_policy=CacheProviderWritePolicy.WRITE_ALL,
        )
```
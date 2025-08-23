# YoutubeIE JS Challenge Provider Framework

As part of the YouTube extractor, we have a framework for solving JS Challenges programmatically (sig, nsig). This can be used by plugins.

> [!TIP]
> If publishing a JS Challenge Provider plugin to GitHub, add the [yt-dlp-jsc-provider](https://github.com/topics/yt-dlp-pot-provider) topic to your repository to help users find it.


## Public APIs

- `yt_dlp.extractor.youtube.js.provider`
- `yt_dlp.extractor.youtube.js.utils`

Everything else is internal-only and no guarantees are made about the API stability.

> [!WARNING]
> We will try our best to maintain stability with the public APIs.
> However, due to the nature of extractors and YouTube, we may need to remove or change APIs in the future.
> If you are using these APIs outside yt-dlp plugins, please account for this by importing them safely.

## JS Challenge Provider

`yt_dlp.extractor.youtube.js.provider`

```python
from yt_dlp.extractor.youtube.js.provider import (
    register_provider,
    register_preference,
    JsChallengeProvider,
    JsChallengeRequest,
    JsChallengeResponse,
    JsChallengeProviderError,
    JsChallengeProviderRejectedRequest,
    JsChallengeType, 
    JsChallengeProviderResponse,
)
from yt_dlp.networking.common import Request
from yt_dlp.utils import traverse_obj, Popen
from yt_dlp.networking.exceptions import RequestError
import json
import subprocess


@register_provider
class MyJsChallengeProviderJSP(JsChallengeProvider):  # Provider class name must end with "JSP"
    PROVIDER_VERSION = '0.2.1'
    # Define a unique display name for the provider
    PROVIDER_NAME = 'my-provider'
    BUG_REPORT_LOCATION = 'https://issues.example.com/report'
    
    # Set supported challenge types.
    # If None, the provider will handle all types.
    _SUPPORTED_TYPES = (JsChallengeType.NSIG,)

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

    def _real_solve(self, request: JsChallengeRequest) -> JsChallengeResponse:
        # ℹ️ If you need to validate the request before making the request to the external source.
        # Raise yt_dlp.extractor.youtube.js.provider.JsChallengeProviderRejectedRequest if the request is not supported.
        if len(request.challenge) > 255:
            raise JsChallengeProviderRejectedRequest('Challenges longer than 255 are not supported', expected=True)
            

        # ℹ️ Settings are pulled from extractor args passed to yt-dlp with the key `youtubejs-<PROVIDER_KEY>`.
        # For this example, the extractor arg would be:
        # `--extractor-args "youtubejs-myjschallengeprovider:bin_path=/path/to/bin"`
        bin_path = self._configuration_arg(
            'bin_path', default=['/path/to/bin'])[0]
        
        # See below for logging guidelines
        self.logger.trace(f'Using bin path: {bin_path}')
        
        # You can use the _get_player method to get the player JS code if needed.
        # This shares the same caching as the YouTube extractor, so it will not make unnecessary requests.
        player_js = self._get_player(request.video_id, request.player_url)
        
        cmd = f'{bin_path} {request.challenge} {player_js}'
        self.logger.info(f'Executing command: {cmd}')
        stdout, _, ret = Popen.run(cmd, text=True, shell=True, stdout=subprocess.PIPE)
        if ret != 0:
            # ℹ️ If there is an error, raise JsChallengeProviderError.
            # You can specify whether it is expected or not. If it is unexpected, 
            #  the log will include a link to the bug report location (BUG_REPORT_LOCATION).
            raise JsChallengeProviderError(f'Command returned error code {ret}', expected=False)

        return JsChallengeResponse(challenge_result=stdout)
        
    # def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> list[JsChallengeProviderResponse]:
        # Optional bulk solve method, called when multiple requests are made at once.
        # This is useful for providers that can handle multiple requests at once.
        
        # IMPORTANT: This method should NOT raise any errors. 
        # The method should return a list of JsChallengeProviderResponse objects for every request. 
        # In case of an error, return a JsChallengeProviderResponse with the error set.


# If there are multiple JS Challenge Providers that can handle the same JsChallengeRequest(s),
# you can define a preference function to increase/decrease the priority of providers.

@register_preference(MyJsChallengeProviderJSP)
def my_provider_preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 50
```

## Logging Guidelines

todo

## Debugging

- Use `-v --extractor-args "youtube:js_trace=true"` to enable JS Challenge debug output.

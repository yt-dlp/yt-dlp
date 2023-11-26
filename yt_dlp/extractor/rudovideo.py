from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class RudoVideoIE(InfoExtractor):
    _VALID_URL = r'https?://rudo\.video/live/(?P<id>[^/]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if "Streaming is not available in your area." in webpage:
            self.raise_geo_restricted()

        stream_url = self._search_regex(r'var\s+streamURL\s*=\s*\'([^?\']+)', webpage, "streamUrl")
        token_array_string = self._search_regex(r'<script>var\s+_\$_[a-zA-Z0-9]+\s*=\s*(\[[^]]+\])', webpage, 'token_array', default=None)
        if token_array_string:
            token_array_string = token_array_string.replace("x", "u00")
            token_array = self._parse_json(token_array_string, video_id)
            if len(token_array) != 9:
                raise ExtractorError('Couldnt get access token array', video_id=video_id)
            access_token_webpage = self._download_webpage(token_array[0], video_id)
            access_token = self._parse_json(access_token_webpage, video_id)
            if "data" not in access_token or token_array[3] not in access_token.get("data"):
                raise ExtractorError('Couldnt get access token', video_id=video_id)
            query_string = token_array[5] + traverse_obj(access_token, ("data", token_array[3]))
            stream_url = f'{stream_url}{query_string}'

        return self.url_result(
            stream_url,
            display_id=video_id, url_transparent=True)

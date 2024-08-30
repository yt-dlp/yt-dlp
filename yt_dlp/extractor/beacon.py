import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_iso8601,
    traverse_obj,
)


class BeaconTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?beacon\.tv/content/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://beacon.tv/content/welcome-to-beacon',
        'md5': 'b3f5932d437f288e662f10f3bfc5bd04',
        'info_dict': {
            'id': 'welcome-to-beacon',
            'ext': 'mp4',
            'upload_date': '20240509',
            'description': 'md5:ea2bd32e71acf3f9fca6937412cc3563',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/I4CkkEvN/poster.jpg?width=720',
            'title': 'Your home for Critical Role!',
            'timestamp': 1715227200,
            'duration': 105.494,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        state = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['__APOLLO_STATE__']

        content_data = traverse_obj(state, (lambda k, v: k.startswith('Content:') and v['slug'] == video_id, any))

        if not content_data or not content_data.get('contentVideo'):
            raise ExtractorError(
                'Failed to extract video. Either the given content is not a video, or it requires authentication', expected=True)

        return {
            **self._parse_jwplayer_data(traverse_obj(
                content_data, ('contentVideo', 'video', 'videoData', {json.loads})), video_id),
            **traverse_obj(content_data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('publishedAt', {parse_iso8601}),
            }),
        }

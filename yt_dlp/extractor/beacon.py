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
    }, {
        'url': 'https://beacon.tv/content/re-slayers-take-trailer',
        'md5': 'd879b091485dbed2245094c8152afd89',
        'info_dict': {
            'id': 're-slayers-take-trailer',
            'ext': 'mp4',
            'title': 'The Re-Slayer’s Take | Official Trailer',
            'timestamp': 1715189040,
            'upload_date': '20240508',
            'duration': 53.249,
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/PW5ApIw3/poster.jpg?width=720',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        content_data = traverse_obj(self._search_nextjs_data(webpage, video_id), (
            'props', 'pageProps', '__APOLLO_STATE__',
            lambda k, v: k.startswith('Content:') and v['slug'] == video_id, any))
        if not content_data:
            raise ExtractorError('Failed to extract content data')

        jwplayer_data = traverse_obj(content_data, (
            (('contentVideo', 'video', 'videoData'),
             ('contentPodcast', 'podcast', 'audioData')), {json.loads}, {dict}, any))
        if not jwplayer_data:
            if content_data.get('contentType') not in ('videoPodcast', 'video', 'podcast'):
                raise ExtractorError('Content is not a video/podcast', expected=True)
            if traverse_obj(content_data, ('contentTier', '__ref')) != 'MemberTier:65b258d178f89be87b4dc0a4':
                self.raise_login_required('This video/podcast is for members only')
            raise ExtractorError('Failed to extract content')

        return {
            **self._parse_jwplayer_data(jwplayer_data, video_id),
            **traverse_obj(content_data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('publishedAt', {parse_iso8601}),
            }),
        }

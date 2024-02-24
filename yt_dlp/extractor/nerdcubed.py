from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import parse_iso8601, url_or_none
from ..utils.traversal import traverse_obj


class NerdCubedFeedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nerdcubed\.co\.uk/?(?:$|[#?])'
    _TEST = {
        'url': 'http://www.nerdcubed.co.uk/',
        'info_dict': {
            'id': 'nerdcubed-feed',
            'title': 'nerdcubed.co.uk feed',
        },
        'playlist_mincount': 5500,
    }

    def _extract_video(self, feed_entry):
        return self.url_result(
            f'https://www.youtube.com/watch?v={feed_entry["id"]}', YoutubeIE,
            **traverse_obj(feed_entry, {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('publishedAt', {parse_iso8601}),
                'channel': ('source', 'name', {str}),
                'channel_id': ('source', 'id', {str}),
                'channel_url': ('source', 'url', {str}),
                'thumbnail': ('thumbnail', 'source', {url_or_none}),
            }), url_transparent=True)

    def _real_extract(self, url):
        video_id = 'nerdcubed-feed'
        feed = self._download_json('https://www.nerdcubed.co.uk/_/cdn/videos.json', video_id)

        return self.playlist_result(
            map(self._extract_video, traverse_obj(feed, ('videos', lambda _, v: v['id']))),
            video_id, 'nerdcubed.co.uk feed')

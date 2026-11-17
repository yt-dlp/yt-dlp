import re

from .cloudflarestream import CloudflareStreamIE
from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class HytaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hytale\.com/news/\d+/\d+/(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://hytale.com/news/2021/07/summer-2021-development-update',
        'info_dict': {
            'id': 'summer-2021-development-update',
            'title': 'Summer 2021 Development Update',
        },
        'playlist_count': 4,
        'playlist': [{
            'md5': '0854ebe347d233ee19b86ab7b2ead610',
            'info_dict': {
                'id': 'ed51a2609d21bad6e14145c37c334999',
                'ext': 'mp4',
                'title': 'Avatar Personalization',
                'thumbnail': r're:https://videodelivery\.net/\w+/thumbnails/thumbnail\.jpg',
            },
        }],
    }, {
        'url': 'https://www.hytale.com/news/2019/11/hytale-graphics-update',
        'info_dict': {
            'id': 'hytale-graphics-update',
            'title': 'Hytale graphics update',
        },
        'playlist_count': 2,
    }]

    def _real_initialize(self):
        media_webpage = self._download_webpage(
            'https://hytale.com/media', None, note='Downloading list of media', fatal=False) or ''

        clips_json = traverse_obj(
            self._search_json(
                r'window\.__INITIAL_COMPONENTS_STATE__\s*=\s*\[',
                media_webpage, 'clips json', None),
            ('media', 'clips')) or []

        self._titles = {clip.get('src'): clip.get('caption') for clip in clips_json}

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        entries = [
            self.url_result(
                f'https://cloudflarestream.com/{video_hash}/manifest/video.mpd?parentOrigin=https%3A%2F%2Fhytale.com',
                CloudflareStreamIE, title=self._titles.get(video_hash), url_transparent=True)
            for video_hash in re.findall(
                r'<stream\s+class\s*=\s*"ql-video\s+cf-stream"\s+src\s*=\s*"([a-f0-9]{32})"',
                webpage)
        ]

        return self.playlist_result(entries, playlist_id, self._og_search_title(webpage))

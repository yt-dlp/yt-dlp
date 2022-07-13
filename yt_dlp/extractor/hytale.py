import re

from .common import InfoExtractor
from ..utils import traverse_obj


class HytaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hytale\.com/news/\d+/\d+/(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://hytale.com/news/2021/07/summer-2021-development-update',
        'info_dict': {
            'id': 'summer-2021-development-update',
            'title': 'Summer 2021 Development Update',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://www.hytale.com/news/2019/11/hytale-graphics-update',
        'info_dict': {
            'id': 'hytale-graphics-update',
            'title': 'Hytale graphics update',
        },
        'playlist_count': 2,
    }]

    _VIDEO_BASE_URL = 'https://cloudflarestream.com/{}/manifest/video.mpd?parentOrigin=https%3A%2F%2Fhytale.com'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)
        title = self._og_search_title(webpage)

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': title,
            'entries': [
                self.url_result(self._VIDEO_BASE_URL.format(video_hash),
                                video_title=self.videos_ids_and_titles[video_hash],
                                url_transparent=True)
                if video_hash in self.videos_ids_and_titles
                else self.url_result(self._VIDEO_BASE_URL.format(video_hash),
                                     video_title=title,
                                     url_transparent=True)
                for video_hash in re.findall(
                    r'<stream\s+class\s*=\s*"ql-video\s+cf-stream"\s+src\s*=\s*"([a-f0-9]{32})"',
                    webpage)

            ]
        }

    def _real_initialize(self):
        self.videos_ids_and_titles = {}

        media_webpage = self._download_webpage('https://hytale.com/media',
                                               'media', fatal=False)
        if media_webpage:
            clips_json = traverse_obj(
                self._search_json(
                    r'window\.__INITIAL_COMPONENTS_STATE__\s*=\s*\[',
                    media_webpage, 'clips json', 'media'),
                ('media', 'clips'))
            self.videos_ids_and_titles = {clip.get('src'): clip.get('caption') for clip in clips_json}

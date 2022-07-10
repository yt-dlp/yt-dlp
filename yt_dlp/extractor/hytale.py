from re import findall

from .common import InfoExtractor


class HytaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hytale\.com/news/20\d\d/(?:0?[1-9]|1[0-2])/(?P<id>[a-z0-9-]+)'
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

    _MD5_REGEX = r'<stream\s+class\s*=\s*"ql-video\s+cf-stream"\s+src\s*=\s*"([a-f0-9]{32})"'
    _VIDEO_BASE_URL = 'https://cloudflarestream.com/{}/manifest/video.mpd?parentOrigin=https%3A%2F%2Fhytale.com'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        entries = [self.url_result(self._VIDEO_BASE_URL.format(video_hash),
                                   video_title=f'Hytale video #{video_hash}',
                                   url_transparent=True)
                   for video_hash in findall(self._MD5_REGEX, webpage)]

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': self._og_search_title(webpage),
            'playlist_count': len(entries),
            'entries': entries,
        }

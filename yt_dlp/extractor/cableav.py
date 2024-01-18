from .common import InfoExtractor


class CableAVIE(InfoExtractor):
    _VALID_URL = r'https://cableav\.tv/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://cableav.tv/lS4iR9lWjN8/',
        'md5': '7e3fe5e49d61c4233b7f5b0f69b15e18',
        'info_dict': {
            'id': 'lS4iR9lWjN8',
            'ext': 'mp4',
            'title': '國產麻豆AV 叮叮映畫 DDF001 情欲小說家 - CableAV',
            'description': '國產AV 480p, 720p 国产麻豆AV 叮叮映画 DDF001 情欲小说家',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_url = self._og_search_video_url(webpage, secure=False)

        formats = self._extract_m3u8_formats(video_url, video_id, 'mp4')

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': formats,
        }

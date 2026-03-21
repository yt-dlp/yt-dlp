from .common import InfoExtractor
from ..utils import (
    int_or_none,
    url_or_none,
)


class RedzidzirdilatvijuIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?redzidzirdilatviju\.lv/(?P<lang>[^/]+)/search/(?:movie|video)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://redzidzirdilatviju.lv/en/search/movie/175277',
        'info_dict': {
            'id': '175277',
            'ext': 'mp4',
            'title': 'md5:placeholder',
            'thumbnail': 'https://redzidzirdilatviju.lv/placeholder.jpg',
        },
        'params': {
            'skip_download': 'manifest',
        },
    }, {
        'url': 'https://redzidzirdilatviju.lv/lv/search/movie/175277',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        webpage = self._download_webpage(url, video_id)

        # Try to find video URL in the page
        video_url = self._search_regex(
            r'(?:video_url|src|href)\s*[:=]\s*["\']([^"\']+(?:\.m3u8|\.mp4)[^"\']*)["\']',
            webpage, 'video url', default=None)

        if not video_url:
            # Try JSON-LD or other structured data
            video_url = self._search_json(
                r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>',
                webpage, 'json ld', video_id, default=None)

        thumbnail = self._search_regex(
            r'(?:poster|thumbnail|image)\s*[:=]\s*["\']([^"\']+)["\']',
            webpage, 'thumbnail', default=None)

        title = self._og_search_title(webpage, default=None) or video_id

        formats = []
        if video_url:
            if '.m3u8' in video_url:
                formats.extend(self._extract_m3u8_formats(video_url, video_id, fatal=False))
            elif video_url.startswith('http'):
                formats.append({'url': video_url})

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }

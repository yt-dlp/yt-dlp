import re
import urllib.parse

from .common import InfoExtractor
from ..utils import float_or_none, int_or_none
from ..utils.traversal import traverse_obj


class UrsulaBlickleVideoArchivIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ursulablicklevideoarchiv\.com/video/(?P<slug>[^/]+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://ursulablicklevideoarchiv.com/video/d-detroit/585d6bba5acf5d5e0f51a0ba52365979',
        'md5': '7349b78c044449dbb2a24521ec61b309',
        'info_dict': {
            'id': '585d6bba5acf5d5e0f51a0ba52365979',
            'title': 'D (Detroit) - Medien - Belvedere',
            'ext': 'mp4',
            'categories': ['Film und Video'],
            'display_id': 'd-detroit',
            'description': 'md5:13caa7306d359d1b25e992c58b9762c2',
            'duration': 982.0,
            'like_count': int,
            'release_year': 2007,
            'tags': ['Urbanität', 'Loop'],
            'thumbnail': 'https://ursulablicklevideoarchiv.com/cache/0f125e170cf6299376ebc2f91dc73d21.png',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        slug, video_id = self._match_valid_url(url).group('slug', 'id')
        webpage = self._download_webpage(url, video_id)
        options = self._search_json(r'\s+options\s*=', webpage, 'options JSON', video_id)
        language = options.get('language')
        height = traverse_obj(options, ('videojsVimpOptions', 'videoDuration', {int_or_none}))
        width = traverse_obj(options, ('videojsVimpOptions', 'videoDuration', {int_or_none}))
        poster = options.get('poster')
        category = self._html_search_regex(r'<a\s+href=["\']/category/[^"\']+["\']\s+name=["\']([^"\']+)["\']>', webpage, 'category', None)
        formats = []

        for src in options['sources']:
            if src.get('type') == 'application/x-mpegURL':
                formats.extend(self._extract_m3u8_formats(src['src'], video_id))
            else:
                ext = self._search_regex(r'video/([^/]+)', src.get('type'), 'video extension', None)
                if ext:
                    formats.append({
                        'url': src['src'],
                        'ext': ext,
                        'format_id': f'http-{ext}',
                    })
        for fmt in formats:
            fmt.setdefault('language', language)
            fmt.setdefault('width', width)
            fmt.setdefault('height', height)
        return {
            'formats': formats,
            'id': video_id,
            'display_id': slug,
            'duration': traverse_obj(options, ('videojsVimpOptions', 'videoDuration', {float_or_none})),
            'thumbnail': urllib.parse.urljoin(url, poster) if poster else None,
            'title': self._html_extract_title(webpage),
            'description': self._html_search_regex(r'<section[^>]*\s+class=["\']description["\'][^>]*>(.*?)</section>', webpage, 'description', None) or self._html_search_meta('description', webpage),
            'view_count': int_or_none(self._html_search_regex(r'>(\d+)\s+views</', webpage, 'view count', None)),
            'like_count': int_or_none(self._html_search_regex(r'>(\d+)\s+favou?rites</', webpage, 'like count', None)),
            'release_year': int_or_none(self._html_search_regex(r'<h3>Produktionsjahr</h3>\s*<span>(\d+)</span>', webpage, 'release year', None)),
            'categories': category and [category],
            'tags': re.findall(r'<button\s+class=["\']tag["\']\s+name=["\']([^"\']+)["\']>', webpage),
        }

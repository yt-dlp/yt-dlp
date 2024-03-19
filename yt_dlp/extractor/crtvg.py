import re

from .common import InfoExtractor
from ..utils import make_archive_id, remove_end


class CrtvgIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?crtvg\.es/tvg/a-carta/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.crtvg.es/tvg/a-carta/os-caimans-do-tea-5839623',
        'md5': 'c0958d9ff90e4503a75544358758921d',
        'info_dict': {
            'id': 'os-caimans-do-tea-5839623',
            'title': 'Os caimáns do Tea',
            'ext': 'mp4',
            'description': 'md5:f71cfba21ae564f0a6f415b31de1f842',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            '_old_archive_ids': ['crtvg 5839623'],
        },
        'params': {'skip_download': 'm3u8'}
    }, {
        'url': 'https://www.crtvg.es/tvg/a-carta/a-parabolica-love-story',
        'md5': '9a47b95a1749db7b7eb3214904624584',
        'info_dict': {
            'id': 'a-parabolica-love-story',
            'title': 'A parabólica / Trabuco, o can mordedor / Love Story',
            'ext': 'mp4',
            'description': 'md5:f71cfba21ae564f0a6f415b31de1f842',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'params': {'skip_download': 'm3u8'}
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_url = self._search_regex(r'var\s+url\s*=\s*["\']([^"\']+)', webpage, 'video url')
        formats = self._extract_m3u8_formats(video_url + '/playlist.m3u8', video_id, fatal=False)
        formats.extend(self._extract_mpd_formats(video_url + '/manifest.mpd', video_id, fatal=False))

        old_video_id = None
        if mobj := re.fullmatch(r'[^/#?]+-(?P<old_id>\d{7})', video_id):
            old_video_id = [make_archive_id(self, mobj.group('old_id'))]

        return {
            'id': video_id,
            '_old_archive_ids': old_video_id,
            'formats': formats,
            'title': remove_end(self._html_search_meta(
                ['og:title', 'twitter:title'], webpage, 'title', default=None), ' | CRTVG'),
            'description': self._html_search_meta('description', webpage, 'description', default=None),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail', default=None),
        }

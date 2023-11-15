import re

from .common import InfoExtractor
from ..utils import traverse_obj


class TelecaribePlayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?play\.telecaribe\.co/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.play.telecaribe.co/breicok',
        'info_dict': {
            'id': 'breicok',
            'title': 'Breicok',
        },
        'playlist_count': 7,
    }, {
        'url': 'https://www.play.telecaribe.co/si-fue-gol-de-yepes',
        'info_dict': {
            'id': 'si-fue-gol-de-yepes',
            'title': 'Sí Fue Gol de Yepes',
        },
        'playlist_count': 6,
    }, {
        'url': 'https://www.play.telecaribe.co/ciudad-futura',
        'info_dict': {
            'id': 'ciudad-futura',
            'title': 'Ciudad Futura',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.play.telecaribe.co/live',
        'info_dict': {
            'id': 'live',
            'title': r're:^Señal en vivo',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        }
    }, {
        'url': 'https://www.play.telecaribe.co/liveplus',
        'info_dict': {
            'id': 'liveplus',
            'title': r're:^Señal en vivo Plus',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
        'skip': 'Geo-restricted to Colombia',
    }]

    def _download_player_webpage(self, webpage, display_id):
        page_id = self._search_regex(
            (r'window\.firstPageId\s*=\s*["\']([^"\']+)', r'<div[^>]+id\s*=\s*"pageBackground_([^"]+)'),
            webpage, 'page_id')

        props = self._download_json(self._search_regex(
            rf'<link[^>]+href\s*=\s*"([^"]+)"[^>]+id\s*=\s*"features_{page_id}"',
            webpage, 'json_props_url'), display_id)['props']['render']['compProps']

        return self._download_webpage(traverse_obj(props, (..., 'url'))[-1], display_id)

    def _get_clean_title(self, title):
        return re.sub(r'\s*\|\s*Telecaribe\s*VOD', '', title or '').strip() or None

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        player = self._download_player_webpage(webpage, display_id)

        livestream_url = self._search_regex(
            r'(?:let|const|var)\s+source\s*=\s*["\']([^"\']+)', player, 'm3u8 url', default=None)

        if not livestream_url:
            return self.playlist_from_matches(
                re.findall(r'<a[^>]+href\s*=\s*"([^"]+\.mp4)', player), display_id,
                self._get_clean_title(self._og_search_title(webpage)))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            livestream_url, display_id, 'mp4', live=True)

        return {
            'id': display_id,
            'title': self._get_clean_title(self._og_search_title(webpage)),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
        }

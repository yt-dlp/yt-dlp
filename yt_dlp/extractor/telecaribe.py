import re

from .common import InfoExtractor


class TelecaribeBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?play\.telecaribe\.co'

    def _download_player_webpage(self, webpage, display_id):
        page_id = (self._search_regex(r'window.firstPageId\s*=\s*["\']([^"\']+)', webpage, 'page_id', fatal=False)
                   or self._search_regex(r'<div[^>]+id\s*=\s*"pageBackground_([^"]+)', webpage, 'page_id', fatal=False))

        props = self._download_json(self._search_regex(
            rf'<link[^>]+href\s*=\s*"([^"]+)"[^>]+id\s*=\s*"features_{page_id}"', webpage, 'json_props_url'),
            display_id)['props']['render']['compProps']

        # We reverse over the keys, to prefer the last dict that contains an 'url' key
        return self._download_webpage(
            next(props[prop_key]['url'] for prop_key in reversed(props.keys())
                 if 'url' in dict.keys(props[prop_key])), display_id)

    def _get_clean_title(self, title):
        return re.sub(r'\s*\|\s*Telecaribe\s*VOD', '', title or '').strip() or None


class TelecaribePlayVODIE(TelecaribeBaseIE):
    _VALID_URL = TelecaribeBaseIE._VALID_URL_BASE + r'/(?P<id>(?!live$)[\w-]+)'

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
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        return self.playlist_from_matches(
            re.findall(r'<a[^>]+href\s*=\s*"([^"]+\.mp4)', self._download_player_webpage(webpage, display_id)),
            playlist_id=display_id, playlist_title=self._get_clean_title(self._og_search_title(webpage)))


class TelecaribePlayLiveIE(TelecaribeBaseIE):
    _VALID_URL = TelecaribeBaseIE._VALID_URL_BASE + r'/(?P<id>live)$'

    _TESTS = [{
        'url': 'https://www.play.telecaribe.co/live',
        'info_dict': {
            'id': 'live',
            'title': r're:^Señal en vivo',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            self._search_regex(
                r'(?:let|const|var)\s+source\s*=\s*["\']([^"\']+)',
                self._download_player_webpage(webpage, display_id), 'formats_url'), display_id, 'mp4')

        return {
            'id': display_id,
            'title': self._get_clean_title(self._og_search_title(webpage)),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
        }

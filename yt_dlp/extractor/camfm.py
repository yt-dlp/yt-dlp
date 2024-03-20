import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    get_elements_by_class,
    join_nonempty,
    traverse_obj,
    unified_timestamp,
    urljoin,
)


class CamFMShowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?camfm\.co\.uk/shows/(?P<id>[^/]+)'
    _TESTS = [{
        'playlist_mincount': 5,
        'url': 'https://camfm.co.uk/shows/soul-mining/',
        'info_dict': {
            'id': 'soul-mining',
            'thumbnail': 'md5:6a873091f92c936f23bdcce80f75e66a',
            'title': 'Soul Mining',
            'description': 'Telling the stories of jazz, funk and soul from all corners of the world.',
        },
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        page = self._download_webpage(url, show_id)

        return {
            '_type': 'playlist',
            'id': show_id,
            'entries': [self.url_result(urljoin('https://camfm.co.uk', i), CamFMEpisodeIE)
                        for i in re.findall(r"javascript:popup\('(/player/[^']+)', 'listen'", page)],
            'thumbnail': urljoin('https://camfm.co.uk', self._search_regex(
                r'<img[^>]+class="thumb-expand"[^>]+src="([^"]+)"', page, 'thumbnail', fatal=False)),
            'title': self._html_search_regex('<h1>([^<]+)</h1>', page, 'title', fatal=False),
            'description': clean_html(get_element_by_class('small-12 medium-8 cell', page))
        }


class CamFMEpisodeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?camfm\.co\.uk/player/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://camfm.co.uk/player/43336',
        'skip': 'Episode will expire - don\'t actually know when, but it will go eventually',
        'info_dict': {
            'id': '43336',
            'title': 'AITAA: Am I the Agony Aunt? - 19:00 Tue 16/05/2023',
            'ext': 'mp3',
            'upload_date': '20230516',
            'description': 'md5:f165144f94927c0f1bfa2ee6e6ab7bbf',
            'timestamp': 1684263600,
            'series': 'AITAA: Am I the Agony Aunt?',
            'thumbnail': 'md5:5980a831360d0744c3764551be3d09c1',
            'categories': ['Entertainment'],
        }
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        page = self._download_webpage(url, episode_id)
        audios = self._parse_html5_media_entries('https://audio.camfm.co.uk', page, episode_id)

        caption = get_element_by_class('caption', page)
        series = clean_html(re.sub(r'<span[^<]+<[^<]+>', '', caption))

        card_section = get_element_by_class('card-section', page)
        date = self._html_search_regex('>Aired at ([^<]+)<', card_section, 'air date', fatal=False)

        return {
            'id': episode_id,
            'title': join_nonempty(series, date, delim=' - '),
            'formats': traverse_obj(audios, (..., 'formats', ...)),
            'timestamp': unified_timestamp(date),  # XXX: Does not account for UK's daylight savings
            'series': series,
            'description': clean_html(re.sub(r'<b>[^<]+</b><br[^>]+/>', '', card_section)),
            'thumbnail': urljoin('https://camfm.co.uk', self._search_regex(
                r'<div[^>]+class="cover-art"[^>]+style="[^"]+url\(\'([^\']+)',
                page, 'thumbnail', fatal=False)),
            'categories': get_elements_by_class('label', caption),
            'was_live': True,
        }

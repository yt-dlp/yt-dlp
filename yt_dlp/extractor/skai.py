from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    js_to_json,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class SkaiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skai(?:tv)?\.gr/(?:tv/)?episode/(?P<id>[^/?#]+(?:/[^/?#]+)*)'
    _GEO_COUNTRIES = ['GR']
    _TESTS = [{
        'url': 'https://www.skai.gr/tv/episode/seires/tote-vs-tora/2025-12-17-21',
        'info_dict': {
            'id': '341062',
            'display_id': 'seires/tote-vs-tora/2025-12-17-21',
            'ext': 'mp4',
            'title': 'Τότε και Τώρα | Ρεβεγιόν',
            'description': 'md5:28fbe574bcbd01fbcd206c880f04a2e3',
            'thumbnail': r'https://media.skaitv.gr/images/1170/0/files/tote_vs_tora/2025-2026/tote_7_revegion.jpg',
            'timestamp': 1765929600,
            'upload_date': '20251217',
            'series': 'Τότε και Τώρα',
            'episode': 'Ρεβεγιόν',
            'episode_number': 7,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.skai.gr/tv/episode/psuchagogia/movietime-3/2025-12-22-21/o-monomachos',
        'info_dict': {
            'id': '338667',
            'display_id': 'psuchagogia/movietime-3/2025-12-22-21/o-monomachos',
            'ext': 'mp4',
            'title': 'Ο μονομάχος',
            'description': 'md5:bbb3d3d104d8f544f1b990b5d6c57b24',
            'thumbnail': r'https://media.skaitv.gr/images/1170/0/files/tainies/monomaxos1_landscape.jpg',
            'timestamp': 1766361600,
            'upload_date': '20251222',
            'episode': 'Ο μονομάχος',
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        data = self._search_json(
            r'var\s+data\s*=(?=\s*{"episode")', webpage, 'player data', display_id,
            transform_source=js_to_json)

        media_item_file = traverse_obj(data, ('episode', 0, 'media_item_file', {str}))
        if not media_item_file:
            raise ExtractorError('Video not found', expected=True)

        media_item_file = media_item_file.lstrip('/')
        pre = 'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/'
        m3u8_url = pre + media_item_file + '/chunklist.m3u8'
        formats = self._extract_m3u8_formats(m3u8_url, display_id, 'mp4', m3u8_id='hls')

        info = self._search_json_ld(webpage, display_id, expected_type='VideoObject', default={})
        info = {
            **info,
            'id': display_id,
            'display_id': display_id,
            'formats': formats,
            **traverse_obj(info, {
                'description': ('description', {clean_html}),
            }),
            **traverse_obj(data, ('episode', 0), {
                'id': ('id', {str_or_none}),
                'title': ('title', {str}),
                'description': ('descr', {clean_html}),
                'thumbnail': ('img', {url_or_none}),
                'timestamp': ('start', {unified_timestamp}),
                'episode_number': ('episode_number', {int_or_none}),
            }),
        }
        if not info.get('title'):
            info['title'] = self._html_search_meta(
                ('title', 'og:title', 'twitter:title'), webpage) or self._html_extract_title(webpage)
        if not info.get('description'):
            info['description'] = (
                self._html_search_meta(
                    ('description', 'og:description', 'twitter:description'), webpage)
                or traverse_obj(data, ('episode', 0, ('meta_descr', 'short_descr'), {clean_html}, any)))
        if not info.get('thumbnail'):
            info['thumbnail'] = self._og_search_thumbnail(webpage)
        series, _, info['episode'] = info['title'].rpartition(' | ')
        if series:
            info['series'] = series
        return info

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    js_to_json,
    traverse_obj,
    unified_strdate,
)


class SkaiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skai(?:tv)?\.gr/(?:tv/)?episode/(?P<id>[^/?#]+(?:/[^/?#]+)*)'
    _TESTS = [{
        'url': 'https://www.skai.gr/tv/episode/seires/tote-vs-tora/2025-12-17-21',
        'info_dict': {
            'id': '341062',
            'display_id': 'seires/tote-vs-tora/2025-12-17-21',
            'ext': 'mp4',
            'title': 'Τότε και Τώρα | Ρεβεγιόν',
            'description': 'md5:28fbe574bcbd01fbcd206c880f04a2e3',
            'thumbnail': r'https://media.skaitv.gr/images/1170/0/files/tote_vs_tora/2025-2026/tote_7_revegion.jpg',
            'upload_date': '20251217',
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
            'upload_date': '20251222',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        data = self._search_json(
            r'var\s+data\s*=\s*(?={"episode")', webpage, 'player data', display_id,
            transform_source=js_to_json)

        episode = traverse_obj(data, ('episode', 0))
        if not episode:
            raise ExtractorError('Video not found', expected=True)

        video_id = episode.get('id') or display_id
        title = episode.get('title') or self._og_search_title(webpage)
        description = clean_html(episode.get('descr')) or self._og_search_description(webpage)
        thumbnail = episode.get('img') or self._og_search_thumbnail(webpage)

        media_item_file = episode.get('media_item_file')

        if not media_item_file:
            raise ExtractorError('Video not found', expected=True)

        media_item_file = media_item_file.lstrip('/')
        pre = 'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/'
        m3u8_url = pre + media_item_file + '/chunklist.m3u8'
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')

        # Try to get upload date from JSON-LD or 'start' field
        json_ld = self._search_json_ld(webpage, video_id, default={})
        upload_date = unified_strdate(json_ld.get('uploadDate') or episode.get('start'))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'upload_date': upload_date,
        }

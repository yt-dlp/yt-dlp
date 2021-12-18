# coding: utf-8
from .common import InfoExtractor


class MegatvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?megatv\.com/[g|e]?tvshows/[0-9]+/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.megatv.com/tvshows/49259/antio-kurie-upourge/',
        'md5': '1d1be304fa2776c11acd90cf5198f795',
        'info_dict': {
            'id': 'antio-kurie-upourge',
            'ext': 'mp4',
            'title': 'Το Κόκκινο Δωμάτιο: Επεισόδιο: 1',
            'thumbnail': 'https://www.megatv.com/wp-content/uploads/2020/09/5-901.jpeg',
        }
    }, {
        'url': 'https://www.megatv.com/gtvshows/551051/epeisodio-22-9/',
        'md5': 'fbeac3be2e102917e657c745cd657cb2',
        'info_dict': {
            'id': 'epeisodio-22-9',
            'ext': 'mp4',
            'title': 'Celebrity Game Night: Επεισόδιο 22',
            'thumbnail': 'https://www.megatv.com/wp-content/uploads/2021/11/27-2.jpg'
        }
    }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        thumbnail_url, hls_playlist, title = self._search_regex(
            r'''<div[^>]+
                data-kwik_image="(?P<thumbnail>[^"]+)"[^>]+
                data-kwik_source="(?P<hls>[^"]+)"[^>]+
                data-kwik_label="(?P<title>[^"]+)[^>]+>''',
            webpage, 'title, hls_url, thumbnail', group=("thumbnail", "hls", "title"))
        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            hls_playlist, video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(fmts)
        return {
            'id': video_id,
            'title': title,
            'formats': fmts,
            'thumbnail': thumbnail_url,
            'subtitles': subs
        }

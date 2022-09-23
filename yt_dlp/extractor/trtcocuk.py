from urllib.parse import unquote

from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, traverse_obj


class TrtCocukVideoIE(InfoExtractor):
    _VALID_URL = r'https?://www\.trtcocuk\.net\.tr/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.trtcocuk.net.tr/video/kaptan-pengu-ve-arkadaslari-1',
        'info_dict': {
            'id': '3789738',
            'ext': 'mp4',
            'season_number': 1,
            'series': '"Kaptan Pengu ve Arkadaşları"',
            'season': 'Season 1',
            'title': 'Kaptan Pengu ve Arkadaşları 1 Bölüm İzle TRT Çocuk',
            'release_date': '20201209',
            'release_timestamp': 1607513774,
        }
    }, {
        'url': 'https://www.trtcocuk.net.tr/video/sef-rokanin-lezzet-dunyasi-17',
        'info_dict': {
            'id': '10260842',
            'ext': 'mp4',
            'series': '"Şef Roka\'nın Lezzet Dünyası"',
            'title': 'Şef Roka\'nın Lezzet Dünyası 17 Bölüm İzle TRT Çocuk',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        nuxtjs_data = self._search_nuxt_data(webpage, display_id)['data']
        video_url = self._search_regex(
            r'[\'"]?(?P<url>[^"]+)', unquote(nuxtjs_data['video']), 'video_url')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            str(video_url).replace(r'\u002F', '/'), display_id)
        return {
            'id': str(nuxtjs_data['id']),
            'formats': formats,
            'subtitles': subtitles,
            'season_number': int_or_none(nuxtjs_data.get('season')),
            'release_timestamp': parse_iso8601(nuxtjs_data.get('publishedDate')),
            'series': traverse_obj(nuxtjs_data, ('show', 0, 'title')),
            'title': self._html_extract_title(webpage)  # TODO: get better title
        }

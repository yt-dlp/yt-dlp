from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, str_or_none, traverse_obj


class TempoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.tempo\.co/\w+/\d+/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://video.tempo.co/read/30058/anies-baswedan-ajukan-banding-putusan-ptun-batalkan-ump-dki',
        'info_dict': {
            'id': '2144438',
            'ext': 'mp4',
            'title': 'Anies Baswedan Ajukan Banding Putusan PTUN Batalkan UMP DKI',
            'display_id': 'anies-baswedan-ajukan-banding-putusan-ptun-batalkan-ump-dki',
            'duration': 84,
            'description': 'md5:a6822b7c4c874fa7e5bd63e96a387b66',
            'thumbnail': 'https://statik.tempo.co/data/2022/07/27/id_1128287/1128287_720.jpg',
            'timestamp': 1658911277,
            'upload_date': '20220727',
            'tags': ['Anies Baswedan', ' PTUN', ' PTUN | Pengadilan Tata Usaha Negara', ' PTUN Batalkan UMP DKI', ' UMP DKI'],
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        player_key, widget_id = self._search_regex(
            r'<ivs-player\s*[^>]+data-ivs-key\s*=\s*"(?P<player_key>[\w]+)[^>]+\bdata-ivs-wid="(?P<widget_id>[\w-]+)',
            webpage, 'player_key, widget_id', group=('player_key', 'widget_id'))

        json_ld_data = self._search_json_ld(webpage, display_id)

        json_data = self._download_json(
            f'https://ivxplayer.ivideosmart.com/prod/widget/{widget_id}',
            display_id, query={'key': player_key})
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            json_data['player']['video_url'], display_id, ext='mp4')

        return {
            'id': str(json_data['ivx']['id']),
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': (self._html_search_meta('twitter:title', webpage) or self._og_search_title(webpage)
                      or traverse_obj(json_data, ('ivx', 'name'))),
            'duration': int_or_none(traverse_obj(json_data, ('ivx', 'duration'))),
            'thumbnail': (self._html_search_meta('twitter:image:src', webpage) or self._og_search_thumbnail(webpage)
                          or traverse_obj(json_data, ('ivx', 'thumbnail_url'))),
            'description': (json_ld_data.get('description') or self._html_search_meta(['description', 'twitter:description'], webpage)
                            or self._og_search_description(webpage)),
            'timestamp': parse_iso8601(traverse_obj(json_data, ('ivx', 'created_at'))),
            'tags': str_or_none(self._html_search_meta('keywords', webpage), '').split(','),
        }

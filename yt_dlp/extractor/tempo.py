from .common import InfoExtractor
from ..utils import str_or_none


class TempoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.tempo\.co/\w+/\d+/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://video.tempo.co/read/30058/anies-baswedan-ajukan-banding-putusan-ptun-batalkan-ump-dki',
        'info_dict': {
            'id': '2144275',
            'display_id': 'anies-baswedan-ajukan-banding-putusan-ptun-batalkan-ump-dki',
            'ext': 'mp4',
            'title': 'Anies Baswedan Ajukan Banding Putusan PTUN Batalkan UMP DKI',
            'duration': 85,
            'description': 'md5:a6822b7c4c874fa7e5bd63e96a387b66',
            'thumbnail': 'https://statik.tempo.co/data/2022/07/27/id_1128287/1128287_720.jpg',
            'timestamp': 1658907970,
            'upload_date': '20220727',
            'tags': ['Anies Baswedan', ' PTUN', ' PTUN | Pengadilan Tata Usaha Negara', ' PTUN Batalkan UMP DKI', ' UMP DKI'],
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        player_key, video_id = self._search_regex(
            r'<ivs-player\s*[^>]+data-ivs-key\s*=\s*"(?P<player_key>[\w]+)\s*[^>]+\bdata-ivs-vid="(?P<video_id>[\w-]+)',
            webpage, 'player_key, video_id', group=('player_key', 'video_id'))

        json_ld_data = self._search_json_ld(webpage, display_id)

        return self.url_result(
            f'ivxplayer:{video_id}:{player_key}', display_id=display_id,
            thumbnail=self._html_search_meta('twitter:image:src', webpage) or self._og_search_thumbnail(webpage),
            tags=str_or_none(self._html_search_meta('keywords', webpage), '').split(','),
            description=(
                json_ld_data.get('description') or self._html_search_meta(['description', 'twitter:description'], webpage)
                or self._og_search_description(webpage)), url_transparent=True)

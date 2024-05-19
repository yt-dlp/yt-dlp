from .common import InfoExtractor
from ..utils import extract_attributes, remove_end


class TheHoleTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?the-hole\.tv/episodes/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://the-hole.tv/episodes/gromkii-vopros-sergey-orlov',
        'md5': 'fea6682f47786f3ae5a6cbd635ec4bf9',
        'info_dict': {
            'id': 'gromkii-vopros-sergey-orlov',
            'ext': 'mp4',
            'title': 'Сергей Орлов — Громкий вопрос',
            'thumbnail': 'https://assets-cdn.the-hole.tv/images/t8gan4n6zn627e7wni11b2uemqts',
            'description': 'md5:45741a9202331f995d9fb76996759379'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        player_attrs = extract_attributes(self._search_regex(
            r'(<div[^>]*\bdata-controller="player"[^>]*>)', webpage, 'video player'))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            player_attrs['data-player-source-value'], video_id, 'mp4')

        return {
            'id': video_id,
            'title': remove_end(self._html_extract_title(webpage), ' — The Hole'),
            'description': self._og_search_description(webpage),
            'thumbnail': player_attrs.get('data-player-poster-value'),
            'formats': formats,
            'subtitles': subtitles
        }

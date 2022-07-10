from .common import InfoExtractor
from ..utils import extract_attributes


class TheHoleTvExtractorIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?the-hole\.tv/episodes/(?P<id>[a-z0-9\-]+)'
    _TESTS = [{
        'url': "https://the-hole.tv/episodes/gromkii-vopros-sergey-orlov",
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

        title = self._html_extract_title(webpage).removesuffix(' — The Hole')
        description = self._og_search_description(webpage)

        player_div = self._search_regex(r'(<div[^>]*data-controller="player">)', webpage, 'video player div')
        player_attrs = extract_attributes(player_div)

        thumbnail = player_attrs['data-player-poster-value']
        formats = self._extract_m3u8_formats(player_attrs['data-player-source-value'], video_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }

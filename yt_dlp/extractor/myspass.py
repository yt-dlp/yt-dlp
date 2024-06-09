from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    xpath_text,
)


class MySpassIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myspass\.de/(?:[^/]+/)*(?P<id>\d+)/?[^/]*$'
    _TESTS = [{
        'url': 'http://www.myspass.de/myspass/shows/tvshows/absolute-mehrheit/Absolute-Mehrheit-vom-17022013-Die-Highlights-Teil-2--/11741/',
        'md5': '0b49f4844a068f8b33f4b7c88405862b',
        'info_dict': {
            'id': '11741',
            'ext': 'mp4',
            'description': 'md5:9f0db5044c8fe73f528a390498f7ce9b',
            'title': '17.02.2013 - Die Highlights, Teil 2',
            'thumbnail': r're:.*\.jpg',
            'duration': 323.0,
            'episode': '17.02.2013 - Die Highlights, Teil 2',
            'season_id': '544',
            'episode_number': 1,
            'series': 'Absolute Mehrheit',
            'season_number': 2,
            'season': 'Season 2',
        },
    },
        {
        'url': 'https://www.myspass.de/shows/tvshows/tv-total/Novak-Puffovic-bei-bester-Laune--/44996/',
        'md5': 'eb28b7c5e254192046e86ebaf7deac8f',
        'info_dict': {
            'id': '44996',
            'ext': 'mp4',
            'description': 'md5:74c7f886e00834417f1e427ab0da6121',
            'title': 'Novak Puffovic bei bester Laune',
            'thumbnail': r're:.*\.jpg',
            'episode_number': 8,
            'episode': 'Novak Puffovic bei bester Laune',
            'series': 'TV total',
            'season': 'Season 19',
            'season_id': '987',
            'duration': 2941.0,
            'season_number': 19,
        },
    },
        {
        'url': 'https://www.myspass.de/channels/tv-total-raabigramm/17033/20831/',
        'md5': '7b293a6b9f3a7acdd29304c8d0dbb7cc',
        'info_dict': {
            'id': '20831',
            'ext': 'mp4',
            'description': 'Gefühle pur: Schaut euch die ungeschnittene Version von Stefans Liebesbeweis an die Moderationsgrazie von Welt, Verona Feldbusch, an.',
            'title': 'Raabigramm Verona Feldbusch',
            'thumbnail': r're:.*\.jpg',
            'episode_number': 6,
            'episode': 'Raabigramm Verona Feldbusch',
            'series': 'TV total',
            'season': 'Season 1',
            'season_id': '34',
            'duration': 105.0,
            'season_number': 1,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_xml('http://www.myspass.de/myspass/includes/apps/video/getvideometadataxml.php?id=' + video_id, video_id)

        title = xpath_text(metadata, 'title', fatal=True)
        video_url = xpath_text(metadata, 'url_flv', 'download url', True)
        video_id_int = int(video_id)
        for group in self._search_regex(r'/myspass2009/\d+/(\d+)/(\d+)/(\d+)/', video_url, 'myspass', group=(1, 2, 3), default=[]):
            group_int = int(group)
            if group_int > video_id_int:
                video_url = video_url.replace(group, str(group_int // video_id_int))

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'thumbnail': xpath_text(metadata, 'imagePreview'),
            'description': xpath_text(metadata, 'description'),
            'duration': parse_duration(xpath_text(metadata, 'duration')),
            'series': xpath_text(metadata, 'format'),
            'season_number': int_or_none(xpath_text(metadata, 'season')),
            'season_id': xpath_text(metadata, 'season_id'),
            'episode': title,
            'episode_number': int_or_none(xpath_text(metadata, 'episode')),
        }

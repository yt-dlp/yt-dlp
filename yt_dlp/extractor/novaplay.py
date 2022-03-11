# coding: utf-8
from .common import InfoExtractor
from ..utils import int_or_none, parse_duration, parse_iso8601


class NovaPlayIE(InfoExtractor):
    _VALID_URL = r'https://play.nova\.bg/video/.*/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://play.nova.bg/video/bratya/season-3/bratq-2021-10-08/548677',
            'md5': 'b1127a84e61bed1632b7c2ca9cbb4153',
            'info_dict': {
                'id': '548677',
                'ext': 'mp4',
                'title': 'Братя',
                'alt_title': 'bratya/season-3/bratq-2021-10-08',
                'duration': 1603.0,
                'timestamp': 1633724150,
                'upload_date': '20211008',
                'thumbnail': 'https://nbg-img.fite.tv/img/548677_460x260.jpg',
                'description': 'Сезон 3 Епизод 25'
            },
        },
        {
            'url': 'https://play.nova.bg/video/igri-na-volqta/season-3/igri-na-volqta-2021-09-20-1/548227',
            'md5': '5fd61b8ecbe582fc021019d570965d58',
            'info_dict': {
                'id': '548227',
                'ext': 'mp4',
                'title': 'Игри на волята: България (20.09.2021) - част 1',
                'alt_title': 'gri-na-volqta/season-3/igri-na-volqta-2021-09-20-1',
                'duration': 4060.0,
                'timestamp': 1632167564,
                'upload_date': '20210920',
                'thumbnail': 'https://nbg-img.fite.tv/img/548227_460x260.jpg',
                'description': 'Сезон 3 Епизод 13'
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_props = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['video']
        m3u8_url = self._download_json(
            f'https://nbg-api.fite.tv/api/v2/videos/{video_id}/streams',
            video_id, headers={'x-flipps-user-agent': 'Flipps/75/9.7'})[0]['url']
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_props['title'],
            'alt_title': video_props.get('slug'),
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'duration': parse_duration(video_props['duration']),
            'timestamp': parse_iso8601(video_props['published_at']),
            'view_count': int_or_none(video_props['view_count']),
        }

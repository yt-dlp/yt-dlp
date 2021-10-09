# coding: utf-8
from .common import InfoExtractor
import re
import json
from ..utils import parse_duration


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
                'release_date': '2021-10-08T20:15:50+00:00',
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
                'release_date': '2021-09-20T19:52:44+00:00',
                'thumbnail': 'https://nbg-img.fite.tv/img/548227_460x260.jpg',
                'description': 'Сезон 3 Епизод 13'
            },
        }
    ]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, self._match_id(url))
        video_props = json.loads(re.search(
            r'<script\s?id=\"__NEXT_DATA__\"\s?type=\"application/json\">({.+})</script>',
            webpage).group(1))['props']['pageProps']['video']
        m3u8_url = self._download_json(
            f'https://nbg-api.fite.tv/api/v2/videos/{video_props["id"]}/streams',
            video_props['id'], headers={'x-flipps-user-agent': 'Flipps/75/9.7'})[0]['url']
        formats = self._extract_m3u8_formats(m3u8_url, video_props['id'], 'mp4', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': str(video_props['id']),
            'url': url,
            'title': video_props['title'],
            'alt_title': video_props['slug'],
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'duration': parse_duration(video_props['duration']),
            'release_date': video_props['published_at'],
            'view_count': video_props['view_count']
        }

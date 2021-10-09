# coding: utf-8
from .common import InfoExtractor


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
                'thumbnail': 'https://nbg-img.fite.tv/img/548227_460x260.jpg',
                'description': 'Сезон 3 Епизод 13'
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage)
        thumbnail = self._og_search_property('image', webpage)
        api_url = 'https://nbg-api.fite.tv/api/v2/videos/' + video_id + '/streams'
        m3u8_url = self._download_json(api_url, video_id, headers={
            'x-flipps-user-agent': 'Flipps/75/9.7'
        })[0]['url']
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'url': m3u8_url,
            'title': title,
            'thumbnail': thumbnail,
            'description': self._og_search_description(webpage),
            'formats': formats
        }

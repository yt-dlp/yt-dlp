from __future__ import unicode_literals


from .common import InfoExtractor

from ..utils import int_or_none


class MediaiteIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mediaite.com/(?:tv|sports|politics|podcasts|opinion)/[\w-]+/'
    _TESTS = [{
        'url': 'https://www.mediaite.com/sports/bill-burr-roasts-nfl-for-promoting-black-lives-matter-while-scheduling-more-games-after-all-the-sht-they-know-about-cte/',
        'info_dict': {
            'id': 'vPHKITzy',
            'ext': 'm4a',
            'title': 'Bill Burr On NFL And Black Lives Matter',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/vPHKITzy/poster.jpg?width=720',
            'duration': 55,
            'timestamp': 1631630185,
            'upload_date': '20210914',
            'filesize': 790208
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.mediaite.com/tv/joe-scarborough-goes-off-on-tax-breaks-for-super-wealthy-largest-income-redistribution-scam-in-american-history/',
        'info_dict': {
            'id': 'eeFcK4Xm',
            'ext': 'mp4',
            'title': 'Morning Joe-6_16_52 am - 6_21_10 am-2021-09-14.mp4',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/eeFcK4Xm/poster.jpg?width=720',
            'duration': 258,
            'timestamp': 1631618057,
            'upload_date': '20210914',
            'filesize': 34511073
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.mediaite.com/politics/watch-rudy-giuliani-impersonates-queen-elizabeth-calls-mark-milley-an-asshle-in-bizarre-9-11-speech/',
        'info_dict': {
            'id': 'EiyiXKcr',
            'ext': 'mp4',
            'title': 'Giuliani 1',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/EiyiXKcr/poster.jpg?width=720',
            'duration': 39,
            'timestamp': 1631536476,
            'upload_date': '20210913',
            'filesize': 2071224
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.mediaite.com/podcasts/clarissa-ward-says-she-decided-to-become-a-journalist-on-9-11/',
        'info_dict': {
            'id': 'TxavoRTx',
            'ext': 'mp4',
            'title': 'clarissa-ward-3.mp4',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/TxavoRTx/poster.jpg?width=720',
            'duration': 83,
            'timestamp': 1631311188,
            'upload_date': '20210910',
            'filesize': 3715800
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.mediaite.com/opinion/mainstream-media-ignores-rose-mcgowans-bombshell-allegation-that-newsoms-wife-tried-to-silence-her-on-weinstein/',
        'info_dict': {
            'id': 'sEIWvKR7',
            'ext': 'mp4',
            'title': 'KTTV_09-13-2021_05.34.21',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/sEIWvKR7/poster.jpg?width=720',
            'duration': 52,
            'timestamp': 1631553328,
            'upload_date': '20210913',
            'filesize': 10468713
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        id = self._search_regex(r'data-video-id\s?=\s?\"([^\"]+)\"', webpage, 'id')
        data_json = self._download_json(f'https://cdn.jwplayer.com/v2/media/{id}', id)
        video_json = data_json['playlist'][0]
        formats = []
        for source in video_json.get('sources', []):
            if source.get('type') == 'application/vnd.apple.mpegurl':
                formats.extend(self._extract_m3u8_formats(source.get('file'), id, fatal=False))
            elif source.get('type') == 'video/mp4':
                formats.append({
                    'url': source.get('file'),
                    'height': source.get('height'),
                    'width': source.get('width'),
                    'filesize': source.get('filesize'),
                    'tbr': source.get('bitrate') / 1000,
                    'fps': source.get('framerate'),
                })
            elif source.get('type') == 'audio/mp4':
                formats.append({
                    'url': source.get('file'),
                    'filesize': source.get('filesize'),
                    'tbr': source.get('bitrate') / 1000,
                    'vcodec': 'none',
                })
        self._sort_formats(formats)
        return {
            'id': id,
            'title': data_json.get('title'),
            'description': data_json.get('description'),
            'thumbnail': video_json.get('image'),
            'duration': video_json.get('duration'),
            'timestamp': int_or_none(video_json.get('pubdate')),
            'formats': formats,
        }

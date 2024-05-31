from .common import InfoExtractor


class MediaiteIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mediaite\.com(?!/category)(?:/[\w-]+){2}'
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
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.mediaite.com/news/watch-cnbcs-jim-cramer-says-nobody-wants-to-die-getting-infected-by-unvaccinated-coworker-even-for-22-an-hour/',
        'info_dict': {
            'id': 'nwpt1elX',
            'ext': 'mp4',
            'title': "CNBC's Jim Cramer Says Nobody Wants to Die Getting Infected by Unvaccinated Coworker 'Even for $22 an Hour'.mp4",
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/nwpt1elX/poster.jpg?width=720',
            'duration': 60,
            'timestamp': 1633014214,
            'upload_date': '20210930',
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.mediaite.com/politics/i-cant-read-it-fast-enough-while-defending-trump-larry-kudlow-overwhelmed-by-volume-of-ex-presidents-legal-troubles/',
        'info_dict': {
            'id': 'E6EhDX5z',
            'ext': 'mp4',
            'title': 'Fox Business Network - 4:00 PM - 5:00 PM - 1:39:42 pm - 1:42:20 pm',
            'description': '',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/E6EhDX5z/poster.jpg?width=720',
            'duration': 157,
            'timestamp': 1691015535,
            'upload_date': '20230802',
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        video_id = self._search_regex(
            [r'"https://cdn\.jwplayer\.com/players/(\w+)', r'data-video-id\s*=\s*\"([^\"]+)\"'], webpage, 'id')
        data_json = self._download_json(f'https://cdn.jwplayer.com/v2/media/{video_id}', video_id)
        return self._parse_jwplayer_data(data_json)

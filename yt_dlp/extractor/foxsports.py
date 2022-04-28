from .common import InfoExtractor


class FoxSportsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?foxsports\.com/(?:[^/]+/)*video/(?P<id>\d+)'

    _TEST = {
        'url': 'http://www.foxsports.com/tennessee/video/432609859715',
        'md5': 'b49050e955bebe32c301972e4012ac17',
        'info_dict': {
            'id': '432609859715',
            'ext': 'mp4',
            'title': 'Courtney Lee on going up 2-0 in series vs. Blazers',
            'description': 'Courtney Lee talks about Memphis being focused.',
            # TODO: fix timestamp
            'upload_date': '19700101',  # '20150423',
            # 'timestamp': 1429761109,
            'uploader': 'NEWA-FNG-FOXSPORTS',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['ThePlatform'],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return self.url_result(
            'https://feed.theplatform.com/f/BKQ29B/foxsports-all?byId=' + video_id, 'ThePlatformFeed')

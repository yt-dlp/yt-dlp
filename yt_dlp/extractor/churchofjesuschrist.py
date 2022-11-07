from .common import InfoExtractor


class ChurchOfJesusChristIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)?churchofjesuschrist\.org\/broadcasts\/(?:(?:watch\/)|(?:article\/(?:(?:\w|-)*?)\/(?:\d*?)\/(?:\d*?)\/))(?P<id>(?:\w|-)+)(?:\?)*?'
    _TESTS = [{
        'url': 'https://www.churchofjesuschrist.org/broadcasts/article/ces-devotionals/2014/01/what-is-the-blueprint-of-christs-church?lang=eng',
        'md5': '5b20cebab4eb9dcfc4f8c5b79dac6398',
        'add_ie': ['BrightcoveNew'],
        'info_dict': {
            'id': '3045864911001',
            'ext': 'mp4',
            'upload_date': '20140113',
            'uploader_id': '1257553577001',
            'timestamp': 1389579921,
            'title': 'What Is the Blueprint of Christ\'s Church',
            'tags': ['2014 ces devotionals for young adults', 'ces devotionals', 'eng', 'seminaries and institutes of religion'],
            'description': 'January 12, 2014: Elder Tad R. Callister explains the spiritual blueprint the Lord used to build His church in order to best accommodate the spiritual needs of his children.',
            'duration': 3362.11,
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/static/1257553577001/8b16f142-2c03-4908-a6f2-8fcb40605792/15d3b352-dee5-4c37-afea-5f1187abf983/1920x1080/match/image.jpg'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        brightcove_id = self._html_search_regex(r'@videoPlayer":"(\d+)', webpage, 'brightcove id')
        brightcove_account = self._html_search_regex(r'"account":(?:{"default-account-id":")?"?(\d*?)"', webpage, 'brightcove account')

        target_url = f'http://players.brightcove.net/{brightcove_account}/default_default/index.html?videoId={brightcove_id}'

        return self.url_result(target_url, ie='BrightcoveNew')

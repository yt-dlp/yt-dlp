from .common import InfoExtractor


class ChurchOfJesusChristIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)?churchofjesuschrist\.org\/broadcasts\/watch\/(?P<id>(?:\w|-)*?)\/(?:.*)'
    _TESTS = [{
        'url': 'https://www.churchofjesuschrist.org/broadcasts/watch/lethbridge-alberta-member-devotional/2022/10?lang=eng',
        'md5': '424b7a63b9c3c706d1b1309c3bda90d6',
        'add_ie': ['BrightcoveNew'],
        'info_dict': {
            'id': '6313308990112',
            'ext': 'mp4',
            'upload_date': '20221005',
            'uploader_id': '710857117001',
            'timestamp': 1664994416,
            'title': str,
            'tags': [],
            'live_status': str
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        brightcove_id = self._html_search_regex(r'@videoPlayer":"(?P<id>\d*?)"', webpage, 'brightcove id')
        brightcove_account = self._html_search_regex(r'"account":"(\d*?)"', webpage, 'brightcove account')

        target_url = f'http://players.brightcove.net/{brightcove_account}/default_default/index.html?videoId={brightcove_id}'

        return self.url_result(target_url, ie='BrightcoveNew')
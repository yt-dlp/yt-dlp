from .common import InfoExtractor


class MyVidsterIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myvidster\.com/video/(?P<id>\d+)'

    _TEST = {
        'url': 'http://www.myvidster.com/video/32059805/Hot_chemistry_with_raw_love_making',
        'md5': '95296d0231c1363222c3441af62dc4ca',
        'info_dict': {
            'id': '3685814',
            'title': 'md5:7d8427d6d02c4fbcef50fe269980c749',
            'upload_date': '20141027',
            'uploader': 'utkualp',
            'ext': 'mp4',
            'age_limit': 18,
        },
        'add_ie': ['XHamster'],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return self.url_result(self._html_search_regex(
            r'rel="videolink" href="(?P<real_url>.*)">',
            webpage, 'real video url'))

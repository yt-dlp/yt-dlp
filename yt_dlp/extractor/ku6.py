from .common import InfoExtractor


class Ku6IE(InfoExtractor):
    _VALID_URL = r'https?://v\.ku6\.com/show/(?P<id>[a-zA-Z0-9\-\_]+)(?:\.)*html'
    _TEST = {
        'url': 'http://v.ku6.com/show/JG-8yS14xzBr4bCn1pu0xw...html',
        'md5': '01203549b9efbb45f4b87d55bdea1ed1',
        'info_dict': {
            'id': 'JG-8yS14xzBr4bCn1pu0xw',
            'ext': 'f4v',
            'title': 'techniques test',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<h1 title=.*>(.*?)</h1>', webpage, 'title')
        dataUrl = 'http://v.ku6.com/fetchVideo4Player/%s.html' % video_id
        jsonData = self._download_json(dataUrl, video_id)
        downloadUrl = jsonData['data']['f']

        return {
            'id': video_id,
            'title': title,
            'url': downloadUrl
        }

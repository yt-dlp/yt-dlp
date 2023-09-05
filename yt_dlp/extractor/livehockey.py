from .common import InfoExtractor
from .jwplatform import JWPlatformIE


class LiveHockeyIE(InfoExtractor):
    _VALID_URL = r'https?://livehockey\.com\.au/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://livehockey.com.au/hockey/wa/mens/03-september-fw1-hockey-wa-pl-mens-hale-v-uwa/',
        'md5': '69a67b3f9064824b807152a9c8b976e3',
        'info_dict': {
            'id': 'tJwY44y1',
            'ext': 'mp4',
            'title': "03 September - FW1 - Hockey WA PL Mens - Hale v UWA",
            'description': 'md5:c1a87687f504bc046bc063994cc25498',
            'upload_date': '20230903',
            'timestamp': 1693738139,
            'thumbnail': 'startswith:https://cdn.jwplayer.com/v2/media/tJwY44y1/poster.jpg',
        },
    }, {
        'url': 'https://livehockey.com.au/hockey/wa/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        jwplatform_id = self._search_regex(
            (r'jw(Media)?Id\s*[:=]\s*["\']([a-zA-Z0-9]{8})',
             r'jwplayer\.com/v2/media/([a-zA-Z0-9]{8})'),
            webpage, 'jwplatform id')
        return self.url_result(
            'jwplatform:%s' % jwplatform_id, ie=JWPlatformIE.ie_key(),
            video_id=video_id)

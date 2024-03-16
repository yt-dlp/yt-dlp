from .common import InfoExtractor
from ..compat import compat_b64decode
from ..networking import HEADRequest, Request
from ..utils import ExtractorError, urlencode_postdata


class HotNewHipHopIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?hotnewhiphop\.com/.*\.(?P<id>.*)\.html'
    _TEST = {
        'url': 'http://www.hotnewhiphop.com/freddie-gibbs-lay-it-down-song.1435540.html',
        'md5': '2c2cd2f76ef11a9b3b581e8b232f3d96',
        'info_dict': {
            'id': '1435540',
            'ext': 'mp3',
            'title': 'Freddie Gibbs - Lay It Down'
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_url_base64 = self._search_regex(
            r'data-path="(.*?)"', webpage, 'video URL', default=None)

        if video_url_base64 is None:
            video_url = self._search_regex(
                r'"contentUrl" content="(.*?)"', webpage, 'content URL')
            return self.url_result(video_url, ie='Youtube')

        reqdata = urlencode_postdata([
            ('mediaType', 's'),
            ('mediaId', video_id),
        ])
        r = Request(
            'http://www.hotnewhiphop.com/ajax/media/getActions/', data=reqdata)
        r.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        mkd = self._download_json(
            r, video_id, note='Requesting media key',
            errnote='Could not download media key')
        if 'mediaKey' not in mkd:
            raise ExtractorError('Did not get a media key')

        redirect_url = compat_b64decode(video_url_base64).decode('utf-8')
        redirect_req = HEADRequest(redirect_url)
        req = self._request_webpage(
            redirect_req, video_id,
            note='Resolving final URL', errnote='Could not resolve final URL')
        video_url = req.url
        if video_url.endswith('.html'):
            raise ExtractorError('Redirect failed')

        video_title = self._og_search_title(webpage).strip()

        return {
            'id': video_id,
            'url': video_url,
            'title': video_title,
            'thumbnail': self._og_search_thumbnail(webpage),
        }

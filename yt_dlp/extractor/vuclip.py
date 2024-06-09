import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_duration,
    remove_end,
)


class VuClipIE(InfoExtractor):
    _VALID_URL = r'https?://(?:m\.)?vuclip\.com/w\?.*?cid=(?P<id>[0-9]+)'

    _TEST = {
        'url': 'http://m.vuclip.com/w?cid=1129900602&bu=8589892792&frm=w&z=34801&op=0&oc=843169247&section=recommend',
        'info_dict': {
            'id': '1129900602',
            'ext': '3gp',
            'title': 'Top 10 TV Convicts',
            'duration': 733,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        ad_m = re.search(
            r'''value="No.*?" onClick="location.href='([^"']+)'"''', webpage)
        if ad_m:
            urlr = urllib.parse.urlparse(url)
            adfree_url = urlr.scheme + '://' + urlr.netloc + ad_m.group(1)
            webpage = self._download_webpage(
                adfree_url, video_id, note='Download post-ad page')

        error_msg = self._html_search_regex(
            r'<p class="message">(.*?)</p>', webpage, 'error message',
            default=None)
        if error_msg:
            raise ExtractorError(
                f'{self.IE_NAME} said: {error_msg}', expected=True)

        # These clowns alternate between two page types
        video_url = self._search_regex(
            r'<a[^>]+href="([^"]+)"[^>]*><img[^>]+src="[^"]*/play\.gif',
            webpage, 'video URL', default=None)
        if video_url:
            formats = [{
                'url': video_url,
            }]
        else:
            formats = self._parse_html5_media_entries(url, webpage, video_id)[0]['formats']

        title = remove_end(self._html_search_regex(
            r'<title>(.*?)-\s*Vuclip</title>', webpage, 'title').strip(), ' - Video')

        duration = parse_duration(self._html_search_regex(
            r'[(>]([0-9]+:[0-9]+)(?:<span|\))', webpage, 'duration', fatal=False))

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'duration': duration,
        }

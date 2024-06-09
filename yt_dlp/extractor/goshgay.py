import urllib.parse

from .common import InfoExtractor
from ..utils import (
    parse_duration,
)


class GoshgayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?goshgay\.com/video(?P<id>\d+?)($|/)'
    _TEST = {
        'url': 'http://www.goshgay.com/video299069/diesel_sfw_xxx_video',
        'md5': '4b6db9a0a333142eb9f15913142b0ed1',
        'info_dict': {
            'id': '299069',
            'ext': 'flv',
            'title': 'DIESEL SFW XXX Video',
            'thumbnail': r're:^http://.*\.jpg$',
            'duration': 80,
            'age_limit': 18,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<h2>(.*?)<', webpage, 'title')
        duration = parse_duration(self._html_search_regex(
            r'<span class="duration">\s*-?\s*(.*?)</span>',
            webpage, 'duration', fatal=False))

        flashvars = urllib.parse.parse_qs(self._html_search_regex(
            r'<embed.+?id="flash-player-embed".+?flashvars="([^"]+)"',
            webpage, 'flashvars'))
        thumbnail = flashvars.get('url_bigthumb', [None])[0]
        video_url = flashvars['flv_url'][0]

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': 18,
        }

from .common import InfoExtractor
from .jwplatform import JWPlatformIE

from ..utils import (
    unified_strdate,
)


class NormalbootsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?normalboots\.com/video/(?P<id>[0-9a-z-]*)/?$'
    _TEST = {
        'url': 'http://normalboots.com/video/home-alone-games-jontron/',
        'info_dict': {
            'id': 'home-alone-games-jontron',
            'ext': 'mp4',
            'title': 'Home Alone Games - JonTron - NormalBoots',
            'description': 'Jon is late for Christmas. Typical. Thanks to: Paul Ritchey for Co-Writing/Filming: http://www.youtube.com/user/ContinueShow Michael Azzi for Christmas Intro Animation: http://michafrar.tumblr.com/ Jerrod Waters for Christmas Intro Music: http://www.youtube.com/user/xXJerryTerryXx Casey Ormond for ‘Tense Battle Theme’:\xa0http://www.youtube.com/Kiamet/',
            'uploader': 'JonTron',
            'upload_date': '20140125',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['JWPlatform'],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_uploader = self._html_search_regex(
            r'Posted\sby\s<a\shref="[A-Za-z0-9/]*">(?P<uploader>[A-Za-z]*)\s</a>',
            webpage, 'uploader', fatal=False)
        video_upload_date = unified_strdate(self._html_search_regex(
            r'<span style="text-transform:uppercase; font-size:inherit;">[A-Za-z]+, (?P<date>.*)</span>',
            webpage, 'date', fatal=False))

        jwplatform_url = JWPlatformIE._extract_url(webpage)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': jwplatform_url,
            'ie_key': JWPlatformIE.ie_key(),
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': video_uploader,
            'upload_date': video_upload_date,
        }

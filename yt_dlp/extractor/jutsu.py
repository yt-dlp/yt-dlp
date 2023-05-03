from yt_dlp.utils import determine_ext
from .common import InfoExtractor
from pprint import pprint
import urllib

class JutSuIE(InfoExtractor):
    IE_NAME = "jut.su"
    _VALID_URL = r'https:\/\/jut\.su\/([\w-]+)\/([\w-]+)\/?(?P<id>[\w-]+)\.html' # https://regex101.com/r/o9o0qs/1
    REGEX = r"<source\s+src=\"([^\"]+)\"" # https://regex101.com/r/c1dKWt/1

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        source = self._html_search_regex(self.REGEX, webpage, "video links")

        formats = [
            {
                'url': source,
                'ext': determine_ext(source)
            }
        ]

        return {
            'formats': formats,
            'id': self._match_id(url),
            'title': self._html_extract_title(webpage),
        }
        

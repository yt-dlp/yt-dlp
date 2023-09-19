import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html, get_element_by_class, strip_or_none

class MojevideoIE(InfoExtractor):
    _VALID_URL = r'https://www\.mojevideo\.sk/video/'


    def _real_extract(self, url):
        webpage = self._download_webpage(url, 1)

<<<<<<< HEAD
        video_id = re.search(r'vId=(\d+)', webpage).group(1)
        video_expiration = re.search(r"vEx='(\d+)'", webpage).group(1)
        video_hash = re.search(r'vHash=\[([^\]]+)', webpage).group(1).split(",")[0].replace("'", "")


        info = {}
        video_url = "https://cache01.mojevideo.sk/securevideos69/" + video_id + ".mp4?md5=" + video_hash + "&expires=" + video_expiration
        if video_url:
            info = {
                'id' : video_id,
                'url': video_url,

            }
=======
        vId = re.search(r'vId=(\d+)', webpage).group(1)
        vEx = re.search(r"vEx='(\d+)'", webpage).group(1)
        vHash = re.search(r'vHash=\[([^\]]+)', webpage).group(1).split(",")[0].replace("'", "")


        info = {}
        video_url = ""
        if video_url:
            info = {url: video_url}
>>>>>>> parent of 14ca868f2 (update mojevideo extractor)
        if not info:
            raise ExtractorError('No videos found on webpage', expected=True)

        return {
            **info,
        }

import re
from .common import InfoExtractor
from ..utils import ExtractorError


class MojevideoIE(InfoExtractor):
    _VALID_URL = r'https://www\.mojevideo\.sk/video/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://www.mojevideo.sk/video/3d17c/chlapci_dobetonovali_sme_mame_hotovo.html',
        'md5': '384a4628bd2bbd261c5206cf77c38c17',
        'info_dict': {
            'id': '250236',
            'ext': 'mp4',
            'title': 'Chlapci dobetónovali sme, máme hotovo!',
            'description': 'Celodenná práca bola za pár sekúnd fuč. Betón stiekol k susedovi, kam aj zrútil celý plot, ktorý polámal aj tuje. Chlapom zostali iba oči pre plač.'
        }
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, 1)

        video_id = re.search(r'vId=(\d+)', webpage).group(1)
        video_expiration = re.search(r"vEx='(\d+)'", webpage).group(1)
        video_hash = re.search(r'vHash=\[([^\]]+)', webpage).group(1).split(",")[0].replace("'", "")
        video_title = re.search(r'<h1>(.*?)</h1>', webpage).group(1)
        video_description = re.search(r'<div id="video-comment">.*?<p>(.*?)</p>', webpage, re.DOTALL).group(1)

        info = {}
        video_url = "https://cache01.mojevideo.sk/securevideos69/" + video_id + ".mp4?md5=" + video_hash + "&expires=" + video_expiration
        if video_url:
            print(video_id)
            info = {
                'id': video_id,
                'url': video_url,
                'title': video_title,
                'description': video_description
            }
        if not info:
            raise ExtractorError('No videos found on webpage', expected=True)

        return {
            **info,
        }

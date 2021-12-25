# coding: utf-8
from .common import InfoExtractor
from ..utils import url_or_none


# CamHub.cc uses KVS Player hosted inside an iframe.  GenericIE supports KVS Player, but can't
# find the video content due to the iframe.  CamHubIE extracts the iframe src url, then hands it
# off to GenericIE to do the rest.
class CamHubIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?camhub\.cc/videos/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.camhub.cc/videos/533581/syren-de-mer-onlyfans-05-07-2020have-a-happy-safe-holiday5f014e68a220979bdb8cd-source-27660a6a72c095ca/',
        'md5': 'fbe89af4cfb59c8fd9f34a202bb03e32',
        'info_dict': {
            'id': '389508',
            'ext': 'mp4',
            'title': 'Syren De Mer  onlyfans_05-07-2020Have_a_happy_safe_holiday5f014e68a220979bdb8cd_source / Embed плеер',
            'display_id': 'syren-de-mer-onlyfans-05-07-2020have-a-happy-safe-holiday5f014e68a220979bdb8cd-source',
            'thumbnail': 'http://www.camhub.world/contents/videos_screenshots/389000/389508/preview.mp4.jpg',
        }}]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_iframe_url = url_or_none(self._search_regex(
            r'<div[^>]*?class=[\'"].*?embed-wrap.*?[\'"][^>]*>[^<]*<iframe[^>]*?src=[\'"]([^\'"?]*)',
            webpage, 'video iframe url', fatal=True))

        return self.url_result(video_iframe_url, 'Generic')

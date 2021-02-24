from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError


class PhoenixIE(InfoExtractor):
    IE_NAME = 'phoenix.de'
    _VALID_URL = r'''https?://(?:www\.)?phoenix.de/\D+(?P<id>\d+)\.html'''
    _TESTS = [
        {
            'url': 'https://www.phoenix.de/sendungen/dokumentationen/unsere-welt-in-zukunft---stadt-a-1283620.html',
            'md5': '5e765e838aa3531c745a4f5b249ee3e3',
            'info_dict': {
                'id': '0OB4HFc43Ns',
                'ext': 'mp4',
                'title': 'Unsere Welt in Zukunft - Stadt',
                'description': 'md5:9bfb6fd498814538f953b2dcad7ce044',
                'upload_date': '20190912',
                'uploader': 'phoenix',
                'uploader_id': 'phoenix',
            }
        },
        {
            'url': 'https://www.phoenix.de/drohnenangriffe-in-saudi-arabien-a-1286995.html?ref=aktuelles',
            'only_matching': True,
        },
        # an older page: https://www.phoenix.de/sendungen/gespraeche/phoenix-persoenlich/im-dialog-a-177727.html
        # seems to not have an embedded video, even though it's uploaded on youtube: https://www.youtube.com/watch?v=4GxnoUHvOkM
    ]

    def extract_from_json_api(self, video_id, api_url):
        doc = self._download_json(
            api_url, video_id,
            note="Downloading webpage metadata",
            errnote="Failed to load webpage metadata")

        for a in doc["absaetze"]:
            if a["typ"] == "video-youtube":
                return {
                    '_type': 'url_transparent',
                    'id': a["id"],
                    'title': doc["titel"],
                    'url': "https://www.youtube.com/watch?v=%s" % a["id"],
                    'ie_key': 'Youtube',
                }
        raise ExtractorError("No downloadable video found", expected=True)

    def _real_extract(self, url):
        page_id = self._match_id(url)
        api_url = 'https://www.phoenix.de/response/id/%s' % page_id
        return self.extract_from_json_api(page_id, api_url)

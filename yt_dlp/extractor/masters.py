from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import url_or_none


class MastersIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?masters\.com/en_US/watch/[\d]{4}-[\d]{2}-[\d]{2}/(?P<id>[0-9]+)/(.*)\.html'
    _TESTS = [{
        'url': 'https://www.masters.com/en_US/watch/2022-04-07/16493755593805191/sungjae_im_thursday_interview_2022.html',
        'info_dict': {
            'id': '16493755593805191',
            'ext': 'mp4',
            'title': 'Sungjae Im: Thursday Interview 2022',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }]

    _CONTENT_API_URL = "https://www.masters.com/relatedcontent/rest/v2/masters_v1/en/content/masters_v1_{video_id}_en"

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content_resp = self._download_json(self._CONTENT_API_URL.format(video_id=video_id), video_id)
        formats = self._extract_m3u8_formats(content_resp['media']['m3u8'], video_id, 'mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': content_resp["title"],
            'formats': formats,
            'thumbnail': url_or_none(content_resp['images'][0]['large']),
        }

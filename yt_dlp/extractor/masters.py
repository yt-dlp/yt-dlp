from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_strdate,
)


class MastersIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?masters\.com/en_US/watch/(?P<date>\d{4}-\d{2}-\d{2})/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.masters.com/en_US/watch/2022-04-07/16493755593805191/sungjae_im_thursday_interview_2022.html',
        'info_dict': {
            'id': '16493755593805191',
            'ext': 'mp4',
            'title': 'Sungjae Im: Thursday Interview 2022',
            'upload_date': '20220407',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }]

    def _real_extract(self, url):
        video_id, upload_date = self._match_valid_url(url).group('id', 'date')
        content_resp = self._download_json(
            f'https://www.masters.com/relatedcontent/rest/v2/masters_v1/en/content/masters_v1_{video_id}_en',
            video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(traverse_obj(content_resp, ('media', 'm3u8')), video_id, 'mp4')

        thumbnails = [{'id': name, 'url': url} for name, url in traverse_obj(content_resp, ('images', 0), default={}).items()]

        return {
            'id': video_id,
            'title': content_resp.get('title'),
            'formats': formats,
            'subtitles': subtitles,
            'upload_date': unified_strdate(upload_date),
            'thumbnails': thumbnails,
        }

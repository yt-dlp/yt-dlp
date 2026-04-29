import re

from .common import InfoExtractor
from ..utils import parse_duration, parse_iso8601, url_or_none
from ..utils.traversal import traverse_obj


class ParlviewIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aph\.gov\.au/News_and_Events/Watch_Read_Listen/ParlView/video/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.aph.gov.au/News_and_Events/Watch_Read_Listen/ParlView/video/3406614',
        'info_dict': {
            'id': '3406614',
            'ext': 'mp4',
            'title': 'Senate Chamber',
            'description': 'Official Recording of Senate Proceedings from the Australian Parliament',
            'thumbnail': 'https://aphbroadcasting-prod.z01.azurefd.net/vod-storage/vod-logos/SenateParlview06.jpg',
            'upload_date': '20250325',
            'duration': 17999,
            'timestamp': 1742939400,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.aph.gov.au/News_and_Events/Watch_Read_Listen/ParlView/video/SV1394.dv',
        'info_dict': {
            'id': 'SV1394.dv',
            'ext': 'mp4',
            'title': 'Senate Select Committee on Uranium Mining and Milling [Part 1]',
            'description': 'Official Recording of Senate Committee Proceedings from the Australian Parliament',
            'thumbnail': 'https://aphbroadcasting-prod.z01.azurefd.net/vod-storage/vod-logos/CommitteeThumbnail06.jpg',
            'upload_date': '19960822',
            'duration': 14765,
            'timestamp': 840754200,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_details = self._download_json(
            f'https://vodapi.aph.gov.au/api/search/parlview/{video_id}', video_id)['videoDetails']

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_details['files']['file']['url'], video_id, 'mp4')

        DURATION_RE = re.compile(r'(?P<duration>\d+:\d+:\d+):\d+')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_details, {
                'title': (('parlViewTitle', 'title'), {str}, any),
                'description': ('parlViewDescription', {str}),
                'duration': ('files', 'file', 'duration', {DURATION_RE.fullmatch}, 'duration', {parse_duration}),
                'timestamp': ('recordingFrom', {parse_iso8601}),
                'thumbnail': ('thumbUrl', {url_or_none}),
            }),
        }

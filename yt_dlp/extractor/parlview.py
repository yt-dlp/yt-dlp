from yt_dlp.utils.traversal import (
    traverse_obj,
)

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    join_nonempty,
    parse_duration,
    unified_timestamp,
    url_or_none,
)


class ParlviewIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'https?://(?:www\.)?aph\.gov\.au/(?:.*/)?video/(?P<id>\d{5,7})'
    _TESTS = [{
        'url': 'https://www.aph.gov.au/News_and_Events/Watch_Read_Listen/ParlView/video/3406614',
        'info_dict': {
            'id': '3406614',
            'ext': 'mp4',
            'title': 'Senate Chamber',
            'description': 'Official Recording of Senate Proceedings from the Australian Parliament',
            'thumbnail': 'https://aphbroadcasting-prod.z01.azurefd.net/vod-storage/vod-logos/SenateParlview06.jpg',
            'upload_date': '20250326',
            'uploader': 'Australian Parliament House',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.aph.gov.au/News_and_Events/Watch_Read_Listen/ParlView/video/3406614',
        'only_matching': True,
    }]
    _API_URL = 'https://vodapi.aph.gov.au/api/search/parlview/%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_data = self._download_json(self._API_URL % video_id, video_id)
        if not api_data:
            self.raise_no_formats('Failed to retrieve API data')

        video_details = traverse_obj(api_data, ('videoDetails', {dict}))
        if not video_details:
            raise ExtractorError('API request was not successful', expected=traverse_obj(api_data, ('wasSuccessful', {bool})) is False)

        m3u8_url = traverse_obj(video_details, ('files', 'file', 'url', {str}))
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', 'm3u8_native')

        return {
            'id': video_id,
            'formats': formats,
            'uploader': 'Australian Parliament House',
            ** traverse_obj(video_details, {
                'title': (('parlViewTitle', 'title'), {str}, any),
                'description': ('parlViewDescription', {str}),
                'duration': ('files', 'file', 'duration', {lambda s: ':'.join((s or '').split(':')[:3])}, {parse_duration}),
                'timestamp': ('recordingFrom', {unified_timestamp}),
                'thumbnail': ('thumbUrl', {url_or_none}),
                'series': (None, {lambda vd: join_nonempty('eventGroup', 'eventSubGroup', delim=' - ', from_dict=vd)}),
            }),
        }

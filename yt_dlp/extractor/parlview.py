from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
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

        if not api_data.get('wasSuccessful'):
            self.raise_no_formats('API request was not successful')

        video_details = api_data.get('videoDetails')
        if not video_details:
            self.raise_no_formats('No video details found')

        files_data = video_details.get('files')
        if not files_data:
            self.raise_no_formats('No files data found')

        file_info = files_data.get('file')
        if not file_info:
            self.raise_no_formats('No file information found')

        m3u8_url = file_info.get('url')
        if not m3u8_url:
            self.raise_no_formats('No M3U8 URL found')

        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', 'm3u8_native')

        # Parse duration from duration string (format: "HH:MM:SS:FF")
        duration_str = file_info.get('duration')
        duration = None
        if duration_str:
            # Convert "HH:MM:SS:FF" to seconds (ignoring frames)
            try:
                time_parts = duration_str.split(':')
                if len(time_parts) >= 3:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    seconds = int(time_parts[2])
                    duration = hours * 3600 + minutes * 60 + seconds
            except (ValueError, IndexError):
                pass

        # Parse upload date from recordingFrom
        upload_date = None
        recording_from = video_details.get('recordingFrom')
        if recording_from:
            upload_date = unified_timestamp(recording_from)

        return {
            'id': video_id,
            'title': video_details.get('parlViewTitle') or video_details.get('title'),
            'description': video_details.get('parlViewDescription'),
            'formats': formats,
            'duration': duration,
            'timestamp': upload_date,
            'uploader': 'Australian Parliament House',
            'thumbnail': video_details.get('thumbUrl'),
            'series': f"{video_details.get('eventGroup')} - {video_details.get('eventSubGroup')}" if video_details.get('eventGroup') and video_details.get('eventSubGroup') else None,
        }

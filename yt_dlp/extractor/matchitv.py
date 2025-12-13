from .common import InfoExtractor
from ..utils import unified_strdate


class MatchiTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?matchi\.tv/watch\?s=(?P<id>[A-Za-z0-9_-]+)'
    _TESTS = [{
        'url': 'https://matchi.tv/watch?s=pNOyrdC8Bmu',
        'info_dict': {
            'id': 'pNOyrdC8Bmu',
            'ext': 'mp4',
            'title': str,
            'thumbnail': 'https://thumbnails.padelgo.tv/pNOyrdC8Bmu.jpg',
            'upload_date': str,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Download webpage to extract metadata
        webpage = self._download_webpage(url, video_id)

        # Extract courtDescription and startDateTime
        court_description = self._search_regex(
            r'"courtDescription"\s*:\s*"([^"]+)"',
            webpage, 'court description')
        start_date_time = self._search_regex(
            r'"startDateTime"\s*:\s*"([^"]+)"',
            webpage, 'start date time')

        # Build title from courtDescription and startDateTime
        title = f'{court_description} {start_date_time}'

        # Parse upload_date from startDateTime (format: YYYYMMDD)
        upload_date = unified_strdate(start_date_time)

        # Construct M3U8 URL directly from video ID
        m3u8_url = f'https://streams.padelgo.tv/v2/streams/m3u8/{video_id}/anonymous/playlist.m3u8'

        # Construct thumbnail URL directly from video ID
        thumbnail = f'https://thumbnails.padelgo.tv/{video_id}.jpg'

        # Extract M3U8 formats
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'formats': formats,
        }

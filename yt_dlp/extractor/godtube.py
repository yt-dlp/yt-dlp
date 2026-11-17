from .common import InfoExtractor
from ..utils import (
    parse_duration,
    parse_iso8601,
)


class GodTubeIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?godtube\.com/watch/\?v=(?P<id>[\da-zA-Z]+)'
    _TESTS = [
        {
            'url': 'https://www.godtube.com/watch/?v=0C0CNNNU',
            'md5': '77108c1e4ab58f48031101a1a2119789',
            'info_dict': {
                'id': '0C0CNNNU',
                'ext': 'mp4',
                'title': 'Woman at the well.',
                'duration': 159,
                'timestamp': 1205712000,
                'uploader': 'beverlybmusic',
                'upload_date': '20080317',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        config = self._download_xml(
            f'http://www.godtube.com/resource/mediaplayer/{video_id.lower()}.xml',
            video_id, 'Downloading player config XML')

        video_url = config.find('file').text
        uploader = config.find('author').text
        timestamp = parse_iso8601(config.find('date').text)
        duration = parse_duration(config.find('duration').text)
        thumbnail = config.find('image').text

        media = self._download_xml(
            f'http://www.godtube.com/media/xml/?v={video_id}', video_id, 'Downloading media XML')

        title = media.find('title').text

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader': uploader,
            'duration': duration,
        }

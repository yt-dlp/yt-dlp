from .common import InfoExtractor
from ..utils import traverse_obj
import json
import time
import calendar


class LivestreamfailsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?livestreamfails\.com/clip/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://livestreamfails.com/clip/139200',
        'md5': '8a03aea1a46e94a05af6410337463102',
        'info_dict': {
            'id': '139200',
            'ext': 'mp4',
            'display_id': 'ConcernedLitigiousSalmonPeteZaroll-O8yo9W2L8OZEKhV2',
            'title': 'Streamer jumps off a trampoline at full speed',
            'creator': 'paradeev1ch',
            'thumbnail': r're:^https?://.*\..*$',
            'timestamp': 1656271785,
            'upload_date': '20220626',
        }
    }]

    def _real_extract(self, url):
        result = {}
        result['id'] = self._match_id(url)

        # https://livestreamfails.com/clip/id uses https://api.livestreamfails.com/clip/ to fetch the video metadata
        # Use the same endpoint here to avoid loading and parsing the provided page (which requires JS)
        apiResponse = json.loads(self._download_webpage('https://api.livestreamfails.com/clip/' + result['id'], result['id']))

        # Twitch ID of clip
        result['display_id'] = apiResponse.get('sourceId')

        # Get the input timestamp (test case gives 2022-06-26T19:29:45.515Z)
        result['timestamp'] = apiResponse.get('createdAt')
        if(result.get('timestamp')):
            # Parse it into a struct_time
            result['timestamp'] = time.strptime(result['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
            # Convert the struct_time to a UNIX timestamp while ignoring the local timezone attached by time.strptime()
            result['timestamp'] = calendar.timegm(result['timestamp'])

        # Other fields
        result['url'] = 'https://livestreamfails-video-prod.b-cdn.net/video/' + apiResponse.get('videoId')
        result['title'] = apiResponse.get('label')
        result['creator'] = traverse_obj(apiResponse, ('streamer', 'label'))
        result['thumbnail'] = 'https://livestreamfails-image-prod.b-cdn.net/image/' + apiResponse.get('imageId')

        return result

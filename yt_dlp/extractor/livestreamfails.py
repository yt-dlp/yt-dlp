from .common import InfoExtractor
from ..utils import format_field, traverse_obj, unified_timestamp


class LivestreamfailsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?livestreamfails\.com/(?:clip|post)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://livestreamfails.com/clip/139200',
        'md5': '8a03aea1a46e94a05af6410337463102',
        'info_dict': {
            'id': '139200',
            'ext': 'mp4',
            'display_id': 'ConcernedLitigiousSalmonPeteZaroll-O8yo9W2L8OZEKhV2',
            'title': 'Streamer jumps off a trampoline at full speed',
            'creator': 'paradeev1ch',
            'thumbnail': r're:^https?://.+',
            'timestamp': 1656271785,
            'upload_date': '20220626',
        }
    }, {
        'url': 'https://livestreamfails.com/post/139200',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_response = self._download_json(f'https://api.livestreamfails.com/clip/{video_id}', video_id)

        return {
            'id': video_id,
            'display_id': api_response.get('sourceId'),
            'timestamp': unified_timestamp(api_response.get('createdAt')),
            'url': f'https://livestreamfails-video-prod.b-cdn.net/video/{api_response["videoId"]}',
            'title': api_response.get('label'),
            'creator': traverse_obj(api_response, ('streamer', 'label')),
            'thumbnail': format_field(api_response, 'imageId', 'https://livestreamfails-image-prod.b-cdn.net/image/%s')
        }

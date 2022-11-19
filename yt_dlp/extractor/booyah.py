from .common import InfoExtractor
from ..utils import int_or_none, str_or_none, traverse_obj


class BooyahBaseIE(InfoExtractor):
    _BOOYAH_SESSION_KEY = None

    def _real_initialize(self):
        BooyahBaseIE._BOOYAH_SESSION_KEY = self._request_webpage(
            'https://booyah.live/api/v3/auths/sessions', None, data=b'').getheader('booyah-session-key')

    def _get_comments(self, video_id):
        comment_json = self._download_json(
            f'https://booyah.live/api/v3/playbacks/{video_id}/comments/tops', video_id,
            headers={'Booyah-Session-Key': self._BOOYAH_SESSION_KEY}, fatal=False) or {}

        return [{
            'id': comment.get('comment_id'),
            'author': comment.get('from_nickname'),
            'author_id': comment.get('from_uid'),
            'author_thumbnail': comment.get('from_thumbnail'),
            'text': comment.get('content'),
            'timestamp': comment.get('create_time'),
            'like_count': comment.get('like_cnt'),
        } for comment in comment_json.get('comment_list') or ()]


class BooyahClipsIE(BooyahBaseIE):
    _VALID_URL = r'https?://booyah.live/clips/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://booyah.live/clips/13887261322952306617',
        'info_dict': {
            'id': '13887261322952306617',
            'ext': 'mp4',
            'view_count': int,
            'duration': 30,
            'channel_id': 90565760,
            'like_count': int,
            'title': 'Cayendo con estilo 😎',
            'uploader': '♡LɪꜱGΛ​MER​',
            'comment_count': int,
            'uploader_id': '90565760',
            'thumbnail': 'https://resmambet-a.akamaihd.net/mambet-storage/Clip/90565760/90565760-27204374-fba0-409d-9d7b-63a48b5c0e75.jpg',
            'upload_date': '20220617',
            'timestamp': 1655490556,
            'modified_timestamp': 1655490556,
            'modified_date': '20220617',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(
            f'https://booyah.live/api/v3/playbacks/{video_id}', video_id,
            headers={'Booyah-Session-key': self._BOOYAH_SESSION_KEY})

        formats = []
        for video_data in json_data['playback']['endpoint_list']:
            formats.extend(({
                'url': video_data.get('stream_url'),
                'ext': 'mp4',
                'height': video_data.get('resolution'),
            }, {
                'url': video_data.get('download_url'),
                'ext': 'mp4',
                'format_note': 'Watermarked',
                'height': video_data.get('resolution'),
                'preference': -10,
            }))

        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('playback', 'name')),
            'thumbnail': traverse_obj(json_data, ('playback', 'thumbnail_url')),
            'formats': formats,
            'view_count': traverse_obj(json_data, ('playback', 'views')),
            'like_count': traverse_obj(json_data, ('playback', 'likes')),
            'duration': traverse_obj(json_data, ('playback', 'duration')),
            'comment_count': traverse_obj(json_data, ('playback', 'comment_cnt')),
            'channel_id': traverse_obj(json_data, ('playback', 'channel_id')),
            'uploader': traverse_obj(json_data, ('user', 'nickname')),
            'uploader_id': str_or_none(traverse_obj(json_data, ('user', 'uid'))),
            'modified_timestamp': int_or_none(traverse_obj(json_data, ('playback', 'update_time_ms')), 1000),
            'timestamp': int_or_none(traverse_obj(json_data, ('playback', 'create_time_ms')), 1000),
            '__post_extractor': self.extract_comments(video_id, self._get_comments(video_id)),
        }

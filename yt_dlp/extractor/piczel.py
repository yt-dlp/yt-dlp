from .common import InfoExtractor
from ..utils import (
    UserNotLive,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_strdate,
)


class PiczelIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:www\.)?piczel\.tv/watch/(?P<id>[^/]+)',
    ]
    _TESTS = [{
        'url': 'https://piczel.tv/watch/Crittermatic',
        'info_dict': {
            'id': '10558',
            'formats': list,
            'title': 'Crittermatic animation streams',
            'age_limit': int,
            'uploader': 'Crittermatic',
            'uploader_id': 10649,
            'upload_date': '20260307',
            'ext': 'mp4',
            'description': 'More over on https://www.patreon.com/Crittermatic',
            'tags': list,
            'concurrent_view_count': int,
            'channel_follower_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://piczel.tv/watch/Mangrover',
        'info_dict': {
            'id': '140239',
            'formats': list,
            'title': 'Stream',
            'age_limit': int,
            'uploader': 'Mangrover',
            'uploader_id': 146061,
            'ext': 'mp4',
            'description': None,
            'tags': list,
            'concurrent_view_count': int,
            'channel_follower_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'HTTP Error 404: Not Found',
    }]

    def _real_extract(self, url):
        username = self._match_id(url)

        meta = self._download_json(f'https://api.piczel.tv/streams/{username}', username)
        main_stream = traverse_obj(meta, ('data', lambda _, v: v.get('username') == username), get_all=False)

        if not main_stream.get('live'):
            raise UserNotLive(msg=f'{username} is not live.')
        elif traverse_obj(main_stream, ('is_private'), ('isPrivate?')):
            self.raise_login_required('User is in private room')

        stream_id = main_stream.get('id')
        formats = self._extract_m3u8_formats(f'https://boston.piczel.tv/live/{stream_id}/llhls.m3u8', stream_id)

        return {
            **traverse_obj(main_stream, ({
                'id': ('id', {str_or_none}),
                'title': ('title', {str_or_none}),
                'description': ('description', {str_or_none}),
                'concurrent_view_count': ('viewers', {int_or_none}),
                'channel_follower_count': ('follower_count', {int_or_none}),
                'tags': ('tags', ..., 'title'),
                'uploader_id': ('user', 'id', {int_or_none}),
                'uploader': ('username', {str_or_none}),
                'upload_date': ('live_since', {unified_strdate}),
            })),
            'formats': formats,
            'age_limit': 18 if main_stream.get('adult') else 0,
        }

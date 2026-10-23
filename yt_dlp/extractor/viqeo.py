from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    url_or_none,
)


class ViqeoIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'''(?x)
                        (?:
                            viqeo:|
                            https?://cdn\.viqeo\.tv/embed/*\?.*?\bvid=|
                            https?://api\.viqeo\.tv/v\d+/data/startup?.*?\bvideo(?:%5B%5D|\[\])=
                        )
                        (?P<id>[\da-f]+)
                    '''
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//cdn\.viqeo\.tv/embed/*\?.*?\bvid=[\da-f]+.*?)\1']
    _TESTS = [{
        'url': 'https://cdn.viqeo.tv/embed/?vid=cde96f09d25f39bee837',
        'md5': 'a169dd1a6426b350dca4296226f21e76',
        'info_dict': {
            'id': 'cde96f09d25f39bee837',
            'ext': 'mp4',
            'title': 'cde96f09d25f39bee837',
            'thumbnail': r're:https?://.+\.jpg',
            'duration': 76,
        },
    }, {
        'url': 'viqeo:cde96f09d25f39bee837',
        'only_matching': True,
    }, {
        'url': 'https://api.viqeo.tv/v1/data/startup?video%5B%5D=71bbec412ade45c3216c&profile=112',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://viqeo.tv/',
        'info_dict': {
            'id': 'viqeo',
            'title': 'Viqeo video platform',
            'age_limit': 0,
            'description': 'md5:e8e06e20df92ed66febeaef2533a0d5d',
            'thumbnail': r're:https?://static\.tildacdn\.com/.+\.png',
            'timestamp': 1751479769,
            'upload_date': '20250702',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            f'https://cdn.viqeo.tv/embed/?vid={video_id}', video_id)

        data = self._parse_json(
            self._search_regex(
                r'SLOT_DATA\s*=\s*({.+?})\s*;', webpage, 'slot data'),
            video_id)

        formats = []
        thumbnails = []
        for media_file in data['mediaFiles']:
            if not isinstance(media_file, dict):
                continue
            media_url = url_or_none(media_file.get('url'))
            if not media_url or not media_url.startswith(('http', '//')):
                continue
            media_type = str_or_none(media_file.get('type'))
            if not media_type:
                continue
            media_kind = media_type.split('/')[0].lower()
            f = {
                'url': media_url,
                'width': int_or_none(media_file.get('width')),
                'height': int_or_none(media_file.get('height')),
            }
            format_id = str_or_none(media_file.get('quality'))
            if media_kind == 'image':
                f['id'] = format_id
                thumbnails.append(f)
            elif media_kind in ('video', 'audio'):
                is_audio = media_kind == 'audio'
                f.update({
                    'format_id': 'audio' if is_audio else format_id,
                    'fps': int_or_none(media_file.get('fps')),
                    'vcodec': 'none' if is_audio else None,
                })
                formats.append(f)

        duration = int_or_none(data.get('duration'))

        return {
            'id': video_id,
            'title': video_id,
            'duration': duration,
            'thumbnails': thumbnails,
            'formats': formats,
        }

import functools

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    parse_iso8601,
    qualities,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class PornboxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornbox\.com/application/watch-page/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://pornbox.com/application/watch-page/212108',
        'md5': '3ff6b6e206f263be4c5e987a3162ac6e',
        'info_dict': {
            'id': '212108',
            'ext': 'mp4',
            'title': 'md5:ececc5c6e6c9dd35d290c45fed05fd49',
            'uploader': 'Lily Strong',
            'timestamp': 1665871200,
            'upload_date': '20221015',
            'age_limit': 18,
            'availability': 'needs_auth',
            'duration': 1505,
            'cast': ['Lily Strong', 'John Strong'],
            'tags': 'count:11',
            'description': 'md5:589c7f33e183aa8aa939537300efb859',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$',
        },
    }, {
        'url': 'https://pornbox.com/application/watch-page/216045',
        'info_dict': {
            'id': '216045',
            'title': 'md5:3e48528e73a9a2b12f7a2772ed0b26a2',
            'description': 'md5:3e631dcaac029f15ed434e402d1b06c7',
            'uploader': 'VK Studio',
            'timestamp': 1618264800,
            'upload_date': '20210412',
            'age_limit': 18,
            'availability': 'premium_only',
            'duration': 2710,
            'cast': 'count:3',
            'tags': 'count:29',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$',
            'subtitles': 'count:6',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'You are either not logged in or do not have access to this scene',
            'No video formats found', 'Requested format is not available'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        public_data = self._download_json(f'https://pornbox.com/contents/{video_id}', video_id)

        subtitles = {country_code: [{
            'url': f'https://pornbox.com/contents/{video_id}/subtitles/{country_code}',
            'ext': 'srt',
        }] for country_code in traverse_obj(public_data, ('subtitles', ..., {str}))}

        is_free_scene = traverse_obj(
            public_data, ('price', 'is_available_for_free', {bool}), default=False)

        metadata = {
            'id': video_id,
            **traverse_obj(public_data, {
                'title': ('scene_name', {str.strip}),
                'description': ('small_description', {str.strip}),
                'uploader': 'studio',
                'duration': ('runtime', {parse_duration}),
                'cast': (('models', 'male_models'), ..., 'model_name'),
                'thumbnail': ('player_poster', {url_or_none}),
                'tags': ('niches', ..., 'niche'),
            }),
            'age_limit': 18,
            'timestamp': parse_iso8601(traverse_obj(
                public_data, ('studios', 'release_date'), 'publish_date')),
            'availability': self._availability(needs_auth=True, needs_premium=not is_free_scene),
            'subtitles': subtitles,
        }

        if not public_data.get('is_purchased') or not is_free_scene:
            self.raise_login_required(
                'You are either not logged in or do not have access to this scene', metadata_available=True)
            return metadata

        media_id = traverse_obj(public_data, (
            'medias', lambda _, v: v['title'] == 'Full video', 'media_id', {int}), get_all=False)
        if not media_id:
            self.raise_no_formats('Could not find stream id', video_id=video_id)

        stream_data = self._download_json(
            f'https://pornbox.com/media/{media_id}/stream', video_id=video_id, note='Getting manifest urls')

        get_quality = qualities(['web', 'vga', 'hd', '1080p', '4k', '8k'])
        metadata['formats'] = traverse_obj(stream_data, ('qualities', lambda _, v: v['src'], {
            'url': 'src',
            'vbr': ('bitrate', {functools.partial(int_or_none, scale=1000)}),
            'format_id': ('quality', {str_or_none}),
            'quality': ('quality', {get_quality}),
            'width': ('size', {lambda x: int(x[:-1])}),
        }))

        return metadata

from .common import InfoExtractor
from ..compat import functools
from ..utils import (
    parse_duration,
    traverse_obj,
    str_or_none,
    int_or_none,
    strip_or_none,
    parse_iso8601,
    qualities
)


class PornboxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornbox\.com/application/watch-page/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://pornbox.com/application/watch-page/426095',
        'md5': '0cc35f4d4300bc8e0496aef2a9ec20b9',
        'info_dict': {
            'id': '426095',
            'ext': 'mp4',
            'title': 'md5:96b05922d74be2be939cf247294f26bd',
            'uploader': 'Giorgio Grandi',
            'timestamp': 1686088800,
            'upload_date': '20230606',
            'age_limit': 18,
            'availability': 'needs_auth',
            'duration': 1767,
            'cast': ['Tina Kay', 'Neeo', 'Mr. Anderson', 'Thomas Lee', 'Brian Ragnastone', 'Rycky Optimal'],
            'tags': 'count:37',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$'
        }
    }, {
        'url': 'https://pornbox.com/application/watch-page/216045',
        'md5': '56cb78bb1d8e0d2dad8b75c278c20098',
        'info_dict': {
            'id': '216045',
            'ext': 'mp4',
            'title': 'md5:3e48528e73a9a2b12f7a2772ed0b26a2',
            'description': 'md5:3e631dcaac029f15ed434e402d1b06c7',
            'uploader': 'VK Studio',
            'timestamp': 1618264800,
            'upload_date': '20210412',
            'age_limit': 18,
            'availability': 'premium_only',
            'duration': 2710,
            'cast': ['Bella Grey', 'Oliver Trunk'],
            'tags': 'count:29',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$',
            'subtitles': 'count:6'
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True
        },
        'skip': 'Only for subscribers'
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        public_data = self._download_json(f'https://pornbox.com/contents/{video_id}', video_id)

        date = traverse_obj(public_data, ('studios', 'release_date'), 'publish_date')
        cast = traverse_obj(public_data, (('models', 'male_models'), ..., 'model_name'))

        subtitles = {country_code: [{
            'url': f'https://pornbox.com/contents/{video_id}/subtitles/{country_code}',
            'ext': 'srt'
        }] for country_code in traverse_obj(public_data, ('subtitles', ...))}

        metadata = {
            'id': video_id,
            'title': public_data.get('scene_name').strip(),
            'description': strip_or_none(public_data.get('small_description')),
            'uploader': public_data.get('studio'),
            'timestamp': parse_iso8601(date),
            'age_limit': 18,
            'duration': parse_duration(public_data.get('runtime')),
            'cast': cast,
            'tags': traverse_obj(public_data, ('niches', ..., 'niche'), default=[]),
            'thumbnail': str_or_none(public_data.get('player_poster')),
            'subtitles': subtitles,
        }

        is_free_scene = traverse_obj(public_data, ('price', 'is_available_for_free'), default=False, expected_type=bool)
        if is_free_scene:
            metadata['availability'] = 'needs_auth'
        else:
            metadata['availability'] = 'premium_only'

        if (not public_data.get('is_purchased')) or (not is_free_scene):
            self.raise_login_required('You are either not logged in or do not have access to this scene',
                                      metadata_available=True, method='cookies')
            return metadata

        media_id = traverse_obj(public_data, (
            'medias', lambda _, v: v['title'] == 'Full video', 'media_id', {int}), get_all=False)
        if not media_id:
            self.raise_no_formats('Could not find stream id', video_id=video_id)

        stream_data = self._download_json(
            f'https://pornbox.com/media/{media_id}/stream', video_id=video_id, note='Getting manifest urls')

        get_quality = qualities(['web', 'vga', 'hd', '1080p', '4k', '8k'])
        metadata['formats'] = [traverse_obj(q, {
            'url': 'src',
            'vbr': ('bitrate', {functools.partial(int_or_none, scale=1000)}),
            'format_id': ('quality', {str_or_none}),
            'quality': ('quality', {get_quality}),
            'width': ('size', {lambda x: int(x[:-1])})
        }) for q in stream_data.get('qualities') or []]

        return metadata

# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    try_get,
)


class RedGifsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|thumbs2?)\.)?redgifs\.com/(?:watch/)?(?P<id>[^-/?#\.]+)'
    _FORMATS = {
        'gif': 250,
        'sd': 480,
        'hd': None,
    }
    _TESTS = [{
        'url': 'https://www.redgifs.com/watch/squeakyhelplesswisent',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
        }
    }, {
        'url': 'https://thumbs2.redgifs.com/SqueakyHelplessWisent-mobile.mp4#t=0',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).lower()

        video_info = self._download_json(
            'https://api.redgifs.com/v2/gifs/%s' % video_id,
            video_id, 'Downloading video info')
        if 'error' in video_info:
            raise ExtractorError(f'RedGifs said: {video_info["error"]}', expected=True)

        gif = video_info['gif']
        urls = gif['urls']

        quality = qualities(tuple(self._FORMATS.keys()))

        orig_height = int_or_none(gif.get('height'))
        aspect_ratio = try_get(gif, lambda x: orig_height / x['width'])

        formats = []
        for format_id, height in self._FORMATS.items():
            video_url = urls.get(format_id)
            if not video_url:
                continue
            height = min(orig_height, height or orig_height)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': height * aspect_ratio if aspect_ratio else None,
                'height': height,
                'quality': quality(format_id),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': ' '.join(gif.get('tags') or []) or 'RedGifs',
            'timestamp': int_or_none(gif.get('createDate')),
            'uploader': gif.get('userName'),
            'duration': int_or_none(gif.get('duration')),
            'view_count': int_or_none(gif.get('views')),
            'like_count': int_or_none(gif.get('likes')),
            'categories': gif.get('tags') or [],
            'age_limit': 18,
            'formats': formats,
        }

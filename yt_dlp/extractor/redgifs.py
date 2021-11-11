# coding: utf-8

from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
)


class RedGifsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|thumbs2?)\.)?redgifs\.com/(?:watch/)?(?P<id>[^-/?#\.]+)'
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
            raise ExtractorError('RedGifs said: ' + video_info['error'], expected=True)

        gif = video_info['gif']
        urls = gif['urls']

        # redgifs do not have title
        title = ' '.join(gif.get('tags')) or 'RedGifs'
        timestamp = int_or_none(gif.get('createDate'))
        uploader = gif.get('userName')
        view_count = int_or_none(gif.get('views'))
        like_count = int_or_none(gif.get('likes'))
        age_limit = 18

        orig_width = int_or_none(gif.get('width'))
        orig_height = int_or_none(gif.get('height'))

        duration = int_or_none(gif.get('duration'))

        categories = gif.get('tags') or []

        FORMATS = ('gif', 'sd', 'hd')
        quality = qualities(FORMATS)

        formats = []
        for format_id in FORMATS:
            video_url = urls.get(format_id)
            if not video_url:
                continue
            if format_id == 'gif':
                max_height = 250
            elif format_id == 'sd':
                max_height = 480
            else:
                max_height = orig_height

            height = orig_height if max_height > orig_height else max_height
            width = orig_width if height == orig_height else int(height / orig_height * orig_width)

            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': width,
                'height': height,
                'quality': quality(format_id),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'uploader': uploader,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'categories': categories,
            'age_limit': age_limit,
            'formats': formats,
        }

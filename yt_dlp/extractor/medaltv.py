# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    format_field,
    float_or_none,
    int_or_none,
    str_or_none,
    try_get,
)


class MedalTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?medal\.tv/clips/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://medal.tv/clips/2mA60jWAGQCBH',
        'md5': '7b07b064331b1cf9e8e5c52a06ae68fa',
        'info_dict': {
            'id': '2mA60jWAGQCBH',
            'ext': 'mp4',
            'title': 'Quad Cold',
            'description': 'Medal,https://medal.tv/desktop/',
            'uploader': 'MowgliSB',
            'timestamp': 1603165266,
            'upload_date': '20201020',
            'uploader_id': '10619174',
        }
    }, {
        'url': 'https://medal.tv/clips/2um24TWdty0NA',
        'md5': 'b6dc76b78195fff0b4f8bf4a33ec2148',
        'info_dict': {
            'id': '2um24TWdty0NA',
            'ext': 'mp4',
            'title': 'u tk me i tk u bigger',
            'description': 'Medal,https://medal.tv/desktop/',
            'uploader': 'Mimicc',
            'timestamp': 1605580939,
            'upload_date': '20201117',
            'uploader_id': '5156321',
        }
    }, {
        'url': 'https://medal.tv/clips/37rMeFpryCC-9',
        'only_matching': True,
    }, {
        'url': 'https://medal.tv/clips/2WRj40tpY_EU9',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        hydration_data = self._parse_json(self._search_regex(
            r'<script[^>]*>\s*(?:var\s*)?hydrationData\s*=\s*({.+?})\s*</script>',
            webpage, 'hydration data', default='{}'), video_id)

        clip = try_get(
            hydration_data, lambda x: x['clips'][video_id], dict) or {}
        if not clip:
            raise ExtractorError(
                'Could not find video information.', video_id=video_id)

        title = clip['contentTitle']

        source_width = int_or_none(clip.get('sourceWidth'))
        source_height = int_or_none(clip.get('sourceHeight'))

        aspect_ratio = source_width / source_height if source_width and source_height else 16 / 9

        def add_item(container, item_url, height, id_key='format_id', item_id=None):
            item_id = item_id or '%dp' % height
            if item_id not in item_url:
                return
            width = int(round(aspect_ratio * height))
            container.append({
                'url': item_url,
                id_key: item_id,
                'width': width,
                'height': height
            })

        formats = []
        thumbnails = []
        for k, v in clip.items():
            if not (v and isinstance(v, compat_str)):
                continue
            mobj = re.match(r'(contentUrl|thumbnail)(?:(\d+)p)?$', k)
            if not mobj:
                continue
            prefix = mobj.group(1)
            height = int_or_none(mobj.group(2))
            if prefix == 'contentUrl':
                add_item(
                    formats, v, height or source_height,
                    item_id=None if height else 'source')
            elif prefix == 'thumbnail':
                add_item(thumbnails, v, height, 'id')

        error = clip.get('error')
        if not formats and error:
            if error == 404:
                self.raise_no_formats(
                    'That clip does not exist.',
                    expected=True, video_id=video_id)
            else:
                self.raise_no_formats(
                    'An unknown error occurred ({0}).'.format(error),
                    video_id=video_id)

        self._sort_formats(formats)

        # Necessary because the id of the author is not known in advance.
        # Won't raise an issue if no profile can be found as this is optional.
        author = try_get(
            hydration_data, lambda x: list(x['profiles'].values())[0], dict) or {}
        author_id = str_or_none(author.get('id'))
        author_url = format_field(author_id, template='https://medal.tv/users/%s')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnails': thumbnails,
            'description': clip.get('contentDescription'),
            'uploader': author.get('displayName'),
            'timestamp': float_or_none(clip.get('created'), 1000),
            'uploader_id': author_id,
            'uploader_url': author_url,
            'duration': int_or_none(clip.get('videoLengthSeconds')),
            'view_count': int_or_none(clip.get('views')),
            'like_count': int_or_none(clip.get('likes')),
            'comment_count': int_or_none(clip.get('comments')),
        }

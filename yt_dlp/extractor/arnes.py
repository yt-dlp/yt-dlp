# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    format_field,
    float_or_none,
    int_or_none,
    parse_iso8601,
    remove_start,
)


class ArnesIE(InfoExtractor):
    IE_NAME = 'video.arnes.si'
    IE_DESC = 'Arnes Video'
    _VALID_URL = r'https?://video\.arnes\.si/(?:[a-z]{2}/)?(?:watch|embed|api/(?:asset|public/video))/(?P<id>[0-9a-zA-Z]{12})'
    _TESTS = [{
        'url': 'https://video.arnes.si/watch/a1qrWTOQfVoU?t=10',
        'md5': '4d0f4d0a03571b33e1efac25fd4a065d',
        'info_dict': {
            'id': 'a1qrWTOQfVoU',
            'ext': 'mp4',
            'title': 'Linearna neodvisnost, definicija',
            'description': 'Linearna neodvisnost, definicija',
            'license': 'PRIVATE',
            'creator': 'Polona Oblak',
            'timestamp': 1585063725,
            'upload_date': '20200324',
            'channel': 'Polona Oblak',
            'channel_id': 'q6pc04hw24cj',
            'channel_url': 'https://video.arnes.si/?channel=q6pc04hw24cj',
            'duration': 596.75,
            'view_count': int,
            'tags': ['linearna_algebra'],
            'start_time': 10,
        }
    }, {
        'url': 'https://video.arnes.si/api/asset/s1YjnV7hadlC/play.mp4',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/embed/s1YjnV7hadlC',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/en/watch/s1YjnV7hadlC',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/embed/s1YjnV7hadlC?t=123&hideRelated=1',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/api/public/video/s1YjnV7hadlC',
        'only_matching': True,
    }]
    _BASE_URL = 'https://video.arnes.si'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            self._BASE_URL + '/api/public/video/' + video_id, video_id)['data']
        title = video['title']

        formats = []
        for media in (video.get('media') or []):
            media_url = media.get('url')
            if not media_url:
                continue
            formats.append({
                'url': self._BASE_URL + media_url,
                'format_id': remove_start(media.get('format'), 'FORMAT_'),
                'format_note': media.get('formatTranslation'),
                'width': int_or_none(media.get('width')),
                'height': int_or_none(media.get('height')),
            })
        self._sort_formats(formats)

        channel = video.get('channel') or {}
        channel_id = channel.get('url')
        thumbnail = video.get('thumbnailUrl')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': self._BASE_URL + thumbnail,
            'description': video.get('description'),
            'license': video.get('license'),
            'creator': video.get('author'),
            'timestamp': parse_iso8601(video.get('creationTime')),
            'channel': channel.get('name'),
            'channel_id': channel_id,
            'channel_url': format_field(channel_id, template=f'{self._BASE_URL}/?channel=%s'),
            'duration': float_or_none(video.get('duration'), 1000),
            'view_count': int_or_none(video.get('views')),
            'tags': video.get('hashtags'),
            'start_time': int_or_none(compat_parse_qs(
                compat_urllib_parse_urlparse(url).query).get('t', [None])[0]),
        }

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    qualities,
)


class CrooksAndLiarsIE(InfoExtractor):
    _VALID_URL = r'https?://embed\.crooksandliars\.com/(?:embed|v)/(?P<id>[A-Za-z0-9]+)'
    _EMBED_REGEX = [r'<(?:iframe[^>]+src|param[^>]+value)=(["\'])(?P<url>(?:https?:)?//embed\.crooksandliars\.com/(?:embed|v)/.+?)\1']

    _TESTS = [{
        'url': 'https://embed.crooksandliars.com/embed/8RUoRhRi',
        'info_dict': {
            'id': '8RUoRhRi',
            'ext': 'mp4',
            'title': 'Fox & Friends Says Protecting Atheists From Discrimination Is Anti-Christian!',
            'description': 'md5:e1a46ad1650e3a5ec7196d432799127f',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1428207000,
            'upload_date': '20150405',
            'uploader': 'Heather',
            'duration': 236,
        }
    }, {
        'url': 'http://embed.crooksandliars.com/v/MTE3MjUtMzQ2MzA',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://embed.crooksandliars.com/embed/%s' % video_id, video_id)

        manifest = self._parse_json(
            self._search_regex(
                r'var\s+manifest\s*=\s*({.+?})\n', webpage, 'manifest JSON'),
            video_id)

        quality = qualities(('webm_low', 'mp4_low', 'webm_high', 'mp4_high'))

        formats = [{
            'url': item['url'],
            'format_id': item['type'],
            'quality': quality(item['type']),
        } for item in manifest['flavors'] if item['mime'].startswith('video/')]

        return {
            'url': url,
            'id': video_id,
            'title': manifest['title'],
            'description': manifest.get('description'),
            'thumbnail': self._proto_relative_url(manifest.get('poster')),
            'timestamp': int_or_none(manifest.get('created')),
            'uploader': manifest.get('author'),
            'duration': int_or_none(manifest.get('duration')),
            'formats': formats,
        }

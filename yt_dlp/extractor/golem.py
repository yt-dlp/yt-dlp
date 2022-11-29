from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    determine_ext,
)


class GolemIE(InfoExtractor):
    _VALID_URL = r'^https?://video\.golem\.de/.+?/(?P<id>.+?)/'
    _TEST = {
        'url': 'http://video.golem.de/handy/14095/iphone-6-und-6-plus-test.html',
        'md5': 'c1a2c0a3c863319651c7c992c5ee29bf',
        'info_dict': {
            'id': '14095',
            'format_id': 'high',
            'ext': 'mp4',
            'title': 'iPhone 6 und 6 Plus - Test',
            'duration': 300.44,
            'filesize': 65309548,
        }
    }

    _PREFIX = 'http://video.golem.de'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        config = self._download_xml(
            'https://video.golem.de/xml/{0}.xml'.format(video_id), video_id)

        info = {
            'id': video_id,
            'title': config.findtext('./title', 'golem'),
            'duration': self._float(config.findtext('./playtime'), 'duration'),
        }

        formats = []
        for e in config:
            url = e.findtext('./url')
            if not url:
                continue

            formats.append({
                'format_id': compat_str(e.tag),
                'url': compat_urlparse.urljoin(self._PREFIX, url),
                'height': self._int(e.get('height'), 'height'),
                'width': self._int(e.get('width'), 'width'),
                'filesize': self._int(e.findtext('filesize'), 'filesize'),
                'ext': determine_ext(e.findtext('./filename')),
            })
        info['formats'] = formats

        thumbnails = []
        for e in config.findall('.//teaser'):
            url = e.findtext('./url')
            if not url:
                continue
            thumbnails.append({
                'url': compat_urlparse.urljoin(self._PREFIX, url),
                'width': self._int(e.get('width'), 'thumbnail width'),
                'height': self._int(e.get('height'), 'thumbnail height'),
            })
        info['thumbnails'] = thumbnails

        return info

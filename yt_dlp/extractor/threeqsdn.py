from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_iso8601,
)


class ThreeQSDNIE(InfoExtractor):
    IE_NAME = '3qsdn'
    IE_DESC = '3Q SDN'
    _VALID_URL = r'https?://playout\.3qsdn\.com/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TESTS = [{
        # https://player.3qsdn.com/demo.html
        'url': 'https://playout.3qsdn.com/7201c779-6b3c-11e7-a40e-002590c750be',
        'md5': '64a57396b16fa011b15e0ea60edce918',
        'info_dict': {
            'id': '7201c779-6b3c-11e7-a40e-002590c750be',
            'ext': 'mp4',
            'title': 'Video Ads',
            'is_live': False,
            'description': 'Video Ads Demo',
            'timestamp': 1500334803,
            'upload_date': '20170717',
            'duration': 888.032,
            'subtitles': {
                'eng': 'count:1',
            },
        },
        'expected_warnings': ['Unknown MIME type application/mp4 in DASH manifest'],
    }, {
        # live video stream
        'url': 'https://playout.3qsdn.com/66e68995-11ca-11e8-9273-002590c750be',
        'info_dict': {
            'id': '66e68995-11ca-11e8-9273-002590c750be',
            'ext': 'mp4',
            'title': 're:^66e68995-11ca-11e8-9273-002590c750be [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
        },
        'params': {
            'skip_download': True,  # m3u8 downloads
        },
    }, {
        # live audio stream
        'url': 'http://playout.3qsdn.com/9edf36e0-6bf2-11e2-a16a-9acf09e2db48',
        'only_matching': True,
    }, {
        # live audio stream with some 404 URLs
        'url': 'http://playout.3qsdn.com/ac5c3186-777a-11e2-9c30-9acf09e2db48',
        'only_matching': True,
    }, {
        # geo restricted with 'This content is not available in your country'
        'url': 'http://playout.3qsdn.com/d63a3ffe-75e8-11e2-9c30-9acf09e2db48',
        'only_matching': True,
    }, {
        # geo restricted with 'playout.3qsdn.com/forbidden'
        'url': 'http://playout.3qsdn.com/8e330f26-6ae2-11e2-a16a-9acf09e2db48',
        'only_matching': True,
    }, {
        # live video with rtmp link
        'url': 'https://playout.3qsdn.com/6092bb9e-8f72-11e4-a173-002590c750be',
        'only_matching': True,
    }, {
        # ondemand from http://www.philharmonie.tv/veranstaltung/26/
        'url': 'http://playout.3qsdn.com/0280d6b9-1215-11e6-b427-0cc47a188158?protocol=http',
        'only_matching': True,
    }, {
        # live video stream
        'url': 'https://playout.3qsdn.com/d755d94b-4ab9-11e3-9162-0025907ad44f?js=true',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+\b(?:data-)?src=(["\'])(?P<url>%s.*?)\1' % ThreeQSDNIE._VALID_URL, webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            config = self._download_json(
                url.replace('://playout.3qsdn.com/', '://playout.3qsdn.com/config/'), video_id)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                self.raise_geo_restricted()
            raise

        live = config.get('streamContent') == 'live'
        aspect = float_or_none(config.get('aspect'))

        formats = []
        for source_type, source in (config.get('sources') or {}).items():
            if not source:
                continue
            if source_type == 'dash':
                formats.extend(self._extract_mpd_formats(
                    source, video_id, mpd_id='mpd', fatal=False))
            elif source_type == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    source, video_id, 'mp4', 'm3u8' if live else 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif source_type == 'progressive':
                for s in source:
                    src = s.get('src')
                    if not (src and self._is_valid_url(src, video_id)):
                        continue
                    width = None
                    format_id = ['http']
                    ext = determine_ext(src)
                    if ext:
                        format_id.append(ext)
                    height = int_or_none(s.get('height'))
                    if height:
                        format_id.append('%dp' % height)
                        if aspect:
                            width = int(height * aspect)
                    formats.append({
                        'ext': ext,
                        'format_id': '-'.join(format_id),
                        'height': height,
                        'source_preference': 0,
                        'url': src,
                        'vcodec': 'none' if height == 0 else None,
                        'width': width,
                    })
        # It seems like this would be correctly handled by default
        # However, unless someone can confirm this, the old
        # behaviour is being kept as-is
        self._sort_formats(formats, ('res', 'source_preference'))

        subtitles = {}
        for subtitle in (config.get('subtitles') or []):
            src = subtitle.get('src')
            if not src:
                continue
            subtitles.setdefault(subtitle.get('label') or 'eng', []).append({
                'url': src,
            })

        title = config.get('title') or video_id

        return {
            'id': video_id,
            'title': self._live_title(title) if live else title,
            'thumbnail': config.get('poster') or None,
            'description': config.get('description') or None,
            'timestamp': parse_iso8601(config.get('upload_date')),
            'duration': float_or_none(config.get('vlength')) or None,
            'is_live': live,
            'formats': formats,
            'subtitles': subtitles,
        }

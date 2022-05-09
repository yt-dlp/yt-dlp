import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    format_field,
    int_or_none,
    js_to_json,
    try_get,
)


class JojIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    (?:
                        joj:|
                        https?://media\.joj\.sk/embed/
                    )
                    (?P<id>[^/?#^]+)
                '''
    _TESTS = [{
        'url': 'https://media.joj.sk/embed/a388ec4c-6019-4a4a-9312-b1bee194e932',
        'info_dict': {
            'id': 'a388ec4c-6019-4a4a-9312-b1bee194e932',
            'ext': 'mp4',
            'title': 'NOVÉ BÝVANIE',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 3118,
        }
    }, {
        'url': 'https://media.joj.sk/embed/9i1cxv',
        'only_matching': True,
    }, {
        'url': 'joj:a388ec4c-6019-4a4a-9312-b1bee194e932',
        'only_matching': True,
    }, {
        'url': 'joj:9i1cxv',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [
            mobj.group('url')
            for mobj in re.finditer(
                r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//media\.joj\.sk/embed/(?:(?!\1).)+)\1',
                webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://media.joj.sk/embed/%s' % video_id, video_id)

        title = self._search_regex(
            (r'videoTitle\s*:\s*(["\'])(?P<title>(?:(?!\1).)+)\1',
             r'<title>(?P<title>[^<]+)'), webpage, 'title',
            default=None, group='title') or self._og_search_title(webpage)

        bitrates = self._parse_json(
            self._search_regex(
                r'(?s)(?:src|bitrates)\s*=\s*({.+?});', webpage, 'bitrates',
                default='{}'),
            video_id, transform_source=js_to_json, fatal=False)

        formats = []
        for format_url in try_get(bitrates, lambda x: x['mp4'], list) or []:
            if isinstance(format_url, compat_str):
                height = self._search_regex(
                    r'(\d+)[pP]\.', format_url, 'height', default=None)
                formats.append({
                    'url': format_url,
                    'format_id': format_field(height, template='%sp'),
                    'height': int(height),
                })
        if not formats:
            playlist = self._download_xml(
                'https://media.joj.sk/services/Video.php?clip=%s' % video_id,
                video_id)
            for file_el in playlist.findall('./files/file'):
                path = file_el.get('path')
                if not path:
                    continue
                format_id = file_el.get('id') or file_el.get('label')
                formats.append({
                    'url': 'http://n16.joj.sk/storage/%s' % path.replace(
                        'dat/', '', 1),
                    'format_id': format_id,
                    'height': int_or_none(self._search_regex(
                        r'(\d+)[pP]', format_id or path, 'height',
                        default=None)),
                })
        self._sort_formats(formats)

        thumbnail = self._og_search_thumbnail(webpage)

        duration = int_or_none(self._search_regex(
            r'videoDuration\s*:\s*(\d+)', webpage, 'duration', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
        }

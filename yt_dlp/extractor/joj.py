from .common import InfoExtractor
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
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//media\.joj\.sk/embed/(?:(?!\1).)+)\1']
    _TESTS = [{
        'url': 'https://media.joj.sk/embed/a388ec4c-6019-4a4a-9312-b1bee194e932',
        'info_dict': {
            'id': 'a388ec4c-6019-4a4a-9312-b1bee194e932',
            'ext': 'mp4',
            'title': 'NOVÉ BÝVANIE',
            'thumbnail': r're:^https?://.*?$',
            'duration': 3118,
        },
    }, {
        'url': 'https://media.joj.sk/embed/CSM0Na0l0p1',
        'info_dict': {
            'id': 'CSM0Na0l0p1',
            'ext': 'mp4',
            'height': 576,
            'title': 'Extrémne rodiny 2 - POKRAČOVANIE (2012/04/09 21:30:00)',
            'duration': 3937,
            'thumbnail': r're:^https?://.*?$',
        },
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

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            f'https://media.joj.sk/embed/{video_id}', video_id)

        title = (self._search_json(r'videoTitle\s*:', webpage, 'title', video_id,
                                   contains_pattern=r'["\'].+["\']', default=None)
                 or self._html_extract_title(webpage, default=None)
                 or self._og_search_title(webpage))

        bitrates = self._parse_json(
            self._search_regex(
                r'(?s)(?:src|bitrates)\s*=\s*({.+?});', webpage, 'bitrates',
                default='{}'),
            video_id, transform_source=js_to_json, fatal=False)

        formats = []
        for format_url in try_get(bitrates, lambda x: x['mp4'], list) or []:
            if isinstance(format_url, str):
                height = self._search_regex(
                    r'(\d+)[pP]|(pal)\.', format_url, 'height', default=None)
                if height == 'pal':
                    height = 576
                formats.append({
                    'url': format_url,
                    'format_id': format_field(height, None, '%sp'),
                    'height': int_or_none(height),
                })
        if not formats:
            playlist = self._download_xml(
                f'https://media.joj.sk/services/Video.php?clip={video_id}',
                video_id)
            for file_el in playlist.findall('./files/file'):
                path = file_el.get('path')
                if not path:
                    continue
                format_id = file_el.get('id') or file_el.get('label')
                formats.append({
                    'url': 'http://n16.joj.sk/storage/{}'.format(path.replace(
                        'dat/', '', 1)),
                    'format_id': format_id,
                    'height': int_or_none(self._search_regex(
                        r'(\d+)[pP]', format_id or path, 'height',
                        default=None)),
                })

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

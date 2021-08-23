from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_duration,
    url_or_none,
)


class YouJizzIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?youjizz\.com/videos/(?:[^/#?]*-(?P<id>\d+)\.html|embed/(?P<embed_id>\d+))'
    _TESTS = [{
        'url': 'http://www.youjizz.com/videos/zeichentrick-1-2189178.html',
        'md5': 'b1e1dfaa8bb9537d8b84eeda9cf4acf4',
        'info_dict': {
            'id': '2189178',
            'ext': 'mp4',
            'title': 'Zeichentrick 1',
            'age_limit': 18,
            'duration': 2874,
        }
    }, {
        'url': 'http://www.youjizz.com/videos/-2189178.html',
        'only_matching': True,
    }, {
        'url': 'https://www.youjizz.com/videos/embed/31991001',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('embed_id')

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<title>(.+?)</title>', webpage, 'title')

        formats = []

        encodings = self._parse_json(
            self._search_regex(
                r'[Ee]ncodings\s*=\s*(\[.+?\]);\n', webpage, 'encodings',
                default='[]'),
            video_id, fatal=False)
        for encoding in encodings:
            if not isinstance(encoding, dict):
                continue
            format_url = url_or_none(encoding.get('filename'))
            if not format_url:
                continue
            if determine_ext(format_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                format_id = encoding.get('name') or encoding.get('quality')
                height = int_or_none(self._search_regex(
                    r'^(\d+)[pP]', format_id, 'height', default=None))
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                    'height': height,
                })

        if formats:
            info_dict = {
                'formats': formats,
            }
        else:
            # YouJizz's HTML5 player has invalid HTML
            webpage = webpage.replace('"controls', '" controls')
            info_dict = self._parse_html5_media_entries(
                url, webpage, video_id)[0]

        duration = parse_duration(self._search_regex(
            r'<strong>Runtime:</strong>([^<]+)', webpage, 'duration',
            default=None))
        uploader = self._search_regex(
            r'<strong>Uploaded By:.*?<a[^>]*>([^<]+)', webpage, 'uploader',
            default=None)

        info_dict.update({
            'id': video_id,
            'title': title,
            'age_limit': self._rta_search(webpage),
            'duration': duration,
            'uploader': uploader,
        })

        return info_dict

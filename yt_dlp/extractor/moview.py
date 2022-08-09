from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none, 
    traverse_obj,
    try_call,
    try_call,
)


class MoviewPlayIE(InfoExtractor):
    _VALID_URL = r'https?://www\.moview\.id/play/\d+/(?P<id>[\w-]+)'
    _TESTS = [
        {
            'url': 'https://www.moview.id/play/174/Candy-Monster',
            'info_dict': {
                'id': '146182',
                'ext': 'mp4',
                'display_id': 'Candy-Monster',
                'uploader_id': 'Mo165qXUUf',
                'duration': 528.2,
                'title': 'Candy Monster',
                'categories': [''],
                'tags': [''],
                'description': 'Mengapa Candy Monster ingin mengambil permen Chloe?',
                'thumbnail': 'https://video.jixie.media/1034/146182/146182_1280x720.jpg',
            }
        }
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            r'video_id\s*=\s*"(?P<video_id>[^"]+)', webpage, 'video_id')

        # adapted from kompas.py
        json_data = self._download_json(
            'https://apidam.jixie.io/api/public/stream', display_id,
            query={'metadata': 'full', 'video_id': video_id})['data']
        
        formats, subtitles = [], {}
        for stream in json_data['streams']:
            if stream.get('type') == 'HLS':
                if json_data.get('drm'):
                    self.write_debug('Found drm content, trying to use non-drm link')
                else:
                    fmt, sub = self._extract_m3u8_formats_and_subtitles(stream.get('url'), display_id, ext='mp4')
                    formats.extend(fmt)
                    self._merge_subtitles(sub, target=subtitles)
            else:
                formats.append({
                    'url': stream.get('url'),
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'ext': 'mp4',
                })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': json_data.get('title') or self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': (clean_html(traverse_obj(json_data, ('metadata', 'description')))
                            or self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage)),
            'thumbnails': traverse_obj(json_data, ('metadata', 'thumbnails')),
            'duration': float_or_none(traverse_obj(json_data, ('metadata', 'duration'))),
            'tags': try_call(lambda: json_data['metadata']['keywords'].split(',')),
            'categories': try_call(lambda: json_data['metadata']['categories'].split(',')),
            'uploader_id': json_data.get('owner_id'),
        }

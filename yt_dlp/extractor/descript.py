from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class DescriptIE(InfoExtractor):
    _VALID_URL = r'https?://share\.descript\.com/(?:view|embed)/(?P<id>[^/?#]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://share.descript.com/view/3nvfjWuet4r',
        'md5': '637286c7ad0cecda6529f41acfb20db0',
        'info_dict': {
            'id': '3nvfjWuet4r',
            'ext': 'mp4',
            'title': 'clip1_doac',
            'uploader': 'Siddharth Rodrigues',
            'timestamp': 1770805377,
            'upload_date': '20260211',
            'duration': 15.0,
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }, {
        'url': 'https://share.descript.com/view/ZS2zF6ZONam',
        'only_matching': True,
    }, {
        'url': 'https://share.descript.com/embed/3nvfjWuet4r',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://share.descript.com/view/{video_id}', video_id)

        metadata = self._search_json(
            r'<script[^>]+\bid=["\']metadata["\'][^>]*>',
            webpage, 'metadata', video_id, end_pattern=r'</script>')

        formats = []

        original_url = traverse_obj(
            metadata, ('contents', 'media', 'original', 'cdn_url', {url_or_none}))
        if original_url:
            formats.append({
                'url': original_url,
                'format_id': 'original',
                'quality': 1,
                **traverse_obj(metadata, ('contents', 'media', 'original', 'video', {
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                })),
            })

        stream_url = traverse_obj(
            metadata, ('contents', 'media', 'stream', 'cdn_url', {url_or_none}))
        if stream_url:
            formats.extend(self._extract_m3u8_formats(
                stream_url, video_id, 'mp4', m3u8_id='hls', fatal=False))

        # Duration is in the document script (transcript data), not in the metadata script
        duration = float_or_none(self._search_regex(
            r'"duration"\s*:\s*([\d.]+)', webpage, 'duration', fatal=False))

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': self.extract_subtitles(video_id, metadata),
            'duration': duration,
            'uploader': ' '.join(traverse_obj(
                metadata, ('published_by', ('first_name', 'last_name'), {str}))).strip() or None,
            **traverse_obj(metadata, {
                'title': ('name', {str}),
                'timestamp': ('created_at', {parse_iso8601}),
                'thumbnail': ('contents', 'media', 'thumbnail', 'cdn_url', {url_or_none}),
            }),
        }

    def _get_subtitles(self, video_id, metadata):
        subtitles = {}
        for sub_key, ext in [('subtitles', 'vtt'), ('transcript', 'json')]:
            if sub_url := traverse_obj(metadata, ('contents', sub_key, 'cdn_url', {url_or_none})):
                subtitles.setdefault('en', []).append({'url': sub_url, 'ext': ext})
        return subtitles

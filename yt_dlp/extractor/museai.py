import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    js_to_json,
    traverse_obj,
    url_or_none,
)


class MuseAIIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?muse\.ai/(?:v|embed)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://muse.ai/embed/YdTWvUW',
        'md5': 'f994f9a38be1c3aaf9e37cbd7d76fe7c',
        'info_dict': {
            'id': 'YdTWvUW',
            'ext': 'mp4',
            'title': '2023-05-28-Grabien-1941111 (1)',
            'description': '',
            'uploader': 'Today News Africa',
            'uploader_id': 'TodayNewsAfrica',
            'upload_date': '20230528',
            'timestamp': 1685285044,
            'duration': 1291.3,
            'view_count': int,
            'availability': 'public',
        },
    }, {
        'url': 'https://muse.ai/v/gQ4gGAA-0756',
        'md5': '52dbfc78e865e56dc19a1715badc35e8',
        'info_dict': {
            'id': 'gQ4gGAA',
            'ext': 'mp4',
            'title': '0756',
            'description': 'md5:0ca1483f9aac423e9a96ad00bb3a0785',
            'uploader': 'Aerial.ie',
            'uploader_id': 'aerial',
            'upload_date': '20210306',
            'timestamp': 1615072842,
            'duration': 21.4,
            'view_count': int,
            'availability': 'public',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://muse.ai/docs',
        'playlist_mincount': 4,
        'info_dict': {
            'id': 'docs',
            'title': 'muse.ai | docs',
            'description': 'md5:6c0293431481582739c82ee8902687fa',
            'age_limit': 0,
            'thumbnail': 'https://muse.ai/static/imgs/poster-img-docs.png',
        },
        'params': {'allowed_extractors': ['all', '-html5']},
    }]
    _EMBED_REGEX = [r'<iframe[^>]*\bsrc=["\'](?P<url>https://muse\.ai/embed/\w+)']

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)
        for embed_id in re.findall(r'<script>[^<]*\bMusePlayer\(\{[^}<]*\bvideo:\s*["\'](\w+)["\']', webpage):
            yield f'https://muse.ai/embed/{embed_id}'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://muse.ai/embed/{video_id}', video_id)
        data = self._search_json(
            r'player\.setData\(', webpage, 'player data', video_id, transform_source=js_to_json)

        source_url = data['url']
        if not url_or_none(source_url):
            raise ExtractorError('Unable to extract video URL')

        formats = [{
            'url': source_url,
            'format_id': 'source',
            'quality': 1,
            **traverse_obj(data, {
                'ext': ('filename', {determine_ext}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
                'filesize': ('size', {int_or_none}),
            }),
        }]
        if source_url.endswith('/data'):
            base_url = f'{source_url[:-5]}/videos'
            formats.extend(self._extract_m3u8_formats(
                f'{base_url}/hls.m3u8', video_id, m3u8_id='hls', fatal=False))
            formats.extend(self._extract_mpd_formats(
                f'{base_url}/dash.mpd', video_id, mpd_id='dash', fatal=False))

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'duration': ('duration', {float_or_none}),
                'timestamp': ('tcreated', {int_or_none}),
                'uploader': ('owner_name', {str}),
                'uploader_id': ('owner_username', {str}),
                'view_count': ('views', {int_or_none}),
                'age_limit': ('mature', {lambda x: 18 if x else None}),
                'availability': ('visibility', {lambda x: x if x in ('private', 'unlisted') else 'public'}),
            }),
        }

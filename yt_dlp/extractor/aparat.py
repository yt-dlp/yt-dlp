from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class AparatIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aparat\.com/(?:v/|video/video/embed/videohash/)(?P<id>[a-zA-Z0-9]+)'
    _EMBED_REGEX = [r'<iframe .*?src="(?P<url>https?://(?:www\.)?aparat\.com/video/[^"]+)"']
    _API_BASE = 'https://www.aparat.com/api/fa/v1'

    _TESTS = [{
        'url': 'http://www.aparat.com/v/wP8On',
        'info_dict': {
            'id': 'wP8On',
            'ext': 'mp4',
            'title': 'تیم گلکسی 11 - زومیت',
            'description': 'md5:096bdabcdcc4569f2b8a5e903a3b3028',
            'duration': 231,
            'timestamp': 1387394859,
            'upload_date': '20131218',
            'uploader_id': 'thezoomit',
            'thumbnail': r're:^https?://.+',
            'view_count': int,
            'like_count': int,
            'tags': ['تیم', 'گلکسی', 'زومیت'],
            'categories': ['فناوری و رایانه'],
        },
    }, {
        # multiple formats
        'url': 'https://www.aparat.com/v/qur3I',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        attrs = self._download_json(
            f'{self._API_BASE}/video/video/show/videohash/{video_id}', video_id,
            'Downloading video JSON')['data']['attributes']

        formats = []
        for link in attrs.get('file_link_all') or []:
            file_url = traverse_obj(link, ('urls', 0, {url_or_none}))
            if not file_url:
                continue
            profile = link.get('profile')  # e.g. '720p'; empty for single-quality videos
            formats.append({
                'url': file_url,
                'format_id': f'http-{profile}' if profile else 'http',
                'height': int_or_none((profile or '')[:-1]),
            })
        hls_url = traverse_obj(attrs, ('hls', 'link', {url_or_none}))
        if hls_url:
            formats.extend(self._extract_m3u8_formats(
                hls_url, video_id, 'mp4', m3u8_id='hls', fatal=False))

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(attrs, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('mdate', {parse_iso8601}),
                'thumbnail': ('big_poster', {url_or_none}),
                'view_count': ('visit_cnt_non_formatted', {int_or_none}),
                'like_count': ('like_cnt_non_formatted', {int_or_none}),
                'uploader_id': ('owner_username', {str}),
                'tags': ('tags', ..., {str.strip}, filter),
                'categories': ('category', 'name', {str}, filter, all),
            }),
        }


class AparatPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aparat\.com/playlist/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.aparat.com/playlist/448747',
        'info_dict': {
            'id': '448747',
            'title': 'مشکلات مک',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        data = self._download_json(
            f'{AparatIE._API_BASE}/video/playlist/one/playlist_id/{playlist_id}', playlist_id)

        return self.playlist_from_matches(
            traverse_obj(data, ('included', lambda _, v: v['type'] == 'Video', 'attributes', 'uid')),
            playlist_id, traverse_obj(data, ('data', 'attributes', 'title', {str})),
            getter=lambda uid: f'https://www.aparat.com/v/{uid}', ie=AparatIE)

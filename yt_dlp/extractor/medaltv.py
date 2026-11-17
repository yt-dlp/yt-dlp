from .common import InfoExtractor
from ..utils import (
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class MedalTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?medal\.tv/games/[^/?#&]+/clips/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://medal.tv/games/valorant/clips/jTBFnLKdLy15K',
        'md5': '03e4911fdcf7fce563090705c2e79267',
        'info_dict': {
            'id': 'jTBFnLKdLy15K',
            'ext': 'mp4',
            'title': "Mornu's clutch",
            'description': '',
            'uploader': 'Aciel',
            'timestamp': 1651628243,
            'upload_date': '20220504',
            'uploader_id': '19335460',
            'uploader_url': 'https://medal.tv/users/19335460',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 13,
            'thumbnail': r're:https://cdn\.medal\.tv/ugcp/content-thumbnail/.*\.jpg',
            'tags': ['headshot', 'valorant', '4k', 'clutch', 'mornu'],
        },
    }, {
        'url': 'https://medal.tv/games/cod-cold-war/clips/2um24TWdty0NA',
        'md5': 'b6dc76b78195fff0b4f8bf4a33ec2148',
        'info_dict': {
            'id': '2um24TWdty0NA',
            'ext': 'mp4',
            'title': 'u tk me i tk u bigger',
            'description': '',
            'uploader': 'zahl',
            'timestamp': 1605580939,
            'upload_date': '20201117',
            'uploader_id': '5156321',
            'thumbnail': r're:https://cdn\.medal\.tv/source/.*\.png',
            'uploader_url': 'https://medal.tv/users/5156321',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 9,
        },
    }, {
        # API requires auth
        'url': 'https://medal.tv/games/valorant/clips/2WRj40tpY_EU9',
        'md5': '6c6bb6569777fd8b4ef7b33c09de8dcf',
        'info_dict': {
            'id': '2WRj40tpY_EU9',
            'ext': 'mp4',
            'title': '1v5 clutch',
            'description': '',
            'uploader': 'adny',
            'uploader_id': '6256941',
            'uploader_url': 'https://medal.tv/users/6256941',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 25,
            'thumbnail': r're:https://cdn\.medal\.tv/source/.*\.jpg',
            'timestamp': 1612896680,
            'upload_date': '20210209',
        },
        'expected_warnings': ['Video formats are not available through API'],
    }, {
        'url': 'https://medal.tv/games/valorant/clips/37rMeFpryCC-9',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        content_data = self._download_json(
            f'https://medal.tv/api/content/{video_id}', video_id,
            headers={'Accept': 'application/json'})

        formats = []
        if m3u8_url := url_or_none(content_data.get('contentUrlHls')):
            formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls'))
        if http_url := url_or_none(content_data.get('contentUrl')):
            formats.append({
                'url': http_url,
                'format_id': 'http-source',
                'ext': 'mp4',
                'quality': 1,
            })
        formats = [fmt for fmt in formats if 'video/privacy-protected-guest' not in fmt['url']]
        if not formats:
            # Fallback, does not require auth
            self.report_warning('Video formats are not available through API, falling back to social video URL')
            urlh = self._request_webpage(
                f'https://medal.tv/api/content/{video_id}/socialVideoUrl', video_id,
                note='Checking social video URL')
            formats.append({
                'url': urlh.url,
                'format_id': 'social-video',
                'ext': 'mp4',
                'quality': -1,
            })

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(content_data, {
                'title': ('contentTitle', {str}),
                'description': ('contentDescription', {str}),
                'timestamp': ('created', {int_or_none(scale=1000)}),
                'duration': ('videoLengthSeconds', {int_or_none}),
                'view_count': ('views', {int_or_none}),
                'like_count': ('likes', {int_or_none}),
                'comment_count': ('comments', {int_or_none}),
                'uploader': ('poster', 'displayName', {str}),
                'uploader_id': ('poster', 'userId', {str}),
                'uploader_url': ('poster', 'userId', {str}, filter, {lambda x: x and f'https://medal.tv/users/{x}'}),
                'tags': ('tags', ..., {str}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
            }),
        }

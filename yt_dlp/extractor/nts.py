from .common import InfoExtractor
from ..utils import parse_iso8601, url_or_none
from ..utils.traversal import traverse_obj


class NTSLiveIE(InfoExtractor):
    IE_NAME = 'nts.live'
    _VALID_URL = r'https?://(?:www\.)?nts\.live/shows/[^/?#]+/episodes/(?P<id>[^/?#]+)'
    _TESTS = [
        {
            # embedded soundcloud
            'url': 'https://www.nts.live/shows/yu-su/episodes/yu-su-2nd-april-2024',
            'md5': 'b5444c04888c869d68758982de1a27d8',
            'info_dict': {
                'id': '1791563518',
                'ext': 'opus',
                'uploader_id': '995579326',
                'title': 'Pender Street Steppers & YU SU',
                'timestamp': 1712073600,
                'upload_date': '20240402',
                'thumbnail': 'https://i1.sndcdn.com/artworks-qKcNO0z0AQGGbv9s-GljJCw-original.jpg',
                'license': 'all-rights-reserved',
                'repost_count': int,
                'uploader_url': 'https://soundcloud.com/user-643553014',
                'uploader': 'NTS Latest',
                'description': 'md5:cd00ac535a63caaad722483ae3ff802a',
                'duration': 10784.157,
                'genres': ['Deep House', 'House', 'Leftfield Disco', 'Jazz Fusion', 'Dream Pop'],
                'modified_timestamp': 1712564687,
                'modified_date': '20240408',
            },
        },
        {
            # embedded mixcloud
            'url': 'https://www.nts.live/shows/absolute-fiction/episodes/absolute-fiction-23rd-july-2022',
            'info_dict': {
                'id': 'NTSRadio_absolute-fiction-23rd-july-2022',
                'ext': 'webm',
                'like_count': int,
                'title': 'Absolute Fiction',
                'comment_count': int,
                'uploader_url': 'https://www.mixcloud.com/NTSRadio/',
                'description': 'md5:ba49da971ae8d71ee45813c52c5e2a04',
                'tags': [],
                'duration': 3529,
                'timestamp': 1658588400,
                'repost_count': int,
                'upload_date': '20220723',
                'uploader_id': 'NTSRadio',
                'thumbnail': 'https://thumbnailer.mixcloud.com/unsafe/1024x1024/extaudio/5/1/a/d/ae3e-1be9-4fd4-983e-9c3294226eac',
                'uploader': 'Mixcloud NTS Radio',
                'genres': ['Minimal Synth', 'Post Punk', 'Industrial '],
                'modified_timestamp': 1658842165,
                'modified_date': '20220726',
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._search_json(r'window\._REACT_STATE_\s*=', webpage, 'react state', video_id)

        return {
            '_type': 'url_transparent',
            **traverse_obj(data, ('episode', {
                'url': ('audio_sources', ..., 'url', {url_or_none}, any),
                'title': ('name', {str}),
                'description': ('description', {str}),
                'genres': ('genres', ..., 'value', {str}),
                'timestamp': ('broadcast', {parse_iso8601}),
                'modified_timestamp': ('updated', {parse_iso8601}),
            })),
        }

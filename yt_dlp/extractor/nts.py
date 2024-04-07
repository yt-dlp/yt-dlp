from .common import InfoExtractor
from ..utils import extract_attributes


class NTSLiveIE(InfoExtractor):
    IE_NAME = 'nts.live'
    _VALID_URL = r'https?://(?:www\.)?nts\.live/shows/[^/]+/episodes/(?P<id>[^./?#]+)'
    _TESTS = [
        {
            # embedded soundcloud
            'url': 'https://www.nts.live/shows/yu-su/episodes/yu-su-2nd-april-2024',
            'md5': 'b5444c04888c869d68758982de1a27d8',
            'info_dict': {
                'id': '1791563518',
                'ext': 'opus',
                'uploader_id': '995579326',
                'title': 'Pender Street Steppers & YU SU 020424',
                'timestamp': 1712143743,
                'upload_date': '20240403',
                'thumbnail': 'https://i1.sndcdn.com/artworks-qKcNO0z0AQGGbv9s-GljJCw-original.jpg',
                'license': 'all-rights-reserved',
                'repost_count': int,
                'uploader_url': 'https://soundcloud.com/user-643553014',
                'uploader': 'NTS Latest',
                'description': 'md5:cf9d7d7997ef00a7b6046c9615b72c55',
                'duration': 10784.157,
            }
        },
        {
            # embedded mixcloud
            'url': 'https://www.nts.live/shows/absolute-fiction/episodes/absolute-fiction-23rd-july-2022',
            'md5': 'TODO',
            'info_dict': {
                'id': 'NTSRadio_absolute-fiction-23rd-july-2022',
                'ext': 'webm',
                'like_count': int,
                'title': 'Absolute Fiction - 23rd July 2022',
                'comment_count': int,
                'uploader_url': 'https://www.mixcloud.com/NTSRadio/',
                'description': 'md5:a8cb9d9f040adb6525d33a6604fc759c',
                'tags': [],
                'duration': 3529,
                'timestamp': 1658772398,
                'repost_count': int,
                'upload_date': '20220725',
                'uploader_id': 'NTSRadio',
                'thumbnail': 'https://thumbnailer.mixcloud.com/unsafe/1024x1024/extaudio/5/1/a/d/ae3e-1be9-4fd4-983e-9c3294226eac',
                'uploader': 'Mixcloud NTS Radio',
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        attrs = extract_attributes(self._search_regex(
            r'(<button[^>]+?aria-label="Play"[^>]*?>)', webpage, 'player'))

        return self.url_result(attrs['data-src'])

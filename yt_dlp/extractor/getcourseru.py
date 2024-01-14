from .common import InfoExtractor
from ..utils import ExtractorError


class GetCourseRuIE(InfoExtractor):
    _NETRC_MACHINE = 'getcourseru'
    _VALID_URL = r'^https?:\/\/[^\/]+\.getcourse\.ru\/sign-player\/\?.*$'

    _TESTS = [{
        'url': 'http://player02.getcourse.ru/sign-player/?json=eyJ2aWRlb19oYXNoIjoiZTJlZWE3MTI5ZDk3OWQzYzYzMDYzMDUzOGJkMzZlZjEiLCJ1c2VyX2lkIjozNTc3NjY5NjIsInN1Yl9sb2dpbl91c2VyX2lkIjpudWxsLCJsZXNzb25faWQiOm51bGwsImlwIjoiNDYuMTQyLjE4My44NSIsImdjX2hvc3QiOiJhY2FkZW15bWVsLm9ubGluZSIsInRpbWUiOjE3MDM4MDY1NzksInBheWxvYWQiOiJ1XzM1Nzc2Njk2MiIsInVpX2xhbmd1YWdlIjoicnUiLCJpc19oYXZlX2N1c3RvbV9zdHlsZSI6dHJ1ZX0=&s=a2ed5bd648a2ae7a4f7684abe815ec7a',
        'info_dict': {
            'id': 'master.m3u8?user-cdn=cdnvideo&acc-id=714517&user-id=357766962&loc-mode=ru&version=10:2:1:0:2:cdnvideo&consumer=vod&jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyLWlkIjozNTc3NjY5NjJ9',
            'title': 'master',
            'ext': 'mp4',
            'duration': 1871
            # note: the original URL is necessary to obtain an up-to-date URL, because the URL is always changing
        },
        'skip': 'Requires authentication',
        'note': 'This extractor is used by AcademyMel extractor, which has a login feature'
    }]

    def _real_extract(self, url):
        valid_url = self._match_valid_url(url)

        if not valid_url:
            raise ExtractorError('Invalid URL found', expected=True)

        webpage = self._download_webpage(url,
                                         None,
                                         fatal=True,
                                         note='Retrieving metadata...',
                                         errnote='Failed to retrieve metadata')

        window_configs = self._search_json(
            r'window\.configs\s*=\s*',
            webpage,
            'config',
            video_id=None,
            fatal=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            window_configs.get('masterPlaylistUrl'),
            window_configs.get('videoId'))

        return {
            'id': str(window_configs.get('videoId')),
            'title': window_configs.get('videoHash'),
            'thumbnail': window_configs.get('thumbnailUrl'),
            'duration': int(window_configs.get('videoDuration')),
            'formats': formats,
            'subtitles': subtitles
        }

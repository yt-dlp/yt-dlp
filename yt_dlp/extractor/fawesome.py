import re
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
    unified_timestamp,
)


class FawesomeIE(InfoExtractor):
    _VALID_URL = r'https?://fawesome\.tv/(?:movies|tv-shows)/(?P<id>\d+)/.+'
    _TESTS = [{
        'url': 'https://fawesome.tv/movies/10527435/calla-lily',
        'info_dict': {
            'id': '10527435',
            'ext': 'mp4',
            'title': 'Calla Lily',
            'description': 'md5:7a26a1754e8e81373d22b320582cc5dc',
            'duration': 4945,
            'thumbnail': r're:https://ftmain.cachefly.net/files/.+\.jpg',
            'creators': ['FilmHub'],
            'timestamp': 1693440000,
            'release_timestamp': 1451606400,
            'upload_date': '20230831',
            'release_date': '20160101',
        },
        'params': {
            'skip_download': True,
        },
    },
        {
        'url': 'https://fawesome.tv/tv-shows/10598460/s01-e01-back-to-californy-the-beverly-hillbillies',
        'info_dict': {
            'id': '10598460',
            'ext': 'mp4',
            'title': 'S01 E01 - Back to Californy - The Beverly Hillbillies',
            'description': 'md5:db7a427f8a9c13300fa1eee0e67b902f',
            'duration': 1532,
            'thumbnail': r're:https://ftmain.cachefly.net/files/.+\.jpg',
            'creators': ['CineverseMG'],
            'timestamp': 1718928000,
            'release_timestamp': -229305600,
            'upload_date': '20240621',
            'release_date': '19620926',
        },
        'params': {
            'skip_download': True,
        },
    }]

    @staticmethod
    def _create_url(version, api, device_id, extra_params=''):
        # auth-token is actually the device type
        # 1217575 is a fixed value for "website"
        # appId=9 and siteId=236 are also from their website
        return (
            f'https://fawesome.tv/home/new/{version}/api/'
            f'{api}?'
            '&appId=9'
            '&siteId=236'
            '&auth-token=1217575'
            f'&deviceId={device_id}'
            '&apiEnv=production'
            f'{extra_params}')

    def _real_extract(self, url):
        device_id = uuid.uuid4()
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        version = self._search_regex(r'/home/new/(v[^/]+)', webpage, 'api version', default='v444')

        # Get the auth token
        auth_url = FawesomeIE._create_url(version, 'getSecurityToken.php', device_id)
        webpage = self._download_json(auth_url, video_id)
        token = webpage.get('securityToken')
        if not token:
            raise ExtractorError('Failed to get security token')

        # Download via HLS m3u8 file
        video_data_url = FawesomeIE._create_url(version, 'recipes.php', device_id,
                                                f'&searchType=nodeid&start-index=0&dltype=1&nid={video_id}')
        video_data = self._download_json(video_data_url, video_id, headers={'Token': token, 'Referer': url})
        metadata = traverse_obj(video_data, ('results', 0))
        if not metadata:
            raise ExtractorError('Failed to get video metadata')

        # Remove period and comma for unified_timestamp (ex. Aug. 31, 2023)
        timestamp = metadata.get('date', '').replace('.', '').replace(',', '')

        # Remove hyphen and clock for unified_timestamp (ex. 01 January 2016 - 12:00 am)
        release_date = re.sub(r' - .+', '', metadata.get('release_date', ''))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(metadata.get('video_hls_url'), video_id)

        return {
            'id': video_id,
            'title': metadata.get('title'),
            'description': metadata.get('description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': metadata.get('picture'),
            'format': metadata.get('video_format'),
            'creators': [metadata.get('author')],
            'timestamp': unified_timestamp(timestamp, day_first=False),
            'release_timestamp': unified_timestamp(release_date, day_first=True),
            'duration': int_or_none(metadata.get('runtime')),
        }

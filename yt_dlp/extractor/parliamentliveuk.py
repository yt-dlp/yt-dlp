from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
    try_get,
)


class ParliamentLiveUKIE(InfoExtractor):
    IE_NAME = 'parliamentlive.tv'
    IE_DESC = 'UK parliament videos'
    _VALID_URL = r'(?i)https?://(?:www\.)?parliamentlive\.tv/Event/Index/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'

    _TESTS = [{
        'url': 'http://parliamentlive.tv/Event/Index/c1e9d44d-fd6c-4263-b50f-97ed26cc998b',
        'info_dict': {
            'id': 'c1e9d44d-fd6c-4263-b50f-97ed26cc998b',
            'ext': 'mp4',
            'title': 'Home Affairs Committee',
            'timestamp': 1395153872,
            'upload_date': '20140318',
            'thumbnail': r're:https?://[^?#]+c1e9d44d-fd6c-4263-b50f-97ed26cc998b[^/]*/thumbnail',
        },
    }, {
        'url': 'http://parliamentlive.tv/event/index/3f24936f-130f-40bf-9a5d-b3d6479da6a4',
        'only_matching': True,
    }, {
        'url': 'https://parliamentlive.tv/Event/Index/27cf25e4-e77b-42a3-93c5-c815cd6d7377',
        'info_dict': {
            'id': '27cf25e4-e77b-42a3-93c5-c815cd6d7377',
            'ext': 'mp4',
            'title': 'House of Commons',
            'timestamp': 1658392447,
            'upload_date': '20220721',
            'thumbnail': r're:https?://[^?#]+27cf25e4-e77b-42a3-93c5-c815cd6d7377[^/]*/thumbnail',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(f'https://www.parliamentlive.tv/Event/GetShareVideo/{video_id}', video_id)

        return {
            '_type': 'url_transparent',
            'url': f'redbee:UKParliament:ParliamentLive:{video_id}',
            'title': video_info['event']['title'],
            'timestamp': unified_timestamp(try_get(video_info, lambda x: x['event']['publishedStartTime'])),
            'thumbnail': video_info.get('thumbnailUrl'),
        }

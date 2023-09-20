from .common import InfoExtractor
from ..utils import (
    parse_duration,
    traverse_obj,
)


class WimbledonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wimbledon\.com/\w+/video/media/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.wimbledon.com/en_GB/video/media/6330247525112.html',
        'info_dict': {
            'id': '6330247525112',
            'ext': 'mp4',
            'timestamp': 1687972186,
            'description': '',
            'thumbnail': r're:^https://[\w.-]+\.prod\.boltdns\.net/[^?#]+/image\.jpg',
            'upload_date': '20230628',
            'title': 'Coco Gauff | My Wimbledon Inspiration',
            'tags': ['features', 'trending', 'homepage'],
            'uploader_id': '3506358525001',
            'duration': 163072.0,
        },
    }, {
        'url': 'https://www.wimbledon.com/en_GB/video/media/6308703111112.html',
        'info_dict': {
            'id': '6308703111112',
            'ext': 'mp4',
            'thumbnail': r're:^https://[\w.-]+\.prod\.boltdns\.net/[^?#]+/image\.jpg',
            'description': 'null',
            'upload_date': '20220629',
            'uploader_id': '3506358525001',
            'title': 'Roblox | WimbleWorld ',
            'duration': 101440.0,
            'tags': ['features', 'kids'],
            'timestamp': 1656500867,
        },
    }, {
        'url': 'https://www.wimbledon.com/en_US/video/media/6309327106112.html',
        'only_matching': True,
    }, {
        'url': 'https://www.wimbledon.com/es_Es/video/media/6308377909112.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(
            f'https://www.wimbledon.com/relatedcontent/rest/v2/wim_v1/en/content/wim_v1_{video_id}_en', video_id)

        return {
            '_type': 'url_transparent',
            'url': f'http://players.brightcove.net/3506358525001/default_default/index.html?videoId={video_id}',
            'ie_key': 'BrightcoveNew',
            'id': video_id,
            **traverse_obj(metadata, {
                'title': 'title',
                'description': 'description',
                'duration': ('metadata', 'duration', {parse_duration}),
            }),
        }

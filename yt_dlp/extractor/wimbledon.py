from .common import InfoExtractor
from ..utils import (
    parse_duration,
    traverse_obj,
)


class WimbledonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wimbledon\.com/en_GB/video/media/(?P<id>[0-9]+).html'
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    _TESTS = [{
        'url': 'https://www.wimbledon.com/en_GB/video/media/6330247525112.html',
        'info_dict': {
            'id': '6330247525112',
            'ext': 'mp4',
            'timestamp': 1687972186,
            'description': '',
            'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/static/3506358525001/97312363-ba01-4158-8a45-1e51e518c0ff/806b5b8a-22dc-4618-aac9-f73bd6202715/1920x1080/match/image.jpg',
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
            'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/jit/3506358525001/3144a401-e6b3-4d49-9dfc-627866a2e2de/main/1920x1080/50s720ms/match/image.jpg',
            'description': 'null',
            'upload_date': '20220629',
            'uploader_id': '3506358525001',
            'title': 'Roblox | WimbleWorld ',
            'duration': 101440.0,
            'tags': ['features', 'kids'],
            'timestamp': 1656500867,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        account = '3506358525001'

        metadata = self._download_json(
            f'https://www.wimbledon.com/relatedcontent/rest/v2/wim_v1/en/content/wim_v1_{video_id}_en',
            video_id,
        )

        return {
            '_type': 'url_transparent',
            'url': self.BRIGHTCOVE_URL_TEMPLATE % (account, video_id),
            'ie_key': 'BrightcoveNew',
            'id': video_id,
            'title': metadata.get('title'),
            'description': metadata.get('description'),
            'language': metadata.get('language'),
            'duration': parse_duration(traverse_obj(metadata, ('metadata', 'duration'))),
        }

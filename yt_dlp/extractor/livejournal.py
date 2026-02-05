from .common import InfoExtractor
from ..utils import int_or_none


class LiveJournalIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:[^.]+\.)?livejournal\.com/video/album/\d+.+?\bid=(?P<id>\d+)'
    _TEST = {
        'url': 'https://andrei-bt.livejournal.com/video/album/407/?mode=view&id=51272',
        'md5': 'adaf018388572ced8a6f301ace49d4b2',
        'info_dict': {
            'id': '1263729',
            'ext': 'mp4',
            'title': 'Истребители против БПЛА',
            'upload_date': '20190624',
            'timestamp': 1561406715,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        record = self._parse_json(self._search_regex(
            r'Site\.page\s*=\s*({.+?});', webpage,
            'page data'), video_id)['video']['record']
        storage_id = str(record['storageid'])
        title = record.get('name')
        if title:
            # remove filename extension(.mp4, .mov, etc...)
            title = title.rsplit('.', 1)[0]
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'title': title,
            'thumbnail': record.get('thumbnail'),
            'timestamp': int_or_none(record.get('timecreate')),
            'url': 'eagleplatform:vc.videos.livejournal.com:' + storage_id,
            'ie_key': 'EaglePlatform',
        }

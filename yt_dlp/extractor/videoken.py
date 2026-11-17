import urllib.parse

from .common import InfoExtractor
from .slideslive import SlidesLiveIE
from ..utils import (
    remove_start,
    update_url_query,
    url_or_none,
)


class VideoKenPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\.videoken\.com/embed/slideslive-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://player.videoken.com/embed/slideslive-38968434',
        'info_dict': {
            'id': '38968434',
            'ext': 'mp4',
            'title': 'Deep Learning with Label Differential Privacy',
            'timestamp': 1643377020,
            'upload_date': '20220128',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:30',
            'chapters': 'count:29',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    def _create_slideslive_url(self, video_url, video_id, referer):
        if not video_url and not video_id:
            return
        elif not video_url or 'embed/sign-in' in video_url:
            video_url = f'https://slideslive.com/embed/{remove_start(video_id, "slideslive-")}'
        if url_or_none(referer):
            return update_url_query(video_url, {
                'embed_parent_url': referer,
                'embed_container_origin': f'https://{urllib.parse.urlparse(referer).hostname}',
            })
        return video_url

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            self._create_slideslive_url(None, video_id, url), SlidesLiveIE, video_id)

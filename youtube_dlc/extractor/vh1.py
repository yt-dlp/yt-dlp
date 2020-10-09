# coding: utf-8
from __future__ import unicode_literals

from .mtv import MTVServicesInfoExtractor

# TODO Remove - Reason: Outdated Site


class VH1IE(MTVServicesInfoExtractor):
    IE_NAME = 'vh1.com'
    _FEED_URL = 'http://www.vh1.com/feeds/mrss/'
    _TESTS = [{
        'url': 'http://www.vh1.com/episodes/0umwpq/hip-hop-squares-kent-jones-vs-nick-young-season-1-ep-120',
        'info_dict': {
            'title': 'Kent Jones vs. Nick Young',
            'description': 'Come to Play. Stay to Party. With Mike Epps, TIP, O’Shea Jackson Jr., T-Pain, Tisha Campbell-Martin and more.',
        },
        'playlist_mincount': 4,
    }, {
        # Clip
        'url': 'http://www.vh1.com/video-clips/t74mif/scared-famous-scared-famous-extended-preview',
        'info_dict': {
            'id': '0a50c2d2-a86b-4141-9565-911c7e2d0b92',
            'ext': 'mp4',
            'title': 'Scared Famous|October 9, 2017|1|NO-EPISODE#|Scared Famous + Extended Preview',
            'description': 'md5:eff5551a274c473a29463de40f7b09da',
            'upload_date': '20171009',
            'timestamp': 1507574700,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    _VALID_URL = r'https?://(?:www\.)?vh1\.com/(?:video-clips|episodes)/(?P<id>[^/?#.]+)'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        mgid = self._extract_triforce_mgid(webpage)
        videos_info = self._get_videos_info(mgid)
        return videos_info

from __future__ import unicode_literals

from .cbs import CBSBaseIE


class CBSSportsIE(CBSBaseIE):
    _VALID_URL = r'https?://(?:www\.)?cbssports\.com/[^/]+/(?:video|news)/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://www.cbssports.com/nba/video/donovan-mitchell-flashes-star-potential-in-game-2-victory-over-thunder/',
        'info_dict': {
            'id': '1214315075735',
            'ext': 'mp4',
            'title': 'Donovan Mitchell flashes star potential in Game 2 victory over Thunder',
            'description': 'md5:df6f48622612c2d6bd2e295ddef58def',
            'timestamp': 1524111457,
            'upload_date': '20180419',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        'url': 'https://www.cbssports.com/nba/news/nba-playoffs-2018-watch-76ers-vs-heat-game-3-series-schedule-tv-channel-online-stream/',
        'only_matching': True,
    }]

    def _extract_video_info(self, filter_query, video_id):
        return self._extract_feed_info('dJ5BDC', 'VxxJg8Ymh8sE', filter_query, video_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(
            [r'(?:=|%26)pcid%3D(\d+)', r'embedVideo(?:Container)?_(\d+)'],
            webpage, 'video id')
        return self._extract_video_info('byId=%s' % video_id, video_id)

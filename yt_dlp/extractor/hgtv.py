# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class HGTVComShowIE(InfoExtractor):
    IE_NAME = 'hgtv.com:show'
    _VALID_URL = r'https?://(?:www\.)?hgtv\.com/shows/[^/]+/(?P<id>[^/?#&]+)'
    _TESTS = [{
        # data-module="video"
        'url': 'http://www.hgtv.com/shows/flip-or-flop/flip-or-flop-full-episodes-season-4-videos',
        'info_dict': {
            'id': 'flip-or-flop-full-episodes-season-4-videos',
            'title': 'Flip or Flop Full Episodes',
        },
        'playlist_mincount': 15,
    }, {
        # data-deferred-module="video"
        'url': 'http://www.hgtv.com/shows/good-bones/episodes/an-old-victorian-house-gets-a-new-facelift',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        config = self._parse_json(
            self._search_regex(
                r'(?s)data-(?:deferred-)?module=["\']video["\'][^>]*>.*?<script[^>]+type=["\']text/x-config["\'][^>]*>(.+?)</script',
                webpage, 'video config'),
            display_id)['channels'][0]

        entries = [
            self.url_result(video['releaseUrl'])
            for video in config['videos'] if video.get('releaseUrl')]

        return self.playlist_result(
            entries, display_id, config.get('title'), config.get('description'))

# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class KaraoketvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?karaoketv\.co\.il/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.karaoketv.co.il/%D7%A9%D7%99%D7%A8%D7%99_%D7%A7%D7%A8%D7%99%D7%95%D7%A7%D7%99/58356/%D7%90%D7%99%D7%96%D7%95%D7%9F',
        'info_dict': {
            'id': '58356',
            'ext': 'flv',
            'title': 'קריוקי של איזון',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        api_page_url = self._search_regex(
            r'<iframe[^>]+src=(["\'])(?P<url>https?://www\.karaoke\.co\.il/api_play\.php\?.+?)\1',
            webpage, 'API play URL', group='url')

        api_page = self._download_webpage(api_page_url, video_id)
        video_cdn_url = self._search_regex(
            r'<iframe[^>]+src=(["\'])(?P<url>https?://www\.video-cdn\.com/embed/iframe/.+?)\1',
            api_page, 'video cdn URL', group='url')

        video_cdn = self._download_webpage(video_cdn_url, video_id)
        play_path = self._parse_json(
            self._search_regex(
                r'var\s+options\s*=\s*({.+?});', video_cdn, 'options'),
            video_id)['clip']['url']

        settings = self._parse_json(
            self._search_regex(
                r'var\s+settings\s*=\s*({.+?});', video_cdn, 'servers', default='{}'),
            video_id, fatal=False) or {}

        servers = settings.get('servers')
        if not servers or not isinstance(servers, list):
            servers = ('wowzail.video-cdn.com:80/vodcdn', )

        formats = [{
            'url': 'rtmp://%s' % server if not server.startswith('rtmp') else server,
            'play_path': play_path,
            'app': 'vodcdn',
            'page_url': video_cdn_url,
            'player_url': 'http://www.video-cdn.com/assets/flowplayer/flowplayer.commercial-3.2.18.swf',
            'rtmp_real_time': True,
            'ext': 'flv',
        } for server in servers]

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'formats': formats,
        }

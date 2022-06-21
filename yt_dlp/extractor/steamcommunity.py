from .common import InfoExtractor


class SteamCommunityBroadcastIE(InfoExtractor):
    _VALID_URL = r'https?://steamcommunity\.(?:com)/broadcast/watch/(?P<id>)\d+'
    _TESTS = [{
        'url': 'https://steamcommunity.com/broadcast/watch/76561199037072858',
        'only_matching': True,
    }]
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._download_json(
            f'https://steamcommunity.com/broadcast/getbroadcastmpd/?steamid={video_id}',
            video_id,
        )
        
        # for now just extract hls_url because url give 403 error
        formats, subs = self._extract_m3u8_and_subtitles(json_data['hls_url'])
        
        return {
            'id': video_id,
            'title': self._html_extract_title(webpage) or self._og_search_title(webpage),
            'formats': formats,
            'live_status': 'is_live',
        }
        
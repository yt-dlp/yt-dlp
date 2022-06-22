from .common import InfoExtractor


class SteamCommunityBroadcastIE(InfoExtractor):
    _VALID_URL = r'https?://steamcommunity\.(?:com)/broadcast/watch/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://steamcommunity.com/broadcast/watch/76561199037072858',
        'only_matching': True,
    }]
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._download_json(
            f'https://steamcommunity.com/broadcast/getbroadcastmpd/',
            video_id, query={'steamid': f'{video_id}'}
        )
        formats = []
        mpd_formats, mpd_subs = self._extract_mpd_formats_and_subtitles(json_data['url'], video_id)
        format_, subs = self._extract_m3u8_formats_and_subtitles(json_data['hls_url'], video_id)
        
        formats.extend(format_)
        formats.extend(mpd_formats)
        
        uploader_json = self._download_json(
            f'https://steamcommunity.com/actions/ajaxresolveusers',
            video_id, query={'steamids': f'{video_id}'})[0]  # assume the data only one
        
        # TODO: get chat from 'view_url_template' in https://steamcommunity.com/broadcast/getchatinfo?steamid={video_id}
        # the chat is using '0' as first chat id and then changed based on '47639818'
        # the chat need requested regulary, i think https://github.com/yt-dlp/yt-dlp/pull/3048 can help
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': self._html_extract_title(webpage) or self._og_search_title(webpage),
            'formats': formats,
            'live_status': 'is_live',
            'view_count': json_data.get('num_view'),
            'uploader': uploader_json.get('persona_name'),
            'uploader_id': uploader_json.get('accountid'),
            
        }
        
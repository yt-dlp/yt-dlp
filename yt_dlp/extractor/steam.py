import json

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    join_nonempty,
    js_to_json,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
    trim_str,
)


class SteamIE(InfoExtractor):
    _VALID_URL = r'https?://store\.steampowered\.com(?:/agecheck)?/app/(?P<id>\d+)/?(?:[^?/#]+/?)?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://store.steampowered.com/app/105600',
        'info_dict': {
            'id': '105600',
            'title': 'Terraria',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://store.steampowered.com/app/271590/Grand_Theft_Auto_V/',
        'info_dict': {
            'id': '271590',
            'title': 'Grand Theft Auto V Legacy',
        },
        'playlist_mincount': 26,
    }]

    def _real_extract(self, url):
        app_id = self._match_id(url)

        self._set_cookie('store.steampowered.com', 'wants_mature_content', '1')
        self._set_cookie('store.steampowered.com', 'birthtime', '946652401')
        self._set_cookie('store.steampowered.com', 'lastagecheckage', '1-January-2000')

        webpage = self._download_webpage(url, app_id)
        app_name = traverse_obj(webpage, ({find_element(cls='apphub_AppName')}, {clean_html}))

        entries = []
        for data_prop in traverse_obj(webpage, (
            {find_elements(cls='highlight_player_item highlight_movie', html=True)},
            ..., {extract_attributes}, 'data-props', {json.loads}, {dict},
        )):
            formats = []
            if hls_manifest := traverse_obj(data_prop, ('hlsManifest', {url_or_none})):
                formats.extend(self._extract_m3u8_formats(
                    hls_manifest, app_id, 'mp4', m3u8_id='hls', fatal=False))
            for dash_manifest in traverse_obj(data_prop, ('dashManifests', ..., {url_or_none})):
                formats.extend(self._extract_mpd_formats(
                    dash_manifest, app_id, mpd_id='dash', fatal=False))

            movie_id = traverse_obj(data_prop, ('id', {trim_str(start='highlight_movie_')}))
            entries.append({
                'id': movie_id,
                'title': join_nonempty(app_name, 'video', movie_id, delim=' '),
                'formats': formats,
                'series': app_name,
                'series_id': app_id,
                'thumbnail': traverse_obj(data_prop, ('screenshot', {url_or_none})),
            })

        return self.playlist_result(entries, app_id, app_name)


class SteamCommunityIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?steamcommunity\.com/sharedfiles/filedetails(?:/?\?(?:[^#]+&)?id=|/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://steamcommunity.com/sharedfiles/filedetails/2717708756',
        'info_dict': {
            'id': '39Sp2mB1Ly8',
            'ext': 'mp4',
            'title': 'Gmod Stamina System + Customisable HUD',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Gaming'],
            'channel': 'Zworld Gmod',
            'channel_follower_count': int,
            'channel_id': 'UCER1FWFSdMMiTKBnnEDBPaw',
            'channel_url': 'https://www.youtube.com/channel/UCER1FWFSdMMiTKBnnEDBPaw',
            'chapters': 'count:3',
            'comment_count': int,
            'description': 'md5:0ba8d8e550231211fa03fac920e5b0bf',
            'duration': 162,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:20',
            'thumbnail': r're:https?://i\.ytimg\.com/vi/.+',
            'timestamp': 1641955348,
            'upload_date': '20220112',
            'uploader': 'Zworld Gmod',
            'uploader_id': '@gmod-addons',
            'uploader_url': 'https://www.youtube.com/@gmod-addons',
            'view_count': int,
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://steamcommunity.com/sharedfiles/filedetails/?id=3544291945',
        'info_dict': {
            'id': '5JZZlsAdsvI',
            'ext': 'mp4',
            'title': 'Memories',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Gaming'],
            'channel': 'Bombass Team',
            'channel_follower_count': int,
            'channel_id': 'UCIJgtNyCV53IeSkzg3FWSFA',
            'channel_url': 'https://www.youtube.com/channel/UCIJgtNyCV53IeSkzg3FWSFA',
            'comment_count': int,
            'description': 'md5:1b8a103a5d67a3c48d07c065de7e2c63',
            'duration': 83,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:10',
            'thumbnail': r're:https?://i\.ytimg\.com/vi/.+',
            'timestamp': 1754427291,
            'upload_date': '20250805',
            'uploader': 'Bombass Team',
            'uploader_id': '@BombassTeam',
            'uploader_url': 'https://www.youtube.com/@BombassTeam',
            'view_count': int,
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        file_id = self._match_id(url)
        webpage = self._download_webpage(url, file_id)

        flashvars = self._search_json(
            r'var\s+rgMovieFlashvars\s*=', webpage, 'flashvars',
            file_id, default={}, transform_source=js_to_json)
        youtube_id = (
            traverse_obj(flashvars, (..., 'YOUTUBE_VIDEO_ID', {str}, any))
            or traverse_obj(webpage, (
                {find_element(cls='movieFrame modal', html=True)}, {extract_attributes}, 'id', {str})))
        if not youtube_id:
            raise ExtractorError('No video found', expected=True)

        return self.url_result(youtube_id, YoutubeIE)


class SteamCommunityBroadcastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?steamcommunity\.com/broadcast/watch/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://steamcommunity.com/broadcast/watch/76561199073851486',
        'info_dict': {
            'id': '76561199073851486',
            'ext': 'mp4',
            'title': str,
            'uploader_id': '1113585758',
            'uploader': 'pepperm!nt',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'Livestream'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._download_json(
            'https://steamcommunity.com/broadcast/getbroadcastmpd/',
            video_id, query={'steamid': f'{video_id}'})

        formats, subs = self._extract_m3u8_formats_and_subtitles(json_data['hls_url'], video_id)

        ''' # We cannot download live dash atm
        mpd_formats, mpd_subs = self._extract_mpd_formats_and_subtitles(json_data['url'], video_id)
        formats.extend(mpd_formats)
        self._merge_subtitles(mpd_subs, target=subs)
        '''

        uploader_json = self._download_json(
            'https://steamcommunity.com/actions/ajaxresolveusers',
            video_id, query={'steamids': video_id})[0]

        return {
            'id': video_id,
            'title': self._generic_title('', webpage),
            'formats': formats,
            'live_status': 'is_live',
            'view_count': json_data.get('num_view'),
            'uploader': uploader_json.get('persona_name'),
            'uploader_id': str_or_none(uploader_json.get('accountid')),
            'subtitles': subs,
        }

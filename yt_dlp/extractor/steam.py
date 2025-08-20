import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
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
    _VALID_URL = r'''(?x)
        https?://(?:store\.steampowered|steamcommunity)\.com/
            (?:agecheck/)?
            (?P<urltype>video|app)/ #If the page is only for videos or for a game
            (?P<gameID>\d+)/?
            (?P<videoID>\d*)(?P<extra>\??) # For urltype == video we sometimes get the videoID
        |
        https?://(?:www\.)?steamcommunity\.com/sharedfiles/filedetails/\?id=(?P<fileID>[0-9]+)
    '''
    _VIDEO_PAGE_TEMPLATE = 'https://store.steampowered.com/video/%s/'
    _AGECHECK_TEMPLATE = 'https://store.steampowered.com/agecheck/video/%s/?snr=1_agecheck_agecheck__age-gate&ageDay=1&ageMonth=January&ageYear=1970'
    _TESTS = [{
        'url': 'https://store.steampowered.com/video/105600/',
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
        m = self._match_valid_url(url)
        file_id = m.group('fileID')
        if file_id:
            video_url = url
            playlist_id = file_id
        else:
            game_id = m.group('gameID')
            playlist_id = game_id
            video_url = self._VIDEO_PAGE_TEMPLATE % playlist_id

        self._set_cookie('steampowered.com', 'wants_mature_content', '1')
        self._set_cookie('steampowered.com', 'birthtime', '944006401')
        self._set_cookie('steampowered.com', 'lastagecheckage', '1-0-2000')

        webpage = self._download_webpage(video_url, playlist_id)

        if re.search('<div[^>]+>Please enter your birth date to continue:</div>', webpage) is not None:
            video_url = self._AGECHECK_TEMPLATE % playlist_id
            self.report_age_confirmation()
            webpage = self._download_webpage(video_url, playlist_id)

        app_name = traverse_obj(webpage, ({find_element(cls='apphub_AppName')}, {clean_html}))
        entries = []
        for data_prop in traverse_obj(webpage, (
            {find_elements(cls='highlight_player_item highlight_movie', html=True)},
            ..., {extract_attributes}, 'data-props', {json.loads}, {dict},
        )):
            formats = []
            if hls_manifest := traverse_obj(data_prop, ('hlsManifest', {url_or_none})):
                formats.extend(self._extract_m3u8_formats(
                    hls_manifest, playlist_id, 'mp4', m3u8_id='hls', fatal=False))

            for dash_manifest in traverse_obj(data_prop, ('dashManifests', ..., {url_or_none})):
                formats.extend(self._extract_mpd_formats(
                    dash_manifest, playlist_id, mpd_id='dash', fatal=False))

            movie_id = traverse_obj(data_prop, ('id', {trim_str(start='highlight_movie_')}))
            entries.append({
                'id': movie_id,
                'title': f'{app_name} video {movie_id}',
                'formats': formats,
                'thumbnail': traverse_obj(data_prop, ('screenshot', {url_or_none})),
            })

        embedded_videos = re.findall(r'(<iframe[^>]+>)', webpage)
        for evideos in embedded_videos:
            evideos = extract_attributes(evideos).get('src')
            video_id = self._search_regex(r'youtube\.com/embed/([0-9A-Za-z_-]{11})', evideos, 'youtube_video_id', default=None)
            if video_id:
                entries.append({
                    '_type': 'url_transparent',
                    'id': video_id,
                    'url': video_id,
                    'ie_key': 'Youtube',
                })
        if not entries:
            raise ExtractorError('Could not find any videos')

        return self.playlist_result(entries, playlist_id, app_name)


class SteamCommunityBroadcastIE(InfoExtractor):
    _VALID_URL = r'https?://steamcommunity\.(?:com)/broadcast/watch/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://steamcommunity.com/broadcast/watch/76561199073851486',
        'info_dict': {
            'id': '76561199073851486',
            'title': r're:Steam Community :: pepperm!nt :: Broadcast 2022-06-26 \d{2}:\d{2}',
            'ext': 'mp4',
            'uploader_id': '1113585758',
            'uploader': 'pepperm!nt',
            'live_status': 'is_live',
        },
        'skip': 'Stream has ended',
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

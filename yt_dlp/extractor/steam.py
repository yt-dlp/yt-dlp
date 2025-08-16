import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_element_by_class,
    str_or_none,
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
    _VIDEO_PAGE_TEMPLATE = 'http://store.steampowered.com/video/%s/'
    _AGECHECK_TEMPLATE = 'http://store.steampowered.com/agecheck/video/%s/?snr=1_agecheck_agecheck__age-gate&ageDay=1&ageMonth=January&ageYear=1970'
    _TESTS = [{
        'url': 'http://store.steampowered.com/video/105600/',
        'playlist': [
            {
                'md5': 'e800bd0baf47286d8b434d07b357247e',
                'info_dict': {
                    'id': '256785003',
                    'ext': 'mp4',
                    'title': 'Terraria video 256785003',
                    'thumbnail': r're:^https?://[^/]*steamstatic\.com',
                },
            },
            {
                'md5': '9612ee058ebd645371c5ddd69adb310f',
                'info_dict': {
                    'id': '2040428',
                    'ext': 'mp4',
                    'title': 'Terraria video 2040428',
                    'thumbnail': r're:^https?://[^/]*steamstatic\.com',
                },
            },
        ],
        'info_dict': {
            'id': '105600',
            'title': 'Terraria',
        },
        'params': {
            'playlistend': 2,
        },
    }, {
        'url': 'https://store.steampowered.com/app/271590/Grand_Theft_Auto_V/',
        'info_dict': {
            'id': '271590',
            'title': 'Grand Theft Auto V',
        },
        'playlist_count': 23,
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

        videos = re.findall(r'(<div[^>]+id=[\'"]highlight_movie_(\d+)[\'"][^>]+>)', webpage)
        entries = []
        playlist_title = get_element_by_class('apphub_AppName', webpage)
        for movie, movie_id in videos:
            if not movie:
                continue
            movie = extract_attributes(movie)
            if not movie_id:
                continue
            entry = {
                'id': movie_id,
                'title': f'{playlist_title} video {movie_id}',
            }
            formats = []
            if movie:
                data = self._parse_json(movie['data-props'], video_id=movie_id)

                entry['thumbnail'] = data.get('screenshot')

                for dash_url in data.get('dashManifests', []):
                    formats.extend(self._extract_mpd_formats(
                        dash_url, movie_id, mpd_id='dash', fatal=False))

                hls_url = data.get('hlsManifest')
                if hls_url:
                    formats.extend(self._extract_m3u8_formats(
                        hls_url, movie_id, entry_protocol='m3u8', m3u8_id='hls', fatal=False))

            entry['formats'] = formats
            entries.append(entry)
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

        return self.playlist_result(entries, playlist_id, playlist_title)


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

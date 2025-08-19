import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    jwt_decode_hs256,
    jwt_is_expired,
    parse_age_limit,
    str_or_none,
    try_call,
    try_get,
    unified_strdate,
    unified_timestamp,
    url_or_none,
)


class Zee5IE(InfoExtractor):
    _VALID_URL = r'''(?x)
                     (?:
                        zee5:|
                        https?://(?:www\.)?zee5\.com/(?:[^#?]+/)?
                        (?:
                            (?:tv-shows|kids|web-series|zee5originals)(?:/[^#/?]+){3}
                            |(?:movies|kids|videos|news|music-videos)/(?!kids-shows)[^#/?]+
                        )/(?P<display_id>[^#/?]+)/
                     )
                     (?P<id>[^#/?]+)/?(?:$|[?#])
                     '''
    _TESTS = [{
        'url': 'https://www.zee5.com/movies/details/adavari-matalaku-ardhale-verule/0-0-movie_1143162669',
        'info_dict': {
            'id': '0-0-movie_1143162669',
            'ext': 'mp4',
            'display_id': 'adavari-matalaku-ardhale-verule',
            'title': 'Adavari Matalaku Ardhale Verule',
            'duration': 9360,
            'description': str,
            'alt_title': 'Adavari Matalaku Ardhale Verule',
            'uploader': 'Zee Entertainment Enterprises Ltd',
            'release_date': '20070427',
            'upload_date': '20070427',
            'timestamp': 1177632000,
            'thumbnail': r're:^https?://.*\.jpg$',
            'episode_number': 0,
            'episode': 'Episode 0',
            'tags': list,
        },
        'params': {
            'format': 'bv',
        },
    }, {
        'url': 'https://www.zee5.com/kids/kids-shows/bandbudh-aur-budbak/0-6-1899/yoga-se-hoga-bandbudh-aur-budbak/0-1-239839',
        'info_dict': {
            'id': '0-1-239839',
            'ext': 'mp4',
            'display_id': 'yoga-se-hoga-bandbudh-aur-budbak',
            'title': 'Yoga Se Hoga-Bandbudh aur Budbak',
            'duration': 659,
            'description': str,
            'alt_title': 'Yoga Se Hoga-Bandbudh aur Budbak',
            'uploader': 'Zee Entertainment Enterprises Ltd',
            'release_date': '20150101',
            'upload_date': '20150101',
            'timestamp': 1420070400,
            'thumbnail': r're:^https?://.*\.jpg$',
            'series': 'Bandbudh Aur Budbak',
            'season_number': 1,
            'episode_number': 1,
            'episode': 'Episode 1',
            'season': 'Season 1',
            'tags': list,
        },
        'params': {
            'format': 'bv',
        },
    }, {
        'url': 'https://www.zee5.com/hi/tv-shows/details/kundali-bhagya/0-6-366/kundali-bhagya-march-08-2021/0-1-manual_7g9jv1os7730?country=IN',
        'only_matching': True,
    }, {
        'url': 'https://www.zee5.com/global/hi/tv-shows/details/kundali-bhagya/0-6-366/kundali-bhagya-march-08-2021/0-1-manual_7g9jv1os7730',
        'only_matching': True,
    }, {
        'url': 'https://www.zee5.com/web-series/details/mithya/0-6-4z587408/maine-dekhi-hai-uski-mrityu/0-1-6z587412',
        'only_matching': True,
    }, {
        'url': 'https://www.zee5.com/kids/kids-movies/maya-bommalu/0-0-movie_1040370005',
        'only_matching': True,
    }, {
        'url': 'https://www.zee5.com/news/details/jana-sena-chief-pawan-kalyan-shows-slippers-to-ysrcp-leaders/0-0-newsauto_6ettj4242oo0',
        'only_matching': True,
    }, {
        'url': 'https://www.zee5.com/music-videos/details/adhento-gaani-vunnapaatuga-jersey-nani-shraddha-srinath/0-0-56973',
        'only_matching': True,
    }]
    _DEVICE_ID = str(uuid.uuid4())
    _USER_TOKEN = None
    _LOGIN_HINT = 'Use "--username <mobile_number>" to login using otp or "--username token" and "--password <user_token>" to login using user token.'
    _NETRC_MACHINE = 'zee5'
    _GEO_COUNTRIES = ['IN']
    _USER_COUNTRY = None

    def _perform_login(self, username, password):
        if len(username) == 10 and username.isdigit() and self._USER_TOKEN is None:
            self.report_login()
            otp_request_json = self._download_json(f'https://b2bapi.zee5.com/device/sendotp_v1.php?phoneno=91{username}',
                                                   None, note='Sending OTP')
            if otp_request_json['code'] == 0:
                self.to_screen(otp_request_json['message'])
            else:
                raise ExtractorError(otp_request_json['message'], expected=True)
            otp_code = self._get_tfa_info('OTP')
            otp_verify_json = self._download_json(f'https://b2bapi.zee5.com/device/verifyotp_v1.php?phoneno=91{username}&otp={otp_code}&guest_token={self._DEVICE_ID}&platform=web',
                                                  None, note='Verifying OTP', fatal=False)
            if not otp_verify_json:
                raise ExtractorError('Unable to verify OTP.', expected=True)
            self._USER_TOKEN = otp_verify_json.get('token')
            if not self._USER_TOKEN:
                raise ExtractorError(otp_request_json['message'], expected=True)
        elif username.lower() == 'token' and try_call(lambda: jwt_decode_hs256(password)):
            self._USER_TOKEN = password
        else:
            raise ExtractorError(self._LOGIN_HINT, expected=True)

        if jwt_is_expired(self._USER_TOKEN):
            raise ExtractorError('User token has expired', expected=True)
        self._USER_COUNTRY = jwt_decode_hs256(self._USER_TOKEN).get('current_country')

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        access_token_request = self._download_json(
            'https://launchapi.zee5.com/launch?platform_name=web_app',
            video_id, note='Downloading access token')['platform_token']
        data = {
            'x-access-token': access_token_request['token'],
        }
        if self._USER_TOKEN:
            data['Authorization'] = f'bearer {self._USER_TOKEN}'
        else:
            data['X-Z5-Guest-Token'] = self._DEVICE_ID

        json_data = self._download_json(
            'https://spapi.zee5.com/singlePlayback/getDetails/secure', video_id, query={
                'content_id': video_id,
                'device_id': self._DEVICE_ID,
                'platform_name': 'desktop_web',
                'country': self._USER_COUNTRY or self.get_param('geo_bypass_country') or 'IN',
                'check_parental_control': False,
            }, headers={'content-type': 'application/json'}, data=json.dumps(data).encode())
        asset_data = json_data['assetDetails']
        show_data = json_data.get('showDetails', {})
        if 'premium' in asset_data['business_type']:
            raise ExtractorError('Premium content is DRM protected.', expected=True)
        if not asset_data.get('hls_url'):
            self.raise_login_required(self._LOGIN_HINT, metadata_available=True, method=None)
        formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(asset_data['hls_url'], video_id, 'mp4', fatal=False)

        subtitles = {}
        for sub in asset_data.get('subtitle_url', []):
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('language', 'en'), []).append({
                'url': self._proto_relative_url(sub_url),
            })
        subtitles = self._merge_subtitles(subtitles, m3u8_subs)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': asset_data['title'],
            'formats': formats,
            'subtitles': subtitles,
            'duration': int_or_none(asset_data.get('duration')),
            'description': str_or_none(asset_data.get('description')),
            'alt_title': str_or_none(asset_data.get('original_title')),
            'uploader': str_or_none(asset_data.get('content_owner')),
            'age_limit': parse_age_limit(asset_data.get('age_rating')),
            'release_date': unified_strdate(asset_data.get('release_date')),
            'timestamp': unified_timestamp(asset_data.get('release_date')),
            'thumbnail': url_or_none(asset_data.get('image_url')),
            'series': str_or_none(asset_data.get('tvshow_name')),
            'season': try_get(show_data, lambda x: x['seasons']['title'], str),
            'season_number': int_or_none(try_get(show_data, lambda x: x['seasons'][0]['orderid'])),
            'episode_number': int_or_none(try_get(asset_data, lambda x: x['orderid'])),
            'tags': try_get(asset_data, lambda x: x['tags'], list),
        }


class Zee5SeriesIE(InfoExtractor):
    IE_NAME = 'zee5:series'
    _VALID_URL = r'''(?x)
                     (?:
                        zee5:series:|
                        https?://(?:www\.)?zee5\.com/(?:[^#?]+/)?
                        (?:tv-shows|web-series|kids|zee5originals)/(?!kids-movies)(?:[^#/?]+/){2}
                     )
                     (?P<id>[^#/?]+)(?:/episodes)?/?(?:$|[?#])
                     '''
    _TESTS = [{
        'url': 'https://www.zee5.com/kids/kids-shows/bandbudh-aur-budbak/0-6-1899',
        'playlist_mincount': 156,
        'info_dict': {
            'id': '0-6-1899',
        },
    }, {
        'url': 'https://www.zee5.com/tv-shows/details/bhabi-ji-ghar-par-hai/0-6-199',
        'playlist_mincount': 1500,
        'info_dict': {
            'id': '0-6-199',
        },
    }, {
        'url': 'https://www.zee5.com/tv-shows/details/agent-raghav-crime-branch/0-6-965',
        'playlist_mincount': 24,
        'info_dict': {
            'id': '0-6-965',
        },
    }, {
        'url': 'https://www.zee5.com/ta/tv-shows/details/nagabhairavi/0-6-3201',
        'playlist_mincount': 3,
        'info_dict': {
            'id': '0-6-3201',
        },
    }, {
        'url': 'https://www.zee5.com/global/hi/tv-shows/details/khwaabon-ki-zamin-par/0-6-270',
        'playlist_mincount': 150,
        'info_dict': {
            'id': '0-6-270',
        },
    }, {
        'url': 'https://www.zee5.com/tv-shows/details/chala-hawa-yeu-dya-ladies-zindabaad/0-6-2943/episodes',
        'only_matching': True,
    }, {
        'url': 'https://www.zee5.com/web-series/details/mithya/0-6-4z587408',
        'only_matching': True,
    }]

    def _entries(self, show_id):
        access_token_request = self._download_json(
            'https://launchapi.zee5.com/launch?platform_name=web_app',
            show_id, note='Downloading access token')['platform_token']
        headers = {
            'X-Access-Token': access_token_request['token'],
            'Referer': 'https://www.zee5.com/',
        }
        show_url = f'https://gwapi.zee5.com/content/tvshow/{show_id}?translation=en&country=IN'

        page_num = 0
        show_json = self._download_json(show_url, video_id=show_id, headers=headers)
        for season in show_json.get('seasons') or []:
            season_id = try_get(season, lambda x: x['id'], str)
            next_url = f'https://gwapi.zee5.com/content/tvshow/?season_id={season_id}&type=episode&translation=en&country=IN&on_air=false&asset_subtype=tvshow&page=1&limit=100'
            while next_url:
                page_num += 1
                episodes_json = self._download_json(
                    next_url, video_id=show_id, headers=headers,
                    note=f'Downloading JSON metadata page {page_num}')
                for episode in try_get(episodes_json, lambda x: x['episode'], list) or []:
                    video_id = episode.get('id')
                    yield self.url_result(
                        f'zee5:{video_id}',
                        ie=Zee5IE.ie_key(), video_id=video_id)
                next_url = url_or_none(episodes_json.get('next_episode_api'))

    def _real_extract(self, url):
        show_id = self._match_id(url)
        return self.playlist_result(self._entries(show_id), playlist_id=show_id)

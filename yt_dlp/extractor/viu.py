import re
import json
import uuid
import random
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_str
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    merge_dicts,
    remove_end,
    strip_or_none,
    traverse_obj,
    try_get,
    smuggle_url,
    unified_timestamp,
    unsmuggle_url,
    url_or_none,
)


class ViuBaseIE(InfoExtractor):
    def _call_api(self, path, *args, headers={}, **kwargs):
        response = self._download_json(
            f'https://www.viu.com/api/{path}', *args, **kwargs,
            headers={**self.geo_verification_headers(), **headers})['response']
        if response.get('status') != 'success':
            raise ExtractorError(f'{self.IE_NAME} said: {response["message"]}', expected=True)
        return response


class ViuIE(ViuBaseIE):
    _VALID_URL = r'(?:viu:|https?://[^/]+\.viu\.com/[a-z]{2}/media/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.viu.com/en/media/1116705532?containerId=playlist-22168059',
        'info_dict': {
            'id': '1116705532',
            'ext': 'mp4',
            'title': 'Citizen Khan - Ep 1',
            'description': 'md5:d7ea1604f49e5ba79c212c551ce2110e',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
        'skip': 'Geo-restricted to India',
    }, {
        'url': 'https://www.viu.com/en/media/1130599965',
        'info_dict': {
            'id': '1130599965',
            'ext': 'mp4',
            'title': 'Jealousy Incarnate - Episode 1',
            'description': 'md5:d3d82375cab969415d2720b6894361e9',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
        'skip': 'Geo-restricted to Indonesia',
    }, {
        'url': 'https://india.viu.com/en/media/1126286865',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._call_api(
            'clip/load', video_id, 'Downloading video data', query={
                'appid': 'viu_desktop',
                'fmt': 'json',
                'id': video_id
            })['item'][0]

        title = video_data['title']

        m3u8_url = None
        url_path = video_data.get('urlpathd') or video_data.get('urlpath')
        tdirforwhole = video_data.get('tdirforwhole')
        # #EXT-X-BYTERANGE is not supported by native hls downloader
        # and ffmpeg (#10955)
        # FIXME: It is supported in yt-dlp
        # hls_file = video_data.get('hlsfile')
        hls_file = video_data.get('jwhlsfile')
        if url_path and tdirforwhole and hls_file:
            m3u8_url = '%s/%s/%s' % (url_path, tdirforwhole, hls_file)
        else:
            # m3u8_url = re.sub(
            #     r'(/hlsc_)[a-z]+(\d+\.m3u8)',
            #     r'\1whe\2', video_data['href'])
            m3u8_url = video_data['href']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4')

        for key, value in video_data.items():
            mobj = re.match(r'^subtitle_(?P<lang>[^_]+)_(?P<ext>(vtt|srt))', key)
            if not mobj:
                continue
            subtitles.setdefault(mobj.group('lang'), []).append({
                'url': value,
                'ext': mobj.group('ext')
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'series': video_data.get('moviealbumshowname'),
            'episode': title,
            'episode_number': int_or_none(video_data.get('episodeno')),
            'duration': int_or_none(video_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
        }


class ViuPlaylistIE(ViuBaseIE):
    IE_NAME = 'viu:playlist'
    _VALID_URL = r'https?://www\.viu\.com/[^/]+/listing/playlist-(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.viu.com/en/listing/playlist-22461380',
        'info_dict': {
            'id': '22461380',
            'title': 'The Good Wife',
        },
        'playlist_count': 16,
        'skip': 'Geo-restricted to Indonesia',
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_data = self._call_api(
            'container/load', playlist_id,
            'Downloading playlist info', query={
                'appid': 'viu_desktop',
                'fmt': 'json',
                'id': 'playlist-' + playlist_id
            })['container']

        entries = []
        for item in playlist_data.get('item', []):
            item_id = item.get('id')
            if not item_id:
                continue
            item_id = compat_str(item_id)
            entries.append(self.url_result(
                'viu:' + item_id, 'Viu', item_id))

        return self.playlist_result(
            entries, playlist_id, playlist_data.get('title'))


class ViuOTTIE(InfoExtractor):
    IE_NAME = 'viu:ott'
    _NETRC_MACHINE = 'viu'
    _VALID_URL = r'https?://(?:www\.)?viu\.com/ott/(?P<country_code>[a-z]{2})/(?P<lang_code>[a-z]{2}(?:-[a-z]{2})?)/vod/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.viu.com/ott/sg/en-us/vod/3421/The%20Prime%20Minister%20and%20I',
        'info_dict': {
            'id': '3421',
            'ext': 'mp4',
            'title': 'A New Beginning',
            'description': 'md5:1e7486a619b6399b25ba6a41c0fe5b2c',
        },
        'params': {
            'skip_download': 'm3u8 download',
            'noplaylist': True,
        },
        'skip': 'Geo-restricted to Singapore',
    }, {
        'url': 'https://www.viu.com/ott/hk/zh-hk/vod/430078/%E7%AC%AC%E5%85%AD%E6%84%9F-3',
        'info_dict': {
            'id': '430078',
            'ext': 'mp4',
            'title': '大韓民國的1%',
            'description': 'md5:74d6db47ddd9ddb9c89a05739103ccdb',
            'episode_number': 1,
            'duration': 6614,
            'episode': '大韓民國的1%',
            'series': '第六感 3',
            'thumbnail': 'https://d2anahhhmp1ffz.cloudfront.net/1313295781/d2b14f48d008ef2f3a9200c98d8e9b63967b9cc2',
        },
        'params': {
            'skip_download': 'm3u8 download',
            'noplaylist': True,
        },
        'skip': 'Geo-restricted to Hong Kong',
    }, {
        'url': 'https://www.viu.com/ott/hk/zh-hk/vod/444666/%E6%88%91%E7%9A%84%E5%AE%A4%E5%8F%8B%E6%98%AF%E4%B9%9D%E5%B0%BE%E7%8B%90',
        'playlist_count': 16,
        'info_dict': {
            'id': '23807',
            'title': '我的室友是九尾狐',
            'description': 'md5:b42c95f2b4a316cdd6ae14ca695f33b9',
        },
        'params': {
            'skip_download': 'm3u8 download',
            'noplaylist': False,
        },
        'skip': 'Geo-restricted to Hong Kong',
    }, {
        'url': 'https://www.viu.com/ott/id/id/vod/2221644/Detective-Conan',
        'info_dict': {
            'id': '2221644',
            'ext': 'mp4',
            'description': 'md5:b199bcdb07b1e01a03529f155349ddd5',
            'duration': 1425,
            'series': 'Detective Conan',
            'title': 'Detective Conan - Episode 1150',
            'episode': 'Detective Conan - Episode 1150',
            'episode_number': 1150,
            'thumbnail': r're:https?://prod-images\.viu\.com/clip_asset_v6/\d+/\d+/[a-f0-9]+',
        }
    }]

    _AREA_ID = {
        'HK': 1,
        'SG': 2,
        'TH': 4,
        'PH': 5,
    }
    _LANGUAGE_FLAG = {
        'zh-hk': 1,
        'zh-cn': 2,
        'en-us': 3,
    }

    _user_token = None
    _auth_codes = {}

    def _detect_error(self, response):
        code = try_get(response, lambda x: x['status']['code'])
        if code and code > 0:
            message = try_get(response, lambda x: x['status']['message'])
            raise ExtractorError(f'{self.IE_NAME} said: {message} ({code})', expected=True)
        return response.get('data') or {}

    def _login(self, country_code, video_id):
        if self._user_token is None:
            username, password = self._get_login_info()
            if username is None:
                return
            headers = {
                'Authorization': f'Bearer {self._auth_codes[country_code]}',
                'Content-Type': 'application/json'
            }
            data = self._download_json(
                'https://api-gateway-global.viu.com/api/account/validate',
                video_id, 'Validating email address', headers=headers,
                data=json.dumps({
                    'principal': username,
                    'provider': 'email'
                }).encode())
            if not data.get('exists'):
                raise ExtractorError('Invalid email address')

            data = self._download_json(
                'https://api-gateway-global.viu.com/api/auth/login',
                video_id, 'Logging in', headers=headers,
                data=json.dumps({
                    'email': username,
                    'password': password,
                    'provider': 'email',
                }).encode())
            self._detect_error(data)
            self._user_token = data.get('identity')
            # need to update with valid user's token else will throw an error again
            self._auth_codes[country_code] = data.get('token')
        return self._user_token

    def _get_token(self, country_code, video_id):
        rand = ''.join(random.choices('0123456789', k=10))
        return self._download_json(
            f'https://api-gateway-global.viu.com/api/auth/token?v={rand}000', video_id,
            headers={'Content-Type': 'application/json'}, note='Getting bearer token',
            data=json.dumps({
                'countryCode': country_code.upper(),
                'platform': 'browser',
                'platformFlagLabel': 'web',
                'language': 'en',
                'uuid': str(uuid.uuid4()),
                'carrierId': '0'
            }).encode('utf-8'))['token']

    def _real_extract(self, url):
        url, idata = unsmuggle_url(url, {})
        country_code, lang_code, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, video_id, fatal=False)
        json_ld = self._search_json_ld(webpage, video_id, fatal=False)
        next_js_data = (self._search_nextjs_data(webpage, video_id, fatal=False) or {}).get('props')
        runtime_info = traverse_obj(next_js_data, ('initialState', 'app', 'runtimeInfo'))

        query = {
            'r': 'vod/ajax-detail',
            'platform_flag_label': 'web',
            'product_id': video_id,
        }

        area_id = self._AREA_ID.get(country_code.upper()) or runtime_info.get('areaId')
        if area_id:
            query['area_id'] = area_id

        try:
            product_data = self._download_json(
                f'http://www.viu.com/ott/{country_code}/index.php', video_id,
                'Downloading video info', query=query)['data']
        # The `fatal` in `_download_json` didn't prevent json error
        # FIXME: probably the error still too broad
        except ExtractorError as e:
            if not isinstance(e.cause, (json.JSONDecodeError, HTTPError)):
                raise
            # NOTE: some geo-blocked like https://www.viu.com/ott/sg/en/vod/108599/The-Beauty-Inside actually can bypassed
            # on other region (like in ID)
            product_data = traverse_obj(
                next_js_data, ('pageProps', 'fallback', lambda k, v: v if re.match(r'@"PRODUCT_DETAIL"[^:]+', k) else None),
                get_all=False)['data']

        video_data = product_data.get('current_product')
        if not video_data:
            self.raise_geo_restricted()

        series_id = video_data.get('series_id') or traverse_obj(product_data, ('series', 'series_id'))
        if self._yes_playlist(series_id, video_id, idata):
            series = product_data.get('series') or traverse_obj(product_data, ('series', 'name')) or {}
            product = series.get('product')
            if product:
                entries = []
                for entry in sorted(product, key=lambda x: int_or_none(x.get('number', 0))):
                    item_id = entry.get('product_id')
                    if not item_id:
                        continue
                    entries.append(self.url_result(
                        smuggle_url(f'http://www.viu.com/ott/{country_code}/{lang_code}/vod/{item_id}/',
                                    {'force_noplaylist': True}),
                        ViuOTTIE, str(item_id), entry.get('synopsis', '').strip()))

                return self.playlist_result(entries, series_id, series.get('name'), series.get('description'))

        duration_limit = False
        query = {
            'ccs_product_id': video_data['ccs_product_id'],
            'language_flag_id': self._LANGUAGE_FLAG.get(lang_code.lower()) or runtime_info.get('languageFlagId') or '3',
            'platform_flag_label': 'web',
            'countryCode': country_code.upper()
        }

        def download_playback():
            stream_data = self._download_json(
                'https://api-gateway-global.viu.com/api/playback/distribute',
                video_id=video_id, query=query, fatal=False, note='Downloading stream info',
                headers={
                    'Authorization': f'Bearer {self._auth_codes[country_code]}',
                    'Referer': url,
                    'Origin': url
                })
            return self._detect_error(stream_data).get('stream')

        if not self._auth_codes.get(country_code):
            self._auth_codes[country_code] = self._get_token(country_code, video_id)

        stream_data = None
        try:
            stream_data = download_playback()
        except (ExtractorError, KeyError):
            token = self._login(country_code, video_id)
            if token is not None:
                query['identity'] = token
            else:
                # The content is Preview or for VIP only.
                # We can try to bypass the duration which is limited to 3mins only
                duration_limit, query['duration'] = True, '180'
            try:
                stream_data = download_playback()
            except (ExtractorError, KeyError):
                if token is not None:
                    raise
                self.raise_login_required(method='password')
        if not stream_data:
            raise ExtractorError('Cannot get stream info', expected=True)

        formats = []
        for vid_format, stream_url in (stream_data.get('url') or {}).items():
            height = int(self._search_regex(r's(\d+)p', vid_format, 'height', default=None))

            # bypass preview duration limit
            if duration_limit:
                old_stream_url = urllib.parse.urlparse(stream_url)
                query = dict(urllib.parse.parse_qsl(old_stream_url.query, keep_blank_values=True))
                query.update({
                    'duration': video_data.get('time_duration') or '9999999',
                    'duration_start': '0',
                })
                stream_url = old_stream_url._replace(query=urllib.parse.urlencode(query)).geturl()

            formats.append({
                'format_id': vid_format,
                'url': stream_url,
                'height': height,
                'ext': 'mp4',
                'filesize': try_get(stream_data, lambda x: x['size'][vid_format], int)
            })

        subtitles = {}
        for sub in video_data.get('subtitle') or []:
            lang = sub.get('name') or 'und'
            if sub.get('url'):
                subtitles.setdefault(lang, []).append({
                    'url': sub['url'],
                    'ext': 'srt',
                    'name': f'Spoken text for {lang}',
                })
            if sub.get('second_subtitle_url'):
                subtitles.setdefault(f'{lang}_ost', []).append({
                    'url': sub['second_subtitle_url'],
                    'ext': 'srt',
                    'name': f'On-screen text for {lang}',
                })

        title = strip_or_none(video_data.get('synopsis'))
        return merge_dicts({
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'series': try_get(product_data, lambda x: x['series']['name']),
            'episode': title,
            'episode_number': int_or_none(video_data.get('number')),
            'duration': int_or_none(stream_data.get('duration')),
            'thumbnail': url_or_none(video_data.get('cover_image_url')),
            'formats': formats,
            'subtitles': subtitles,
        }, traverse_obj(json_ld, {
            'thumbnails': 'thumbnails',
            'title': 'title',
            'episode': 'episode',
            'episode_number': 'episode_number'
        }))


class ViuOTTIndonesiaBaseIE(InfoExtractor):
    _BASE_QUERY = {
        'ver': 1.0,
        'fmt': 'json',
        'aver': 5.0,
        'appver': 2.0,
        'appid': 'viu_desktop',
        'platform': 'desktop',
    }

    _DEVICE_ID = str(uuid.uuid4())
    _SESSION_ID = str(uuid.uuid4())
    _TOKEN = None

    _HEADERS = {
        'x-session-id': _SESSION_ID,
        'x-client': 'browser'
    }

    _AGE_RATINGS_MAPPER = {
        'ADULTS': 18,
        'teens': 13
    }

    def _real_initialize(self):
        ViuOTTIndonesiaBaseIE._TOKEN = self._download_json(
            'https://um.viuapi.io/user/identity', None,
            headers={'Content-type': 'application/json', **self._HEADERS},
            query={**self._BASE_QUERY, 'iid': self._DEVICE_ID},
            data=json.dumps({'deviceId': self._DEVICE_ID}).encode(),
            note='Downloading token information')['token']


class ViuOTTIndonesiaIE(ViuOTTIndonesiaBaseIE):
    _VALID_URL = r'https?://www\.viu\.com/ott/\w+/\w+/all/video-[\w-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.viu.com/ott/id/id/all/video-japanese-drama-tv_shows-detective_conan_episode_793-1165863142?containerId=playlist-26271226',
        'info_dict': {
            'id': '1165863142',
            'ext': 'mp4',
            'episode_number': 793,
            'episode': 'Episode 793',
            'title': 'Detective Conan - Episode 793',
            'duration': 1476,
            'description': 'md5:b79d55345bc1e0217ece22616267c9a5',
            'thumbnail': 'https://vuclipi-a.akamaihd.net/p/cloudinary/h_171,w_304,dpr_1.5,f_auto,c_thumb,q_auto:low/1165863189/d-1',
            'upload_date': '20210101',
            'timestamp': 1609459200,
        }
    }, {
        'url': 'https://www.viu.com/ott/id/id/all/video-korean-reality-tv_shows-entertainment_weekly_episode_1622-1118617054',
        'info_dict': {
            'id': '1118617054',
            'ext': 'mp4',
            'episode_number': 1622,
            'episode': 'Episode 1622',
            'description': 'md5:6d68ca450004020113e9bf27ad99f0f8',
            'title': 'Entertainment Weekly - Episode 1622',
            'duration': 4729,
            'thumbnail': 'https://vuclipi-a.akamaihd.net/p/cloudinary/h_171,w_304,dpr_1.5,f_auto,c_thumb,q_auto:low/1120187848/d-1',
            'timestamp': 1420070400,
            'upload_date': '20150101',
            'cast': ['Shin Hyun-joon', 'Lee Da-Hee']
        }
    }, {
        # age-limit test
        'url': 'https://www.viu.com/ott/id/id/all/video-japanese-trailer-tv_shows-trailer_jujutsu_kaisen_ver_01-1166044219?containerId=playlist-26273140',
        'info_dict': {
            'id': '1166044219',
            'ext': 'mp4',
            'upload_date': '20200101',
            'timestamp': 1577836800,
            'title': 'Trailer \'Jujutsu Kaisen\' Ver.01',
            'duration': 92,
            'thumbnail': 'https://vuclipi-a.akamaihd.net/p/cloudinary/h_171,w_304,dpr_1.5,f_auto,c_thumb,q_auto:low/1166044240/d-1',
            'description': 'Trailer \'Jujutsu Kaisen\' Ver.01',
            'cast': ['Junya Enoki', ' Yûichi Nakamura', ' Yuma Uchida', 'Asami Seto'],
            'age_limit': 13,
        }
    }, {
        # json ld metadata type equal to Movie instead of TVEpisodes
        'url': 'https://www.viu.com/ott/id/id/all/video-japanese-animation-movies-demon_slayer_kimetsu_no_yaiba_the_movie_mugen_train-1165892707?containerId=1675060691786',
        'info_dict': {
            'id': '1165892707',
            'ext': 'mp4',
            'timestamp': 1577836800,
            'upload_date': '20200101',
            'title': 'Demon Slayer - Kimetsu no Yaiba - The Movie: Mugen Train',
            'age_limit': 13,
            'cast': 'count:9',
            'thumbnail': 'https://vuclipi-a.akamaihd.net/p/cloudinary/h_171,w_304,dpr_1.5,f_auto,c_thumb,q_auto:low/1165895279/d-1',
            'description': 'md5:1ce9c35a3aeab384085533f746c87469',
            'duration': 7021,
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_data = self._download_json(
            f'https://um.viuapi.io/drm/v1/content/{display_id}', display_id, data=b'',
            headers={'Authorization': ViuOTTIndonesiaBaseIE._TOKEN, **self._HEADERS, 'ccode': 'ID'})
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_data['playUrl'], display_id)

        initial_state = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state',
            display_id)['content']['clipDetails']
        for key, url in initial_state.items():
            lang, ext = self._search_regex(
                r'^subtitle_(?P<lang>[\w-]+)_(?P<ext>\w+)$', key, 'subtitle metadata',
                default=(None, None), group=('lang', 'ext'))
            if lang and ext:
                subtitles.setdefault(lang, []).append({
                    'ext': ext,
                    'url': url,
                })

                if ext == 'vtt':
                    subtitles[lang].append({
                        'ext': 'srt',
                        'url': f'{remove_end(initial_state[key], "vtt")}srt',
                    })

        episode = traverse_obj(list(filter(
            lambda x: x.get('@type') in ('TVEpisode', 'Movie'), self._yield_json_ld(webpage, display_id))), 0) or {}
        return {
            'id': display_id,
            'title': (traverse_obj(initial_state, 'title', 'display_title')
                      or episode.get('name')),
            'description': initial_state.get('description') or episode.get('description'),
            'duration': initial_state.get('duration'),
            'thumbnail': traverse_obj(episode, ('image', 'url')),
            'timestamp': unified_timestamp(episode.get('dateCreated')),
            'formats': formats,
            'subtitles': subtitles,
            'episode_number': (traverse_obj(initial_state, 'episode_no', 'episodeno', expected_type=int_or_none)
                               or int_or_none(episode.get('episodeNumber'))),
            'cast': traverse_obj(episode, ('actor', ..., 'name'), default=None),
            'age_limit': self._AGE_RATINGS_MAPPER.get(initial_state.get('internal_age_rating'))
        }

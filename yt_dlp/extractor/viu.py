import re
import json
import uuid
import random
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    strip_or_none,
    try_get,
    smuggle_url,
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
        self._sort_formats(formats)

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
    _VALID_URL = r'https?://(?:www\.)?viu\.com/ott/(?P<country_code>[a-z]{2})/(?P<lang_code>[a-z]{2}-[a-z]{2})/vod/(?P<id>\d+)'
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
        'url': 'http://www.viu.com/ott/hk/zh-hk/vod/7123/%E5%A4%A7%E4%BA%BA%E5%A5%B3%E5%AD%90',
        'info_dict': {
            'id': '7123',
            'ext': 'mp4',
            'title': '這就是我的生活之道',
            'description': 'md5:4eb0d8b08cf04fcdc6bbbeb16043434f',
        },
        'params': {
            'skip_download': 'm3u8 download',
            'noplaylist': True,
        },
        'skip': 'Geo-restricted to Hong Kong',
    }, {
        'url': 'https://www.viu.com/ott/hk/zh-hk/vod/68776/%E6%99%82%E5%B0%9A%E5%AA%BD%E5%92%AA',
        'playlist_count': 12,
        'info_dict': {
            'id': '3916',
            'title': '時尚媽咪',
        },
        'params': {
            'skip_download': 'm3u8 download',
            'noplaylist': False,
        },
        'skip': 'Geo-restricted to Hong Kong',
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
        rand = ''.join(random.choice('0123456789') for _ in range(10))
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

        query = {
            'r': 'vod/ajax-detail',
            'platform_flag_label': 'web',
            'product_id': video_id,
        }

        area_id = self._AREA_ID.get(country_code.upper())
        if area_id:
            query['area_id'] = area_id

        product_data = self._download_json(
            f'http://www.viu.com/ott/{country_code}/index.php', video_id,
            'Downloading video info', query=query)['data']

        video_data = product_data.get('current_product')
        if not video_data:
            self.raise_geo_restricted()

        series_id = video_data.get('series_id')
        if self._yes_playlist(series_id, video_id, idata):
            series = product_data.get('series') or {}
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
            'language_flag_id': self._LANGUAGE_FLAG.get(lang_code.lower()) or '3',
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
        self._sort_formats(formats)

        subtitles = {}
        for sub in video_data.get('subtitle') or []:
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('name'), []).append({
                'url': sub_url,
                'ext': 'srt',
            })

        title = strip_or_none(video_data.get('synopsis'))
        return {
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
        }

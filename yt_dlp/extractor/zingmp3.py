# coding: utf-8
from __future__ import unicode_literals

import hashlib
import hmac
from urllib.parse import urlencode

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    traverse_obj,
)


class ZingMp3BaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>(?:%s))/[^/]+/(?P<id>\w+)(?:\.html|\?)'
    _GEO_COUNTRIES = ['VN']
    _IS_UPDATE_COOKIES = False
    _DOMAIN = 'https://zingmp3.vn'
    _SLUG_API = {
        'bai-hat': '/api/v2/page/get/song',
        'embed': '/api/v2/page/get/song',
        'video-clip': '/api/v2/page/get/video',
        'playlist': '/api/v2/page/get/playlist',
        'album': '/api/v2/page/get/playlist',
        'lyric': '/api/v2/lyric/get/lyric',
        'song_streaming': '/api/v2/song/get/streaming',
    }

    _TEMP_TIMESTAMP = '123456'
    _API_KEY = '88265e23d4284f25963e6eedac8fbfa3'
    _SECRET_KEY = b'2aa2d1c561e809b267f3638c4a307aab'

    def _extract_item(self, item, song_id, type_url, fatal):
        item_id = item.get('encodeId') or song_id
        title = item.get('title') or item.get('alias')

        if type_url == 'video-clip':
            source = item.get('streaming')
        else:
            api = self.get_api_with_signature(name_api=self._SLUG_API.get('song_streaming'), param={
                'ctime': self._TEMP_TIMESTAMP,
                'id': item_id})
            source = self.download_json(api, item_id).get('data')

        formats = []
        for k, v in (source or {}).items():
            if not v:
                continue
            if k in ('mp4', 'hls'):
                for res, video_url in v.items():
                    if not video_url:
                        continue
                    if k == 'hls':
                        formats.extend(self._extract_m3u8_formats(
                            video_url, item_id, 'mp4',
                            'm3u8_native', m3u8_id=k, fatal=False))
                    elif k == 'mp4':
                        formats.append({
                            'format_id': 'mp4-' + res,
                            'url': video_url,
                            'height': int_or_none(self._search_regex(
                                r'^(\d+)p', res, 'resolution', default=None)),
                        })
            else:
                if v != 'VIP':
                    formats.append({
                        'ext': 'mp3',
                        'format_id': k,
                        'tbr': int_or_none(k),
                        'url': self._proto_relative_url(v),
                        'vcodec': 'none',
                    })
        if not formats:
            if not fatal:
                return
            msg = item.get('msg')
            if msg == 'Sorry, this content is not available in your country.':
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
            self.raise_no_formats(msg, expected=True)
        self._sort_formats(formats)

        lyric = item.get('lyric')
        if not lyric:
            api = self.get_api_with_signature(name_api=self._SLUG_API.get("lyric"), param={
                'ctime': self._TEMP_TIMESTAMP,
                'id': item_id})
            info_lyric = self.download_json(api, item_id)
            lyric = traverse_obj(info_lyric, ('data', 'file'))
        subtitles = {
            'origin': [{
                'url': lyric,
            }],
        } if lyric else None

        album = item.get('album') or {}

        return {
            'id': item_id,
            'title': title,
            'formats': formats,
            'thumbnail': try_get(item, lambda x: x['thumbnail']) or try_get(item, lambda x: x['thumbnailM']),
            'subtitles': subtitles,
            'duration': int_or_none(try_get(item, lambda x: x['duration'])),
            'track': title,
            'artist': try_get(item, lambda x: x['artistsNames']) or try_get(item, lambda x: x['artists_names']),
            'album': try_get(album, lambda x: x['name']) or try_get(album, lambda x: x['title']),
            'album_artist': try_get(album, lambda x: x['artistsNames']) or try_get(album, lambda x: x['artists_names']),
        }

    def _real_extract(self, url):
        song_id, type_url = self._match_valid_url(url).group('id', 'type')

        api = self.get_api_with_signature(name_api=self._SLUG_API[type_url], param={
            'ctime': self._TEMP_TIMESTAMP,
            'id': song_id})
        info = self.download_json(api, song_id)
        return self._process_data(info.get('data'), song_id, type_url)

    def download_json(self, api, video_id):
        # For the first time making the request, we need to make one more temp request to update the cookie
        # and the next time we don't need to do it.
        # But if download with cookieFile, so we don't need to make one more temp request
        if self._downloader.params.get('cookiefile'):
            self._IS_UPDATE_COOKIES = True

        if not self._IS_UPDATE_COOKIES:
            self._download_json(api, video_id=video_id, note='Update cookies for request')
            self._IS_UPDATE_COOKIES = True

        return self._download_json(api, video_id=video_id)

    def get_api_with_signature(self, name_api, param):
        sha256 = self.sha256_params(''.join(f'{k}={v}' for k, v in param.items()))

        data = {
            'ctime': param.get('ctime'),
            'apiKey': self._API_KEY,
            'sig': self.hmac512_string(f'{name_api}{sha256}')
        }
        data.update(param)
        return f'{self._DOMAIN}{name_api}?{urlencode(data)}'

    def sha256_params(self, string):
        return hashlib.sha256(string.encode('utf-8')).hexdigest()

    def hmac512_string(self, string):
        return hmac.new(self._SECRET_KEY, string.encode('utf-8'), hashlib.sha512).hexdigest()


class ZingMp3IE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'bai-hat|video-clip|embed'
    _TESTS = [{
        'url': 'https://zingmp3.vn/bai-hat/Xa-Mai-Xa-Bao-Thy/ZWZB9WAB.html',
        'md5': 'ead7ae13693b3205cbc89536a077daed',
        'info_dict': {
            'id': 'ZWZB9WAB',
            'title': 'Xa Mãi Xa',
            'ext': 'mp3',
            'thumbnail': r're:^https?://.+\.jpg',
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }]
            },
            'duration': 255,
            'track': 'Xa Mãi Xa',
            'artist': 'Bảo Thy',
            'album': 'Special Album',
            'album_artist': 'Bảo Thy',
        },
    }, {
        'url': 'https://zingmp3.vn/video-clip/Suong-Hoa-Dua-Loi-K-ICM-RYO/ZO8ZF7C7.html',
        'md5': 'e9c972b693aa88301ef981c8151c4343',
        'info_dict': {
            'id': 'ZO8ZF7C7',
            'title': 'Sương Hoa Đưa Lối',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 207,
            'track': 'Sương Hoa Đưa Lối',
            'artist': 'K-ICM, RYO',
        },
    }, {
        'url': 'https://zingmp3.vn/embed/song/ZWZEI76B?start=false',
        'only_matching': True,
    }, {
        'url': 'https://zingmp3.vn/bai-hat/Xa-Mai-Xa-Bao-Thy/ZWZB9WAB.html',
        'only_matching': True,
    }]
    IE_NAME = 'zingmp3'
    IE_DESC = 'zingmp3.vn'

    def _process_data(self, data, song_id, type_url):
        return self._extract_item(data, song_id, type_url, True)


class ZingMp3AlbumIE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'album|playlist'
    _TESTS = [{
        'url': 'http://mp3.zing.vn/album/Lau-Dai-Tinh-Ai-Bang-Kieu-Minh-Tuyet/ZWZBWDAF.html',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ZWZBWDAF',
            'title': 'Lâu Đài Tình Ái',
        },
        'playlist_count': 9,
    }, {
        'url': 'http://mp3.zing.vn/playlist/Duong-Hong-Loan-apollobee/IWCAACCB.html',
        'only_matching': True,
    }, {
        'url': 'https://zingmp3.vn/album/Lau-Dai-Tinh-Ai-Bang-Kieu-Minh-Tuyet/ZWZBWDAF.html',
        'only_matching': True,
    }]
    IE_NAME = 'zingmp3:album'

    def _process_data(self, data, song_id, type_url):
        def entries():
            for item in (try_get(data, lambda x: x['song']['items']) or []):
                entry = self._extract_item(item, song_id, type_url, False)
                if entry:
                    yield entry

        album_id = data.get('id') or data.get('encodeId')
        return self.playlist_result(entries(), album_id, data.get('name') or data.get('title'))

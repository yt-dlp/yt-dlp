import hashlib
import hmac
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
)


class ZingMp3BaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>(?:%s))/[^/]+/(?P<id>\w+)(?:\.html|\?)'
    _GEO_COUNTRIES = ['VN']
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

    _API_KEY = '88265e23d4284f25963e6eedac8fbfa3'
    _SECRET_KEY = b'2aa2d1c561e809b267f3638c4a307aab'

    def _extract_item(self, item, song_id, type_url, fatal):
        item_id = item.get('encodeId') or song_id
        title = item.get('title') or item.get('alias')

        if type_url == 'video-clip':
            source = item.get('streaming')
        else:
            api = self.get_api_with_signature(name_api=self._SLUG_API.get('song_streaming'), param={'id': item_id})
            source = self._download_json(api, video_id=item_id).get('data')

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
                continue
            elif v == 'VIP':
                continue
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
            api = self.get_api_with_signature(name_api=self._SLUG_API.get("lyric"), param={'id': item_id})
            info_lyric = self._download_json(api, video_id=item_id)
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
            'thumbnail': traverse_obj(item, 'thumbnail', 'thumbnailM'),
            'subtitles': subtitles,
            'duration': int_or_none(item.get('duration')),
            'track': title,
            'artist': traverse_obj(item, 'artistsNames', 'artists_names'),
            'album': traverse_obj(album, 'name', 'title'),
            'album_artist': traverse_obj(album, 'artistsNames', 'artists_names'),
        }

    def _real_initialize(self):
        if not self.get_param('cookiefile') and not self.get_param('cookiesfrombrowser'):
            self._request_webpage(self.get_api_with_signature(name_api=self._SLUG_API['bai-hat'], param={'id': ''}),
                                  None, note='Updating cookies')

    def _real_extract(self, url):
        song_id, type_url = self._match_valid_url(url).group('id', 'type')
        api = self.get_api_with_signature(name_api=self._SLUG_API[type_url], param={'id': song_id})
        return self._process_data(self._download_json(api, song_id)['data'], song_id, type_url)

    def get_api_with_signature(self, name_api, param):
        param.update({'ctime': '1'})
        sha256 = hashlib.sha256(''.join(f'{i}={param[i]}' for i in sorted(param)).encode('utf-8')).hexdigest()
        data = {
            'apiKey': self._API_KEY,
            'sig': hmac.new(self._SECRET_KEY, f'{name_api}{sha256}'.encode('utf-8'), hashlib.sha512).hexdigest(),
            **param,
        }
        return f'{self._DOMAIN}{name_api}?{urllib.parse.urlencode(data)}'


class ZingMp3IE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'bai-hat|video-clip|embed'
    _TESTS = [{
        'url': 'https://mp3.zing.vn/bai-hat/Xa-Mai-Xa-Bao-Thy/ZWZB9WAB.html',
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
        'md5': 'c7f23d971ac1a4f675456ed13c9b9612',
        'info_dict': {
            'id': 'ZO8ZF7C7',
            'title': 'Sương Hoa Đưa Lối',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 207,
            'track': 'Sương Hoa Đưa Lối',
            'artist': 'K-ICM, RYO',
            'album': 'Sương Hoa Đưa Lối (Single)',
            'album_artist': 'K-ICM, RYO',
        },
    }, {
        'url': 'https://zingmp3.vn/bai-hat/Nguoi-Yeu-Toi-Lanh-Lung-Sat-Da-Mr-Siro/ZZ6IW7OU.html',
        'md5': '3e9f7a9bd0d965573dbff8d7c68b629d',
        'info_dict': {
            'id': 'ZZ6IW7OU',
            'title': 'Người Yêu Tôi Lạnh Lùng Sắt Đá',
            'ext': 'mp3',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 303,
            'track': 'Người Yêu Tôi Lạnh Lùng Sắt Đá',
            'artist': 'Mr. Siro',
            'album': 'Người Yêu Tôi Lạnh Lùng Sắt Đá (Single)',
            'album_artist': 'Mr. Siro',
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
        'url': 'https://zingmp3.vn/album/Nhung-Bai-Hat-Hay-Nhat-Cua-Mr-Siro-Mr-Siro/ZWZAEZZD.html',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ZWZAEZZD',
            'title': 'Những Bài Hát Hay Nhất Của Mr. Siro',
        },
        'playlist_count': 49,
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
            for item in traverse_obj(data, ('song', 'items')) or []:
                entry = self._extract_item(item, song_id, type_url, False)
                if entry:
                    yield entry

        return self.playlist_result(entries(), traverse_obj(data, 'id', 'encodeId'),
                                    traverse_obj(data, 'name', 'title'))

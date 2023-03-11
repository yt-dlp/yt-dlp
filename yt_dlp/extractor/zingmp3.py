import functools
import hashlib
import hmac
import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    int_or_none,
    traverse_obj,
    urljoin,
    ExtractorError,
)


class ZingMp3BaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>(?:%s))/[^/?#]+/(?P<id>\w+)(?:\.html|\?)'
    _GEO_COUNTRIES = ['VN']
    _DOMAIN = 'https://zingmp3.vn'
    _PER_PAGE = 50
    _API_SLUGS = {
        # Audio/video
        'bai-hat': '/api/v2/page/get/song',
        'embed': '/api/v2/page/get/song',
        'video-clip': '/api/v2/page/get/video',
        'lyric': '/api/v2/lyric/get/lyric',
        'song-streaming': '/api/v2/song/get/streaming',
        'eps': '/api/v2/page/get/podcast-episode',
        'episode-streaming': '/api/v2/podcast/episode/get/streaming',
        # Playlist
        'playlist': '/api/v2/page/get/playlist',
        'album': '/api/v2/page/get/playlist',
        'pgr': '/api/v2/page/get/podcast-program',
        # Chart
        'zing-chart': '/api/v2/page/get/chart-home',
        'zing-chart-tuan': '/api/v2/page/get/week-chart',
        'moi-phat-hanh': '/api/v2/page/get/newrelease-chart',
        'the-loai-video': '/api/v2/video/get/list',
        # User
        'info-artist': '/api/v2/page/get/artist',
        'user-list-song': '/api/v2/song/get/list',
        'user-list-video': '/api/v2/video/get/list',
        'liveradio': '/api/v2/livestream/get/info',
    }

    def _api_url(self, url_type, params):
        api_slug = self._API_SLUGS[url_type]
        params.update({'ctime': '1'})
        sha256 = hashlib.sha256(
            ''.join(f'{k}={v}' for k, v in sorted(params.items())).encode()).hexdigest()
        data = {
            **params,
            'apiKey': '88265e23d4284f25963e6eedac8fbfa3',
            'sig': hmac.new(
                b'2aa2d1c561e809b267f3638c4a307aab', f'{api_slug}{sha256}'.encode(), hashlib.sha512).hexdigest(),
        }
        return f'{self._DOMAIN}{api_slug}?{urllib.parse.urlencode(data)}'

    def _call_api(self, url_type, params, display_id=None, **kwargs):
        resp = self._download_json(
            self._api_url(url_type, params), display_id or params.get('id'),
            note=f'Downloading {url_type} JSON metadata', **kwargs)
        return (resp or {}).get('data') or {}

    def _real_initialize(self):
        if not self._cookies_passed:
            self._request_webpage(
                self._api_url('bai-hat', {'id': ''}), None, note='Updating cookies')

    def _parse_items(self, items):
        for url in traverse_obj(items, (..., 'link')) or []:
            yield self.url_result(urljoin(self._DOMAIN, url))


class ZingMp3IE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'bai-hat|video-clip|embed|eps'
    IE_NAME = 'zingmp3'
    IE_DESC = 'zingmp3.vn'
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
        'md5': '3c2081e79471a2f4a3edd90b70b185ea',
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
        'url': 'https://zingmp3.vn/eps/Nhung-dieu-can-luu-y-khi-mua-bao-hiem-nhan-tho-How2Money-x-Doctor-Housing-Ep5/ZZEOWI7B.html',
        'md5': 'bc8793b186ffeee1cf2b6e54a69a8f33',
        'info_dict': {
            'id': 'ZZEOWI7B',
            'title': 'Những điều cần lưu ý khi mua bảo hiểm nhân thọ | How2Money x Doctor Housing. Ep5',
            'ext': 'mp3',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 912,
            'track': 'Những điều cần lưu ý khi mua bảo hiểm nhân thọ | How2Money x Doctor Housing. Ep5',
            'artist': 'Zing News',
            'album': 'Top Podcast',
            'album_artist': 'Zing News',
        },
    }, {
        'url': 'https://zingmp3.vn/embed/song/ZWZEI76B?start=false',
        'only_matching': True,
    }, {
        'url': 'https://zingmp3.vn/bai-hat/Xa-Mai-Xa-Bao-Thy/ZWZB9WAB.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        song_id, url_type = self._match_valid_url(url).group('id', 'type')
        item = self._call_api(url_type, {'id': song_id})

        item_id = item.get('encodeId') or song_id
        if url_type == 'video-clip':
            source = item.get('streaming')
            source['mp4'] = self._download_json(
                'http://api.mp3.zing.vn/api/mobile/video/getvideoinfo', item_id,
                query={'requestdata': json.dumps({'id': item_id})},
                note='Downloading mp4 JSON metadata').get('source')
        elif url_type == 'eps':
            source = self._call_api('episode-streaming', {'id': item_id})
        else:
            source = self._call_api('song-streaming', {'id': item_id})

        formats = []
        for k, v in (source or {}).items():
            if not v or v == 'VIP':
                continue
            if k not in ('mp4', 'hls'):
                formats.append({
                    'ext': 'mp3',
                    'format_id': k,
                    'tbr': int_or_none(k),
                    'url': self._proto_relative_url(v),
                    'vcodec': 'none',
                })
                continue
            for res, video_url in v.items():
                if not video_url:
                    continue
                if k == 'hls':
                    formats.extend(self._extract_m3u8_formats(video_url, item_id, 'mp4', m3u8_id=k, fatal=False))
                    continue
                formats.append({
                    'format_id': f'mp4-{res}',
                    'url': video_url,
                    'height': int_or_none(res),
                })

        if not formats and item.get('msg') == 'Sorry, this content is not available in your country.':
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)

        lyric = item.get('lyric') or self._call_api('lyric', {'id': item_id}, fatal=False).get('file')

        return {
            'id': item_id,
            'title': traverse_obj(item, 'title', 'alias'),
            'thumbnail': traverse_obj(item, 'thumbnail', 'thumbnailM'),
            'duration': int_or_none(item.get('duration')),
            'track': traverse_obj(item, 'title', 'alias'),
            'artist': traverse_obj(item, 'artistsNames', 'artists_names') or traverse_obj(item, ('artists', 0, 'name')),
            'album': traverse_obj(item, ('album', ('name', 'title')), get_all=False) or traverse_obj(
                item, ('genres', 0, 'name')),
            'album_artist': traverse_obj(item, ('album', ('artistsNames', 'artists_names')),
                                         get_all=False) or traverse_obj(item, ('artists', 0, 'name')),
            'formats': formats,
            'subtitles': {'origin': [{'url': lyric}]} if lyric else None,
        }


class ZingMp3AlbumIE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'album|playlist'
    _TESTS = [{
        'url': 'http://mp3.zing.vn/album/Lau-Dai-Tinh-Ai-Bang-Kieu-Minh-Tuyet/ZWZBWDAF.html',
        'info_dict': {
            'id': 'ZWZBWDAF',
            'title': 'Lâu Đài Tình Ái',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://zingmp3.vn/album/Nhung-Bai-Hat-Hay-Nhat-Cua-Mr-Siro-Mr-Siro/ZWZAEZZD.html',
        'info_dict': {
            'id': 'ZWZAEZZD',
            'title': 'Những Bài Hát Hay Nhất Của Mr. Siro',
        },
        'playlist_mincount': 49,
    }, {
        'url': 'https://zingmp3.vn/pgr/How2Money-x-Doctor-Housing/6BUUFAEO.html',
        'info_dict': {
            'id': '6BUUFAEO',
            'title': 'Những Bài Hát Hay Nhất Của Mr. Siro',
        },
        'playlist_mincount': 49,
    }, {
        'url': 'http://mp3.zing.vn/playlist/Duong-Hong-Loan-apollobee/IWCAACCB.html',
        'only_matching': True,
    }, {
        'url': 'https://zingmp3.vn/album/Lau-Dai-Tinh-Ai-Bang-Kieu-Minh-Tuyet/ZWZBWDAF.html',
        'only_matching': True,
    }]
    IE_NAME = 'zingmp3:album'

    def _real_extract(self, url):
        song_id, url_type = self._match_valid_url(url).group('id', 'type')
        data = self._call_api(url_type, {'id': song_id})
        return self.playlist_result(
            self._parse_items(traverse_obj(data, ('song', 'items'))),
            traverse_obj(data, 'id', 'encodeId'), traverse_obj(data, 'name', 'title'))


class ZingMp3ChartHomeIE(ZingMp3BaseIE):
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<id>(?:zing-chart|moi-phat-hanh))/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://zingmp3.vn/zing-chart',
        'info_dict': {
            'id': 'zing-chart',
        },
        'playlist_mincount': 100,
    }, {
        'url': 'https://zingmp3.vn/moi-phat-hanh',
        'info_dict': {
            'id': 'moi-phat-hanh',
        },
        'playlist_mincount': 100,
    }]
    IE_NAME = 'zingmp3:chart-home'

    def _real_extract(self, url):
        url_type = self._match_id(url)
        data = self._call_api(url_type, {'id': url_type})
        items = traverse_obj(data, ('RTChart', 'items') if url_type == 'zing-chart' else 'items')
        return self.playlist_result(self._parse_items(items), url_type)


class ZingMp3WeekChartIE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'zing-chart-tuan'
    IE_NAME = 'zingmp3:week-chart'
    _TESTS = [{
        'url': 'https://zingmp3.vn/zing-chart-tuan/Bai-hat-Viet-Nam/IWZ9Z08I.html',
        'info_dict': {
            'id': 'IWZ9Z08I',
            'title': 'zing-chart-vn',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://zingmp3.vn/zing-chart-tuan/Bai-hat-US-UK/IWZ9Z0BW.html',
        'info_dict': {
            'id': 'IWZ9Z0BW',
            'title': 'zing-chart-us',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://zingmp3.vn/zing-chart-tuan/Bai-hat-KPop/IWZ9Z0BO.html',
        'info_dict': {
            'id': 'IWZ9Z0BO',
            'title': 'zing-chart-korea',
        },
        'playlist_mincount': 10,
    }]

    def _real_extract(self, url):
        song_id, url_type = self._match_valid_url(url).group('id', 'type')
        data = self._call_api(url_type, {'id': song_id})
        return self.playlist_result(
            self._parse_items(data['items']), song_id, f'zing-chart-{data.get("country", "")}')


class ZingMp3ChartMusicVideoIE(ZingMp3BaseIE):
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>the-loai-video)/(?P<regions>[^/]+)/(?P<id>[^\.]+)'
    IE_NAME = 'zingmp3:chart-music-video'
    _TESTS = [{
        'url': 'https://zingmp3.vn/the-loai-video/Viet-Nam/IWZ9Z08I.html',
        'info_dict': {
            'id': 'IWZ9Z08I',
            'title': 'the-loai-video_Viet-Nam',
        },
        'playlist_mincount': 400,
    }, {
        'url': 'https://zingmp3.vn/the-loai-video/Au-My/IWZ9Z08O.html',
        'info_dict': {
            'id': 'IWZ9Z08O',
            'title': 'the-loai-video_Au-My',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://zingmp3.vn/the-loai-video/Han-Quoc/IWZ9Z08W.html',
        'info_dict': {
            'id': 'IWZ9Z08W',
            'title': 'the-loai-video_Han-Quoc',
        },
        'playlist_mincount': 30,
    }, {
        'url': 'https://zingmp3.vn/the-loai-video/Khong-Loi/IWZ9Z086.html',
        'info_dict': {
            'id': 'IWZ9Z086',
            'title': 'the-loai-video_Khong-Loi',
        },
        'playlist_mincount': 10,
    }]

    def _fetch_page(self, song_id, url_type, page):
        return self._parse_items(self._call_api(url_type, {
            'id': song_id,
            'type': 'genre',
            'page': page + 1,
            'count': self._PER_PAGE
        }).get('items'))

    def _real_extract(self, url):
        song_id, regions, url_type = self._match_valid_url(url).group('id', 'regions', 'type')
        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, song_id, url_type), self._PER_PAGE),
            song_id, f'{url_type}_{regions}')


class ZingMp3UserIE(ZingMp3BaseIE):
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<user>[^/]+)/(?P<type>bai-hat|single|album|video)/?(?:[?#]|$)'
    IE_NAME = 'zingmp3:user'
    _TESTS = [{
        'url': 'https://zingmp3.vn/Mr-Siro/bai-hat',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - bai-hat',
            'description': 'md5:85ab29bd7b21725c12bf76fd1d6922e5',
        },
        'playlist_mincount': 91,
    }, {
        'url': 'https://zingmp3.vn/Mr-Siro/album',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - album',
            'description': 'md5:85ab29bd7b21725c12bf76fd1d6922e5',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://zingmp3.vn/Mr-Siro/single',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - single',
            'description': 'md5:85ab29bd7b21725c12bf76fd1d6922e5',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://zingmp3.vn/Mr-Siro/video',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - video',
            'description': 'md5:85ab29bd7b21725c12bf76fd1d6922e5',
        },
        'playlist_mincount': 15,
    }]

    def _fetch_page(self, user_id, url_type, page):
        url_type = 'user-list-song' if url_type == 'bai-hat' else 'user-list-video'
        return self._parse_items(self._call_api(url_type, {
            'id': user_id,
            'type': 'artist',
            'page': page + 1,
            'count': self._PER_PAGE
        }, query={'sort': 'new', 'sectionId': 'aSong'}).get('items'))

    def _real_extract(self, url):
        user_alias, url_type = self._match_valid_url(url).group('user', 'type')
        if not url_type:
            url_type = 'bai-hat'

        user_info = self._call_api('info-artist', {}, user_alias, query={'alias': user_alias})
        if url_type in ('bai-hat', 'video'):
            entries = OnDemandPagedList(
                functools.partial(self._fetch_page, user_info['id'], url_type), self._PER_PAGE)
        else:
            entries = self._parse_items(traverse_obj(user_info, (
                'sections', lambda _, v: v['link'] == f'/{user_alias}/{url_type}', 'items', ...)))
        return self.playlist_result(
            entries, user_info['id'], f'{user_info.get("name")} - {url_type}', user_info.get('biography'))


class ZingMp3LiveRadioIE(ZingMp3BaseIE):
    IE_NAME = 'zingmp3:liveradio'
    _VALID_URL = 'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>(?:liveradio))/(?P<id>\w+)(?:\.html|\?)'
    _TESTS = [{
        'url': 'https://zingmp3.vn/liveradio/IWZ979UB.html',
        'info_dict': {
            'id': 'IWZ979UB',
            'title': 're:^V\-POP',
            'description': 'md5:aa857f8a91dc9ce69e862a809e4bdc10',
            'protocol': 'm3u8_native',
            'ext': 'mp4',
            'view_count': int,
            'thumbnail': 're:^https?://.*\.jpg',
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://zingmp3.vn/liveradio/IWZ97CWB.html',
        'info_dict': {
            'id': 'IWZ97CWB',
            'title': 're:^Live\s247',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'protocol': 'm3u8_native',
            'ext': 'm4a',
            'view_count': int,
            'thumbnail': 're:^https?://.*\.jpg',
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        url_type, live_radio_id = self._match_valid_url(url).group('type', 'id')
        info = self._call_api(url_type, {'id': live_radio_id})
        manifest_url = info.get('streaming')
        if not manifest_url:
            raise ExtractorError('This radio is offline.', expected=True)
        fmts, subtitles = self._extract_m3u8_formats_and_subtitles(manifest_url, live_radio_id, fatal=False)
        return {
            'id': live_radio_id,
            'title': traverse_obj(info, 'title'),
            'thumbnail': traverse_obj(info, 'thumbnail', 'thumbnailM', 'thumbnailV', 'thumbnailH'),
            'formats': fmts,
            'view_count': traverse_obj(info, 'activeUsers'),
            'like_count': traverse_obj(info, 'totalReaction'),
            'description': traverse_obj(info, 'description'),
            'subtitles': subtitles,
        }


class ZingMp3PostCastEpisodeIE(ZingMp3BaseIE):
    IE_NAME = 'zingmp3:PostcastEpisode'
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'pgr'
    _TESTS = [{
        'url': 'https://zingmp3.vn/pgr/How2Money-x-Doctor-Housing/6BUUFAEO.html',
        'info_dict': {
            'id': '6BUUFAEO',
            'title': 'Những Bài Hát Hay Nhất Của Mr. Siro',
        },
        'playlist_mincount': 49,
    }]

    def _real_extract(self, url):
        post_cast_id, url_type = self._match_valid_url(url).group('id', 'type')
        post_cast_info = self._call_api(url_type, {'id': post_cast_id})
        return

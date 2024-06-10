import hashlib
import hmac
import itertools
import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    try_call,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


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
        'liveradio': '/api/v2/livestream/get/info',
        'eps': '/api/v2/page/get/podcast-episode',
        'episode-streaming': '/api/v2/podcast/episode/get/streaming',
        # Playlist
        'playlist': '/api/v2/page/get/playlist',
        'album': '/api/v2/page/get/playlist',
        'pgr': '/api/v2/page/get/podcast-program',
        'pgr-list': '/api/v2/podcast/episode/get/list',
        'cgr': '/api/v2/page/get/podcast-category',
        'cgr-list': '/api/v2/podcast/program/get/list-by-cate',
        'cgrs': '/api/v2/page/get/podcast-categories',
        # Chart
        'zing-chart': '/api/v2/page/get/chart-home',
        'zing-chart-tuan': '/api/v2/page/get/week-chart',
        'moi-phat-hanh': '/api/v2/page/get/newrelease-chart',
        'the-loai-video': '/api/v2/video/get/list',
        # User
        'info-artist': '/api/v2/page/get/artist',
        'user-list-song': '/api/v2/song/get/list',
        'user-list-video': '/api/v2/video/get/list',
        'hub': '/api/v2/page/get/hub-detail',
        'new-release': '/api/v2/chart/get/new-release',
        'top100': '/api/v2/page/get/top-100',
        'podcast-new': '/api/v2/podcast/program/get/list-by-type',
        'top-podcast': '/api/v2/podcast/program/get/top-episode',
    }

    def _api_url(self, url_type, params):
        api_slug = self._API_SLUGS[url_type]
        params.update({'ctime': '1'})
        sha256 = hashlib.sha256(
            ''.join(f'{k}={v}' for k, v in sorted(params.items())).encode()).hexdigest()
        data = {
            **params,
            'apiKey': 'X5BM3w8N7MKozC0B85o4KMlzLZKhV00y',
            'sig': hmac.new(b'acOrvUS15XRW2o9JksiK1KgQ6Vbds8ZW',
                            f'{api_slug}{sha256}'.encode(), hashlib.sha512).hexdigest(),
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

    def _fetch_page(self, id_, url_type, page):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _paged_list(self, _id, url_type):
        count = 0
        for page in itertools.count(1):
            data = self._fetch_page(_id, url_type, page)
            entries = list(self._parse_items(data.get('items')))
            count += len(entries)
            yield from entries
            if not data.get('hasMore') or try_call(lambda: count > data['total']):
                break


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
        'md5': '92c6e7a019f06b4682a6c35ae5785fab',
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
        'url': 'https://zingmp3.vn/eps/Cham-x-Ban-Noi-Goi-La-Nha/ZZD9ACWI.html',
        'md5': 'd52f9f63e2631e004e4f15188eedcf80',
        'info_dict': {
            'id': 'ZZD9ACWI',
            'title': 'Chạm x Bạn - Nơi Gọi Là Nhà',
            'ext': 'mp3',
            'duration': 3716,
            'thumbnail': r're:^https?://.+\.jpg',
            'track': 'Chạm x Bạn - Nơi Gọi Là Nhà',
            'artist': 'On Air',
            'album': 'Top Podcast',
            'album_artist': 'On Air',
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

        if not formats:
            if item.get('msg') == 'Sorry, this content is not available in your country.':
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
            else:
                self.raise_no_formats('The song is only for VIP accounts.')

        lyric = item.get('lyric') or self._call_api('lyric', {'id': item_id}, fatal=False).get('file')

        return {
            'id': item_id,
            'title': traverse_obj(item, 'title', 'alias'),
            'thumbnail': traverse_obj(item, 'thumbnail', 'thumbnailM'),
            'duration': int_or_none(item.get('duration')),
            'track': traverse_obj(item, 'title', 'alias'),
            'artist': traverse_obj(item, 'artistsNames', 'artists_names', ('artists', 0, 'name')),
            'album': traverse_obj(item, ('album', ('name', 'title')), ('genres', 0, 'name'), get_all=False),
            'album_artist': traverse_obj(item, ('album', ('artistsNames', 'artists_names')),
                                         ('artists', 0, 'name'), get_all=False),
            'formats': formats,
            'subtitles': {'origin': [{'url': lyric}]} if lyric else None,
        }


class ZingMp3AlbumIE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'album|playlist'
    _TESTS = [{
        'url': 'https://zingmp3.vn/album/Ca-Phe-Quan-Quen-Hoang-Dung-My-Anh-Da-LAB-Thinh-Suy/ZOC7WUZC.html',
        'info_dict': {
            'id': 'ZOC7WUZC',
            'title': 'Cà Phê Quán Quen',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://zingmp3.vn/album/Nhung-Bai-Hat-Hay-Nhat-Cua-Mr-Siro-Mr-Siro/ZWZAEZZD.html',
        'info_dict': {
            'id': 'ZWZAEZZD',
            'title': 'Những Bài Hát Hay Nhất Của Mr. Siro',
        },
        'playlist_mincount': 20,
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
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<id>(?:zing-chart|moi-phat-hanh|top100|podcast-discover))/?(?:[#?]|$)'
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
    }, {
        'url': 'https://zingmp3.vn/top100',
        'info_dict': {
            'id': 'top100',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://zingmp3.vn/podcast-discover',
        'info_dict': {
            'id': 'podcast-discover',
        },
        'playlist_mincount': 4,
    }]
    IE_NAME = 'zingmp3:chart-home'

    def _real_extract(self, url):
        url_type = self._match_id(url)
        params = {'id': url_type}
        if url_type == 'podcast-discover':
            params['type'] = 'discover'
        data = self._call_api(url_type, params)
        items = []
        if url_type == 'top100':
            items.extend(traverse_obj(data, (..., 'items', ..., {dict})))
        elif url_type == 'zing-chart':
            items.extend(traverse_obj(data, ('RTChart', 'items', ..., {dict})))
        else:
            items.extend(traverse_obj(data, ('items', ..., {dict})))
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
        'playlist_mincount': 1,
    }]

    def _fetch_page(self, song_id, url_type, page):
        return self._call_api(url_type, {
            'id': song_id,
            'type': 'genre',
            'page': page,
            'count': self._PER_PAGE
        })

    def _real_extract(self, url):
        song_id, regions, url_type = self._match_valid_url(url).group('id', 'regions', 'type')
        return self.playlist_result(self._paged_list(song_id, url_type), song_id, f'{url_type}_{regions}')


class ZingMp3UserIE(ZingMp3BaseIE):
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<user>[^/]+)/(?P<type>bai-hat|single|album|video|song)/?(?:[?#]|$)'
    IE_NAME = 'zingmp3:user'
    _TESTS = [{
        'url': 'https://zingmp3.vn/Mr-Siro/bai-hat',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - bai-hat',
            'description': 'md5:5bdcf45e955dc1b8d7f518f322ffef36',
        },
        'playlist_mincount': 91,
    }, {
        'url': 'https://zingmp3.vn/Mr-Siro/album',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - album',
            'description': 'md5:5bdcf45e955dc1b8d7f518f322ffef36',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://zingmp3.vn/Mr-Siro/single',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - single',
            'description': 'md5:5bdcf45e955dc1b8d7f518f322ffef36',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://zingmp3.vn/Mr-Siro/video',
        'info_dict': {
            'id': 'IWZ98609',
            'title': 'Mr. Siro - video',
            'description': 'md5:5bdcf45e955dc1b8d7f518f322ffef36',
        },
        'playlist_mincount': 15,
    }, {
        'url': 'https://zingmp3.vn/new-release/song',
        'info_dict': {
            'id': 'new-release-song',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://zingmp3.vn/new-release/album',
        'info_dict': {
            'id': 'new-release-album',
        },
        'playlist_mincount': 20,
    }]

    def _fetch_page(self, user_id, url_type, page):
        url_type = 'user-list-song' if url_type == 'bai-hat' else 'user-list-video'
        return self._call_api(url_type, {
            'id': user_id,
            'type': 'artist',
            'page': page,
            'count': self._PER_PAGE
        })

    def _real_extract(self, url):
        alias, url_type = self._match_valid_url(url).group('user', 'type')
        if not url_type:
            url_type = 'bai-hat'

        user_info = self._call_api('info-artist', {}, alias, query={'alias': alias})

        # Handle for new-release
        if alias == 'new-release' and url_type in ('song', 'album'):
            _id = f'{alias}-{url_type}'
            return self.playlist_result(self._parse_items(
                self._call_api('new-release', params={'type': url_type}, display_id=_id)), _id)
        else:
            # Handle for user/artist
            if url_type in ('bai-hat', 'video'):
                entries = self._paged_list(user_info['id'], url_type)
            else:
                section_id = 'aAlbum' if url_type == 'album' else 'aSingle'
                entries = self._parse_items(traverse_obj(user_info, (
                    'sections', lambda _, v: v['sectionId'] == section_id, 'items', ...)))
            return self.playlist_result(
                entries, user_info['id'], join_nonempty(user_info.get('name'), url_type, delim=' - '),
                user_info.get('biography'))


class ZingMp3HubIE(ZingMp3BaseIE):
    IE_NAME = 'zingmp3:hub'
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>hub)/(?P<regions>[^/]+)/(?P<id>[^\.]+)'
    _TESTS = [{
        'url': 'https://zingmp3.vn/hub/Nhac-Moi/IWZ9Z0CA.html',
        'info_dict': {
            'id': 'IWZ9Z0CA',
            'title': 'BXH Nhạc Mới',
            'description': 'md5:1cc31b68a6f746427b07b2756c22a558',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://zingmp3.vn/hub/Nhac-Viet/IWZ9Z087.html',
        'info_dict': {
            'id': 'IWZ9Z087',
            'title': 'Nhạc Việt',
            'description': 'md5:acc976c8bdde64d5c6ee4a92c39f7a77',
        },
        'playlist_mincount': 30,
    }]

    def _real_extract(self, url):
        song_id, regions, url_type = self._match_valid_url(url).group('id', 'regions', 'type')
        hub_detail = self._call_api(url_type, {'id': song_id})
        entries = self._parse_items(traverse_obj(hub_detail, (
            'sections', lambda _, v: v['sectionId'] == 'hub', 'items', ...)))
        return self.playlist_result(
            entries, song_id, hub_detail.get('title'), hub_detail.get('description'))


class ZingMp3LiveRadioIE(ZingMp3BaseIE):
    IE_NAME = 'zingmp3:liveradio'
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<type>(?:liveradio))/(?P<id>\w+)(?:\.html|\?)'
    _TESTS = [{
        'url': 'https://zingmp3.vn/liveradio/IWZ979UB.html',
        'info_dict': {
            'id': 'IWZ979UB',
            'title': r're:^V\-POP',
            'description': 'md5:aa857f8a91dc9ce69e862a809e4bdc10',
            'ext': 'mp4',
            'view_count': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'like_count': int,
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://zingmp3.vn/liveradio/IWZ97CWB.html',
        'info_dict': {
            'id': 'IWZ97CWB',
            'title': r're:^Live\s247',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'ext': 'm4a',
            'view_count': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'like_count': int,
            'live_status': 'is_live',
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
            'is_live': True,
            'formats': fmts,
            'subtitles': subtitles,
            **traverse_obj(info, {
                'title': 'title',
                'thumbnail': (('thumbnail', 'thumbnailM', 'thumbnailV', 'thumbnailH'), {url_or_none}),
                'view_count': ('activeUsers', {int_or_none}),
                'like_count': ('totalReaction', {int_or_none}),
                'description': 'description',
            }, get_all=False),
        }


class ZingMp3PodcastEpisodeIE(ZingMp3BaseIE):
    IE_NAME = 'zingmp3:podcast-episode'
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'pgr|cgr'
    _TESTS = [{
        'url': 'https://zingmp3.vn/pgr/Nhac-Moi-Moi-Ngay/68Z9W66B.html',
        'info_dict': {
            'id': '68Z9W66B',
            'title': 'Nhạc Mới Mỗi Ngày',
            'description': 'md5:2875dfa951f8e5356742f1610cf20691'
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://zingmp3.vn/cgr/Am-nhac/IWZ980AO.html',
        'info_dict': {
            'id': 'IWZ980AO',
            'title': 'Âm nhạc'
        },
        'playlist_mincount': 2,
    }]

    def _fetch_page(self, eps_id, url_type, page):
        return self._call_api(url_type, {
            'id': eps_id,
            'page': page,
            'count': self._PER_PAGE
        })

    def _real_extract(self, url):
        podcast_id, url_type = self._match_valid_url(url).group('id', 'type')
        podcast_info = self._call_api(url_type, {'id': podcast_id})
        entries = self._paged_list(podcast_id, 'pgr-list' if url_type == 'pgr' else 'cgr-list')
        return self.playlist_result(
            entries, podcast_id, podcast_info.get('title'), podcast_info.get('description'))


class ZingMp3PodcastIE(ZingMp3BaseIE):
    IE_NAME = 'zingmp3:podcast'
    _VALID_URL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?P<id>(?:cgr|top-podcast|podcast-new))/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://zingmp3.vn/cgr',
        'info_dict': {
            'id': 'cgr',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://zingmp3.vn/top-podcast',
        'info_dict': {
            'id': 'top-podcast',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://zingmp3.vn/podcast-new',
        'info_dict': {
            'id': 'podcast-new',
        },
        'playlist_mincount': 4,
    }]

    def _real_extract(self, url):
        url_type = self._match_id(url)
        params = {'id': url_type}
        if url_type == 'podcast-new':
            params['type'] = 'new'
        items = self._call_api('cgrs' if url_type == 'cgr' else url_type, params)['items']
        return self.playlist_result(self._parse_items(items), url_type)

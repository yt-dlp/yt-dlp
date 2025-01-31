import time

from .wrestleuniverse import WrestleUniverseBaseIE
from ..utils import (
    int_or_none,
    traverse_obj,
    url_or_none,
)


class StacommuBaseIE(WrestleUniverseBaseIE):
    _NETRC_MACHINE = 'stacommu'
    _API_HOST = 'api.stacommu.jp'
    _LOGIN_QUERY = {'key': 'AIzaSyCR9czxhH2eWuijEhTNWBZ5MCcOYEUTAhg'}
    _LOGIN_HEADERS = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-Client-Version': 'Chrome/JsCore/9.9.4/FirebaseCore-web',
        'Referer': 'https://www.stacommu.jp/',
        'Origin': 'https://www.stacommu.jp',
    }

    @WrestleUniverseBaseIE._TOKEN.getter
    def _TOKEN(self):
        if self._REAL_TOKEN and self._TOKEN_EXPIRY <= int(time.time()):
            self._refresh_token()

        return self._REAL_TOKEN

    def _get_formats(self, data, path, video_id=None):
        if not traverse_obj(data, path) and not data.get('canWatch') and not self._TOKEN:
            self.raise_login_required(method='password')
        return super()._get_formats(data, path, video_id)

    def _extract_hls_key(self, data, path, decrypt):
        encryption_data = traverse_obj(data, path)
        if traverse_obj(encryption_data, ('encryptType', {int})) == 0:
            return None
        return traverse_obj(encryption_data, {'key': ('key', {decrypt}), 'iv': ('iv', {decrypt})})

    def _extract_vod(self, url):
        video_id = self._match_id(url)
        video_info = self._download_metadata(
            url, video_id, 'ja', ('dehydratedState', 'queries', 0, 'state', 'data'))
        hls_info, decrypt = self._call_encrypted_api(
            video_id, ':watch', 'stream information', data={'method': 1})

        return {
            'id': video_id,
            'formats': self._get_formats(hls_info, ('protocolHls', 'url', {url_or_none}), video_id),
            'hls_aes': self._extract_hls_key(hls_info, 'protocolHls', decrypt),
            **traverse_obj(video_info, {
                'title': ('displayName', {str}),
                'description': ('description', {str}),
                'timestamp': ('watchStartTime', {int_or_none}),
                'thumbnail': ('keyVisualUrl', {url_or_none}),
                'cast': ('casts', ..., 'displayName', {str}),
                'duration': ('duration', {int}),
            }),
        }

    def _extract_ppv(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api(video_id, msg='video information', query={'al': 'ja'}, auth=False)
        hls_info, decrypt = self._call_encrypted_api(
            video_id, ':watchArchive', 'stream information', data={'method': 1})

        return {
            'id': video_id,
            'formats': self._get_formats(hls_info, ('hls', 'urls', ..., {url_or_none}), video_id),
            'hls_aes': self._extract_hls_key(hls_info, 'hls', decrypt),
            **traverse_obj(video_info, {
                'title': ('displayName', {str}),
                'timestamp': ('startTime', {int_or_none}),
                'thumbnail': ('keyVisualUrl', {url_or_none}),
                'duration': ('duration', {int_or_none}),
            }),
        }


class StacommuVODIE(StacommuBaseIE):
    _VALID_URL = r'https?://www\.stacommu\.jp/(?:en/)?videos/episodes/(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        # not encrypted
        'url': 'https://www.stacommu.jp/videos/episodes/aXcVKjHyAENEjard61soZZ',
        'info_dict': {
            'id': 'aXcVKjHyAENEjard61soZZ',
            'ext': 'mp4',
            'title': 'スタコミュAWARDの裏側、ほぼ全部見せます！〜晴れ舞台の直前ドキドキ編〜',
            'description': 'md5:6400275c57ae75c06da36b06f96beb1c',
            'timestamp': 1679652000,
            'upload_date': '20230324',
            'thumbnail': 'https://image.stacommu.jp/6eLobQan8PFtBoU4RL4uGg/6eLobQan8PFtBoU4RL4uGg',
            'cast': 'count:11',
            'duration': 250,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # encrypted; requires a premium account
        'url': 'https://www.stacommu.jp/videos/episodes/3hybMByUvzMEqndSeu5LpD',
        'info_dict': {
            'id': '3hybMByUvzMEqndSeu5LpD',
            'ext': 'mp4',
            'title': 'スタプラフェス2023〜裏側ほぼ全部見せます〜＃10',
            'description': 'md5:85494488ccf1dfa1934accdeadd7b340',
            'timestamp': 1682506800,
            'upload_date': '20230426',
            'thumbnail': 'https://image.stacommu.jp/eMdXtEefR4kEyJJMpAFi7x/eMdXtEefR4kEyJJMpAFi7x',
            'cast': 'count:55',
            'duration': 312,
            'hls_aes': {
                'key': '6bbaf241b8e1fd9f59ecf546a70e4ae7',
                'iv': '1fc9002a23166c3bb1d240b953d09de9',
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.stacommu.jp/en/videos/episodes/aXcVKjHyAENEjard61soZZ',
        'only_matching': True,
    }]

    _API_PATH = 'videoEpisodes'

    def _real_extract(self, url):
        return self._extract_vod(url)


class StacommuLiveIE(StacommuBaseIE):
    _VALID_URL = r'https?://www\.stacommu\.jp/(?:en/)?live/(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.stacommu.jp/live/d2FJ3zLnndegZJCAEzGM3m',
        'info_dict': {
            'id': 'd2FJ3zLnndegZJCAEzGM3m',
            'ext': 'mp4',
            'title': '仲村悠菜 2023/05/04',
            'timestamp': 1683195647,
            'upload_date': '20230504',
            'thumbnail': 'https://image.stacommu.jp/pHGF57SPEHE2ke83FS92FN/pHGF57SPEHE2ke83FS92FN',
            'duration': 5322,
            'hls_aes': {
                'key': 'efbb3ec0b8246f61adf1764c5a51213a',
                'iv': '80621d19a1f19167b64cedb415b05d1c',
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.stacommu.jp/en/live/d2FJ3zLnndegZJCAEzGM3m',
        'only_matching': True,
    }]

    _API_PATH = 'events'

    def _real_extract(self, url):
        return self._extract_ppv(url)


class TheaterComplexTownBaseIE(StacommuBaseIE):
    _NETRC_MACHINE = 'theatercomplextown'
    _API_HOST = 'api.theater-complex.town'
    _LOGIN_QUERY = {'key': 'AIzaSyAgNCqToaIz4a062EeIrkhI_xetVfAOrfc'}
    _LOGIN_HEADERS = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-Client-Version': 'Chrome/JsCore/9.23.0/FirebaseCore-web',
        'Referer': 'https://www.theater-complex.town/',
        'Origin': 'https://www.theater-complex.town',
    }


class TheaterComplexTownVODIE(TheaterComplexTownBaseIE):
    _VALID_URL = r'https?://(?:www\.)?theater-complex\.town/(?:(?:en|ja)/)?videos/episodes/(?P<id>\w+)'
    IE_NAME = 'theatercomplextown:vod'
    _TESTS = [{
        'url': 'https://www.theater-complex.town/videos/episodes/hoxqidYNoAn7bP92DN6p78',
        'info_dict': {
            'id': 'hoxqidYNoAn7bP92DN6p78',
            'ext': 'mp4',
            'title': '演劇ドラフトグランプリ2023　劇団『恋のぼり』〜劇団名決定秘話ラジオ',
            'description': 'md5:a7e2e9cf570379ea67fb630f345ff65d',
            'cast': ['玉城 裕規', '石川 凌雅'],
            'thumbnail': 'https://image.theater-complex.town/5URnXX6KCeDysuFrPkP38o/5URnXX6KCeDysuFrPkP38o',
            'upload_date': '20231103',
            'timestamp': 1699016400,
            'duration': 868,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.theater-complex.town/en/videos/episodes/6QT7XYwM9dJz5Gf9VB6K5y',
        'only_matching': True,
    }, {
        'url': 'https://www.theater-complex.town/ja/videos/episodes/hoxqidYNoAn7bP92DN6p78',
        'only_matching': True,
    }]

    _API_PATH = 'videoEpisodes'

    def _real_extract(self, url):
        return self._extract_vod(url)


class TheaterComplexTownPPVIE(TheaterComplexTownBaseIE):
    _VALID_URL = r'https?://(?:www\.)?theater-complex\.town/(?:(?:en|ja)/)?(?:ppv|live)/(?P<id>\w+)'
    IE_NAME = 'theatercomplextown:ppv'
    _TESTS = [{
        'url': 'https://www.theater-complex.town/ppv/wytW3X7khrjJBUpKuV3jen',
        'info_dict': {
            'id': 'wytW3X7khrjJBUpKuV3jen',
            'ext': 'mp4',
            'title': 'BREAK FREE STARS　11月5日（日）12:30千秋楽公演',
            'thumbnail': 'https://image.theater-complex.town/5GWEB31JcTUfjtgdeV5t6o/5GWEB31JcTUfjtgdeV5t6o',
            'upload_date': '20231105',
            'timestamp': 1699155000,
            'duration': 8378,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.theater-complex.town/en/ppv/wytW3X7khrjJBUpKuV3jen',
        'only_matching': True,
    }, {
        'url': 'https://www.theater-complex.town/ja/ppv/qwUVmLmGEiZ3ZW6it9uGys',
        'only_matching': True,
    }, {
        'url': 'https://www.theater-complex.town/en/live/79akNM7bJeD5Fi9EP39aDp',
        'only_matching': True,
    }]

    _API_PATH = 'events'

    def _real_extract(self, url):
        return self._extract_ppv(url)

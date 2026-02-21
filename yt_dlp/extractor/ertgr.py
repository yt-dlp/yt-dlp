import json
import re
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    jwt_decode_hs256,
    parse_age_limit,
    parse_qs,
)
from ..utils.traversal import traverse_obj


class ERTFlixBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'ERTFLIX'
    _TOKEN_CACHE_KEY = 'ert_token_data'

    _ACCESS_TOKEN = None
    _REFRESH_TOKEN = None
    _LANG = 'en_GB'

    def _real_initialize(self):
        langs = ('en', 'el', 'english', 'greek')
        lang = self._configuration_arg('language', default='en', ie_key=self.ie_key())
        if not lang:
            return
        if lang not in langs:
            raise ExtractorError(f'Unsupported language {lang} - Supported langs are {langs}')
        self._LANG = f'{lang}_GB' if 'en' in lang else f'{lang}_GR'

    @staticmethod
    def _is_jwt_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def get_access_token(self):
        if self._ACCESS_TOKEN and not self._is_jwt_expired(self._ACCESS_TOKEN):
            return True
        else:
            self._ACCESS_TOKEN, self._REFRESH_TOKEN = self.cache.load(self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, default=[None, None])

            if self._ACCESS_TOKEN and self._REFRESH_TOKEN:
                if not self._is_jwt_expired(self._ACCESS_TOKEN):
                    return True
                else:
                    self.refresh_token()
                    return True
        return None

    def _perform_login(self, username, password):
        if username == 'username':
            if not self._is_jwt_expired(password):
                self._ACCESS_TOKEN = password
            else:
                raise ExtractorError('You given access token is expired please refresh it', expected=True)
            return
        if self.get_access_token():
            return

        try:
            login_data = self._download_json(
                'https://api.ertflix.opentv.com/ias/v3/token/actions/signOnByUserNamePassword',
                None,
                note='Loggin in',
                data=json.dumps({
                    'password': password.replace('@', '%40'),
                    'username': username.replace('@', '%40'),
                    'deviceInformation': {
                        'securePlayer': {'streamings': [], 'codecs': [], 'DRMs': []},
                        'device': {
                            'hardware': {
                                'manufacturer': 'Chrome - 144.0.0.0',
                                'model': ' Win64',
                                'type': 'Linux',
                            },
                            'OS': {'type': 'Linux', 'version': 'unknown'},
                            'CPU': {'cores': 0, 'neon': 0},
                            'screen': {'density': 0, 'width': 1920, 'height': 1080},
                            'GPU': {'cores': '0', 'frequency': '0.000000'},
                        },
                    },
                }).encode(),
                headers={
                    'Content-Type': 'application/json',
                    'nv-tenant-id': 'nagra',
                },
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                raise ExtractorError('Invalid username or password', expected=True)
            raise

        self._ACCESS_TOKEN = login_data.get('access_token')
        self._REFRESH_TOKEN = login_data.get('refresh_token')
        if not self._ACCESS_TOKEN:
            raise ExtractorError('Failed to retrieve access token')
        self.cache.store(self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])
        return

    def refresh_token(self):
        if not self._REFRESH_TOKEN:
            return self._perform_login(**self._get_login_info())

        data = self._download_json(
            'https://api.ertflix.opentv.com/ias/v3/token/actions/refresh',
            None,
            note='Refreshing token',
            data=json.dumps({}).encode(),
            headers={
                'Authorization': f'Bearer {self._REFRESH_TOKEN}',
                'Content-Type': 'application/json',
                'nv-tenant-id': 'nagra',
            },
        )

        if not data:
            self.to_screen('Failed to refresh access token')
            return self._perform_login(**self._get_login_info())
        self._ACCESS_TOKEN = data.get('access_token')
        if not self._ACCESS_TOKEN:
            self.to_screen('Unable to refresh access token')
            return self._perform_login(**self._get_login_info())
        self._REFRESH_TOKEN = data.get('refresh_token')
        self.cache.store(self._NETRC_MACHINE, self._TOKEN_CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])

    def _call_api(
            self, video_id, is_metadata='metadata', method='Player/AcquireContent', api_version=1, data=None, headers=None, params=None):
        headers = headers or {}
        headers.update({
            'nagra-device-type': 'Browser',
            'nagra-target': 'Desktop',
            'accept-language': self._LANG,  # Required As per Site
        })
        if self._ACCESS_TOKEN:
            headers.update({
                'Authorization': f'Bearer {self._ACCESS_TOKEN}',
            })
        version_path = f'v{api_version!s}/' if api_version else ''
        params = params or {}
        if not params:
            params = {
                'deviceType': 'Browser',
            }
        is_metadata = f'{is_metadata}/' if is_metadata else ''
        try:
            response = self._download_json(
                f'https://api.ertflix.opentv.com/{is_metadata}{version_path}{method}',
                video_id, query=params, data=data, headers=headers)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (403, 500):
                self.raise_login_required()
            raise e

        return response

    def extract_urls_from_data(self, data):
        if isinstance(data, dict):
            return []

        data = traverse_obj(data, (..., 'media'), ('media', ...))

        urls = []

        av_blocks = traverse_obj(
            data,
            (..., lambda k, v: k.startswith('AV')), default=None,
        )
        if av_blocks:
            for block in av_blocks:
                urls.append(traverse_obj(block, ('uri')))
        else:
            urls.extend(traverse_obj(data, (..., 'uri')))

        return urls

    # TODO: Not needed for now but if needed then add in _extract_formats
    def _urls_resolver(self, data):
        raw_urls = self.extract_urls_from_data(data)
        res_urls = []
        str.split()
        cid = data.get('contentLinkId') or (data.get('id')).split('_')[-1]
        content_id = f'DRM_{cid}'
        for url in raw_urls:
            content_id = f'{content_id}_DASH' if '.mpd' in url else f'{content_id}_HLS'
            resolved_data = self._call_api(
                cid, is_metadata=None,
                method='urlbuilder/v1/playout/content/token',
                api_version=None,
                params={
                    'content_id': content_id,
                    'type': 'account',
                    'content_URL': url,
                },
            )
            res_url = traverse_obj(resolved_data, ('cdnAccessToken'), ('playbackUrl'))
            if res_url:
                res_urls.append(res_url)

        return res_urls


class ERTFlixCodenameIE(ERTFlixBaseIE):
    IE_NAME = 'ertflix:codename'
    IE_DESC = 'ERTFLIX videos by codename'
    _VALID_URL = r'ertflix:(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'ertflix:ERT_M001162',
        'info_dict': {
            'id': 'ERT_M001162',
            'title': 'Scoring a Goal in Love',
            'ext': 'mp4',
            'description': 'md5:ae2e217e579eecf25dc92c249c07f96e',
            'age_limit': 8,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'https://www.ertflix.gr/#/details/{video_id}', ERTFlixIE.ie_key(), video_id)


class ERTFlixIE(ERTFlixBaseIE):
    IE_NAME = 'ertflix'
    IE_DESC = 'ERTFLIX videos'
    _VALID_URL = r'https?://www\.ertflix\.gr/(?:[^/]+/)(?:details)/(?P<id>[^?&#]+)'
    _TESTS = [{
        'url': 'https://www.ertflix.gr/#/details/ERT_M001162',
        'md5': '6479d5e60fd7e520b07ba5411dcdd6e7',
        'info_dict': {
            'id': 'ERT_M001162',
            'ext': 'mp4',
            'title': 'Scoring a Goal in Love',
            'description': 'md5:ae2e217e579eecf25dc92c249c07f96e',
            'age_limit': 8,
        },
        'skip': 'Require login',
    }, {
        'url': 'https://www.ertflix.gr/#/details/ERT_PS054698_E0',
        'info_dict': {
            'id': 'ERT_PS054698',
            'title': 'The Oath',
            'age_limit': 8,
        },
        'playlist_mincount': 36,
        'skip': 'Require login',
    }, {
        'url': 'https://www.ertflix.gr/#/details/ERT_PS054134_E0',
        'info_dict': {
            'id': 'ERT_PS054134',
            'age_limit': 12,
        },
        'playlist_mincount': 8,
        'skip': 'Require login',
    }, {
        'url': 'https://www.ertflix.gr/#/details/ERT_PS054089_E0',
        'info_dict': {
            'id': 'ERT_PS054089',
            'age_limit': 8,
            'title': '5 Archelaοu Street',
        },
        'playlist_mincount': 80,
        'skip': 'Require login',
    }, {
        'url': 'https://www.ertflix.gr/#/details/ERT_DS019291_E0',
        'info_dict': {
            'id': 'ERT_DS019291',
            'title': 'The Beacons of Our Time',
            'age_limit': 8,
        },
        'playlist_mincount': 10,
        'skip': 'Require login',
    }, {
        'url': 'https://www.ertflix.gr/#/details/ERT_171308',
        'only_matching': True,
    }]

    def _extract_video(self, video_id, metadata=None):
        if not metadata:
            metadata = self._call_api(
                video_id,
                method=f'vod/{video_id}/mediacard')
        formats, subs = self._extract_formats(metadata, video_id)
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subs,
            'age_limit': self._parse_age_rating(metadata),
            'title': metadata.get('Title'),
            'description': metadata.get('Description'),
        }

    @staticmethod
    def _parse_age_rating(data):
        return parse_age_limit(
            traverse_obj(data, ('Ratings', 0, 'code'), ('Ratings', 0, 'precedence'))
            or data.get('AgeRating')
            or (data.get('IsAdultContent') and 18)
            or (data.get('IsKidsContent') and 0))

    def _extract_formats(self, data, video_id):
        if not isinstance(data, (dict, list)):
            return []

        formats, subtitles = [], {}
        urls = self.extract_urls_from_data(data)

        for url in urls or []:
            if not url:
                continue
            ext = determine_ext(url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    url, video_id, m3u8_id='hls', ext='mp4', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    url, video_id, mpd_id='dash', fatal=False)
            else:
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return formats, subtitles

    def _extract_season(self, season_data):
        season_id = season_data.get('id')
        season = self._call_api(
            season_id, method='delivery/v2/ERT/vod/editorials',
            api_version=None,
            params={
                'filter': json.dumps({
                    'editorial.seasonRef': season_id,
                    'locale': self._LANG,
                }),
                'sort': json.dumps([['editorial.episodeNumber', 1]]),
                'offset': 0,
                'limit': 300,
            },
        )
        for ep in season.get('editorials'):
            ep_id = ep.get('id')
            technicals = ep.get('technicals')
            formats, subtitles = self._extract_formats(technicals, ep_id)
            yield {
                'id': ep_id,
                'title': ep.get('Title'),
                'description': ep.get('Description'),
                'formats': formats,
                'subtitles': subtitles,
                'age_limit': self._parse_age_rating(ep),
            }

    def _extract_series(self, series_id, metadata):
        series_data = self._call_api(
            series_id, method='delivery/ERT/vod/series',
            api_version=None,
            params={
                'filter': json.dumps({
                    'seriesRef': series_id,
                    'locale': self._LANG,
                }),
                'sort': json.dumps([['SeasonNumber', 1]]),
                'offset': 0,
                'limit': 300,
            },
        )

        series_info = {
            'age_limit': self._parse_age_rating(metadata),
            'title': metadata.get('Title'),
            'description': metadata.get('Description'),
        }

        def entries(series_data):
            desired_seasons = self._configuration_arg('season', None, ie_key=self.ie_key())
            if desired_seasons:
                desired_seasons = [int(s) for s in desired_seasons]
            for season in traverse_obj(series_data, ('series')):
                if desired_seasons and season.get('SeasonNumberNumeric') not in desired_seasons:
                    continue
                yield from self._extract_season(season)

        return self.playlist_result(
            entries(series_data), playlist_id=series_id, **series_info)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._call_api(
            video_id,
            method=f'vod/{video_id}/mediacard')
        if seriesid := metadata.get('MasterSeries'):
            return self._extract_series(seriesid, metadata)
        return self._extract_video(video_id, metadata)


class ERTWebtvEmbedIE(InfoExtractor):
    IE_NAME = 'ertwebtv:embed'
    IE_DESC = 'ert.gr webtv embedded videos'
    _BASE_PLAYER_URL_RE = re.escape('//www.ert.gr/webtv/live-uni/vod/dt-uni-vod.php')
    _VALID_URL = rf'https?:{_BASE_PLAYER_URL_RE}\?([^#]+&)?f=(?P<id>[^#&]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+?src=(?P<_q1>["\'])(?P<url>(?:https?:)?{_BASE_PLAYER_URL_RE}\?(?:(?!(?P=_q1)).)+)(?P=_q1)']

    _TESTS = [{
        'url': 'https://www.ert.gr/webtv/live-uni/vod/dt-uni-vod.php?f=trailers/E2251_TO_DIKTYO_E09_16-01_1900.mp4&bgimg=/photos/2022/1/to_diktio_ep09_i_istoria_tou_diadiktiou_stin_Ellada_1021x576.jpg',
        'md5': 'f9e9900c25c26f4ecfbddbb4b6305854',
        'info_dict': {
            'id': 'trailers/E2251_TO_DIKTYO_E09_16-01_1900.mp4',
            'title': 'md5:914f06a73cd8b62fbcd6fb90c636e497',
            'ext': 'mp4',
            'thumbnail': 'https://program.ert.gr/photos/2022/1/to_diktio_ep09_i_istoria_tou_diadiktiou_stin_Ellada_1021x576.jpg',
        },
        'skip': 'Invalid URL',
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.ertnews.gr/video/manolis-goyalles-o-anthropos-piso-apo-ti-diadiktyaki-vasilopita/',
        'info_dict': {
            'id': '2022/tv/news-themata-ianouarios/20220114-apotis6-gouales-pita.mp4',
            'ext': 'mp4',
            'title': 'VOD - 2022/tv/news-themata-ianouarios/20220114-apotis6-gouales-pita.mp4',
            'thumbnail': r're:https?://www\.ert\.gr/themata/photos/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats, subs = self._extract_m3u8_formats_and_subtitles(
            f'https://mediastream.ert.gr/vodedge/_definst_/mp4:dvrorigin/{video_id}/playlist.m3u8',
            video_id, 'mp4')
        thumbnail_id = parse_qs(url).get('bgimg', [None])[0]
        if thumbnail_id and not thumbnail_id.startswith('http'):
            thumbnail_id = f'https://program.ert.gr{thumbnail_id}'
        return {
            'id': video_id,
            'title': f'VOD - {video_id}',
            'thumbnail': thumbnail_id,
            'formats': formats,
            'subtitles': subs,
        }

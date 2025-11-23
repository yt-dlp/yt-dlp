import json
import math
import time

from .common import ExtractorError, HTTPError, InfoExtractor
from ..utils import InAdvancePagedList, functools, int_or_none, jwt_decode_hs256, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class AGalegaBaseIE(InfoExtractor):
    _access_token = None

    @staticmethod
    def _jwt_is_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 120

    def _refresh_access_token(self, video_id):
        AGalegaBaseIE._access_token = self._download_json(
            'https://www.agalega.gal/api/fetch-api/jwt/token', video_id,
            note='Downloading access token',
            data=json.dumps({
                'username': None,
                'password': None,
                'client': 'crtvg',
                'checkExistsCookies': False,
            }).encode())['access']

    def _call_api(self, endpoint, display_id, note, fatal=True, query=None):
        if not AGalegaBaseIE._access_token or self._jwt_is_expired(AGalegaBaseIE._access_token):
            self._refresh_access_token(endpoint)
        return self._download_json(
            f'https://api-agalega.interactvty.com/api/2.0/contents/{endpoint}', display_id,
            note=note, fatal=fatal, query=query,
            headers={'Authorization': f'jwtok {AGalegaBaseIE._access_token}'})


class AGalegaIE(AGalegaBaseIE):
    IE_NAME = 'agalega:videos'
    _VALID_URL = r'https?://(?:www\.)?agalega\.gal/videos/(?:detail/)?(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.agalega.gal/videos/288664-lr-ninguencheconta',
        'md5': '04533a66c5f863d08dd9724b11d1c223',
        'info_dict': {
            'id': '288664',
            'title': 'Roberto e Ángel Martín atenden consultas dos espectadores',
            'description': 'O cómico ademais fai un repaso dalgúns momentos da súa traxectoria profesional',
            'thumbnail': 'https://crtvg-bucket.flumotion.cloud/content_cards/2ef32c3b9f6249d9868fd8f11d389d3d.png',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.agalega.gal/videos/detail/296152-pulso-activo-7',
        'md5': '26df7fdcf859f38ad92d837279d6b56d',
        'info_dict': {
            'id': '296152',
            'title': 'Pulso activo | 18-11-2025',
            'description': 'Anxo, Noemí, Silvia e Estrella  comparten as sensacións da clase de Eddy.',
            'thumbnail': 'https://crtvg-bucket.flumotion.cloud/content_cards/a6bb7da6c8994b82bf961ac6cad1707b.png',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content_data = self._call_api(
            f'content/{video_id}/', video_id, note='Downloading content data', fatal=False,
            query={
                'optional_fields': 'image,is_premium,short_description,has_subtitle',
            })
        resource_data = self._call_api(
            f'content_resources/{video_id}/', video_id, note='Downloading resource data',
            query={
                'optional_fields': 'media_url',
            })

        formats = []
        subtitles = {}
        for m3u8_url in traverse_obj(resource_data, ('results', ..., 'media_url', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, ext='mp4', m3u8_id='hls')
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(content_data, {
                'title': ('name', {str}),
                'description': (('description', 'short_description'), {str}, any),
                'thumbnail': ('image', {url_or_none}),
            }),
        }


class AGalegaSeriesIE(AGalegaBaseIE):
    IE_NAME = 'agalega:series'
    _VALID_URL = r'https?://(?:www\.)?agalega\.gal/videos/category/(?P<id>[0-9]+)'
    _CATEGORY_DATA = None
    _MAX_ITEMS = 10
    _TESTS = [{
        'url': 'https://www.agalega.gal/videos/category/27035-galician-friki',
        'info_dict': {
            'id': '27035',
            'title': 'Galician Friki',
        },
        'playlist_count': 7,
    }, {
        'url': 'https://www.agalega.gal/videos/category/17175-na-gloria?cat=17176',
        'info_dict': {
            'id': '17175',
            'title': 'Na Gloria',
        },
        'playlist_count': 17,
    }, {
        'url': 'https://www.agalega.gal/videos/category/30380-land-rober-show',
        'info_dict': {
            'id': '30380',
            'title': 'Land Rober + show',
        },
        'playlist_count': 34,
    }, {
        'url': 'https://www.agalega.gal/videos/category/17062-peliculas-e-documentais',
        'info_dict': {
            'id': '17062',
            'title': 'Películas e documentais ',
        },
        'playlist_count': 55,
    }]

    def _series_information(self, category_id):
        category_data = self._call_api(
            f'category/{category_id}/', category_id, 'series info',
            query={
                'optional_fields': 'image,short_description,has_subtitle,description',
            })
        AGalegaSeriesIE._CATEGORY_DATA = traverse_obj(category_data, {
            'series_id': ('id', {int}, {str_or_none}),
            'series_name': ('name', {str}),
        })

    def _get_episodes_per_season(self, season_id, season_name, page):
        try:
            category_content_data = self._call_api(
                f'category_contents/{season_id}', season_id, 'Downloading category content',
                query={
                    'optional_fields': 'image,short_description,has_subtitle,description',
                    'page': page + 2,
                },
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                return
            raise

        for episode in traverse_obj(category_content_data, 'results', ...):
            video_id = str_or_none(episode.get('id'))
            resource_data = self._call_api(
                f'content_resources/{video_id}/', video_id, note='Downloading resource data',
                query={'optional_fields': 'media_url'})

            m3u8_url = traverse_obj(resource_data, ('results', 0, 'media_url', {url_or_none}))
            yield self.url_result(m3u8_url,
                                  video_id=video_id, video_title=str_or_none(episode.get('name')), url_transparent=True,
                                  **traverse_obj(resource_data, ('results', 0, {
                                      'season_name': season_name,
                                      'season_id': season_id,
                                      'episode_id': video_id,
                                      'episode_name': ('name', {str}),
                                  })))

    def _process_episodes_from_data(self, category_content_data, season_id, season_name):
        for episode in traverse_obj(category_content_data, 'results', ...):
            video_id = str_or_none(episode.get('id'))
            resource_data = self._call_api(
                f'content_resources/{video_id}/', video_id, note='Downloading resource data',
                query={'optional_fields': 'media_url'})

            m3u8_url = traverse_obj(resource_data, ('results', 0, 'media_url', {url_or_none}))
            yield self.url_result(m3u8_url,
                                  video_id=video_id, video_title=str_or_none(episode.get('name')), url_transparent=True,
                                  **traverse_obj(resource_data, ('results', 0, {
                                      'season_name': season_name,
                                      'season_id': season_id,
                                      'episode_id': video_id,
                                      'episode_name': ('name', {str}),
                                  })))

    def _get_seasons_page(self, series_id, series_name):
        try:
            sub_category_data = self._call_api(
                f'subcategory/{series_id}/', series_id,
                'Downloading seasons',
                query={
                    'optional_fields': 'image,short_description,has_subtitle,description',
                },
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                return
            raise

        season_info = traverse_obj(sub_category_data, ('results', ..., {
            'season_id': ('id', {int}, {str_or_none}),
            'season_name': ('name', {str}),
        }))
        if season_info:
            for season in season_info:
                first_page = self._call_api(
                    f"category_contents/{season.get('season_id')}", season.get('season_id'),
                    f"Downloading episode count for season {season.get('season_name')}",
                    query={
                        'optional_fields': 'image,short_description,has_subtitle,description',
                    })

                total_count = int_or_none(first_page.get('count'))
                results_count = len(traverse_obj(first_page, ('results', ...)))

                if total_count is not None and total_count > results_count:
                    yield from self._process_episodes_from_data(first_page, season.get('season_id'), season.get('season_name'))
                    page_count = math.ceil(total_count / self._MAX_ITEMS)
                    yield from InAdvancePagedList(
                        functools.partial(self._get_episodes_per_season, season.get('season_id'),
                                          season.get('season_name')),
                        page_count - 1,
                        self._MAX_ITEMS)
                else:
                    yield from self._process_episodes_from_data(first_page, season.get('season_id'), season.get('season_name'))
        first_page = self._call_api(
            f'category_contents/{series_id}', series_id,
            f'Downloading episode count for season {series_name}',
            query={
                'optional_fields': 'image,short_description,has_subtitle,description',
            })
        total_count = int_or_none(first_page.get('count'))
        results_count = len(traverse_obj(first_page, ('results', ...)))

        if results_count:
            if total_count is not None and total_count > results_count:
                yield from self._process_episodes_from_data(first_page, series_id, series_name)
                page_count = math.ceil(total_count / self._MAX_ITEMS)
                yield from InAdvancePagedList(
                    functools.partial(self._get_episodes_per_season, series_id,
                                      series_name),
                    page_count - 1,
                    self._MAX_ITEMS)
            else:
                yield from self._process_episodes_from_data(first_page, series_id, series_name)

    def _real_extract(self, url):
        category_id = self._match_id(url)
        self._series_information(category_id)
        if self._CATEGORY_DATA:
            entries = self._get_seasons_page(self._CATEGORY_DATA.get('series_id'), self._CATEGORY_DATA.get('series_name'))
            return self.playlist_result(entries,
                                        self._CATEGORY_DATA.get('series_id'), self._CATEGORY_DATA.get('series_name'))

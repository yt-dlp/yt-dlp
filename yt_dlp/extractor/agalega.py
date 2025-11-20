import json

from .common import ExtractorError, HTTPError, InfoExtractor
from ..utils import itertools, require, str_or_none, traverse_obj, url_or_none


class AGalegaBaseIE(InfoExtractor):
    def _get_access_token(self, video_id):
        access_token = self._download_json(
            'https://www.agalega.gal/api/fetch-api/jwt/token', video_id,
            note='Downloading access token',
            data=json.dumps({
                'username': None,
                'password': None,
                'client': 'crtvg',
                'checkExistsCookies': False,
            }).encode())['access']
        return {'authorization': f'jwtok {access_token}'}


class AGalegaVideoIE(AGalegaBaseIE):
    IE_NAME = 'agalega:video'
    _VALID_URL = r'https?://(?:www\.)?agalega\.gal/videos/(?P<id>[0-9]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        auth_header = self._get_access_token(video_id)

        media_url = f'https://api-agalega.interactvty.com/api/2.0/contents/content_resources/{video_id}/?optional_fields=media_url'
        resource_data = self._download_json(media_url, video_id, headers=auth_header)

        m3u8_url = traverse_obj(resource_data, ('results', 0, 'media_url', {url_or_none}))
        if not m3u8_url:
            raise ExtractorError('Failed to extract m3u8 URL')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
        }


class AGalegaVideosIE(AGalegaBaseIE):
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
    },
        {
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
        playlist_id = self._match_id(url)
        auth_headers = self._get_access_token(playlist_id)
        content_data = self._download_json(
            f'https://api-agalega.interactvty.com/api/2.0/contents/content/{playlist_id}/', playlist_id,
            note='Downloading content data', fatal=False, headers=auth_headers,
            query={
                'optional_fields': 'image,is_premium,short_description,has_subtitle',
            })
        resource_data = self._download_json(
            f'https://api-agalega.interactvty.com/api/2.0/contents/content_resources/{playlist_id}/',
            playlist_id, note='Downloading resource data', headers=auth_headers,
            query={
                'optional_fields': 'media_url',
            })

        if content_data is not None and resource_data is not None:
            m3u8_url = traverse_obj(resource_data, ('results', ..., 'media_url', {url_or_none}, any, {require('media_url')}))
            formats = []
            subtitles = {}
            for m3u8_url in traverse_obj(resource_data, ('results', ..., 'media_url', {url_or_none})):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    m3u8_url, playlist_id, ext='mp4', m3u8_id='hls')
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            return {
                'id': playlist_id,
                'formats': formats,
                **traverse_obj(content_data, {
                    'title': ('name', {str_or_none}),
                    'description': (('description', 'short_description'), {str_or_none}, any),
                    'thumbnail': ('image', {url_or_none}),
                }),
            }
        return None


class AGalegaSeriesIE(AGalegaBaseIE):
    IE_NAME = 'agalega:series'
    _VALID_URL = r'https?://(?:www\.)?agalega\.gal/videos/category/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.agalega.gal/videos/category/27035-galician-friki',
        'info_dict': {
            'id': '27035',
        },
        'playlist_count': 7,
    }, {
        'url': 'https://www.agalega.gal/videos/category/17175-na-gloria?cat=17176',
        'info_dict': {
            'id': '17175',
        },
        'playlist_count': 17,
    }]

    def _get_episodes_for_season(self, season_id, season_name, auth_header):
        category_contents_url = f'https://api-agalega.interactvty.com/api/2.0/contents/category_contents/{season_id}/?optional_fields=image,short_description'

        content_data = self._download_json(
            category_contents_url,
            season_id,
            headers=auth_header,
            note=f'Downloading episodes for season {season_id}, page 1',
            fatal=False)

        if not content_data:
            return

        results = content_data.get('results') or []
        if results:
            for episode_item in results:
                episode_id = traverse_obj(episode_item, ('id', {int}, {str_or_none}))
                if not episode_id:
                    continue

                yield self.url_result(
                    f'https://www.agalega.gal/videos/{episode_id}',
                    ie=AGalegaVideoIE.ie_key(),
                    video_id=episode_id,
                    season=season_name,
                    **traverse_obj(episode_item, {
                        'title': ('name', {str}),
                        'thumbnail': ('image', {url_or_none}),
                        'description': (('description', 'short_description'), {str_or_none}, any),
                    }))

    def _get_season_entries_with_episodes(self, category_id, auth_header):
        sub_category_url = f'https://api-agalega.interactvty.com/api/2.0/contents/subcategory/{category_id}/?optional_fields=image'
        sub_category_data = None

        for should_retry in (True, False):
            try:
                sub_category_data = self._download_json(sub_category_url, category_id, headers=auth_header)
                break
            except ExtractorError as e:
                if should_retry and isinstance(e.cause, HTTPError) and e.cause.status == 401:
                    auth_header = self._get_access_token(category_id)
                    continue
                raise

        if not sub_category_data:
            return

        results = sub_category_data.get('results', [])
        if results:
            for season_item in results:
                season_id = traverse_obj(season_item, ('id', {int}, {str_or_none}))
                if not season_id:
                    continue

                season_name = traverse_obj(season_item, ('name', {str_or_none}))
                yield from self._get_episodes_for_season(season_id, season_name, auth_header)

        next_url = url_or_none(sub_category_data.get('next'))
        if not next_url:
            return

        for page_num in itertools.count(2):
            for should_retry in (True, False):
                try:
                    sub_category_data = self._download_json(
                        sub_category_url,
                        category_id,
                        headers=auth_header,
                        query={'page': page_num},
                        note=f'Downloading seasons page {page_num}',
                        fatal=True)
                    break
                except ExtractorError as e:
                    if should_retry and isinstance(e.cause, HTTPError) and e.cause.status == 401:
                        auth_header = self._get_access_token(category_id)
                        continue
                    raise

            if not sub_category_data:
                break

            results = sub_category_data.get('results', [])
            if not results:
                break

            for season_item in results:
                season_id = traverse_obj(season_item, ('id', {int}, {str_or_none}))
                if not season_id:
                    continue

                season_name = traverse_obj(season_item, ('name', {str_or_none}))
                yield from self._get_episodes_for_season(season_id, season_name, auth_header)

            next_url = url_or_none(sub_category_data.get('next'))
            if not next_url:
                break

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        auth_header = self._get_access_token(playlist_id)

        return self.playlist_result(
            self._get_season_entries_with_episodes(playlist_id, auth_header),
            playlist_id)

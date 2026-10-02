import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class CanariasPlayBaseIE(InfoExtractor):
    _API_BASE = 'https://api-rtvctv.interactvty.com/api/2.0/contents'

    def _get_api_headers(self, video_id):
        access_token = self._download_json(
            'https://www.canariasplay.es/api/fetch-api/jwt/token', video_id,
            'Downloading access token', data=json.dumps({'client': 'rtvctv'}).encode(),
            headers={'Content-Type': 'application/json'})['access']
        return {'Authorization': f'jwtok {access_token}'}


class CanariasPlayIE(CanariasPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?canariasplay\.es/(?:es/)?videos/(?:detail/)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.canariasplay.es/videos/detail/305962-resece50000a',
        'info_dict': {
            'id': '305962',
            'ext': 'mp4',
            'title': 'Capítulo 1 | 1983-1987',
            'description': 'md5:047b2f77c2c36e5e9bff15b40982a1fc',
            'thumbnail': 'https://d3n11mbncca13o.cloudfront.net/content_cards/f4fc07b19aca404b93f20b16dc759f8a.png',
            'duration': 1909,
            'timestamp': 1766137084,
            'upload_date': '20251219',
        },
    }, {
        'url': 'https://www.canariasplay.es/videos/305962-resece50000a',
        'info_dict': {
            'id': '305962',
            'ext': 'mp4',
            'title': 'Capítulo 1 | 1983-1987',
            'description': 'md5:047b2f77c2c36e5e9bff15b40982a1fc',
            'thumbnail': 'https://d3n11mbncca13o.cloudfront.net/content_cards/f4fc07b19aca404b93f20b16dc759f8a.png',
            'duration': 1909,
            'timestamp': 1766137084,
            'upload_date': '20251219',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_headers = self._get_api_headers(video_id)

        content_data = self._download_json(
            f'{self._API_BASE}/content/{video_id}/', video_id,
            'Downloading content metadata', fatal=False, expected_status=(404, 452), headers=api_headers,
            query={'optional_fields': 'description,short_description,image,duration,created_at'})
        error = traverse_obj(content_data, ('error', {str}))
        if error == 'RESOURCE_NOT_FOUND':
            raise ExtractorError('Video not found', expected=True)
        if error == 'GEO_BLOCKED':
            self.raise_geo_restricted(traverse_obj(content_data, ('reason', 'message', {str})))

        resource_data = self._download_json(
            f'{self._API_BASE}/content_resources/{video_id}/', video_id,
            'Downloading resource metadata', headers=api_headers,
            query={'optional_fields': 'is_initial,assets'})

        resources = traverse_obj(resource_data, ('results', ..., {dict}))
        resources.sort(key=lambda resource: not resource.get('is_initial'))
        hls_url, selected_resource = None, {}
        has_drm = False
        for resource in resources:
            for asset in traverse_obj(resource, ('assets', ..., {dict})):
                asset_url = url_or_none(asset.get('url'))
                if asset.get('type') != 'HLS' or not asset_url:
                    continue
                if asset.get('drm_type'):
                    has_drm = True
                    continue
                hls_url, selected_resource = asset_url, resource
                break
            if hls_url:
                break

        formats, subtitles = [], {}
        if hls_url:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, 'mp4', m3u8_id='hls')
        elif has_drm:
            self.report_drm(video_id)
        else:
            self.raise_no_formats(
                'No playable HLS resource found', expected=True, video_id=video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(selected_resource, {
                'title': ('name', {str.strip}),
            }),
            **traverse_obj(content_data, {
                'title': ('name', {str.strip}),
                'description': (('description', 'short_description'), {str}, any),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('duration', {float_or_none}),
                'timestamp': ('created_at', {parse_iso8601}),
            }),
        }


class CanariasPlayCategoryIE(CanariasPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?canariasplay\.es/(?:es/)?videos/category/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.canariasplay.es/videos/category/32711-plum-la-superbruja',
        'info_dict': {
            'id': '32711',
            'title': 'Plum, la superbruja',
        },
        'playlist_mincount': 30,
    }]

    def _entries(self, category_id, api_headers):
        next_url = f'{self._API_BASE}/category_contents/{category_id}/'
        for page_num in itertools.count(1):
            page = self._download_json(
                next_url, category_id, f'Downloading category page {page_num}', headers=api_headers)
            for content in page['results']:
                video_id = str(content['id'])
                yield self.url_result(
                    f'https://www.canariasplay.es/videos/detail/{video_id}',
                    CanariasPlayIE, video_id, content.get('name'))
            next_url = page.get('next')
            if not next_url:
                break

    def _real_extract(self, url):
        category_id = self._match_id(url)
        api_headers = self._get_api_headers(category_id)
        category = self._download_json(
            f'{self._API_BASE}/category/{category_id}/', category_id,
            'Downloading category metadata', fatal=False, headers=api_headers)
        return self.playlist_result(
            self._entries(category_id, api_headers), category_id,
            traverse_obj(category, ('name', {str})))

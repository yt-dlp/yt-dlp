import json
import math
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    int_or_none,
    orderedSet,
    parse_iso8601,
    str_or_none,
)


class ShahidBaseIE(InfoExtractor):
    _API_BASE = 'https://api3.shahid.net/proxy/v2.1'
    _VALID_URL_BASE = r'https?://shahid\.mbc\.net/[a-z]{2}/'

    def _call_api(self, path, item_id, request):
        api_url = f'{self._API_BASE}/{path}'
        query_params = {'request': json.dumps(request)}
        query_string = urllib.parse.urlencode(query_params)
        return self._download_json(f'{api_url}?{query_string}', item_id)

    def _call_playout_api(self, video_id, country):
        query_params = {'outputParameter': 'vmap'}
        if country:
            query_params['country'] = country
        query_string = urllib.parse.urlencode(query_params)
        api_url = f'{self._API_BASE}/playout/new/url/{video_id}?{query_string}'

        return self._download_json(api_url, video_id, note=f'Downloading API JSON for country={country}', fatal=False)

    def get_formats_subtitles(self, video_id, live):
        geo_bypass_country = self.get_param('geo_bypass_country', None)
        # Try multiple country codes for geo-unblocking
        countries = orderedSet((geo_bypass_country, None, 'SA', 'AE', 'EG', 'US'))
        response = None
        for country_code in countries:
            try:
                response = self._call_playout_api(video_id, country_code)
                if response:
                    break
            except Exception as e:
                self.write_debug(f'API call failed for country={country_code}: {e}')
                continue

        if not response:
            raise ExtractorError('Unable to get a successful API response for ' + video_id)

        playout = response.get('playout', {})
        if not self.get_param('allow_unplayable_formats') and playout.get('drm', False):
            self.report_drm(video_id)

        stream_url = playout.get('url')
        if not stream_url:
            raise ExtractorError('Stream URL not found in API response.')

        return self._extract_m3u8_formats_and_subtitles(re.sub(
            # https://docs.aws.amazon.com/mediapackage/latest/ug/manifest-filtering.html
            r'aws\.manifestfilter=[\w:;,-]+&?',
            '', stream_url), video_id, 'mp4', live=live)

    def _get_product_info(self, product_id):
        return self._call_api('product/id', product_id, {
            'id': product_id,
        })

    def remove_params(self, url):
        if url:
            parsed_url = urllib.parse.urlparse(url)
            return urllib.parse.urlunparse(parsed_url._replace(query=''))
        return url


class ShahidIE(ShahidBaseIE):
    _VALID_URL = ShahidBaseIE._VALID_URL_BASE + r'player/(?P<type>clips|episodes)/(?P<title>[^/]+)/id-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://shahid.mbc.net/ar/player/clips/Al-Daheeh-Museum-season-1-clip-1/id-816924',
        'info_dict': {
            'id': '816924',
            'ext': 'mp4',
            'title': 'برومو',
            'timestamp': 1602806400,
            'upload_date': '20201016',
            'description': 'برومو',
            'duration': 22,
            'categories': ['كوميديا'],
            'thumbnail': r're:^https?://.*\.jpg$',
            'series': 'متحف الدحيح',
            'season': 1,
            'season_number': 1,
            'season_id': '816485',
            'episode': 'Episode 1',
            'episode_number': 1,
            'episode_id': '816924',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://shahid.mbc.net/en/player/episodes/Ramez-Fi-Al-Shallal-season-1-episode-1/id-359319',
        'info_dict': {
            'id': '359319',
            'title': 'فيفي عبدو',
            'description': 'فيفي عبدو',
            'duration': 1530,
            'thumbnail': r're:^https?://.*\.jpg$',
            'categories': ['كوميديا', 'مصري', 'تلفزيون الواقع'],
            'series': 'رامز في الشلال',
            'season': 'Season 1',
            'season_number': 1,
            'season_id': '357909',
            'episode': 'Episode 1',
            'episode_number': 1,
            'episode_id': '359319',
            'timestamp': 1557162000,
            'upload_date': '20190506',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://shahid.mbc.net/en/player/episodes/Maraya-season-1-episode-1/id-985363',
        'info_dict': {
            'id': '985363',
            'title': 'مرايا',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 3144,
            'timestamp': 1683158400,
            'categories': ['كوميديا', 'سوري'],
            'series': 'مرايا',
            'episode_number': 1,
            'episode_id': '985363',
            'upload_date': '20230504',
            'episode': 'Episode 1',
            'season': 1,
            'season_number': 1,
            'season_id': '985240',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://shahid.mbc.net/ar/player/episodes/Bab-Al-Hara-season-3-episode-17/id-76878',
        'info_dict': {
            'id': '76878',
            'title': 'باب الحارة',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2647,
            'timestamp': 1399334400,
            'categories': ['إجتماعي', 'سوري', 'دراما'],
            'series': 'باب الحارة',
            'episode_number': 17,
            'episode_id': '76878',
            'upload_date': '20140506',
            'episode': 'Episode 17',
            'season': 3,
            'season_number': 3,
            'season_id': '68680',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats, subtitles = self.get_formats_subtitles(video_id, live=False)

        product_info_response = self._get_product_info(video_id)
        product = product_info_response.get('productModel', {})
        show = product.get('show', {})
        season = show.get('season', {})

        return {
            'id': video_id,
            'title': str_or_none(product.get('title') or show.get('title')),
            'description': str_or_none(product.get('description')),
            'thumbnail': str_or_none(self.remove_params(product.get('thumbnailImage'))),
            'duration': int_or_none(product.get('duration')),
            'timestamp': parse_iso8601(product.get('createdDate')),
            'categories': [genre.get('title') for genre in product.get('genres', []) if genre.get('title')],
            'series': str_or_none(show.get('title')),
            'season': int_or_none(season.get('seasonName')),
            'season_number': int_or_none(season.get('seasonNumber')),
            'season_id': str_or_none(season.get('id')),
            'episode_number': int_or_none(product.get('number')),
            'episode_id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'ext': 'mp4',
        }


class ShahidLiveIE(ShahidBaseIE):
    _VALID_URL = ShahidBaseIE._VALID_URL_BASE + r'?livestream/[^/]+/livechannel-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://shahid.mbc.net/en/livestream/SBC/livechannel-946940',
        'only_matching': True,  # DRM Protected
    }, {
        'url': 'https://shahid.mbc.net/fr/livestream/Wanasa/livechannel-414449',
        'info_dict': {
            'id': '414449',
            'title': str,
            'live_status': 'is_live',
            'description': 'md5:eba66fad0a5fd9c8081d5158145dc924',
            'thumbnail': str,
            'categories': ['عمل غنائي', 'موسيقي'],
            'ext': 'mp4',
        },
    }, {
        'url': 'https://shahid.mbc.net/en/livestream/MBC1/livechannel-387238',
        'info_dict': {
            'id': '387238',
            'title': str,
            'live_status': 'is_live',
            'description': 'md5:2562c67c7897e59c763c713c6a7712ec',
            'thumbnail': str,
            'categories': ['دراما'],
            'ext': 'mp4',
        },
    }, {
        'url': 'https://shahid.mbc.net/ar/livestream/MBC1/livechannel-816764',  # Requires country = 'US'
        'info_dict': {
            'id': '816764',
            'title': str,
            'live_status': 'is_live',
            'description': 'md5:14faec01d54423a5dadaef27dd525130',
            'thumbnail': str,
            'categories': ['دراما'],
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        product_info_response = self._get_product_info(video_id)
        product = product_info_response.get('productModel', {})
        formats, subtitles = self.get_formats_subtitles(video_id, live=True)

        return {
            'id': video_id,
            'title': str_or_none(product.get('title')),
            'description': str_or_none(product.get('description')),
            'thumbnail': str_or_none(self.remove_params(product.get('thumbnailImage'))),
            'categories': [genre.get('title') for genre in product.get('genres', []) if genre.get('title')],
            'formats': formats,
            'subtitles': subtitles,
            'ext': 'mp4',
            'is_live': True,
        }


class ShahidShowIE(ShahidBaseIE):
    _VALID_URL = ShahidBaseIE._VALID_URL_BASE + r'(?:show|serie)s/[^/]+/(?:show|series)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://shahid.mbc.net/ar/shows/%D8%B1%D8%A7%D9%85%D8%B2-%D9%82%D8%B1%D8%B4-%D8%A7%D9%84%D8%A8%D8%AD%D8%B1/show-79187',
        'info_dict': {
            'id': '79187',
            'title': 'رامز قرش البحر',
            'description': 'md5:d85c0675eb07251f9ec5273ee1979496',
        },
        'playlist_mincount': 32,
    }, {
        'url': 'https://shahid.mbc.net/ar/series/How-to-live-Longer-(The-Big-Think)/series-291861',
        'only_matching': True,
    }]
    _PAGE_SIZE = 30

    def _real_extract(self, url):
        show_id = self._match_id(url)

        product = self._call_api(
            'playableAsset', show_id, {'showId': show_id})['productModel']
        playlist = product['playlist']
        playlist_id = playlist['id']
        show = product.get('show', {})

        def page_func(page_num):
            playlist = self._call_api(
                'product/playlist', show_id, {
                    'playListId': playlist_id,
                    'pageNumber': page_num,
                    'pageSize': 30,
                    'sorts': [{
                        'order': 'DESC',
                        'type': 'SORTDATE',
                    }],
                })
            for product in playlist.get('productList', {}).get('products', []):
                product_url = product.get('productUrl', []).get('url')
                if not product_url:
                    continue
                yield self.url_result(
                    product_url, 'Shahid',
                    str_or_none(product.get('id')),
                    product.get('title'))

        entries = InAdvancePagedList(
            page_func,
            math.ceil(playlist['count'] / self._PAGE_SIZE),
            self._PAGE_SIZE)

        return self.playlist_result(
            entries, show_id, show.get('title'), show.get('description'))

import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    clean_podcast_url,
    int_or_none,
    jwt_decode_hs256,
    jwt_encode,
    parse_iso8601,
    try_call,
    update_url,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class AppleBaseIE(InfoExtractor):
    """Subclasses must set _BASE_URL and _JWT_KEY_ID"""

    _jwt_cache = {}

    @staticmethod
    def _jwt_is_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 120

    def _get_token(self, webpage, episode_id):
        if self._jwt_cache.get(self._BASE_URL) and not self._jwt_is_expired(self._jwt_cache[self._BASE_URL]):
            return self._jwt

        js_path = self._search_regex(
            r'<script [^>]*\bsrc="(/assets/index~[0-9a-f]+\.js)">', webpage, 'JS asset path')
        js_code = self._download_webpage(
            urljoin(self._BASE_URL, js_path), episode_id,
            'Downloading JS asset', 'Unable to download JS asset')

        header = jwt_encode({}, '', headers={'typ': 'JWT', 'alg': 'ES256', 'kid': self._JWT_KEY_ID}).split('.')[0]
        self._jwt_cache[self._BASE_URL] = self._search_regex(
            fr'(["\'])(?P<jwt>{header}(?:\.[\w-]+){{2}})\1', js_code, 'JSON Web Token', group='jwt')
        if self._jwt_is_expired(self._jwt_cache[self._BASE_URL]):
            raise ExtractorError('The fetched token is already expired')

        return self._jwt_cache[self._BASE_URL]


class ApplePodcastsIE(AppleBaseIE):
    IE_NAME = 'apple:podcasts'
    IE_DESC = 'Apple Podcasts'

    _VALID_URL = r'https?://podcasts\.apple\.com/(?P<country>[^/?#]+/)?podcast(?:/[^/?#]+){1,2}/?\?(?:[^#]+&)?i=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/us/podcast/urbana-podcast-724-by-david-penn/id1531349107?i=1000748574256',
        'md5': 'f8a6f92735d0cfbd5e6a7294151e28d8',
        'info_dict': {
            'id': '1000748574256',
            'ext': 'm4a',
            'title': 'URBANA PODCAST 724 BY DAVID PENN',
            'episode': 'URBANA PODCAST 724 BY DAVID PENN',
            'description': 'md5:fec77bacba32db8c9b3dda5486ed085f',
            'upload_date': '20260206',
            'timestamp': 1770400801,
            'duration': 3602,
            'series': 'Urbana Radio Show',
            'thumbnail': r're:https://.+/.+\.jpg',
        },
    }, {
        'url': 'https://podcasts.apple.com/us/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'md5': 'baf8a6b8b8aa6062dbb4639ed73d0052',
        'info_dict': {
            'id': '1000482637777',
            'ext': 'mp3',
            'title': '207 - Whitney Webb Returns',
            'episode': '207 - Whitney Webb Returns',
            'episode_number': 207,
            'description': 'md5:75ef4316031df7b41ced4e7b987f79c6',
            'upload_date': '20200705',
            'timestamp': 1593932400,
            'duration': 5369,
            'series': 'The Tim Dillon Show',
            'thumbnail': r're:https://.+/.+\.jpg',
        },
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/id1135137367?i=1000482637777',
        'only_matching': True,
    }]

    _BASE_URL = 'https://podcasts.apple.com'
    _JWT_KEY_ID = 'C4J7GBP74H'

    def _extract_podcast_from_api(self, webpage, episode_id, country_code):
        data = self._download_json(
            f'https://amp-api.podcasts.apple.com/v1/catalog/{country_code or "us"}/podcast-episodes/{episode_id}',
            episode_id, headers={
                'Authorization': f'Bearer {self._get_token(webpage, episode_id)}',
                'Origin': self._BASE_URL,
            },
            query={
                # XXX: if video is available, try adding the params 'with=entitlements,hlsVideo'
                'extend': 'fullDescription',
                'include': 'podcast',
                'l': 'en-US',
            })['data'][0]

        thumb_info = traverse_obj(data, ('attributes', 'artwork', {
            'url': ('url', {url_or_none}),
            'h': ('height', {int_or_none}),
            'w': ('width', {int_or_none}),
        }))

        return {
            'id': episode_id,
            **traverse_obj(data, {
                'title': ('attributes', 'name', {str}),
                'description': ('attributes', 'fullDescription', {clean_html}),
                'url': ('attributes', 'assetUrl', {clean_podcast_url}, {update_url(scheme='https')}),
                'timestamp': ('attributes', 'releaseDateTime', {parse_iso8601}),
                'duration': ('attributes', 'durationInMilliseconds', {int_or_none(scale=1000)}),
                'episode': ('attributes', 'name', {str}),
                'episode_number': ('attributes', 'episodeNumber', {int_or_none}),
                'series': ('relationships', 'podcast', 'data', 0, 'attributes', 'name', {str}),
            }),
            'thumbnail': try_call(lambda: thumb_info.pop('url').format(f='jpg', **thumb_info)),
            'vcodec': 'none',
        }

    def _extract_podcast_from_webpage(self, webpage, episode_id):
        server_data = self._search_json(
            r'<script [^>]*\bid=["\']serialized-server-data["\'][^>]*>', webpage,
            'server data', episode_id, default=None)
        model_data = traverse_obj(server_data, (
            'data', 0, 'data', 'headerButtonItems',
            lambda _, v: v['$kind'] == 'share' and v['modelType'] == 'EpisodeLockup',
            'model', {dict}, any))
        if not model_data:
            return None

        return {
            'id': episode_id,
            **traverse_obj(model_data, {
                'title': ('title', {str}),
                'description': ('summary', {clean_html}),
                'url': ('playAction', 'episodeOffer', 'streamUrl', {clean_podcast_url}),
                'timestamp': ('releaseDate', {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
                'episode': ('title', {str}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'series': ('showTitle', {str}),
            }),
            'thumbnail': self._og_search_thumbnail(webpage),
            'vcodec': 'none',
        }

    def _real_extract(self, url):
        episode_id, country_code = self._match_valid_url(url).group('id', 'country')
        # Webpage may be unavailable, see https://github.com/yt-dlp/yt-dlp/issues/17266
        webpage = self._download_webpage(url, episode_id, expected_status=500)

        return (
            self._extract_podcast_from_webpage(webpage, episode_id)
            or self._extract_podcast_from_api(webpage, episode_id, country_code))

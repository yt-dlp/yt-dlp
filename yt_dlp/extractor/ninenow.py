import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    smuggle_url,
    str_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
)
from ..utils.traversal import traverse_obj


class NineNowIE(InfoExtractor):
    IE_NAME = '9now.com.au'
    _VALID_URL = r'https?://(?:www\.)?9now\.com\.au/(?:[^/]+/){2}(?P<id>(?P<type>clip|episode)-[^/?#]+)'
    _GEO_COUNTRIES = ['AU']
    _TESTS = [{
        # clip
        'url': 'https://www.9now.com.au/today/season-2025/clip-cm8hw9h5z00080hquqa5hszq7',
        'info_dict': {
            'id': '6370295582112',
            'ext': 'mp4',
            'title': 'Would Karl Stefanovic be able to land a plane?',
            'description': 'The Today host\'s skills are put to the test with the latest simulation tech.',
            'uploader_id': '4460760524001',
            'duration': 197.376,
            'tags': ['clip', 'flights', 'technology', 'karl stefanovic'],
            'season': 'Season 2025',
            'season_number': 2025,
            'timestamp': 1742507988,
            'upload_date': '20250320',
            'release_date': '20250320',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # episode
        'url': 'https://www.9now.com.au/afl-footy-show/2016/episode-19',
        'only_matching': True,
    }, {
        # DRM protected
        'url': 'https://www.9now.com.au/andrew-marrs-history-of-the-world/season-1/episode-1',
        'only_matching': True,
    }, {
        # episode of series
        'url': 'https://www.9now.com.au/lego-masters/season-3/episode-3',
        'info_dict': {
            'id': '6308830406112',
            'title': 'Episode 3',
            'ext': 'mp4',
            'season_number': 3,
            'episode_number': 3,
            'description': 'In the first elimination of the competition, teams will have 10 hours to build a world inside a snow globe.',
            'uploader_id': '4460760524001',
            'timestamp': 1619002200,
            'upload_date': '20210421',
            'duration': 3574.085,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'tags': ['episode'],
            'season': 'Season 3',
            'episode': 'Episode 3',
            'release_date': '20210421',
        },
        'params': {
            'skip_download': True,
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/4460760524001/default_default/index.html?videoId=%s'

    # XXX: For parsing next.js v15+ data; see also yt_dlp.extractor.francetv and yt_dlp.extractor.goplay
    def _find_json(self, s):
        return self._search_json(
            r'\w+\s*:\s*', s, 'next js data', None, contains_pattern=r'\[(?s:.+)\]', default=None)

    def _old_extract_common_data(self, webpage, display_id, video_type):
        self.write_debug('Falling back to the old method for extracting common data')

        page_data = self._parse_json(self._search_regex(
            r'window\.__data\s*=\s*({.*?});', webpage,
            'page data', default='{}'), display_id, fatal=False)
        if not page_data:
            page_data = self._parse_json(self._parse_json(self._search_regex(
                r'window\.__data\s*=\s*JSON\.parse\s*\(\s*(".+?")\s*\)\s*;',
                webpage, 'page data'), display_id), display_id)

        for kind in ('episode', 'clip'):
            current_key = page_data.get(kind, {}).get(
                f'current{kind.capitalize()}Key')
            if not current_key:
                continue
            cache = page_data.get(kind, {}).get(f'{kind}Cache', {})
            if not cache:
                continue
            return {
                video_type: (cache.get(current_key) or next(iter(cache.values())))[kind],
                'season': (cache.get(current_key) or next(iter(cache.values()))).get('season', None),
            }

    def _real_extract(self, url):
        display_id, video_type = self._match_valid_url(url).group('id', 'type')
        webpage = self._download_webpage(url, display_id)

        common_data = traverse_obj(
            re.findall(r'<script[^>]*>\s*self\.__next_f\.push\(\s*(\[.+?\])\s*\);?\s*</script>', webpage),
            (..., {json.loads}, ..., {self._find_json},
             lambda _, v: v['payload'][video_type]['slug'] == display_id,
             'payload', any)) or self._old_extract_common_data(webpage, display_id, video_type)
        if not common_data:
            raise ExtractorError('Unable to extract video data')

        if traverse_obj(common_data, (video_type, 'video', 'drm', {bool})):
            self.report_drm(display_id)
        brightcove_id = try_get(
            common_data, lambda x: x[video_type]['video']['brightcoveId'], str) or 'ref:{}'.format(common_data[video_type]['video']['referenceId'])
        video_id = str_or_none(try_get(common_data, lambda x: x['episode']['video']['id'])) or brightcove_id

        title = try_get(common_data, lambda x: x[video_type]['name'], str)
        season_number = try_get(common_data, lambda x: x['season']['seasonNumber'], int)
        episode_number = try_get(common_data, lambda x: x['episode']['episodeNumber'], int)
        timestamp = unified_timestamp(try_get(common_data, lambda x: x['episode']['airDate'], str))
        release_date = unified_strdate(try_get(common_data, lambda x: x[video_type]['availability'], str))
        thumbnails_data = try_get(common_data, lambda x: x['episode']['image']['sizes'], dict) or {}
        thumbnails = [{
            'id': thumbnail_id,
            'url': thumbnail_url,
            'width': int_or_none(thumbnail_id[1:]),
        } for thumbnail_id, thumbnail_url in thumbnails_data.items()]

        return {
            '_type': 'url_transparent',
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id,
                {'geo_countries': self._GEO_COUNTRIES}),
            'id': video_id,
            'title': title,
            'description': try_get(common_data, lambda x: x[video_type]['description'], str),
            'duration': float_or_none(try_get(common_data, lambda x: x[video_type]['video']['duration'], float), 1000),
            'thumbnails': thumbnails,
            'ie_key': 'BrightcoveNew',
            'season_number': season_number,
            'episode_number': episode_number,
            'timestamp': timestamp,
            'release_date': release_date,
        }

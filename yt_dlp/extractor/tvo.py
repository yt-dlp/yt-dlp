import json
import urllib.parse

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_duration,
    parse_iso8601,
    smuggle_url,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import (
    require,
    traverse_obj,
    trim_str,
)


class TvoIE(InfoExtractor):
    IE_NAME = 'TVO'
    _VALID_URL = r'https?://(?:www\.)?tvo\.org/video(?:/documentaries)?/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.tvo.org/video/how-can-ontario-survive-the-trade-war',
        'info_dict': {
            'id': '6377531034112',
            'ext': 'mp4',
            'title': 'How Can Ontario Survive the Trade War?',
            'description': 'md5:e7455d9cd4b6b1270141922044161457',
            'display_id': 'how-can-ontario-survive-the-trade-war',
            'duration': 3531,
            'episode': 'How Can Ontario Survive the Trade War?',
            'episode_id': 'how-can-ontario-survive-the-trade-war',
            'episode_number': 1,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'TVO at AMO',
            'series_id': 'tvo-at-amo',
            'tags': 'count:17',
            'thumbnail': r're:https?://.+',
            'timestamp': 1756944016,
            'upload_date': '20250904',
            'uploader_id': '18140038001',
        },
    }, {
        'url': 'https://www.tvo.org/video/documentaries/the-pitch',
        'info_dict': {
            'id': '6382500333112',
            'ext': 'mp4',
            'title': 'The Pitch',
            'categories': ['Documentaries'],
            'description': 'md5:9d4246b70dce772a3a396c4bd84c8506',
            'display_id': 'the-pitch',
            'duration': 5923,
            'episode': 'The Pitch',
            'episode_id': 'the-pitch',
            'episode_number': 1,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'The Pitch',
            'series_id': 'the-pitch',
            'tags': 'count:8',
            'thumbnail': r're:https?://.+',
            'timestamp': 1762693216,
            'upload_date': '20251109',
            'uploader_id': '18140038001',
        },
    }, {
        'url': 'https://www.tvo.org/video/documentaries/valentines-day',
        'info_dict': {
            'id': '6387298331112',
            'ext': 'mp4',
            'title': 'Valentine\'s Day',
            'categories': ['Documentaries'],
            'description': 'md5:b142149beb2d3a855244816c50cd2f14',
            'display_id': 'valentines-day',
            'duration': 3121,
            'episode': 'Valentine\'s Day',
            'episode_id': 'valentines-day',
            'episode_number': 2,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'How We Celebrate',
            'series_id': 'how-we-celebrate',
            'tags': 'count:6',
            'thumbnail': r're:https?://.+',
            'timestamp': 1770386416,
            'upload_date': '20260206',
            'uploader_id': '18140038001',
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/18140038001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        video_data = self._download_json(
            'https://hmy0rc1bo2.execute-api.ca-central-1.amazonaws.com/graphql',
            display_id, headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'operationName': 'getVideo',
                'variables': {'slug': urllib.parse.urlparse(url).path.rstrip('/')},
                'query': '''query getVideo($slug: String) {
                  getTVOOrgVideo(slug: $slug) {
                    contentCategory
                    description
                    length
                    program {
                      nodeUrl
                      title
                    }
                    programOrder
                    publishedAt
                    season
                    tags
                    thumbnail
                    title
                    videoSource {
                      brightcoveRefId
                    }
                  }
                }''',
            }, separators=(',', ':')).encode(),
        )['data']['getTVOOrgVideo']

        brightcove_id = traverse_obj(video_data, (
            'videoSource', 'brightcoveRefId', {str_or_none}, {require('Brightcove ID')}))

        return {
            '_type': 'url_transparent',
            'ie_key': BrightcoveNewIE.ie_key(),
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id, {'geo_countries': ['CA']}),
            'display_id': display_id,
            'episode_id': display_id,
            **traverse_obj(video_data, {
                'title': ('title', {clean_html}, filter),
                'categories': ('contentCategory', {clean_html}, filter, all, filter),
                'description': ('description', {clean_html}, filter),
                'duration': ('length', {parse_duration}),
                'episode': ('title', {clean_html}, filter),
                'episode_number': ('programOrder', {int_or_none}),
                'season_number': ('season', {int_or_none}),
                'tags': ('tags', ..., {clean_html}, filter),
                'thumbnail': ('thumbnail', {url_or_none}),
                'timestamp': ('publishedAt', {parse_iso8601}),
            }),
            **traverse_obj(video_data, ('program', {
                'series': ('title', {clean_html}, filter),
                'series_id': ('nodeUrl', {clean_html}, {trim_str(start='/programs/')}, filter),
            })),
        }

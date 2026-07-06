from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_iso8601,
    parse_resolution,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import (
    get_first,
    require,
    traverse_obj,
    value,
)


class NineNowIE(InfoExtractor):
    IE_NAME = '9now.com.au'
    _VALID_URL = r'https?://(?:www\.)?9now\.com\.au/(?:[^/?#]+/){2}(?P<id>(?P<type>clip|episode)-[^/?#]+)'
    _GEO_BYPASS = False
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
            'tags': ['flights', 'technology', 'Karl Stefanovic'],
            'season': 'Season 2025',
            'season_number': 2025,
            'series': 'TODAY',
            'timestamp': 1742507988,
            'upload_date': '20250320',
            'release_timestamp': 1742507983,
            'release_date': '20250320',
            'thumbnail': r're:https?://.+/1920x0/.+\.jpg',
        },
        'params': {
            'skip_download': 'HLS/DASH fragments and mp4 URLs are geo-restricted; only available in AU',
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
            'thumbnail': r're:https?://.+/1920x0/.+\.jpg',
            'tags': ['episode'],
            'series': 'Lego Masters',
            'season': 'Season 3',
            'episode': 'Episode 3',
            'release_timestamp': 1619002200,
            'release_date': '20210421',
        },
        'params': {
            'skip_download': 'HLS/DASH fragments and mp4 URLs are geo-restricted; only available in AU',
        },
    }, {
        'url': 'https://www.9now.com.au/married-at-first-sight/season-12/episode-1',
        'info_dict': {
            'id': '6367798770112',
            'ext': 'mp4',
            'title': 'Episode 1',
            'description': r're:The cultural sensation of Married At First Sight returns with our first weddings! .{90}$',
            'uploader_id': '4460760524001',
            'duration': 5415.079,
            'thumbnail': r're:https?://.+/1920x0/.+\.png',
            'tags': ['episode'],
            'season': 'Season 12',
            'season_number': 12,
            'episode': 'Episode 1',
            'episode_number': 1,
            'series': 'Married at First Sight',
            'timestamp': 1737973800,
            'upload_date': '20250127',
            'release_timestamp': 1737973800,
            'release_date': '20250127',
        },
        'params': {
            'skip_download': 'HLS/DASH fragments and mp4 URLs are geo-restricted; only available in AU',
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/4460760524001/default_default/index.html?videoId={}'

    def _real_extract(self, url):
        display_id, video_type = self._match_valid_url(url).group('id', 'type')
        webpage = self._download_webpage(url, display_id)

        common_data = get_first(self._search_nextjs_v13_data(webpage, display_id), ('payload', {dict}))

        if traverse_obj(common_data, (video_type, 'video', 'drm', {bool})):
            self.report_drm(display_id)
        brightcove_id = traverse_obj(common_data, (
            video_type, 'video', (
                ('brightcoveId', {str}),
                ('referenceId', {str}, {lambda x: f'ref:{x}' if x else None}),
            ), any, {require('brightcove ID')}))

        return {
            '_type': 'url_transparent',
            'ie_key': BrightcoveNewIE.ie_key(),
            'url': self.BRIGHTCOVE_URL_TEMPLATE.format(brightcove_id),
            **traverse_obj(common_data, {
                'id': (video_type, 'video', 'id', {int}, ({str_or_none}, {value(brightcove_id)}), any),
                'title': (video_type, 'name', {str}),
                'description': (video_type, 'description', {str}),
                'duration': (video_type, 'video', 'duration', {float_or_none(scale=1000)}),
                'tags': (video_type, 'tags', ..., 'name', {str}, all, filter),
                'series': ('tvSeries', 'name', {str}),
                'season_number': ('season', 'seasonNumber', {int_or_none}),
                'episode_number': ('episode', 'episodeNumber', {int_or_none}),
                'timestamp': ('episode', 'airDate', {parse_iso8601}),
                'release_timestamp': (video_type, 'availability', {parse_iso8601}),
                'thumbnails': (video_type, 'image', 'sizes', {dict.items}, lambda _, v: url_or_none(v[1]), {
                    'id': 0,
                    'url': 1,
                    'width': (1, {parse_resolution}, 'width'),
                }),
            }),
        }

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    smuggle_url,
    str_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
)


class NineNowIE(InfoExtractor):
    IE_NAME = '9now.com.au'
    _VALID_URL = r'https?://(?:www\.)?9now\.com\.au/(?:[^/]+/){2}(?P<id>[^/?#]+)'
    _GEO_COUNTRIES = ['AU']
    _TESTS = [{
        # clip
        'url': 'https://www.9now.com.au/afl-footy-show/2016/clip-ciql02091000g0hp5oktrnytc',
        'md5': '17cf47d63ec9323e562c9957a968b565',
        'info_dict': {
            'id': '16801',
            'ext': 'mp4',
            'title': 'St. Kilda\'s Joey Montagna on the potential for a player\'s strike',
            'description': 'Is a boycott of the NAB Cup "on the table"?',
            'uploader_id': '4460760524001',
            'upload_date': '20160713',
            'timestamp': 1468421266,
        },
        'skip': 'Only available in Australia',
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
            'id': '6249614030001',
            'title': 'Episode 3',
            'ext': 'mp4',
            'season_number': 3,
            'episode_number': 3,
            'description': 'In the first elimination of the competition, teams will have 10 hours to build a world inside a snow globe.',
            'uploader_id': '4460760524001',
            'timestamp': 1619002200,
            'upload_date': '20210421',
        },
        'expected_warnings': ['Ignoring subtitle tracks'],
        'params':{
            'skip_download': True,
        }
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/4460760524001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        page_data = self._parse_json(self._search_regex(
            r'window\.__data\s*=\s*({.*?});', webpage,
            'page data', default='{}'), display_id, fatal=False)
        if not page_data:
            page_data = self._parse_json(self._parse_json(self._search_regex(
                r'window\.__data\s*=\s*JSON\.parse\s*\(\s*(".+?")\s*\)\s*;',
                webpage, 'page data'), display_id), display_id)

        for kind in ('episode', 'clip'):
            current_key = page_data.get(kind, {}).get(
                'current%sKey' % kind.capitalize())
            if not current_key:
                continue
            cache = page_data.get(kind, {}).get('%sCache' % kind, {})
            if not cache:
                continue
            common_data = {
                'episode': (cache.get(current_key) or list(cache.values())[0])[kind],
                'season': (cache.get(current_key) or list(cache.values())[0]).get('season', None)
            }
            break
        else:
            raise ExtractorError('Unable to find video data')

        if not self.get_param('allow_unplayable_formats') and try_get(common_data, lambda x: x['episode']['video']['drm'], bool):
            self.report_drm(display_id)
        brightcove_id = try_get(
            common_data, lambda x: x['episode']['video']['brightcoveId'], compat_str) or 'ref:%s' % common_data['episode']['video']['referenceId']
        video_id = str_or_none(try_get(common_data, lambda x: x['episode']['video']['id'])) or brightcove_id

        title = try_get(common_data, lambda x: x['episode']['name'], compat_str)
        season_number = try_get(common_data, lambda x: x['season']['seasonNumber'], int)
        episode_number = try_get(common_data, lambda x: x['episode']['episodeNumber'], int)
        timestamp = unified_timestamp(try_get(common_data, lambda x: x['episode']['airDate'], compat_str))
        release_date = unified_strdate(try_get(common_data, lambda x: x['episode']['availability'], compat_str))
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
            'description': try_get(common_data, lambda x: x['episode']['description'], compat_str),
            'duration': float_or_none(try_get(common_data, lambda x: x['episode']['video']['duration'], float), 1000),
            'thumbnails': thumbnails,
            'ie_key': 'BrightcoveNew',
            'season_number': season_number,
            'episode_number': episode_number,
            'timestamp': timestamp,
            'release_date': release_date,
        }

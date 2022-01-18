# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    remove_start,
    smuggle_url,
    traverse_obj,
)


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?P<path>(?:corner|episode|feature)/(?P<id>f?\d+))'
    # videos are only available for 7 days
    _TESTS = [{
        'url': 'https://tver.jp/corner/f0062178',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/feature/f0062413',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/episode/79622438',
        'only_matching': True,
    }, {
        # subtitle = ' '
        'url': 'https://tver.jp/corner/f0068870',
        'only_matching': True,
    }]
    _TOKEN = None
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_initialize(self):
        self._TOKEN = self._download_json(
            'https://tver.jp/api/access_token.php', None)['token']

    def _real_extract(self, url):
        path, video_id = self._match_valid_url(url).groups()
        api_response = self._download_json(
            'https://api.tver.jp/v4/' + path, video_id,
            query={'token': self._TOKEN})
        p_id = traverse_obj(api_response, ('main', 'publisher_id'))
        if not p_id:
            error_msg, expected = traverse_obj(api_response, ('episode', 0, 'textbar', 0, ('text', 'longer')), get_all=False), True
            if not error_msg:
                error_msg, expected = 'Failed to extract publisher ID', False
            raise ExtractorError(error_msg, expected=expected)
        service = remove_start(traverse_obj(api_response, ('main', 'service')), 'ts_')

        r_id = traverse_obj(api_response, ('main', 'reference_id'))
        if service not in ('tx', 'russia2018', 'sebare2018live', 'gorin'):
            r_id = 'ref:' + r_id
        bc_url = smuggle_url(
            self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id),
            {'geo_countries': ['JP']})

        return {
            '_type': 'url_transparent',
            'description': traverse_obj(api_response, ('main', 'note', 0, 'text'), expected_type=compat_str),
            'episode_number': int_or_none(traverse_obj(api_response, ('main', 'ext', 'episode_number'), expected_type=compat_str)),
            'url': bc_url,
            'ie_key': 'BrightcoveNew',
        }

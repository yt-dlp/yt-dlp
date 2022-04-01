# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    smuggle_url,
    traverse_obj,
)


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?P<path>corner|episodes?|feature|lp|tokyo2020/video)/(?P<id>[a-zA-Z0-9]+)'
    # videos are only available for 7 days
    _TESTS = [{
        'url': 'https://tver.jp/episodes/ephss8yveb',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _PATH_MAP = {
        'episodes': 'episode',
    }

    def _real_extract(self, url):
        path, video_id = self._match_valid_url(url).groups()
        if path == 'lp':
            webpage = self._download_webpage(url, video_id)
            redirect_path = self._search_regex(r'to_href="([^"]+)', webpage, 'redirect path')
            path, video_id = self._match_valid_url(f'https://tver.jp{redirect_path}').groups()
        api_response = self._download_json(
            f'https://statics.tver.jp/content/{self._PATH_MAP.get(path, path)}/{video_id}.json', video_id,
            query={'v': '5'}, headers={
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
            })
        p_id = traverse_obj(api_response, ('video', 'accountID'))
        r_id = 'ref:' + traverse_obj(api_response, ('video', 'videoRefID'))
        bc_url = smuggle_url(
            self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id),
            {'geo_countries': ['JP']})

        return {
            '_type': 'url_transparent',
            'description': traverse_obj(api_response, 'description', expected_type=compat_str),
            'episode_number': int_or_none(traverse_obj(api_response, ('main', 'ext', 'episode_number'), expected_type=compat_str)),
            'url': bc_url,
            'ie_key': 'BrightcoveNew',
        }

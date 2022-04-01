# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    smuggle_url,
    str_or_none,
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

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id,
            query={'v': '5'}, headers={
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
            })
        p_id = traverse_obj(video_info, ('video', 'accountID'))
        r_id = 'ref:' + traverse_obj(video_info, ('video', 'videoRefID'))
        bc_url = smuggle_url(
            self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id),
            {'geo_countries': ['JP']})

        return {
            '_type': 'url_transparent',
            'title': str_or_none(video_info.get('title')),
            'description': str_or_none(video_info.get('description')),
            'url': bc_url,
            'ie_key': 'BrightcoveNew',
        }

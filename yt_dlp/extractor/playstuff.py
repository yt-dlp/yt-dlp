from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    smuggle_url,
    try_get,
)


class PlayStuffIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?play\.stuff\.co\.nz/details/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://play.stuff.co.nz/details/608778ac1de1c4001a3fa09a',
        'md5': 'c82d3669e5247c64bc382577843e5bd0',
        'info_dict': {
            'id': '6250584958001',
            'ext': 'mp4',
            'title': 'Episode 1: Rotorua/Mt Maunganui/Tauranga',
            'description': 'md5:c154bafb9f0dd02d01fd4100fb1c1913',
            'uploader_id': '6005208634001',
            'timestamp': 1619491027,
            'upload_date': '20210427',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        # geo restricted, bypassable
        'url': 'https://play.stuff.co.nz/details/_6155660351001',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        state = self._parse_json(
            self._search_regex(
                r'__INITIAL_STATE__\s*=\s*({.+?})\s*;', webpage, 'state'),
            video_id)

        account_id = try_get(
            state, lambda x: x['configurations']['accountId'],
            compat_str) or '6005208634001'
        player_id = try_get(
            state, lambda x: x['configurations']['playerId'],
            compat_str) or 'default'

        entries = []
        for item_id, video in state['items'].items():
            if not isinstance(video, dict):
                continue
            asset_id = try_get(
                video, lambda x: x['content']['attributes']['assetId'],
                compat_str)
            if not asset_id:
                continue
            entries.append(self.url_result(
                smuggle_url(
                    self.BRIGHTCOVE_URL_TEMPLATE % (account_id, player_id, asset_id),
                    {'geo_countries': ['NZ']}),
                'BrightcoveNew', video_id))

        return self.playlist_result(entries, video_id)

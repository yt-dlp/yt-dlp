# coding: utf-8
import re

from .common import InfoExtractor

from ..utils import urljoin


class AFLWomensPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?womens\.afl/(?P<id>match-(?:replays|highlights)|video/[a-z0-9-]+)$'
    _TESTS = [{
        'url': 'https://www.womens.afl/match-replays',
        'playlist_mincount': 3,
        'info_dict': {
            'id': 'match-replays',
            'title': 'Match Replays',
            'entries': [{
                'url': 'https://www.womens.afl/video/86436/aflw-match-replay-west-coast-v-richmond',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86276/r7-carlton-v-st-kilda',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86190/aflw-match-replay-gws-v-adelaide',
                '_type': 'url'
            }],
        },
    }, {
        'url': 'https://www.womens.afl/video/all-video',
        'playlist_mincount': 3,
        'info_dict': {
            'id': 'video/all-video',
            'title': 'Latest Videos',
            'entries': [{
                'url': 'https://www.womens.afl/video/86562/aflw-match-highlights-north-melbourne-v-collingwood',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86584/aflw-full-post-match-kangaroos',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86582/aflw-full-post-match-magpies',
                '_type': 'url'
            }],
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        title = self._html_search_regex(r'<h1 class="widget-header__title">(.+?)</h1>', webpage, 'title')

        entries = [
            {
                '_type': 'url',
                'url': urljoin(url, path)
            } for path in re.findall(r'<a\b(?=[^>]* class="[^"]*(?<=[" ])media-thumbnail__link[" ])(?=[^>]* href="([^"]*))', webpage)
        ]

        return self.playlist_result(entries, playlist_id, title)

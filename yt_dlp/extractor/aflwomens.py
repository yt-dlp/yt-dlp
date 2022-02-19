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
                'url': 'https://www.womens.afl/video/86276/r7-carlton-v-st-kilda',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86190/aflw-match-replay-gws-v-adelaide',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/85970/aflw-match-replay-western-bulldogs-v-geelong',
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
                'url': 'https://www.womens.afl/video/86438/aflw-mini-match-west-coast-v-richmond',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86434/aflw-full-post-match-eagles',
                '_type': 'url'
            }, {
                'url': 'https://www.womens.afl/video/86424/aflw-full-post-match-tigers',
                '_type': 'url'
            }],
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        title = self._html_search_regex(r'<h1 class="widget-header__title">(.+?)</h1>', webpage, 'title')

        entries = []

        if webpage:
            for path in re.findall(r'<a\b(?=[^>]* class="[^"]*(?<=[" ])media-thumbnail__link[" ])(?=[^>]* href="([^"]*))', webpage):
                video_url = urljoin(url, path)

                entries.append({
                    '_type': 'url',
                    'url': video_url
                })

        return self.playlist_result(entries, playlist_id, title)

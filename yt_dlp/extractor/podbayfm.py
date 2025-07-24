from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    clean_html,
    int_or_none,
    jwt_decode_hs256,
    url_or_none,
)
from ..utils.traversal import traverse_obj


def result_from_props(props):
    return {
        **traverse_obj(props, {
            'id': ('_id', {str}),
            'title': ('title', {str}),
            'url': ('mediaURL', {url_or_none}),
            'description': ('description', {clean_html}),
            'thumbnail': ('image', {jwt_decode_hs256}, 'url', {url_or_none}),
            'timestamp': ('timestamp', {int_or_none}),
            'duration': ('duration', {int_or_none}),
        }),
        'ext': 'mp3',
        'vcodec': 'none',
    }


class PodbayFMIE(InfoExtractor):
    _VALID_URL = r'https?://podbay\.fm/p/[^/?#]+/e/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podbay.fm/p/behind-the-bastards/e/1647338400',
        'md5': '895ac8505de349515f5ee8a4a3195c93',
        'info_dict': {
            'id': '62306451f4a48e58d0c4d6a8',
            'title': 'Part One: Kissinger',
            'ext': 'mp3',
            'description': r're:^We begin our epic six part series on Henry Kissinger.+',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1647338400,
            'duration': 5001,
            'upload_date': '20220315',
        },
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        data = self._search_nextjs_data(webpage, episode_id)
        return result_from_props(data['props']['pageProps']['episode'])


class PodbayFMChannelIE(InfoExtractor):
    _VALID_URL = r'https?://podbay\.fm/p/(?P<id>[^/?#]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://podbay.fm/p/behind-the-bastards',
        'info_dict': {
            'id': 'behind-the-bastards',
            'title': 'Behind the Bastards',
        },
        'playlist_mincount': 21,
    }]
    _PAGE_SIZE = 10

    def _fetch_page(self, channel_id, pagenum):
        return self._download_json(
            f'https://podbay.fm/api/podcast?reverse=true&page={pagenum}&slug={channel_id}',
            f'Downloading channel JSON page {pagenum + 1}', channel_id)['podcast']

    @staticmethod
    def _results_from_page(channel_id, page):
        return [{
            **result_from_props(e),
            'extractor': PodbayFMIE.IE_NAME,
            'extractor_key': PodbayFMIE.ie_key(),
            # somehow they use timestamps as the episode identifier
            'webpage_url': f'https://podbay.fm/p/{channel_id}/e/{e["timestamp"]}',
        } for e in page['episodes']]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        first_page = self._fetch_page(channel_id, 0)
        entries = OnDemandPagedList(
            lambda pagenum: self._results_from_page(
                channel_id, self._fetch_page(channel_id, pagenum) if pagenum else first_page),
            self._PAGE_SIZE)

        return self.playlist_result(entries, channel_id, first_page.get('title'))

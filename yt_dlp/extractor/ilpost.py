import itertools

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class IlPostIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/podcasts/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.ilpost.it/podcasts/timbuctu/ep-323-lanno-record-della-pena-di-morte/',
        'md5': '55d88cc23bcab991639ebcbf1b4c0aa1',
        'info_dict': {
            'id': '3326553',
            'ext': 'mp3',
            'display_id': 'ep-323-lanno-record-della-pena-di-morte',
            'title': 'Ep. 323 – L’anno record della pena di morte',
            'url': 'https://static-prod.cdnilpost.com/wp-content/uploads/2025/05/25/1748196012-timbuctu_250526_v1_-16lufs.mp3',
            'timestamp': 1748235641,
            'upload_date': '20250526',
            'description': 'md5:331514a14779fab06e902160ec8c89ba',
            'duration': 751,
            'availability': 'public',
            'series_id': '233679',
            'thumbnail': 'https://www.ilpost.it/wp-content/uploads/2023/05/19/1684536738-copertina500x500.jpg',
        },
    },
        {
            'url': 'https://www.ilpost.it/podcasts/l-invasione/1-avis-akvasas-ka/',
            'md5': '43649f002d85e1c2f319bb478d479c40',
            'info_dict': {
                'id': '2972047',
                'ext': 'mp3',
                'display_id': '1-avis-akvasas-ka',
                'title': '1. Avis akvasas ka',
                'url': 'https://www.ilpost.it/wp-content/uploads/2023/12/28/1703781217-l-invasione-pt1-v6.mp3',
                'timestamp': 1703835014,
                'upload_date': '20231229',
                'description': 'md5:57d147951b522c92095f64e28570cf4a',
                'duration': 2495.0,
                'availability': 'public',
                'series_id': '235598',
                'thumbnail': 'https://www.ilpost.it/wp-content/uploads/2023/12/22/1703238848-copertina500x500.jpg',
            },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        episode = self._search_nextjs_data(
            webpage, display_id)['props']['pageProps']['data']['data']['episode']['data'][0]

        return {
            'id': str(episode['id']),
            'display_id': display_id,
            **traverse_obj(episode, {
                'series_id': ('parent', 'id', {str_or_none}),
                'title': ('title', {clean_html}),
                'description': ('content_html', {clean_html}),
                'url': ('episode_raw_url', {url_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'timestamp': ('timestamp', {int_or_none}),
                'duration': ('milliseconds', {float_or_none(scale=1000)}),
                'availability': ('access_level', {lambda v: 'public' if v == 'all' else 'subscriber_only'}),
            }),
        }


class IlPostPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/podcasts/(?P<id>[^/?#]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.ilpost.it/podcasts/basaglia-e-i-suoi/',
        'info_dict': {
            'id': '239295',
            'title': 'Basaglia e i suoi',
        },
        'playlist_mincount': 5,
    },
        {
            'url': 'https://www.ilpost.it/podcasts/morning/',
            'info_dict': {
                'id': '227474',
                'title': 'Morning',
            },
            'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        entries = []
        podcast = None

        max_hits = 10000  # found experimentally

        for page in itertools.count(1):
            data = self._download_json(
                f'https://api-prod.ilpost.it/podcast/v1/podcast/{display_id}',
                display_id,
                query={'hits': max_hits, 'pg': page},
                expected_status=500,
            )

            if podcast is None:
                podcast = traverse_obj(data, ('data', 0, 'parent'))

            if data.get('data') is None:
                break

            entries += [{
                '_type': 'url',
                'ie_key': IlPostIE.ie_key(),
                'url': episode['url'],
                **traverse_obj(episode, {
                    'episode_id': ('id', {str_or_none}),
                    'title': ('title', {clean_html}),
                    'description': ('content_html', {clean_html}),
                }),
            } for episode in traverse_obj(data, ('data', lambda _, v: url_or_none(v['url'])))]

        return self.playlist_result(entries, str_or_none(podcast.get('id')), clean_html(podcast.get('title')))

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    int_or_none,
    unescapeHTML,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class IlPostIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/podcasts/[^/]+/(?P<id>[^/?#]+)'
    _TESTS = [{
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
            'description': 'md5:54c5f12fb5b90f6c7cca6476a0802a99',
            'duration': 2495.0,
            'availability': 'public',
            'series_id': '235598',
            'thumbnail': 'https://www.ilpost.it/wp-content/uploads/2023/12/22/1703238848-copertina500x500.jpg',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        try:
            episode = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['data']['data']['episode']['data'][0]
            episode_id = episode['id']
        except KeyError:
            raise ExtractorError('Failed to extract episode')

        return {
            'id': str(episode_id),
            'display_id': display_id,
            **traverse_obj(episode, {
                'series_id': ('parent', 'id', {int_or_none}),
                'title': ('title', {unescapeHTML}),
                'description': ('content_html', {clean_html}),
                'url': ('episode_raw_url', {url_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'timestamp': ('timestamp', {int_or_none}),
                'duration': ('milliseconds', {float_or_none(scale=1000)}),
                'availability': ('access_level', {lambda v: 'public' if v == 'all' else 'subscriber_only'}),
            }),
        }


class IlPostPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/podcasts/(?P<id>[\w\-]+)[/?#]?$'
    _TESTS = [{
        'url': 'https://www.ilpost.it/podcasts/morning/',
        'info_dict': {
            'id': 'morning',
            'display_id': 'morning',
            'title': 'Morning',
            'series': 'Morning',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://www.ilpost.it/podcasts/basaglia-e-i-suoi/',
        'info_dict': {
            'id': 'basaglia-e-i-suoi',
            'display_id': 'basaglia-e-i-suoi',
            'title': 'Basaglia e i suoi',
            'series': 'Basaglia e i suoi',
        },
        'playlist_mincount': 5,
    }]

    def _real_extract(self, url):
        display_id = self._match_valid_url(url).group('id')
        data = self._download_json(f'https://api-prod.ilpost.it/podcast/v1/podcast/{display_id}?hits=20', display_id)

        try:
            podcast = data['data'][0]['parent']
        except KeyError:
            raise ExtractorError('Failed to extract series')

        entries = [{
            '_type': 'url',
            'ie_key': 'IlPost',
            'url': episode['url'],
            'episode_id': episode['id'],
            'title': unescapeHTML(episode.get('title')),
            'description': clean_html(episode.get('content_html')),
            'series': unescapeHTML(podcast.get('title')),
        } for episode in traverse_obj(data, ('data'))]

        return {
            '_type': 'playlist',
            'id': podcast.get('id'),
            'display_id': display_id,
            'title': unescapeHTML(podcast.get('title')),
            'entries': entries,
        }

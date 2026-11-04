
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj

PODCAST_API = 'https://api-prod.ilpost.it/podcast/v1/podcast/%s?hits=20'


class IlPostIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/podcasts/(?:.*?)/(?P<id>[^/?#]+)'
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
            'description': '<p>Circa tre miliardi di persone, oggi, parlano lingue che hanno un’unica antenata: dall’italiano all’inglese, passando per il farsi e l’islandese, queste lingue discendono tutte da una lingua arrivata in Europa circa cinquemila anni fa, insieme a un gruppo di persone ben preciso.<br />\nCon la loro lingua queste persone si portarono dietro anche alcuni oggetti, miti e leggende, e una certa visione della società, lasciando tracce indelebili ancora oggi.</p>\n<p>Per approfondire gli argomenti trattati nel podcast abbiamo raccolto in <a href="https://www.ilpost.it/2024/01/05/invasione-testi/?homepagePosition=3">questa pagina</a> le cose da leggere e da guardare dopo aver ascoltato le puntate.</p>\n',
            'duration': 2495.0,
            'availability': 'public',
            'series_id': '235598',
            'thumbnail': 'https://www.ilpost.it/wp-content/uploads/2023/12/22/1703238848-copertina500x500.jpg',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        endpoint_metadata = self._search_json(
            r'{"props":{"pageProps":', webpage, 'metadata', display_id)
        episode_id = endpoint_metadata['data']['data']['episode']['data'][0]['id']
        podcast_id = traverse_obj(endpoint_metadata, ('data', 'data', 'episode', 'data', 0, 'parent', 'id'))
        podcast_metadata = traverse_obj(endpoint_metadata, ('data', 'data', 'episode', 'data', 0))

        episode = podcast_metadata
        if not episode:
            raise ExtractorError('Episode could not be extracted')

        return {
            'id': str(episode_id),
            'display_id': str(display_id),
            'series_id': str(podcast_id),
            **traverse_obj(episode, {
                'title': ('title', {str}),
                'url': ('episode_raw_url', {url_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'description': ('content_html', {str}),
                'timestamp': ('timestamp', {int_or_none}),
                'duration': ('milliseconds', {float_or_none(scale=1000)}),
                'availability': ('access_level', {lambda v: 'public' if v else 'subscriber_only'}),
            }),
        }


class IlPostPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/podcasts/(?P<id>[a-zA-Z0-9\-]+)/?$'
    _TESTS = [{
        'url': 'https://www.ilpost.it/podcasts/morning/',
        'info_dict': {
            'id': 'morning',
            'display_id': 'morning',
            'title': 'Morning',
            'series': 'Morning',
            'season_number': 1,
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://www.ilpost.it/podcasts/basaglia-e-i-suoi/',
        'info_dict': {
            'id': 'basaglia-e-i-suoi',
            'display_id': 'basaglia-e-i-suoi',
            'title': 'Basaglia e i suoi',
            'series': 'Basaglia e i suoi',
            'season_number': 1,
        },
        'playlist_mincount': 5,
    }]

    def _real_extract(self, url):
        display_id = self._match_valid_url(url).group('id')
        data = self._download_json(PODCAST_API % display_id, display_id)

        entries = [{
            '_type': 'url',
            'url': episode['url'],
            'title': episode.get('title'),
            'description': episode.get('content_html'),
            'series': traverse_obj(data, ('data', 0, 'parent', 'title')),
            'season_number': 1,
            'episode_number': episode['id'],
        } for episode in traverse_obj(data, ('data'))]

        return {
            '_type': 'playlist',
            'id': display_id,
            'display_id': display_id,
            'title': traverse_obj(data, ('data', 0, 'parent', 'title')),
            'series': traverse_obj(data, ('data', 0, 'parent', 'title')),
            'entries': entries,
            'season_number': 1,
        }

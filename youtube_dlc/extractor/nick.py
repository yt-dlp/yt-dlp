# coding: utf-8
from __future__ import unicode_literals

import re

from .mtv import MTVServicesInfoExtractor
from ..utils import update_url_query


class NickIE(MTVServicesInfoExtractor):
    # None of videos on the website are still alive?
    IE_NAME = 'nick.com'
    _VALID_URL = r'https?://(?P<domain>(?:(?:www|beta)\.)?nick(?:jr)?\.com)/(?:[^/]+/)?(?:videos/clip|[^/]+/videos)/(?P<id>[^/?#.]+)'
    _FEED_URL = 'http://udat.mtvnservices.com/service1/dispatch.htm'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        'url': 'http://www.nick.com/videos/clip/alvinnn-and-the-chipmunks-112-full-episode.html',
        'playlist': [
            {
                'md5': '6e5adc1e28253bbb1b28ab05403dd4d4',
                'info_dict': {
                    'id': 'be6a17b0-412d-11e5-8ff7-0026b9414f30',
                    'ext': 'mp4',
                    'title': 'ALVINNN!!! and The Chipmunks: "Mojo Missing/Who\'s The Animal" S1',
                    'description': 'Alvin is convinced his mojo was in a cap he gave to a fan, and must find a way to get his hat back before the Chipmunks’ big concert.\nDuring a costume visit to the zoo, Alvin finds himself mistaken for the real Tasmanian devil.',

                }
            },
            {
                'md5': 'd7be441fc53a1d4882fa9508a1e5b3ce',
                'info_dict': {
                    'id': 'be6b8f96-412d-11e5-8ff7-0026b9414f30',
                    'ext': 'mp4',
                    'title': 'ALVINNN!!! and The Chipmunks: "Mojo Missing/Who\'s The Animal" S2',
                    'description': 'Alvin is convinced his mojo was in a cap he gave to a fan, and must find a way to get his hat back before the Chipmunks’ big concert.\nDuring a costume visit to the zoo, Alvin finds himself mistaken for the real Tasmanian devil.',

                }
            },
            {
                'md5': 'efffe1728a234b2b0d2f2b343dd1946f',
                'info_dict': {
                    'id': 'be6cf7e6-412d-11e5-8ff7-0026b9414f30',
                    'ext': 'mp4',
                    'title': 'ALVINNN!!! and The Chipmunks: "Mojo Missing/Who\'s The Animal" S3',
                    'description': 'Alvin is convinced his mojo was in a cap he gave to a fan, and must find a way to get his hat back before the Chipmunks’ big concert.\nDuring a costume visit to the zoo, Alvin finds himself mistaken for the real Tasmanian devil.',
                }
            },
            {
                'md5': '1ec6690733ab9f41709e274a1d5c7556',
                'info_dict': {
                    'id': 'be6e3354-412d-11e5-8ff7-0026b9414f30',
                    'ext': 'mp4',
                    'title': 'ALVINNN!!! and The Chipmunks: "Mojo Missing/Who\'s The Animal" S4',
                    'description': 'Alvin is convinced his mojo was in a cap he gave to a fan, and must find a way to get his hat back before the Chipmunks’ big concert.\nDuring a costume visit to the zoo, Alvin finds himself mistaken for the real Tasmanian devil.',
                }
            },
        ],
    }, {
        'url': 'http://www.nickjr.com/paw-patrol/videos/pups-save-a-goldrush-s3-ep302-full-episode/',
        'only_matching': True,
    }, {
        'url': 'http://beta.nick.com/nicky-ricky-dicky-and-dawn/videos/nicky-ricky-dicky-dawn-301-full-episode/',
        'only_matching': True,
    }]

    def _get_feed_query(self, uri):
        return {
            'feed': 'nick_arc_player_prime',
            'mgid': uri,
        }

    def _real_extract(self, url):
        domain, display_id = re.match(self._VALID_URL, url).groups()
        video_data = self._download_json(
            'http://%s/data/video.endLevel.json' % domain,
            display_id, query={
                'urlKey': display_id,
            })
        return self._get_videos_info(video_data['player'] + video_data['id'])


class NickBrIE(MTVServicesInfoExtractor):
    IE_NAME = 'nickelodeon:br'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?P<domain>(?:www\.)?nickjr|mundonick\.uol)\.com\.br|
                            (?:www\.)?nickjr\.[a-z]{2}|
                            (?:www\.)?nickelodeonjunior\.fr
                        )
                        /(?:programas/)?[^/]+/videos/(?:episodios/)?(?P<id>[^/?\#.]+)
                    '''
    _TESTS = [{
        'url': 'http://www.nickjr.com.br/patrulha-canina/videos/210-labirinto-de-pipoca/',
        'only_matching': True,
    }, {
        'url': 'http://mundonick.uol.com.br/programas/the-loud-house/videos/muitas-irmas/7ljo9j',
        'only_matching': True,
    }, {
        'url': 'http://www.nickjr.nl/paw-patrol/videos/311-ge-wol-dig-om-terug-te-zijn/',
        'only_matching': True,
    }, {
        'url': 'http://www.nickjr.de/blaze-und-die-monster-maschinen/videos/f6caaf8f-e4e8-4cc1-b489-9380d6dcd059/',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeonjunior.fr/paw-patrol-la-pat-patrouille/videos/episode-401-entier-paw-patrol/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, display_id = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, display_id)
        uri = self._search_regex(
            r'data-(?:contenturi|mgid)="([^"]+)', webpage, 'mgid')
        video_id = self._id_from_uri(uri)
        config = self._download_json(
            'http://media.mtvnservices.com/pmt/e1/access/index.html',
            video_id, query={
                'uri': uri,
                'configtype': 'edge',
            }, headers={
                'Referer': url,
            })
        info_url = self._remove_template_parameter(config['feedWithQueryParams'])
        if info_url == 'None':
            if domain.startswith('www.'):
                domain = domain[4:]
            content_domain = {
                'mundonick.uol': 'mundonick.com.br',
                'nickjr': 'br.nickelodeonjunior.tv',
            }[domain]
            query = {
                'mgid': uri,
                'imageEp': content_domain,
                'arcEp': content_domain,
            }
            if domain == 'nickjr.com.br':
                query['ep'] = 'c4b16088'
            info_url = update_url_query(
                'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed', query)
        return self._get_videos_info_from_url(info_url, video_id)


class NickDeIE(MTVServicesInfoExtractor):
    IE_NAME = 'nick.de'
    _VALID_URL = r'https?://(?:www\.)?(?P<host>nick\.(?:de|com\.pl|ch)|nickelodeon\.(?:nl|be|at|dk|no|se))/[^/]+/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.nick.de/playlist/3773-top-videos/videos/episode/17306-zu-wasser-und-zu-land-rauchende-erdnusse',
        'only_matching': True,
    }, {
        'url': 'http://www.nick.de/shows/342-icarly',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.nl/shows/474-spongebob/videos/17403-een-kijkje-in-de-keuken-met-sandy-van-binnenuit',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.at/playlist/3773-top-videos/videos/episode/77993-das-letzte-gefecht',
        'only_matching': True,
    }, {
        'url': 'http://www.nick.com.pl/seriale/474-spongebob-kanciastoporty/wideo/17412-teatr-to-jest-to-rodeo-oszolom',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.no/program/2626-bulderhuset/videoer/90947-femteklasse-veronica-vs-vanzilla',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.dk/serier/2626-hojs-hus/videoer/761-tissepause',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.se/serier/2626-lugn-i-stormen/videos/998-',
        'only_matching': True,
    }, {
        'url': 'http://www.nick.ch/shows/2304-adventure-time-abenteuerzeit-mit-finn-und-jake',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.be/afspeellijst/4530-top-videos/videos/episode/73917-inval-broodschapper-lariekoek-arie',
        'only_matching': True,
    }]

    def _get_feed_url(self, uri, url=None):
        video_id = self._id_from_uri(uri)
        config = self._download_json(
            'http://media.mtvnservices.com/pmt/e1/access/index.html?uri=%s&configtype=edge&ref=%s' % (uri, url), video_id)
        return self._remove_template_parameter(config['feedWithQueryParams'])


class NickNightIE(NickDeIE):
    IE_NAME = 'nicknight'
    _VALID_URL = r'https?://(?:www\.)(?P<host>nicknight\.(?:de|at|tv))/(?:playlist|shows)/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.nicknight.at/shows/977-awkward/videos/85987-nimmer-beste-freunde',
        'only_matching': True,
    }, {
        'url': 'http://www.nicknight.at/shows/977-awkward',
        'only_matching': True,
    }, {
        'url': 'http://www.nicknight.at/shows/1900-faking-it',
        'only_matching': True,
    }]

    def _extract_mrss_url(self, webpage, *args):
        return self._search_regex(
            r'mrss\s*:\s*(["\'])(?P<url>http.+?)\1', webpage,
            'mrss url', group='url')


class NickRuIE(MTVServicesInfoExtractor):
    IE_NAME = 'nickelodeonru'
    _VALID_URL = r'https?://(?:www\.)nickelodeon\.(?:ru|fr|es|pt|ro|hu|com\.tr)/[^/]+/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.nickelodeon.ru/shows/henrydanger/videos/episodes/3-sezon-15-seriya-licenziya-na-polyot/pmomfb#playlist/7airc6',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.ru/videos/smotri-na-nickelodeon-v-iyule/g9hvh7',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.fr/programmes/bob-l-eponge/videos/le-marathon-de-booh-kini-bottom-mardi-31-octobre/nfn7z0',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.es/videos/nickelodeon-consejos-tortitas/f7w7xy',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.pt/series/spongebob-squarepants/videos/a-bolha-de-tinta-gigante/xutq1b',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.ro/emisiuni/shimmer-si-shine/video/nahal-din-bomboane/uw5u2k',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.hu/musorok/spongyabob-kockanadrag/videok/episodes/buborekfujas-az-elszakadt-nadrag/q57iob#playlist/k6te4y',
        'only_matching': True,
    }, {
        'url': 'http://www.nickelodeon.com.tr/programlar/sunger-bob/videolar/kayip-yatak/mgqbjy',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        mgid = self._extract_mgid(webpage, url)
        return self.url_result('http://media.mtvnservices.com/embed/%s' % mgid)

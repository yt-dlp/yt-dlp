# coding: utf-8
from __future__ import unicode_literals

import re

from .mtv import MTVServicesInfoExtractor
from ..utils import update_url_query


class NickIE(MTVServicesInfoExtractor):
    IE_NAME = 'nick.com'
    _VALID_URL = r'https?://(?P<domain>(?:www\.)?nick(?:jr)?\.com)/(?:[^/]+/)?(?P<type>videos/clip|[^/]+/videos|episodes/[^/]+)/(?P<id>[^/?#.]+)'
    _FEED_URL = 'http://udat.mtvnservices.com/service1/dispatch.htm'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        'url': 'https://www.nick.com/episodes/sq47rw/spongebob-squarepants-a-place-for-pets-lockdown-for-love-season-13-ep-1',
        'info_dict': {
            'description': 'md5:0650a9eb88955609d5c1d1c79292e234',
            'title': 'A Place for Pets/Lockdown for Love',
        },
        'playlist': [
            {
                'md5': 'cb8a2afeafb7ae154aca5a64815ec9d6',
                'info_dict': {
                    'id': '85ee8177-d6ce-48f8-9eee-a65364f8a6df',
                    'ext': 'mp4',
                    'title': 'SpongeBob SquarePants: "A Place for Pets/Lockdown for Love" S1',
                    'description': 'A Place for Pets/Lockdown for Love: When customers bring pets into the Krusty Krab, Mr. Krabs realizes pets are more profitable than owners. Plankton ruins another date with Karen, so she puts the Chum Bucket on lockdown until he proves his affection.',

                }
            },
            {
                'md5': '839a04f49900a1fcbf517020d94e0737',
                'info_dict': {
                    'id': '2e2a9960-8fd4-411d-868b-28eb1beb7fae',
                    'ext': 'mp4',
                    'title': 'SpongeBob SquarePants: "A Place for Pets/Lockdown for Love" S2',
                    'description': 'A Place for Pets/Lockdown for Love: When customers bring pets into the Krusty Krab, Mr. Krabs realizes pets are more profitable than owners. Plankton ruins another date with Karen, so she puts the Chum Bucket on lockdown until he proves his affection.',

                }
            },
            {
                'md5': 'f1145699f199770e2919ee8646955d46',
                'info_dict': {
                    'id': 'dc91c304-6876-40f7-84a6-7aece7baa9d0',
                    'ext': 'mp4',
                    'title': 'SpongeBob SquarePants: "A Place for Pets/Lockdown for Love" S3',
                    'description': 'A Place for Pets/Lockdown for Love: When customers bring pets into the Krusty Krab, Mr. Krabs realizes pets are more profitable than owners. Plankton ruins another date with Karen, so she puts the Chum Bucket on lockdown until he proves his affection.',

                }
            },
            {
                'md5': 'd463116875aee2585ee58de3b12caebd',
                'info_dict': {
                    'id': '5d929486-cf4c-42a1-889a-6e0d183a101a',
                    'ext': 'mp4',
                    'title': 'SpongeBob SquarePants: "A Place for Pets/Lockdown for Love" S4',
                    'description': 'A Place for Pets/Lockdown for Love: When customers bring pets into the Krusty Krab, Mr. Krabs realizes pets are more profitable than owners. Plankton ruins another date with Karen, so she puts the Chum Bucket on lockdown until he proves his affection.',

                }
            },
        ],
    }, {
        'url': 'http://www.nickjr.com/blues-clues-and-you/videos/blues-clues-and-you-original-209-imagination-station/',
        'info_dict': {
            'id': '31631529-2fc5-430b-b2ef-6a74b4609abd',
            'ext': 'mp4',
            'description': 'md5:9d65a66df38e02254852794b2809d1cf',
            'title': 'Blue\'s Imagination Station',
        },
    }]

    def _get_feed_query(self, uri):
        return {
            'feed': 'nick_arc_player_prime',
            'mgid': uri,
        }

    def _extract_mgid(self, webpage):
        mgid = self._search_regex(r'"media":{"video":{"config":{"uri":"(mgid:.*?)"', webpage, 'mgid', default=None)
        return mgid

    def _real_extract(self, url):
        domain, video_type, display_id = re.match(self._VALID_URL, url).groups()
        if video_type.startswith("episodes"):
            return super()._real_extract(url)
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

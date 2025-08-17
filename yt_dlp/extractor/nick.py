from .mtv import MTVServicesBaseIE


class NickIE(MTVServicesBaseIE):
    IE_NAME = 'nick.com'
    _VALID_URL = r'https?://(?:www\.)?nick\.com/(?:video-clips|episodes)/(?P<id>[\da-z]{6})'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        'url': 'https://www.nick.com/episodes/u3smw8/wylde-pak-best-summer-ever-season-1-ep-1',
        'info_dict': {
            'id': 'eb9d4db0-274a-11ef-a913-0e37995d42c9',
            'ext': 'mp4',
            'display_id': 'u3smw8',
            'title': 'Best Summer Ever?',
            'description': 'md5:c737a0ade3fbc09d569c3b3d029a7792',
            'channel': 'Nickelodeon',
            'duration': 1296.0,
            'thumbnail': r're:https://assets\.nick\.com/uri/mgid:arc:imageassetref:',
            'series': 'Wylde Pak',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1746100800,
            'upload_date': '20250501',
            'release_timestamp': 1746100800,
            'release_date': '20250501',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nick.com/video-clips/0p4706/spongebob-squarepants-spongebob-loving-the-krusty-krab-for-7-minutes',
        'info_dict': {
            'id': '4aac2228-5295-4076-b986-159513cf4ce4',
            'ext': 'mp4',
            'display_id': '0p4706',
            'title': 'SpongeBob Loving the Krusty Krab for 7 Minutes!',
            'description': 'md5:72bf59babdf4e6d642187502864e111d',
            'duration': 423.423,
            'thumbnail': r're:https://assets\.nick\.com/uri/mgid:arc:imageassetref:',
            'series': 'SpongeBob SquarePants',
            'season': 'Season 0',
            'season_number': 0,
            'episode': 'Episode 0',
            'episode_number': 0,
            'timestamp': 1663819200,
            'upload_date': '20220922',
        },
        'params': {'skip_download': 'm3u8'},
    }]


class NickBrIE(MTVServicesBaseIE):
    IE_NAME = 'nickelodeon:br'
    _WORKING = False
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


class NickDeIE(MTVServicesBaseIE):
    IE_NAME = 'nick.de'
    _WORKING = False
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


class NickRuIE(MTVServicesBaseIE):
    IE_NAME = 'nickelodeonru'
    _WORKING = False
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

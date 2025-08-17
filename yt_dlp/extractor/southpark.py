from .mtv import MTVServicesBaseIE


class SouthParkIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.cc.com'
    _VALID_URL = r'https?://(?:www\.)?southpark(?:\.cc|studios)\.com/(?:video-clips|episodes|collections)/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://southpark.cc.com/video-clips/d7wr06/south-park-you-all-agreed-to-counseling',
        'info_dict': {
            'id': '31929ad5-8269-11eb-8774-70df2f866ace',
            'ext': 'mp4',
            'display_id': 'd7wr06',
            'title': 'You All Agreed to Counseling',
            'description': 'md5:01f78fb306c7042f3f05f3c78edfc212',
            'duration': 134.552,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 24',
            'season_number': 24,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1615352400,
            'upload_date': '20210310',
            'release_timestamp': 1615352400,
            'release_date': '20210310',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://southpark.cc.com/episodes/940f8z/south-park-cartman-gets-an-anal-probe-season-1-ep-1',
        'info_dict': {
            'id': '5fb8887e-ecfd-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'display_id': '940f8z',
            'title': 'Cartman Gets An Anal Probe',
            'description': 'md5:964e1968c468545752feef102b140300',
            'channel': 'Comedy Central',
            'duration': 1319.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 871473600,
            'upload_date': '19970813',
            'release_timestamp': 871473600,
            'release_date': '19970813',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://southpark.cc.com/collections/dejukt/south-park-best-of-mr-mackey/tphx9j',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.com/episodes/h4o269/south-park-stunning-and-brave-season-19-ep-1',
        'only_matching': True,
    }]


class SouthParkEsIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.cc.com:español'
    _VALID_URL = r'https?://(?:www\.)?southpark\.cc\.com/es/episodios/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://southpark.cc.com/es/episodios/er4a32/south-park-aumento-de-peso-4000-temporada-1-ep-2',
        'info_dict': {
            'id': '5fb94f0c-ecfd-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'display_id': 'er4a32',
            'title': 'Aumento de peso 4000',
            'description': 'md5:a939b4819ea74c245a0cde180de418c0',
            'channel': 'Comedy Central',
            'duration': 1320.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 872078400,
            'upload_date': '19970820',
            'release_timestamp': 872078400,
            'release_date': '19970820',
        },
        'params': {'skip_download': 'm3u8'},
    }]


class SouthParkDeIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.de'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.de/(?:(en/(videoclip|collections|episodes|video-clips))|(videoclip|collections|folgen))/(?P<id>(?P<unique_id>.+?)/.+?)(?:\?|#|$))'
    _GEO_COUNTRIES = ['DE']
    _TESTS = [{
        'url': 'https://www.southpark.de/videoclip/rsribv/south-park-rueckzug-zum-gummibonbon-wald',
        'only_matching': True,
    }, {
        'url': 'https://www.southpark.de/folgen/jiru42/south-park-verkabelung-staffel-23-ep-9',
        'only_matching': True,
    }, {
        'url': 'https://www.southpark.de/collections/zzno5a/south-park-good-eats/7q26gp',
        'only_matching': True,
    }, {
        # clip
        'url': 'https://www.southpark.de/en/video-clips/ct46op/south-park-tooth-fairy-cartman',
        'info_dict': {
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Tooth Fairy Cartman',
            'description': 'md5:db02e23818b4dc9cb5f0c5a7e8833a68',
        },
    }, {
        # episode
        'url': 'https://www.southpark.de/en/episodes/yy0vjs/south-park-the-pandemic-special-season-24-ep-1',
        'info_dict': {
            'id': 'f5fbd823-04bc-11eb-9b1b-0e40cf2fc285',
            'ext': 'mp4',
            'title': 'South Park',
            'description': 'md5:ae0d875eff169dcbed16b21531857ac1',
        },
    }, {
        # clip
        'url': 'https://www.southpark.de/videoclip/ct46op/south-park-zahnfee-cartman',
        'info_dict': {
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Zahnfee Cartman',
            'description': 'md5:b917eec991d388811d911fd1377671ac',
        },
    }, {
        # episode
        'url': 'https://www.southpark.de/folgen/242csn/south-park-her-mit-dem-hirn-staffel-1-ep-7',
        'info_dict': {
            'id': '607115f3-496f-40c3-8647-2b0bcff486c0',
            'ext': 'mp4',
            'title': 'md5:South Park | Pink Eye | E 0107 | HDSS0107X deu | Version: 634312 | Comedy Central S1',
        },
    }]


class SouthParkLatIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.lat'
    _VALID_URL = r'https?://(?:www\.)?southpark\.lat/(?:en/)?(?:video-?clips?|collections|episod(?:e|io)s)/(?P<id>[^/?#&]+)'
    _GEO_COUNTRIES = ['BR']
    _TESTS = [{
        'url': 'https://www.southpark.lat/en/video-clips/ct46op/south-park-tooth-fairy-cartman',
        'only_matching': True,
    }, {
        'url': 'https://www.southpark.lat/episodios/9h0qbg/south-park-orgia-gatuna-temporada-3-ep-7',
        'only_matching': True,
    }, {
        'url': 'https://www.southpark.lat/en/collections/29ve08/south-park-heating-up/lydbrc',
        'only_matching': True,
    }, {
        # clip
        'url': 'https://www.southpark.lat/en/video-clips/ct46op/south-park-tooth-fairy-cartman',
        'info_dict': {
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Tooth Fairy Cartman',
            'description': 'md5:db02e23818b4dc9cb5f0c5a7e8833a68',
        },
    }, {
        # episode
        'url': 'https://www.southpark.lat/episodios/9h0qbg/south-park-orgia-gatuna-temporada-3-ep-7',
        'info_dict': {
            'id': 'f5fbd823-04bc-11eb-9b1b-0e40cf2fc285',
            'ext': 'mp4',
            'title': 'South Park',
            'description': 'md5:ae0d875eff169dcbed16b21531857ac1',
        },
    }]


class SouthParkNlIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.nl'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.nl/(?:clips|(?:full-)?episodes|collections)/(?P<id>.+?)(\?|#|$))'
    _GEO_COUNTRIES = ['NL']
    _TESTS = [{
        'url': 'http://www.southpark.nl/full-episodes/s18e06-freemium-isnt-free',
        'info_dict': {
            'title': 'Freemium Isn\'t Free',
            'description': 'Stan is addicted to the new Terrance and Phillip mobile game.',
        },
        'playlist_mincount': 3,
    }]


class SouthParkDkIE(MTVServicesBaseIE):
    IE_NAME = 'southparkstudios.dk'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southparkstudios\.(?:dk|nu)/(?:clips|full-episodes|collections)/(?P<id>.+?)(\?|#|$))'
    _GEO_COUNTRIES = ['DK']
    _TESTS = [{
        'url': 'http://www.southparkstudios.dk/full-episodes/s18e07-grounded-vindaloop',
        'info_dict': {
            'title': 'Grounded Vindaloop',
            'description': 'Butters is convinced he\'s living in a virtual reality.',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'http://www.southparkstudios.dk/collections/2476/superhero-showdown/1',
        'only_matching': True,
    }, {
        'url': 'http://www.southparkstudios.nu/collections/2476/superhero-showdown/1',
        'only_matching': True,
    }]

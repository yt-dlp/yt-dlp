from .mtv import MTVServicesInfoExtractor


class SouthParkIE(MTVServicesInfoExtractor):
    IE_NAME = 'southpark.cc.com'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark(?:\.cc|studios)\.com/((?:video-)?clips|(?:full-)?episodes|collections)/(?P<id>.+?)(\?|#|$))'

    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'

    _TESTS = [{
        'url': 'https://southpark.cc.com/video-clips/d7wr06/south-park-you-all-agreed-to-counseling',
        'info_dict': {
            'ext': 'mp4',
            'title': 'You All Agreed to Counseling',
            'description': 'Kenny, Cartman, Stan, and Kyle visit Mr. Mackey and ask for his help getting Mrs. Nelson to come back. Mr. Mackey reveals the only way to get things back to normal is to get the teachers vaccinated.',
            'timestamp': 1615352400,
            'upload_date': '20210310',
        },
    }, {
        'url': 'http://southpark.cc.com/collections/7758/fan-favorites/1',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.com/episodes/h4o269/south-park-stunning-and-brave-season-19-ep-1',
        'only_matching': True,
    }]

    def _get_feed_query(self, uri):
        return {
            'accountOverride': 'intl.mtvi.com',
            'arcEp': 'shared.southpark.global',
            'ep': '90877963',
            'imageEp': 'shared.southpark.global',
            'mgid': uri,
        }


class SouthParkEsIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.cc.com:español'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.cc\.com/es/episodios/(?P<id>.+?)(\?|#|$))'
    _LANG = 'es'

    _TESTS = [{
        'url': 'http://southpark.cc.com/es/episodios/s01e01-cartman-consigue-una-sonda-anal#source=351c1323-0b96-402d-a8b9-40d01b2e9bde&position=1&sort=!airdate',
        'info_dict': {
            'title': 'Cartman Consigue Una Sonda Anal',
            'description': 'Cartman Consigue Una Sonda Anal',
        },
        'playlist_count': 4,
        'skip': 'Geo-restricted',
    }]


class SouthParkDeIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.de'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.de/(?:(en/(videoclip|collections|episodes|video-clips))|(videoclip|collections|folgen))/(?P<id>(?P<unique_id>.+?)/.+?)(?:\?|#|$))'
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

    def _get_feed_url(self, uri, url=None):
        video_id = self._id_from_uri(uri)
        config = self._download_json(
            f'http://media.mtvnservices.com/pmt/e1/access/index.html?uri={uri}&configtype=edge&ref={url}', video_id)
        return self._remove_template_parameter(config['feedWithQueryParams'])

    def _get_feed_query(self, uri):
        return


class SouthParkLatIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.lat'
    _VALID_URL = r'https?://(?:www\.)?southpark\.lat/(?:en/)?(?:video-?clips?|collections|episod(?:e|io)s)/(?P<id>[^/?#&]+)'
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

    def _get_feed_url(self, uri, url=None):
        video_id = self._id_from_uri(uri)
        config = self._download_json(
            f'http://media.mtvnservices.com/pmt/e1/access/index.html?uri={uri}&configtype=edge&ref={url}',
            video_id)
        return self._remove_template_parameter(config['feedWithQueryParams'])

    def _get_feed_query(self, uri):
        return


class SouthParkNlIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.nl'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.nl/(?:clips|(?:full-)?episodes|collections)/(?P<id>.+?)(\?|#|$))'
    _FEED_URL = 'http://www.southpark.nl/feeds/video-player/mrss/'

    _TESTS = [{
        'url': 'http://www.southpark.nl/full-episodes/s18e06-freemium-isnt-free',
        'info_dict': {
            'title': 'Freemium Isn\'t Free',
            'description': 'Stan is addicted to the new Terrance and Phillip mobile game.',
        },
        'playlist_mincount': 3,
    }]


class SouthParkDkIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southparkstudios.dk'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southparkstudios\.(?:dk|nu)/(?:clips|full-episodes|collections)/(?P<id>.+?)(\?|#|$))'
    _FEED_URL = 'http://www.southparkstudios.dk/feeds/video-player/mrss/'

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

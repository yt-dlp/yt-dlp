import json
import uuid

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    int_or_none,
    remove_start,
    strip_or_none,
    try_get,
    unified_timestamp,
)


class DPlayBaseIE(InfoExtractor):
    _PATH_REGEX = r'/(?P<id>[^/]+/[^/?#]+)'
    _auth_token_cache = {}

    def _get_auth(self, disco_base, display_id, realm, needs_device_id=True):
        key = (disco_base, realm)
        st = self._get_cookies(disco_base).get('st')
        token = (st and st.value) or self._auth_token_cache.get(key)

        if not token:
            query = {'realm': realm}
            if needs_device_id:
                query['deviceId'] = uuid.uuid4().hex
            token = self._download_json(
                disco_base + 'token', display_id, 'Downloading token',
                query=query)['data']['attributes']['token']

            # Save cache only if cookies are not being set
            if not self._get_cookies(disco_base).get('st'):
                self._auth_token_cache[key] = token

        return f'Bearer {token}'

    def _process_errors(self, e, geo_countries):
        info = self._parse_json(e.cause.read().decode('utf-8'), None)
        error = info['errors'][0]
        error_code = error.get('code')
        if error_code == 'access.denied.geoblocked':
            self.raise_geo_restricted(countries=geo_countries)
        elif error_code in ('access.denied.missingpackage', 'invalid.token'):
            raise ExtractorError(
                'This video is only available for registered users. You may want to use --cookies.', expected=True)
        raise ExtractorError(info['errors'][0]['detail'], expected=True)

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers['Authorization'] = self._get_auth(disco_base, display_id, realm, False)

    def _download_video_playback_info(self, disco_base, video_id, headers):
        streaming = self._download_json(
            disco_base + 'playback/videoPlaybackInfo/' + video_id,
            video_id, headers=headers)['data']['attributes']['streaming']
        streaming_list = []
        for format_id, format_dict in streaming.items():
            streaming_list.append({
                'type': format_id,
                'url': format_dict.get('url'),
            })
        return streaming_list

    def _get_disco_api_info(self, url, display_id, disco_host, realm, country, domain=''):
        country = self.get_param('geo_bypass_country') or country
        geo_countries = [country.upper()]
        self._initialize_geo_bypass({
            'countries': geo_countries,
        })
        disco_base = 'https://%s/' % disco_host
        headers = {
            'Referer': url,
        }
        self._update_disco_api_headers(headers, disco_base, display_id, realm)
        try:
            video = self._download_json(
                disco_base + 'content/videos/' + display_id, display_id,
                headers=headers, query={
                    'fields[channel]': 'name',
                    'fields[image]': 'height,src,width',
                    'fields[show]': 'name',
                    'fields[tag]': 'name',
                    'fields[video]': 'description,episodeNumber,name,publishStart,seasonNumber,videoDuration',
                    'include': 'images,primaryChannel,show,tags'
                })
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                self._process_errors(e, geo_countries)
            raise
        video_id = video['data']['id']
        info = video['data']['attributes']
        title = info['name'].strip()
        formats = []
        subtitles = {}
        try:
            streaming = self._download_video_playback_info(
                disco_base, video_id, headers)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self._process_errors(e, geo_countries)
            raise
        for format_dict in streaming:
            if not isinstance(format_dict, dict):
                continue
            format_url = format_dict.get('url')
            if not format_url:
                continue
            format_id = format_dict.get('type')
            ext = determine_ext(format_url)
            if format_id == 'dash' or ext == 'mpd':
                dash_fmts, dash_subs = self._extract_mpd_formats_and_subtitles(
                    format_url, display_id, mpd_id='dash', fatal=False)
                formats.extend(dash_fmts)
                subtitles = self._merge_subtitles(subtitles, dash_subs)
            elif format_id == 'hls' or ext == 'm3u8':
                m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, display_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls',
                    fatal=False)
                formats.extend(m3u8_fmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                })

        creator = series = None
        tags = []
        thumbnails = []
        included = video.get('included') or []
        if isinstance(included, list):
            for e in included:
                attributes = e.get('attributes')
                if not attributes:
                    continue
                e_type = e.get('type')
                if e_type == 'channel':
                    creator = attributes.get('name')
                elif e_type == 'image':
                    src = attributes.get('src')
                    if src:
                        thumbnails.append({
                            'url': src,
                            'width': int_or_none(attributes.get('width')),
                            'height': int_or_none(attributes.get('height')),
                        })
                if e_type == 'show':
                    series = attributes.get('name')
                elif e_type == 'tag':
                    name = attributes.get('name')
                    if name:
                        tags.append(name)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': strip_or_none(info.get('description')),
            'duration': float_or_none(info.get('videoDuration'), 1000),
            'timestamp': unified_timestamp(info.get('publishStart')),
            'series': series,
            'season_number': int_or_none(info.get('seasonNumber')),
            'episode_number': int_or_none(info.get('episodeNumber')),
            'creator': creator,
            'tags': tags,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': {
                'referer': domain,
            },
        }


class DPlayIE(DPlayBaseIE):
    _VALID_URL = r'''(?x)https?://
        (?P<domain>
            (?:www\.)?(?P<host>d
                (?:
                    play\.(?P<country>dk|fi|jp|se|no)|
                    iscoveryplus\.(?P<plus_country>dk|es|fi|it|se|no)
                )
            )|
            (?P<subdomain_country>es|it)\.dplay\.com
        )/[^/]+''' + DPlayBaseIE._PATH_REGEX

    _TESTS = [{
        # non geo restricted, via secure api, unsigned download hls URL
        'url': 'https://www.dplay.se/videos/nugammalt-77-handelser-som-format-sverige/nugammalt-77-handelser-som-format-sverige-101',
        'info_dict': {
            'id': '13628',
            'display_id': 'nugammalt-77-handelser-som-format-sverige/nugammalt-77-handelser-som-format-sverige-101',
            'ext': 'mp4',
            'title': 'Svensken lär sig njuta av livet',
            'description': 'md5:d3819c9bccffd0fe458ca42451dd50d8',
            'duration': 2649.856,
            'timestamp': 1365453720,
            'upload_date': '20130408',
            'creator': 'Kanal 5',
            'series': 'Nugammalt - 77 händelser som format Sverige',
            'season_number': 1,
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # geo restricted, via secure api, unsigned download hls URL
        'url': 'http://www.dplay.dk/videoer/ted-bundy-mind-of-a-monster/ted-bundy-mind-of-a-monster',
        'info_dict': {
            'id': '104465',
            'display_id': 'ted-bundy-mind-of-a-monster/ted-bundy-mind-of-a-monster',
            'ext': 'mp4',
            'title': 'Ted Bundy: Mind Of A Monster',
            'description': 'md5:8b780f6f18de4dae631668b8a9637995',
            'duration': 5290.027,
            'timestamp': 1570694400,
            'upload_date': '20191010',
            'creator': 'ID - Investigation Discovery',
            'series': 'Ted Bundy: Mind Of A Monster',
            'season_number': 1,
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # disco-api
        'url': 'https://www.dplay.no/videoer/i-kongens-klr/sesong-1-episode-7',
        'info_dict': {
            'id': '40206',
            'display_id': 'i-kongens-klr/sesong-1-episode-7',
            'ext': 'mp4',
            'title': 'Episode 7',
            'description': 'md5:e3e1411b2b9aebeea36a6ec5d50c60cf',
            'duration': 2611.16,
            'timestamp': 1516726800,
            'upload_date': '20180123',
            'series': 'I kongens klær',
            'season_number': 1,
            'episode_number': 7,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'http://it.dplay.com/nove/biografie-imbarazzanti/luigi-di-maio-la-psicosi-di-stanislawskij/',
        'md5': '2b808ffb00fc47b884a172ca5d13053c',
        'info_dict': {
            'id': '6918',
            'display_id': 'biografie-imbarazzanti/luigi-di-maio-la-psicosi-di-stanislawskij',
            'ext': 'mp4',
            'title': 'Luigi Di Maio: la psicosi di Stanislawskij',
            'description': 'md5:3c7a4303aef85868f867a26f5cc14813',
            'thumbnail': r're:^https?://.*\.jpe?g',
            'upload_date': '20160524',
            'timestamp': 1464076800,
            'series': 'Biografie imbarazzanti',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        'url': 'https://es.dplay.com/dmax/la-fiebre-del-oro/temporada-8-episodio-1/',
        'info_dict': {
            'id': '21652',
            'display_id': 'la-fiebre-del-oro/temporada-8-episodio-1',
            'ext': 'mp4',
            'title': 'Episodio 1',
            'description': 'md5:b9dcff2071086e003737485210675f69',
            'thumbnail': r're:^https?://.*\.png',
            'upload_date': '20180709',
            'timestamp': 1531173540,
            'series': 'La fiebre del oro',
            'season_number': 8,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.dplay.fi/videot/shifting-gears-with-aaron-kaufman/episode-16',
        'only_matching': True,
    }, {
        'url': 'https://www.dplay.jp/video/gold-rush/24086',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.se/videos/nugammalt-77-handelser-som-format-sverige/nugammalt-77-handelser-som-format-sverige-101',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.dk/videoer/ted-bundy-mind-of-a-monster/ted-bundy-mind-of-a-monster',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.no/videoer/i-kongens-klr/sesong-1-episode-7',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.it/videos/biografie-imbarazzanti/luigi-di-maio-la-psicosi-di-stanislawskij',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.es/videos/la-fiebre-del-oro/temporada-8-episodio-1',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.fi/videot/shifting-gears-with-aaron-kaufman/episode-16',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        domain = remove_start(mobj.group('domain'), 'www.')
        country = mobj.group('country') or mobj.group('subdomain_country') or mobj.group('plus_country')
        host = 'disco-api.' + domain if domain[0] == 'd' else 'eu2-prod.disco-api.com'
        return self._get_disco_api_info(
            url, display_id, host, 'dplay' + country, country, domain)


class HGTVDeIE(DPlayBaseIE):
    _VALID_URL = r'https?://de\.hgtv\.com/sendungen' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://de.hgtv.com/sendungen/tiny-house-klein-aber-oho/wer-braucht-schon-eine-toilette/',
        'info_dict': {
            'id': '151205',
            'display_id': 'tiny-house-klein-aber-oho/wer-braucht-schon-eine-toilette',
            'ext': 'mp4',
            'title': 'Wer braucht schon eine Toilette',
            'description': 'md5:05b40a27e7aed2c9172de34d459134e2',
            'duration': 1177.024,
            'timestamp': 1595705400,
            'upload_date': '20200725',
            'creator': 'HGTV',
            'series': 'Tiny House - klein, aber oho',
            'season_number': 3,
            'episode_number': 3,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        return self._get_disco_api_info(
            url, display_id, 'eu1-prod.disco-api.com', 'hgtv', 'de')


class DiscoveryPlusBaseIE(DPlayBaseIE):
    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers['x-disco-client'] = f'WEB:UNKNOWN:{self._PRODUCT}:25.2.6'

    def _download_video_playback_info(self, disco_base, video_id, headers):
        return self._download_json(
            disco_base + 'playback/v3/videoPlaybackInfo',
            video_id, headers=headers, data=json.dumps({
                'deviceInfo': {
                    'adBlocker': False,
                },
                'videoId': video_id,
                'wisteriaProperties': {
                    'platform': 'desktop',
                    'product': self._PRODUCT,
                },
            }).encode('utf-8'))['data']['attributes']['streaming']

    def _real_extract(self, url):
        return self._get_disco_api_info(url, self._match_id(url), **self._DISCO_API_PARAMS)


class GoDiscoveryIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:go\.)?discovery\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://go.discovery.com/video/dirty-jobs-discovery-atve-us/rodbuster-galvanizer',
        'info_dict': {
            'id': '4164906',
            'display_id': 'dirty-jobs-discovery-atve-us/rodbuster-galvanizer',
            'ext': 'mp4',
            'title': 'Rodbuster / Galvanizer',
            'description': 'Mike installs rebar with a team of rodbusters, then he galvanizes steel.',
            'season_number': 9,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://discovery.com/video/dirty-jobs-discovery-atve-us/rodbuster-galvanizer',
        'only_matching': True,
    }]

    _PRODUCT = 'dsc'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.go.discovery.com',
        'realm': 'go',
        'country': 'us',
    }


class TravelChannelIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:watch\.)?travelchannel\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://watch.travelchannel.com/video/ghost-adventures-travel-channel/ghost-train-of-ely',
        'info_dict': {
            'id': '2220256',
            'display_id': 'ghost-adventures-travel-channel/ghost-train-of-ely',
            'ext': 'mp4',
            'title': 'Ghost Train of Ely',
            'description': 'The crew investigates the dark history of the Nevada Northern Railway.',
            'season_number': 24,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://watch.travelchannel.com/video/ghost-adventures-travel-channel/ghost-train-of-ely',
        'only_matching': True,
    }]

    _PRODUCT = 'trav'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.watch.travelchannel.com',
        'realm': 'go',
        'country': 'us',
    }


class CookingChannelIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:watch\.)?cookingchanneltv\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://watch.cookingchanneltv.com/video/carnival-eats-cooking-channel/the-postman-always-brings-rice-2348634',
        'info_dict': {
            'id': '2348634',
            'display_id': 'carnival-eats-cooking-channel/the-postman-always-brings-rice-2348634',
            'ext': 'mp4',
            'title': 'The Postman Always Brings Rice',
            'description': 'Noah visits the Maui Fair and the Aurora Winter Festival in Vancouver.',
            'season_number': 9,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://watch.cookingchanneltv.com/video/carnival-eats-cooking-channel/the-postman-always-brings-rice-2348634',
        'only_matching': True,
    }]

    _PRODUCT = 'cook'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.watch.cookingchanneltv.com',
        'realm': 'go',
        'country': 'us',
    }


class HGTVUsaIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:watch\.)?hgtv\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://watch.hgtv.com/video/home-inspector-joe-hgtv-atve-us/this-mold-house',
        'info_dict': {
            'id': '4289736',
            'display_id': 'home-inspector-joe-hgtv-atve-us/this-mold-house',
            'ext': 'mp4',
            'title': 'This Mold House',
            'description': 'Joe and Noel help take a familys dream home from hazardous to fabulous.',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://watch.hgtv.com/video/home-inspector-joe-hgtv-atve-us/this-mold-house',
        'only_matching': True,
    }]

    _PRODUCT = 'hgtv'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.watch.hgtv.com',
        'realm': 'go',
        'country': 'us',
    }


class FoodNetworkIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:watch\.)?foodnetwork\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://watch.foodnetwork.com/video/kids-baking-championship-food-network/float-like-a-butterfly',
        'info_dict': {
            'id': '4116449',
            'display_id': 'kids-baking-championship-food-network/float-like-a-butterfly',
            'ext': 'mp4',
            'title': 'Float Like a Butterfly',
            'description': 'The 12 kid bakers create colorful carved butterfly cakes.',
            'season_number': 10,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://watch.foodnetwork.com/video/kids-baking-championship-food-network/float-like-a-butterfly',
        'only_matching': True,
    }]

    _PRODUCT = 'food'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.watch.foodnetwork.com',
        'realm': 'go',
        'country': 'us',
    }


class DestinationAmericaIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?destinationamerica\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.destinationamerica.com/video/alaska-monsters-destination-america-atve-us/central-alaskas-bigfoot',
        'info_dict': {
            'id': '4210904',
            'display_id': 'alaska-monsters-destination-america-atve-us/central-alaskas-bigfoot',
            'ext': 'mp4',
            'title': 'Central Alaskas Bigfoot',
            'description': 'A team heads to central Alaska to investigate an aggressive Bigfoot.',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://www.destinationamerica.com/video/alaska-monsters-destination-america-atve-us/central-alaskas-bigfoot',
        'only_matching': True,
    }]

    _PRODUCT = 'dam'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.destinationamerica.com',
        'realm': 'go',
        'country': 'us',
    }


class InvestigationDiscoveryIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?investigationdiscovery\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.investigationdiscovery.com/video/unmasked-investigation-discovery/the-killer-clown',
        'info_dict': {
            'id': '2139409',
            'display_id': 'unmasked-investigation-discovery/the-killer-clown',
            'ext': 'mp4',
            'title': 'The Killer Clown',
            'description': 'A wealthy Florida woman is fatally shot in the face by a clown at her door.',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://www.investigationdiscovery.com/video/unmasked-investigation-discovery/the-killer-clown',
        'only_matching': True,
    }]

    _PRODUCT = 'ids'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.investigationdiscovery.com',
        'realm': 'go',
        'country': 'us',
    }


class AmHistoryChannelIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ahctv\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.ahctv.com/video/modern-sniper-ahc/army',
        'info_dict': {
            'id': '2309730',
            'display_id': 'modern-sniper-ahc/army',
            'ext': 'mp4',
            'title': 'Army',
            'description': 'Snipers today face challenges their predecessors couldve only dreamed of.',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://www.ahctv.com/video/modern-sniper-ahc/army',
        'only_matching': True,
    }]

    _PRODUCT = 'ahc'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.ahctv.com',
        'realm': 'go',
        'country': 'us',
    }


class ScienceChannelIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?sciencechannel\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.sciencechannel.com/video/strangest-things-science-atve-us/nazi-mystery-machine',
        'info_dict': {
            'id': '2842849',
            'display_id': 'strangest-things-science-atve-us/nazi-mystery-machine',
            'ext': 'mp4',
            'title': 'Nazi Mystery Machine',
            'description': 'Experts investigate the secrets of a revolutionary encryption machine.',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://www.sciencechannel.com/video/strangest-things-science-atve-us/nazi-mystery-machine',
        'only_matching': True,
    }]

    _PRODUCT = 'sci'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.sciencechannel.com',
        'realm': 'go',
        'country': 'us',
    }


class DIYNetworkIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:watch\.)?diynetwork\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://watch.diynetwork.com/video/pool-kings-diy-network/bringing-beach-life-to-texas',
        'info_dict': {
            'id': '2309730',
            'display_id': 'pool-kings-diy-network/bringing-beach-life-to-texas',
            'ext': 'mp4',
            'title': 'Bringing Beach Life to Texas',
            'description': 'The Pool Kings give a family a day at the beach in their own backyard.',
            'season_number': 10,
            'episode_number': 2,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://watch.diynetwork.com/video/pool-kings-diy-network/bringing-beach-life-to-texas',
        'only_matching': True,
    }]

    _PRODUCT = 'diy'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.watch.diynetwork.com',
        'realm': 'go',
        'country': 'us',
    }


class DiscoveryLifeIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoverylife\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.discoverylife.com/video/surviving-death-discovery-life-atve-us/bodily-trauma',
        'info_dict': {
            'id': '2218238',
            'display_id': 'surviving-death-discovery-life-atve-us/bodily-trauma',
            'ext': 'mp4',
            'title': 'Bodily Trauma',
            'description': 'Meet three people who tested the limits of the human body.',
            'season_number': 1,
            'episode_number': 2,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://www.discoverylife.com/video/surviving-death-discovery-life-atve-us/bodily-trauma',
        'only_matching': True,
    }]

    _PRODUCT = 'dlf'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.discoverylife.com',
        'realm': 'go',
        'country': 'us',
    }


class AnimalPlanetIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?animalplanet\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.animalplanet.com/video/north-woods-law-animal-planet/squirrel-showdown',
        'info_dict': {
            'id': '3338923',
            'display_id': 'north-woods-law-animal-planet/squirrel-showdown',
            'ext': 'mp4',
            'title': 'Squirrel Showdown',
            'description': 'A woman is suspected of being in possession of flying squirrel kits.',
            'season_number': 16,
            'episode_number': 11,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://www.animalplanet.com/video/north-woods-law-animal-planet/squirrel-showdown',
        'only_matching': True,
    }]

    _PRODUCT = 'apl'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.animalplanet.com',
        'realm': 'go',
        'country': 'us',
    }


class TLCIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:go\.)?tlc\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://go.tlc.com/video/my-600-lb-life-tlc/melissas-story-part-1',
        'info_dict': {
            'id': '2206540',
            'display_id': 'my-600-lb-life-tlc/melissas-story-part-1',
            'ext': 'mp4',
            'title': 'Melissas Story (Part 1)',
            'description': 'At 650 lbs, Melissa is ready to begin her seven-year weight loss journey.',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://go.tlc.com/video/my-600-lb-life-tlc/melissas-story-part-1',
        'only_matching': True,
    }]

    _PRODUCT = 'tlc'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.tlc.com',
        'realm': 'go',
        'country': 'us',
    }


class MotorTrendIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:watch\.)?motortrend\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://watch.motortrend.com/video/car-issues-motortrend-atve-us/double-dakotas',
        'info_dict': {
            'id': '"4859182"',
            'display_id': 'double-dakotas',
            'ext': 'mp4',
            'title': 'Double Dakotas',
            'description': 'Tylers buy-one-get-one Dakota deal has the Wizard pulling double duty.',
            'season_number': 2,
            'episode_number': 3,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://watch.motortrend.com/video/car-issues-motortrend-atve-us/double-dakotas',
        'only_matching': True,
    }]

    _PRODUCT = 'vel'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.watch.motortrend.com',
        'realm': 'go',
        'country': 'us',
    }


class MotorTrendOnDemandIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?motortrendondemand\.com/detail' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.motortrendondemand.com/detail/wheelstanding-dump-truck-stubby-bobs-comeback/37699/784',
        'info_dict': {
            'id': '37699',
            'display_id': 'wheelstanding-dump-truck-stubby-bobs-comeback/37699',
            'ext': 'mp4',
            'title': 'Wheelstanding Dump Truck! Stubby Bob’s Comeback',
            'description': 'md5:996915abe52a1c3dfc83aecea3cce8e7',
            'season_number': 5,
            'episode_number': 52,
            'episode': 'Episode 52',
            'season': 'Season 5',
            'thumbnail': r're:^https?://.+\.jpe?g$',
            'timestamp': 1388534401,
            'duration': 1887.345,
            'creator': 'Originals',
            'series': 'Roadkill',
            'upload_date': '20140101',
            'tags': [],
        },
    }]

    _PRODUCT = 'MTOD'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.motortrendondemand.com',
        'realm': 'motortrend',
        'country': 'us',
    }

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm}',
            'x-disco-client': f'WEB:UNKNOWN:{self._PRODUCT}:4.39.1-gi1',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })


class DiscoveryPlusIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.com/(?!it/)(?:\w{2}/)?video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.discoveryplus.com/video/property-brothers-forever-home/food-and-family',
        'info_dict': {
            'id': '1140794',
            'display_id': 'property-brothers-forever-home/food-and-family',
            'ext': 'mp4',
            'title': 'Food and Family',
            'description': 'The brothers help a Richmond family expand their single-level home.',
            'duration': 2583.113,
            'timestamp': 1609304400,
            'upload_date': '20201230',
            'creator': 'HGTV',
            'series': 'Property Brothers: Forever Home',
            'season_number': 1,
            'episode_number': 1,
        },
        'skip': 'Available for Premium users',
    }, {
        'url': 'https://discoveryplus.com/ca/video/bering-sea-gold-discovery-ca/goldslingers',
        'only_matching': True,
    }]

    _PRODUCT = 'dplus_us'
    _DISCO_API_PARAMS = {
        'disco_host': 'us1-prod-direct.discoveryplus.com',
        'realm': 'go',
        'country': 'us',
    }


class DiscoveryPlusIndiaIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.in/videos?' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.discoveryplus.in/videos/how-do-they-do-it/fugu-and-more?seasonId=8&type=EPISODE',
        'info_dict': {
            'id': '27104',
            'ext': 'mp4',
            'display_id': 'how-do-they-do-it/fugu-and-more',
            'title': 'Fugu and More',
            'description': 'The Japanese catch, prepare and eat the deadliest fish on the planet.',
            'duration': 1319.32,
            'timestamp': 1582309800,
            'upload_date': '20200221',
            'series': 'How Do They Do It?',
            'season_number': 8,
            'episode_number': 2,
            'creator': 'Discovery Channel',
            'thumbnail': r're:https://.+\.jpeg',
            'episode': 'Episode 2',
            'season': 'Season 8',
            'tags': [],
        },
        'params': {
            'skip_download': True,
        }
    }]

    _PRODUCT = 'dplus-india'
    _DISCO_API_PARAMS = {
        'disco_host': 'ap2-prod-direct.discoveryplus.in',
        'realm': 'dplusindia',
        'country': 'in',
        'domain': 'https://www.discoveryplus.in/',
    }

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': 'realm=%s' % realm,
            'x-disco-client': f'WEB:UNKNOWN:{self._PRODUCT}:17.0.0',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })


class DiscoveryNetworksDeIE(DPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<domain>(?:tlc|dmax)\.de|dplay\.co\.uk)/(?:programme|show|sendungen)/(?P<programme>[^/]+)/(?:video/)?(?P<alternate_id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.tlc.de/programme/breaking-amish/video/die-welt-da-drauen/DCB331270001100',
        'info_dict': {
            'id': '78867',
            'ext': 'mp4',
            'title': 'Die Welt da draußen',
            'description': 'md5:61033c12b73286e409d99a41742ef608',
            'timestamp': 1554069600,
            'upload_date': '20190331',
            'creator': 'TLC',
            'season': 'Season 1',
            'series': 'Breaking Amish',
            'episode_number': 1,
            'tags': ['new york', 'großstadt', 'amische', 'landleben', 'modern', 'infos', 'tradition', 'herausforderung'],
            'display_id': 'breaking-amish/die-welt-da-drauen',
            'episode': 'Episode 1',
            'duration': 2625.024,
            'season_number': 1,
            'thumbnail': r're:https://.+\.jpg',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.dmax.de/programme/dmax-highlights/video/tuning-star-sidney-hoffmann-exklusiv-bei-dmax/191023082312316',
        'only_matching': True,
    }, {
        'url': 'https://www.dplay.co.uk/show/ghost-adventures/video/hotel-leger-103620/EHD_280313B',
        'only_matching': True,
    }, {
        'url': 'https://tlc.de/sendungen/breaking-amish/die-welt-da-drauen/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, programme, alternate_id = self._match_valid_url(url).groups()
        country = 'GB' if domain == 'dplay.co.uk' else 'DE'
        realm = 'questuk' if country == 'GB' else domain.replace('.', '')
        return self._get_disco_api_info(
            url, '%s/%s' % (programme, alternate_id),
            'sonic-eu1-prod.disco-api.com', realm, country)


class DiscoveryPlusShowBaseIE(DPlayBaseIE):

    def _entries(self, show_name):
        headers = {
            'x-disco-client': self._X_CLIENT,
            'x-disco-params': f'realm={self._REALM}',
            'referer': self._DOMAIN,
            'Authentication': self._get_auth(self._BASE_API, None, self._REALM),
        }
        show_json = self._download_json(
            f'{self._BASE_API}cms/routes/{self._SHOW_STR}/{show_name}?include=default',
            video_id=show_name, headers=headers)['included'][self._INDEX]['attributes']['component']
        show_id = show_json['mandatoryParams'].split('=')[-1]
        season_url = self._BASE_API + 'content/videos?sort=episodeNumber&filter[seasonNumber]={}&filter[show.id]={}&page[size]=100&page[number]={}'
        for season in show_json['filters'][0]['options']:
            season_id = season['id']
            total_pages, page_num = 1, 0
            while page_num < total_pages:
                season_json = self._download_json(
                    season_url.format(season_id, show_id, str(page_num + 1)), show_name, headers=headers,
                    note='Downloading season %s JSON metadata%s' % (season_id, ' page %d' % page_num if page_num else ''))
                if page_num == 0:
                    total_pages = try_get(season_json, lambda x: x['meta']['totalPages'], int) or 1
                episodes_json = season_json['data']
                for episode in episodes_json:
                    video_path = episode['attributes']['path']
                    yield self.url_result(
                        '%svideos/%s' % (self._DOMAIN, video_path),
                        ie=self._VIDEO_IE.ie_key(), video_id=episode.get('id') or video_path)
                page_num += 1

    def _real_extract(self, url):
        show_name = self._match_valid_url(url).group('show_name')
        return self.playlist_result(self._entries(show_name), playlist_id=show_name)


class DiscoveryPlusItalyIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.com/it/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.discoveryplus.com/it/video/i-signori-della-neve/stagione-2-episodio-1-i-preparativi',
        'only_matching': True,
    }, {
        'url': 'https://www.discoveryplus.com/it/video/super-benny/trailer',
        'only_matching': True,
    }]

    _PRODUCT = 'dplus_us'
    _DISCO_API_PARAMS = {
        'disco_host': 'eu1-prod-direct.discoveryplus.com',
        'realm': 'dplay',
        'country': 'it',
    }

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': 'realm=%s' % realm,
            'x-disco-client': f'WEB:UNKNOWN:{self._PRODUCT}:25.2.6',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })


class DiscoveryPlusItalyShowIE(DiscoveryPlusShowBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.it/programmi/(?P<show_name>[^/]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.discoveryplus.it/programmi/deal-with-it-stai-al-gioco',
        'playlist_mincount': 168,
        'info_dict': {
            'id': 'deal-with-it-stai-al-gioco',
        },
    }]

    _BASE_API = 'https://disco-api.discoveryplus.it/'
    _DOMAIN = 'https://www.discoveryplus.it/'
    _X_CLIENT = 'WEB:UNKNOWN:dplay-client:2.6.0'
    _REALM = 'dplayit'
    _SHOW_STR = 'programmi'
    _INDEX = 1
    _VIDEO_IE = DPlayIE


class DiscoveryPlusIndiaShowIE(DiscoveryPlusShowBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.in/show/(?P<show_name>[^/]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.discoveryplus.in/show/how-do-they-do-it',
        'playlist_mincount': 140,
        'info_dict': {
            'id': 'how-do-they-do-it',
        },
    }]

    _BASE_API = 'https://ap2-prod-direct.discoveryplus.in/'
    _DOMAIN = 'https://www.discoveryplus.in/'
    _X_CLIENT = 'WEB:UNKNOWN:dplus-india:prod'
    _REALM = 'dplusindia'
    _SHOW_STR = 'show'
    _INDEX = 4
    _VIDEO_IE = DiscoveryPlusIndiaIE


class GlobalCyclingNetworkPlusIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://plus\.globalcyclingnetwork\.com/watch/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://plus.globalcyclingnetwork.com/watch/1397691',
        'info_dict': {
            'id': '1397691',
            'ext': 'mp4',
            'title': 'The Athertons: Mountain Biking\'s Fastest Family',
            'description': 'md5:75a81937fcd8b989eec6083a709cd837',
            'thumbnail': 'https://us1-prod-images.disco-api.com/2021/03/04/eb9e3026-4849-3001-8281-9356466f0557.png',
            'series': 'gcn',
            'creator': 'Gcn',
            'upload_date': '20210309',
            'timestamp': 1615248000,
            'duration': 2531.0,
            'tags': [],
        },
        'skip': 'Subscription required',
        'params': {'skip_download': 'm3u8'},
    }]

    _PRODUCT = 'web'
    _DISCO_API_PARAMS = {
        'disco_host': 'disco-api-prod.globalcyclingnetwork.com',
        'realm': 'gcn',
        'country': 'us',
    }

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm}',
            'x-disco-client': f'WEB:UNKNOWN:{self._PRODUCT}:27.3.2',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })

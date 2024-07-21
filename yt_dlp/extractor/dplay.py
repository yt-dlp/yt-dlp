import json
import uuid

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
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
        info = self._parse_json(e.cause.response.read().decode('utf-8'), None)
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
        disco_base = f'https://{disco_host}/'
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
                    'include': 'images,primaryChannel,show,tags',
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
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
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
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
    """Subclasses must set _PRODUCT, _DISCO_API_PARAMS"""

    _DISCO_CLIENT_VER = '27.43.0'

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm},siteLookupKey={self._PRODUCT}',
            'x-disco-client': f'WEB:UNKNOWN:{self._PRODUCT}:{self._DISCO_CLIENT_VER}',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })

    def _download_video_playback_info(self, disco_base, video_id, headers):
        return self._download_json(
            disco_base + 'playback/v3/videoPlaybackInfo',
            video_id, headers=headers, data=json.dumps({
                'deviceInfo': {
                    'adBlocker': False,
                    'drmSupported': False,
                },
                'videoId': video_id,
                'wisteriaProperties': {},
            }).encode())['data']['attributes']['streaming']

    def _real_extract(self, url):
        return self._get_disco_api_info(url, self._match_id(url), **self._DISCO_API_PARAMS)


class GoDiscoveryIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:go\.)?discovery\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://go.discovery.com/video/in-the-eye-of-the-storm-discovery-atve-us/trapped-in-a-twister',
        'info_dict': {
            'id': '5352642',
            'display_id': 'in-the-eye-of-the-storm-discovery-atve-us/trapped-in-a-twister',
            'ext': 'mp4',
            'title': 'Trapped in a Twister',
            'description': 'Twisters destroy Midwest towns, trapping spotters in the eye of the storm.',
            'episode_number': 1,
            'episode': 'Episode 1',
            'season_number': 1,
            'season': 'Season 1',
            'series': 'In The Eye Of The Storm',
            'duration': 2490.237,
            'upload_date': '20240715',
            'timestamp': 1721008800,
            'tags': [],
            'creators': ['Discovery'],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2024/07/10/5e39637d-cabf-3ab3-8e9a-f4e9d37bc036.jpeg',
        },
    }, {
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
        'url': 'https://watch.travelchannel.com/video/the-dead-files-travel-channel/protect-the-children',
        'info_dict': {
            'id': '4710177',
            'display_id': 'the-dead-files-travel-channel/protect-the-children',
            'ext': 'mp4',
            'title': 'Protect the Children',
            'description': 'An evil presence threatens an Ohio woman\'s children and marriage.',
            'season_number': 14,
            'season': 'Season 14',
            'episode_number': 10,
            'episode': 'Episode 10',
            'series': 'The Dead Files',
            'duration': 2550.481,
            'timestamp': 1664510400,
            'upload_date': '20220930',
            'tags': [],
            'creators': ['Travel Channel'],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2022/03/17/5e45eace-de5d-343a-9293-f400a2aa77d5.jpeg',
        },
    }, {
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
        'url': 'https://watch.cookingchanneltv.com/video/bobbys-triple-threat-food-network-atve-us/titans-vs-marcus-samuelsson',
        'info_dict': {
            'id': '5350005',
            'ext': 'mp4',
            'display_id': 'bobbys-triple-threat-food-network-atve-us/titans-vs-marcus-samuelsson',
            'title': 'Titans vs Marcus Samuelsson',
            'description': 'Marcus Samuelsson throws his legendary global tricks at the Titans.',
            'episode_number': 1,
            'episode': 'Episode 1',
            'season_number': 3,
            'season': 'Season 3',
            'series': 'Bobby\'s Triple Threat',
            'duration': 2520.851,
            'upload_date': '20240710',
            'timestamp': 1720573200,
            'tags': [],
            'creators': ['Food Network'],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2024/07/04/529cd095-27ec-35c5-84e9-90ebd3e5d2da.jpeg',
        },
    }, {
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
        'url': 'https://watch.hgtv.com/video/flip-or-flop-the-final-flip-hgtv-atve-us/flip-or-flop-the-final-flip',
        'info_dict': {
            'id': '5025585',
            'display_id': 'flip-or-flop-the-final-flip-hgtv-atve-us/flip-or-flop-the-final-flip',
            'ext': 'mp4',
            'title': 'Flip or Flop: The Final Flip',
            'description': 'Tarek and Christina are going their separate ways after one last flip!',
            'series': 'Flip or Flop: The Final Flip',
            'duration': 2580.644,
            'upload_date': '20231101',
            'timestamp': 1698811200,
            'tags': [],
            'creators': ['HGTV'],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2022/11/27/455caa6c-1462-3f14-b63d-a026d7a5e6d3.jpeg',
        },
    }, {
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
        'url': 'https://watch.foodnetwork.com/video/guys-grocery-games-food-network/wild-in-the-aisles',
        'info_dict': {
            'id': '2152549',
            'display_id': 'guys-grocery-games-food-network/wild-in-the-aisles',
            'ext': 'mp4',
            'title': 'Wild in the Aisles',
            'description': 'The chefs make spaghetti and meatballs with "Out of Stock" ingredients.',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'Episode 1',
            'series': 'Guy\'s Grocery Games',
            'tags': [],
            'creators': ['Food Network'],
            'duration': 2520.651,
            'upload_date': '20230623',
            'timestamp': 1687492800,
            'thumbnail': 'https://us1-prod-images.disco-api.com/2022/06/15/37fb5333-cad2-3dbb-af7c-c20ec77c89c6.jpeg',
        },
    }, {
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
        'url': 'https://www.destinationamerica.com/video/bbq-pit-wars-destination-america/smoke-on-the-water',
        'info_dict': {
            'id': '2218409',
            'display_id': 'bbq-pit-wars-destination-america/smoke-on-the-water',
            'ext': 'mp4',
            'title': 'Smoke on the Water',
            'description': 'The pitmasters head to Georgia for the Smoke on the Water BBQ Festival.',
            'season_number': 2,
            'season': 'Season 2',
            'episode_number': 1,
            'episode': 'Episode 1',
            'series': 'BBQ Pit Wars',
            'tags': [],
            'creators': ['Destination America'],
            'duration': 2614.878,
            'upload_date': '20230623',
            'timestamp': 1687492800,
            'thumbnail': 'https://us1-prod-images.disco-api.com/2020/05/11/c0f8e85d-9a10-3e6f-8e43-f6faafa81ba2.jpeg',
        },
    }, {
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
        'url': 'https://www.investigationdiscovery.com/video/deadly-influence-the-social-media-murders-investigation-discovery-atve-us/rip-bianca',
        'info_dict': {
            'id': '5341132',
            'display_id': 'deadly-influence-the-social-media-murders-investigation-discovery-atve-us/rip-bianca',
            'ext': 'mp4',
            'title': 'RIP Bianca',
            'description': 'A teenage influencer discovers an online world of threat, harm and danger.',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 3,
            'episode': 'Episode 3',
            'series': 'Deadly Influence: The Social Media Murders',
            'creators': ['Investigation Discovery'],
            'tags': [],
            'duration': 2490.888,
            'upload_date': '20240618',
            'timestamp': 1718672400,
            'thumbnail': 'https://us1-prod-images.disco-api.com/2024/06/15/b567c774-9e44-3c6c-b0ba-db860a73e812.jpeg',
        },
    }, {
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
        'url': 'https://www.ahctv.com/video/blood-and-fury-americas-civil-war-ahc/battle-of-bull-run',
        'info_dict': {
            'id': '2139199',
            'display_id': 'blood-and-fury-americas-civil-war-ahc/battle-of-bull-run',
            'ext': 'mp4',
            'title': 'Battle of Bull Run',
            'description': 'Two untested armies clash in the first real battle of the Civil War.',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'Episode 1',
            'series': 'Blood and Fury: America\'s Civil War',
            'duration': 2612.509,
            'upload_date': '20220923',
            'timestamp': 1663905600,
            'creators': ['AHC'],
            'tags': [],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2020/05/11/4af61bd7-d705-3108-82c4-1a6e541e20fa.jpeg',
        },
    }, {
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
        'url': 'https://www.sciencechannel.com/video/spaces-deepest-secrets-science-atve-us/mystery-of-the-dead-planets',
        'info_dict': {
            'id': '2347335',
            'display_id': 'spaces-deepest-secrets-science-atve-us/mystery-of-the-dead-planets',
            'ext': 'mp4',
            'title': 'Mystery of the Dead Planets',
            'description': 'Astronomers unmask the truly destructive nature of the cosmos.',
            'season_number': 7,
            'season': 'Season 7',
            'episode_number': 1,
            'episode': 'Episode 1',
            'series': 'Space\'s Deepest Secrets',
            'duration': 2524.989,
            'upload_date': '20230128',
            'timestamp': 1674882000,
            'creators': ['Science'],
            'tags': [],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2021/03/30/3796829d-aead-3f9a-bd8d-e49048b3cdca.jpeg',
        },
    }, {
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


class DiscoveryLifeIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoverylife\.com/video' + DPlayBaseIE._PATH_REGEX
    _TESTS = [{
        'url': 'https://www.discoverylife.com/video/er-files-discovery-life-atve-us/sweet-charity',
        'info_dict': {
            'id': '2347614',
            'display_id': 'er-files-discovery-life-atve-us/sweet-charity',
            'ext': 'mp4',
            'title': 'Sweet Charity',
            'description': 'The staff at Charity Hospital treat a serious foot infection.',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'Episode 1',
            'series': 'ER Files',
            'duration': 2364.261,
            'upload_date': '20230721',
            'timestamp': 1689912000,
            'creators': ['Discovery Life'],
            'tags': [],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2021/03/16/4b6f0124-360b-3546-b6a4-5552db886b86.jpeg',
        },
    }, {
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
        'url': 'https://www.animalplanet.com/video/mysterious-creatures-with-forrest-galante-animal-planet-atve-us/the-demon-of-peru',
        'info_dict': {
            'id': '4650835',
            'display_id': 'mysterious-creatures-with-forrest-galante-animal-planet-atve-us/the-demon-of-peru',
            'ext': 'mp4',
            'title': 'The Demon of Peru',
            'description': 'In Peru, a farming village is being terrorized by a “man-like beast.”',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 4,
            'episode': 'Episode 4',
            'series': 'Mysterious Creatures with Forrest Galante',
            'duration': 2490.488,
            'upload_date': '20230111',
            'timestamp': 1673413200,
            'creators': ['Animal Planet'],
            'tags': [],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2022/03/01/6dbaa833-9a2e-3fee-9381-c19eddf67c0c.jpeg',
        },
    }, {
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
        'url': 'https://go.tlc.com/video/90-day-the-last-resort-tlc-atve-us/the-last-chance',
        'info_dict': {
            'id': '5186422',
            'display_id': '90-day-the-last-resort-tlc-atve-us/the-last-chance',
            'ext': 'mp4',
            'title': 'The Last Chance',
            'description': 'Infidelity shakes Kalani and Asuelu\'s world, and Angela threatens divorce.',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'Episode 1',
            'series': '90 Day: The Last Resort',
            'duration': 5123.91,
            'upload_date': '20230815',
            'timestamp': 1692061200,
            'creators': ['TLC'],
            'tags': [],
            'thumbnail': 'https://us1-prod-images.disco-api.com/2023/08/08/0ee367e2-ac76-334d-bf23-dbf796696a24.jpeg',
        },
    }, {
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


class DiscoveryPlusIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?discoveryplus\.com/(?!it/)(?:(?P<country>[a-z]{2})/)?video(?:/sport)?' + DPlayBaseIE._PATH_REGEX
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
    }, {
        'url': 'https://www.discoveryplus.com/gb/video/sport/eurosport-1-british-eurosport-1-british-sport/6-hours-of-spa-review',
        'only_matching': True,
    }]

    _PRODUCT = None
    _DISCO_API_PARAMS = None

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm},siteLookupKey={self._PRODUCT}',
            'x-disco-client': f'WEB:UNKNOWN:dplus_us:{self._DISCO_CLIENT_VER}',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })

    def _real_extract(self, url):
        video_id, country = self._match_valid_url(url).group('id', 'country')
        if not country:
            country = 'us'

        self._PRODUCT = f'dplus_{country}'

        if country in ('br', 'ca', 'us'):
            self._DISCO_API_PARAMS = {
                'disco_host': 'us1-prod-direct.discoveryplus.com',
                'realm': 'go',
                'country': country,
            }
        else:
            self._DISCO_API_PARAMS = {
                'disco_host': 'eu1-prod-direct.discoveryplus.com',
                'realm': 'dplay',
                'country': country,
            }

        return self._get_disco_api_info(url, video_id, **self._DISCO_API_PARAMS)


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
        },
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
            'x-disco-params': f'realm={realm}',
            'x-disco-client': f'WEB:UNKNOWN:{self._PRODUCT}:17.0.0',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })


class DiscoveryNetworksDeIE(DiscoveryPlusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<domain>(?:tlc|dmax)\.de|dplay\.co\.uk)/(?:programme|show|sendungen)/(?P<programme>[^/]+)/(?:video/)?(?P<alternate_id>[^/]+)'

    _TESTS = [{
        'url': 'https://dmax.de/sendungen/goldrausch-in-australien/german-gold',
        'info_dict': {
            'id': '4756322',
            'ext': 'mp4',
            'title': 'German Gold',
            'description': 'md5:f3073306553a8d9b40e6ac4cdbf09fc6',
            'display_id': 'goldrausch-in-australien/german-gold',
            'episode': 'Episode 1',
            'episode_number': 1,
            'season': 'Season 5',
            'season_number': 5,
            'series': 'Goldrausch in Australien',
            'duration': 2648.0,
            'upload_date': '20230517',
            'timestamp': 1684357500,
            'creators': ['DMAX'],
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2023/05/09/f72fb510-7992-3b12-af7f-f16a2c22d1e3.jpeg',
            'tags': ['schatzsucher', 'schatz', 'nugget', 'bodenschätze', 'down under', 'australien', 'goldrausch'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
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
        'skip': '404 Not Found',
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
            url, f'{programme}/{alternate_id}', 'eu1-prod.disco-api.com', realm, country)

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm}',
            'x-disco-client': 'Alps:HyogaPlayer:0.0.0',
            'Authorization': self._get_auth(disco_base, display_id, realm),
        })


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
                    note='Downloading season {} JSON metadata{}'.format(season_id, f' page {page_num}' if page_num else ''))
                if page_num == 0:
                    total_pages = try_get(season_json, lambda x: x['meta']['totalPages'], int) or 1
                episodes_json = season_json['data']
                for episode in episodes_json:
                    video_path = episode['attributes']['path']
                    yield self.url_result(
                        f'{self._DOMAIN}videos/{video_path}',
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

    _PRODUCT = 'dplus_it'
    _DISCO_API_PARAMS = {
        'disco_host': 'eu1-prod-direct.discoveryplus.com',
        'realm': 'dplay',
        'country': 'it',
    }

    def _update_disco_api_headers(self, headers, disco_base, display_id, realm):
        headers.update({
            'x-disco-params': f'realm={realm},siteLookupKey={self._PRODUCT}',
            'x-disco-client': f'WEB:UNKNOWN:dplus_us:{self._DISCO_CLIENT_VER}',
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

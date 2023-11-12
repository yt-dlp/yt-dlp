import re
import json
import base64
import time
import urllib.parse

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    js_to_json,
    orderedSet,
    parse_iso8601,
    smuggle_url,
    strip_or_none,
    traverse_obj,
    try_get,
)


class CBCIE(InfoExtractor):
    IE_NAME = 'cbc.ca'
    _VALID_URL = r'https?://(?:www\.)?cbc\.ca/(?!player/)(?:[^/]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        # with mediaId
        'url': 'http://www.cbc.ca/22minutes/videos/clips-season-23/don-cherry-play-offs',
        'md5': '97e24d09672fc4cf56256d6faa6c25bc',
        'info_dict': {
            'id': '2682904050',
            'ext': 'mp4',
            'title': 'Don Cherry – All-Stars',
            'description': 'Don Cherry has a bee in his bonnet about AHL player John Scott because that guy’s got heart.',
            'timestamp': 1454463000,
            'upload_date': '20160203',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada',
    }, {
        # with clipId, feed available via tpfeed.cbc.ca and feed.theplatform.com
        'url': 'http://www.cbc.ca/22minutes/videos/22-minutes-update/22-minutes-update-episode-4',
        'md5': '162adfa070274b144f4fdc3c3b8207db',
        'info_dict': {
            'id': '2414435309',
            'ext': 'mp4',
            'title': '22 Minutes Update: What Not To Wear Quebec',
            'description': "This week's latest Canadian top political story is What Not To Wear Quebec.",
            'upload_date': '20131025',
            'uploader': 'CBCC-NEW',
            'timestamp': 1382717907,
        },
        'skip': 'No longer available',
    }, {
        # with clipId, feed only available via tpfeed.cbc.ca
        'url': 'http://www.cbc.ca/archives/entry/1978-robin-williams-freestyles-on-90-minutes-live',
        'md5': '0274a90b51a9b4971fe005c63f592f12',
        'info_dict': {
            'id': '2487345465',
            'ext': 'mp4',
            'title': 'Robin Williams freestyles on 90 Minutes Live',
            'description': 'Wacky American comedian Robin Williams shows off his infamous "freestyle" comedic talents while being interviewed on CBC\'s 90 Minutes Live.',
            'upload_date': '19780210',
            'uploader': 'CBCC-NEW',
            'timestamp': 255977160,
        },
        'skip': '404 Not Found',
    }, {
        # multiple iframes
        'url': 'http://www.cbc.ca/natureofthings/blog/birds-eye-view-from-vancouvers-burrard-street-bridge-how-we-got-the-shot',
        'playlist': [{
            'md5': '377572d0b49c4ce0c9ad77470e0b96b4',
            'info_dict': {
                'id': '2680832926',
                'ext': 'mp4',
                'title': 'An Eagle\'s-Eye View Off Burrard Bridge',
                'description': 'Hercules the eagle flies from Vancouver\'s Burrard Bridge down to a nearby park with a mini-camera strapped to his back.',
                'upload_date': '20160201',
                'timestamp': 1454342820,
                'uploader': 'CBCC-NEW',
            },
        }, {
            'md5': '415a0e3f586113894174dfb31aa5bb1a',
            'info_dict': {
                'id': '2658915080',
                'ext': 'mp4',
                'title': 'Fly like an eagle!',
                'description': 'Eagle equipped with a mini camera flies from the world\'s tallest tower',
                'upload_date': '20150315',
                'timestamp': 1426443984,
                'uploader': 'CBCC-NEW',
            },
        }],
        'skip': 'Geo-restricted to Canada',
    }, {
        # multiple CBC.APP.Caffeine.initInstance(...)
        'url': 'http://www.cbc.ca/news/canada/calgary/dog-indoor-exercise-winter-1.3928238',
        'info_dict': {
            'title': 'Keep Rover active during the deep freeze with doggie pushups and other fun indoor tasks',  # FIXME
            'id': 'dog-indoor-exercise-winter-1.3928238',
            'description': 'md5:c18552e41726ee95bd75210d1ca9194c',
        },
        'playlist_mincount': 6,
    }]

    @classmethod
    def suitable(cls, url):
        return False if CBCPlayerIE.suitable(url) else super(CBCIE, cls).suitable(url)

    def _extract_player_init(self, player_init, display_id):
        player_info = self._parse_json(player_init, display_id, js_to_json)
        media_id = player_info.get('mediaId')
        if not media_id:
            clip_id = player_info['clipId']
            feed = self._download_json(
                'http://tpfeed.cbc.ca/f/ExhSPC/vms_5akSXx4Ng_Zn?byCustomValue={:mpsReleases}{%s}' % clip_id,
                clip_id, fatal=False)
            if feed:
                media_id = try_get(feed, lambda x: x['entries'][0]['guid'], compat_str)
            if not media_id:
                media_id = self._download_json(
                    'http://feed.theplatform.com/f/h9dtGB/punlNGjMlc1F?fields=id&byContent=byReleases%3DbyId%253D' + clip_id,
                    clip_id)['entries'][0]['id'].split('/')[-1]
        return self.url_result('cbcplayer:%s' % media_id, 'CBCPlayer', media_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        title = (self._og_search_title(webpage, default=None)
                 or self._html_search_meta('twitter:title', webpage, 'title', default=None)
                 or self._html_extract_title(webpage))
        entries = [
            self._extract_player_init(player_init, display_id)
            for player_init in re.findall(r'CBC\.APP\.Caffeine\.initInstance\(({.+?})\);', webpage)]
        media_ids = []
        for media_id_re in (
                r'<iframe[^>]+src="[^"]+?mediaId=(\d+)"',
                r'<div[^>]+\bid=["\']player-(\d+)',
                r'guid["\']\s*:\s*["\'](\d+)'):
            media_ids.extend(re.findall(media_id_re, webpage))
        entries.extend([
            self.url_result('cbcplayer:%s' % media_id, 'CBCPlayer', media_id)
            for media_id in orderedSet(media_ids)])
        return self.playlist_result(
            entries, display_id, strip_or_none(title),
            self._og_search_description(webpage))


class CBCPlayerIE(InfoExtractor):
    IE_NAME = 'cbc.ca:player'
    _VALID_URL = r'(?:cbcplayer:|https?://(?:www\.)?cbc\.ca/(?:player/play/|i/caffeine/syndicate/\?mediaId=))(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.cbc.ca/player/play/2683190193',
        'md5': '64d25f841ddf4ddb28a235338af32e2c',
        'info_dict': {
            'id': '2683190193',
            'ext': 'mp4',
            'title': 'Gerry Runs a Sweat Shop',
            'description': 'md5:b457e1c01e8ff408d9d801c1c2cd29b0',
            'timestamp': 1455071400,
            'upload_date': '20160210',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada and no longer available',
    }, {
        # Redirected from http://www.cbc.ca/player/AudioMobile/All%20in%20a%20Weekend%20Montreal/ID/2657632011/
        'url': 'http://www.cbc.ca/player/play/2657631896',
        'md5': 'e5e708c34ae6fca156aafe17c43e8b75',
        'info_dict': {
            'id': '2657631896',
            'ext': 'mp3',
            'title': 'CBC Montreal is organizing its first ever community hackathon!',
            'description': 'The modern technology we tend to depend on so heavily, is never without it\'s share of hiccups and headaches. Next weekend - CBC Montreal will be getting members of the public for its first Hackathon.',
            'timestamp': 1425704400,
            'upload_date': '20150307',
            'uploader': 'CBCC-NEW',
            'thumbnail': 'http://thumbnails.cbc.ca/maven_legacy/thumbnails/sonali-karnick-220.jpg',
            'chapters': [],
            'duration': 494.811,
        },
    }, {
        'url': 'http://www.cbc.ca/player/play/2164402062',
        'md5': '33fcd8f6719b9dd60a5e73adcb83b9f6',
        'info_dict': {
            'id': '2164402062',
            'ext': 'mp4',
            'title': 'Cancer survivor four times over',
            'description': 'Tim Mayer has beaten three different forms of cancer four times in five years.',
            'timestamp': 1320410746,
            'upload_date': '20111104',
            'uploader': 'CBCC-NEW',
            'thumbnail': 'https://thumbnails.cbc.ca/maven_legacy/thumbnails/277/67/cancer_852x480_2164412612.jpg',
            'chapters': [],
            'duration': 186.867,
        },
    }, {
        # Has subtitles
        # These broadcasts expire after ~1 month, can find new test URL here:
        # https://www.cbc.ca/player/news/TV%20Shows/The%20National/Latest%20Broadcast
        'url': 'http://www.cbc.ca/player/play/2249992771553',
        'md5': '2f2fb675dd4f0f8a5bb7588d1b13bacd',
        'info_dict': {
            'id': '2249992771553',
            'ext': 'mp4',
            'title': 'The National | Women’s soccer pay, Florida seawater, Swift quake',
            'description': 'md5:adba28011a56cfa47a080ff198dad27a',
            'timestamp': 1690596000,
            'duration': 2716.333,
            'subtitles': {'eng': [{'ext': 'vtt', 'protocol': 'm3u8_native'}]},
            'thumbnail': 'https://thumbnails.cbc.ca/maven_legacy/thumbnails/481/326/thumbnail.jpeg',
            'uploader': 'CBCC-NEW',
            'chapters': 'count:5',
            'upload_date': '20230729',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'url': smuggle_url(
                'http://link.theplatform.com/s/ExhSPC/media/guid/2655402169/%s?mbr=true&formats=MPEG4,FLV,MP3' % video_id, {
                    'force_smil_url': True
                }),
            'id': video_id,
            '_format_sort_fields': ('res', 'proto')  # Prioritize direct http formats over HLS
        }


class CBCPlayerPlaylistIE(InfoExtractor):
    IE_NAME = 'cbc.ca:player:playlist'
    _VALID_URL = r'https?://(?:www\.)?cbc\.ca/(?:player/)(?!play/)(?P<id>[^?#]+)'
    _TESTS = [{
        'url': 'https://www.cbc.ca/player/news/TV%20Shows/The%20National/Latest%20Broadcast',
        'playlist_mincount': 25,
        'info_dict': {
            'id': 'news/tv shows/the national/latest broadcast',
        }
    }, {
        'url': 'https://www.cbc.ca/player/news/Canada/North',
        'playlist_mincount': 25,
        'info_dict': {
            'id': 'news/canada/north',
        }
    }]

    def _real_extract(self, url):
        playlist_id = urllib.parse.unquote(self._match_id(url)).lower()
        webpage = self._download_webpage(url, playlist_id)
        json_content = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', playlist_id)

        def entries():
            for video_id in traverse_obj(json_content, (
                'video', 'clipsByCategory', lambda k, _: k.lower() == playlist_id, 'items', ..., 'id'
            )):
                yield self.url_result(f'https://www.cbc.ca/player/play/{video_id}', CBCPlayerIE)

        return self.playlist_result(entries(), playlist_id)


class CBCGemIE(InfoExtractor):
    IE_NAME = 'gem.cbc.ca'
    _VALID_URL = r'https?://gem\.cbc\.ca/(?:media/)?(?P<id>[0-9a-z-]+/s[0-9]+[a-z][0-9]+)'
    _TESTS = [{
        # This is a normal, public, TV show video
        'url': 'https://gem.cbc.ca/media/schitts-creek/s06e01',
        'md5': '93dbb31c74a8e45b378cf13bd3f6f11e',
        'info_dict': {
            'id': 'schitts-creek/s06e01',
            'ext': 'mp4',
            'title': 'Smoke Signals',
            'description': 'md5:929868d20021c924020641769eb3e7f1',
            'thumbnail': 'https://images.radio-canada.ca/v1/synps-cbc/episode/perso/cbc_schitts_creek_season_06e01_thumbnail_v01.jpg?im=Resize=(Size)',
            'duration': 1314,
            'categories': ['comedy'],
            'series': 'Schitt\'s Creek',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Smoke Signals',
            'episode_number': 1,
            'episode_id': 'schitts-creek/s06e01',
        },
        'params': {'format': 'bv'},
        'skip': 'Geo-restricted to Canada',
    }, {
        # This video requires an account in the browser, but works fine in yt-dlp
        'url': 'https://gem.cbc.ca/media/schitts-creek/s01e01',
        'md5': '297a9600f554f2258aed01514226a697',
        'info_dict': {
            'id': 'schitts-creek/s01e01',
            'ext': 'mp4',
            'title': 'The Cup Runneth Over',
            'description': 'md5:9bca14ea49ab808097530eb05a29e797',
            'thumbnail': 'https://images.radio-canada.ca/v1/synps-cbc/episode/perso/cbc_schitts_creek_season_01e01_thumbnail_v01.jpg?im=Resize=(Size)',
            'series': 'Schitt\'s Creek',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'The Cup Runneth Over',
            'episode_id': 'schitts-creek/s01e01',
            'duration': 1309,
            'categories': ['comedy'],
        },
        'params': {'format': 'bv'},
        'skip': 'Geo-restricted to Canada',
    }, {
        'url': 'https://gem.cbc.ca/nadiyas-family-favourites/s01e01',
        'only_matching': True,
    }]

    _GEO_COUNTRIES = ['CA']
    _TOKEN_API_KEY = '3f4beddd-2061-49b0-ae80-6f1f2ed65b37'
    _NETRC_MACHINE = 'cbcgem'
    _claims_token = None

    def _new_claims_token(self, email, password):
        data = json.dumps({
            'email': email,
            'password': password,
        }).encode()
        headers = {'content-type': 'application/json'}
        query = {'apikey': self._TOKEN_API_KEY}
        resp = self._download_json('https://api.loginradius.com/identity/v2/auth/login',
                                   None, data=data, headers=headers, query=query)
        access_token = resp['access_token']

        query = {
            'access_token': access_token,
            'apikey': self._TOKEN_API_KEY,
            'jwtapp': 'jwt',
        }
        resp = self._download_json('https://cloud-api.loginradius.com/sso/jwt/api/token',
                                   None, headers=headers, query=query)
        sig = resp['signature']

        data = json.dumps({'jwt': sig}).encode()
        headers = {'content-type': 'application/json', 'ott-device-type': 'web'}
        resp = self._download_json('https://services.radio-canada.ca/ott/cbc-api/v2/token',
                                   None, data=data, headers=headers, expected_status=426)
        cbc_access_token = resp['accessToken']

        headers = {'content-type': 'application/json', 'ott-device-type': 'web', 'ott-access-token': cbc_access_token}
        resp = self._download_json('https://services.radio-canada.ca/ott/cbc-api/v2/profile',
                                   None, headers=headers, expected_status=426)
        return resp['claimsToken']

    def _get_claims_token_expiry(self):
        # Token is a JWT
        # JWT is decoded here and 'exp' field is extracted
        # It is a Unix timestamp for when the token expires
        b64_data = self._claims_token.split('.')[1]
        data = base64.urlsafe_b64decode(b64_data + "==")
        return json.loads(data)['exp']

    def claims_token_expired(self):
        exp = self._get_claims_token_expiry()
        if exp - time.time() < 10:
            # It will expire in less than 10 seconds, or has already expired
            return True
        return False

    def claims_token_valid(self):
        return self._claims_token is not None and not self.claims_token_expired()

    def _get_claims_token(self, email, password):
        if not self.claims_token_valid():
            self._claims_token = self._new_claims_token(email, password)
            self.cache.store(self._NETRC_MACHINE, 'claims_token', self._claims_token)
        return self._claims_token

    def _real_initialize(self):
        if self.claims_token_valid():
            return
        self._claims_token = self.cache.load(self._NETRC_MACHINE, 'claims_token')

    def _find_secret_formats(self, formats, video_id):
        """ Find a valid video url and convert it to the secret variant """
        base_format = next((f for f in formats if f.get('vcodec') != 'none'), None)
        if not base_format:
            return

        base_url = re.sub(r'(Manifest\(.*?),filter=[\w-]+(.*?\))', r'\1\2', base_format['url'])
        url = re.sub(r'(Manifest\(.*?),format=[\w-]+(.*?\))', r'\1\2', base_url)

        secret_xml = self._download_xml(url, video_id, note='Downloading secret XML', fatal=False)
        if not secret_xml:
            return

        for child in secret_xml:
            if child.attrib.get('Type') != 'video':
                continue
            for video_quality in child:
                bitrate = int_or_none(video_quality.attrib.get('Bitrate'))
                if not bitrate or 'Index' not in video_quality.attrib:
                    continue
                height = int_or_none(video_quality.attrib.get('MaxHeight'))

                yield {
                    **base_format,
                    'format_id': join_nonempty('sec', height),
                    # Note: \g<1> is necessary instead of \1 since bitrate is a number
                    'url': re.sub(r'(QualityLevels\()\d+(\))', fr'\g<1>{bitrate}\2', base_url),
                    'width': int_or_none(video_quality.attrib.get('MaxWidth')),
                    'tbr': bitrate / 1000.0,
                    'height': height,
                }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(
            f'https://services.radio-canada.ca/ott/cbc-api/v2/assets/{video_id}',
            video_id, expected_status=426)

        email, password = self._get_login_info()
        if email and password:
            claims_token = self._get_claims_token(email, password)
            headers = {'x-claims-token': claims_token}
        else:
            headers = {}
        m3u8_info = self._download_json(video_info['playSession']['url'], video_id, headers=headers)
        m3u8_url = m3u8_info.get('url')

        if m3u8_info.get('errorCode') == 1:
            self.raise_geo_restricted(countries=['CA'])
        elif m3u8_info.get('errorCode') == 35:
            self.raise_login_required(method='password')
        elif m3u8_info.get('errorCode') != 0:
            raise ExtractorError(f'{self.IE_NAME} said: {m3u8_info.get("errorCode")} - {m3u8_info.get("message")}')

        formats = self._extract_m3u8_formats(m3u8_url, video_id, m3u8_id='hls')
        self._remove_duplicate_formats(formats)
        formats.extend(self._find_secret_formats(formats, video_id))

        for format in formats:
            if format.get('vcodec') == 'none':
                if format.get('ext') is None:
                    format['ext'] = 'm4a'
                if format.get('acodec') is None:
                    format['acodec'] = 'mp4a.40.2'

                # Put described audio at the beginning of the list, so that it
                # isn't chosen by default, as most people won't want it.
                if 'descriptive' in format['format_id'].lower():
                    format['preference'] = -2

        return {
            'id': video_id,
            'title': video_info['title'],
            'description': video_info.get('description'),
            'thumbnail': video_info.get('image'),
            'series': video_info.get('series'),
            'season_number': video_info.get('season'),
            'season': f'Season {video_info.get("season")}',
            'episode_number': video_info.get('episode'),
            'episode': video_info.get('title'),
            'episode_id': video_id,
            'duration': video_info.get('duration'),
            'categories': [video_info.get('category')],
            'formats': formats,
            'release_timestamp': video_info.get('airDate'),
            'timestamp': video_info.get('availableDate'),
        }


class CBCGemPlaylistIE(InfoExtractor):
    IE_NAME = 'gem.cbc.ca:playlist'
    _VALID_URL = r'https?://gem\.cbc\.ca/(?:media/)?(?P<id>(?P<show>[0-9a-z-]+)/s(?P<season>[0-9]+))/?(?:[?#]|$)'
    _TESTS = [{
        # TV show playlist, all public videos
        'url': 'https://gem.cbc.ca/media/schitts-creek/s06',
        'playlist_count': 16,
        'info_dict': {
            'id': 'schitts-creek/s06',
            'title': 'Season 6',
            'description': 'md5:6a92104a56cbeb5818cc47884d4326a2',
            'series': 'Schitt\'s Creek',
            'season_number': 6,
            'season': 'Season 6',
            'thumbnail': 'https://images.radio-canada.ca/v1/synps-cbc/season/perso/cbc_schitts_creek_season_06_carousel_v03.jpg?impolicy=ott&im=Resize=(_Size_)&quality=75',
        },
    }, {
        'url': 'https://gem.cbc.ca/schitts-creek/s06',
        'only_matching': True,
    }]
    _API_BASE = 'https://services.radio-canada.ca/ott/cbc-api/v2/shows/'

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        season_id = match.group('id')
        show = match.group('show')
        show_info = self._download_json(self._API_BASE + show, season_id, expected_status=426)
        season = int(match.group('season'))

        season_info = next((s for s in show_info['seasons'] if s.get('season') == season), None)

        if season_info is None:
            raise ExtractorError(f'Couldn\'t find season {season} of {show}')

        episodes = []
        for episode in season_info['assets']:
            episodes.append({
                '_type': 'url_transparent',
                'ie_key': 'CBCGem',
                'url': 'https://gem.cbc.ca/media/' + episode['id'],
                'id': episode['id'],
                'title': episode.get('title'),
                'description': episode.get('description'),
                'thumbnail': episode.get('image'),
                'series': episode.get('series'),
                'season_number': episode.get('season'),
                'season': season_info['title'],
                'season_id': season_info.get('id'),
                'episode_number': episode.get('episode'),
                'episode': episode.get('title'),
                'episode_id': episode['id'],
                'duration': episode.get('duration'),
                'categories': [episode.get('category')],
            })

        thumbnail = None
        tn_uri = season_info.get('image')
        # the-national was observed to use a "data:image/png;base64"
        # URI for their 'image' value. The image was 1x1, and is
        # probably just a placeholder, so it is ignored.
        if tn_uri is not None and not tn_uri.startswith('data:'):
            thumbnail = tn_uri

        return {
            '_type': 'playlist',
            'entries': episodes,
            'id': season_id,
            'title': season_info['title'],
            'description': season_info.get('description'),
            'thumbnail': thumbnail,
            'series': show_info.get('title'),
            'season_number': season_info.get('season'),
            'season': season_info['title'],
        }


class CBCGemLiveIE(InfoExtractor):
    IE_NAME = 'gem.cbc.ca:live'
    _VALID_URL = r'https?://gem\.cbc\.ca/live(?:-event)?/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://gem.cbc.ca/live/920604739687',
            'info_dict': {
                'title': 'Ottawa',
                'description': 'The live TV channel and local programming from Ottawa',
                'thumbnail': 'https://thumbnails.cbc.ca/maven_legacy/thumbnails/CBC_OTT_VMS/Live_Channel_Static_Images/Ottawa_2880x1620.jpg',
                'is_live': True,
                'id': 'AyqZwxRqh8EH',
                'ext': 'mp4',
                'timestamp': 1492106160,
                'upload_date': '20170413',
                'uploader': 'CBCC-NEW',
            },
            'skip': 'Live might have ended',
        },
        {
            'url': 'https://gem.cbc.ca/live/44',
            'info_dict': {
                'id': '44',
                'ext': 'mp4',
                'is_live': True,
                'title': r're:^Ottawa [0-9\-: ]+',
                'description': 'The live TV channel and local programming from Ottawa',
                'live_status': 'is_live',
                'thumbnail': r're:https://images.gem.cbc.ca/v1/cbc-gem/live/.*'
            },
            'params': {'skip_download': True},
            'skip': 'Live might have ended',
        },
        {
            'url': 'https://gem.cbc.ca/live-event/10835',
            'info_dict': {
                'id': '10835',
                'ext': 'mp4',
                'is_live': True,
                'title': r're:^The National \| Biden’s trip wraps up, Paltrow testifies, Bird flu [0-9\-: ]+',
                'description': 'March 24, 2023 | President Biden’s Ottawa visit ends with big pledges from both countries. Plus, Gwyneth Paltrow testifies in her ski collision trial.',
                'live_status': 'is_live',
                'thumbnail': r're:https://images.gem.cbc.ca/v1/cbc-gem/live/.*',
                'timestamp': 1679706000,
                'upload_date': '20230325',
            },
            'params': {'skip_download': True},
            'skip': 'Live might have ended',
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_info = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['data']

        # Two types of metadata JSON
        if not video_info.get('formattedIdMedia'):
            video_info = traverse_obj(
                video_info, (('freeTv', ('streams', ...)), 'items', lambda _, v: v['key'] == video_id, {dict}),
                get_all=False, default={})

        video_stream_id = video_info.get('formattedIdMedia')
        if not video_stream_id:
            raise ExtractorError('Couldn\'t find video metadata, maybe this livestream is now offline', expected=True)

        stream_data = self._download_json(
            'https://services.radio-canada.ca/media/validation/v2/', video_id, query={
                'appCode': 'mpx',
                'connectionType': 'hd',
                'deviceType': 'ipad',
                'idMedia': video_stream_id,
                'multibitrate': 'true',
                'output': 'json',
                'tech': 'hls',
                'manifestType': 'desktop',
            })

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(stream_data['url'], video_id, 'mp4', live=True),
            'is_live': True,
            **traverse_obj(video_info, {
                'title': 'title',
                'description': 'description',
                'thumbnail': ('images', 'card', 'url'),
                'timestamp': ('airDate', {parse_iso8601}),
            })
        }

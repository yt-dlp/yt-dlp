import base64
import calendar
import collections
import copy
import datetime as dt
import enum
import functools
import hashlib
import itertools
import json
import math
import os.path
import random
import re
import shlex
import sys
import threading
import time
import traceback
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from .openload import PhantomJSwrapper
from ..jsinterp import JSInterpreter
from ..networking.exceptions import HTTPError, network_exceptions
from ..utils import (
    NO_DEFAULT,
    ExtractorError,
    LazyList,
    UserNotLive,
    bug_reports_message,
    classproperty,
    clean_html,
    datetime_from_str,
    dict_get,
    filesize_from_tbr,
    filter_dict,
    float_or_none,
    format_field,
    get_first,
    int_or_none,
    is_html,
    join_nonempty,
    js_to_json,
    mimetype2ext,
    orderedSet,
    parse_codecs,
    parse_count,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    remove_start,
    smuggle_url,
    str_or_none,
    str_to_int,
    strftime_or_none,
    traverse_obj,
    try_call,
    try_get,
    unescapeHTML,
    unified_strdate,
    unified_timestamp,
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urljoin,
    variadic,
)

STREAMING_DATA_CLIENT_NAME = '__yt_dlp_client'
# any clients starting with _ cannot be explicitly requested by the user
INNERTUBE_CLIENTS = {
    'web': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20240726.00.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 1,
    },
    # Safari UA returns pre-merged video+audio 144p/240p/360p/720p/1080p HLS formats
    'web_safari': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20240726.00.00',
                'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15,gzip(gfe)',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 1,
    },
    'web_embedded': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_EMBEDDED_PLAYER',
                'clientVersion': '1.20240723.01.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 56,
    },
    'web_music': {
        'INNERTUBE_HOST': 'music.youtube.com',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '1.20240724.00.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 67,
    },
    'web_creator': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_CREATOR',
                'clientVersion': '1.20240723.03.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 62,
    },
    'android': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '19.29.37',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.youtube/19.29.37 (Linux; U; Android 11) gzip',
                'osName': 'Android',
                'osVersion': '11',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 3,
        'REQUIRE_JS_PLAYER': False,
    },
    'android_music': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_MUSIC',
                'clientVersion': '7.11.50',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.apps.youtube.music/7.11.50 (Linux; U; Android 11) gzip',
                'osName': 'Android',
                'osVersion': '11',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 21,
        'REQUIRE_JS_PLAYER': False,
    },
    'android_creator': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_CREATOR',
                'clientVersion': '24.30.100',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.apps.youtube.creator/24.30.100 (Linux; U; Android 11) gzip',
                'osName': 'Android',
                'osVersion': '11',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 14,
        'REQUIRE_JS_PLAYER': False,
    },
    # YouTube Kids videos aren't returned on this client for some reason
    'android_vr': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_VR',
                'clientVersion': '1.57.29',
                'deviceMake': 'Oculus',
                'deviceModel': 'Quest 3',
                'androidSdkVersion': 32,
                'userAgent': 'com.google.android.apps.youtube.vr.oculus/1.57.29 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip',
                'osName': 'Android',
                'osVersion': '12L',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 28,
        'REQUIRE_JS_PLAYER': False,
    },
    'android_testsuite': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_TESTSUITE',
                'clientVersion': '1.9',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.youtube/1.9 (Linux; U; Android 11) gzip',
                'osName': 'Android',
                'osVersion': '11',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 30,
        'REQUIRE_JS_PLAYER': False,
        'PLAYER_PARAMS': '2AMB',
    },
    # This client only has legacy formats and storyboards
    'android_producer': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_PRODUCER',
                'clientVersion': '0.111.1',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.apps.youtube.producer/0.111.1 (Linux; U; Android 11) gzip',
                'osName': 'Android',
                'osVersion': '11',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 91,
        'REQUIRE_JS_PLAYER': False,
    },
    # iOS clients have HLS live streams. Setting device model to get 60fps formats.
    # See: https://github.com/TeamNewPipe/NewPipeExtractor/issues/680#issuecomment-1002724558
    'ios': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS',
                'clientVersion': '19.29.1',
                'deviceMake': 'Apple',
                'deviceModel': 'iPhone16,2',
                'userAgent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
                'osName': 'iPhone',
                'osVersion': '17.5.1.21F90',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 5,
        'REQUIRE_JS_PLAYER': False,
    },
    'ios_music': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS_MUSIC',
                'clientVersion': '7.08.2',
                'deviceMake': 'Apple',
                'deviceModel': 'iPhone16,2',
                'userAgent': 'com.google.ios.youtubemusic/7.08.2 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
                'osName': 'iPhone',
                'osVersion': '17.5.1.21F90',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 26,
        'REQUIRE_JS_PLAYER': False,
    },
    'ios_creator': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS_CREATOR',
                'clientVersion': '24.30.100',
                'deviceMake': 'Apple',
                'deviceModel': 'iPhone16,2',
                'userAgent': 'com.google.ios.ytcreator/24.30.100 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
                'osName': 'iPhone',
                'osVersion': '17.5.1.21F90',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 15,
        'REQUIRE_JS_PLAYER': False,
    },
    # mweb has 'ultralow' formats
    # See: https://github.com/yt-dlp/yt-dlp/pull/557
    'mweb': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'MWEB',
                'clientVersion': '2.20240726.01.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 2,
    },
    'tv': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'TVHTML5',
                'clientVersion': '7.20240724.13.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 7,
    },
    # This client can access age restricted videos (unless the uploader has disabled the 'allow embedding' option)
    # See: https://github.com/zerodytrash/YouTube-Internal-Clients
    'tv_embedded': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                'clientVersion': '2.0',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 85,
    },
    # This client has pre-merged video+audio 720p/1080p streams
    'mediaconnect': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'MEDIA_CONNECT_FRONTEND',
                'clientVersion': '0.1',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 95,
        'REQUIRE_JS_PLAYER': False,
    },
}


def _split_innertube_client(client_name):
    variant, *base = client_name.rsplit('.', 1)
    if base:
        return variant, base[0], variant
    base, *variant = client_name.split('_', 1)
    return client_name, base, variant[0] if variant else None


def short_client_name(client_name):
    main, *parts = _split_innertube_client(client_name)[0].split('_')
    return join_nonempty(main[:4], ''.join(x[0] for x in parts)).upper()


def build_innertube_clients():
    THIRD_PARTY = {
        'embedUrl': 'https://www.youtube.com/',  # Can be any valid URL
    }
    BASE_CLIENTS = ('ios', 'web', 'tv', 'mweb', 'android')
    priority = qualities(BASE_CLIENTS[::-1])

    for client, ytcfg in tuple(INNERTUBE_CLIENTS.items()):
        ytcfg.setdefault('INNERTUBE_HOST', 'www.youtube.com')
        ytcfg.setdefault('REQUIRE_JS_PLAYER', True)
        ytcfg.setdefault('PLAYER_PARAMS', None)
        ytcfg['INNERTUBE_CONTEXT']['client'].setdefault('hl', 'en')

        _, base_client, variant = _split_innertube_client(client)
        ytcfg['priority'] = 10 * priority(base_client)

        if variant == 'embedded':
            ytcfg['INNERTUBE_CONTEXT']['thirdParty'] = THIRD_PARTY
            ytcfg['priority'] -= 2
        elif variant:
            ytcfg['priority'] -= 3


build_innertube_clients()


class BadgeType(enum.Enum):
    AVAILABILITY_UNLISTED = enum.auto()
    AVAILABILITY_PRIVATE = enum.auto()
    AVAILABILITY_PUBLIC = enum.auto()
    AVAILABILITY_PREMIUM = enum.auto()
    AVAILABILITY_SUBSCRIPTION = enum.auto()
    LIVE_NOW = enum.auto()
    VERIFIED = enum.auto()


class YoutubeBaseInfoExtractor(InfoExtractor):
    """Provide base functions for Youtube extractors"""

    _RESERVED_NAMES = (
        r'channel|c|user|playlist|watch|w|v|embed|e|live|watch_popup|clip|'
        r'shorts|movies|results|search|shared|hashtag|trending|explore|feed|feeds|'
        r'browse|oembed|get_video_info|iframe_api|s/player|source|'
        r'storefront|oops|index|account|t/terms|about|upload|signin|logout')

    _PLAYLIST_ID_RE = r'(?:(?:PL|LL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)[0-9A-Za-z-_]{10,}|RDMM|WL|LL|LM)'

    # _NETRC_MACHINE = 'youtube'

    # If True it will raise an error if no login info is provided
    _LOGIN_REQUIRED = False

    _INVIDIOUS_SITES = (
        # invidious-redirect websites
        r'(?:www\.)?redirect\.invidious\.io',
        r'(?:(?:www|dev)\.)?invidio\.us',
        # Invidious instances taken from https://github.com/iv-org/documentation/blob/master/docs/instances.md
        r'(?:www\.)?invidious\.pussthecat\.org',
        r'(?:www\.)?invidious\.zee\.li',
        r'(?:www\.)?invidious\.ethibox\.fr',
        r'(?:www\.)?iv\.ggtyler\.dev',
        r'(?:www\.)?inv\.vern\.i2p',
        r'(?:www\.)?am74vkcrjp2d5v36lcdqgsj2m6x36tbrkhsruoegwfcizzabnfgf5zyd\.onion',
        r'(?:www\.)?inv\.riverside\.rocks',
        r'(?:www\.)?invidious\.silur\.me',
        r'(?:www\.)?inv\.bp\.projectsegfau\.lt',
        r'(?:www\.)?invidious\.g4c3eya4clenolymqbpgwz3q3tawoxw56yhzk4vugqrl6dtu3ejvhjid\.onion',
        r'(?:www\.)?invidious\.slipfox\.xyz',
        r'(?:www\.)?invidious\.esmail5pdn24shtvieloeedh7ehz3nrwcdivnfhfcedl7gf4kwddhkqd\.onion',
        r'(?:www\.)?inv\.vernccvbvyi5qhfzyqengccj7lkove6bjot2xhh5kajhwvidqafczrad\.onion',
        r'(?:www\.)?invidious\.tiekoetter\.com',
        r'(?:www\.)?iv\.odysfvr23q5wgt7i456o5t3trw2cw5dgn56vbjfbq2m7xsc5vqbqpcyd\.onion',
        r'(?:www\.)?invidious\.nerdvpn\.de',
        r'(?:www\.)?invidious\.weblibre\.org',
        r'(?:www\.)?inv\.odyssey346\.dev',
        r'(?:www\.)?invidious\.dhusch\.de',
        r'(?:www\.)?iv\.melmac\.space',
        r'(?:www\.)?watch\.thekitty\.zone',
        r'(?:www\.)?invidious\.privacydev\.net',
        r'(?:www\.)?ng27owmagn5amdm7l5s3rsqxwscl5ynppnis5dqcasogkyxcfqn7psid\.onion',
        r'(?:www\.)?invidious\.drivet\.xyz',
        r'(?:www\.)?vid\.priv\.au',
        r'(?:www\.)?euxxcnhsynwmfidvhjf6uzptsmh4dipkmgdmcmxxuo7tunp3ad2jrwyd\.onion',
        r'(?:www\.)?inv\.vern\.cc',
        r'(?:www\.)?invidious\.esmailelbob\.xyz',
        r'(?:www\.)?invidious\.sethforprivacy\.com',
        r'(?:www\.)?yt\.oelrichsgarcia\.de',
        r'(?:www\.)?yt\.artemislena\.eu',
        r'(?:www\.)?invidious\.flokinet\.to',
        r'(?:www\.)?invidious\.baczek\.me',
        r'(?:www\.)?y\.com\.sb',
        r'(?:www\.)?invidious\.epicsite\.xyz',
        r'(?:www\.)?invidious\.lidarshield\.cloud',
        r'(?:www\.)?yt\.funami\.tech',
        r'(?:www\.)?invidious\.3o7z6yfxhbw7n3za4rss6l434kmv55cgw2vuziwuigpwegswvwzqipyd\.onion',
        r'(?:www\.)?osbivz6guyeahrwp2lnwyjk2xos342h4ocsxyqrlaopqjuhwn2djiiyd\.onion',
        r'(?:www\.)?u2cvlit75owumwpy4dj2hsmvkq7nvrclkpht7xgyye2pyoxhpmclkrad\.onion',
        # youtube-dl invidious instances list
        r'(?:(?:www|no)\.)?invidiou\.sh',
        r'(?:(?:www|fi)\.)?invidious\.snopyta\.org',
        r'(?:www\.)?invidious\.kabi\.tk',
        r'(?:www\.)?invidious\.mastodon\.host',
        r'(?:www\.)?invidious\.zapashcanon\.fr',
        r'(?:www\.)?(?:invidious(?:-us)?|piped)\.kavin\.rocks',
        r'(?:www\.)?invidious\.tinfoil-hat\.net',
        r'(?:www\.)?invidious\.himiko\.cloud',
        r'(?:www\.)?invidious\.reallyancient\.tech',
        r'(?:www\.)?invidious\.tube',
        r'(?:www\.)?invidiou\.site',
        r'(?:www\.)?invidious\.site',
        r'(?:www\.)?invidious\.xyz',
        r'(?:www\.)?invidious\.nixnet\.xyz',
        r'(?:www\.)?invidious\.048596\.xyz',
        r'(?:www\.)?invidious\.drycat\.fr',
        r'(?:www\.)?inv\.skyn3t\.in',
        r'(?:www\.)?tube\.poal\.co',
        r'(?:www\.)?tube\.connect\.cafe',
        r'(?:www\.)?vid\.wxzm\.sx',
        r'(?:www\.)?vid\.mint\.lgbt',
        r'(?:www\.)?vid\.puffyan\.us',
        r'(?:www\.)?yewtu\.be',
        r'(?:www\.)?yt\.elukerio\.org',
        r'(?:www\.)?yt\.lelux\.fi',
        r'(?:www\.)?invidious\.ggc-project\.de',
        r'(?:www\.)?yt\.maisputain\.ovh',
        r'(?:www\.)?ytprivate\.com',
        r'(?:www\.)?invidious\.13ad\.de',
        r'(?:www\.)?invidious\.toot\.koeln',
        r'(?:www\.)?invidious\.fdn\.fr',
        r'(?:www\.)?watch\.nettohikari\.com',
        r'(?:www\.)?invidious\.namazso\.eu',
        r'(?:www\.)?invidious\.silkky\.cloud',
        r'(?:www\.)?invidious\.exonip\.de',
        r'(?:www\.)?invidious\.riverside\.rocks',
        r'(?:www\.)?invidious\.blamefran\.net',
        r'(?:www\.)?invidious\.moomoo\.de',
        r'(?:www\.)?ytb\.trom\.tf',
        r'(?:www\.)?yt\.cyberhost\.uk',
        r'(?:www\.)?kgg2m7yk5aybusll\.onion',
        r'(?:www\.)?qklhadlycap4cnod\.onion',
        r'(?:www\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\.onion',
        r'(?:www\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\.onion',
        r'(?:www\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\.onion',
        r'(?:www\.)?invidious\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\.onion',
        r'(?:www\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\.b32\.i2p',
        r'(?:www\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\.onion',
        r'(?:www\.)?w6ijuptxiku4xpnnaetxvnkc5vqcdu7mgns2u77qefoixi63vbvnpnqd\.onion',
        r'(?:www\.)?kbjggqkzv65ivcqj6bumvp337z6264huv5kpkwuv6gu5yjiskvan7fad\.onion',
        r'(?:www\.)?grwp24hodrefzvjjuccrkw3mjq4tzhaaq32amf33dzpmuxe7ilepcmad\.onion',
        r'(?:www\.)?hpniueoejy4opn7bc4ftgazyqjoeqwlvh2uiku2xqku6zpoa4bf5ruid\.onion',
        # piped instances from https://github.com/TeamPiped/Piped/wiki/Instances
        r'(?:www\.)?piped\.kavin\.rocks',
        r'(?:www\.)?piped\.tokhmi\.xyz',
        r'(?:www\.)?piped\.syncpundit\.io',
        r'(?:www\.)?piped\.mha\.fi',
        r'(?:www\.)?watch\.whatever\.social',
        r'(?:www\.)?piped\.garudalinux\.org',
        r'(?:www\.)?piped\.rivo\.lol',
        r'(?:www\.)?piped-libre\.kavin\.rocks',
        r'(?:www\.)?yt\.jae\.fi',
        r'(?:www\.)?piped\.mint\.lgbt',
        r'(?:www\.)?il\.ax',
        r'(?:www\.)?piped\.esmailelbob\.xyz',
        r'(?:www\.)?piped\.projectsegfau\.lt',
        r'(?:www\.)?piped\.privacydev\.net',
        r'(?:www\.)?piped\.palveluntarjoaja\.eu',
        r'(?:www\.)?piped\.smnz\.de',
        r'(?:www\.)?piped\.adminforge\.de',
        r'(?:www\.)?watch\.whatevertinfoil\.de',
        r'(?:www\.)?piped\.qdi\.fi',
        r'(?:(?:www|cf)\.)?piped\.video',
        r'(?:www\.)?piped\.aeong\.one',
        r'(?:www\.)?piped\.moomoo\.me',
        r'(?:www\.)?piped\.chauvet\.pro',
        r'(?:www\.)?watch\.leptons\.xyz',
        r'(?:www\.)?pd\.vern\.cc',
        r'(?:www\.)?piped\.hostux\.net',
        r'(?:www\.)?piped\.lunar\.icu',
        # Hyperpipe instances from https://hyperpipe.codeberg.page/
        r'(?:www\.)?hyperpipe\.surge\.sh',
        r'(?:www\.)?hyperpipe\.esmailelbob\.xyz',
        r'(?:www\.)?listen\.whatever\.social',
        r'(?:www\.)?music\.adminforge\.de',
    )

    # extracted from account/account_menu ep
    # XXX: These are the supported YouTube UI and API languages,
    # which is slightly different from languages supported for translation in YouTube studio
    _SUPPORTED_LANG_CODES = [
        'af', 'az', 'id', 'ms', 'bs', 'ca', 'cs', 'da', 'de', 'et', 'en-IN', 'en-GB', 'en', 'es',
        'es-419', 'es-US', 'eu', 'fil', 'fr', 'fr-CA', 'gl', 'hr', 'zu', 'is', 'it', 'sw', 'lv',
        'lt', 'hu', 'nl', 'no', 'uz', 'pl', 'pt-PT', 'pt', 'ro', 'sq', 'sk', 'sl', 'sr-Latn', 'fi',
        'sv', 'vi', 'tr', 'be', 'bg', 'ky', 'kk', 'mk', 'mn', 'ru', 'sr', 'uk', 'el', 'hy', 'iw',
        'ur', 'ar', 'fa', 'ne', 'mr', 'hi', 'as', 'bn', 'pa', 'gu', 'or', 'ta', 'te', 'kn', 'ml',
        'si', 'th', 'lo', 'my', 'ka', 'am', 'km', 'zh-CN', 'zh-TW', 'zh-HK', 'ja', 'ko',
    ]

    _IGNORED_WARNINGS = {
        'Unavailable videos will be hidden during playback',
        'Unavailable videos are hidden',
    }

    _YT_HANDLE_RE = r'@[\w.-]{3,30}'  # https://support.google.com/youtube/answer/11585688?hl=en
    _YT_CHANNEL_UCID_RE = r'UC[\w-]{22}'

    def ucid_or_none(self, ucid):
        return self._search_regex(rf'^({self._YT_CHANNEL_UCID_RE})$', ucid, 'UC-id', default=None)

    def handle_or_none(self, handle):
        return self._search_regex(rf'^({self._YT_HANDLE_RE})$', handle, '@-handle', default=None)

    def handle_from_url(self, url):
        return self._search_regex(rf'^(?:https?://(?:www\.)?youtube\.com)?/({self._YT_HANDLE_RE})',
                                  url, 'channel handle', default=None)

    def ucid_from_url(self, url):
        return self._search_regex(rf'^(?:https?://(?:www\.)?youtube\.com)?/({self._YT_CHANNEL_UCID_RE})',
                                  url, 'channel id', default=None)

    @functools.cached_property
    def _preferred_lang(self):
        """
        Returns a language code supported by YouTube for the user preferred language.
        Returns None if no preferred language set.
        """
        preferred_lang = self._configuration_arg('lang', ie_key='Youtube', casesense=True, default=[''])[0]
        if not preferred_lang:
            return
        if preferred_lang not in self._SUPPORTED_LANG_CODES:
            raise ExtractorError(
                f'Unsupported language code: {preferred_lang}. Supported language codes (case-sensitive): {join_nonempty(*self._SUPPORTED_LANG_CODES, delim=", ")}.',
                expected=True)
        elif preferred_lang != 'en':
            self.report_warning(
                f'Preferring "{preferred_lang}" translated fields. Note that some metadata extraction may fail or be incorrect.')
        return preferred_lang

    def _initialize_consent(self):
        cookies = self._get_cookies('https://www.youtube.com/')
        if cookies.get('__Secure-3PSID'):
            return
        socs = cookies.get('SOCS')
        if socs and not socs.value.startswith('CAA'):  # not consented
            return
        self._set_cookie('.youtube.com', 'SOCS', 'CAI', secure=True)  # accept all (required for mixes)

    def _initialize_pref(self):
        cookies = self._get_cookies('https://www.youtube.com/')
        pref_cookie = cookies.get('PREF')
        pref = {}
        if pref_cookie:
            try:
                pref = dict(urllib.parse.parse_qsl(pref_cookie.value))
            except ValueError:
                self.report_warning('Failed to parse user PREF cookie' + bug_reports_message())
        pref.update({'hl': self._preferred_lang or 'en', 'tz': 'UTC'})
        self._set_cookie('.youtube.com', name='PREF', value=urllib.parse.urlencode(pref))

    def _real_initialize(self):
        self._initialize_pref()
        self._initialize_consent()
        self._check_login_required()

    def _check_login_required(self):
        if self._LOGIN_REQUIRED and not self._cookies_passed:
            self.raise_login_required('Login details are needed to download this content', method='cookies')

    _YT_INITIAL_DATA_RE = r'(?:window\s*\[\s*["\']ytInitialData["\']\s*\]|ytInitialData)\s*='
    _YT_INITIAL_PLAYER_RESPONSE_RE = r'ytInitialPlayerResponse\s*='

    def _get_default_ytcfg(self, client='web'):
        return copy.deepcopy(INNERTUBE_CLIENTS[client])

    def _get_innertube_host(self, client='web'):
        return INNERTUBE_CLIENTS[client]['INNERTUBE_HOST']

    def _ytcfg_get_safe(self, ytcfg, getter, expected_type=None, default_client='web'):
        # try_get but with fallback to default ytcfg client values when present
        _func = lambda y: try_get(y, getter, expected_type)
        return _func(ytcfg) or _func(self._get_default_ytcfg(default_client))

    def _extract_client_name(self, ytcfg, default_client='web'):
        return self._ytcfg_get_safe(
            ytcfg, (lambda x: x['INNERTUBE_CLIENT_NAME'],
                    lambda x: x['INNERTUBE_CONTEXT']['client']['clientName']), str, default_client)

    def _extract_client_version(self, ytcfg, default_client='web'):
        return self._ytcfg_get_safe(
            ytcfg, (lambda x: x['INNERTUBE_CLIENT_VERSION'],
                    lambda x: x['INNERTUBE_CONTEXT']['client']['clientVersion']), str, default_client)

    def _select_api_hostname(self, req_api_hostname, default_client=None):
        return (self._configuration_arg('innertube_host', [''], ie_key=YoutubeIE.ie_key())[0]
                or req_api_hostname or self._get_innertube_host(default_client or 'web'))

    def _extract_context(self, ytcfg=None, default_client='web'):
        context = get_first(
            (ytcfg, self._get_default_ytcfg(default_client)), 'INNERTUBE_CONTEXT', expected_type=dict)
        # Enforce language and tz for extraction
        client_context = traverse_obj(context, 'client', expected_type=dict, default={})
        client_context.update({'hl': self._preferred_lang or 'en', 'timeZone': 'UTC', 'utcOffsetMinutes': 0})
        return context

    _SAPISID = None

    def _generate_sapisidhash_header(self, origin='https://www.youtube.com'):
        time_now = round(time.time())
        if self._SAPISID is None:
            yt_cookies = self._get_cookies('https://www.youtube.com')
            # Sometimes SAPISID cookie isn't present but __Secure-3PAPISID is.
            # See: https://github.com/yt-dlp/yt-dlp/issues/393
            sapisid_cookie = dict_get(
                yt_cookies, ('__Secure-3PAPISID', 'SAPISID'))
            if sapisid_cookie and sapisid_cookie.value:
                self._SAPISID = sapisid_cookie.value
                self.write_debug('Extracted SAPISID cookie')
                # SAPISID cookie is required if not already present
                if not yt_cookies.get('SAPISID'):
                    self.write_debug('Copying __Secure-3PAPISID cookie to SAPISID cookie')
                    self._set_cookie(
                        '.youtube.com', 'SAPISID', self._SAPISID, secure=True, expire_time=time_now + 3600)
            else:
                self._SAPISID = False
        if not self._SAPISID:
            return None
        # SAPISIDHASH algorithm from https://stackoverflow.com/a/32065323
        sapisidhash = hashlib.sha1(
            f'{time_now} {self._SAPISID} {origin}'.encode()).hexdigest()
        return f'SAPISIDHASH {time_now}_{sapisidhash}'

    def _call_api(self, ep, query, video_id, fatal=True, headers=None,
                  note='Downloading API JSON', errnote='Unable to download API page',
                  context=None, api_key=None, api_hostname=None, default_client='web'):

        data = {'context': context} if context else {'context': self._extract_context(default_client=default_client)}
        data.update(query)
        real_headers = self.generate_api_headers(default_client=default_client)
        real_headers.update({'content-type': 'application/json'})
        if headers:
            real_headers.update(headers)
        return self._download_json(
            f'https://{self._select_api_hostname(api_hostname, default_client)}/youtubei/v1/{ep}',
            video_id=video_id, fatal=fatal, note=note, errnote=errnote,
            data=json.dumps(data).encode('utf8'), headers=real_headers,
            query=filter_dict({
                'key': self._configuration_arg(
                    'innertube_key', [api_key], ie_key=YoutubeIE.ie_key(), casesense=True)[0],
                'prettyPrint': 'false',
            }, cndn=lambda _, v: v))

    def extract_yt_initial_data(self, item_id, webpage, fatal=True):
        return self._search_json(self._YT_INITIAL_DATA_RE, webpage, 'yt initial data', item_id, fatal=fatal)

    @staticmethod
    def _extract_session_index(*data):
        """
        Index of current account in account list.
        See: https://github.com/yt-dlp/yt-dlp/pull/519
        """
        for ytcfg in data:
            session_index = int_or_none(try_get(ytcfg, lambda x: x['SESSION_INDEX']))
            if session_index is not None:
                return session_index

    # Deprecated?
    def _extract_identity_token(self, ytcfg=None, webpage=None):
        if ytcfg:
            token = try_get(ytcfg, lambda x: x['ID_TOKEN'], str)
            if token:
                return token
        if webpage:
            return self._search_regex(
                r'\bID_TOKEN["\']\s*:\s*["\'](.+?)["\']', webpage,
                'identity token', default=None, fatal=False)

    @staticmethod
    def _extract_account_syncid(*args):
        """
        Extract syncId required to download private playlists of secondary channels
        @params response and/or ytcfg
        """
        for data in args:
            # ytcfg includes channel_syncid if on secondary channel
            delegated_sid = try_get(data, lambda x: x['DELEGATED_SESSION_ID'], str)
            if delegated_sid:
                return delegated_sid
            sync_ids = (try_get(
                data, (lambda x: x['responseContext']['mainAppWebResponseContext']['datasyncId'],
                       lambda x: x['DATASYNC_ID']), str) or '').split('||')
            if len(sync_ids) >= 2 and sync_ids[1]:
                # datasyncid is of the form "channel_syncid||user_syncid" for secondary channel
                # and just "user_syncid||" for primary channel. We only want the channel_syncid
                return sync_ids[0]

    @staticmethod
    def _extract_visitor_data(*args):
        """
        Extracts visitorData from an API response or ytcfg
        Appears to be used to track session state
        """
        return get_first(
            args, [('VISITOR_DATA', ('INNERTUBE_CONTEXT', 'client', 'visitorData'), ('responseContext', 'visitorData'))],
            expected_type=str)

    @functools.cached_property
    def is_authenticated(self):
        return bool(self._generate_sapisidhash_header())

    def extract_ytcfg(self, video_id, webpage):
        if not webpage:
            return {}
        return self._parse_json(
            self._search_regex(
                r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', webpage, 'ytcfg',
                default='{}'), video_id, fatal=False) or {}

    def generate_api_headers(
            self, *, ytcfg=None, account_syncid=None, session_index=None,
            visitor_data=None, identity_token=None, api_hostname=None, default_client='web'):

        origin = 'https://' + (self._select_api_hostname(api_hostname, default_client))
        headers = {
            'X-YouTube-Client-Name': str(
                self._ytcfg_get_safe(ytcfg, lambda x: x['INNERTUBE_CONTEXT_CLIENT_NAME'], default_client=default_client)),
            'X-YouTube-Client-Version': self._extract_client_version(ytcfg, default_client),
            'Origin': origin,
            'X-Youtube-Identity-Token': identity_token or self._extract_identity_token(ytcfg),
            'X-Goog-PageId': account_syncid or self._extract_account_syncid(ytcfg),
            'X-Goog-Visitor-Id': visitor_data or self._extract_visitor_data(ytcfg),
            'User-Agent': self._ytcfg_get_safe(ytcfg, lambda x: x['INNERTUBE_CONTEXT']['client']['userAgent'], default_client=default_client),
        }
        if session_index is None:
            session_index = self._extract_session_index(ytcfg)
        if account_syncid or session_index is not None:
            headers['X-Goog-AuthUser'] = session_index if session_index is not None else 0

        auth = self._generate_sapisidhash_header(origin)
        if auth is not None:
            headers['Authorization'] = auth
            headers['X-Origin'] = origin
        return filter_dict(headers)

    def _download_ytcfg(self, client, video_id):
        url = {
            'web': 'https://www.youtube.com',
            'web_music': 'https://music.youtube.com',
            'web_embedded': f'https://www.youtube.com/embed/{video_id}?html5=1',
        }.get(client)
        if not url:
            return {}
        webpage = self._download_webpage(
            url, video_id, fatal=False, note=f'Downloading {client.replace("_", " ").strip()} client config')
        return self.extract_ytcfg(video_id, webpage) or {}

    @staticmethod
    def _build_api_continuation_query(continuation, ctp=None):
        query = {
            'continuation': continuation,
        }
        # TODO: Inconsistency with clickTrackingParams.
        # Currently we have a fixed ctp contained within context (from ytcfg)
        # and a ctp in root query for continuation.
        if ctp:
            query['clickTracking'] = {'clickTrackingParams': ctp}
        return query

    @classmethod
    def _extract_next_continuation_data(cls, renderer):
        next_continuation = try_get(
            renderer, (lambda x: x['continuations'][0]['nextContinuationData'],
                       lambda x: x['continuation']['reloadContinuationData']), dict)
        if not next_continuation:
            return
        continuation = next_continuation.get('continuation')
        if not continuation:
            return
        ctp = next_continuation.get('clickTrackingParams')
        return cls._build_api_continuation_query(continuation, ctp)

    @classmethod
    def _extract_continuation_ep_data(cls, continuation_ep: dict):
        if isinstance(continuation_ep, dict):
            continuation = try_get(
                continuation_ep, lambda x: x['continuationCommand']['token'], str)
            if not continuation:
                return
            ctp = continuation_ep.get('clickTrackingParams')
            return cls._build_api_continuation_query(continuation, ctp)

    @classmethod
    def _extract_continuation(cls, renderer):
        next_continuation = cls._extract_next_continuation_data(renderer)
        if next_continuation:
            return next_continuation

        return traverse_obj(renderer, (
            ('contents', 'items', 'rows'), ..., 'continuationItemRenderer',
            ('continuationEndpoint', ('button', 'buttonRenderer', 'command')),
        ), get_all=False, expected_type=cls._extract_continuation_ep_data)

    @classmethod
    def _extract_alerts(cls, data):
        for alert_dict in try_get(data, lambda x: x['alerts'], list) or []:
            if not isinstance(alert_dict, dict):
                continue
            for alert in alert_dict.values():
                alert_type = alert.get('type')
                if not alert_type:
                    continue
                message = cls._get_text(alert, 'text')
                if message:
                    yield alert_type, message

    def _report_alerts(self, alerts, expected=True, fatal=True, only_once=False):
        errors, warnings = [], []
        for alert_type, alert_message in alerts:
            if alert_type.lower() == 'error' and fatal:
                errors.append([alert_type, alert_message])
            elif alert_message not in self._IGNORED_WARNINGS:
                warnings.append([alert_type, alert_message])

        for alert_type, alert_message in (warnings + errors[:-1]):
            self.report_warning(f'YouTube said: {alert_type} - {alert_message}', only_once=only_once)
        if errors:
            raise ExtractorError(f'YouTube said: {errors[-1][1]}', expected=expected)

    def _extract_and_report_alerts(self, data, *args, **kwargs):
        return self._report_alerts(self._extract_alerts(data), *args, **kwargs)

    def _extract_badges(self, badge_list: list):
        """
        Extract known BadgeType's from a list of badge renderers.
        @returns [{'type': BadgeType}]
        """
        icon_type_map = {
            'PRIVACY_UNLISTED': BadgeType.AVAILABILITY_UNLISTED,
            'PRIVACY_PRIVATE': BadgeType.AVAILABILITY_PRIVATE,
            'PRIVACY_PUBLIC': BadgeType.AVAILABILITY_PUBLIC,
            'CHECK_CIRCLE_THICK': BadgeType.VERIFIED,
            'OFFICIAL_ARTIST_BADGE': BadgeType.VERIFIED,
            'CHECK': BadgeType.VERIFIED,
        }

        badge_style_map = {
            'BADGE_STYLE_TYPE_MEMBERS_ONLY': BadgeType.AVAILABILITY_SUBSCRIPTION,
            'BADGE_STYLE_TYPE_PREMIUM': BadgeType.AVAILABILITY_PREMIUM,
            'BADGE_STYLE_TYPE_LIVE_NOW': BadgeType.LIVE_NOW,
            'BADGE_STYLE_TYPE_VERIFIED': BadgeType.VERIFIED,
            'BADGE_STYLE_TYPE_VERIFIED_ARTIST': BadgeType.VERIFIED,
        }

        label_map = {
            'unlisted': BadgeType.AVAILABILITY_UNLISTED,
            'private': BadgeType.AVAILABILITY_PRIVATE,
            'members only': BadgeType.AVAILABILITY_SUBSCRIPTION,
            'live': BadgeType.LIVE_NOW,
            'premium': BadgeType.AVAILABILITY_PREMIUM,
            'verified': BadgeType.VERIFIED,
            'official artist channel': BadgeType.VERIFIED,
        }

        badges = []
        for badge in traverse_obj(badge_list, (..., lambda key, _: re.search(r'[bB]adgeRenderer$', key))):
            badge_type = (
                icon_type_map.get(traverse_obj(badge, ('icon', 'iconType'), expected_type=str))
                or badge_style_map.get(traverse_obj(badge, 'style'))
            )
            if badge_type:
                badges.append({'type': badge_type})
                continue

            # fallback, won't work in some languages
            label = traverse_obj(
                badge, 'label', ('accessibilityData', 'label'), 'tooltip', 'iconTooltip', get_all=False, expected_type=str, default='')
            for match, label_badge_type in label_map.items():
                if match in label.lower():
                    badges.append({'type': label_badge_type})
                    break

        return badges

    @staticmethod
    def _has_badge(badges, badge_type):
        return bool(traverse_obj(badges, lambda _, v: v['type'] == badge_type))

    @staticmethod
    def _get_text(data, *path_list, max_runs=None):
        for path in path_list or [None]:
            if path is None:
                obj = [data]
            else:
                obj = traverse_obj(data, path, default=[])
                if not any(key is ... or isinstance(key, (list, tuple)) for key in variadic(path)):
                    obj = [obj]
            for item in obj:
                text = try_get(item, lambda x: x['simpleText'], str)
                if text:
                    return text
                runs = try_get(item, lambda x: x['runs'], list) or []
                if not runs and isinstance(item, list):
                    runs = item

                runs = runs[:min(len(runs), max_runs or len(runs))]
                text = ''.join(traverse_obj(runs, (..., 'text'), expected_type=str))
                if text:
                    return text

    def _get_count(self, data, *path_list):
        count_text = self._get_text(data, *path_list) or ''
        count = parse_count(count_text)
        if count is None:
            count = str_to_int(
                self._search_regex(r'^([\d,]+)', re.sub(r'\s', '', count_text), 'count', default=None))
        return count

    @staticmethod
    def _extract_thumbnails(data, *path_list, final_key='thumbnails'):
        """
        Extract thumbnails from thumbnails dict
        @param path_list: path list to level that contains 'thumbnails' key
        """
        thumbnails = []
        for path in path_list or [()]:
            for thumbnail in traverse_obj(data, (*variadic(path), final_key, ...)):
                thumbnail_url = url_or_none(thumbnail.get('url'))
                if not thumbnail_url:
                    continue
                # Sometimes youtube gives a wrong thumbnail URL. See:
                # https://github.com/yt-dlp/yt-dlp/issues/233
                # https://github.com/ytdl-org/youtube-dl/issues/28023
                if 'maxresdefault' in thumbnail_url:
                    thumbnail_url = thumbnail_url.split('?')[0]
                thumbnails.append({
                    'url': thumbnail_url,
                    'height': int_or_none(thumbnail.get('height')),
                    'width': int_or_none(thumbnail.get('width')),
                })
        return thumbnails

    @staticmethod
    def extract_relative_time(relative_time_text):
        """
        Extracts a relative time from string and converts to dt object
        e.g. 'streamed 6 days ago', '5 seconds ago (edited)', 'updated today', '8 yr ago'
        """

        # XXX: this could be moved to a general function in utils/_utils.py
        # The relative time text strings are roughly the same as what
        # Javascript's Intl.RelativeTimeFormat function generates.
        # See: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/RelativeTimeFormat
        mobj = re.search(
            r'(?P<start>today|yesterday|now)|(?P<time>\d+)\s*(?P<unit>sec(?:ond)?|s|min(?:ute)?|h(?:our|r)?|d(?:ay)?|w(?:eek|k)?|mo(?:nth)?|y(?:ear|r)?)s?\s*ago',
            relative_time_text)
        if mobj:
            start = mobj.group('start')
            if start:
                return datetime_from_str(start)
            try:
                return datetime_from_str('now-{}{}'.format(mobj.group('time'), mobj.group('unit')))
            except ValueError:
                return None

    def _parse_time_text(self, text):
        if not text:
            return
        dt_ = self.extract_relative_time(text)
        timestamp = None
        if isinstance(dt_, dt.datetime):
            timestamp = calendar.timegm(dt_.timetuple())

        if timestamp is None:
            timestamp = (
                unified_timestamp(text) or unified_timestamp(
                    self._search_regex(
                        (r'([a-z]+\s*\d{1,2},?\s*20\d{2})', r'(?:.+|^)(?:live|premieres|ed|ing)(?:\s*(?:on|for))?\s*(.+\d)'),
                        text.lower(), 'time text', default=None)))

        if text and timestamp is None and self._preferred_lang in (None, 'en'):
            self.report_warning(
                f'Cannot parse localized time text "{text}"', only_once=True)
        return timestamp

    def _extract_response(self, item_id, query, note='Downloading API JSON', headers=None,
                          ytcfg=None, check_get_keys=None, ep='browse', fatal=True, api_hostname=None,
                          default_client='web'):
        raise_for_incomplete = bool(self._configuration_arg('raise_incomplete_data', ie_key=YoutubeIE))
        # Incomplete Data should be a warning by default when retries are exhausted, while other errors should be fatal.
        icd_retries = iter(self.RetryManager(fatal=raise_for_incomplete))
        icd_rm = next(icd_retries)
        main_retries = iter(self.RetryManager())
        main_rm = next(main_retries)
        # Manual retry loop for multiple RetryManagers
        # The proper RetryManager MUST be advanced after an error
        # and its result MUST be checked if the manager is non fatal
        while True:
            try:
                response = self._call_api(
                    ep=ep, fatal=True, headers=headers,
                    video_id=item_id, query=query, note=note,
                    context=self._extract_context(ytcfg, default_client),
                    api_hostname=api_hostname, default_client=default_client)
            except ExtractorError as e:
                if not isinstance(e.cause, network_exceptions):
                    return self._error_or_warning(e, fatal=fatal)
                elif not isinstance(e.cause, HTTPError):
                    main_rm.error = e
                    next(main_retries)
                    continue

                first_bytes = e.cause.response.read(512)
                if not is_html(first_bytes):
                    yt_error = try_get(
                        self._parse_json(
                            self._webpage_read_content(e.cause.response, None, item_id, prefix=first_bytes) or '{}', item_id, fatal=False),
                        lambda x: x['error']['message'], str)
                    if yt_error:
                        self._report_alerts([('ERROR', yt_error)], fatal=False)
                # Downloading page may result in intermittent 5xx HTTP error
                # Sometimes a 404 is also received. See: https://github.com/ytdl-org/youtube-dl/issues/28289
                # We also want to catch all other network exceptions since errors in later pages can be troublesome
                # See https://github.com/yt-dlp/yt-dlp/issues/507#issuecomment-880188210
                if e.cause.status not in (403, 429):
                    main_rm.error = e
                    next(main_retries)
                    continue
                return self._error_or_warning(e, fatal=fatal)

            try:
                self._extract_and_report_alerts(response, only_once=True)
            except ExtractorError as e:
                # YouTube's servers may return errors we want to retry on in a 200 OK response
                # See: https://github.com/yt-dlp/yt-dlp/issues/839
                if 'unknown error' in e.msg.lower():
                    main_rm.error = e
                    next(main_retries)
                    continue
                return self._error_or_warning(e, fatal=fatal)
            # Youtube sometimes sends incomplete data
            # See: https://github.com/ytdl-org/youtube-dl/issues/28194
            if not traverse_obj(response, *variadic(check_get_keys)):
                icd_rm.error = ExtractorError('Incomplete data received', expected=True)
                should_retry = next(icd_retries, None)
                if not should_retry:
                    return None
                continue

            return response

    @staticmethod
    def is_music_url(url):
        return re.match(r'(https?://)?music\.youtube\.com/', url) is not None

    def _extract_video(self, renderer):
        video_id = renderer.get('videoId')

        reel_header_renderer = traverse_obj(renderer, (
            'navigationEndpoint', 'reelWatchEndpoint', 'overlay', 'reelPlayerOverlayRenderer',
            'reelPlayerHeaderSupportedRenderers', 'reelPlayerHeaderRenderer'))

        title = self._get_text(renderer, 'title', 'headline') or self._get_text(reel_header_renderer, 'reelTitleText')
        description = self._get_text(renderer, 'descriptionSnippet')

        duration = int_or_none(renderer.get('lengthSeconds'))
        if duration is None:
            duration = parse_duration(self._get_text(
                renderer, 'lengthText', ('thumbnailOverlays', ..., 'thumbnailOverlayTimeStatusRenderer', 'text')))
        if duration is None:
            # XXX: should write a parser to be more general to support more cases (e.g. shorts in shorts tab)
            duration = parse_duration(self._search_regex(
                r'(?i)(ago)(?!.*\1)\s+(?P<duration>[a-z0-9 ,]+?)(?:\s+[\d,]+\s+views)?(?:\s+-\s+play\s+short)?$',
                traverse_obj(renderer, ('title', 'accessibility', 'accessibilityData', 'label'), default='', expected_type=str),
                video_id, default=None, group='duration'))

        channel_id = traverse_obj(
            renderer, ('shortBylineText', 'runs', ..., 'navigationEndpoint', 'browseEndpoint', 'browseId'),
            expected_type=str, get_all=False)
        if not channel_id:
            channel_id = traverse_obj(reel_header_renderer, ('channelNavigationEndpoint', 'browseEndpoint', 'browseId'))

        channel_id = self.ucid_or_none(channel_id)

        overlay_style = traverse_obj(
            renderer, ('thumbnailOverlays', ..., 'thumbnailOverlayTimeStatusRenderer', 'style'),
            get_all=False, expected_type=str)
        badges = self._extract_badges(traverse_obj(renderer, 'badges'))
        owner_badges = self._extract_badges(traverse_obj(renderer, 'ownerBadges'))
        navigation_url = urljoin('https://www.youtube.com/', traverse_obj(
            renderer, ('navigationEndpoint', 'commandMetadata', 'webCommandMetadata', 'url'),
            expected_type=str)) or ''
        url = f'https://www.youtube.com/watch?v={video_id}'
        if overlay_style == 'SHORTS' or '/shorts/' in navigation_url:
            url = f'https://www.youtube.com/shorts/{video_id}'

        time_text = (self._get_text(renderer, 'publishedTimeText', 'videoInfo')
                     or self._get_text(reel_header_renderer, 'timestampText') or '')
        scheduled_timestamp = str_to_int(traverse_obj(renderer, ('upcomingEventData', 'startTime'), get_all=False))

        live_status = (
            'is_upcoming' if scheduled_timestamp is not None
            else 'was_live' if 'streamed' in time_text.lower()
            else 'is_live' if overlay_style == 'LIVE' or self._has_badge(badges, BadgeType.LIVE_NOW)
            else None)

        # videoInfo is a string like '50K views • 10 years ago'.
        view_count_text = self._get_text(renderer, 'viewCountText', 'shortViewCountText', 'videoInfo') or ''
        view_count = (0 if 'no views' in view_count_text.lower()
                      else self._get_count({'simpleText': view_count_text}))
        view_count_field = 'concurrent_view_count' if live_status in ('is_live', 'is_upcoming') else 'view_count'

        channel = (self._get_text(renderer, 'ownerText', 'shortBylineText')
                   or self._get_text(reel_header_renderer, 'channelTitleText'))

        channel_handle = traverse_obj(renderer, (
            'shortBylineText', 'runs', ..., 'navigationEndpoint',
            (('commandMetadata', 'webCommandMetadata', 'url'), ('browseEndpoint', 'canonicalBaseUrl'))),
            expected_type=self.handle_from_url, get_all=False)
        return {
            '_type': 'url',
            'ie_key': YoutubeIE.ie_key(),
            'id': video_id,
            'url': url,
            'title': title,
            'description': description,
            'duration': duration,
            'channel_id': channel_id,
            'channel': channel,
            'channel_url': f'https://www.youtube.com/channel/{channel_id}' if channel_id else None,
            'uploader': channel,
            'uploader_id': channel_handle,
            'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
            'thumbnails': self._extract_thumbnails(renderer, 'thumbnail'),
            'timestamp': (self._parse_time_text(time_text)
                          if self._configuration_arg('approximate_date', ie_key=YoutubeTabIE)
                          else None),
            'release_timestamp': scheduled_timestamp,
            'availability':
                'public' if self._has_badge(badges, BadgeType.AVAILABILITY_PUBLIC)
                else self._availability(
                    is_private=self._has_badge(badges, BadgeType.AVAILABILITY_PRIVATE) or None,
                    needs_premium=self._has_badge(badges, BadgeType.AVAILABILITY_PREMIUM) or None,
                    needs_subscription=self._has_badge(badges, BadgeType.AVAILABILITY_SUBSCRIPTION) or None,
                    is_unlisted=self._has_badge(badges, BadgeType.AVAILABILITY_UNLISTED) or None),
            view_count_field: view_count,
            'live_status': live_status,
            'channel_is_verified': True if self._has_badge(owner_badges, BadgeType.VERIFIED) else None,
        }


class YoutubeIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube'
    _VALID_URL = r'''(?x)^
                     (
                         (?:https?://|//)                                    # http(s):// or protocol-independent URL
                         (?:(?:(?:(?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie|kids)?\.com|
                            (?:www\.)?deturl\.com/www\.youtube\.com|
                            (?:www\.)?pwnyoutube\.com|
                            (?:www\.)?hooktube\.com|
                            (?:www\.)?yourepeat\.com|
                            tube\.majestyc\.net|
                            {invidious}|
                            youtube\.googleapis\.com)/                        # the various hostnames, with wildcard subdomains
                         (?:.*?\#/)?                                          # handle anchor (#/) redirect urls
                         (?:                                                  # the various things that can precede the ID:
                             (?:(?:v|embed|e|shorts|live)/(?!videoseries|live_stream))  # v/ or embed/ or e/ or shorts/
                             |(?:                                             # or the v= param in all its forms
                                 (?:(?:watch|movie)(?:_popup)?(?:\.php)?/?)?  # preceding watch(_popup|.php) or nothing (like /?v=xxxx)
                                 (?:\?|\#!?)                                  # the params delimiter ? or # or #!
                                 (?:.*?[&;])??                                # any other preceding param (like /?s=tuff&v=xxxx or ?s=tuff&amp;v=V36LpHqtcDY)
                                 v=
                             )
                         ))
                         |(?:
                            youtu\.be|                                        # just youtu.be/xxxx
                            vid\.plus|                                        # or vid.plus/xxxx
                            zwearz\.com/watch|                                # or zwearz.com/watch/xxxx
                            {invidious}
                         )/
                         |(?:www\.)?cleanvideosearch\.com/media/action/yt/watch\?videoId=
                         )
                     )?                                                       # all until now is optional -> you can pass the naked ID
                     (?P<id>[0-9A-Za-z_-]{{11}})                              # here is it! the YouTube video ID
                     (?(1).+)?                                                # if we found the ID, everything can follow
                     (?:\#|$)'''.format(
        invidious='|'.join(YoutubeBaseInfoExtractor._INVIDIOUS_SITES),
    )
    _EMBED_REGEX = [
        r'''(?x)
            (?:
                <(?:[0-9A-Za-z-]+?)?iframe[^>]+?src=|
                data-video-url=|
                <embed[^>]+?src=|
                embedSWF\(?:\s*|
                <object[^>]+data=|
                new\s+SWFObject\(
            )
            (["\'])
                (?P<url>(?:https?:)?//(?:www\.)?youtube(?:-nocookie)?\.com/
                (?:embed|v|p)/[0-9A-Za-z_-]{11}.*?)
            \1''',
        # https://wordpress.org/plugins/lazy-load-for-videos/
        r'''(?xs)
            <a\s[^>]*\bhref="(?P<url>https://www\.youtube\.com/watch\?v=[0-9A-Za-z_-]{11})"
            \s[^>]*\bclass="[^"]*\blazy-load-youtube''',
    ]
    _RETURN_TYPE = 'video'  # XXX: How to handle multifeed?

    _PLAYER_INFO_RE = (
        r'/s/player/(?P<id>[a-zA-Z0-9_-]{8,})/player',
        r'/(?P<id>[a-zA-Z0-9_-]{8,})/player(?:_ias\.vflset(?:/[a-zA-Z]{2,3}_[a-zA-Z]{2,3})?|-plasma-ias-(?:phone|tablet)-[a-z]{2}_[A-Z]{2}\.vflset)/base\.js$',
        r'\b(?P<id>vfl[a-zA-Z0-9_-]+)\b.*?\.js$',
    )
    _formats = {  # NB: Used in YoutubeWebArchiveIE and GoogleDriveIE
        '5': {'ext': 'flv', 'width': 400, 'height': 240, 'acodec': 'mp3', 'abr': 64, 'vcodec': 'h263'},
        '6': {'ext': 'flv', 'width': 450, 'height': 270, 'acodec': 'mp3', 'abr': 64, 'vcodec': 'h263'},
        '13': {'ext': '3gp', 'acodec': 'aac', 'vcodec': 'mp4v'},
        '17': {'ext': '3gp', 'width': 176, 'height': 144, 'acodec': 'aac', 'abr': 24, 'vcodec': 'mp4v'},
        '18': {'ext': 'mp4', 'width': 640, 'height': 360, 'acodec': 'aac', 'abr': 96, 'vcodec': 'h264'},
        '22': {'ext': 'mp4', 'width': 1280, 'height': 720, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        '34': {'ext': 'flv', 'width': 640, 'height': 360, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        '35': {'ext': 'flv', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        # itag 36 videos are either 320x180 (BaW_jenozKc) or 320x240 (__2ABJjxzNo), abr varies as well
        '36': {'ext': '3gp', 'width': 320, 'acodec': 'aac', 'vcodec': 'mp4v'},
        '37': {'ext': 'mp4', 'width': 1920, 'height': 1080, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        '38': {'ext': 'mp4', 'width': 4096, 'height': 3072, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        '43': {'ext': 'webm', 'width': 640, 'height': 360, 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8'},
        '44': {'ext': 'webm', 'width': 854, 'height': 480, 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8'},
        '45': {'ext': 'webm', 'width': 1280, 'height': 720, 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8'},
        '46': {'ext': 'webm', 'width': 1920, 'height': 1080, 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8'},
        '59': {'ext': 'mp4', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        '78': {'ext': 'mp4', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},


        # 3D videos
        '82': {'ext': 'mp4', 'height': 360, 'format_note': '3D', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -20},
        '83': {'ext': 'mp4', 'height': 480, 'format_note': '3D', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -20},
        '84': {'ext': 'mp4', 'height': 720, 'format_note': '3D', 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264', 'preference': -20},
        '85': {'ext': 'mp4', 'height': 1080, 'format_note': '3D', 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264', 'preference': -20},
        '100': {'ext': 'webm', 'height': 360, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8', 'preference': -20},
        '101': {'ext': 'webm', 'height': 480, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8', 'preference': -20},
        '102': {'ext': 'webm', 'height': 720, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8', 'preference': -20},

        # Apple HTTP Live Streaming
        '91': {'ext': 'mp4', 'height': 144, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '92': {'ext': 'mp4', 'height': 240, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '93': {'ext': 'mp4', 'height': 360, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -10},
        '94': {'ext': 'mp4', 'height': 480, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -10},
        '95': {'ext': 'mp4', 'height': 720, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 256, 'vcodec': 'h264', 'preference': -10},
        '96': {'ext': 'mp4', 'height': 1080, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 256, 'vcodec': 'h264', 'preference': -10},
        '132': {'ext': 'mp4', 'height': 240, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '151': {'ext': 'mp4', 'height': 72, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 24, 'vcodec': 'h264', 'preference': -10},

        # DASH mp4 video
        '133': {'ext': 'mp4', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '134': {'ext': 'mp4', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '135': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '136': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '137': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '138': {'ext': 'mp4', 'format_note': 'DASH video', 'vcodec': 'h264'},  # Height can vary (https://github.com/ytdl-org/youtube-dl/issues/4559)
        '160': {'ext': 'mp4', 'height': 144, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '212': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '264': {'ext': 'mp4', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '298': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'h264', 'fps': 60},
        '299': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'h264', 'fps': 60},
        '266': {'ext': 'mp4', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'h264'},

        # Dash mp4 audio
        '139': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 48, 'container': 'm4a_dash'},
        '140': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 128, 'container': 'm4a_dash'},
        '141': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 256, 'container': 'm4a_dash'},
        '256': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'container': 'm4a_dash'},
        '258': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'container': 'm4a_dash'},
        '325': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'dtse', 'container': 'm4a_dash'},
        '328': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'ec-3', 'container': 'm4a_dash'},

        # Dash webm
        '167': {'ext': 'webm', 'height': 360, 'width': 640, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '168': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '169': {'ext': 'webm', 'height': 720, 'width': 1280, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '170': {'ext': 'webm', 'height': 1080, 'width': 1920, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '218': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '219': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '278': {'ext': 'webm', 'height': 144, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp9'},
        '242': {'ext': 'webm', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '243': {'ext': 'webm', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '244': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '245': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '246': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '247': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '248': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '271': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        # itag 272 videos are either 3840x2160 (e.g. RtoitU2A-3E) or 7680x4320 (sLprVF6d7Ug)
        '272': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '302': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '303': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '308': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '313': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '315': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},

        # Dash webm audio
        '171': {'ext': 'webm', 'acodec': 'vorbis', 'format_note': 'DASH audio', 'abr': 128},
        '172': {'ext': 'webm', 'acodec': 'vorbis', 'format_note': 'DASH audio', 'abr': 256},

        # Dash webm audio with opus inside
        '249': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 50},
        '250': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 70},
        '251': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 160},

        # RTMP (unnamed)
        '_rtmp': {'protocol': 'rtmp'},

        # av01 video only formats sometimes served with "unknown" codecs
        '394': {'ext': 'mp4', 'height': 144, 'format_note': 'DASH video', 'vcodec': 'av01.0.00M.08'},
        '395': {'ext': 'mp4', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'av01.0.00M.08'},
        '396': {'ext': 'mp4', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'av01.0.01M.08'},
        '397': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'av01.0.04M.08'},
        '398': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'av01.0.05M.08'},
        '399': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'av01.0.08M.08'},
        '400': {'ext': 'mp4', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'av01.0.12M.08'},
        '401': {'ext': 'mp4', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'av01.0.12M.08'},
    }
    _SUBTITLE_FORMATS = ('json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt')
    _POTOKEN_EXPERIMENTS = ('51217476', '51217102')
    _BROKEN_CLIENTS = {
        short_client_name(client): client
        for client in ('android', 'android_creator', 'android_music')
    }

    _GEO_BYPASS = False

    IE_NAME = 'youtube'
    _TESTS = [
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&t=1s&end=9',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'channel': 'Philipp Hagemeister',
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'upload_date': '20121002',
                'description': 'md5:8fb536f4877b8a7455c2ec23794dbc22',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'availability': 'public',
                'playable_in_embed': True,
                'thumbnail': 'https://i.ytimg.com/vi/BaW_jenozKc/maxresdefault.jpg',
                'live_status': 'not_live',
                'age_limit': 0,
                'start_time': 1,
                'end_time': 9,
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': 'Philipp Hagemeister',
                'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
                'uploader_id': '@PhilippHagemeister',
                'heatmap': 'count:100',
                'timestamp': 1349198244,
            },
        },
        {
            'url': '//www.YouTube.com/watch?v=yZIXLfi8CZQ',
            'note': 'Embed-only video (#1746)',
            'info_dict': {
                'id': 'yZIXLfi8CZQ',
                'ext': 'mp4',
                'upload_date': '20120608',
                'title': 'Principal Sexually Assaults A Teacher - Episode 117 - 8th June 2012',
                'description': 'md5:09b78bd971f1e3e289601dfba15ca4f7',
                'age_limit': 18,
            },
            'skip': 'Private video',
        },
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&v=yZIXLfi8CZQ',
            'note': 'Use the first video ID in the URL',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'channel': 'Philipp Hagemeister',
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'upload_date': '20121002',
                'description': 'md5:8fb536f4877b8a7455c2ec23794dbc22',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'availability': 'public',
                'playable_in_embed': True,
                'thumbnail': 'https://i.ytimg.com/vi/BaW_jenozKc/maxresdefault.jpg',
                'live_status': 'not_live',
                'age_limit': 0,
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': 'Philipp Hagemeister',
                'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
                'uploader_id': '@PhilippHagemeister',
                'heatmap': 'count:100',
                'timestamp': 1349198244,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtube.com/watch?v=a9LDPn-MO4I',
            'note': '256k DASH audio (format 141) via DASH manifest',
            'info_dict': {
                'id': 'a9LDPn-MO4I',
                'ext': 'm4a',
                'upload_date': '20121002',
                'description': '',
                'title': 'UHDTV TEST 8K VIDEO.mp4',
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '141',
            },
            'skip': 'format 141 not served anymore',
        },
        # DASH manifest with encrypted signature
        {
            'url': 'https://www.youtube.com/watch?v=IB3lcPjvWLA',
            'info_dict': {
                'id': 'IB3lcPjvWLA',
                'ext': 'm4a',
                'title': 'Afrojack, Spree Wilson - The Spark (Official Music Video) ft. Spree Wilson',
                'description': 'md5:8f5e2b82460520b619ccac1f509d43bf',
                'duration': 244,
                'upload_date': '20131011',
                'abr': 129.495,
                'like_count': int,
                'channel_id': 'UChuZAo1RKL85gev3Eal9_zg',
                'playable_in_embed': True,
                'channel_url': 'https://www.youtube.com/channel/UChuZAo1RKL85gev3Eal9_zg',
                'view_count': int,
                'track': 'The Spark',
                'live_status': 'not_live',
                'thumbnail': 'https://i.ytimg.com/vi_webp/IB3lcPjvWLA/maxresdefault.webp',
                'channel': 'Afrojack',
                'tags': 'count:19',
                'availability': 'public',
                'categories': ['Music'],
                'age_limit': 0,
                'alt_title': 'The Spark',
                'channel_follower_count': int,
                'uploader': 'Afrojack',
                'uploader_url': 'https://www.youtube.com/@Afrojack',
                'uploader_id': '@Afrojack',
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '141/bestaudio[ext=m4a]',
            },
        },
        # Age-gate videos. See https://github.com/yt-dlp/yt-dlp/pull/575#issuecomment-888837000
        {
            'note': 'Embed allowed age-gate video',
            'url': 'https://youtube.com/watch?v=HtVdAasjOgU',
            'info_dict': {
                'id': 'HtVdAasjOgU',
                'ext': 'mp4',
                'title': 'The Witcher 3: Wild Hunt - The Sword Of Destiny Trailer',
                'description': r're:(?s).{100,}About the Game\n.*?The Witcher 3: Wild Hunt.{100,}',
                'duration': 142,
                'upload_date': '20140605',
                'age_limit': 18,
                'categories': ['Gaming'],
                'thumbnail': 'https://i.ytimg.com/vi_webp/HtVdAasjOgU/maxresdefault.webp',
                'availability': 'needs_auth',
                'channel_url': 'https://www.youtube.com/channel/UCzybXLxv08IApdjdN0mJhEg',
                'like_count': int,
                'channel': 'The Witcher',
                'live_status': 'not_live',
                'tags': 'count:17',
                'channel_id': 'UCzybXLxv08IApdjdN0mJhEg',
                'playable_in_embed': True,
                'view_count': int,
                'channel_follower_count': int,
                'uploader': 'The Witcher',
                'uploader_url': 'https://www.youtube.com/@thewitcher',
                'uploader_id': '@thewitcher',
                'comment_count': int,
                'channel_is_verified': True,
                'heatmap': 'count:100',
                'timestamp': 1401991663,
            },
        },
        {
            'note': 'Age-gate video with embed allowed in public site',
            'url': 'https://youtube.com/watch?v=HsUATh_Nc2U',
            'info_dict': {
                'id': 'HsUATh_Nc2U',
                'ext': 'mp4',
                'title': 'Godzilla 2 (Official Video)',
                'description': 'md5:bf77e03fcae5529475e500129b05668a',
                'upload_date': '20200408',
                'age_limit': 18,
                'availability': 'needs_auth',
                'channel_id': 'UCYQT13AtrJC0gsM1far_zJg',
                'channel': 'FlyingKitty',
                'channel_url': 'https://www.youtube.com/channel/UCYQT13AtrJC0gsM1far_zJg',
                'view_count': int,
                'categories': ['Entertainment'],
                'live_status': 'not_live',
                'tags': ['Flyingkitty', 'godzilla 2'],
                'thumbnail': 'https://i.ytimg.com/vi/HsUATh_Nc2U/maxresdefault.jpg',
                'like_count': int,
                'duration': 177,
                'playable_in_embed': True,
                'channel_follower_count': int,
                'uploader': 'FlyingKitty',
                'uploader_url': 'https://www.youtube.com/@FlyingKitty900',
                'uploader_id': '@FlyingKitty900',
                'comment_count': int,
                'channel_is_verified': True,
            },
        },
        {
            'note': 'Age-gate video embedable only with clientScreen=EMBED',
            'url': 'https://youtube.com/watch?v=Tq92D6wQ1mg',
            'info_dict': {
                'id': 'Tq92D6wQ1mg',
                'title': '[MMD] Adios - EVERGLOW [+Motion DL]',
                'ext': 'mp4',
                'upload_date': '20191228',
                'description': 'md5:17eccca93a786d51bc67646756894066',
                'age_limit': 18,
                'like_count': int,
                'availability': 'needs_auth',
                'channel_id': 'UC1yoRdFoFJaCY-AGfD9W0wQ',
                'view_count': int,
                'thumbnail': 'https://i.ytimg.com/vi_webp/Tq92D6wQ1mg/sddefault.webp',
                'channel': 'Projekt Melody',
                'live_status': 'not_live',
                'tags': ['mmd', 'dance', 'mikumikudance', 'kpop', 'vtuber'],
                'playable_in_embed': True,
                'categories': ['Entertainment'],
                'duration': 106,
                'channel_url': 'https://www.youtube.com/channel/UC1yoRdFoFJaCY-AGfD9W0wQ',
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': 'Projekt Melody',
                'uploader_url': 'https://www.youtube.com/@ProjektMelody',
                'uploader_id': '@ProjektMelody',
                'timestamp': 1577508724,
            },
        },
        {
            'note': 'Non-Agegated non-embeddable video',
            'url': 'https://youtube.com/watch?v=MeJVWBSsPAY',
            'info_dict': {
                'id': 'MeJVWBSsPAY',
                'ext': 'mp4',
                'title': 'OOMPH! - Such Mich Find Mich (Lyrics)',
                'description': 'Fan Video. Music & Lyrics by OOMPH!.',
                'upload_date': '20130730',
                'track': 'Such mich find mich',
                'age_limit': 0,
                'tags': ['oomph', 'such mich find mich', 'lyrics', 'german industrial', 'musica industrial'],
                'like_count': int,
                'playable_in_embed': False,
                'creator': 'OOMPH!',
                'thumbnail': 'https://i.ytimg.com/vi/MeJVWBSsPAY/sddefault.jpg',
                'view_count': int,
                'alt_title': 'Such mich find mich',
                'duration': 210,
                'channel': 'Herr Lurik',
                'channel_id': 'UCdR3RSDPqub28LjZx0v9-aA',
                'categories': ['Music'],
                'availability': 'public',
                'channel_url': 'https://www.youtube.com/channel/UCdR3RSDPqub28LjZx0v9-aA',
                'live_status': 'not_live',
                'artist': 'OOMPH!',
                'channel_follower_count': int,
                'uploader': 'Herr Lurik',
                'uploader_url': 'https://www.youtube.com/@HerrLurik',
                'uploader_id': '@HerrLurik',
            },
        },
        {
            'note': 'Non-bypassable age-gated video',
            'url': 'https://youtube.com/watch?v=Cr381pDsSsA',
            'only_matching': True,
        },
        # video_info is None (https://github.com/ytdl-org/youtube-dl/issues/4421)
        # YouTube Red ad is not captured for creator
        {
            'url': '__2ABJjxzNo',
            'info_dict': {
                'id': '__2ABJjxzNo',
                'ext': 'mp4',
                'duration': 266,
                'upload_date': '20100430',
                'creator': 'deadmau5',
                'description': 'md5:6cbcd3a92ce1bc676fc4d6ab4ace2336',
                'title': 'Deadmau5 - Some Chords (HD)',
                'alt_title': 'Some Chords',
                'availability': 'public',
                'tags': 'count:14',
                'channel_id': 'UCYEK6xds6eo-3tr4xRdflmQ',
                'view_count': int,
                'live_status': 'not_live',
                'channel': 'deadmau5',
                'thumbnail': 'https://i.ytimg.com/vi_webp/__2ABJjxzNo/maxresdefault.webp',
                'like_count': int,
                'track': 'Some Chords',
                'artist': 'deadmau5',
                'playable_in_embed': True,
                'age_limit': 0,
                'channel_url': 'https://www.youtube.com/channel/UCYEK6xds6eo-3tr4xRdflmQ',
                'categories': ['Music'],
                'album': 'Some Chords',
                'channel_follower_count': int,
                'uploader': 'deadmau5',
                'uploader_url': 'https://www.youtube.com/@deadmau5',
                'uploader_id': '@deadmau5',
            },
            'expected_warnings': [
                'DASH manifest missing',
            ],
        },
        # Olympics (https://github.com/ytdl-org/youtube-dl/issues/4431)
        {
            'url': 'lqQg6PlCWgI',
            'info_dict': {
                'id': 'lqQg6PlCWgI',
                'ext': 'mp4',
                'duration': 6085,
                'upload_date': '20150827',
                'description': 'md5:04bbbf3ccceb6795947572ca36f45904',
                'title': 'Hockey - Women -  GER-AUS - London 2012 Olympic Games',
                'like_count': int,
                'release_timestamp': 1343767800,
                'playable_in_embed': True,
                'categories': ['Sports'],
                'release_date': '20120731',
                'channel': 'Olympics',
                'tags': ['Hockey', '2012-07-31', '31 July 2012', 'Riverbank Arena', 'Session', 'Olympics', 'Olympic Games', 'London 2012', '2012 Summer Olympics', 'Summer Games'],
                'channel_id': 'UCTl3QQTvqHFjurroKxexy2Q',
                'thumbnail': 'https://i.ytimg.com/vi/lqQg6PlCWgI/maxresdefault.jpg',
                'age_limit': 0,
                'availability': 'public',
                'live_status': 'was_live',
                'view_count': int,
                'channel_url': 'https://www.youtube.com/channel/UCTl3QQTvqHFjurroKxexy2Q',
                'channel_follower_count': int,
                'uploader': 'Olympics',
                'uploader_url': 'https://www.youtube.com/@Olympics',
                'uploader_id': '@Olympics',
                'channel_is_verified': True,
                'timestamp': 1440707674,
            },
            'params': {
                'skip_download': 'requires avconv',
            },
        },
        # Non-square pixels
        {
            'url': 'https://www.youtube.com/watch?v=_b-2C3KPAM0',
            'info_dict': {
                'id': '_b-2C3KPAM0',
                'ext': 'mp4',
                'stretched_ratio': 16 / 9.,
                'duration': 85,
                'upload_date': '20110310',
                'description': 'made by Wacom from Korea | 字幕&加油添醋 by TY\'s Allen | 感謝heylisa00cavey1001同學熱情提供梗及翻譯',
                'title': '[A-made] 變態妍字幕版 太妍 我就是這樣的人',
                'playable_in_embed': True,
                'channel': '孫ᄋᄅ',
                'age_limit': 0,
                'tags': 'count:11',
                'channel_url': 'https://www.youtube.com/channel/UCS-xxCmRaA6BFdmgDPA_BIw',
                'channel_id': 'UCS-xxCmRaA6BFdmgDPA_BIw',
                'thumbnail': 'https://i.ytimg.com/vi/_b-2C3KPAM0/maxresdefault.jpg',
                'view_count': int,
                'categories': ['People & Blogs'],
                'like_count': int,
                'live_status': 'not_live',
                'availability': 'unlisted',
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': '孫ᄋᄅ',
                'uploader_url': 'https://www.youtube.com/@AllenMeow',
                'uploader_id': '@AllenMeow',
                'timestamp': 1299776999,
            },
        },
        # url_encoded_fmt_stream_map is empty string
        {
            'url': 'qEJwOuvDf7I',
            'info_dict': {
                'id': 'qEJwOuvDf7I',
                'ext': 'webm',
                'title': 'Обсуждение судебной практики по выборам 14 сентября 2014 года в Санкт-Петербурге',
                'description': '',
                'upload_date': '20150404',
            },
            'params': {
                'skip_download': 'requires avconv',
            },
            'skip': 'This live event has ended.',
        },
        # Extraction from multiple DASH manifests (https://github.com/ytdl-org/youtube-dl/pull/6097)
        {
            'url': 'https://www.youtube.com/watch?v=FIl7x6_3R5Y',
            'info_dict': {
                'id': 'FIl7x6_3R5Y',
                'ext': 'webm',
                'title': 'md5:7b81415841e02ecd4313668cde88737a',
                'description': 'md5:116377fd2963b81ec4ce64b542173306',
                'duration': 220,
                'upload_date': '20150625',
                'formats': 'mincount:31',
            },
            'skip': 'not actual anymore',
        },
        # DASH manifest with segment_list
        {
            'url': 'https://www.youtube.com/embed/CsmdDsKjzN8',
            'md5': '8ce563a1d667b599d21064e982ab9e31',
            'info_dict': {
                'id': 'CsmdDsKjzN8',
                'ext': 'mp4',
                'upload_date': '20150501',  # According to '<meta itemprop="datePublished"', but in other places it's 20150510
                'description': 'Retransmisión en directo de la XVIII media maratón de Zaragoza.',
                'title': 'Retransmisión XVIII Media maratón Zaragoza 2015',
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '135',  # bestvideo
            },
            'skip': 'This live event has ended.',
        },
        {
            # Multifeed videos (multiple cameras), URL can be of any Camera
            # TODO: fix multifeed titles
            'url': 'https://www.youtube.com/watch?v=zaPI8MvL8pg',
            'info_dict': {
                'id': 'zaPI8MvL8pg',
                'title': 'Terraria 1.2 Live Stream | Let\'s Play - Part 04',
                'description': 'md5:563ccbc698b39298481ca3c571169519',
            },
            'playlist': [{
                'info_dict': {
                    'id': 'j5yGuxZ8lLU',
                    'ext': 'mp4',
                    'title': 'Terraria 1.2 Live Stream | Let\'s Play - Part 04 (Chris)',
                    'description': 'md5:563ccbc698b39298481ca3c571169519',
                    'duration': 10120,
                    'channel_follower_count': int,
                    'channel_url': 'https://www.youtube.com/channel/UCN2XePorRokPB9TEgRZpddg',
                    'availability': 'public',
                    'playable_in_embed': True,
                    'upload_date': '20131105',
                    'categories': ['Gaming'],
                    'live_status': 'was_live',
                    'tags': 'count:24',
                    'release_timestamp': 1383701910,
                    'thumbnail': 'https://i.ytimg.com/vi/j5yGuxZ8lLU/maxresdefault.jpg',
                    'comment_count': int,
                    'age_limit': 0,
                    'like_count': int,
                    'channel_id': 'UCN2XePorRokPB9TEgRZpddg',
                    'channel': 'WiiLikeToPlay',
                    'view_count': int,
                    'release_date': '20131106',
                    'uploader': 'WiiLikeToPlay',
                    'uploader_id': '@WLTP',
                    'uploader_url': 'https://www.youtube.com/@WLTP',
                },
            }, {
                'info_dict': {
                    'id': 'zaPI8MvL8pg',
                    'ext': 'mp4',
                    'title': 'Terraria 1.2 Live Stream | Let\'s Play - Part 04 (Tyson)',
                    'availability': 'public',
                    'channel_url': 'https://www.youtube.com/channel/UCN2XePorRokPB9TEgRZpddg',
                    'channel': 'WiiLikeToPlay',
                    'channel_follower_count': int,
                    'description': 'md5:563ccbc698b39298481ca3c571169519',
                    'duration': 10108,
                    'age_limit': 0,
                    'like_count': int,
                    'tags': 'count:24',
                    'channel_id': 'UCN2XePorRokPB9TEgRZpddg',
                    'release_timestamp': 1383701915,
                    'comment_count': int,
                    'upload_date': '20131105',
                    'thumbnail': 'https://i.ytimg.com/vi/zaPI8MvL8pg/maxresdefault.jpg',
                    'release_date': '20131106',
                    'playable_in_embed': True,
                    'live_status': 'was_live',
                    'categories': ['Gaming'],
                    'view_count': int,
                    'uploader': 'WiiLikeToPlay',
                    'uploader_id': '@WLTP',
                    'uploader_url': 'https://www.youtube.com/@WLTP',
                },
            }, {
                'info_dict': {
                    'id': 'R7r3vfO7Hao',
                    'ext': 'mp4',
                    'title': 'Terraria 1.2 Live Stream | Let\'s Play - Part 04 (Spencer)',
                    'thumbnail': 'https://i.ytimg.com/vi/R7r3vfO7Hao/maxresdefault.jpg',
                    'channel_id': 'UCN2XePorRokPB9TEgRZpddg',
                    'like_count': int,
                    'availability': 'public',
                    'playable_in_embed': True,
                    'upload_date': '20131105',
                    'description': 'md5:563ccbc698b39298481ca3c571169519',
                    'channel_follower_count': int,
                    'tags': 'count:24',
                    'release_date': '20131106',
                    'comment_count': int,
                    'channel_url': 'https://www.youtube.com/channel/UCN2XePorRokPB9TEgRZpddg',
                    'channel': 'WiiLikeToPlay',
                    'categories': ['Gaming'],
                    'release_timestamp': 1383701914,
                    'live_status': 'was_live',
                    'age_limit': 0,
                    'duration': 10128,
                    'view_count': int,
                    'uploader': 'WiiLikeToPlay',
                    'uploader_id': '@WLTP',
                    'uploader_url': 'https://www.youtube.com/@WLTP',
                },
            }],
            'params': {'skip_download': True},
            'skip': 'Not multifeed anymore',
        },
        {
            # Multifeed video with comma in title (see https://github.com/ytdl-org/youtube-dl/issues/8536)
            'url': 'https://www.youtube.com/watch?v=gVfLd0zydlo',
            'info_dict': {
                'id': 'gVfLd0zydlo',
                'title': 'DevConf.cz 2016 Day 2 Workshops 1 14:00 - 15:30',
            },
            'playlist_count': 2,
            'skip': 'Not multifeed anymore',
        },
        {
            'url': 'https://vid.plus/FlRa-iH7PGw',
            'only_matching': True,
        },
        {
            'url': 'https://zwearz.com/watch/9lWxNJF-ufM/electra-woman-dyna-girl-official-trailer-grace-helbig.html',
            'only_matching': True,
        },
        {
            # Title with JS-like syntax "};" (see https://github.com/ytdl-org/youtube-dl/issues/7468)
            # Also tests cut-off URL expansion in video description (see
            # https://github.com/ytdl-org/youtube-dl/issues/1892,
            # https://github.com/ytdl-org/youtube-dl/issues/8164)
            'url': 'https://www.youtube.com/watch?v=lsguqyKfVQg',
            'info_dict': {
                'id': 'lsguqyKfVQg',
                'ext': 'mp4',
                'title': '{dark walk}; Loki/AC/Dishonored; collab w/Elflover21',
                'alt_title': 'Dark Walk',
                'description': 'md5:8085699c11dc3f597ce0410b0dcbb34a',
                'duration': 133,
                'upload_date': '20151119',
                'creator': 'Todd Haberman;\nDaniel Law Heath and Aaron Kaplan',
                'track': 'Dark Walk',
                'artist': 'Todd Haberman;\nDaniel Law Heath and Aaron Kaplan',
                'album': 'Position Music - Production Music Vol. 143 - Dark Walk',
                'thumbnail': 'https://i.ytimg.com/vi_webp/lsguqyKfVQg/maxresdefault.webp',
                'categories': ['Film & Animation'],
                'view_count': int,
                'live_status': 'not_live',
                'channel_url': 'https://www.youtube.com/channel/UCTSRgz5jylBvFt_S7wnsqLQ',
                'channel_id': 'UCTSRgz5jylBvFt_S7wnsqLQ',
                'tags': 'count:13',
                'availability': 'public',
                'channel': 'IronSoulElf',
                'playable_in_embed': True,
                'like_count': int,
                'age_limit': 0,
                'channel_follower_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Tags with '};' (see https://github.com/ytdl-org/youtube-dl/issues/7468)
            'url': 'https://www.youtube.com/watch?v=Ms7iBXnlUO8',
            'only_matching': True,
        },
        {
            # Video with yt:stretch=17:0
            'url': 'https://www.youtube.com/watch?v=Q39EVAstoRM',
            'info_dict': {
                'id': 'Q39EVAstoRM',
                'ext': 'mp4',
                'title': 'Clash Of Clans#14 Dicas De Ataque Para CV 4',
                'description': 'md5:ee18a25c350637c8faff806845bddee9',
                'upload_date': '20151107',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video does not exist.',
        },
        {
            # Video with incomplete 'yt:stretch=16:'
            'url': 'https://www.youtube.com/watch?v=FRhJzUSJbGI',
            'only_matching': True,
        },
        {
            # Video licensed under Creative Commons
            'url': 'https://www.youtube.com/watch?v=M4gD1WSo5mA',
            'info_dict': {
                'id': 'M4gD1WSo5mA',
                'ext': 'mp4',
                'title': 'md5:e41008789470fc2533a3252216f1c1d1',
                'description': 'md5:a677553cf0840649b731a3024aeff4cc',
                'duration': 721,
                'upload_date': '20150128',
                'license': 'Creative Commons Attribution license (reuse allowed)',
                'channel_id': 'UCuLGmD72gJDBwmLw06X58SA',
                'channel_url': 'https://www.youtube.com/channel/UCuLGmD72gJDBwmLw06X58SA',
                'like_count': int,
                'age_limit': 0,
                'tags': ['Copyright (Legal Subject)', 'Law (Industry)', 'William W. Fisher (Author)'],
                'channel': 'The Berkman Klein Center for Internet & Society',
                'availability': 'public',
                'view_count': int,
                'categories': ['Education'],
                'thumbnail': 'https://i.ytimg.com/vi_webp/M4gD1WSo5mA/maxresdefault.webp',
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel_follower_count': int,
                'chapters': list,
                'uploader': 'The Berkman Klein Center for Internet & Society',
                'uploader_id': '@BKCHarvard',
                'uploader_url': 'https://www.youtube.com/@BKCHarvard',
                'timestamp': 1422422076,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtube.com/watch?v=eQcmzGIKrzg',
            'info_dict': {
                'id': 'eQcmzGIKrzg',
                'ext': 'mp4',
                'title': 'Democratic Socialism and Foreign Policy | Bernie Sanders',
                'description': 'md5:13a2503d7b5904ef4b223aa101628f39',
                'duration': 4060,
                'upload_date': '20151120',
                'license': 'Creative Commons Attribution license (reuse allowed)',
                'playable_in_embed': True,
                'tags': 'count:12',
                'like_count': int,
                'channel_id': 'UCH1dpzjCEiGAt8CXkryhkZg',
                'age_limit': 0,
                'availability': 'public',
                'categories': ['News & Politics'],
                'channel': 'Bernie Sanders',
                'thumbnail': 'https://i.ytimg.com/vi_webp/eQcmzGIKrzg/maxresdefault.webp',
                'view_count': int,
                'live_status': 'not_live',
                'channel_url': 'https://www.youtube.com/channel/UCH1dpzjCEiGAt8CXkryhkZg',
                'comment_count': int,
                'channel_follower_count': int,
                'chapters': list,
                'uploader': 'Bernie Sanders',
                'uploader_url': 'https://www.youtube.com/@BernieSanders',
                'uploader_id': '@BernieSanders',
                'channel_is_verified': True,
                'heatmap': 'count:100',
                'timestamp': 1447987198,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtube.com/watch?feature=player_embedded&amp;amp;v=V36LpHqtcDY',
            'only_matching': True,
        },
        {
            # YouTube Red paid video (https://github.com/ytdl-org/youtube-dl/issues/10059)
            'url': 'https://www.youtube.com/watch?v=i1Ko8UG-Tdo',
            'only_matching': True,
        },
        {
            # Rental video preview
            'url': 'https://www.youtube.com/watch?v=yYr8q0y5Jfg',
            'info_dict': {
                'id': 'uGpuVWrhIzE',
                'ext': 'mp4',
                'title': 'Piku - Trailer',
                'description': 'md5:c36bd60c3fd6f1954086c083c72092eb',
                'upload_date': '20150811',
                'license': 'Standard YouTube License',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video is not available.',
        },
        {
            # YouTube Red video with episode data
            'url': 'https://www.youtube.com/watch?v=iqKdEhx-dD4',
            'info_dict': {
                'id': 'iqKdEhx-dD4',
                'ext': 'mp4',
                'title': 'Isolation - Mind Field (Ep 1)',
                'description': 'md5:f540112edec5d09fc8cc752d3d4ba3cd',
                'duration': 2085,
                'upload_date': '20170118',
                'series': 'Mind Field',
                'season_number': 1,
                'episode_number': 1,
                'thumbnail': 'https://i.ytimg.com/vi_webp/iqKdEhx-dD4/maxresdefault.webp',
                'tags': 'count:12',
                'view_count': int,
                'availability': 'public',
                'age_limit': 0,
                'channel': 'Vsauce',
                'episode': 'Episode 1',
                'categories': ['Entertainment'],
                'season': 'Season 1',
                'channel_id': 'UC6nSFpj9HTCZ5t-N3Rm3-HA',
                'channel_url': 'https://www.youtube.com/channel/UC6nSFpj9HTCZ5t-N3Rm3-HA',
                'like_count': int,
                'playable_in_embed': True,
                'live_status': 'not_live',
                'channel_follower_count': int,
                'uploader': 'Vsauce',
                'uploader_url': 'https://www.youtube.com/@Vsauce',
                'uploader_id': '@Vsauce',
                'comment_count': int,
                'channel_is_verified': True,
                'timestamp': 1484761047,
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': [
                'Skipping DASH manifest',
            ],
        },
        {
            # The following content has been identified by the YouTube community
            # as inappropriate or offensive to some audiences.
            'url': 'https://www.youtube.com/watch?v=6SJNVb0GnPI',
            'info_dict': {
                'id': '6SJNVb0GnPI',
                'ext': 'mp4',
                'title': 'Race Differences in Intelligence',
                'description': 'md5:5d161533167390427a1f8ee89a1fc6f1',
                'duration': 965,
                'upload_date': '20140124',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video has been removed for violating YouTube\'s policy on hate speech.',
        },
        {
            # itag 212
            'url': '1t24XAntNCY',
            'only_matching': True,
        },
        {
            # geo restricted to JP
            'url': 'sJL6WA-aGkQ',
            'only_matching': True,
        },
        {
            'url': 'https://invidio.us/watch?v=BaW_jenozKc',
            'only_matching': True,
        },
        {
            'url': 'https://redirect.invidious.io/watch?v=BaW_jenozKc',
            'only_matching': True,
        },
        {
            # from https://nitter.pussthecat.org/YouTube/status/1360363141947944964#m
            'url': 'https://redirect.invidious.io/Yh0AhrY9GjA',
            'only_matching': True,
        },
        {
            # DRM protected
            'url': 'https://www.youtube.com/watch?v=s7_qI6_mIXc',
            'only_matching': True,
        },
        {
            # Video with unsupported adaptive stream type formats
            'url': 'https://www.youtube.com/watch?v=Z4Vy8R84T1U',
            'info_dict': {
                'id': 'Z4Vy8R84T1U',
                'ext': 'mp4',
                'title': 'saman SMAN 53 Jakarta(Sancety) opening COFFEE4th at SMAN 53 Jakarta',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'duration': 433,
                'upload_date': '20130923',
                'formats': 'maxcount:10',
            },
            'params': {
                'skip_download': True,
                'youtube_include_dash_manifest': False,
            },
            'skip': 'not actual anymore',
        },
        {
            # Youtube Music Auto-generated description
            # TODO: fix metadata extraction
            'url': 'https://music.youtube.com/watch?v=MgNrAu2pzNs',
            'info_dict': {
                'id': 'MgNrAu2pzNs',
                'ext': 'mp4',
                'title': 'Voyeur Girl',
                'description': 'md5:7ae382a65843d6df2685993e90a8628f',
                'upload_date': '20190312',
                'artists': ['Stephen'],
                'creators': ['Stephen'],
                'track': 'Voyeur Girl',
                'album': 'it\'s too much love to know my dear',
                'release_date': '20190313',
                'alt_title': 'Voyeur Girl',
                'view_count': int,
                'playable_in_embed': True,
                'like_count': int,
                'categories': ['Music'],
                'channel_url': 'https://www.youtube.com/channel/UC-pWHpBjdGG69N9mM2auIAA',
                'channel': 'Stephen',  # TODO: should be "Stephen - Topic"
                'uploader': 'Stephen',
                'availability': 'public',
                'duration': 169,
                'thumbnail': 'https://i.ytimg.com/vi_webp/MgNrAu2pzNs/maxresdefault.webp',
                'age_limit': 0,
                'channel_id': 'UC-pWHpBjdGG69N9mM2auIAA',
                'tags': 'count:11',
                'live_status': 'not_live',
                'channel_follower_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtubekids.com/watch?v=3b8nCWDgZ6Q',
            'only_matching': True,
        },
        {
            # invalid -> valid video id redirection
            'url': 'DJztXj2GPfl',
            'info_dict': {
                'id': 'DJztXj2GPfk',
                'ext': 'mp4',
                'title': 'Panjabi MC - Mundian To Bach Ke (The Dictator Soundtrack)',
                'description': 'md5:bf577a41da97918e94fa9798d9228825',
                'upload_date': '20090125',
                'artist': 'Panjabi MC',
                'track': 'Beware of the Boys (Mundian to Bach Ke) - Motivo Hi-Lectro Remix',
                'album': 'Beware of the Boys (Mundian To Bach Ke)',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'Video unavailable',
        },
        {
            # empty description results in an empty string
            'url': 'https://www.youtube.com/watch?v=x41yOUIvK2k',
            'info_dict': {
                'id': 'x41yOUIvK2k',
                'ext': 'mp4',
                'title': 'IMG 3456',
                'description': '',
                'upload_date': '20170613',
                'view_count': int,
                'thumbnail': 'https://i.ytimg.com/vi_webp/x41yOUIvK2k/maxresdefault.webp',
                'like_count': int,
                'channel_id': 'UCo03ZQPBW5U4UC3regpt1nw',
                'tags': [],
                'channel_url': 'https://www.youtube.com/channel/UCo03ZQPBW5U4UC3regpt1nw',
                'availability': 'public',
                'age_limit': 0,
                'categories': ['Pets & Animals'],
                'duration': 7,
                'playable_in_embed': True,
                'live_status': 'not_live',
                'channel': 'l\'Or Vert asbl',
                'channel_follower_count': int,
                'uploader': 'l\'Or Vert asbl',
                'uploader_url': 'https://www.youtube.com/@ElevageOrVert',
                'uploader_id': '@ElevageOrVert',
                'timestamp': 1497343210,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # with '};' inside yt initial data (see [1])
            # see [2] for an example with '};' inside ytInitialPlayerResponse
            # 1. https://github.com/ytdl-org/youtube-dl/issues/27093
            # 2. https://github.com/ytdl-org/youtube-dl/issues/27216
            'url': 'https://www.youtube.com/watch?v=CHqg6qOn4no',
            'info_dict': {
                'id': 'CHqg6qOn4no',
                'ext': 'mp4',
                'title': 'Part 77   Sort a list of simple types in c#',
                'description': 'md5:b8746fa52e10cdbf47997903f13b20dc',
                'upload_date': '20130831',
                'channel_id': 'UCCTVrRB5KpIiK6V2GGVsR1Q',
                'like_count': int,
                'channel_url': 'https://www.youtube.com/channel/UCCTVrRB5KpIiK6V2GGVsR1Q',
                'live_status': 'not_live',
                'categories': ['Education'],
                'availability': 'public',
                'thumbnail': 'https://i.ytimg.com/vi/CHqg6qOn4no/sddefault.jpg',
                'tags': 'count:12',
                'playable_in_embed': True,
                'age_limit': 0,
                'view_count': int,
                'duration': 522,
                'channel': 'kudvenkat',
                'comment_count': int,
                'channel_follower_count': int,
                'chapters': list,
                'uploader': 'kudvenkat',
                'uploader_url': 'https://www.youtube.com/@Csharp-video-tutorialsBlogspot',
                'uploader_id': '@Csharp-video-tutorialsBlogspot',
                'channel_is_verified': True,
                'heatmap': 'count:100',
                'timestamp': 1377976349,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # another example of '};' in ytInitialData
            'url': 'https://www.youtube.com/watch?v=gVfgbahppCY',
            'only_matching': True,
        },
        {
            'url': 'https://www.youtube.com/watch_popup?v=63RmMXCd_bQ',
            'only_matching': True,
        },
        {
            # https://github.com/ytdl-org/youtube-dl/pull/28094
            'url': 'OtqTfy26tG0',
            'info_dict': {
                'id': 'OtqTfy26tG0',
                'ext': 'mp4',
                'title': 'Burn Out',
                'description': 'md5:8d07b84dcbcbfb34bc12a56d968b6131',
                'upload_date': '20141120',
                'artist': 'The Cinematic Orchestra',
                'track': 'Burn Out',
                'album': 'Every Day',
                'like_count': int,
                'live_status': 'not_live',
                'alt_title': 'Burn Out',
                'duration': 614,
                'age_limit': 0,
                'view_count': int,
                'channel_url': 'https://www.youtube.com/channel/UCIzsJBIyo8hhpFm1NK0uLgw',
                'creator': 'The Cinematic Orchestra',
                'channel': 'The Cinematic Orchestra',
                'tags': ['The Cinematic Orchestra', 'Every Day', 'Burn Out'],
                'channel_id': 'UCIzsJBIyo8hhpFm1NK0uLgw',
                'availability': 'public',
                'thumbnail': 'https://i.ytimg.com/vi/OtqTfy26tG0/maxresdefault.jpg',
                'categories': ['Music'],
                'playable_in_embed': True,
                'channel_follower_count': int,
                'uploader': 'The Cinematic Orchestra',
                'comment_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # controversial video, only works with bpctr when authenticated with cookies
            'url': 'https://www.youtube.com/watch?v=nGC3D_FkCmg',
            'only_matching': True,
        },
        {
            # controversial video, requires bpctr/contentCheckOk
            'url': 'https://www.youtube.com/watch?v=SZJvDhaSDnc',
            'info_dict': {
                'id': 'SZJvDhaSDnc',
                'ext': 'mp4',
                'title': 'San Diego teen commits suicide after bullying over embarrassing video',
                'channel_id': 'UC-SJ6nODDmufqBzPBwCvYvQ',
                'upload_date': '20140716',
                'description': 'md5:acde3a73d3f133fc97e837a9f76b53b7',
                'duration': 170,
                'categories': ['News & Politics'],
                'view_count': int,
                'channel': 'CBS Mornings',
                'tags': ['suicide', 'bullying', 'video', 'cbs', 'news'],
                'thumbnail': 'https://i.ytimg.com/vi/SZJvDhaSDnc/hqdefault.jpg',
                'age_limit': 18,
                'availability': 'needs_auth',
                'channel_url': 'https://www.youtube.com/channel/UC-SJ6nODDmufqBzPBwCvYvQ',
                'like_count': int,
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel_follower_count': int,
                'uploader': 'CBS Mornings',
                'uploader_url': 'https://www.youtube.com/@CBSMornings',
                'uploader_id': '@CBSMornings',
                'comment_count': int,
                'channel_is_verified': True,
                'timestamp': 1405513526,
            },
        },
        {
            # restricted location, https://github.com/ytdl-org/youtube-dl/issues/28685
            'url': 'cBvYw8_A0vQ',
            'info_dict': {
                'id': 'cBvYw8_A0vQ',
                'ext': 'mp4',
                'title': '4K Ueno Okachimachi  Street  Scenes  上野御徒町歩き',
                'description': 'md5:ea770e474b7cd6722b4c95b833c03630',
                'upload_date': '20201120',
                'duration': 1456,
                'categories': ['Travel & Events'],
                'channel_id': 'UC3o_t8PzBmXf5S9b7GLx1Mw',
                'view_count': int,
                'channel': 'Walk around Japan',
                'tags': ['Ueno Tokyo', 'Okachimachi Tokyo', 'Ameyoko Street', 'Tokyo attraction', 'Travel in Tokyo'],
                'thumbnail': 'https://i.ytimg.com/vi/cBvYw8_A0vQ/hqdefault.jpg',
                'age_limit': 0,
                'availability': 'public',
                'channel_url': 'https://www.youtube.com/channel/UC3o_t8PzBmXf5S9b7GLx1Mw',
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel_follower_count': int,
                'uploader': 'Walk around Japan',
                'uploader_url': 'https://www.youtube.com/@walkaroundjapan7124',
                'uploader_id': '@walkaroundjapan7124',
                'timestamp': 1605884416,
            },
            'params': {
                'skip_download': True,
            },
        }, {
            # Has multiple audio streams
            'url': 'WaOKSUlf4TM',
            'only_matching': True,
        }, {
            # Requires Premium: has format 141 when requested using YTM url
            'url': 'https://music.youtube.com/watch?v=XclachpHxis',
            'only_matching': True,
        }, {
            # multiple subtitles with same lang_code
            'url': 'https://www.youtube.com/watch?v=wsQiKKfKxug',
            'only_matching': True,
        }, {
            # Force use android client fallback
            'url': 'https://www.youtube.com/watch?v=YOelRv7fMxY',
            'info_dict': {
                'id': 'YOelRv7fMxY',
                'title': 'DIGGING A SECRET TUNNEL Part 1',
                'ext': '3gp',
                'upload_date': '20210624',
                'channel_id': 'UCp68_FLety0O-n9QU6phsgw',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCp68_FLety0O-n9QU6phsgw',
                'description': 'md5:5d5991195d599b56cd0c4148907eec50',
                'duration': 596,
                'categories': ['Entertainment'],
                'view_count': int,
                'channel': 'colinfurze',
                'tags': ['Colin', 'furze', 'Terry', 'tunnel', 'underground', 'bunker'],
                'thumbnail': 'https://i.ytimg.com/vi/YOelRv7fMxY/maxresdefault.jpg',
                'age_limit': 0,
                'availability': 'public',
                'like_count': int,
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel_follower_count': int,
                'chapters': list,
                'uploader': 'colinfurze',
                'uploader_url': 'https://www.youtube.com/@colinfurze',
                'uploader_id': '@colinfurze',
                'comment_count': int,
                'channel_is_verified': True,
                'heatmap': 'count:100',
            },
            'params': {
                'format': '17',  # 3gp format available on android
                'extractor_args': {'youtube': {'player_client': ['android']}},
            },
            'skip': 'android client broken',
        },
        {
            # Skip download of additional client configs (remix client config in this case)
            'url': 'https://music.youtube.com/watch?v=MgNrAu2pzNs',
            'only_matching': True,
            'params': {
                'extractor_args': {'youtube': {'player_skip': ['configs']}},
            },
        }, {
            # shorts
            'url': 'https://www.youtube.com/shorts/BGQWPY4IigY',
            'only_matching': True,
        }, {
            'note': 'Storyboards',
            'url': 'https://www.youtube.com/watch?v=5KLPxDtMqe8',
            'info_dict': {
                'id': '5KLPxDtMqe8',
                'ext': 'mhtml',
                'format_id': 'sb0',
                'title': 'Your Brain is Plastic',
                'description': 'md5:89cd86034bdb5466cd87c6ba206cd2bc',
                'upload_date': '20140324',
                'like_count': int,
                'channel_id': 'UCZYTClx2T1of7BRZ86-8fow',
                'channel_url': 'https://www.youtube.com/channel/UCZYTClx2T1of7BRZ86-8fow',
                'view_count': int,
                'thumbnail': 'https://i.ytimg.com/vi/5KLPxDtMqe8/maxresdefault.jpg',
                'playable_in_embed': True,
                'tags': 'count:12',
                'availability': 'public',
                'channel': 'SciShow',
                'live_status': 'not_live',
                'duration': 248,
                'categories': ['Education'],
                'age_limit': 0,
                'channel_follower_count': int,
                'chapters': list,
                'uploader': 'SciShow',
                'uploader_url': 'https://www.youtube.com/@SciShow',
                'uploader_id': '@SciShow',
                'comment_count': int,
                'channel_is_verified': True,
                'heatmap': 'count:100',
                'timestamp': 1395685455,
            }, 'params': {'format': 'mhtml', 'skip_download': True},
        }, {
            # Ensure video upload_date is in UTC timezone (video was uploaded 1641170939)
            'url': 'https://www.youtube.com/watch?v=2NUZ8W2llS4',
            'info_dict': {
                'id': '2NUZ8W2llS4',
                'ext': 'mp4',
                'title': 'The NP that test your phone performance 🙂',
                'description': 'md5:144494b24d4f9dfacb97c1bbef5de84d',
                'channel_id': 'UCRqNBSOHgilHfAczlUmlWHA',
                'channel_url': 'https://www.youtube.com/channel/UCRqNBSOHgilHfAczlUmlWHA',
                'duration': 21,
                'view_count': int,
                'age_limit': 0,
                'categories': ['Gaming'],
                'tags': 'count:23',
                'playable_in_embed': True,
                'live_status': 'not_live',
                'upload_date': '20220103',
                'like_count': int,
                'availability': 'public',
                'channel': 'Leon Nguyen',
                'thumbnail': 'https://i.ytimg.com/vi_webp/2NUZ8W2llS4/maxresdefault.webp',
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': 'Leon Nguyen',
                'uploader_url': 'https://www.youtube.com/@LeonNguyen',
                'uploader_id': '@LeonNguyen',
                'heatmap': 'count:100',
                'timestamp': 1641170939,
            },
        }, {
            # date text is premiered video, ensure upload date in UTC (published 1641172509)
            'url': 'https://www.youtube.com/watch?v=mzZzzBU6lrM',
            'info_dict': {
                'id': 'mzZzzBU6lrM',
                'ext': 'mp4',
                'title': 'I Met GeorgeNotFound In Real Life...',
                'description': 'md5:978296ec9783a031738b684d4ebf302d',
                'channel_id': 'UC_8NknAFiyhOUaZqHR3lq3Q',
                'channel_url': 'https://www.youtube.com/channel/UC_8NknAFiyhOUaZqHR3lq3Q',
                'duration': 955,
                'view_count': int,
                'age_limit': 0,
                'categories': ['Entertainment'],
                'tags': 'count:26',
                'playable_in_embed': True,
                'live_status': 'not_live',
                'release_timestamp': 1641172509,
                'release_date': '20220103',
                'upload_date': '20220103',
                'like_count': int,
                'availability': 'public',
                'channel': 'Quackity',
                'thumbnail': 'https://i.ytimg.com/vi/mzZzzBU6lrM/maxresdefault.jpg',
                'channel_follower_count': int,
                'uploader': 'Quackity',
                'uploader_id': '@Quackity',
                'uploader_url': 'https://www.youtube.com/@Quackity',
                'comment_count': int,
                'channel_is_verified': True,
                'heatmap': 'count:100',
                'timestamp': 1641172509,
            },
        },
        {   # continuous livestream.
            # Upload date was 2022-07-12T05:12:29-07:00, while stream start is 2022-07-12T15:59:30+00:00
            'url': 'https://www.youtube.com/watch?v=jfKfPfyJRdk',
            'info_dict': {
                'id': 'jfKfPfyJRdk',
                'ext': 'mp4',
                'channel_id': 'UCSJ4gkVC6NrvII8umztf0Ow',
                'like_count': int,
                'uploader': 'Lofi Girl',
                'categories': ['Music'],
                'concurrent_view_count': int,
                'playable_in_embed': True,
                'timestamp': 1657627949,
                'release_date': '20220712',
                'channel_url': 'https://www.youtube.com/channel/UCSJ4gkVC6NrvII8umztf0Ow',
                'description': 'md5:13a6f76df898f5674f9127139f3df6f7',
                'age_limit': 0,
                'thumbnail': 'https://i.ytimg.com/vi/jfKfPfyJRdk/maxresdefault.jpg',
                'release_timestamp': 1657641570,
                'uploader_url': 'https://www.youtube.com/@LofiGirl',
                'channel_follower_count': int,
                'channel_is_verified': True,
                'title': r're:^lofi hip hop radio 📚 - beats to relax/study to',
                'view_count': int,
                'live_status': 'is_live',
                'tags': 'count:32',
                'channel': 'Lofi Girl',
                'availability': 'public',
                'upload_date': '20220712',
                'uploader_id': '@LofiGirl',
            },
            'params': {'skip_download': True},
        }, {
            'url': 'https://www.youtube.com/watch?v=tjjjtzRLHvA',
            'info_dict': {
                'id': 'tjjjtzRLHvA',
                'ext': 'mp4',
                'title': 'ハッシュタグ無し };if window.ytcsi',
                'upload_date': '20220323',
                'like_count': int,
                'availability': 'unlisted',
                'channel': 'Lesmiscore',
                'thumbnail': r're:^https?://.*\.jpg',
                'age_limit': 0,
                'categories': ['Music'],
                'view_count': int,
                'description': '',
                'channel_url': 'https://www.youtube.com/channel/UCdqltm_7iv1Vs6kp6Syke5A',
                'channel_id': 'UCdqltm_7iv1Vs6kp6Syke5A',
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel_follower_count': int,
                'duration': 6,
                'tags': [],
                'uploader_id': '@lesmiscore',
                'uploader': 'Lesmiscore',
                'uploader_url': 'https://www.youtube.com/@lesmiscore',
                'timestamp': 1648005313,
            },
        }, {
            # Prefer primary title+description language metadata by default
            # Do not prefer translated description if primary is empty
            'url': 'https://www.youtube.com/watch?v=el3E4MbxRqQ',
            'info_dict': {
                'id': 'el3E4MbxRqQ',
                'ext': 'mp4',
                'title': 'dlp test video 2 - primary sv no desc',
                'description': '',
                'channel': 'cole-dlp-test-acc',
                'tags': [],
                'view_count': int,
                'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
                'like_count': int,
                'playable_in_embed': True,
                'availability': 'unlisted',
                'thumbnail': r're:^https?://.*\.jpg',
                'age_limit': 0,
                'duration': 5,
                'live_status': 'not_live',
                'upload_date': '20220908',
                'categories': ['People & Blogs'],
                'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
                'uploader_url': 'https://www.youtube.com/@coletdjnz',
                'uploader_id': '@coletdjnz',
                'uploader': 'cole-dlp-test-acc',
                'timestamp': 1662677394,
            },
            'params': {'skip_download': True},
        }, {
            # Extractor argument: prefer translated title+description
            'url': 'https://www.youtube.com/watch?v=gHKT4uU8Zng',
            'info_dict': {
                'id': 'gHKT4uU8Zng',
                'ext': 'mp4',
                'channel': 'cole-dlp-test-acc',
                'tags': [],
                'duration': 5,
                'live_status': 'not_live',
                'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
                'upload_date': '20220729',
                'view_count': int,
                'categories': ['People & Blogs'],
                'thumbnail': r're:^https?://.*\.jpg',
                'title': 'dlp test video title translated (fr)',
                'availability': 'public',
                'age_limit': 0,
                'description': 'dlp test video description translated (fr)',
                'playable_in_embed': True,
                'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
                'uploader_url': 'https://www.youtube.com/@coletdjnz',
                'uploader_id': '@coletdjnz',
                'uploader': 'cole-dlp-test-acc',
                'timestamp': 1659073275,
                'like_count': int,
            },
            'params': {'skip_download': True, 'extractor_args': {'youtube': {'lang': ['fr']}}},
            'expected_warnings': [r'Preferring "fr" translated fields'],
        }, {
            'note': '6 channel audio',
            'url': 'https://www.youtube.com/watch?v=zgdo7-RRjgo',
            'only_matching': True,
        }, {
            'note': 'Multiple HLS formats with same itag',
            'url': 'https://www.youtube.com/watch?v=kX3nB4PpJko',
            'info_dict': {
                'id': 'kX3nB4PpJko',
                'ext': 'mp4',
                'categories': ['Entertainment'],
                'description': 'md5:e8031ff6e426cdb6a77670c9b81f6fa6',
                'live_status': 'not_live',
                'duration': 937,
                'channel_follower_count': int,
                'thumbnail': 'https://i.ytimg.com/vi_webp/kX3nB4PpJko/maxresdefault.webp',
                'title': 'Last To Take Hand Off Jet, Keeps It!',
                'channel': 'MrBeast',
                'playable_in_embed': True,
                'view_count': int,
                'upload_date': '20221112',
                'channel_url': 'https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA',
                'age_limit': 0,
                'availability': 'public',
                'channel_id': 'UCX6OQ3DkcsbYNE6H8uQQuVA',
                'like_count': int,
                'tags': [],
                'uploader': 'MrBeast',
                'uploader_url': 'https://www.youtube.com/@MrBeast',
                'uploader_id': '@MrBeast',
                'comment_count': int,
                'channel_is_verified': True,
                'heatmap': 'count:100',
            },
            'params': {'extractor_args': {'youtube': {'player_client': ['ios']}}, 'format': '233-1'},
        }, {
            'note': 'Audio formats with Dynamic Range Compression',
            'url': 'https://www.youtube.com/watch?v=Tq92D6wQ1mg',
            'info_dict': {
                'id': 'Tq92D6wQ1mg',
                'ext': 'webm',
                'title': '[MMD] Adios - EVERGLOW [+Motion DL]',
                'channel_url': 'https://www.youtube.com/channel/UC1yoRdFoFJaCY-AGfD9W0wQ',
                'channel_id': 'UC1yoRdFoFJaCY-AGfD9W0wQ',
                'channel_follower_count': int,
                'description': 'md5:17eccca93a786d51bc67646756894066',
                'upload_date': '20191228',
                'tags': ['mmd', 'dance', 'mikumikudance', 'kpop', 'vtuber'],
                'playable_in_embed': True,
                'like_count': int,
                'categories': ['Entertainment'],
                'thumbnail': 'https://i.ytimg.com/vi/Tq92D6wQ1mg/sddefault.jpg',
                'age_limit': 18,
                'channel': 'Projekt Melody',
                'view_count': int,
                'availability': 'needs_auth',
                'comment_count': int,
                'live_status': 'not_live',
                'duration': 106,
                'uploader': 'Projekt Melody',
                'uploader_id': '@ProjektMelody',
                'uploader_url': 'https://www.youtube.com/@ProjektMelody',
                'timestamp': 1577508724,
            },
            'params': {'extractor_args': {'youtube': {'player_client': ['tv_embedded']}}, 'format': '251-drc'},
        },
        {
            'url': 'https://www.youtube.com/live/qVv6vCqciTM',
            'info_dict': {
                'id': 'qVv6vCqciTM',
                'ext': 'mp4',
                'age_limit': 0,
                'comment_count': int,
                'chapters': 'count:13',
                'upload_date': '20221223',
                'thumbnail': 'https://i.ytimg.com/vi/qVv6vCqciTM/maxresdefault.jpg',
                'channel_url': 'https://www.youtube.com/channel/UCIdEIHpS0TdkqRkHL5OkLtA',
                'like_count': int,
                'release_date': '20221223',
                'tags': ['Vtuber', '月ノ美兎', '名取さな', 'にじさんじ', 'クリスマス', '3D配信'],
                'title': '【 #インターネット女クリスマス 】3Dで歌ってはしゃぐインターネットの女たち【月ノ美兎/名取さな】',
                'view_count': int,
                'playable_in_embed': True,
                'duration': 4438,
                'availability': 'public',
                'channel_follower_count': int,
                'channel_id': 'UCIdEIHpS0TdkqRkHL5OkLtA',
                'categories': ['Entertainment'],
                'live_status': 'was_live',
                'release_timestamp': 1671793345,
                'channel': 'さなちゃんねる',
                'description': 'md5:6aebf95cc4a1d731aebc01ad6cc9806d',
                'uploader': 'さなちゃんねる',
                'uploader_url': 'https://www.youtube.com/@sana_natori',
                'uploader_id': '@sana_natori',
                'channel_is_verified': True,
                'heatmap': 'count:100',
                'timestamp': 1671798112,
            },
        },
        {
            # Fallbacks when webpage and web client is unavailable
            'url': 'https://www.youtube.com/watch?v=wSSmNUl9Snw',
            'info_dict': {
                'id': 'wSSmNUl9Snw',
                'ext': 'mp4',
                # 'categories': ['Science & Technology'],
                'view_count': int,
                'chapters': 'count:2',
                'channel': 'Scott Manley',
                'like_count': int,
                'age_limit': 0,
                # 'availability': 'public',
                'channel_follower_count': int,
                'live_status': 'not_live',
                'upload_date': '20170831',
                'duration': 682,
                'tags': 'count:8',
                'uploader_url': 'https://www.youtube.com/@scottmanley',
                'description': 'md5:f4bed7b200404b72a394c2f97b782c02',
                'uploader': 'Scott Manley',
                'uploader_id': '@scottmanley',
                'title': 'The Computer Hack That Saved Apollo 14',
                'channel_id': 'UCxzC4EngIsMrPmbm6Nxvb-A',
                'thumbnail': r're:^https?://.*\.webp',
                'channel_url': 'https://www.youtube.com/channel/UCxzC4EngIsMrPmbm6Nxvb-A',
                'playable_in_embed': True,
                'comment_count': int,
                'channel_is_verified': True,
                'heatmap': 'count:100',
            },
            'params': {
                'extractor_args': {'youtube': {'player_client': ['ios'], 'player_skip': ['webpage']}},
            },
        },
    ]

    _WEBPAGE_TESTS = [
        # YouTube <object> embed
        {
            'url': 'http://www.improbable.com/2017/04/03/untrained-modern-youths-and-ancient-masters-in-selfie-portraits/',
            'md5': '873c81d308b979f0e23ee7e620b312a3',
            'info_dict': {
                'id': 'msN87y-iEx0',
                'ext': 'mp4',
                'title': 'Feynman: Mirrors FUN TO IMAGINE 6',
                'upload_date': '20080526',
                'description': 'md5:873c81d308b979f0e23ee7e620b312a3',
                'age_limit': 0,
                'tags': ['feynman', 'mirror', 'science', 'physics', 'imagination', 'fun', 'cool', 'puzzle'],
                'channel_id': 'UCCeo--lls1vna5YJABWAcVA',
                'playable_in_embed': True,
                'thumbnail': 'https://i.ytimg.com/vi/msN87y-iEx0/hqdefault.jpg',
                'like_count': int,
                'comment_count': int,
                'channel': 'Christopher Sykes',
                'live_status': 'not_live',
                'channel_url': 'https://www.youtube.com/channel/UCCeo--lls1vna5YJABWAcVA',
                'availability': 'public',
                'duration': 195,
                'view_count': int,
                'categories': ['Science & Technology'],
                'channel_follower_count': int,
                'uploader': 'Christopher Sykes',
                'uploader_url': 'https://www.youtube.com/@ChristopherSykesDocumentaries',
                'uploader_id': '@ChristopherSykesDocumentaries',
                'heatmap': 'count:100',
                'timestamp': 1211825920,
            },
            'params': {
                'skip_download': True,
            },
        },
    ]

    @classmethod
    def suitable(cls, url):
        from ..utils import parse_qs

        qs = parse_qs(url)
        if qs.get('list', [None])[0]:
            return False
        return super().suitable(url)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._code_cache = {}
        self._player_cache = {}

    def _prepare_live_from_start_formats(self, formats, video_id, live_start_time, url, webpage_url, smuggled_data, is_live):
        lock = threading.Lock()
        start_time = time.time()
        formats = [f for f in formats if f.get('is_from_start')]

        def refetch_manifest(format_id, delay):
            nonlocal formats, start_time, is_live
            if time.time() <= start_time + delay:
                return

            _, _, prs, player_url = self._download_player_responses(url, smuggled_data, video_id, webpage_url)
            video_details = traverse_obj(prs, (..., 'videoDetails'), expected_type=dict)
            microformats = traverse_obj(
                prs, (..., 'microformat', 'playerMicroformatRenderer'),
                expected_type=dict)
            _, live_status, _, formats, _ = self._list_formats(video_id, microformats, video_details, prs, player_url)
            is_live = live_status == 'is_live'
            start_time = time.time()

        def mpd_feed(format_id, delay):
            """
            @returns (manifest_url, manifest_stream_number, is_live) or None
            """
            for retry in self.RetryManager(fatal=False):
                with lock:
                    refetch_manifest(format_id, delay)

                f = next((f for f in formats if f['format_id'] == format_id), None)
                if not f:
                    if not is_live:
                        retry.error = f'{video_id}: Video is no longer live'
                    else:
                        retry.error = f'Cannot find refreshed manifest for format {format_id}{bug_reports_message()}'
                    continue
                return f['manifest_url'], f['manifest_stream_number'], is_live
            return None

        for f in formats:
            f['is_live'] = is_live
            gen = functools.partial(self._live_dash_fragments, video_id, f['format_id'],
                                    live_start_time, mpd_feed, not is_live and f.copy())
            if is_live:
                f['fragments'] = gen
                f['protocol'] = 'http_dash_segments_generator'
            else:
                f['fragments'] = LazyList(gen({}))
                del f['is_from_start']

    def _live_dash_fragments(self, video_id, format_id, live_start_time, mpd_feed, manifestless_orig_fmt, ctx):
        FETCH_SPAN, MAX_DURATION = 5, 432000

        mpd_url, stream_number, is_live = None, None, True

        begin_index = 0
        download_start_time = ctx.get('start') or time.time()

        lack_early_segments = download_start_time - (live_start_time or download_start_time) > MAX_DURATION
        if lack_early_segments:
            self.report_warning(bug_reports_message(
                'Starting download from the last 120 hours of the live stream since '
                'YouTube does not have data before that. If you think this is wrong,'), only_once=True)
            lack_early_segments = True

        known_idx, no_fragment_score, last_segment_url = begin_index, 0, None
        fragments, fragment_base_url = None, None

        def _extract_sequence_from_mpd(refresh_sequence, immediate):
            nonlocal mpd_url, stream_number, is_live, no_fragment_score, fragments, fragment_base_url
            # Obtain from MPD's maximum seq value
            old_mpd_url = mpd_url
            last_error = ctx.pop('last_error', None)
            expire_fast = immediate or last_error and isinstance(last_error, HTTPError) and last_error.status == 403
            mpd_url, stream_number, is_live = (mpd_feed(format_id, 5 if expire_fast else 18000)
                                               or (mpd_url, stream_number, False))
            if not refresh_sequence:
                if expire_fast and not is_live:
                    return False, last_seq
                elif old_mpd_url == mpd_url:
                    return True, last_seq
            if manifestless_orig_fmt:
                fmt_info = manifestless_orig_fmt
            else:
                try:
                    fmts, _ = self._extract_mpd_formats_and_subtitles(
                        mpd_url, None, note=False, errnote=False, fatal=False)
                except ExtractorError:
                    fmts = None
                if not fmts:
                    no_fragment_score += 2
                    return False, last_seq
                fmt_info = next(x for x in fmts if x['manifest_stream_number'] == stream_number)
            fragments = fmt_info['fragments']
            fragment_base_url = fmt_info['fragment_base_url']
            assert fragment_base_url

            _last_seq = int(re.search(r'(?:/|^)sq/(\d+)', fragments[-1]['path']).group(1))
            return True, _last_seq

        self.write_debug(f'[{video_id}] Generating fragments for format {format_id}')
        while is_live:
            fetch_time = time.time()
            if no_fragment_score > 30:
                return
            if last_segment_url:
                # Obtain from "X-Head-Seqnum" header value from each segment
                try:
                    urlh = self._request_webpage(
                        last_segment_url, None, note=False, errnote=False, fatal=False)
                except ExtractorError:
                    urlh = None
                last_seq = try_get(urlh, lambda x: int_or_none(x.headers['X-Head-Seqnum']))
                if last_seq is None:
                    no_fragment_score += 2
                    last_segment_url = None
                    continue
            else:
                should_continue, last_seq = _extract_sequence_from_mpd(True, no_fragment_score > 15)
                no_fragment_score += 2
                if not should_continue:
                    continue

            if known_idx > last_seq:
                last_segment_url = None
                continue

            last_seq += 1

            if begin_index < 0 and known_idx < 0:
                # skip from the start when it's negative value
                known_idx = last_seq + begin_index
            if lack_early_segments:
                known_idx = max(known_idx, last_seq - int(MAX_DURATION // fragments[-1]['duration']))
            try:
                for idx in range(known_idx, last_seq):
                    # do not update sequence here or you'll get skipped some part of it
                    should_continue, _ = _extract_sequence_from_mpd(False, False)
                    if not should_continue:
                        known_idx = idx - 1
                        raise ExtractorError('breaking out of outer loop')
                    last_segment_url = urljoin(fragment_base_url, f'sq/{idx}')
                    yield {
                        'url': last_segment_url,
                        'fragment_count': last_seq,
                    }
                if known_idx == last_seq:
                    no_fragment_score += 5
                else:
                    no_fragment_score = 0
                known_idx = last_seq
            except ExtractorError:
                continue

            if manifestless_orig_fmt:
                # Stop at the first iteration if running for post-live manifestless;
                # fragment count no longer increase since it starts
                break

            time.sleep(max(0, FETCH_SPAN + fetch_time - time.time()))

    def _extract_player_url(self, *ytcfgs, webpage=None):
        player_url = traverse_obj(
            ytcfgs, (..., 'PLAYER_JS_URL'), (..., 'WEB_PLAYER_CONTEXT_CONFIGS', ..., 'jsUrl'),
            get_all=False, expected_type=str)
        if not player_url:
            return
        return urljoin('https://www.youtube.com', player_url)

    def _download_player_url(self, video_id, fatal=False):
        res = self._download_webpage(
            'https://www.youtube.com/iframe_api',
            note='Downloading iframe API JS', video_id=video_id, fatal=fatal)
        if res:
            player_version = self._search_regex(
                r'player\\?/([0-9a-fA-F]{8})\\?/', res, 'player version', fatal=fatal)
            if player_version:
                return f'https://www.youtube.com/s/player/{player_version}/player_ias.vflset/en_US/base.js'

    def _signature_cache_id(self, example_sig):
        """ Return a string representation of a signature """
        return '.'.join(str(len(part)) for part in example_sig.split('.'))

    @classmethod
    def _extract_player_info(cls, player_url):
        for player_re in cls._PLAYER_INFO_RE:
            id_m = re.search(player_re, player_url)
            if id_m:
                break
        else:
            raise ExtractorError(f'Cannot identify player {player_url!r}')
        return id_m.group('id')

    def _load_player(self, video_id, player_url, fatal=True):
        player_id = self._extract_player_info(player_url)
        if player_id not in self._code_cache:
            code = self._download_webpage(
                player_url, video_id, fatal=fatal,
                note='Downloading player ' + player_id,
                errnote=f'Download of {player_url} failed')
            if code:
                self._code_cache[player_id] = code
        return self._code_cache.get(player_id)

    def _extract_signature_function(self, video_id, player_url, example_sig):
        player_id = self._extract_player_info(player_url)

        # Read from filesystem cache
        func_id = f'js_{player_id}_{self._signature_cache_id(example_sig)}'
        assert os.path.basename(func_id) == func_id

        self.write_debug(f'Extracting signature function {func_id}')
        cache_spec, code = self.cache.load('youtube-sigfuncs', func_id), None

        if not cache_spec:
            code = self._load_player(video_id, player_url)
        if code:
            res = self._parse_sig_js(code)
            test_string = ''.join(map(chr, range(len(example_sig))))
            cache_spec = [ord(c) for c in res(test_string)]
            self.cache.store('youtube-sigfuncs', func_id, cache_spec)

        return lambda s: ''.join(s[i] for i in cache_spec)

    def _print_sig_code(self, func, example_sig):
        if not self.get_param('youtube_print_sig_code'):
            return

        def gen_sig_code(idxs):
            def _genslice(start, end, step):
                starts = '' if start == 0 else str(start)
                ends = (':%d' % (end + step)) if end + step >= 0 else ':'
                steps = '' if step == 1 else (':%d' % step)
                return f's[{starts}{ends}{steps}]'

            step = None
            # Quelch pyflakes warnings - start will be set when step is set
            start = '(Never used)'
            for i, prev in zip(idxs[1:], idxs[:-1]):
                if step is not None:
                    if i - prev == step:
                        continue
                    yield _genslice(start, prev, step)
                    step = None
                    continue
                if i - prev in [-1, 1]:
                    step = i - prev
                    start = prev
                    continue
                else:
                    yield 's[%d]' % prev
            if step is None:
                yield 's[%d]' % i
            else:
                yield _genslice(start, i, step)

        test_string = ''.join(map(chr, range(len(example_sig))))
        cache_res = func(test_string)
        cache_spec = [ord(c) for c in cache_res]
        expr_code = ' + '.join(gen_sig_code(cache_spec))
        signature_id_tuple = '({})'.format(', '.join(str(len(p)) for p in example_sig.split('.')))
        code = (f'if tuple(len(p) for p in s.split(\'.\')) == {signature_id_tuple}:\n'
                f'    return {expr_code}\n')
        self.to_screen('Extracted signature function:\n' + code)

    def _parse_sig_js(self, jscode):
        funcname = self._search_regex(
            (r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bm=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(h\.s\)\)',
             r'\bc&&\(c=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(c\)\)',
             r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2,})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)(?:;[a-zA-Z0-9$]{2}\.[a-zA-Z0-9$]{2}\(a,\d+\))?',
             r'(?P<sig>[a-zA-Z0-9$]+)\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
             # Obsolete patterns
             r'("|\')signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(',
             r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\('),
            jscode, 'Initial JS player signature function name', group='sig')

        jsi = JSInterpreter(jscode)
        initial_function = jsi.extract_function(funcname)
        return lambda s: initial_function([s])

    def _cached(self, func, *cache_id):
        def inner(*args, **kwargs):
            if cache_id not in self._player_cache:
                try:
                    self._player_cache[cache_id] = func(*args, **kwargs)
                except ExtractorError as e:
                    self._player_cache[cache_id] = e
                except Exception as e:
                    self._player_cache[cache_id] = ExtractorError(traceback.format_exc(), cause=e)

            ret = self._player_cache[cache_id]
            if isinstance(ret, Exception):
                raise ret
            return ret
        return inner

    def _decrypt_signature(self, s, video_id, player_url):
        """Turn the encrypted s field into a working signature"""
        extract_sig = self._cached(
            self._extract_signature_function, 'sig', player_url, self._signature_cache_id(s))
        func = extract_sig(video_id, player_url, s)
        self._print_sig_code(func, s)
        return func(s)

    def _decrypt_nsig(self, s, video_id, player_url):
        """Turn the encrypted n field into a working signature"""
        if player_url is None:
            raise ExtractorError('Cannot decrypt nsig without player_url')
        player_url = urljoin('https://www.youtube.com', player_url)

        try:
            jsi, player_id, func_code = self._extract_n_function_code(video_id, player_url)
        except ExtractorError as e:
            raise ExtractorError('Unable to extract nsig function code', cause=e)
        if self.get_param('youtube_print_sig_code'):
            self.to_screen(f'Extracted nsig function from {player_id}:\n{func_code[1]}\n')

        try:
            extract_nsig = self._cached(self._extract_n_function_from_code, 'nsig func', player_url)
            ret = extract_nsig(jsi, func_code)(s)
        except JSInterpreter.Exception as e:
            try:
                jsi = PhantomJSwrapper(self, timeout=5000)
            except ExtractorError:
                raise e
            self.report_warning(
                f'Native nsig extraction failed: Trying with PhantomJS\n'
                f'         n = {s} ; player = {player_url}', video_id)
            self.write_debug(e, only_once=True)

            args, func_body = func_code
            ret = jsi.execute(
                f'console.log(function({", ".join(args)}) {{ {func_body} }}({s!r}));',
                video_id=video_id, note='Executing signature code').strip()

        self.write_debug(f'Decrypted nsig {s} => {ret}')
        return ret

    def _extract_n_function_name(self, jscode):
        funcname, idx = self._search_regex(
            r'''(?x)
            (?:
                \.get\("n"\)\)&&\(b=|
                (?:
                    b=String\.fromCharCode\(110\)|
                    ([a-zA-Z0-9$.]+)&&\(b="nn"\[\+\1\]
                ),c=a\.get\(b\)\)&&\(c=
            )
            (?P<nfunc>[a-zA-Z0-9$]+)(?:\[(?P<idx>\d+)\])?\([a-zA-Z0-9]\)''',
            jscode, 'Initial JS player n function name', group=('nfunc', 'idx'))
        if not idx:
            return funcname

        return json.loads(js_to_json(self._search_regex(
            rf'var {re.escape(funcname)}\s*=\s*(\[.+?\])\s*[,;]', jscode,
            f'Initial JS player n function list ({funcname}.{idx})')))[int(idx)]

    def _extract_n_function_code(self, video_id, player_url):
        player_id = self._extract_player_info(player_url)
        func_code = self.cache.load('youtube-nsig', player_id, min_ver='2024.07.09')
        jscode = func_code or self._load_player(video_id, player_url)
        jsi = JSInterpreter(jscode)

        if func_code:
            return jsi, player_id, func_code

        func_name = self._extract_n_function_name(jscode)

        func_code = jsi.extract_function_code(func_name)

        self.cache.store('youtube-nsig', player_id, func_code)
        return jsi, player_id, func_code

    def _extract_n_function_from_code(self, jsi, func_code):
        func = jsi.extract_function_from_code(*func_code)

        def extract_nsig(s):
            try:
                ret = func([s])
            except JSInterpreter.Exception:
                raise
            except Exception as e:
                raise JSInterpreter.Exception(traceback.format_exc(), cause=e)

            if ret.startswith('enhanced_except_'):
                raise JSInterpreter.Exception('Signature function returned an exception')
            return ret

        return extract_nsig

    def _extract_signature_timestamp(self, video_id, player_url, ytcfg=None, fatal=False):
        """
        Extract signatureTimestamp (sts)
        Required to tell API what sig/player version is in use.
        """
        sts = None
        if isinstance(ytcfg, dict):
            sts = int_or_none(ytcfg.get('STS'))

        if not sts:
            # Attempt to extract from player
            if player_url is None:
                error_msg = 'Cannot extract signature timestamp without player_url.'
                if fatal:
                    raise ExtractorError(error_msg)
                self.report_warning(error_msg)
                return
            code = self._load_player(video_id, player_url, fatal=fatal)
            if code:
                sts = int_or_none(self._search_regex(
                    r'(?:signatureTimestamp|sts)\s*:\s*(?P<sts>[0-9]{5})', code,
                    'JS player signature timestamp', group='sts', fatal=fatal))
        return sts

    def _mark_watched(self, video_id, player_responses):
        for is_full, key in enumerate(('videostatsPlaybackUrl', 'videostatsWatchtimeUrl')):
            label = 'fully ' if is_full else ''
            url = get_first(player_responses, ('playbackTracking', key, 'baseUrl'),
                            expected_type=url_or_none)
            if not url:
                self.report_warning(f'Unable to mark {label}watched')
                return
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)

            # cpn generation algorithm is reverse engineered from base.js.
            # In fact it works even with dummy cpn.
            CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
            cpn = ''.join(CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(16))

            # # more consistent results setting it to right before the end
            video_length = [str(float((qs.get('len') or ['1.5'])[0]) - 1)]

            qs.update({
                'ver': ['2'],
                'cpn': [cpn],
                'cmt': video_length,
                'el': 'detailpage',  # otherwise defaults to "shorts"
            })

            if is_full:
                # these seem to mark watchtime "history" in the real world
                # they're required, so send in a single value
                qs.update({
                    'st': 0,
                    'et': video_length,
                })

            url = urllib.parse.urlunparse(
                parsed_url._replace(query=urllib.parse.urlencode(qs, True)))

            self._download_webpage(
                url, video_id, f'Marking {label}watched',
                'Unable to mark watched', fatal=False)

    @classmethod
    def _extract_from_webpage(cls, url, webpage):
        # Invidious Instances
        # https://github.com/yt-dlp/yt-dlp/issues/195
        # https://github.com/iv-org/invidious/pull/1730
        mobj = re.search(
            r'<link rel="alternate" href="(?P<url>https://www\.youtube\.com/watch\?v=[0-9A-Za-z_-]{11})"',
            webpage)
        if mobj:
            yield cls.url_result(mobj.group('url'), cls)
            raise cls.StopExtraction

        yield from super()._extract_from_webpage(url, webpage)

        # lazyYT YouTube embed
        for id_ in re.findall(r'class="lazyYT" data-youtube-id="([^"]+)"', webpage):
            yield cls.url_result(unescapeHTML(id_), cls, id_)

        # Wordpress "YouTube Video Importer" plugin
        for m in re.findall(r'''(?x)<div[^>]+
                class=(?P<q1>[\'"])[^\'"]*\byvii_single_video_player\b[^\'"]*(?P=q1)[^>]+
                data-video_id=(?P<q2>[\'"])([^\'"]+)(?P=q2)''', webpage):
            yield cls.url_result(m[-1], cls, m[-1])

    @classmethod
    def extract_id(cls, url):
        video_id = cls.get_temp_id(url)
        if not video_id:
            raise ExtractorError(f'Invalid URL: {url}')
        return video_id

    def _extract_chapters_from_json(self, data, duration):
        chapter_list = traverse_obj(
            data, (
                'playerOverlays', 'playerOverlayRenderer', 'decoratedPlayerBarRenderer',
                'decoratedPlayerBarRenderer', 'playerBar', 'chapteredPlayerBarRenderer', 'chapters',
            ), expected_type=list)

        return self._extract_chapters_helper(
            chapter_list,
            start_function=lambda chapter: float_or_none(
                traverse_obj(chapter, ('chapterRenderer', 'timeRangeStartMillis')), scale=1000),
            title_function=lambda chapter: traverse_obj(
                chapter, ('chapterRenderer', 'title', 'simpleText'), expected_type=str),
            duration=duration)

    def _extract_chapters_from_engagement_panel(self, data, duration):
        content_list = traverse_obj(
            data,
            ('engagementPanels', ..., 'engagementPanelSectionListRenderer', 'content', 'macroMarkersListRenderer', 'contents'),
            expected_type=list)
        chapter_time = lambda chapter: parse_duration(self._get_text(chapter, 'timeDescription'))
        chapter_title = lambda chapter: self._get_text(chapter, 'title')

        return next(filter(None, (
            self._extract_chapters_helper(traverse_obj(contents, (..., 'macroMarkersListItemRenderer')),
                                          chapter_time, chapter_title, duration)
            for contents in content_list)), [])

    def _extract_heatmap(self, data):
        return traverse_obj(data, (
            'frameworkUpdates', 'entityBatchUpdate', 'mutations',
            lambda _, v: v['payload']['macroMarkersListEntity']['markersList']['markerType'] == 'MARKER_TYPE_HEATMAP',
            'payload', 'macroMarkersListEntity', 'markersList', 'markers', ..., {
                'start_time': ('startMillis', {functools.partial(float_or_none, scale=1000)}),
                'end_time': {lambda x: (int(x['startMillis']) + int(x['durationMillis'])) / 1000},
                'value': ('intensityScoreNormalized', {float_or_none}),
            })) or None

    def _extract_comment(self, entities, parent=None):
        comment_entity_payload = get_first(entities, ('payload', 'commentEntityPayload', {dict}))
        if not (comment_id := traverse_obj(comment_entity_payload, ('properties', 'commentId', {str}))):
            return

        toolbar_entity_payload = get_first(entities, ('payload', 'engagementToolbarStateEntityPayload', {dict}))
        time_text = traverse_obj(comment_entity_payload, ('properties', 'publishedTime', {str})) or ''

        return {
            'id': comment_id,
            'parent': parent or 'root',
            **traverse_obj(comment_entity_payload, {
                'text': ('properties', 'content', 'content', {str}),
                'like_count': ('toolbar', 'likeCountA11y', {parse_count}),
                'author_id': ('author', 'channelId', {self.ucid_or_none}),
                'author': ('author', 'displayName', {str}),
                'author_thumbnail': ('author', 'avatarThumbnailUrl', {url_or_none}),
                'author_is_uploader': ('author', 'isCreator', {bool}),
                'author_is_verified': ('author', 'isVerified', {bool}),
                'author_url': ('author', 'channelCommand', 'innertubeCommand', (
                    ('browseEndpoint', 'canonicalBaseUrl'), ('commandMetadata', 'webCommandMetadata', 'url'),
                ), {lambda x: urljoin('https://www.youtube.com', x)}),
            }, get_all=False),
            'is_favorited': (None if toolbar_entity_payload is None else
                             toolbar_entity_payload.get('heartState') == 'TOOLBAR_HEART_STATE_HEARTED'),
            '_time_text': time_text,  # FIXME: non-standard, but we need a way of showing that it is an estimate.
            'timestamp': self._parse_time_text(time_text),
        }

    def _extract_comment_old(self, comment_renderer, parent=None):
        comment_id = comment_renderer.get('commentId')
        if not comment_id:
            return

        info = {
            'id': comment_id,
            'text': self._get_text(comment_renderer, 'contentText'),
            'like_count': self._get_count(comment_renderer, 'voteCount'),
            'author_id': traverse_obj(comment_renderer, ('authorEndpoint', 'browseEndpoint', 'browseId', {self.ucid_or_none})),
            'author': self._get_text(comment_renderer, 'authorText'),
            'author_thumbnail': traverse_obj(comment_renderer, ('authorThumbnail', 'thumbnails', -1, 'url', {url_or_none})),
            'parent': parent or 'root',
        }

        # Timestamp is an estimate calculated from the current time and time_text
        time_text = self._get_text(comment_renderer, 'publishedTimeText') or ''
        timestamp = self._parse_time_text(time_text)

        info.update({
            # FIXME: non-standard, but we need a way of showing that it is an estimate.
            '_time_text': time_text,
            'timestamp': timestamp,
        })

        info['author_url'] = urljoin(
            'https://www.youtube.com', traverse_obj(comment_renderer, ('authorEndpoint', (
                ('browseEndpoint', 'canonicalBaseUrl'), ('commandMetadata', 'webCommandMetadata', 'url'))),
                expected_type=str, get_all=False))

        author_is_uploader = traverse_obj(comment_renderer, 'authorIsChannelOwner')
        if author_is_uploader is not None:
            info['author_is_uploader'] = author_is_uploader

        comment_abr = traverse_obj(
            comment_renderer, ('actionButtons', 'commentActionButtonsRenderer'), expected_type=dict)
        if comment_abr is not None:
            info['is_favorited'] = 'creatorHeart' in comment_abr

        badges = self._extract_badges([traverse_obj(comment_renderer, 'authorCommentBadge')])
        if self._has_badge(badges, BadgeType.VERIFIED):
            info['author_is_verified'] = True

        is_pinned = traverse_obj(comment_renderer, 'pinnedCommentBadge')
        if is_pinned:
            info['is_pinned'] = True

        return info

    def _comment_entries(self, root_continuation_data, ytcfg, video_id, parent=None, tracker=None):

        get_single_config_arg = lambda c: self._configuration_arg(c, [''])[0]

        def extract_header(contents):
            _continuation = None
            for content in contents:
                comments_header_renderer = traverse_obj(content, 'commentsHeaderRenderer')
                expected_comment_count = self._get_count(
                    comments_header_renderer, 'countText', 'commentsCount')

                if expected_comment_count is not None:
                    tracker['est_total'] = expected_comment_count
                    self.to_screen(f'Downloading ~{expected_comment_count} comments')
                comment_sort_index = int(get_single_config_arg('comment_sort') != 'top')  # 1 = new, 0 = top

                sort_menu_item = try_get(
                    comments_header_renderer,
                    lambda x: x['sortMenu']['sortFilterSubMenuRenderer']['subMenuItems'][comment_sort_index], dict) or {}
                sort_continuation_ep = sort_menu_item.get('serviceEndpoint') or {}

                _continuation = self._extract_continuation_ep_data(sort_continuation_ep) or self._extract_continuation(sort_menu_item)
                if not _continuation:
                    continue

                sort_text = str_or_none(sort_menu_item.get('title'))
                if not sort_text:
                    sort_text = 'top comments' if comment_sort_index == 0 else 'newest first'
                self.to_screen(f'Sorting comments by {sort_text.lower()}')
                break
            return _continuation

        def extract_thread(contents, entity_payloads):
            if not parent:
                tracker['current_page_thread'] = 0
            for content in contents:
                if not parent and tracker['total_parent_comments'] >= max_parents:
                    yield
                comment_thread_renderer = try_get(content, lambda x: x['commentThreadRenderer'])

                # old comment format
                if not entity_payloads:
                    comment_renderer = get_first(
                        (comment_thread_renderer, content), [['commentRenderer', ('comment', 'commentRenderer')]],
                        expected_type=dict, default={})

                    comment = self._extract_comment_old(comment_renderer, parent)

                # new comment format
                else:
                    view_model = (
                        traverse_obj(comment_thread_renderer, ('commentViewModel', 'commentViewModel', {dict}))
                        or traverse_obj(content, ('commentViewModel', {dict})))
                    comment_keys = traverse_obj(view_model, (('commentKey', 'toolbarStateKey'), {str}))
                    if not comment_keys:
                        continue
                    entities = traverse_obj(entity_payloads, lambda _, v: v['entityKey'] in comment_keys)
                    comment = self._extract_comment(entities, parent)
                    if comment:
                        comment['is_pinned'] = traverse_obj(view_model, ('pinnedText', {str})) is not None

                if not comment:
                    continue
                comment_id = comment['id']

                if comment.get('is_pinned'):
                    tracker['pinned_comment_ids'].add(comment_id)
                # Sometimes YouTube may break and give us infinite looping comments.
                # See: https://github.com/yt-dlp/yt-dlp/issues/6290
                if comment_id in tracker['seen_comment_ids']:
                    if comment_id in tracker['pinned_comment_ids'] and not comment.get('is_pinned'):
                        # Pinned comments may appear a second time in newest first sort
                        # See: https://github.com/yt-dlp/yt-dlp/issues/6712
                        continue
                    self.report_warning(
                        'Detected YouTube comments looping. Stopping comment extraction '
                        f'{"for this thread" if parent else ""} as we probably cannot get any more.')
                    yield
                else:
                    tracker['seen_comment_ids'].add(comment['id'])

                tracker['running_total'] += 1
                tracker['total_reply_comments' if parent else 'total_parent_comments'] += 1
                yield comment

                # Attempt to get the replies
                comment_replies_renderer = try_get(
                    comment_thread_renderer, lambda x: x['replies']['commentRepliesRenderer'], dict)

                if comment_replies_renderer:
                    tracker['current_page_thread'] += 1
                    comment_entries_iter = self._comment_entries(
                        comment_replies_renderer, ytcfg, video_id,
                        parent=comment.get('id'), tracker=tracker)
                    yield from itertools.islice(comment_entries_iter, min(
                        max_replies_per_thread, max(0, max_replies - tracker['total_reply_comments'])))

        # Keeps track of counts across recursive calls
        if not tracker:
            tracker = {
                'running_total': 0,
                'est_total': None,
                'current_page_thread': 0,
                'total_parent_comments': 0,
                'total_reply_comments': 0,
                'seen_comment_ids': set(),
                'pinned_comment_ids': set(),
            }

        # TODO: Deprecated
        # YouTube comments have a max depth of 2
        max_depth = int_or_none(get_single_config_arg('max_comment_depth'))
        if max_depth:
            self._downloader.deprecated_feature('[youtube] max_comment_depth extractor argument is deprecated. '
                                                'Set max replies in the max-comments extractor argument instead')
        if max_depth == 1 and parent:
            return

        max_comments, max_parents, max_replies, max_replies_per_thread, *_ = (
            int_or_none(p, default=sys.maxsize) for p in self._configuration_arg('max_comments') + [''] * 4)

        continuation = self._extract_continuation(root_continuation_data)

        response = None
        is_forced_continuation = False
        is_first_continuation = parent is None
        if is_first_continuation and not continuation:
            # Sometimes you can get comments by generating the continuation yourself,
            # even if YouTube initially reports them being disabled - e.g. stories comments.
            # Note: if the comment section is actually disabled, YouTube may return a response with
            # required check_get_keys missing. So we will disable that check initially in this case.
            continuation = self._build_api_continuation_query(self._generate_comment_continuation(video_id))
            is_forced_continuation = True

        continuation_items_path = (
            'onResponseReceivedEndpoints', ..., ('reloadContinuationItemsCommand', 'appendContinuationItemsAction'), 'continuationItems')
        for page_num in itertools.count(0):
            if not continuation:
                break
            headers = self.generate_api_headers(ytcfg=ytcfg, visitor_data=self._extract_visitor_data(response))
            comment_prog_str = f"({tracker['running_total']}/~{tracker['est_total']})"
            if page_num == 0:
                if is_first_continuation:
                    note_prefix = 'Downloading comment section API JSON'
                else:
                    note_prefix = '    Downloading comment API JSON reply thread %d %s' % (
                        tracker['current_page_thread'], comment_prog_str)
            else:
                note_prefix = '{}Downloading comment{} API JSON page {} {}'.format(
                    '       ' if parent else '', ' replies' if parent else '',
                    page_num, comment_prog_str)

            # Do a deep check for incomplete data as sometimes YouTube may return no comments for a continuation
            # Ignore check if YouTube says the comment count is 0.
            check_get_keys = None
            if not is_forced_continuation and not (tracker['est_total'] == 0 and tracker['running_total'] == 0):
                check_get_keys = [[*continuation_items_path, ..., (
                    'commentsHeaderRenderer' if is_first_continuation else ('commentThreadRenderer', 'commentViewModel', 'commentRenderer'))]]
            try:
                response = self._extract_response(
                    item_id=None, query=continuation,
                    ep='next', ytcfg=ytcfg, headers=headers, note=note_prefix,
                    check_get_keys=check_get_keys)
            except ExtractorError as e:
                # Ignore incomplete data error for replies if retries didn't work.
                # This is to allow any other parent comments and comment threads to be downloaded.
                # See: https://github.com/yt-dlp/yt-dlp/issues/4669
                if 'incomplete data' in str(e).lower() and parent:
                    if self.get_param('ignoreerrors') in (True, 'only_download'):
                        self.report_warning(
                            'Received incomplete data for a comment reply thread and retrying did not help. '
                            'Ignoring to let other comments be downloaded. Pass --no-ignore-errors to not ignore.')
                        return
                    else:
                        raise ExtractorError(
                            'Incomplete data received for comment reply thread. '
                            'Pass --ignore-errors to ignore and allow rest of comments to download.',
                            expected=True)
                raise
            is_forced_continuation = False
            continuation = None
            mutations = traverse_obj(response, ('frameworkUpdates', 'entityBatchUpdate', 'mutations', ..., {dict}))
            for continuation_items in traverse_obj(response, continuation_items_path, expected_type=list, default=[]):
                if is_first_continuation:
                    continuation = extract_header(continuation_items)
                    is_first_continuation = False
                    if continuation:
                        break
                    continue

                for entry in extract_thread(continuation_items, mutations):
                    if not entry:
                        return
                    yield entry
                continuation = self._extract_continuation({'contents': continuation_items})
                if continuation:
                    break

        message = self._get_text(root_continuation_data, ('contents', ..., 'messageRenderer', 'text'), max_runs=1)
        if message and not parent and tracker['running_total'] == 0:
            self.report_warning(f'Youtube said: {message}', video_id=video_id, only_once=True)
            raise self.CommentsDisabled

    @staticmethod
    def _generate_comment_continuation(video_id):
        """
        Generates initial comment section continuation token from given video id
        """
        token = f'\x12\r\x12\x0b{video_id}\x18\x062\'"\x11"\x0b{video_id}0\x00x\x020\x00B\x10comments-section'
        return base64.b64encode(token.encode()).decode()

    def _get_comments(self, ytcfg, video_id, contents, webpage):
        """Entry for comment extraction"""
        def _real_comment_extract(contents):
            renderer = next((
                item for item in traverse_obj(contents, (..., 'itemSectionRenderer'), default={})
                if item.get('sectionIdentifier') == 'comment-item-section'), None)
            yield from self._comment_entries(renderer, ytcfg, video_id)

        max_comments = int_or_none(self._configuration_arg('max_comments', [''])[0])
        return itertools.islice(_real_comment_extract(contents), 0, max_comments)

    @staticmethod
    def _get_checkok_params():
        return {'contentCheckOk': True, 'racyCheckOk': True}

    @classmethod
    def _generate_player_context(cls, sts=None):
        context = {
            'html5Preference': 'HTML5_PREF_WANTS',
        }
        if sts is not None:
            context['signatureTimestamp'] = sts
        return {
            'playbackContext': {
                'contentPlaybackContext': context,
            },
            **cls._get_checkok_params(),
        }

    @staticmethod
    def _is_agegated(player_response):
        if traverse_obj(player_response, ('playabilityStatus', 'desktopLegacyAgeGateReason')):
            return True

        reasons = traverse_obj(player_response, ('playabilityStatus', ('status', 'reason')))
        AGE_GATE_REASONS = (
            'confirm your age', 'age-restricted', 'inappropriate',  # reason
            'age_verification_required', 'age_check_required',  # status
        )
        return any(expected in reason for expected in AGE_GATE_REASONS for reason in reasons)

    @staticmethod
    def _is_unplayable(player_response):
        return traverse_obj(player_response, ('playabilityStatus', 'status')) == 'UNPLAYABLE'

    def _extract_player_response(self, client, video_id, master_ytcfg, player_ytcfg, player_url, initial_pr, smuggled_data):

        session_index = self._extract_session_index(player_ytcfg, master_ytcfg)
        syncid = self._extract_account_syncid(player_ytcfg, master_ytcfg, initial_pr)
        sts = self._extract_signature_timestamp(video_id, player_url, master_ytcfg, fatal=False) if player_url else None
        headers = self.generate_api_headers(
            ytcfg=player_ytcfg, account_syncid=syncid, session_index=session_index, default_client=client)

        yt_query = {
            'videoId': video_id,
        }

        default_pp = traverse_obj(
            INNERTUBE_CLIENTS, (_split_innertube_client(client)[0], 'PLAYER_PARAMS', {str}))
        if player_params := self._configuration_arg('player_params', [default_pp], casesense=True)[0]:
            yt_query['params'] = player_params

        yt_query.update(self._generate_player_context(sts))
        return self._extract_response(
            item_id=video_id, ep='player', query=yt_query,
            ytcfg=player_ytcfg, headers=headers, fatal=True,
            default_client=client,
            note='Downloading {} player API JSON'.format(client.replace('_', ' ').strip()),
        ) or None

    def _get_requested_clients(self, url, smuggled_data):
        requested_clients = []
        broken_clients = []
        default = ['ios', 'web']
        allowed_clients = sorted(
            (client for client in INNERTUBE_CLIENTS if client[:1] != '_'),
            key=lambda client: INNERTUBE_CLIENTS[client]['priority'], reverse=True)
        for client in self._configuration_arg('player_client'):
            if client == 'default':
                requested_clients.extend(default)
            elif client == 'all':
                requested_clients.extend(allowed_clients)
            elif client not in allowed_clients:
                self.report_warning(f'Skipping unsupported client {client}')
            elif client in self._BROKEN_CLIENTS.values():
                broken_clients.append(client)
            else:
                requested_clients.append(client)
        # Force deprioritization of _BROKEN_CLIENTS for format de-duplication
        requested_clients.extend(broken_clients)
        if not requested_clients:
            requested_clients = default

        if smuggled_data.get('is_music_url') or self.is_music_url(url):
            for requested_client in requested_clients:
                _, base_client, variant = _split_innertube_client(requested_client)
                music_client = f'{base_client}_music'
                if variant != 'music' and music_client in INNERTUBE_CLIENTS:
                    requested_clients.append(music_client)

        return orderedSet(requested_clients)

    def _invalid_player_response(self, pr, video_id):
        # YouTube may return a different video player response than expected.
        # See: https://github.com/TeamNewPipe/NewPipe/issues/8713
        if (pr_id := traverse_obj(pr, ('videoDetails', 'videoId'))) != video_id:
            return pr_id

    def _extract_player_responses(self, clients, video_id, webpage, master_ytcfg, smuggled_data):
        initial_pr = ignore_initial_response = None
        if webpage:
            if 'web' in clients:
                experiments = traverse_obj(master_ytcfg, (
                    'WEB_PLAYER_CONTEXT_CONFIGS', ..., 'serializedExperimentIds', {lambda x: x.split(',')}, ...))
                if all(x in experiments for x in self._POTOKEN_EXPERIMENTS):
                    self.report_warning(
                        'Webpage contains broken formats (poToken experiment detected). Ignoring initial player response')
                    ignore_initial_response = True
            initial_pr = self._search_json(
                self._YT_INITIAL_PLAYER_RESPONSE_RE, webpage, 'initial player response', video_id, fatal=False)

        prs = []
        if initial_pr and not self._invalid_player_response(initial_pr, video_id):
            # Android player_response does not have microFormats which are needed for
            # extraction of some data. So we return the initial_pr with formats
            # stripped out even if not requested by the user
            # See: https://github.com/yt-dlp/yt-dlp/issues/501
            prs.append({**initial_pr, 'streamingData': None})

        all_clients = set(clients)
        clients = clients[::-1]

        def append_client(*client_names):
            """ Append the first client name that exists but not already used """
            for client_name in client_names:
                actual_client = _split_innertube_client(client_name)[0]
                if actual_client in INNERTUBE_CLIENTS:
                    if actual_client not in all_clients:
                        clients.append(client_name)
                        all_clients.add(actual_client)
                        return

        tried_iframe_fallback = False
        player_url = None
        skipped_clients = {}
        while clients:
            client, base_client, variant = _split_innertube_client(clients.pop())
            player_ytcfg = {}
            if client == 'web':
                player_ytcfg = self._get_default_ytcfg() if ignore_initial_response else master_ytcfg
            elif 'configs' not in self._configuration_arg('player_skip'):
                player_ytcfg = self._download_ytcfg(client, video_id) or player_ytcfg

            player_url = player_url or self._extract_player_url(master_ytcfg, player_ytcfg, webpage=webpage)
            require_js_player = self._get_default_ytcfg(client).get('REQUIRE_JS_PLAYER')
            if 'js' in self._configuration_arg('player_skip'):
                require_js_player = False
                player_url = None

            if not player_url and not tried_iframe_fallback and require_js_player:
                player_url = self._download_player_url(video_id)
                tried_iframe_fallback = True

            pr = initial_pr if client == 'web' and not ignore_initial_response else None
            for retry in self.RetryManager(fatal=False):
                try:
                    pr = pr or self._extract_player_response(
                        client, video_id, player_ytcfg or master_ytcfg, player_ytcfg,
                        player_url if require_js_player else None, initial_pr, smuggled_data)
                except ExtractorError as e:
                    self.report_warning(e)
                    break
                experiments = traverse_obj(pr, (
                    'responseContext', 'serviceTrackingParams', lambda _, v: v['service'] == 'GFEEDBACK',
                    'params', lambda _, v: v['key'] == 'e', 'value', {lambda x: x.split(',')}, ...))
                if all(x in experiments for x in self._POTOKEN_EXPERIMENTS):
                    pr = None
                    retry.error = ExtractorError('API returned broken formats (poToken experiment detected)', expected=True)
            if not pr:
                continue

            if pr_id := self._invalid_player_response(pr, video_id):
                skipped_clients[client] = pr_id
            elif pr:
                # Save client name for introspection later
                name = short_client_name(client)
                sd = traverse_obj(pr, ('streamingData', {dict})) or {}
                sd[STREAMING_DATA_CLIENT_NAME] = name
                for f in traverse_obj(sd, (('formats', 'adaptiveFormats'), ..., {dict})):
                    f[STREAMING_DATA_CLIENT_NAME] = name
                prs.append(pr)

            # creator clients can bypass AGE_VERIFICATION_REQUIRED if logged in
            if variant == 'tv_embedded' and self._is_unplayable(pr) and self.is_authenticated:
                append_client(f'{base_client}_creator')
            elif variant != 'tv_embedded' and self._is_agegated(pr):
                if self.is_authenticated:
                    append_client(f'{base_client}_creator')
                append_client(f'tv_embedded.{base_client}')

        if skipped_clients:
            self.report_warning(
                f'Skipping player responses from {"/".join(skipped_clients)} clients '
                f'(got player responses for video "{"/".join(set(skipped_clients.values()))}" instead of "{video_id}")')
            if not prs:
                raise ExtractorError(
                    'All player responses are invalid. Your IP is likely being blocked by Youtube', expected=True)
        elif not prs:
            raise ExtractorError('Failed to extract any player response')
        return prs, player_url

    def _needs_live_processing(self, live_status, duration):
        if (live_status == 'is_live' and self.get_param('live_from_start')
                or live_status == 'post_live' and (duration or 0) > 2 * 3600):
            return live_status

    def _extract_formats_and_subtitles(self, streaming_data, video_id, player_url, live_status, duration):
        CHUNK_SIZE = 10 << 20
        PREFERRED_LANG_VALUE = 10
        original_language = None
        itags, stream_ids = collections.defaultdict(set), []
        itag_qualities, res_qualities = {}, {0: None}
        q = qualities([
            # Normally tiny is the smallest video-only formats. But
            # audio-only formats with unknown quality may get tagged as tiny
            'tiny',
            'audio_quality_ultralow', 'audio_quality_low', 'audio_quality_medium', 'audio_quality_high',  # Audio only formats
            'small', 'medium', 'large', 'hd720', 'hd1080', 'hd1440', 'hd2160', 'hd2880', 'highres',
        ])
        streaming_formats = traverse_obj(streaming_data, (..., ('formats', 'adaptiveFormats'), ...))
        format_types = self._configuration_arg('formats')
        all_formats = 'duplicate' in format_types
        if self._configuration_arg('include_duplicate_formats'):
            all_formats = True
            self._downloader.deprecated_feature('[youtube] include_duplicate_formats extractor argument is deprecated. '
                                                'Use formats=duplicate extractor argument instead')

        def build_fragments(f):
            return LazyList({
                'url': update_url_query(f['url'], {
                    'range': f'{range_start}-{min(range_start + CHUNK_SIZE - 1, f["filesize"])}',
                }),
            } for range_start in range(0, f['filesize'], CHUNK_SIZE))

        for fmt in streaming_formats:
            if fmt.get('targetDurationSec'):
                continue

            itag = str_or_none(fmt.get('itag'))
            audio_track = fmt.get('audioTrack') or {}
            stream_id = (itag, audio_track.get('id'), fmt.get('isDrc'))
            if not all_formats:
                if stream_id in stream_ids:
                    continue

            quality = fmt.get('quality')
            height = int_or_none(fmt.get('height'))
            if quality == 'tiny' or not quality:
                quality = fmt.get('audioQuality', '').lower() or quality
            # The 3gp format (17) in android client has a quality of "small",
            # but is actually worse than other formats
            if itag == '17':
                quality = 'tiny'
            if quality:
                if itag:
                    itag_qualities[itag] = quality
                if height:
                    res_qualities[height] = quality

            is_default = audio_track.get('audioIsDefault')
            is_descriptive = 'descriptive' in (audio_track.get('displayName') or '').lower()
            language_code = audio_track.get('id', '').split('.')[0]
            if language_code and is_default:
                original_language = language_code

            # FORMAT_STREAM_TYPE_OTF(otf=1) requires downloading the init fragment
            # (adding `&sq=0` to the URL) and parsing emsg box to determine the
            # number of fragment that would subsequently requested with (`&sq=N`)
            if fmt.get('type') == 'FORMAT_STREAM_TYPE_OTF':
                continue

            fmt_url = fmt.get('url')
            if not fmt_url:
                sc = urllib.parse.parse_qs(fmt.get('signatureCipher'))
                fmt_url = url_or_none(try_get(sc, lambda x: x['url'][0]))
                encrypted_sig = try_get(sc, lambda x: x['s'][0])
                if not all((sc, fmt_url, player_url, encrypted_sig)):
                    continue
                try:
                    fmt_url += '&{}={}'.format(
                        traverse_obj(sc, ('sp', -1)) or 'signature',
                        self._decrypt_signature(encrypted_sig, video_id, player_url),
                    )
                except ExtractorError as e:
                    self.report_warning('Signature extraction failed: Some formats may be missing',
                                        video_id=video_id, only_once=True)
                    self.write_debug(e, only_once=True)
                    continue

            query = parse_qs(fmt_url)
            if query.get('n'):
                try:
                    decrypt_nsig = self._cached(self._decrypt_nsig, 'nsig', query['n'][0])
                    fmt_url = update_url_query(fmt_url, {
                        'n': decrypt_nsig(query['n'][0], video_id, player_url),
                    })
                except ExtractorError as e:
                    phantomjs_hint = ''
                    if isinstance(e, JSInterpreter.Exception):
                        phantomjs_hint = (f'         Install {self._downloader._format_err("PhantomJS", self._downloader.Styles.EMPHASIS)} '
                                          f'to workaround the issue. {PhantomJSwrapper.INSTALL_HINT}\n')
                    if player_url:
                        self.report_warning(
                            f'nsig extraction failed: Some formats may be missing\n{phantomjs_hint}'
                            f'         n = {query["n"][0]} ; player = {player_url}', video_id=video_id, only_once=True)
                        self.write_debug(e, only_once=True)
                    else:
                        self.report_warning(
                            'Cannot decrypt nsig without player_url: Some formats may be missing',
                            video_id=video_id, only_once=True)
                    continue

            tbr = float_or_none(fmt.get('averageBitrate') or fmt.get('bitrate'), 1000)
            format_duration = traverse_obj(fmt, ('approxDurationMs', {lambda x: float_or_none(x, 1000)}))
            # Some formats may have much smaller duration than others (possibly damaged during encoding)
            # E.g. 2-nOtRESiUc Ref: https://github.com/yt-dlp/yt-dlp/issues/2823
            # Make sure to avoid false positives with small duration differences.
            # E.g. __2ABJjxzNo, ySuUZEjARPY
            is_damaged = try_call(lambda: format_duration < duration // 2)
            if is_damaged:
                self.report_warning(
                    f'{video_id}: Some formats are possibly damaged. They will be deprioritized', only_once=True)

            client_name = fmt.get(STREAMING_DATA_CLIENT_NAME)
            # _BROKEN_CLIENTS return videoplayback URLs that expire after 30 seconds
            # Ref: https://github.com/yt-dlp/yt-dlp/issues/9554
            is_broken = client_name in self._BROKEN_CLIENTS
            if is_broken:
                self.report_warning(
                    f'{video_id}: {self._BROKEN_CLIENTS[client_name]} client formats are broken '
                    'and may yield HTTP Error 403. They will be deprioritized', only_once=True)

            name = fmt.get('qualityLabel') or quality.replace('audio_quality_', '') or ''
            fps = int_or_none(fmt.get('fps')) or 0
            dct = {
                'asr': int_or_none(fmt.get('audioSampleRate')),
                'filesize': int_or_none(fmt.get('contentLength')),
                'format_id': f'{itag}{"-drc" if fmt.get("isDrc") else ""}',
                'format_note': join_nonempty(
                    join_nonempty(audio_track.get('displayName'), is_default and ' (default)', delim=''),
                    name, fmt.get('isDrc') and 'DRC',
                    try_get(fmt, lambda x: x['projectionType'].replace('RECTANGULAR', '').lower()),
                    try_get(fmt, lambda x: x['spatialAudioType'].replace('SPATIAL_AUDIO_TYPE_', '').lower()),
                    is_damaged and 'DAMAGED', is_broken and 'BROKEN',
                    (self.get_param('verbose') or all_formats) and client_name,
                    delim=', '),
                # Format 22 is likely to be damaged. See https://github.com/yt-dlp/yt-dlp/issues/3372
                'source_preference': (-5 if itag == '22' else -1) + (100 if 'Premium' in name else 0),
                'fps': fps if fps > 1 else None,  # For some formats, fps is wrongly returned as 1
                'audio_channels': fmt.get('audioChannels'),
                'height': height,
                'quality': q(quality) - bool(fmt.get('isDrc')) / 2,
                'has_drm': bool(fmt.get('drmFamilies')),
                'tbr': tbr,
                'filesize_approx': filesize_from_tbr(tbr, format_duration),
                'url': fmt_url,
                'width': int_or_none(fmt.get('width')),
                'language': join_nonempty(language_code, 'desc' if is_descriptive else '') or None,
                'language_preference': PREFERRED_LANG_VALUE if is_default else -10 if is_descriptive else -1,
                # Strictly de-prioritize broken, damaged and 3gp formats
                'preference': -20 if is_broken else -10 if is_damaged else -2 if itag == '17' else None,
            }
            mime_mobj = re.match(
                r'((?:[^/]+)/(?:[^;]+))(?:;\s*codecs="([^"]+)")?', fmt.get('mimeType') or '')
            if mime_mobj:
                dct['ext'] = mimetype2ext(mime_mobj.group(1))
                dct.update(parse_codecs(mime_mobj.group(2)))
            if itag:
                itags[itag].add(('https', dct.get('language')))
                stream_ids.append(stream_id)
            single_stream = 'none' in (dct.get('acodec'), dct.get('vcodec'))
            if single_stream and dct.get('ext'):
                dct['container'] = dct['ext'] + '_dash'

            if (all_formats or 'dashy' in format_types) and dct['filesize']:
                yield {
                    **dct,
                    'format_id': f'{dct["format_id"]}-dashy' if all_formats else dct['format_id'],
                    'protocol': 'http_dash_segments',
                    'fragments': build_fragments(dct),
                }
            if all_formats or 'dashy' not in format_types:
                dct['downloader_options'] = {'http_chunk_size': CHUNK_SIZE}
                yield dct

        needs_live_processing = self._needs_live_processing(live_status, duration)
        skip_bad_formats = 'incomplete' not in format_types
        if self._configuration_arg('include_incomplete_formats'):
            skip_bad_formats = False
            self._downloader.deprecated_feature('[youtube] include_incomplete_formats extractor argument is deprecated. '
                                                'Use formats=incomplete extractor argument instead')

        skip_manifests = set(self._configuration_arg('skip'))
        if (not self.get_param('youtube_include_hls_manifest', True)
                or needs_live_processing == 'is_live'  # These will be filtered out by YoutubeDL anyway
                or needs_live_processing and skip_bad_formats):
            skip_manifests.add('hls')

        if not self.get_param('youtube_include_dash_manifest', True):
            skip_manifests.add('dash')
        if self._configuration_arg('include_live_dash'):
            self._downloader.deprecated_feature('[youtube] include_live_dash extractor argument is deprecated. '
                                                'Use formats=incomplete extractor argument instead')
        elif skip_bad_formats and live_status == 'is_live' and needs_live_processing != 'is_live':
            skip_manifests.add('dash')

        def process_manifest_format(f, proto, client_name, itag):
            key = (proto, f.get('language'))
            if not all_formats and key in itags[itag]:
                return False
            itags[itag].add(key)

            if itag and all_formats:
                f['format_id'] = f'{itag}-{proto}'
            elif any(p != proto for p, _ in itags[itag]):
                f['format_id'] = f'{itag}-{proto}'
            elif itag:
                f['format_id'] = itag

            if original_language and f.get('language') == original_language:
                f['format_note'] = join_nonempty(f.get('format_note'), '(default)', delim=' ')
                f['language_preference'] = PREFERRED_LANG_VALUE

            if f.get('source_preference') is None:
                f['source_preference'] = -1

            if itag in ('616', '235'):
                f['format_note'] = join_nonempty(f.get('format_note'), 'Premium', delim=' ')
                f['source_preference'] += 100

            f['quality'] = q(itag_qualities.get(try_get(f, lambda f: f['format_id'].split('-')[0]), -1))
            if f['quality'] == -1 and f.get('height'):
                f['quality'] = q(res_qualities[min(res_qualities, key=lambda x: abs(x - f['height']))])
            if self.get_param('verbose') or all_formats:
                f['format_note'] = join_nonempty(f.get('format_note'), client_name, delim=', ')
            if f.get('fps') and f['fps'] <= 1:
                del f['fps']

            if proto == 'hls' and f.get('has_drm'):
                f['has_drm'] = 'maybe'
                f['source_preference'] -= 5
            return True

        subtitles = {}
        for sd in streaming_data:
            client_name = sd.get(STREAMING_DATA_CLIENT_NAME)

            hls_manifest_url = 'hls' not in skip_manifests and sd.get('hlsManifestUrl')
            if hls_manifest_url:
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    hls_manifest_url, video_id, 'mp4', fatal=False, live=live_status == 'is_live')
                subtitles = self._merge_subtitles(subs, subtitles)
                for f in fmts:
                    if process_manifest_format(f, 'hls', client_name, self._search_regex(
                            r'/itag/(\d+)', f['url'], 'itag', default=None)):
                        yield f

            dash_manifest_url = 'dash' not in skip_manifests and sd.get('dashManifestUrl')
            if dash_manifest_url:
                formats, subs = self._extract_mpd_formats_and_subtitles(dash_manifest_url, video_id, fatal=False)
                subtitles = self._merge_subtitles(subs, subtitles)  # Prioritize HLS subs over DASH
                for f in formats:
                    if process_manifest_format(f, 'dash', client_name, f['format_id']):
                        f['filesize'] = int_or_none(self._search_regex(
                            r'/clen/(\d+)', f.get('fragment_base_url') or f['url'], 'file size', default=None))
                        if needs_live_processing:
                            f['is_from_start'] = True

                        yield f
        yield subtitles

    def _extract_storyboard(self, player_responses, duration):
        spec = get_first(
            player_responses, ('storyboards', 'playerStoryboardSpecRenderer', 'spec'), default='').split('|')[::-1]
        base_url = url_or_none(urljoin('https://i.ytimg.com/', spec.pop() or None))
        if not base_url:
            return
        L = len(spec) - 1
        for i, args in enumerate(spec):
            args = args.split('#')
            counts = list(map(int_or_none, args[:5]))
            if len(args) != 8 or not all(counts):
                self.report_warning(f'Malformed storyboard {i}: {"#".join(args)}{bug_reports_message()}')
                continue
            width, height, frame_count, cols, rows = counts
            N, sigh = args[6:]

            url = base_url.replace('$L', str(L - i)).replace('$N', N) + f'&sigh={sigh}'
            fragment_count = frame_count / (cols * rows)
            fragment_duration = duration / fragment_count
            yield {
                'format_id': f'sb{i}',
                'format_note': 'storyboard',
                'ext': 'mhtml',
                'protocol': 'mhtml',
                'acodec': 'none',
                'vcodec': 'none',
                'url': url,
                'width': width,
                'height': height,
                'fps': frame_count / duration,
                'rows': rows,
                'columns': cols,
                'fragments': [{
                    'url': url.replace('$M', str(j)),
                    'duration': min(fragment_duration, duration - (j * fragment_duration)),
                } for j in range(math.ceil(fragment_count))],
            }

    def _download_player_responses(self, url, smuggled_data, video_id, webpage_url):
        webpage = None
        if 'webpage' not in self._configuration_arg('player_skip'):
            query = {'bpctr': '9999999999', 'has_verified': '1'}
            pp = self._configuration_arg('player_params', [None], casesense=True)[0]
            if pp:
                query['pp'] = pp
            webpage = self._download_webpage(
                webpage_url, video_id, fatal=False, query=query)

        master_ytcfg = self.extract_ytcfg(video_id, webpage) or self._get_default_ytcfg()

        player_responses, player_url = self._extract_player_responses(
            self._get_requested_clients(url, smuggled_data),
            video_id, webpage, master_ytcfg, smuggled_data)

        return webpage, master_ytcfg, player_responses, player_url

    def _list_formats(self, video_id, microformats, video_details, player_responses, player_url, duration=None):
        live_broadcast_details = traverse_obj(microformats, (..., 'liveBroadcastDetails'))
        is_live = get_first(video_details, 'isLive')
        if is_live is None:
            is_live = get_first(live_broadcast_details, 'isLiveNow')
        live_content = get_first(video_details, 'isLiveContent')
        is_upcoming = get_first(video_details, 'isUpcoming')
        post_live = get_first(video_details, 'isPostLiveDvr')
        live_status = ('post_live' if post_live
                       else 'is_live' if is_live
                       else 'is_upcoming' if is_upcoming
                       else 'was_live' if live_content
                       else 'not_live' if False in (is_live, live_content)
                       else None)
        streaming_data = traverse_obj(player_responses, (..., 'streamingData'))
        *formats, subtitles = self._extract_formats_and_subtitles(streaming_data, video_id, player_url, live_status, duration)
        if all(f.get('has_drm') for f in formats):
            # If there are no formats that definitely don't have DRM, all have DRM
            for f in formats:
                f['has_drm'] = True

        return live_broadcast_details, live_status, streaming_data, formats, subtitles

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)

        base_url = self.http_scheme() + '//www.youtube.com/'
        webpage_url = base_url + 'watch?v=' + video_id

        webpage, master_ytcfg, player_responses, player_url = self._download_player_responses(url, smuggled_data, video_id, webpage_url)

        playability_statuses = traverse_obj(
            player_responses, (..., 'playabilityStatus'), expected_type=dict)

        trailer_video_id = get_first(
            playability_statuses,
            ('errorScreen', 'playerLegacyDesktopYpcTrailerRenderer', 'trailerVideoId'),
            expected_type=str)
        if trailer_video_id:
            return self.url_result(
                trailer_video_id, self.ie_key(), trailer_video_id)

        search_meta = ((lambda x: self._html_search_meta(x, webpage, default=None))
                       if webpage else (lambda x: None))

        video_details = traverse_obj(player_responses, (..., 'videoDetails'), expected_type=dict)
        microformats = traverse_obj(
            player_responses, (..., 'microformat', 'playerMicroformatRenderer'),
            expected_type=dict)

        translated_title = self._get_text(microformats, (..., 'title'))
        video_title = (self._preferred_lang and translated_title
                       or get_first(video_details, 'title')  # primary
                       or translated_title
                       or search_meta(['og:title', 'twitter:title', 'title']))
        translated_description = self._get_text(microformats, (..., 'description'))
        original_description = get_first(video_details, 'shortDescription')
        video_description = (
            self._preferred_lang and translated_description
            # If original description is blank, it will be an empty string.
            # Do not prefer translated description in this case.
            or original_description if original_description is not None else translated_description)

        multifeed_metadata_list = get_first(
            player_responses,
            ('multicamera', 'playerLegacyMulticameraRenderer', 'metadataList'),
            expected_type=str)
        if multifeed_metadata_list and not smuggled_data.get('force_singlefeed'):
            if self.get_param('noplaylist'):
                self.to_screen(f'Downloading just video {video_id} because of --no-playlist')
            else:
                entries = []
                feed_ids = []
                for feed in multifeed_metadata_list.split(','):
                    # Unquote should take place before split on comma (,) since textual
                    # fields may contain comma as well (see
                    # https://github.com/ytdl-org/youtube-dl/issues/8536)
                    feed_data = urllib.parse.parse_qs(
                        urllib.parse.unquote_plus(feed))

                    def feed_entry(name):
                        return try_get(
                            feed_data, lambda x: x[name][0], str)

                    feed_id = feed_entry('id')
                    if not feed_id:
                        continue
                    feed_title = feed_entry('title')
                    title = video_title
                    if feed_title:
                        title += f' ({feed_title})'
                    entries.append({
                        '_type': 'url_transparent',
                        'ie_key': 'Youtube',
                        'url': smuggle_url(
                            '{}watch?v={}'.format(base_url, feed_data['id'][0]),
                            {'force_singlefeed': True}),
                        'title': title,
                    })
                    feed_ids.append(feed_id)
                self.to_screen(
                    'Downloading multifeed video ({}) - add --no-playlist to just download video {}'.format(
                        ', '.join(feed_ids), video_id))
                return self.playlist_result(
                    entries, video_id, video_title, video_description)

        duration = (int_or_none(get_first(video_details, 'lengthSeconds'))
                    or int_or_none(get_first(microformats, 'lengthSeconds'))
                    or parse_duration(search_meta('duration')) or None)

        live_broadcast_details, live_status, streaming_data, formats, automatic_captions = \
            self._list_formats(video_id, microformats, video_details, player_responses, player_url, duration)
        if live_status == 'post_live':
            self.write_debug(f'{video_id}: Video is in Post-Live Manifestless mode')

        if not formats:
            if not self.get_param('allow_unplayable_formats') and traverse_obj(streaming_data, (..., 'licenseInfos')):
                self.report_drm(video_id)
            pemr = get_first(
                playability_statuses,
                ('errorScreen', 'playerErrorMessageRenderer'), expected_type=dict) or {}
            reason = self._get_text(pemr, 'reason') or get_first(playability_statuses, 'reason')
            subreason = clean_html(self._get_text(pemr, 'subreason') or '')
            if subreason:
                if subreason == 'The uploader has not made this video available in your country.':
                    countries = get_first(microformats, 'availableCountries')
                    if not countries:
                        regions_allowed = search_meta('regionsAllowed')
                        countries = regions_allowed.split(',') if regions_allowed else None
                    self.raise_geo_restricted(subreason, countries, metadata_available=True)
                reason += f'. {subreason}'
            if reason:
                self.raise_no_formats(reason, expected=True)

        keywords = get_first(video_details, 'keywords', expected_type=list) or []
        if not keywords and webpage:
            keywords = [
                unescapeHTML(m.group('content'))
                for m in re.finditer(self._meta_regex('og:video:tag'), webpage)]
        for keyword in keywords:
            if keyword.startswith('yt:stretch='):
                mobj = re.search(r'(\d+)\s*:\s*(\d+)', keyword)
                if mobj:
                    # NB: float is intentional for forcing float division
                    w, h = (float(v) for v in mobj.groups())
                    if w > 0 and h > 0:
                        ratio = w / h
                        for f in formats:
                            if f.get('vcodec') != 'none':
                                f['stretched_ratio'] = ratio
                        break
        thumbnails = self._extract_thumbnails((video_details, microformats), (..., ..., 'thumbnail'))
        thumbnail_url = search_meta(['og:image', 'twitter:image'])
        if thumbnail_url:
            thumbnails.append({
                'url': thumbnail_url,
            })
        original_thumbnails = thumbnails.copy()

        # The best resolution thumbnails sometimes does not appear in the webpage
        # See: https://github.com/yt-dlp/yt-dlp/issues/340
        # List of possible thumbnails - Ref: <https://stackoverflow.com/a/20542029>
        thumbnail_names = [
            # While the *1,*2,*3 thumbnails are just below their corresponding "*default" variants
            # in resolution, these are not the custom thumbnail. So de-prioritize them
            'maxresdefault', 'hq720', 'sddefault', 'hqdefault', '0', 'mqdefault', 'default',
            'sd1', 'sd2', 'sd3', 'hq1', 'hq2', 'hq3', 'mq1', 'mq2', 'mq3', '1', '2', '3',
        ]
        n_thumbnail_names = len(thumbnail_names)
        thumbnails.extend({
            'url': 'https://i.ytimg.com/vi{webp}/{video_id}/{name}{live}.{ext}'.format(
                video_id=video_id, name=name, ext=ext,
                webp='_webp' if ext == 'webp' else '', live='_live' if live_status == 'is_live' else ''),
        } for name in thumbnail_names for ext in ('webp', 'jpg'))
        for thumb in thumbnails:
            i = next((i for i, t in enumerate(thumbnail_names) if f'/{video_id}/{t}' in thumb['url']), n_thumbnail_names)
            thumb['preference'] = (0 if '.webp' in thumb['url'] else -1) - (2 * i)
        self._remove_duplicate_formats(thumbnails)
        self._downloader._sort_thumbnails(original_thumbnails)

        category = get_first(microformats, 'category') or search_meta('genre')
        channel_id = self.ucid_or_none(str_or_none(
            get_first(video_details, 'channelId')
            or get_first(microformats, 'externalChannelId')
            or search_meta('channelId')))
        owner_profile_url = get_first(microformats, 'ownerProfileUrl')

        live_start_time = parse_iso8601(get_first(live_broadcast_details, 'startTimestamp'))
        live_end_time = parse_iso8601(get_first(live_broadcast_details, 'endTimestamp'))
        if not duration and live_end_time and live_start_time:
            duration = live_end_time - live_start_time

        needs_live_processing = self._needs_live_processing(live_status, duration)

        def is_bad_format(fmt):
            if needs_live_processing and not fmt.get('is_from_start'):
                return True
            elif (live_status == 'is_live' and needs_live_processing != 'is_live'
                    and fmt.get('protocol') == 'http_dash_segments'):
                return True

        for fmt in filter(is_bad_format, formats):
            fmt['preference'] = (fmt.get('preference') or -1) - 10
            fmt['format_note'] = join_nonempty(fmt.get('format_note'), '(Last 2 hours)', delim=' ')

        if needs_live_processing:
            self._prepare_live_from_start_formats(
                formats, video_id, live_start_time, url, webpage_url, smuggled_data, live_status == 'is_live')

        formats.extend(self._extract_storyboard(player_responses, duration))

        channel_handle = self.handle_from_url(owner_profile_url)

        info = {
            'id': video_id,
            'title': video_title,
            'formats': formats,
            'thumbnails': thumbnails,
            # The best thumbnail that we are sure exists. Prevents unnecessary
            # URL checking if user don't care about getting the best possible thumbnail
            'thumbnail': traverse_obj(original_thumbnails, (-1, 'url')),
            'description': video_description,
            'channel_id': channel_id,
            'channel_url': format_field(channel_id, None, 'https://www.youtube.com/channel/%s', default=None),
            'duration': duration,
            'view_count': int_or_none(
                get_first((video_details, microformats), (..., 'viewCount'))
                or search_meta('interactionCount')),
            'average_rating': float_or_none(get_first(video_details, 'averageRating')),
            'age_limit': 18 if (
                get_first(microformats, 'isFamilySafe') is False
                or search_meta('isFamilyFriendly') == 'false'
                or search_meta('og:restrictions:age') == '18+') else 0,
            'webpage_url': webpage_url,
            'categories': [category] if category else None,
            'tags': keywords,
            'playable_in_embed': get_first(playability_statuses, 'playableInEmbed'),
            'live_status': live_status,
            'release_timestamp': live_start_time,
            '_format_sort_fields': (  # source_preference is lower for potentially damaged formats
                'quality', 'res', 'fps', 'hdr:12', 'source', 'vcodec:vp9.2', 'channels', 'acodec', 'lang', 'proto'),
        }

        subtitles = {}
        pctr = traverse_obj(player_responses, (..., 'captions', 'playerCaptionsTracklistRenderer'), expected_type=dict)
        if pctr:
            def get_lang_code(track):
                return (remove_start(track.get('vssId') or '', '.').replace('.', '-')
                        or track.get('languageCode'))

            # Converted into dicts to remove duplicates
            captions = {
                get_lang_code(sub): sub
                for sub in traverse_obj(pctr, (..., 'captionTracks', ...))}
            translation_languages = {
                lang.get('languageCode'): self._get_text(lang.get('languageName'), max_runs=1)
                for lang in traverse_obj(pctr, (..., 'translationLanguages', ...))}

            def process_language(container, base_url, lang_code, sub_name, query):
                lang_subs = container.setdefault(lang_code, [])
                for fmt in self._SUBTITLE_FORMATS:
                    query.update({
                        'fmt': fmt,
                    })
                    lang_subs.append({
                        'ext': fmt,
                        'url': urljoin('https://www.youtube.com', update_url_query(base_url, query)),
                        'name': sub_name,
                    })

            # NB: Constructing the full subtitle dictionary is slow
            get_translated_subs = 'translated_subs' not in self._configuration_arg('skip') and (
                self.get_param('writeautomaticsub', False) or self.get_param('listsubtitles'))
            for lang_code, caption_track in captions.items():
                base_url = caption_track.get('baseUrl')
                orig_lang = parse_qs(base_url).get('lang', [None])[-1]
                if not base_url:
                    continue
                lang_name = self._get_text(caption_track, 'name', max_runs=1)
                if caption_track.get('kind') != 'asr':
                    if not lang_code:
                        continue
                    process_language(
                        subtitles, base_url, lang_code, lang_name, {})
                    if not caption_track.get('isTranslatable'):
                        continue
                for trans_code, trans_name in translation_languages.items():
                    if not trans_code:
                        continue
                    orig_trans_code = trans_code
                    if caption_track.get('kind') != 'asr' and trans_code != 'und':
                        if not get_translated_subs:
                            continue
                        trans_code += f'-{lang_code}'
                        trans_name += format_field(lang_name, None, ' from %s')
                    if lang_code == f'a-{orig_trans_code}':
                        # Set audio language based on original subtitles
                        for f in formats:
                            if f.get('acodec') != 'none' and not f.get('language'):
                                f['language'] = orig_trans_code
                        # Add an "-orig" label to the original language so that it can be distinguished.
                        # The subs are returned without "-orig" as well for compatibility
                        process_language(
                            automatic_captions, base_url, f'{trans_code}-orig', f'{trans_name} (Original)', {})
                    # Setting tlang=lang returns damaged subtitles.
                    process_language(automatic_captions, base_url, trans_code, trans_name,
                                     {} if orig_lang == orig_trans_code else {'tlang': trans_code})

        info['automatic_captions'] = automatic_captions
        info['subtitles'] = subtitles

        parsed_url = urllib.parse.urlparse(url)
        for component in [parsed_url.fragment, parsed_url.query]:
            query = urllib.parse.parse_qs(component)
            for k, v in query.items():
                for d_k, s_ks in [('start', ('start', 't')), ('end', ('end',))]:
                    d_k += '_time'
                    if d_k not in info and k in s_ks:
                        info[d_k] = parse_duration(v[0])

        # Youtube Music Auto-generated description
        if (video_description or '').strip().endswith('\nAuto-generated by YouTube.'):
            # XXX: Causes catastrophic backtracking if description has "·"
            # E.g. https://www.youtube.com/watch?v=DoPaAxMQoiI
            # Simulating atomic groups:  (?P<a>[^xy]+)x  =>  (?=(?P<a>[^xy]+))(?P=a)x
            # reduces it, but does not fully fix it. https://regex101.com/r/8Ssf2h/2
            mobj = re.search(
                r'''(?xs)
                    (?=(?P<track>[^\n·]+))(?P=track)·
                    (?=(?P<artist>[^\n]+))(?P=artist)\n+
                    (?=(?P<album>[^\n]+))(?P=album)\n
                    (?:.+?℗\s*(?P<release_year>\d{4})(?!\d))?
                    (?:.+?Released on\s*:\s*(?P<release_date>\d{4}-\d{2}-\d{2}))?
                    (.+?\nArtist\s*:\s*
                        (?=(?P<clean_artist>[^\n]+))(?P=clean_artist)\n
                    )?.+\nAuto-generated\ by\ YouTube\.\s*$
                ''', video_description)
            if mobj:
                release_year = mobj.group('release_year')
                release_date = mobj.group('release_date')
                if release_date:
                    release_date = release_date.replace('-', '')
                    if not release_year:
                        release_year = release_date[:4]
                info.update({
                    'album': mobj.group('album'.strip()),
                    'artists': ([a] if (a := mobj.group('clean_artist'))
                                else [a.strip() for a in mobj.group('artist').split('·')]),
                    'track': mobj.group('track').strip(),
                    'release_date': release_date,
                    'release_year': int_or_none(release_year),
                })

        initial_data = None
        if webpage:
            initial_data = self.extract_yt_initial_data(video_id, webpage, fatal=False)
            if not traverse_obj(initial_data, 'contents'):
                self.report_warning('Incomplete data received in embedded initial data; re-fetching using API.')
                initial_data = None
        if not initial_data:
            query = {'videoId': video_id}
            query.update(self._get_checkok_params())
            initial_data = self._extract_response(
                item_id=video_id, ep='next', fatal=False,
                ytcfg=master_ytcfg, query=query, check_get_keys='contents',
                headers=self.generate_api_headers(ytcfg=master_ytcfg),
                note='Downloading initial data API JSON')

        info['comment_count'] = traverse_obj(initial_data, (
            'contents', 'twoColumnWatchNextResults', 'results', 'results', 'contents', ..., 'itemSectionRenderer',
            'contents', ..., 'commentsEntryPointHeaderRenderer', 'commentCount',
        ), (
            'engagementPanels', lambda _, v: v['engagementPanelSectionListRenderer']['panelIdentifier'] == 'comment-item-section',
            'engagementPanelSectionListRenderer', 'header', 'engagementPanelTitleHeaderRenderer', 'contextualInfo',
        ), expected_type=self._get_count, get_all=False)

        try:  # This will error if there is no livechat
            initial_data['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['continuations'][0]['reloadContinuationData']['continuation']
        except (KeyError, IndexError, TypeError):
            pass
        else:
            info.setdefault('subtitles', {})['live_chat'] = [{
                # url is needed to set cookies
                'url': f'https://www.youtube.com/watch?v={video_id}&bpctr=9999999999&has_verified=1',
                'video_id': video_id,
                'ext': 'json',
                'protocol': ('youtube_live_chat' if live_status in ('is_live', 'is_upcoming')
                             else 'youtube_live_chat_replay'),
            }]

        if initial_data:
            info['chapters'] = (
                self._extract_chapters_from_json(initial_data, duration)
                or self._extract_chapters_from_engagement_panel(initial_data, duration)
                or self._extract_chapters_from_description(video_description, duration)
                or None)

            info['heatmap'] = self._extract_heatmap(initial_data)

        contents = traverse_obj(
            initial_data, ('contents', 'twoColumnWatchNextResults', 'results', 'results', 'contents'),
            expected_type=list, default=[])

        vpir = get_first(contents, 'videoPrimaryInfoRenderer')
        if vpir:
            stl = vpir.get('superTitleLink')
            if stl:
                stl = self._get_text(stl)
                if try_get(
                        vpir,
                        lambda x: x['superTitleIcon']['iconType']) == 'LOCATION_PIN':
                    info['location'] = stl
                else:
                    mobj = re.search(r'(.+?)\s*S(\d+)\s*•?\s*E(\d+)', stl)
                    if mobj:
                        info.update({
                            'series': mobj.group(1),
                            'season_number': int(mobj.group(2)),
                            'episode_number': int(mobj.group(3)),
                        })
            for tlb in (try_get(
                    vpir,
                    lambda x: x['videoActions']['menuRenderer']['topLevelButtons'],
                    list) or []):
                tbrs = variadic(
                    traverse_obj(
                        tlb, ('toggleButtonRenderer', ...),
                        ('segmentedLikeDislikeButtonRenderer', ..., 'toggleButtonRenderer')))
                for tbr in tbrs:
                    for getter, regex in [(
                            lambda x: x['defaultText']['accessibility']['accessibilityData'],
                            r'(?P<count>[\d,]+)\s*(?P<type>(?:dis)?like)'), ([
                                lambda x: x['accessibility'],
                                lambda x: x['accessibilityData']['accessibilityData'],
                            ], r'(?P<type>(?:dis)?like) this video along with (?P<count>[\d,]+) other people')]:
                        label = (try_get(tbr, getter, dict) or {}).get('label')
                        if label:
                            mobj = re.match(regex, label)
                            if mobj:
                                info[mobj.group('type') + '_count'] = str_to_int(mobj.group('count'))
                                break

            info['like_count'] = traverse_obj(vpir, (
                'videoActions', 'menuRenderer', 'topLevelButtons', ...,
                'segmentedLikeDislikeButtonViewModel', 'likeButtonViewModel', 'likeButtonViewModel',
                'toggleButtonViewModel', 'toggleButtonViewModel', 'defaultButtonViewModel',
                'buttonViewModel', 'accessibilityText', {parse_count}), get_all=False)

            vcr = traverse_obj(vpir, ('viewCount', 'videoViewCountRenderer'))
            if vcr:
                vc = self._get_count(vcr, 'viewCount')
                # Upcoming premieres with waiting count are treated as live here
                if vcr.get('isLive'):
                    info['concurrent_view_count'] = vc
                elif info.get('view_count') is None:
                    info['view_count'] = vc

        vsir = get_first(contents, 'videoSecondaryInfoRenderer')
        if vsir:
            vor = traverse_obj(vsir, ('owner', 'videoOwnerRenderer'))
            info.update({
                'channel': self._get_text(vor, 'title'),
                'channel_follower_count': self._get_count(vor, 'subscriberCountText')})

            if not channel_handle:
                channel_handle = self.handle_from_url(
                    traverse_obj(vor, (
                        ('navigationEndpoint', ('title', 'runs', ..., 'navigationEndpoint')),
                        (('commandMetadata', 'webCommandMetadata', 'url'), ('browseEndpoint', 'canonicalBaseUrl')),
                        {str}), get_all=False))

            rows = try_get(
                vsir,
                lambda x: x['metadataRowContainer']['metadataRowContainerRenderer']['rows'],
                list) or []
            multiple_songs = False
            for row in rows:
                if try_get(row, lambda x: x['metadataRowRenderer']['hasDividerLine']) is True:
                    multiple_songs = True
                    break
            for row in rows:
                mrr = row.get('metadataRowRenderer') or {}
                mrr_title = mrr.get('title')
                if not mrr_title:
                    continue
                mrr_title = self._get_text(mrr, 'title')
                mrr_contents_text = self._get_text(mrr, ('contents', 0))
                if mrr_title == 'License':
                    info['license'] = mrr_contents_text
                elif not multiple_songs:
                    if mrr_title == 'Album':
                        info['album'] = mrr_contents_text
                    elif mrr_title == 'Artist':
                        info['artists'] = [mrr_contents_text] if mrr_contents_text else None
                    elif mrr_title == 'Song':
                        info['track'] = mrr_contents_text
            owner_badges = self._extract_badges(traverse_obj(vsir, ('owner', 'videoOwnerRenderer', 'badges')))
            if self._has_badge(owner_badges, BadgeType.VERIFIED):
                info['channel_is_verified'] = True

        info.update({
            'uploader': info.get('channel'),
            'uploader_id': channel_handle,
            'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
        })

        # We only want timestamp IF it has time precision AND a timezone
        # Currently the uploadDate in microformats appears to be in US/Pacific timezone.
        timestamp = (
            parse_iso8601(get_first(microformats, 'uploadDate'), timezone=NO_DEFAULT)
            or parse_iso8601(search_meta('uploadDate'), timezone=NO_DEFAULT)
        )
        upload_date = (
            dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime('%Y%m%d') if timestamp else
            (
                unified_strdate(get_first(microformats, 'uploadDate'))
                or unified_strdate(search_meta('uploadDate'))
            ))

        # In the case we cannot get the timestamp:
        # The upload date for scheduled, live and past live streams / premieres in microformats
        # may be different from the stream date. Although not in UTC, we will prefer it in this case.
        # See: https://github.com/yt-dlp/yt-dlp/pull/2223#issuecomment-1008485139
        if not upload_date or (not timestamp and live_status in ('not_live', None)):
            # this should be in UTC, as configured in the cookie/client context
            upload_date = strftime_or_none(
                self._parse_time_text(self._get_text(vpir, 'dateText'))) or upload_date

        info['upload_date'] = upload_date
        info['timestamp'] = timestamp

        if upload_date and live_status not in ('is_live', 'post_live', 'is_upcoming'):
            # Newly uploaded videos' HLS formats are potentially problematic and need to be checked
            upload_datetime = datetime_from_str(upload_date).replace(tzinfo=dt.timezone.utc)
            if upload_datetime >= datetime_from_str('today-2days'):
                for fmt in info['formats']:
                    if fmt.get('protocol') == 'm3u8_native':
                        fmt['__needs_testing'] = True

        for s_k, d_k in [('artists', 'creators'), ('track', 'alt_title')]:
            v = info.get(s_k)
            if v:
                info[d_k] = v

        badges = self._extract_badges(traverse_obj(vpir, 'badges'))

        is_private = (self._has_badge(badges, BadgeType.AVAILABILITY_PRIVATE)
                      or get_first(video_details, 'isPrivate', expected_type=bool))

        info['availability'] = (
            'public' if self._has_badge(badges, BadgeType.AVAILABILITY_PUBLIC)
            else self._availability(
                is_private=is_private,
                needs_premium=(
                    self._has_badge(badges, BadgeType.AVAILABILITY_PREMIUM)
                    or False if initial_data and is_private is not None else None),
                needs_subscription=(
                    self._has_badge(badges, BadgeType.AVAILABILITY_SUBSCRIPTION)
                    or False if initial_data and is_private is not None else None),
                needs_auth=info['age_limit'] >= 18,
                is_unlisted=None if is_private is None else (
                    self._has_badge(badges, BadgeType.AVAILABILITY_UNLISTED)
                    or get_first(microformats, 'isUnlisted', expected_type=bool))))

        info['__post_extractor'] = self.extract_comments(master_ytcfg, video_id, contents, webpage)

        self.mark_watched(video_id, player_responses)

        return info


class YoutubeTabBaseInfoExtractor(YoutubeBaseInfoExtractor):
    @staticmethod
    def passthrough_smuggled_data(func):
        def _smuggle(info, smuggled_data):
            if info.get('_type') not in ('url', 'url_transparent'):
                return info
            if smuggled_data.get('is_music_url'):
                parsed_url = urllib.parse.urlparse(info['url'])
                if parsed_url.netloc in ('www.youtube.com', 'music.youtube.com'):
                    smuggled_data.pop('is_music_url')
                    info['url'] = urllib.parse.urlunparse(parsed_url._replace(netloc='music.youtube.com'))
            if smuggled_data:
                info['url'] = smuggle_url(info['url'], smuggled_data)
            return info

        @functools.wraps(func)
        def wrapper(self, url):
            url, smuggled_data = unsmuggle_url(url, {})
            if self.is_music_url(url):
                smuggled_data['is_music_url'] = True
            info_dict = func(self, url, smuggled_data)
            if smuggled_data:
                _smuggle(info_dict, smuggled_data)
                if info_dict.get('entries'):
                    info_dict['entries'] = (_smuggle(i, smuggled_data.copy()) for i in info_dict['entries'])
            return info_dict
        return wrapper

    @staticmethod
    def _extract_basic_item_renderer(item):
        # Modified from _extract_grid_item_renderer
        known_basic_renderers = (
            'playlistRenderer', 'videoRenderer', 'channelRenderer', 'showRenderer', 'reelItemRenderer',
        )
        for key, renderer in item.items():
            if not isinstance(renderer, dict):
                continue
            elif key in known_basic_renderers:
                return renderer
            elif key.startswith('grid') and key.endswith('Renderer'):
                return renderer

    def _extract_channel_renderer(self, renderer):
        channel_id = self.ucid_or_none(renderer['channelId'])
        title = self._get_text(renderer, 'title')
        channel_url = format_field(channel_id, None, 'https://www.youtube.com/channel/%s', default=None)
        channel_handle = self.handle_from_url(
            traverse_obj(renderer, (
                'navigationEndpoint', (('commandMetadata', 'webCommandMetadata', 'url'),
                                       ('browseEndpoint', 'canonicalBaseUrl')),
                {str}), get_all=False))
        if not channel_handle:
            # As of 2023-06-01, YouTube sets subscriberCountText to the handle in search
            channel_handle = self.handle_or_none(self._get_text(renderer, 'subscriberCountText'))
        return {
            '_type': 'url',
            'url': channel_url,
            'id': channel_id,
            'ie_key': YoutubeTabIE.ie_key(),
            'channel': title,
            'uploader': title,
            'channel_id': channel_id,
            'channel_url': channel_url,
            'title': title,
            'uploader_id': channel_handle,
            'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
            # See above. YouTube sets videoCountText to the subscriber text in search channel renderers.
            # However, in feed/channels this is set correctly to the subscriber count
            'channel_follower_count': traverse_obj(
                renderer, 'subscriberCountText', 'videoCountText', expected_type=self._get_count),
            'thumbnails': self._extract_thumbnails(renderer, 'thumbnail'),
            'playlist_count': (
                # videoCountText may be the subscriber count
                self._get_count(renderer, 'videoCountText')
                if self._get_count(renderer, 'subscriberCountText') is not None else None),
            'description': self._get_text(renderer, 'descriptionSnippet'),
            'channel_is_verified': True if self._has_badge(
                self._extract_badges(traverse_obj(renderer, 'ownerBadges')), BadgeType.VERIFIED) else None,
        }

    def _grid_entries(self, grid_renderer):
        for item in grid_renderer['items']:
            if not isinstance(item, dict):
                continue
            renderer = self._extract_basic_item_renderer(item)
            if not isinstance(renderer, dict):
                continue
            title = self._get_text(renderer, 'title')

            # playlist
            playlist_id = renderer.get('playlistId')
            if playlist_id:
                yield self.url_result(
                    f'https://www.youtube.com/playlist?list={playlist_id}',
                    ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                    video_title=title)
                continue
            # video
            video_id = renderer.get('videoId')
            if video_id:
                yield self._extract_video(renderer)
                continue
            # channel
            channel_id = renderer.get('channelId')
            if channel_id:
                yield self._extract_channel_renderer(renderer)
                continue
            # generic endpoint URL support
            ep_url = urljoin('https://www.youtube.com/', try_get(
                renderer, lambda x: x['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url'],
                str))
            if ep_url:
                for ie in (YoutubeTabIE, YoutubePlaylistIE, YoutubeIE):
                    if ie.suitable(ep_url):
                        yield self.url_result(
                            ep_url, ie=ie.ie_key(), video_id=ie._match_id(ep_url), video_title=title)
                        break

    def _music_reponsive_list_entry(self, renderer):
        video_id = traverse_obj(renderer, ('playlistItemData', 'videoId'))
        if video_id:
            title = traverse_obj(renderer, (
                'flexColumns', 0, 'musicResponsiveListItemFlexColumnRenderer',
                'text', 'runs', 0, 'text'))
            return self.url_result(f'https://music.youtube.com/watch?v={video_id}',
                                   ie=YoutubeIE.ie_key(), video_id=video_id, title=title)
        playlist_id = traverse_obj(renderer, ('navigationEndpoint', 'watchEndpoint', 'playlistId'))
        if playlist_id:
            video_id = traverse_obj(renderer, ('navigationEndpoint', 'watchEndpoint', 'videoId'))
            if video_id:
                return self.url_result(f'https://music.youtube.com/watch?v={video_id}&list={playlist_id}',
                                       ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
            return self.url_result(f'https://music.youtube.com/playlist?list={playlist_id}',
                                   ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
        browse_id = traverse_obj(renderer, ('navigationEndpoint', 'browseEndpoint', 'browseId'))
        if browse_id:
            return self.url_result(f'https://music.youtube.com/browse/{browse_id}',
                                   ie=YoutubeTabIE.ie_key(), video_id=browse_id)

    def _shelf_entries_from_content(self, shelf_renderer):
        content = shelf_renderer.get('content')
        if not isinstance(content, dict):
            return
        renderer = content.get('gridRenderer') or content.get('expandedShelfContentsRenderer')
        if renderer:
            # TODO: add support for nested playlists so each shelf is processed
            # as separate playlist
            # TODO: this includes only first N items
            yield from self._grid_entries(renderer)
        renderer = content.get('horizontalListRenderer')
        if renderer:
            # TODO: handle case
            pass

    def _shelf_entries(self, shelf_renderer, skip_channels=False):
        ep = try_get(
            shelf_renderer, lambda x: x['endpoint']['commandMetadata']['webCommandMetadata']['url'],
            str)
        shelf_url = urljoin('https://www.youtube.com', ep)
        if shelf_url:
            # Skipping links to another channels, note that checking for
            # endpoint.commandMetadata.webCommandMetadata.webPageTypwebPageType == WEB_PAGE_TYPE_CHANNEL
            # will not work
            if skip_channels and '/channels?' in shelf_url:
                return
            title = self._get_text(shelf_renderer, 'title')
            yield self.url_result(shelf_url, video_title=title)
        # Shelf may not contain shelf URL, fallback to extraction from content
        yield from self._shelf_entries_from_content(shelf_renderer)

    def _playlist_entries(self, video_list_renderer):
        for content in video_list_renderer['contents']:
            if not isinstance(content, dict):
                continue
            renderer = content.get('playlistVideoRenderer') or content.get('playlistPanelVideoRenderer')
            if not isinstance(renderer, dict):
                continue
            video_id = renderer.get('videoId')
            if not video_id:
                continue
            yield self._extract_video(renderer)

    def _rich_entries(self, rich_grid_renderer):
        renderer = traverse_obj(
            rich_grid_renderer,
            ('content', ('videoRenderer', 'reelItemRenderer', 'playlistRenderer')), get_all=False) or {}
        video_id = renderer.get('videoId')
        if video_id:
            yield self._extract_video(renderer)
            return
        playlist_id = renderer.get('playlistId')
        if playlist_id:
            yield self.url_result(
                f'https://www.youtube.com/playlist?list={playlist_id}',
                ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                video_title=self._get_text(renderer, 'title'))
            return

    def _video_entry(self, video_renderer):
        video_id = video_renderer.get('videoId')
        if video_id:
            return self._extract_video(video_renderer)

    def _hashtag_tile_entry(self, hashtag_tile_renderer):
        url = urljoin('https://youtube.com', traverse_obj(
            hashtag_tile_renderer, ('onTapCommand', 'commandMetadata', 'webCommandMetadata', 'url')))
        if url:
            return self.url_result(
                url, ie=YoutubeTabIE.ie_key(), title=self._get_text(hashtag_tile_renderer, 'hashtag'))

    def _post_thread_entries(self, post_thread_renderer):
        post_renderer = try_get(
            post_thread_renderer, lambda x: x['post']['backstagePostRenderer'], dict)
        if not post_renderer:
            return
        # video attachment
        video_renderer = try_get(
            post_renderer, lambda x: x['backstageAttachment']['videoRenderer'], dict) or {}
        video_id = video_renderer.get('videoId')
        if video_id:
            entry = self._extract_video(video_renderer)
            if entry:
                yield entry
        # playlist attachment
        playlist_id = try_get(
            post_renderer, lambda x: x['backstageAttachment']['playlistRenderer']['playlistId'], str)
        if playlist_id:
            yield self.url_result(
                f'https://www.youtube.com/playlist?list={playlist_id}',
                ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
        # inline video links
        runs = try_get(post_renderer, lambda x: x['contentText']['runs'], list) or []
        for run in runs:
            if not isinstance(run, dict):
                continue
            ep_url = try_get(
                run, lambda x: x['navigationEndpoint']['urlEndpoint']['url'], str)
            if not ep_url:
                continue
            if not YoutubeIE.suitable(ep_url):
                continue
            ep_video_id = YoutubeIE._match_id(ep_url)
            if video_id == ep_video_id:
                continue
            yield self.url_result(ep_url, ie=YoutubeIE.ie_key(), video_id=ep_video_id)

    def _post_thread_continuation_entries(self, post_thread_continuation):
        contents = post_thread_continuation.get('contents')
        if not isinstance(contents, list):
            return
        for content in contents:
            renderer = content.get('backstagePostThreadRenderer')
            if isinstance(renderer, dict):
                yield from self._post_thread_entries(renderer)
                continue
            renderer = content.get('videoRenderer')
            if isinstance(renderer, dict):
                yield self._video_entry(renderer)

    r''' # unused
    def _rich_grid_entries(self, contents):
        for content in contents:
            video_renderer = try_get(content, lambda x: x['richItemRenderer']['content']['videoRenderer'], dict)
            if video_renderer:
                entry = self._video_entry(video_renderer)
                if entry:
                    yield entry
    '''

    def _report_history_entries(self, renderer):
        for url in traverse_obj(renderer, (
                'rows', ..., 'reportHistoryTableRowRenderer', 'cells', ...,
                'reportHistoryTableCellRenderer', 'cell', 'reportHistoryTableTextCellRenderer', 'text', 'runs', ...,
                'navigationEndpoint', 'commandMetadata', 'webCommandMetadata', 'url')):
            yield self.url_result(urljoin('https://www.youtube.com', url), YoutubeIE)

    def _extract_entries(self, parent_renderer, continuation_list):
        # continuation_list is modified in-place with continuation_list = [continuation_token]
        continuation_list[:] = [None]
        contents = try_get(parent_renderer, lambda x: x['contents'], list) or []
        for content in contents:
            if not isinstance(content, dict):
                continue
            is_renderer = traverse_obj(
                content, 'itemSectionRenderer', 'musicShelfRenderer', 'musicShelfContinuation',
                expected_type=dict)
            if not is_renderer:
                if content.get('richItemRenderer'):
                    for entry in self._rich_entries(content['richItemRenderer']):
                        yield entry
                    continuation_list[0] = self._extract_continuation(parent_renderer)
                elif content.get('reportHistorySectionRenderer'):  # https://www.youtube.com/reporthistory
                    table = traverse_obj(content, ('reportHistorySectionRenderer', 'table', 'tableRenderer'))
                    yield from self._report_history_entries(table)
                    continuation_list[0] = self._extract_continuation(table)
                continue

            isr_contents = try_get(is_renderer, lambda x: x['contents'], list) or []
            for isr_content in isr_contents:
                if not isinstance(isr_content, dict):
                    continue

                known_renderers = {
                    'playlistVideoListRenderer': self._playlist_entries,
                    'gridRenderer': self._grid_entries,
                    'reelShelfRenderer': self._grid_entries,
                    'shelfRenderer': self._shelf_entries,
                    'musicResponsiveListItemRenderer': lambda x: [self._music_reponsive_list_entry(x)],
                    'backstagePostThreadRenderer': self._post_thread_entries,
                    'videoRenderer': lambda x: [self._video_entry(x)],
                    'playlistRenderer': lambda x: self._grid_entries({'items': [{'playlistRenderer': x}]}),
                    'channelRenderer': lambda x: self._grid_entries({'items': [{'channelRenderer': x}]}),
                    'hashtagTileRenderer': lambda x: [self._hashtag_tile_entry(x)],
                    'richGridRenderer': lambda x: self._extract_entries(x, continuation_list),
                }
                for key, renderer in isr_content.items():
                    if key not in known_renderers:
                        continue
                    for entry in known_renderers[key](renderer):
                        if entry:
                            yield entry
                    continuation_list[0] = self._extract_continuation(renderer)
                    break

            if not continuation_list[0]:
                continuation_list[0] = self._extract_continuation(is_renderer)

        if not continuation_list[0]:
            continuation_list[0] = self._extract_continuation(parent_renderer)

    def _entries(self, tab, item_id, ytcfg, account_syncid, visitor_data):
        continuation_list = [None]
        extract_entries = lambda x: self._extract_entries(x, continuation_list)
        tab_content = try_get(tab, lambda x: x['content'], dict)
        if not tab_content:
            return
        parent_renderer = (
            try_get(tab_content, lambda x: x['sectionListRenderer'], dict)
            or try_get(tab_content, lambda x: x['richGridRenderer'], dict) or {})
        yield from extract_entries(parent_renderer)
        continuation = continuation_list[0]
        seen_continuations = set()
        for page_num in itertools.count(1):
            if not continuation:
                break
            continuation_token = continuation.get('continuation')
            if continuation_token is not None and continuation_token in seen_continuations:
                self.write_debug('Detected YouTube feed looping - assuming end of feed.')
                break
            seen_continuations.add(continuation_token)
            headers = self.generate_api_headers(
                ytcfg=ytcfg, account_syncid=account_syncid, visitor_data=visitor_data)
            response = self._extract_response(
                item_id=f'{item_id} page {page_num}',
                query=continuation, headers=headers, ytcfg=ytcfg,
                check_get_keys=('continuationContents', 'onResponseReceivedActions', 'onResponseReceivedEndpoints'))

            if not response:
                break
            # Extracting updated visitor data is required to prevent an infinite extraction loop in some cases
            # See: https://github.com/ytdl-org/youtube-dl/issues/28702
            visitor_data = self._extract_visitor_data(response) or visitor_data

            known_renderers = {
                'videoRenderer': (self._grid_entries, 'items'),  # for membership tab
                'gridPlaylistRenderer': (self._grid_entries, 'items'),
                'gridVideoRenderer': (self._grid_entries, 'items'),
                'gridChannelRenderer': (self._grid_entries, 'items'),
                'playlistVideoRenderer': (self._playlist_entries, 'contents'),
                'itemSectionRenderer': (extract_entries, 'contents'),  # for feeds
                'richItemRenderer': (extract_entries, 'contents'),  # for hashtag
                'backstagePostThreadRenderer': (self._post_thread_continuation_entries, 'contents'),
                'reportHistoryTableRowRenderer': (self._report_history_entries, 'rows'),
                'playlistVideoListContinuation': (self._playlist_entries, None),
                'gridContinuation': (self._grid_entries, None),
                'itemSectionContinuation': (self._post_thread_continuation_entries, None),
                'sectionListContinuation': (extract_entries, None),  # for feeds
            }

            continuation_items = traverse_obj(response, (
                ('onResponseReceivedActions', 'onResponseReceivedEndpoints'), ...,
                'appendContinuationItemsAction', 'continuationItems',
            ), 'continuationContents', get_all=False)
            continuation_item = traverse_obj(continuation_items, 0, None, expected_type=dict, default={})

            video_items_renderer = None
            for key in continuation_item:
                if key not in known_renderers:
                    continue
                func, parent_key = known_renderers[key]
                video_items_renderer = {parent_key: continuation_items} if parent_key else continuation_items
                continuation_list = [None]
                yield from func(video_items_renderer)
                continuation = continuation_list[0] or self._extract_continuation(video_items_renderer)

            if not video_items_renderer:
                break

    @staticmethod
    def _extract_selected_tab(tabs, fatal=True):
        for tab_renderer in tabs:
            if tab_renderer.get('selected'):
                return tab_renderer
        if fatal:
            raise ExtractorError('Unable to find selected tab')

    @staticmethod
    def _extract_tab_renderers(response):
        return traverse_obj(
            response, ('contents', 'twoColumnBrowseResultsRenderer', 'tabs', ..., ('tabRenderer', 'expandableTabRenderer')), expected_type=dict)

    def _extract_from_tabs(self, item_id, ytcfg, data, tabs):
        metadata = self._extract_metadata_from_tabs(item_id, data)

        selected_tab = self._extract_selected_tab(tabs)
        metadata['title'] += format_field(selected_tab, 'title', ' - %s')
        metadata['title'] += format_field(selected_tab, 'expandedText', ' - %s')

        return self.playlist_result(
            self._entries(
                selected_tab, metadata['id'], ytcfg,
                self._extract_account_syncid(ytcfg, data),
                self._extract_visitor_data(data, ytcfg)),
            **metadata)

    def _extract_metadata_from_tabs(self, item_id, data):
        info = {'id': item_id}

        metadata_renderer = traverse_obj(data, ('metadata', 'channelMetadataRenderer'), expected_type=dict)
        if metadata_renderer:
            channel_id = traverse_obj(metadata_renderer, ('externalId', {self.ucid_or_none}),
                                      ('channelUrl', {self.ucid_from_url}))
            info.update({
                'channel': metadata_renderer.get('title'),
                'channel_id': channel_id,
            })
            if info['channel_id']:
                info['id'] = info['channel_id']
        else:
            metadata_renderer = traverse_obj(data, ('metadata', 'playlistMetadataRenderer'), expected_type=dict)

        # pageHeaderViewModel slow rollout began April 2024
        page_header_view_model = traverse_obj(data, (
            'header', 'pageHeaderRenderer', 'content', 'pageHeaderViewModel', {dict}))

        # We can get the uncropped banner/avatar by replacing the crop params with '=s0'
        # See: https://github.com/yt-dlp/yt-dlp/issues/2237#issuecomment-1013694714
        def _get_uncropped(url):
            return url_or_none((url or '').split('=')[0] + '=s0')

        avatar_thumbnails = self._extract_thumbnails(metadata_renderer, 'avatar')
        if avatar_thumbnails:
            uncropped_avatar = _get_uncropped(avatar_thumbnails[0]['url'])
            if uncropped_avatar:
                avatar_thumbnails.append({
                    'url': uncropped_avatar,
                    'id': 'avatar_uncropped',
                    'preference': 1,
                })

        channel_banners = (
            self._extract_thumbnails(data, ('header', ..., ('banner', 'mobileBanner', 'tvBanner')))
            or self._extract_thumbnails(
                page_header_view_model, ('banner', 'imageBannerViewModel', 'image'), final_key='sources'))
        for banner in channel_banners:
            banner['preference'] = -10

        if channel_banners:
            uncropped_banner = _get_uncropped(channel_banners[0]['url'])
            if uncropped_banner:
                channel_banners.append({
                    'url': uncropped_banner,
                    'id': 'banner_uncropped',
                    'preference': -5,
                })

        # Deprecated - remove primary_sidebar_renderer when layout discontinued
        primary_sidebar_renderer = self._extract_sidebar_info_renderer(data, 'playlistSidebarPrimaryInfoRenderer')
        playlist_header_renderer = traverse_obj(data, ('header', 'playlistHeaderRenderer'), expected_type=dict)

        primary_thumbnails = self._extract_thumbnails(
            primary_sidebar_renderer, ('thumbnailRenderer', ('playlistVideoThumbnailRenderer', 'playlistCustomThumbnailRenderer'), 'thumbnail'))
        playlist_thumbnails = self._extract_thumbnails(
            playlist_header_renderer, ('playlistHeaderBanner', 'heroPlaylistThumbnailRenderer', 'thumbnail'))

        info.update({
            'title': (traverse_obj(metadata_renderer, 'title')
                      or self._get_text(data, ('header', 'hashtagHeaderRenderer', 'hashtag'))
                      or info['id']),
            'availability': self._extract_availability(data),
            'channel_follower_count': (
                self._get_count(data, ('header', ..., 'subscriberCountText'))
                or traverse_obj(page_header_view_model, (
                    'metadata', 'contentMetadataViewModel', 'metadataRows', ..., 'metadataParts',
                    lambda _, v: 'subscribers' in v['text']['content'], 'text', 'content', {parse_count}, any))),
            'description': try_get(metadata_renderer, lambda x: x.get('description', '')),
            'tags': (traverse_obj(data, ('microformat', 'microformatDataRenderer', 'tags', ..., {str}))
                     or traverse_obj(metadata_renderer, ('keywords', {lambda x: x and shlex.split(x)}, ...))),
            'thumbnails': (primary_thumbnails or playlist_thumbnails) + avatar_thumbnails + channel_banners,
        })

        channel_handle = (
            traverse_obj(metadata_renderer, (('vanityChannelUrl', ('ownerUrls', ...)), {self.handle_from_url}), get_all=False)
            or traverse_obj(data, ('header', ..., 'channelHandleText', {self.handle_or_none}), get_all=False))

        if channel_handle:
            info.update({
                'uploader_id': channel_handle,
                'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
            })

        channel_badges = self._extract_badges(traverse_obj(data, ('header', ..., 'badges'), get_all=False))
        if self._has_badge(channel_badges, BadgeType.VERIFIED):
            info['channel_is_verified'] = True
        # Playlist stats is a text runs array containing [video count, view count, last updated].
        # last updated or (view count and last updated) may be missing.
        playlist_stats = get_first(
            (primary_sidebar_renderer, playlist_header_renderer), (('stats', 'briefStats', 'numVideosText'), ))

        last_updated_unix = self._parse_time_text(
            self._get_text(playlist_stats, 2)  # deprecated, remove when old layout discontinued
            or self._get_text(playlist_header_renderer, ('byline', 1, 'playlistBylineRenderer', 'text')))
        info['modified_date'] = strftime_or_none(last_updated_unix)

        info['view_count'] = self._get_count(playlist_stats, 1)
        if info['view_count'] is None:  # 0 is allowed
            info['view_count'] = self._get_count(playlist_header_renderer, 'viewCountText')
        if info['view_count'] is None:
            info['view_count'] = self._get_count(data, (
                'contents', 'twoColumnBrowseResultsRenderer', 'tabs', ..., 'tabRenderer', 'content', 'sectionListRenderer',
                'contents', ..., 'itemSectionRenderer', 'contents', ..., 'channelAboutFullMetadataRenderer', 'viewCountText'))

        info['playlist_count'] = self._get_count(playlist_stats, 0)
        if info['playlist_count'] is None:  # 0 is allowed
            info['playlist_count'] = self._get_count(playlist_header_renderer, ('byline', 0, 'playlistBylineRenderer', 'text'))

        if not info.get('channel_id'):
            owner = traverse_obj(playlist_header_renderer, 'ownerText')
            if not owner:  # Deprecated
                owner = traverse_obj(
                    self._extract_sidebar_info_renderer(data, 'playlistSidebarSecondaryInfoRenderer'),
                    ('videoOwner', 'videoOwnerRenderer', 'title'))
            owner_text = self._get_text(owner)
            browse_ep = traverse_obj(owner, ('runs', 0, 'navigationEndpoint', 'browseEndpoint')) or {}
            info.update({
                'channel': self._search_regex(r'^by (.+) and \d+ others?$', owner_text, 'uploader', default=owner_text),
                'channel_id': self.ucid_or_none(browse_ep.get('browseId')),
                'uploader_id': self.handle_from_url(urljoin('https://www.youtube.com', browse_ep.get('canonicalBaseUrl'))),
            })

        info.update({
            'uploader': info['channel'],
            'channel_url': format_field(info.get('channel_id'), None, 'https://www.youtube.com/channel/%s', default=None),
            'uploader_url': format_field(info.get('uploader_id'), None, 'https://www.youtube.com/%s', default=None),
        })

        return info

    def _extract_inline_playlist(self, playlist, playlist_id, data, ytcfg):
        first_id = last_id = response = None
        for page_num in itertools.count(1):
            videos = list(self._playlist_entries(playlist))
            if not videos:
                return
            start = next((i for i, v in enumerate(videos) if v['id'] == last_id), -1) + 1
            if start >= len(videos):
                return
            yield from videos[start:]
            first_id = first_id or videos[0]['id']
            last_id = videos[-1]['id']
            watch_endpoint = try_get(
                playlist, lambda x: x['contents'][-1]['playlistPanelVideoRenderer']['navigationEndpoint']['watchEndpoint'])
            headers = self.generate_api_headers(
                ytcfg=ytcfg, account_syncid=self._extract_account_syncid(ytcfg, data),
                visitor_data=self._extract_visitor_data(response, data, ytcfg))
            query = {
                'playlistId': playlist_id,
                'videoId': watch_endpoint.get('videoId') or last_id,
                'index': watch_endpoint.get('index') or len(videos),
                'params': watch_endpoint.get('params') or 'OAE%3D',
            }
            response = self._extract_response(
                item_id=f'{playlist_id} page {page_num}',
                query=query, ep='next', headers=headers, ytcfg=ytcfg,
                check_get_keys='contents',
            )
            playlist = try_get(
                response, lambda x: x['contents']['twoColumnWatchNextResults']['playlist']['playlist'], dict)

    def _extract_from_playlist(self, item_id, url, data, playlist, ytcfg):
        title = playlist.get('title') or try_get(
            data, lambda x: x['titleText']['simpleText'], str)
        playlist_id = playlist.get('playlistId') or item_id

        # Delegating everything except mix playlists to regular tab-based playlist URL
        playlist_url = urljoin(url, try_get(
            playlist, lambda x: x['endpoint']['commandMetadata']['webCommandMetadata']['url'],
            str))

        # Some playlists are unviewable but YouTube still provides a link to the (broken) playlist page [1]
        # [1] MLCT, RLTDwFCb4jeqaKWnciAYM-ZVHg
        is_known_unviewable = re.fullmatch(r'MLCT|RLTD[\w-]{22}', playlist_id)

        if playlist_url and playlist_url != url and not is_known_unviewable:
            return self.url_result(
                playlist_url, ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                video_title=title)

        return self.playlist_result(
            self._extract_inline_playlist(playlist, playlist_id, data, ytcfg),
            playlist_id=playlist_id, playlist_title=title)

    def _extract_availability(self, data):
        """
        Gets the availability of a given playlist/tab.
        Note: Unless YouTube tells us explicitly, we do not assume it is public
        @param data: response
        """
        sidebar_renderer = self._extract_sidebar_info_renderer(data, 'playlistSidebarPrimaryInfoRenderer') or {}
        playlist_header_renderer = traverse_obj(data, ('header', 'playlistHeaderRenderer')) or {}
        player_header_privacy = playlist_header_renderer.get('privacy')

        badges = self._extract_badges(traverse_obj(sidebar_renderer, 'badges'))

        # Personal playlists, when authenticated, have a dropdown visibility selector instead of a badge
        privacy_setting_icon = get_first(
            (playlist_header_renderer, sidebar_renderer),
            ('privacyForm', 'dropdownFormFieldRenderer', 'dropdown', 'dropdownRenderer', 'entries',
             lambda _, v: v['privacyDropdownItemRenderer']['isSelected'], 'privacyDropdownItemRenderer', 'icon', 'iconType'),
            expected_type=str)

        microformats_is_unlisted = traverse_obj(
            data, ('microformat', 'microformatDataRenderer', 'unlisted'), expected_type=bool)

        return (
            'public' if (
                self._has_badge(badges, BadgeType.AVAILABILITY_PUBLIC)
                or player_header_privacy == 'PUBLIC'
                or privacy_setting_icon == 'PRIVACY_PUBLIC')
            else self._availability(
                is_private=(
                    self._has_badge(badges, BadgeType.AVAILABILITY_PRIVATE)
                    or player_header_privacy == 'PRIVATE' if player_header_privacy is not None
                    else privacy_setting_icon == 'PRIVACY_PRIVATE' if privacy_setting_icon is not None else None),
                is_unlisted=(
                    self._has_badge(badges, BadgeType.AVAILABILITY_UNLISTED)
                    or player_header_privacy == 'UNLISTED' if player_header_privacy is not None
                    else privacy_setting_icon == 'PRIVACY_UNLISTED' if privacy_setting_icon is not None
                    else microformats_is_unlisted if microformats_is_unlisted is not None else None),
                needs_subscription=self._has_badge(badges, BadgeType.AVAILABILITY_SUBSCRIPTION) or None,
                needs_premium=self._has_badge(badges, BadgeType.AVAILABILITY_PREMIUM) or None,
                needs_auth=False))

    @staticmethod
    def _extract_sidebar_info_renderer(data, info_renderer, expected_type=dict):
        sidebar_renderer = try_get(
            data, lambda x: x['sidebar']['playlistSidebarRenderer']['items'], list) or []
        for item in sidebar_renderer:
            renderer = try_get(item, lambda x: x[info_renderer], expected_type)
            if renderer:
                return renderer

    def _reload_with_unavailable_videos(self, item_id, data, ytcfg):
        """
        Reload playlists with unavailable videos (e.g. private videos, region blocked, etc.)
        """
        is_playlist = bool(traverse_obj(
            data, ('metadata', 'playlistMetadataRenderer'), ('header', 'playlistHeaderRenderer')))
        if not is_playlist:
            return
        headers = self.generate_api_headers(
            ytcfg=ytcfg, account_syncid=self._extract_account_syncid(ytcfg, data),
            visitor_data=self._extract_visitor_data(data, ytcfg))
        query = {
            'params': 'wgYCCAA=',
            'browseId': f'VL{item_id}',
        }
        return self._extract_response(
            item_id=item_id, headers=headers, query=query,
            check_get_keys='contents', fatal=False, ytcfg=ytcfg,
            note='Redownloading playlist API JSON with unavailable videos')

    @functools.cached_property
    def skip_webpage(self):
        return 'webpage' in self._configuration_arg('skip', ie_key=YoutubeTabIE.ie_key())

    def _extract_webpage(self, url, item_id, fatal=True):
        webpage, data = None, None
        for retry in self.RetryManager(fatal=fatal):
            try:
                webpage = self._download_webpage(url, item_id, note='Downloading webpage')
                data = self.extract_yt_initial_data(item_id, webpage or '', fatal=fatal) or {}
            except ExtractorError as e:
                if isinstance(e.cause, network_exceptions):
                    if not isinstance(e.cause, HTTPError) or e.cause.status not in (403, 429):
                        retry.error = e
                        continue
                self._error_or_warning(e, fatal=fatal)
                break

            try:
                self._extract_and_report_alerts(data)
            except ExtractorError as e:
                self._error_or_warning(e, fatal=fatal)
                break

            # Sometimes youtube returns a webpage with incomplete ytInitialData
            # See: https://github.com/yt-dlp/yt-dlp/issues/116
            if not traverse_obj(data, 'contents', 'currentVideoEndpoint', 'onResponseReceivedActions'):
                retry.error = ExtractorError('Incomplete yt initial data received')
                data = None
                continue

        return webpage, data

    def _report_playlist_authcheck(self, ytcfg, fatal=True):
        """Use if failed to extract ytcfg (and data) from initial webpage"""
        if not ytcfg and self.is_authenticated:
            msg = 'Playlists that require authentication may not extract correctly without a successful webpage download'
            if 'authcheck' not in self._configuration_arg('skip', ie_key=YoutubeTabIE.ie_key()) and fatal:
                raise ExtractorError(
                    f'{msg}. If you are not downloading private content, or '
                    'your cookies are only for the first account and channel,'
                    ' pass "--extractor-args youtubetab:skip=authcheck" to skip this check',
                    expected=True)
            self.report_warning(msg, only_once=True)

    def _extract_data(self, url, item_id, ytcfg=None, fatal=True, webpage_fatal=False, default_client='web'):
        data = None
        if not self.skip_webpage:
            webpage, data = self._extract_webpage(url, item_id, fatal=webpage_fatal)
            ytcfg = ytcfg or self.extract_ytcfg(item_id, webpage)
            # Reject webpage data if redirected to home page without explicitly requesting
            selected_tab = self._extract_selected_tab(self._extract_tab_renderers(data), fatal=False) or {}
            if (url != 'https://www.youtube.com/feed/recommended'
                    and selected_tab.get('tabIdentifier') == 'FEwhat_to_watch'  # Home page
                    and 'no-youtube-channel-redirect' not in self.get_param('compat_opts', [])):
                msg = 'The channel/playlist does not exist and the URL redirected to youtube.com home page'
                if fatal:
                    raise ExtractorError(msg, expected=True)
                self.report_warning(msg, only_once=True)
        if not data:
            self._report_playlist_authcheck(ytcfg, fatal=fatal)
            data = self._extract_tab_endpoint(url, item_id, ytcfg, fatal=fatal, default_client=default_client)
        return data, ytcfg

    def _extract_tab_endpoint(self, url, item_id, ytcfg=None, fatal=True, default_client='web'):
        headers = self.generate_api_headers(ytcfg=ytcfg, default_client=default_client)
        resolve_response = self._extract_response(
            item_id=item_id, query={'url': url}, check_get_keys='endpoint', headers=headers, ytcfg=ytcfg, fatal=fatal,
            ep='navigation/resolve_url', note='Downloading API parameters API JSON', default_client=default_client)
        endpoints = {'browseEndpoint': 'browse', 'watchEndpoint': 'next'}
        for ep_key, ep in endpoints.items():
            params = try_get(resolve_response, lambda x: x['endpoint'][ep_key], dict)
            if params:
                return self._extract_response(
                    item_id=item_id, query=params, ep=ep, headers=headers,
                    ytcfg=ytcfg, fatal=fatal, default_client=default_client,
                    check_get_keys=('contents', 'currentVideoEndpoint', 'onResponseReceivedActions'))
        err_note = 'Failed to resolve url (does the playlist exist?)'
        if fatal:
            raise ExtractorError(err_note, expected=True)
        self.report_warning(err_note, item_id)

    _SEARCH_PARAMS = None

    def _search_results(self, query, params=NO_DEFAULT, default_client='web'):
        data = {'query': query}
        if params is NO_DEFAULT:
            params = self._SEARCH_PARAMS
        if params:
            data['params'] = params

        content_keys = (
            ('contents', 'twoColumnSearchResultsRenderer', 'primaryContents', 'sectionListRenderer', 'contents'),
            ('onResponseReceivedCommands', 0, 'appendContinuationItemsAction', 'continuationItems'),
            # ytmusic search
            ('contents', 'tabbedSearchResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents'),
            ('continuationContents', ),
        )
        display_id = f'query "{query}"'
        check_get_keys = tuple({keys[0] for keys in content_keys})
        ytcfg = self._download_ytcfg(default_client, display_id) if not self.skip_webpage else {}
        self._report_playlist_authcheck(ytcfg, fatal=False)

        continuation_list = [None]
        search = None
        for page_num in itertools.count(1):
            data.update(continuation_list[0] or {})
            headers = self.generate_api_headers(
                ytcfg=ytcfg, visitor_data=self._extract_visitor_data(search), default_client=default_client)
            search = self._extract_response(
                item_id=f'{display_id} page {page_num}', ep='search', query=data,
                default_client=default_client, check_get_keys=check_get_keys, ytcfg=ytcfg, headers=headers)
            slr_contents = traverse_obj(search, *content_keys)
            yield from self._extract_entries({'contents': list(variadic(slr_contents))}, continuation_list)
            if not continuation_list[0]:
                break


class YoutubeTabIE(YoutubeTabBaseInfoExtractor):
    IE_DESC = 'YouTube Tabs'
    _VALID_URL = r'''(?x:
        https?://
            (?!consent\.)(?:\w+\.)?
            (?:
                youtube(?:kids)?\.com|
                {invidious}
            )/
            (?:
                (?P<channel_type>channel|c|user|browse)/|
                (?P<not_channel>
                    feed/|hashtag/|
                    (?:playlist|watch)\?.*?\blist=
                )|
                (?!(?:{reserved_names})\b)  # Direct URLs
            )
            (?P<id>[^/?\#&]+)
    )'''.format(
        reserved_names=YoutubeBaseInfoExtractor._RESERVED_NAMES,
        invidious='|'.join(YoutubeBaseInfoExtractor._INVIDIOUS_SITES),
    )
    IE_NAME = 'youtube:tab'

    _TESTS = [{
        'note': 'playlists, multipage',
        'url': 'https://www.youtube.com/c/ИгорьКлейнер/playlists?view=1&flow=grid',
        'playlist_mincount': 94,
        'info_dict': {
            'id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'title': 'Igor Kleiner Ph.D. - Playlists',
            'description': 'md5:15d7dd9e333cb987907fcb0d604b233a',
            'uploader': 'Igor Kleiner Ph.D.',
            'uploader_id': '@IgorDataScience',
            'uploader_url': 'https://www.youtube.com/@IgorDataScience',
            'channel': 'Igor Kleiner Ph.D.',
            'channel_id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'tags': ['критическое мышление', 'наука просто', 'математика', 'анализ данных'],
            'channel_url': 'https://www.youtube.com/channel/UCqj7Cz7revf5maW9g5pgNcg',
            'channel_follower_count': int,
        },
    }, {
        'note': 'playlists, multipage, different order',
        'url': 'https://www.youtube.com/user/igorkle1/playlists?view=1&sort=dd',
        'playlist_mincount': 94,
        'info_dict': {
            'id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'title': 'Igor Kleiner Ph.D. - Playlists',
            'description': 'md5:15d7dd9e333cb987907fcb0d604b233a',
            'uploader': 'Igor Kleiner Ph.D.',
            'uploader_id': '@IgorDataScience',
            'uploader_url': 'https://www.youtube.com/@IgorDataScience',
            'tags': ['критическое мышление', 'наука просто', 'математика', 'анализ данных'],
            'channel_id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'channel': 'Igor Kleiner Ph.D.',
            'channel_url': 'https://www.youtube.com/channel/UCqj7Cz7revf5maW9g5pgNcg',
            'channel_follower_count': int,
        },
    }, {
        'note': 'playlists, series',
        'url': 'https://www.youtube.com/c/3blue1brown/playlists?view=50&sort=dd&shelf_id=3',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'UCYO_jab_esuFRV4b17AJtAw',
            'title': '3Blue1Brown - Playlists',
            'description': 'md5:4d1da95432004b7ba840ebc895b6b4c9',
            'channel_url': 'https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw',
            'channel': '3Blue1Brown',
            'channel_id': 'UCYO_jab_esuFRV4b17AJtAw',
            'uploader_id': '@3blue1brown',
            'uploader_url': 'https://www.youtube.com/@3blue1brown',
            'uploader': '3Blue1Brown',
            'tags': ['Mathematics'],
            'channel_follower_count': int,
            'channel_is_verified': True,
        },
    }, {
        'note': 'playlists, singlepage',
        'url': 'https://www.youtube.com/user/ThirstForScience/playlists',
        'playlist_mincount': 4,
        'info_dict': {
            'id': 'UCAEtajcuhQ6an9WEzY9LEMQ',
            'title': 'ThirstForScience - Playlists',
            'description': 'md5:609399d937ea957b0f53cbffb747a14c',
            'uploader': 'ThirstForScience',
            'uploader_url': 'https://www.youtube.com/@ThirstForScience',
            'uploader_id': '@ThirstForScience',
            'channel_id': 'UCAEtajcuhQ6an9WEzY9LEMQ',
            'channel_url': 'https://www.youtube.com/channel/UCAEtajcuhQ6an9WEzY9LEMQ',
            'tags': 'count:12',
            'channel': 'ThirstForScience',
            'channel_follower_count': int,
        },
    }, {
        'url': 'https://www.youtube.com/c/ChristophLaimer/playlists',
        'only_matching': True,
    }, {
        'note': 'basic, single video playlist',
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
        'info_dict': {
            'id': 'PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
            'title': 'youtube-dl public playlist',
            'description': '',
            'tags': [],
            'view_count': int,
            'modified_date': '20201130',
            'channel': 'Sergey M.',
            'channel_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'channel_url': 'https://www.youtube.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
            'availability': 'public',
            'uploader': 'Sergey M.',
            'uploader_url': 'https://www.youtube.com/@sergeym.6173',
            'uploader_id': '@sergeym.6173',
        },
        'playlist_count': 1,
    }, {
        'note': 'empty playlist',
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
        'info_dict': {
            'id': 'PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
            'title': 'youtube-dl empty playlist',
            'tags': [],
            'channel': 'Sergey M.',
            'description': '',
            'modified_date': '20230921',
            'channel_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'channel_url': 'https://www.youtube.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
            'availability': 'unlisted',
            'uploader_url': 'https://www.youtube.com/@sergeym.6173',
            'uploader_id': '@sergeym.6173',
            'uploader': 'Sergey M.',
        },
        'playlist_count': 0,
    }, {
        'note': 'Home tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/featured',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Home',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'channel': 'lex will',
            'tags': ['bible', 'history', 'prophesy'],
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_follower_count': int,
        },
        'playlist_mincount': 2,
    }, {
        'note': 'Videos tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/videos',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Videos',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel': 'lex will',
            'channel_follower_count': int,
        },
        'playlist_mincount': 975,
    }, {
        'note': 'Videos tab, sorted by popular',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/videos?view=0&sort=p&flow=grid',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Videos',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel': 'lex will',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_follower_count': int,
        },
        'playlist_mincount': 199,
    }, {
        'note': 'Playlists tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/playlists',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Playlists',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel': 'lex will',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_follower_count': int,
        },
        'playlist_mincount': 17,
    }, {
        'note': 'Community tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/community',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Community',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'channel': 'lex will',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_follower_count': int,
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'uploader_id': '@lexwill718',
            'uploader': 'lex will',
        },
        'playlist_mincount': 18,
    }, {
        'note': 'Channels tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/channels',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Channels',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'channel': 'lex will',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_follower_count': int,
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'uploader_id': '@lexwill718',
            'uploader': 'lex will',
        },
        'playlist_mincount': 12,
    }, {
        'note': 'Search tab',
        'url': 'https://www.youtube.com/c/3blue1brown/search?query=linear%20algebra',
        'playlist_mincount': 40,
        'info_dict': {
            'id': 'UCYO_jab_esuFRV4b17AJtAw',
            'title': '3Blue1Brown - Search - linear algebra',
            'description': 'md5:4d1da95432004b7ba840ebc895b6b4c9',
            'channel_url': 'https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw',
            'tags': ['Mathematics'],
            'channel': '3Blue1Brown',
            'channel_id': 'UCYO_jab_esuFRV4b17AJtAw',
            'channel_follower_count': int,
            'uploader_url': 'https://www.youtube.com/@3blue1brown',
            'uploader_id': '@3blue1brown',
            'uploader': '3Blue1Brown',
            'channel_is_verified': True,
        },
    }, {
        'url': 'https://invidio.us/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'url': 'https://www.youtubekids.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'url': 'https://music.youtube.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'note': 'Playlist with deleted videos (#651). As a bonus, the video #51 is also twice in this list.',
        'url': 'https://www.youtube.com/playlist?list=PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
        'info_dict': {
            'title': '29C3: Not my department',
            'id': 'PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
            'description': 'md5:a14dc1a8ef8307a9807fe136a0660268',
            'tags': [],
            'view_count': int,
            'modified_date': '20150605',
            'channel_id': 'UCEPzS1rYsrkqzSLNp76nrcg',
            'channel_url': 'https://www.youtube.com/channel/UCEPzS1rYsrkqzSLNp76nrcg',
            'channel': 'Christiaan008',
            'availability': 'public',
            'uploader_id': '@ChRiStIaAn008',
            'uploader': 'Christiaan008',
            'uploader_url': 'https://www.youtube.com/@ChRiStIaAn008',
        },
        'playlist_count': 96,
    }, {
        'note': 'Large playlist',
        'url': 'https://www.youtube.com/playlist?list=UUBABnxM4Ar9ten8Mdjj1j0Q',
        'info_dict': {
            'title': 'Uploads from Cauchemar',
            'id': 'UUBABnxM4Ar9ten8Mdjj1j0Q',
            'channel_url': 'https://www.youtube.com/channel/UCBABnxM4Ar9ten8Mdjj1j0Q',
            'tags': [],
            'modified_date': r're:\d{8}',
            'channel': 'Cauchemar',
            'view_count': int,
            'description': '',
            'channel_id': 'UCBABnxM4Ar9ten8Mdjj1j0Q',
            'availability': 'public',
            'uploader_id': '@Cauchemar89',
            'uploader': 'Cauchemar',
            'uploader_url': 'https://www.youtube.com/@Cauchemar89',
        },
        'playlist_mincount': 1123,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'even larger playlist, 8832 videos',
        'url': 'http://www.youtube.com/user/NASAgovVideo/videos',
        'only_matching': True,
    }, {
        'note': 'Buggy playlist: the webpage has a "Load more" button but it doesn\'t have more videos',
        'url': 'https://www.youtube.com/playlist?list=UUXw-G3eDE9trcvY2sBMM_aA',
        'info_dict': {
            'title': 'Uploads from Interstellar Movie',
            'id': 'UUXw-G3eDE9trcvY2sBMM_aA',
            'tags': [],
            'view_count': int,
            'channel_id': 'UCXw-G3eDE9trcvY2sBMM_aA',
            'channel_url': 'https://www.youtube.com/channel/UCXw-G3eDE9trcvY2sBMM_aA',
            'channel': 'Interstellar Movie',
            'description': '',
            'modified_date': r're:\d{8}',
            'availability': 'public',
            'uploader_id': '@InterstellarMovie',
            'uploader': 'Interstellar Movie',
            'uploader_url': 'https://www.youtube.com/@InterstellarMovie',
        },
        'playlist_mincount': 21,
    }, {
        'note': 'Playlist with "show unavailable videos" button',
        'url': 'https://www.youtube.com/playlist?list=UUTYLiWFZy8xtPwxFwX9rV7Q',
        'info_dict': {
            'title': 'Uploads from Phim Siêu Nhân Nhật Bản',
            'id': 'UUTYLiWFZy8xtPwxFwX9rV7Q',
            'view_count': int,
            'channel': 'Phim Siêu Nhân Nhật Bản',
            'tags': [],
            'description': '',
            'channel_url': 'https://www.youtube.com/channel/UCTYLiWFZy8xtPwxFwX9rV7Q',
            'channel_id': 'UCTYLiWFZy8xtPwxFwX9rV7Q',
            'modified_date': r're:\d{8}',
            'availability': 'public',
            'uploader_url': 'https://www.youtube.com/@phimsieunhannhatban',
            'uploader_id': '@phimsieunhannhatban',
            'uploader': 'Phim Siêu Nhân Nhật Bản',
        },
        'playlist_mincount': 200,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'Playlist with unavailable videos in page 7',
        'url': 'https://www.youtube.com/playlist?list=UU8l9frL61Yl5KFOl87nIm2w',
        'info_dict': {
            'title': 'Uploads from BlankTV',
            'id': 'UU8l9frL61Yl5KFOl87nIm2w',
            'channel': 'BlankTV',
            'channel_url': 'https://www.youtube.com/channel/UC8l9frL61Yl5KFOl87nIm2w',
            'channel_id': 'UC8l9frL61Yl5KFOl87nIm2w',
            'view_count': int,
            'tags': [],
            'modified_date': r're:\d{8}',
            'description': '',
            'availability': 'public',
            'uploader_id': '@blanktv',
            'uploader': 'BlankTV',
            'uploader_url': 'https://www.youtube.com/@blanktv',
        },
        'playlist_mincount': 1000,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'https://github.com/ytdl-org/youtube-dl/issues/21844',
        'url': 'https://www.youtube.com/playlist?list=PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
        'info_dict': {
            'title': 'Data Analysis with Dr Mike Pound',
            'id': 'PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
            'description': 'md5:7f567c574d13d3f8c0954d9ffee4e487',
            'tags': [],
            'view_count': int,
            'channel_id': 'UC9-y-6csu5WGm29I7JiwpnA',
            'channel_url': 'https://www.youtube.com/channel/UC9-y-6csu5WGm29I7JiwpnA',
            'channel': 'Computerphile',
            'availability': 'public',
            'modified_date': '20190712',
            'uploader_id': '@Computerphile',
            'uploader': 'Computerphile',
            'uploader_url': 'https://www.youtube.com/@Computerphile',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://invidio.us/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
        'only_matching': True,
    }, {
        'note': 'Playlist URL that does not actually serve a playlist',
        'url': 'https://www.youtube.com/watch?v=FqZTN594JQw&list=PLMYEtVRpaqY00V9W81Cwmzp6N6vZqfUKD4',
        'info_dict': {
            'id': 'FqZTN594JQw',
            'ext': 'webm',
            'title': "Smiley's People 01 detective, Adventure Series, Action",
            'upload_date': '20150526',
            'license': 'Standard YouTube License',
            'description': 'md5:507cdcb5a49ac0da37a920ece610be80',
            'categories': ['People & Blogs'],
            'tags': list,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This video is not available.',
        'add_ie': [YoutubeIE.ie_key()],
    }, {
        'url': 'https://www.youtubekids.com/watch?v=Agk7R8I8o5U&list=PUZ6jURNr1WQZCNHF0ao-c0g',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?v=MuAGGZNfUkU&list=RDMM',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/channel/UCoMdktPbSTixAyNGwb-UYkQ/live',
        'info_dict': {
            'id': 'hGkQjiJLjWQ',  # This will keep changing
            'ext': 'mp4',
            'title': str,
            'upload_date': r're:\d{8}',
            'description': str,
            'categories': ['News & Politics'],
            'tags': list,
            'like_count': int,
            'release_timestamp': int,
            'channel': 'Sky News',
            'channel_id': 'UCoMdktPbSTixAyNGwb-UYkQ',
            'age_limit': 0,
            'view_count': int,
            'thumbnail': r're:https?://i\.ytimg\.com/vi/[^/]+/maxresdefault(?:_live)?\.jpg',
            'playable_in_embed': True,
            'release_date': r're:\d+',
            'availability': 'public',
            'live_status': 'is_live',
            'channel_url': 'https://www.youtube.com/channel/UCoMdktPbSTixAyNGwb-UYkQ',
            'channel_follower_count': int,
            'concurrent_view_count': int,
            'uploader_url': 'https://www.youtube.com/@SkyNews',
            'uploader_id': '@SkyNews',
            'uploader': 'Sky News',
            'channel_is_verified': True,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Ignoring subtitle tracks found in '],
    }, {
        'url': 'https://www.youtube.com/user/TheYoungTurks/live',
        'info_dict': {
            'id': 'a48o2S1cPoo',
            'ext': 'mp4',
            'title': 'The Young Turks - Live Main Show',
            'upload_date': '20150715',
            'license': 'Standard YouTube License',
            'description': 'md5:438179573adcdff3c97ebb1ee632b891',
            'categories': ['News & Politics'],
            'tags': ['Cenk Uygur (TV Program Creator)', 'The Young Turks (Award-Winning Work)', 'Talk Show (TV Genre)'],
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/channel/UC1yBKRuGpC1tSM73A0ZjYjQ/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/CommanderVideoHq/live',
        'only_matching': True,
    }, {
        'note': 'A channel that is not live. Should raise error',
        'url': 'https://www.youtube.com/user/numberphile/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/trending',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/library',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/history',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/subscriptions',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/watch_later',
        'only_matching': True,
    }, {
        'note': 'Recommended - redirects to home page.',
        'url': 'https://www.youtube.com/feed/recommended',
        'only_matching': True,
    }, {
        'note': 'inline playlist with not always working continuations',
        'url': 'https://www.youtube.com/watch?v=UC6u0Tct-Fo&list=PL36D642111D65BE7C',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/course',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/zsecurity',
        'only_matching': True,
    }, {
        'url': 'http://www.youtube.com/NASAgovVideo/videos',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/TheYoungTurks/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/hashtag/cctv9',
        'info_dict': {
            'id': 'cctv9',
            'title': 'cctv9 - All',
            'tags': [],
        },
        'playlist_mincount': 300,  # not consistent but should be over 300
    }, {
        'url': 'https://www.youtube.com/watch?list=PLW4dVinRY435CBE_JD3t-0SRXKfnZHS1P&feature=youtu.be&v=M9cJMXmQ_ZU',
        'only_matching': True,
    }, {
        'note': 'Requires Premium: should request additional YTM-info webpage (and have format 141) for videos in playlist',
        'url': 'https://music.youtube.com/playlist?list=PLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
        'only_matching': True,
    }, {
        'note': '/browse/ should redirect to /channel/',
        'url': 'https://music.youtube.com/browse/UC1a8OFewdjuLq6KlF8M_8Ng',
        'only_matching': True,
    }, {
        'note': 'VLPL, should redirect to playlist?list=PL...',
        'url': 'https://music.youtube.com/browse/VLPLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
        'info_dict': {
            'id': 'PLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
            'description': 'Providing you with copyright free / safe music for gaming, live streaming, studying and more!',
            'title': 'NCS : All Releases 💿',
            'channel_url': 'https://www.youtube.com/channel/UC_aEa8K-EOJ3D6gOs7HcyNg',
            'modified_date': r're:\d{8}',
            'view_count': int,
            'channel_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'tags': [],
            'channel': 'NoCopyrightSounds',
            'availability': 'public',
            'uploader_url': 'https://www.youtube.com/@NoCopyrightSounds',
            'uploader': 'NoCopyrightSounds',
            'uploader_id': '@NoCopyrightSounds',
        },
        'playlist_mincount': 166,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden', 'YouTube Music is not directly supported'],
    }, {
        # TODO: fix 'unviewable' issue with this playlist when reloading with unavailable videos
        'note': 'Topic, should redirect to playlist?list=UU...',
        'url': 'https://music.youtube.com/browse/UC9ALqqC4aIeG5iDs7i90Bfw',
        'info_dict': {
            'id': 'UU9ALqqC4aIeG5iDs7i90Bfw',
            'title': 'Uploads from Royalty Free Music - Topic',
            'tags': [],
            'channel_id': 'UC9ALqqC4aIeG5iDs7i90Bfw',
            'channel': 'Royalty Free Music - Topic',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC9ALqqC4aIeG5iDs7i90Bfw',
            'modified_date': r're:\d{8}',
            'description': '',
            'availability': 'public',
            'uploader': 'Royalty Free Music - Topic',
        },
        'playlist_mincount': 101,
        'expected_warnings': ['YouTube Music is not directly supported', r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        # Destination channel with only a hidden self tab (tab id is UCtFRv9O2AHqOZjjynzrv-xg)
        # Treat as a general feed
        'url': 'https://www.youtube.com/channel/UCtFRv9O2AHqOZjjynzrv-xg',
        'info_dict': {
            'id': 'UCtFRv9O2AHqOZjjynzrv-xg',
            'title': 'UCtFRv9O2AHqOZjjynzrv-xg',
            'tags': [],
        },
        'playlist_mincount': 9,
    }, {
        'note': 'Youtube music Album',
        'url': 'https://music.youtube.com/browse/MPREb_gTAcphH99wE',
        'info_dict': {
            'id': 'OLAK5uy_l1m0thk3g31NmIIz_vMIbWtyv7eZixlH0',
            'title': 'Album - Royalty Free Music Library V2 (50 Songs)',
            'tags': [],
            'view_count': int,
            'description': '',
            'availability': 'unlisted',
            'modified_date': r're:\d{8}',
        },
        'playlist_count': 50,
        'expected_warnings': ['YouTube Music is not directly supported'],
    }, {
        'note': 'unlisted single video playlist',
        'url': 'https://www.youtube.com/playlist?list=PLwL24UFy54GrB3s2KMMfjZscDi1x5Dajf',
        'info_dict': {
            'id': 'PLwL24UFy54GrB3s2KMMfjZscDi1x5Dajf',
            'title': 'yt-dlp unlisted playlist test',
            'availability': 'unlisted',
            'tags': [],
            'modified_date': '20220418',
            'channel': 'colethedj',
            'view_count': int,
            'description': '',
            'channel_id': 'UC9zHu_mHU96r19o-wV5Qs1Q',
            'channel_url': 'https://www.youtube.com/channel/UC9zHu_mHU96r19o-wV5Qs1Q',
            'uploader_url': 'https://www.youtube.com/@colethedj1894',
            'uploader_id': '@colethedj1894',
            'uploader': 'colethedj',
        },
        'playlist': [{
            'info_dict': {
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'id': 'BaW_jenozKc',
                '_type': 'url',
                'ie_key': 'Youtube',
                'duration': 10,
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': 'https://www.youtube.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'view_count': int,
                'url': 'https://www.youtube.com/watch?v=BaW_jenozKc',
                'channel': 'Philipp Hagemeister',
                'uploader_id': '@PhilippHagemeister',
                'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
                'uploader': 'Philipp Hagemeister',
            },
        }],
        'playlist_count': 1,
        'params': {'extract_flat': True},
    }, {
        'note': 'API Fallback: Recommended - redirects to home page. Requires visitorData',
        'url': 'https://www.youtube.com/feed/recommended',
        'info_dict': {
            'id': 'recommended',
            'title': 'recommended',
            'tags': [],
        },
        'playlist_mincount': 50,
        'params': {
            'skip_download': True,
            'extractor_args': {'youtubetab': {'skip': ['webpage']}},
        },
    }, {
        'note': 'API Fallback: /videos tab, sorted by oldest first',
        'url': 'https://www.youtube.com/user/theCodyReeder/videos?view=0&sort=da&flow=grid',
        'info_dict': {
            'id': 'UCu6mSoMNzHQiBIOCkHUa2Aw',
            'title': 'Cody\'sLab - Videos',
            'description': 'md5:d083b7c2f0c67ee7a6c74c3e9b4243fa',
            'channel': 'Cody\'sLab',
            'channel_id': 'UCu6mSoMNzHQiBIOCkHUa2Aw',
            'tags': [],
            'channel_url': 'https://www.youtube.com/channel/UCu6mSoMNzHQiBIOCkHUa2Aw',
            'channel_follower_count': int,
        },
        'playlist_mincount': 650,
        'params': {
            'skip_download': True,
            'extractor_args': {'youtubetab': {'skip': ['webpage']}},
        },
        'skip': 'Query for sorting no longer works',
    }, {
        'note': 'API Fallback: Topic, should redirect to playlist?list=UU...',
        'url': 'https://music.youtube.com/browse/UC9ALqqC4aIeG5iDs7i90Bfw',
        'info_dict': {
            'id': 'UU9ALqqC4aIeG5iDs7i90Bfw',
            'title': 'Uploads from Royalty Free Music - Topic',
            'modified_date': r're:\d{8}',
            'channel_id': 'UC9ALqqC4aIeG5iDs7i90Bfw',
            'description': '',
            'channel_url': 'https://www.youtube.com/channel/UC9ALqqC4aIeG5iDs7i90Bfw',
            'tags': [],
            'channel': 'Royalty Free Music - Topic',
            'view_count': int,
            'availability': 'public',
            'uploader': 'Royalty Free Music - Topic',
        },
        'playlist_mincount': 101,
        'params': {
            'skip_download': True,
            'extractor_args': {'youtubetab': {'skip': ['webpage']}},
        },
        'expected_warnings': ['YouTube Music is not directly supported', r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'non-standard redirect to regional channel',
        'url': 'https://www.youtube.com/channel/UCwVVpHQ2Cs9iGJfpdFngePQ',
        'only_matching': True,
    }, {
        'note': 'collaborative playlist (uploader name in the form "by <uploader> and x other(s)")',
        'url': 'https://www.youtube.com/playlist?list=PLx-_-Kk4c89oOHEDQAojOXzEzemXxoqx6',
        'info_dict': {
            'id': 'PLx-_-Kk4c89oOHEDQAojOXzEzemXxoqx6',
            'modified_date': '20220407',
            'channel_url': 'https://www.youtube.com/channel/UCKcqXmCcyqnhgpA5P0oHH_Q',
            'tags': [],
            'availability': 'unlisted',
            'channel_id': 'UCKcqXmCcyqnhgpA5P0oHH_Q',
            'channel': 'pukkandan',
            'description': 'Test for collaborative playlist',
            'title': 'yt-dlp test - collaborative playlist',
            'view_count': int,
            'uploader_url': 'https://www.youtube.com/@pukkandan',
            'uploader_id': '@pukkandan',
            'uploader': 'pukkandan',
        },
        'playlist_mincount': 2,
    }, {
        'note': 'translated tab name',
        'url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA/playlists',
        'info_dict': {
            'id': 'UCiu-3thuViMebBjw_5nWYrA',
            'tags': [],
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'description': 'test description',
            'title': 'cole-dlp-test-acc - 再生リスト',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel': 'cole-dlp-test-acc',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist_mincount': 1,
        'params': {'extractor_args': {'youtube': {'lang': ['ja']}}},
        'expected_warnings': ['Preferring "ja"'],
    }, {
        # XXX: this should really check flat playlist entries, but the test suite doesn't support that
        'note': 'preferred lang set with playlist with translated video titles',
        'url': 'https://www.youtube.com/playlist?list=PLt5yu3-wZAlQAaPZ5Z-rJoTdbT-45Q7c0',
        'info_dict': {
            'id': 'PLt5yu3-wZAlQAaPZ5Z-rJoTdbT-45Q7c0',
            'tags': [],
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'channel': 'cole-dlp-test-acc',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'description': 'test',
            'title': 'dlp test playlist',
            'availability': 'public',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist_mincount': 1,
        'params': {'extractor_args': {'youtube': {'lang': ['ja']}}},
        'expected_warnings': ['Preferring "ja"'],
    }, {
        # shorts audio pivot for 2GtVksBMYFM.
        'url': 'https://www.youtube.com/feed/sfv_audio_pivot?bp=8gUrCikSJwoLMkd0VmtzQk1ZRk0SCzJHdFZrc0JNWUZNGgsyR3RWa3NCTVlGTQ==',
        'info_dict': {
            'id': 'sfv_audio_pivot',
            'title': 'sfv_audio_pivot',
            'tags': [],
        },
        'playlist_mincount': 50,

    }, {
        # Channel with a real live tab (not to be mistaken with streams tab)
        # Do not treat like it should redirect to live stream
        'url': 'https://www.youtube.com/channel/UCEH7P7kyJIkS_gJf93VYbmg/live',
        'info_dict': {
            'id': 'UCEH7P7kyJIkS_gJf93VYbmg',
            'title': 'UCEH7P7kyJIkS_gJf93VYbmg - Live',
            'tags': [],
        },
        'playlist_mincount': 20,
    }, {
        # Tab name is not the same as tab id
        'url': 'https://www.youtube.com/channel/UCQvWX73GQygcwXOTSf_VDVg/letsplay',
        'info_dict': {
            'id': 'UCQvWX73GQygcwXOTSf_VDVg',
            'title': 'UCQvWX73GQygcwXOTSf_VDVg - Let\'s play',
            'tags': [],
        },
        'playlist_mincount': 8,
    }, {
        # Home tab id is literally home. Not to get mistaken with featured
        'url': 'https://www.youtube.com/channel/UCQvWX73GQygcwXOTSf_VDVg/home',
        'info_dict': {
            'id': 'UCQvWX73GQygcwXOTSf_VDVg',
            'title': 'UCQvWX73GQygcwXOTSf_VDVg - Home',
            'tags': [],
        },
        'playlist_mincount': 8,
    }, {
        # Should get three playlists for videos, shorts and streams tabs
        'url': 'https://www.youtube.com/channel/UCK9V2B22uJYu3N7eR_BT9QA',
        'info_dict': {
            'id': 'UCK9V2B22uJYu3N7eR_BT9QA',
            'title': 'Polka Ch. 尾丸ポルカ',
            'channel_follower_count': int,
            'channel_id': 'UCK9V2B22uJYu3N7eR_BT9QA',
            'channel_url': 'https://www.youtube.com/channel/UCK9V2B22uJYu3N7eR_BT9QA',
            'description': 'md5:49809d8bf9da539bc48ed5d1f83c33f2',
            'channel': 'Polka Ch. 尾丸ポルカ',
            'tags': 'count:35',
            'uploader_url': 'https://www.youtube.com/@OmaruPolka',
            'uploader': 'Polka Ch. 尾丸ポルカ',
            'uploader_id': '@OmaruPolka',
            'channel_is_verified': True,
        },
        'playlist_count': 3,
    }, {
        # Shorts tab with channel with handle
        # TODO: fix channel description
        'url': 'https://www.youtube.com/@NotJustBikes/shorts',
        'info_dict': {
            'id': 'UC0intLFzLaudFG-xAvUEO-A',
            'title': 'Not Just Bikes - Shorts',
            'tags': 'count:10',
            'channel_url': 'https://www.youtube.com/channel/UC0intLFzLaudFG-xAvUEO-A',
            'description': 'md5:5e82545b3a041345927a92d0585df247',
            'channel_follower_count': int,
            'channel_id': 'UC0intLFzLaudFG-xAvUEO-A',
            'channel': 'Not Just Bikes',
            'uploader_url': 'https://www.youtube.com/@NotJustBikes',
            'uploader': 'Not Just Bikes',
            'uploader_id': '@NotJustBikes',
            'channel_is_verified': True,
        },
        'playlist_mincount': 10,
    }, {
        # Streams tab
        'url': 'https://www.youtube.com/channel/UC3eYAvjCVwNHgkaGbXX3sig/streams',
        'info_dict': {
            'id': 'UC3eYAvjCVwNHgkaGbXX3sig',
            'title': '中村悠一 - Live',
            'tags': 'count:7',
            'channel_id': 'UC3eYAvjCVwNHgkaGbXX3sig',
            'channel_url': 'https://www.youtube.com/channel/UC3eYAvjCVwNHgkaGbXX3sig',
            'channel': '中村悠一',
            'channel_follower_count': int,
            'description': 'md5:e744f6c93dafa7a03c0c6deecb157300',
            'uploader_url': 'https://www.youtube.com/@Yuichi-Nakamura',
            'uploader_id': '@Yuichi-Nakamura',
            'uploader': '中村悠一',
        },
        'playlist_mincount': 60,
    }, {
        # Channel with no uploads and hence no videos, streams, shorts tabs or uploads playlist. This should fail.
        # See test_youtube_lists
        'url': 'https://www.youtube.com/channel/UC2yXPzFejc422buOIzn_0CA',
        'only_matching': True,
    }, {
        # No uploads and no UCID given. Should fail with no uploads error
        # See test_youtube_lists
        'url': 'https://www.youtube.com/news',
        'only_matching': True,
    }, {
        # No videos tab but has a shorts tab
        'url': 'https://www.youtube.com/c/TKFShorts',
        'info_dict': {
            'id': 'UCgJ5_1F6yJhYLnyMszUdmUg',
            'title': 'Shorts Break - Shorts',
            'tags': 'count:48',
            'channel_id': 'UCgJ5_1F6yJhYLnyMszUdmUg',
            'channel': 'Shorts Break',
            'description': 'md5:6de33c5e7ba686e5f3efd4e19c7ef499',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCgJ5_1F6yJhYLnyMszUdmUg',
            'uploader_url': 'https://www.youtube.com/@ShortsBreak_Official',
            'uploader': 'Shorts Break',
            'uploader_id': '@ShortsBreak_Official',
        },
        'playlist_mincount': 30,
    }, {
        # Trending Now Tab. tab id is empty
        'url': 'https://www.youtube.com/feed/trending',
        'info_dict': {
            'id': 'trending',
            'title': 'trending - Now',
            'tags': [],
        },
        'playlist_mincount': 30,
    }, {
        # Trending Gaming Tab. tab id is empty
        'url': 'https://www.youtube.com/feed/trending?bp=4gIcGhpnYW1pbmdfY29ycHVzX21vc3RfcG9wdWxhcg%3D%3D',
        'info_dict': {
            'id': 'trending',
            'title': 'trending - Gaming',
            'tags': [],
        },
        'playlist_mincount': 30,
    }, {
        # Shorts url result in shorts tab
        # TODO: Fix channel id extraction
        'url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA/shorts',
        'info_dict': {
            'id': 'UCiu-3thuViMebBjw_5nWYrA',
            'title': 'cole-dlp-test-acc - Shorts',
            'channel': 'cole-dlp-test-acc',
            'description': 'test description',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist': [{
            'info_dict': {
                # Channel data is not currently available for short renderers (as of 2023-03-01)
                '_type': 'url',
                'ie_key': 'Youtube',
                'url': 'https://www.youtube.com/shorts/sSM9J5YH_60',
                'id': 'sSM9J5YH_60',
                'title': 'SHORT short',
                'view_count': int,
                'thumbnails': list,
            },
        }],
        'params': {'extract_flat': True},
    }, {
        # Live video status should be extracted
        'url': 'https://www.youtube.com/channel/UCQvWX73GQygcwXOTSf_VDVg/live',
        'info_dict': {
            'id': 'UCQvWX73GQygcwXOTSf_VDVg',
            'title': 'UCQvWX73GQygcwXOTSf_VDVg - Live',  # TODO: should be Minecraft - Live or Minecraft - Topic - Live
            'tags': [],
        },
        'playlist': [{
            'info_dict': {
                '_type': 'url',
                'ie_key': 'Youtube',
                'url': 'startswith:https://www.youtube.com/watch?v=',
                'id': str,
                'title': str,
                'live_status': 'is_live',
                'channel_id': str,
                'channel_url': str,
                'concurrent_view_count': int,
                'channel': str,
                'uploader': str,
                'uploader_url': str,
                'uploader_id': str,
                'channel_is_verified': bool,  # this will keep changing
            },
        }],
        'params': {'extract_flat': True, 'playlist_items': '1'},
        'playlist_mincount': 1,
    }, {
        # Channel renderer metadata. Contains number of videos on the channel
        'url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA/channels',
        'info_dict': {
            'id': 'UCiu-3thuViMebBjw_5nWYrA',
            'title': 'cole-dlp-test-acc - Channels',
            'channel': 'cole-dlp-test-acc',
            'description': 'test description',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist': [{
            'info_dict': {
                '_type': 'url',
                'ie_key': 'YoutubeTab',
                'url': 'https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'id': 'UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'channel_id': 'UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'title': 'PewDiePie',
                'channel': 'PewDiePie',
                'channel_url': 'https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'thumbnails': list,
                'channel_follower_count': int,
                'playlist_count': int,
                'uploader': 'PewDiePie',
                'uploader_url': 'https://www.youtube.com/@PewDiePie',
                'uploader_id': '@PewDiePie',
                'channel_is_verified': True,
            },
        }],
        'params': {'extract_flat': True},
    }, {
        'url': 'https://www.youtube.com/@3blue1brown/about',
        'info_dict': {
            'id': '@3blue1brown',
            'tags': ['Mathematics'],
            'title': '3Blue1Brown',
            'channel_follower_count': int,
            'channel_id': 'UCYO_jab_esuFRV4b17AJtAw',
            'channel': '3Blue1Brown',
            'channel_url': 'https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw',
            'description': 'md5:4d1da95432004b7ba840ebc895b6b4c9',
            'uploader_url': 'https://www.youtube.com/@3blue1brown',
            'uploader_id': '@3blue1brown',
            'uploader': '3Blue1Brown',
            'channel_is_verified': True,
        },
        'playlist_count': 0,
    }, {
        # Podcasts tab, with rich entry playlistRenderers
        'url': 'https://www.youtube.com/@99percentinvisiblepodcast/podcasts',
        'info_dict': {
            'id': 'UCVMF2HD4ZgC0QHpU9Yq5Xrw',
            'channel_id': 'UCVMF2HD4ZgC0QHpU9Yq5Xrw',
            'uploader_url': 'https://www.youtube.com/@99percentinvisiblepodcast',
            'description': 'md5:3a0ed38f1ad42a68ef0428c04a15695c',
            'title': '99 Percent Invisible - Podcasts',
            'uploader': '99 Percent Invisible',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCVMF2HD4ZgC0QHpU9Yq5Xrw',
            'tags': [],
            'channel': '99 Percent Invisible',
            'uploader_id': '@99percentinvisiblepodcast',
        },
        'playlist_count': 0,
    }, {
        # Releases tab, with rich entry playlistRenderers (same as Podcasts tab)
        'url': 'https://www.youtube.com/@AHimitsu/releases',
        'info_dict': {
            'id': 'UCgFwu-j5-xNJml2FtTrrB3A',
            'channel': 'A Himitsu',
            'uploader_url': 'https://www.youtube.com/@AHimitsu',
            'title': 'A Himitsu - Releases',
            'uploader_id': '@AHimitsu',
            'uploader': 'A Himitsu',
            'channel_id': 'UCgFwu-j5-xNJml2FtTrrB3A',
            'tags': 'count:12',
            'description': 'I make music',
            'channel_url': 'https://www.youtube.com/channel/UCgFwu-j5-xNJml2FtTrrB3A',
            'channel_follower_count': int,
            'channel_is_verified': True,
        },
        'playlist_mincount': 10,
    }, {
        # Playlist with only shorts, shown as reel renderers
        # FIXME: future: YouTube currently doesn't give continuation for this,
        # may do in future.
        'url': 'https://www.youtube.com/playlist?list=UUxqPAgubo4coVn9Lx1FuKcg',
        'info_dict': {
            'id': 'UUxqPAgubo4coVn9Lx1FuKcg',
            'channel_url': 'https://www.youtube.com/channel/UCxqPAgubo4coVn9Lx1FuKcg',
            'view_count': int,
            'uploader_id': '@BangyShorts',
            'description': '',
            'uploader_url': 'https://www.youtube.com/@BangyShorts',
            'channel_id': 'UCxqPAgubo4coVn9Lx1FuKcg',
            'channel': 'Bangy Shorts',
            'uploader': 'Bangy Shorts',
            'tags': [],
            'availability': 'public',
            'modified_date': r're:\d{8}',
            'title': 'Uploads from Bangy Shorts',
        },
        'playlist_mincount': 100,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'Tags containing spaces',
        'url': 'https://www.youtube.com/channel/UC7_YxT-KID8kRbqZo7MyscQ',
        'playlist_count': 3,
        'info_dict': {
            'id': 'UC7_YxT-KID8kRbqZo7MyscQ',
            'channel': 'Markiplier',
            'channel_id': 'UC7_YxT-KID8kRbqZo7MyscQ',
            'title': 'Markiplier',
            'channel_follower_count': int,
            'description': 'md5:0c010910558658824402809750dc5d97',
            'uploader_id': '@markiplier',
            'uploader_url': 'https://www.youtube.com/@markiplier',
            'uploader': 'Markiplier',
            'channel_url': 'https://www.youtube.com/channel/UC7_YxT-KID8kRbqZo7MyscQ',
            'channel_is_verified': True,
            'tags': ['markiplier', 'comedy', 'gaming', 'funny videos', 'funny moments',
                     'sketch comedy', 'laughing', 'lets play', 'challenge videos', 'hilarious',
                     'challenges', 'sketches', 'scary games', 'funny games', 'rage games',
                     'mark fischbach'],
        },
    }]

    @classmethod
    def suitable(cls, url):
        return False if YoutubeIE.suitable(url) else super().suitable(url)

    _URL_RE = re.compile(rf'(?P<pre>{_VALID_URL})(?(not_channel)|(?P<tab>/[^?#/]+))?(?P<post>.*)$')

    def _get_url_mobj(self, url):
        mobj = self._URL_RE.match(url).groupdict()
        mobj.update((k, '') for k, v in mobj.items() if v is None)
        return mobj

    def _extract_tab_id_and_name(self, tab, base_url='https://www.youtube.com'):
        tab_name = (tab.get('title') or '').lower()
        tab_url = urljoin(base_url, traverse_obj(
            tab, ('endpoint', 'commandMetadata', 'webCommandMetadata', 'url')))

        tab_id = (tab_url and self._get_url_mobj(tab_url)['tab'][1:]
                  or traverse_obj(tab, 'tabIdentifier', expected_type=str))
        if tab_id:
            return {
                'TAB_ID_SPONSORSHIPS': 'membership',
            }.get(tab_id, tab_id), tab_name

        # Fallback to tab name if we cannot get the tab id.
        # XXX: should we strip non-ascii letters? e.g. in case of 'let's play' tab example on special gaming channel
        # Note that in the case of translated tab name this may result in an empty string, which we don't want.
        if tab_name:
            self.write_debug(f'Falling back to selected tab name: {tab_name}')
        return {
            'home': 'featured',
            'live': 'streams',
        }.get(tab_name, tab_name), tab_name

    def _has_tab(self, tabs, tab_id):
        return any(self._extract_tab_id_and_name(tab)[0] == tab_id for tab in tabs)

    def _empty_playlist(self, item_id, data):
        return self.playlist_result([], item_id, **self._extract_metadata_from_tabs(item_id, data))

    @YoutubeTabBaseInfoExtractor.passthrough_smuggled_data
    def _real_extract(self, url, smuggled_data):
        item_id = self._match_id(url)
        url = urllib.parse.urlunparse(
            urllib.parse.urlparse(url)._replace(netloc='www.youtube.com'))
        compat_opts = self.get_param('compat_opts', [])

        mobj = self._get_url_mobj(url)
        pre, tab, post, is_channel = mobj['pre'], mobj['tab'], mobj['post'], not mobj['not_channel']
        if is_channel and smuggled_data.get('is_music_url'):
            if item_id[:2] == 'VL':  # Youtube music VL channels have an equivalent playlist
                return self.url_result(
                    f'https://music.youtube.com/playlist?list={item_id[2:]}', YoutubeTabIE, item_id[2:])
            elif item_id[:2] == 'MP':  # Resolve albums (/[channel/browse]/MP...) to their equivalent playlist
                mdata = self._extract_tab_endpoint(
                    f'https://music.youtube.com/channel/{item_id}', item_id, default_client='web_music')
                murl = traverse_obj(mdata, ('microformat', 'microformatDataRenderer', 'urlCanonical'),
                                    get_all=False, expected_type=str)
                if not murl:
                    raise ExtractorError('Failed to resolve album to playlist')
                return self.url_result(murl, YoutubeTabIE)
            elif mobj['channel_type'] == 'browse':  # Youtube music /browse/ should be changed to /channel/
                return self.url_result(
                    f'https://music.youtube.com/channel/{item_id}{tab}{post}', YoutubeTabIE, item_id)

        original_tab_id, display_id = tab[1:], f'{item_id}{tab}'
        if is_channel and not tab and 'no-youtube-channel-redirect' not in compat_opts:
            url = f'{pre}/videos{post}'
        if smuggled_data.get('is_music_url'):
            self.report_warning(f'YouTube Music is not directly supported. Redirecting to {url}')

        # Handle both video/playlist URLs
        qs = parse_qs(url)
        video_id, playlist_id = (traverse_obj(qs, (key, 0)) for key in ('v', 'list'))
        if not video_id and mobj['not_channel'].startswith('watch'):
            if not playlist_id:
                # If there is neither video or playlist ids, youtube redirects to home page, which is undesirable
                raise ExtractorError('A video URL was given without video ID', expected=True)
            # Common mistake: https://www.youtube.com/watch?list=playlist_id
            self.report_warning(f'A video URL was given without video ID. Trying to download playlist {playlist_id}')
            return self.url_result(
                f'https://www.youtube.com/playlist?list={playlist_id}', YoutubeTabIE, playlist_id)

        if not self._yes_playlist(playlist_id, video_id):
            return self.url_result(
                f'https://www.youtube.com/watch?v={video_id}', YoutubeIE, video_id)

        data, ytcfg = self._extract_data(url, display_id)

        # YouTube may provide a non-standard redirect to the regional channel
        # See: https://github.com/yt-dlp/yt-dlp/issues/2694
        # https://support.google.com/youtube/answer/2976814#zippy=,conditional-redirects
        redirect_url = traverse_obj(
            data, ('onResponseReceivedActions', ..., 'navigateAction', 'endpoint', 'commandMetadata', 'webCommandMetadata', 'url'), get_all=False)
        if redirect_url and 'no-youtube-channel-redirect' not in compat_opts:
            redirect_url = ''.join((urljoin('https://www.youtube.com', redirect_url), tab, post))
            self.to_screen(f'This playlist is likely not available in your region. Following conditional redirect to {redirect_url}')
            return self.url_result(redirect_url, YoutubeTabIE)

        tabs, extra_tabs = self._extract_tab_renderers(data), []
        if is_channel and tabs and 'no-youtube-channel-redirect' not in compat_opts:
            selected_tab = self._extract_selected_tab(tabs)
            selected_tab_id, selected_tab_name = self._extract_tab_id_and_name(selected_tab, url)  # NB: Name may be translated
            self.write_debug(f'Selected tab: {selected_tab_id!r} ({selected_tab_name}), Requested tab: {original_tab_id!r}')

            # /about is no longer a tab
            if original_tab_id == 'about':
                return self._empty_playlist(item_id, data)

            if not original_tab_id and selected_tab_name:
                self.to_screen('Downloading all uploads of the channel. '
                               'To download only the videos in a specific tab, pass the tab\'s URL')
                if self._has_tab(tabs, 'streams'):
                    extra_tabs.append(''.join((pre, '/streams', post)))
                if self._has_tab(tabs, 'shorts'):
                    extra_tabs.append(''.join((pre, '/shorts', post)))
                # XXX: Members-only tab should also be extracted

                if not extra_tabs and selected_tab_id != 'videos':
                    # Channel does not have streams, shorts or videos tabs
                    if item_id[:2] != 'UC':
                        return self._empty_playlist(item_id, data)

                    # Topic channels don't have /videos. Use the equivalent playlist instead
                    pl_id = f'UU{item_id[2:]}'
                    pl_url = f'https://www.youtube.com/playlist?list={pl_id}'
                    try:
                        data, ytcfg = self._extract_data(pl_url, pl_id, ytcfg=ytcfg, fatal=True, webpage_fatal=True)
                    except ExtractorError:
                        return self._empty_playlist(item_id, data)
                    else:
                        item_id, url = pl_id, pl_url
                        self.to_screen(
                            f'The channel does not have a videos, shorts, or live tab. Redirecting to playlist {pl_id} instead')

                elif extra_tabs and selected_tab_id != 'videos':
                    # When there are shorts/live tabs but not videos tab
                    url, data = f'{pre}{post}', None

            elif (original_tab_id or 'videos') != selected_tab_id:
                if original_tab_id == 'live':
                    # Live tab should have redirected to the video
                    # Except in the case the channel has an actual live tab
                    # Example: https://www.youtube.com/channel/UCEH7P7kyJIkS_gJf93VYbmg/live
                    raise UserNotLive(video_id=item_id)
                elif selected_tab_name:
                    raise ExtractorError(f'This channel does not have a {original_tab_id} tab', expected=True)

                # For channels such as https://www.youtube.com/channel/UCtFRv9O2AHqOZjjynzrv-xg
                url = f'{pre}{post}'

        # YouTube sometimes provides a button to reload playlist with unavailable videos.
        if 'no-youtube-unavailable-videos' not in compat_opts:
            data = self._reload_with_unavailable_videos(display_id, data, ytcfg) or data
        self._extract_and_report_alerts(data, only_once=True)

        tabs, entries = self._extract_tab_renderers(data), []
        if tabs:
            entries = [self._extract_from_tabs(item_id, ytcfg, data, tabs)]
            entries[0].update({
                'extractor_key': YoutubeTabIE.ie_key(),
                'extractor': YoutubeTabIE.IE_NAME,
                'webpage_url': url,
            })
        if self.get_param('playlist_items') == '0':
            entries.extend(self.url_result(u, YoutubeTabIE) for u in extra_tabs)
        else:  # Users expect to get all `video_id`s even with `--flat-playlist`. So don't return `url_result`
            entries.extend(map(self._real_extract, extra_tabs))

        if len(entries) == 1:
            return entries[0]
        elif entries:
            metadata = self._extract_metadata_from_tabs(item_id, data)
            uploads_url = 'the Uploads (UU) playlist URL'
            if try_get(metadata, lambda x: x['channel_id'].startswith('UC')):
                uploads_url = f'https://www.youtube.com/playlist?list=UU{metadata["channel_id"][2:]}'
            self.to_screen(
                'Downloading as multiple playlists, separated by tabs. '
                f'To download as a single playlist instead, pass {uploads_url}')
            return self.playlist_result(entries, item_id, **metadata)

        # Inline playlist
        playlist = traverse_obj(
            data, ('contents', 'twoColumnWatchNextResults', 'playlist', 'playlist'), expected_type=dict)
        if playlist:
            return self._extract_from_playlist(item_id, url, data, playlist, ytcfg)

        video_id = traverse_obj(
            data, ('currentVideoEndpoint', 'watchEndpoint', 'videoId'), expected_type=str) or video_id
        if video_id:
            if tab != '/live':  # live tab is expected to redirect to video
                self.report_warning(f'Unable to recognize playlist. Downloading just video {video_id}')
            return self.url_result(f'https://www.youtube.com/watch?v={video_id}', YoutubeIE, video_id)

        raise ExtractorError('Unable to recognize tab page')


class YoutubePlaylistIE(InfoExtractor):
    IE_DESC = 'YouTube playlists'
    _VALID_URL = r'''(?x)(?:
                        (?:https?://)?
                        (?:\w+\.)?
                        (?:
                            (?:
                                youtube(?:kids)?\.com|
                                {invidious}
                            )
                            /.*?\?.*?\blist=
                        )?
                        (?P<id>{playlist_id})
                     )'''.format(
        playlist_id=YoutubeBaseInfoExtractor._PLAYLIST_ID_RE,
        invidious='|'.join(YoutubeBaseInfoExtractor._INVIDIOUS_SITES),
    )
    IE_NAME = 'youtube:playlist'
    _TESTS = [{
        'note': 'issue #673',
        'url': 'PLBB231211A4F62143',
        'info_dict': {
            'title': '[OLD]Team Fortress 2 (Class-based LP)',
            'id': 'PLBB231211A4F62143',
            'uploader': 'Wickman',
            'uploader_id': '@WickmanVT',
            'description': 'md5:8fa6f52abb47a9552002fa3ddfc57fc2',
            'view_count': int,
            'uploader_url': 'https://www.youtube.com/@WickmanVT',
            'modified_date': r're:\d{8}',
            'channel_id': 'UCKSpbfbl5kRQpTdL7kMc-1Q',
            'channel': 'Wickman',
            'tags': [],
            'channel_url': 'https://www.youtube.com/channel/UCKSpbfbl5kRQpTdL7kMc-1Q',
            'availability': 'public',
        },
        'playlist_mincount': 29,
    }, {
        'url': 'PLtPgu7CB4gbY9oDN3drwC3cMbJggS7dKl',
        'info_dict': {
            'title': 'YDL_safe_search',
            'id': 'PLtPgu7CB4gbY9oDN3drwC3cMbJggS7dKl',
        },
        'playlist_count': 2,
        'skip': 'This playlist is private',
    }, {
        'note': 'embedded',
        'url': 'https://www.youtube.com/embed/videoseries?list=PL6IaIsEjSbf96XFRuNccS_RuEXwNdsoEu',
        'playlist_count': 4,
        'info_dict': {
            'title': 'JODA15',
            'id': 'PL6IaIsEjSbf96XFRuNccS_RuEXwNdsoEu',
            'uploader': 'milan',
            'uploader_id': '@milan5503',
            'description': '',
            'channel_url': 'https://www.youtube.com/channel/UCEI1-PVPcYXjB73Hfelbmaw',
            'tags': [],
            'modified_date': '20140919',
            'view_count': int,
            'channel': 'milan',
            'channel_id': 'UCEI1-PVPcYXjB73Hfelbmaw',
            'uploader_url': 'https://www.youtube.com/@milan5503',
            'availability': 'public',
        },
        'expected_warnings': [r'[Uu]navailable videos? (is|are|will be) hidden', 'Retrying', 'Giving up'],
    }, {
        'url': 'http://www.youtube.com/embed/_xDOZElKyNU?list=PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
        'playlist_mincount': 455,
        'info_dict': {
            'title': '2018 Chinese New Singles (11/6 updated)',
            'id': 'PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
            'uploader': 'LBK',
            'uploader_id': '@music_king',
            'description': 'md5:da521864744d60a198e3a88af4db0d9d',
            'channel': 'LBK',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC21nz3_MesPLqtDqwdvnoxA',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@music_king',
            'channel_id': 'UC21nz3_MesPLqtDqwdvnoxA',
            'modified_date': r're:\d{8}',
            'availability': 'public',
        },
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'url': 'TLGGrESM50VT6acwMjAyMjAxNw',
        'only_matching': True,
    }, {
        # music album playlist
        'url': 'OLAK5uy_m4xAFdmMC5rX3Ji3g93pQe3hqLZw_9LhM',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        if YoutubeTabIE.suitable(url):
            return False
        from ..utils import parse_qs
        qs = parse_qs(url)
        if qs.get('v', [None])[0]:
            return False
        return super().suitable(url)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        is_music_url = YoutubeBaseInfoExtractor.is_music_url(url)
        url = update_url_query(
            'https://www.youtube.com/playlist',
            parse_qs(url) or {'list': playlist_id})
        if is_music_url:
            url = smuggle_url(url, {'is_music_url': True})
        return self.url_result(url, ie=YoutubeTabIE.ie_key(), video_id=playlist_id)


class YoutubeYtBeIE(InfoExtractor):
    IE_DESC = 'youtu.be'
    _VALID_URL = rf'https?://youtu\.be/(?P<id>[0-9A-Za-z_-]{{11}})/*?.*?\blist=(?P<playlist_id>{YoutubeBaseInfoExtractor._PLAYLIST_ID_RE})'
    _TESTS = [{
        'url': 'https://youtu.be/yeWKywCrFtk?list=PL2qgrgXsNUG5ig9cat4ohreBjYLAPC0J5',
        'info_dict': {
            'id': 'yeWKywCrFtk',
            'ext': 'mp4',
            'title': 'Small Scale Baler and Braiding Rugs',
            'uploader': 'Backus-Page House Museum',
            'uploader_id': '@backuspagemuseum',
            'uploader_url': r're:https?://(?:www\.)?youtube\.com/@backuspagemuseum',
            'upload_date': '20161008',
            'description': 'md5:800c0c78d5eb128500bffd4f0b4f2e8a',
            'categories': ['Nonprofits & Activism'],
            'tags': list,
            'like_count': int,
            'age_limit': 0,
            'playable_in_embed': True,
            'thumbnail': r're:^https?://.*\.webp',
            'channel': 'Backus-Page House Museum',
            'channel_id': 'UCEfMCQ9bs3tjvjy1s451zaw',
            'live_status': 'not_live',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCEfMCQ9bs3tjvjy1s451zaw',
            'availability': 'public',
            'duration': 59,
            'comment_count': int,
            'channel_follower_count': int,
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        },
    }, {
        'url': 'https://youtu.be/uWyaPkt-VOI?list=PL9D9FC436B881BA21',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        playlist_id = mobj.group('playlist_id')
        return self.url_result(
            update_url_query('https://www.youtube.com/watch', {
                'v': video_id,
                'list': playlist_id,
                'feature': 'youtu.be',
            }), ie=YoutubeTabIE.ie_key(), video_id=playlist_id)


class YoutubeLivestreamEmbedIE(InfoExtractor):
    IE_DESC = 'YouTube livestream embeds'
    _VALID_URL = r'https?://(?:\w+\.)?youtube\.com/embed/live_stream/?\?(?:[^#]+&)?channel=(?P<id>[^&#]+)'
    _TESTS = [{
        'url': 'https://www.youtube.com/embed/live_stream?channel=UC2_KI6RB__jGdlnK6dvFEZA',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        return self.url_result(
            f'https://www.youtube.com/channel/{channel_id}/live',
            ie=YoutubeTabIE.ie_key(), video_id=channel_id)


class YoutubeYtUserIE(InfoExtractor):
    IE_DESC = 'YouTube user videos; "ytuser:" prefix'
    IE_NAME = 'youtube:user'
    _VALID_URL = r'ytuser:(?P<id>.+)'
    _TESTS = [{
        'url': 'ytuser:phihag',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self.url_result(f'https://www.youtube.com/user/{user_id}', YoutubeTabIE, user_id)


class YoutubeFavouritesIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:favorites'
    IE_DESC = 'YouTube liked videos; ":ytfav" keyword (requires cookies)'
    _VALID_URL = r':ytfav(?:ou?rite)?s?'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': ':ytfav',
        'only_matching': True,
    }, {
        'url': ':ytfavorites',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/playlist?list=LL',
            ie=YoutubeTabIE.ie_key())


class YoutubeNotificationsIE(YoutubeTabBaseInfoExtractor):
    IE_NAME = 'youtube:notif'
    IE_DESC = 'YouTube notifications; ":ytnotif" keyword (requires cookies)'
    _VALID_URL = r':ytnotif(?:ication)?s?'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': ':ytnotif',
        'only_matching': True,
    }, {
        'url': ':ytnotifications',
        'only_matching': True,
    }]

    def _extract_notification_menu(self, response, continuation_list):
        notification_list = traverse_obj(
            response,
            ('actions', 0, 'openPopupAction', 'popup', 'multiPageMenuRenderer', 'sections', 0, 'multiPageMenuNotificationSectionRenderer', 'items'),
            ('actions', 0, 'appendContinuationItemsAction', 'continuationItems'),
            expected_type=list) or []
        continuation_list[0] = None
        for item in notification_list:
            entry = self._extract_notification_renderer(item.get('notificationRenderer'))
            if entry:
                yield entry
            continuation = item.get('continuationItemRenderer')
            if continuation:
                continuation_list[0] = continuation

    def _extract_notification_renderer(self, notification):
        video_id = traverse_obj(
            notification, ('navigationEndpoint', 'watchEndpoint', 'videoId'), expected_type=str)
        url = f'https://www.youtube.com/watch?v={video_id}'
        channel_id = None
        if not video_id:
            browse_ep = traverse_obj(
                notification, ('navigationEndpoint', 'browseEndpoint'), expected_type=dict)
            channel_id = self.ucid_or_none(traverse_obj(browse_ep, 'browseId', expected_type=str))
            post_id = self._search_regex(
                r'/post/(.+)', traverse_obj(browse_ep, 'canonicalBaseUrl', expected_type=str),
                'post id', default=None)
            if not channel_id or not post_id:
                return
            # The direct /post url redirects to this in the browser
            url = f'https://www.youtube.com/channel/{channel_id}/community?lb={post_id}'

        channel = traverse_obj(
            notification, ('contextualMenu', 'menuRenderer', 'items', 1, 'menuServiceItemRenderer', 'text', 'runs', 1, 'text'),
            expected_type=str)
        notification_title = self._get_text(notification, 'shortMessage')
        if notification_title:
            notification_title = notification_title.replace('\xad', '')  # remove soft hyphens
        # TODO: handle recommended videos
        title = self._search_regex(
            rf'{re.escape(channel or "")}[^:]+: (.+)', notification_title,
            'video title', default=None)
        timestamp = (self._parse_time_text(self._get_text(notification, 'sentTimeText'))
                     if self._configuration_arg('approximate_date', ie_key=YoutubeTabIE)
                     else None)
        return {
            '_type': 'url',
            'url': url,
            'ie_key': (YoutubeIE if video_id else YoutubeTabIE).ie_key(),
            'video_id': video_id,
            'title': title,
            'channel_id': channel_id,
            'channel': channel,
            'uploader': channel,
            'thumbnails': self._extract_thumbnails(notification, 'videoThumbnail'),
            'timestamp': timestamp,
        }

    def _notification_menu_entries(self, ytcfg):
        continuation_list = [None]
        response = None
        for page in itertools.count(1):
            ctoken = traverse_obj(
                continuation_list, (0, 'continuationEndpoint', 'getNotificationMenuEndpoint', 'ctoken'), expected_type=str)
            response = self._extract_response(
                item_id=f'page {page}', query={'ctoken': ctoken} if ctoken else {}, ytcfg=ytcfg,
                ep='notification/get_notification_menu', check_get_keys='actions',
                headers=self.generate_api_headers(ytcfg=ytcfg, visitor_data=self._extract_visitor_data(response)))
            yield from self._extract_notification_menu(response, continuation_list)
            if not continuation_list[0]:
                break

    def _real_extract(self, url):
        display_id = 'notifications'
        ytcfg = self._download_ytcfg('web', display_id) if not self.skip_webpage else {}
        self._report_playlist_authcheck(ytcfg)
        return self.playlist_result(self._notification_menu_entries(ytcfg), display_id, display_id)


class YoutubeSearchIE(YoutubeTabBaseInfoExtractor, SearchInfoExtractor):
    IE_DESC = 'YouTube search'
    IE_NAME = 'youtube:search'
    _SEARCH_KEY = 'ytsearch'
    _SEARCH_PARAMS = 'EgIQAfABAQ=='  # Videos only
    _TESTS = [{
        'url': 'ytsearch5:youtube-dl test video',
        'playlist_count': 5,
        'info_dict': {
            'id': 'youtube-dl test video',
            'title': 'youtube-dl test video',
        },
    }, {
        'note': 'Suicide/self-harm search warning',
        'url': 'ytsearch1:i hate myself and i wanna die',
        'playlist_count': 1,
        'info_dict': {
            'id': 'i hate myself and i wanna die',
            'title': 'i hate myself and i wanna die',
        },
    }]


class YoutubeSearchDateIE(YoutubeTabBaseInfoExtractor, SearchInfoExtractor):
    IE_NAME = YoutubeSearchIE.IE_NAME + ':date'
    _SEARCH_KEY = 'ytsearchdate'
    IE_DESC = 'YouTube search, newest videos first'
    _SEARCH_PARAMS = 'CAISAhAB8AEB'  # Videos only, sorted by date
    _TESTS = [{
        'url': 'ytsearchdate5:youtube-dl test video',
        'playlist_count': 5,
        'info_dict': {
            'id': 'youtube-dl test video',
            'title': 'youtube-dl test video',
        },
    }]


class YoutubeSearchURLIE(YoutubeTabBaseInfoExtractor):
    IE_DESC = 'YouTube search URLs with sorting and filter support'
    IE_NAME = YoutubeSearchIE.IE_NAME + '_url'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/(?:results|search)\?([^#]+&)?(?:search_query|q)=(?:[^&]+)(?:[&#]|$)'
    _TESTS = [{
        'url': 'https://www.youtube.com/results?baz=bar&search_query=youtube-dl+test+video&filters=video&lclk=video',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'youtube-dl test video',
            'title': 'youtube-dl test video',
        },
    }, {
        'url': 'https://www.youtube.com/results?search_query=python&sp=EgIQAg%253D%253D',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'python',
            'title': 'python',
        },
    }, {
        'url': 'https://www.youtube.com/results?search_query=%23cats',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '#cats',
            'title': '#cats',
            # The test suite does not have support for nested playlists
            # 'entries': [{
            #     'url': r're:https://(www\.)?youtube\.com/hashtag/cats',
            #     'title': '#cats',
            # }],
        },
    }, {
        # Channel results
        'url': 'https://www.youtube.com/results?search_query=kurzgesagt&sp=EgIQAg%253D%253D',
        'info_dict': {
            'id': 'kurzgesagt',
            'title': 'kurzgesagt',
        },
        'playlist': [{
            'info_dict': {
                '_type': 'url',
                'id': 'UCsXVk37bltHxD1rDPwtNM8Q',
                'url': 'https://www.youtube.com/channel/UCsXVk37bltHxD1rDPwtNM8Q',
                'ie_key': 'YoutubeTab',
                'channel': 'Kurzgesagt – In a Nutshell',
                'description': 'md5:4ae48dfa9505ffc307dad26342d06bfc',
                'title': 'Kurzgesagt – In a Nutshell',
                'channel_id': 'UCsXVk37bltHxD1rDPwtNM8Q',
                # No longer available for search as it is set to the handle.
                # 'playlist_count': int,
                'channel_url': 'https://www.youtube.com/channel/UCsXVk37bltHxD1rDPwtNM8Q',
                'thumbnails': list,
                'uploader_id': '@kurzgesagt',
                'uploader_url': 'https://www.youtube.com/@kurzgesagt',
                'uploader': 'Kurzgesagt – In a Nutshell',
                'channel_is_verified': True,
                'channel_follower_count': int,
            },
        }],
        'params': {'extract_flat': True, 'playlist_items': '1'},
        'playlist_mincount': 1,
    }, {
        'url': 'https://www.youtube.com/results?q=test&sp=EgQIBBgB',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        qs = parse_qs(url)
        query = (qs.get('search_query') or qs.get('q'))[0]
        return self.playlist_result(self._search_results(query, qs.get('sp', (None,))[0]), query, query)


class YoutubeMusicSearchURLIE(YoutubeTabBaseInfoExtractor):
    IE_DESC = 'YouTube music search URLs with selectable sections, e.g. #songs'
    IE_NAME = 'youtube:music:search_url'
    _VALID_URL = r'https?://music\.youtube\.com/search\?([^#]+&)?(?:search_query|q)=(?:[^&]+)(?:[&#]|$)'
    _TESTS = [{
        'url': 'https://music.youtube.com/search?q=royalty+free+music',
        'playlist_count': 16,
        'info_dict': {
            'id': 'royalty free music',
            'title': 'royalty free music',
        },
    }, {
        'url': 'https://music.youtube.com/search?q=royalty+free+music&sp=EgWKAQIIAWoKEAoQAxAEEAkQBQ%3D%3D',
        'playlist_mincount': 30,
        'info_dict': {
            'id': 'royalty free music - songs',
            'title': 'royalty free music - songs',
        },
        'params': {'extract_flat': 'in_playlist'},
    }, {
        'url': 'https://music.youtube.com/search?q=royalty+free+music#community+playlists',
        'playlist_mincount': 30,
        'info_dict': {
            'id': 'royalty free music - community playlists',
            'title': 'royalty free music - community playlists',
        },
        'params': {'extract_flat': 'in_playlist'},
    }]

    _SECTIONS = {
        'albums': 'EgWKAQIYAWoKEAoQAxAEEAkQBQ==',
        'artists': 'EgWKAQIgAWoKEAoQAxAEEAkQBQ==',
        'community playlists': 'EgeKAQQoAEABagoQChADEAQQCRAF',
        'featured playlists': 'EgeKAQQoADgBagwQAxAJEAQQDhAKEAU==',
        'songs': 'EgWKAQIIAWoKEAoQAxAEEAkQBQ==',
        'videos': 'EgWKAQIQAWoKEAoQAxAEEAkQBQ==',
    }

    def _real_extract(self, url):
        qs = parse_qs(url)
        query = (qs.get('search_query') or qs.get('q'))[0]
        params = qs.get('sp', (None,))[0]
        if params:
            section = next((k for k, v in self._SECTIONS.items() if v == params), params)
        else:
            section = urllib.parse.unquote_plus(([*url.split('#'), ''])[1]).lower()
            params = self._SECTIONS.get(section)
            if not params:
                section = None
        title = join_nonempty(query, section, delim=' - ')
        return self.playlist_result(self._search_results(query, params, default_client='web_music'), title, title)


class YoutubeFeedsInfoExtractor(InfoExtractor):
    """
    Base class for feed extractors
    Subclasses must re-define the _FEED_NAME property.
    """
    _LOGIN_REQUIRED = True
    _FEED_NAME = 'feeds'

    def _real_initialize(self):
        YoutubeBaseInfoExtractor._check_login_required(self)

    @classproperty
    def IE_NAME(cls):
        return f'youtube:{cls._FEED_NAME}'

    def _real_extract(self, url):
        return self.url_result(
            f'https://www.youtube.com/feed/{self._FEED_NAME}', ie=YoutubeTabIE.ie_key())


class YoutubeWatchLaterIE(InfoExtractor):
    IE_NAME = 'youtube:watchlater'
    IE_DESC = 'Youtube watch later list; ":ytwatchlater" keyword (requires cookies)'
    _VALID_URL = r':ytwatchlater'
    _TESTS = [{
        'url': ':ytwatchlater',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/playlist?list=WL', ie=YoutubeTabIE.ie_key())


class YoutubeRecommendedIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube recommended videos; ":ytrec" keyword'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/?(?:[?#]|$)|:ytrec(?:ommended)?'
    _FEED_NAME = 'recommended'
    _LOGIN_REQUIRED = False
    _TESTS = [{
        'url': ':ytrec',
        'only_matching': True,
    }, {
        'url': ':ytrecommended',
        'only_matching': True,
    }, {
        'url': 'https://youtube.com',
        'only_matching': True,
    }]


class YoutubeSubscriptionsIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube subscriptions feed; ":ytsubs" keyword (requires cookies)'
    _VALID_URL = r':ytsub(?:scription)?s?'
    _FEED_NAME = 'subscriptions'
    _TESTS = [{
        'url': ':ytsubs',
        'only_matching': True,
    }, {
        'url': ':ytsubscriptions',
        'only_matching': True,
    }]


class YoutubeHistoryIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'Youtube watch history; ":ythis" keyword (requires cookies)'
    _VALID_URL = r':ythis(?:tory)?'
    _FEED_NAME = 'history'
    _TESTS = [{
        'url': ':ythistory',
        'only_matching': True,
    }]


class YoutubeShortsAudioPivotIE(InfoExtractor):
    IE_DESC = 'YouTube Shorts audio pivot (Shorts using audio of a given video)'
    IE_NAME = 'youtube:shorts:pivot:audio'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/source/(?P<id>[\w-]{11})/shorts'
    _TESTS = [{
        'url': 'https://www.youtube.com/source/Lyj-MZSAA9o/shorts',
        'only_matching': True,
    }]

    @staticmethod
    def _generate_audio_pivot_params(video_id):
        """
        Generates sfv_audio_pivot browse params for this video id
        """
        pb_params = b'\xf2\x05+\n)\x12\'\n\x0b%b\x12\x0b%b\x1a\x0b%b' % ((video_id.encode(),) * 3)
        return urllib.parse.quote(base64.b64encode(pb_params).decode())

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'https://www.youtube.com/feed/sfv_audio_pivot?bp={self._generate_audio_pivot_params(video_id)}',
            ie=YoutubeTabIE)


class YoutubeTruncatedURLIE(InfoExtractor):
    IE_NAME = 'youtube:truncated_url'
    IE_DESC = False  # Do not list
    _VALID_URL = r'''(?x)
        (?:https?://)?
        (?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie)?\.com/
        (?:watch\?(?:
            feature=[a-z_]+|
            annotation_id=annotation_[^&]+|
            x-yt-cl=[0-9]+|
            hl=[^&]*|
            t=[0-9]+
        )?
        |
            attribution_link\?a=[^&]+
        )
        $
    '''

    _TESTS = [{
        'url': 'https://www.youtube.com/watch?annotation_id=annotation_3951667041',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?x-yt-cl=84503534',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?feature=foo',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?hl=en-GB',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?t=2372',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        raise ExtractorError(
            'Did you forget to quote the URL? Remember that & is a meta '
            'character in most shells, so you want to put the URL in quotes, '
            'like  youtube-dl '
            '"https://www.youtube.com/watch?feature=foo&v=BaW_jenozKc" '
            ' or simply  youtube-dl BaW_jenozKc  .',
            expected=True)


class YoutubeClipIE(YoutubeTabBaseInfoExtractor):
    IE_NAME = 'youtube:clip'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/clip/(?P<id>[^/?#]+)'
    _TESTS = [{
        # FIXME: Other metadata should be extracted from the clip, not from the base video
        'url': 'https://www.youtube.com/clip/UgytZKpehg-hEMBSn3F4AaABCQ',
        'info_dict': {
            'id': 'UgytZKpehg-hEMBSn3F4AaABCQ',
            'ext': 'mp4',
            'section_start': 29.0,
            'section_end': 39.7,
            'duration': 10.7,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Gaming'],
            'channel': 'Scott The Woz',
            'channel_id': 'UC4rqhyiTs7XyuODcECvuiiQ',
            'channel_url': 'https://www.youtube.com/channel/UC4rqhyiTs7XyuODcECvuiiQ',
            'description': 'md5:7a4517a17ea9b4bd98996399d8bb36e7',
            'like_count': int,
            'playable_in_embed': True,
            'tags': 'count:17',
            'thumbnail': 'https://i.ytimg.com/vi_webp/ScPX26pdQik/maxresdefault.webp',
            'title': 'Mobile Games on Console - Scott The Woz',
            'upload_date': '20210920',
            'uploader': 'Scott The Woz',
            'uploader_id': '@ScottTheWoz',
            'uploader_url': 'https://www.youtube.com/@ScottTheWoz',
            'view_count': int,
            'live_status': 'not_live',
            'channel_follower_count': int,
            'chapters': 'count:20',
            'comment_count': int,
            'heatmap': 'count:100',
        },
    }]

    def _real_extract(self, url):
        clip_id = self._match_id(url)
        _, data = self._extract_webpage(url, clip_id)

        video_id = traverse_obj(data, ('currentVideoEndpoint', 'watchEndpoint', 'videoId'))
        if not video_id:
            raise ExtractorError('Unable to find video ID')

        clip_data = traverse_obj(data, (
            'engagementPanels', ..., 'engagementPanelSectionListRenderer', 'content', 'clipSectionRenderer',
            'contents', ..., 'clipAttributionRenderer', 'onScrubExit', 'commandExecutorCommand', 'commands', ...,
            'openPopupAction', 'popup', 'notificationActionRenderer', 'actionButton', 'buttonRenderer', 'command',
            'commandExecutorCommand', 'commands', ..., 'loopCommand'), get_all=False)

        return {
            '_type': 'url_transparent',
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'ie_key': YoutubeIE.ie_key(),
            'id': clip_id,
            'section_start': int(clip_data['startTimeMs']) / 1000,
            'section_end': int(clip_data['endTimeMs']) / 1000,
        }


class YoutubeConsentRedirectIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:consent'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://consent\.youtube\.com/m\?'
    _TESTS = [{
        'url': 'https://consent.youtube.com/m?continue=https%3A%2F%2Fwww.youtube.com%2Flive%2FqVv6vCqciTM%3Fcbrd%3D1&gl=NL&m=0&pc=yt&hl=en&src=1',
        'info_dict': {
            'id': 'qVv6vCqciTM',
            'ext': 'mp4',
            'age_limit': 0,
            'uploader_id': '@sana_natori',
            'comment_count': int,
            'chapters': 'count:13',
            'upload_date': '20221223',
            'thumbnail': 'https://i.ytimg.com/vi/qVv6vCqciTM/maxresdefault.jpg',
            'channel_url': 'https://www.youtube.com/channel/UCIdEIHpS0TdkqRkHL5OkLtA',
            'uploader_url': 'https://www.youtube.com/@sana_natori',
            'like_count': int,
            'release_date': '20221223',
            'tags': ['Vtuber', '月ノ美兎', '名取さな', 'にじさんじ', 'クリスマス', '3D配信'],
            'title': '【 #インターネット女クリスマス 】3Dで歌ってはしゃぐインターネットの女たち【月ノ美兎/名取さな】',
            'view_count': int,
            'playable_in_embed': True,
            'duration': 4438,
            'availability': 'public',
            'channel_follower_count': int,
            'channel_id': 'UCIdEIHpS0TdkqRkHL5OkLtA',
            'categories': ['Entertainment'],
            'live_status': 'was_live',
            'release_timestamp': 1671793345,
            'channel': 'さなちゃんねる',
            'description': 'md5:6aebf95cc4a1d731aebc01ad6cc9806d',
            'uploader': 'さなちゃんねる',
            'channel_is_verified': True,
            'heatmap': 'count:100',
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'Youtube'},
    }]

    def _real_extract(self, url):
        redirect_url = url_or_none(parse_qs(url).get('continue', [None])[-1])
        if not redirect_url:
            raise ExtractorError('Invalid cookie consent redirect URL', expected=True)
        return self.url_result(redirect_url)


class YoutubeTruncatedIDIE(InfoExtractor):
    IE_NAME = 'youtube:truncated_id'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/watch\?v=(?P<id>[0-9A-Za-z_-]{1,10})$'

    _TESTS = [{
        'url': 'https://www.youtube.com/watch?v=N_708QY7Ob',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        raise ExtractorError(
            f'Incomplete YouTube ID {video_id}. URL {url} looks truncated.',
            expected=True)

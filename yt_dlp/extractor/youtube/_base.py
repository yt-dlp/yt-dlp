import calendar
import copy
import dataclasses
import datetime as dt
import enum
import functools
import hashlib
import json
import re
import time
import urllib.parse

from ..common import InfoExtractor
from ...networking.exceptions import HTTPError, network_exceptions
from ...utils import (
    ExtractorError,
    bug_reports_message,
    datetime_from_str,
    filter_dict,
    get_first,
    int_or_none,
    is_html,
    join_nonempty,
    parse_count,
    qualities,
    str_to_int,
    traverse_obj,
    try_call,
    try_get,
    unified_timestamp,
    url_or_none,
    variadic,
)


class _PoTokenContext(enum.Enum):
    PLAYER = 'player'
    GVS = 'gvs'
    SUBS = 'subs'


class StreamingProtocol(enum.Enum):
    HTTPS = 'https'
    DASH = 'dash'
    HLS = 'hls'


@dataclasses.dataclass
class BasePoTokenPolicy:
    required: bool = False
    # Try to fetch a PO Token even if it is not required.
    recommended: bool = False
    not_required_for_premium: bool = False


@dataclasses.dataclass
class GvsPoTokenPolicy(BasePoTokenPolicy):
    not_required_with_player_token: bool = False


@dataclasses.dataclass
class PlayerPoTokenPolicy(BasePoTokenPolicy):
    pass


@dataclasses.dataclass
class SubsPoTokenPolicy(BasePoTokenPolicy):
    pass


WEB_PO_TOKEN_POLICIES = {
    'GVS_PO_TOKEN_POLICY': {
        StreamingProtocol.HTTPS: GvsPoTokenPolicy(
            required=True,
            recommended=True,
            not_required_for_premium=True,
            not_required_with_player_token=False,
        ),
        StreamingProtocol.DASH: GvsPoTokenPolicy(
            required=True,
            recommended=True,
            not_required_for_premium=True,
            not_required_with_player_token=False,
        ),
        StreamingProtocol.HLS: GvsPoTokenPolicy(
            required=False,
            recommended=True,
        ),
    },
    'PLAYER_PO_TOKEN_POLICY': PlayerPoTokenPolicy(required=False),
    # In rollout, currently detected via experiment
    # Premium users DO require a PO Token for subtitles
    'SUBS_PO_TOKEN_POLICY': SubsPoTokenPolicy(required=False),
}

# any clients starting with _ cannot be explicitly requested by the user
INNERTUBE_CLIENTS = {
    'web': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20250312.04.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 1,
        'SUPPORTS_COOKIES': True,
        **WEB_PO_TOKEN_POLICIES,
        'PLAYER_PARAMS': '8AEB',
    },
    # Safari UA returns pre-merged video+audio 144p/240p/360p/720p/1080p HLS formats
    'web_safari': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20250312.04.00',
                'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15,gzip(gfe)',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 1,
        'SUPPORTS_COOKIES': True,
        **WEB_PO_TOKEN_POLICIES,
        'PLAYER_PARAMS': '8AEB',
    },
    'web_embedded': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_EMBEDDED_PLAYER',
                'clientVersion': '1.20250310.01.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 56,
        'SUPPORTS_COOKIES': True,
    },
    'web_music': {
        'INNERTUBE_HOST': 'music.youtube.com',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '1.20250310.01.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 67,
        'GVS_PO_TOKEN_POLICY': {
            StreamingProtocol.HTTPS: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_for_premium=True,
                not_required_with_player_token=False,
            ),
            StreamingProtocol.DASH: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_for_premium=True,
                not_required_with_player_token=False,
            ),
            StreamingProtocol.HLS: GvsPoTokenPolicy(
                required=False,
                recommended=True,
            ),
        },
        'SUPPORTS_COOKIES': True,
    },
    # This client now requires sign-in for every video
    'web_creator': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_CREATOR',
                'clientVersion': '1.20250312.03.01',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 62,
        'GVS_PO_TOKEN_POLICY': {
            StreamingProtocol.HTTPS: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_for_premium=True,
                not_required_with_player_token=False,
            ),
            StreamingProtocol.DASH: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_for_premium=True,
                not_required_with_player_token=False,
            ),
            StreamingProtocol.HLS: GvsPoTokenPolicy(
                required=False,
                recommended=True,
            ),
        },
        'REQUIRE_AUTH': True,
        'SUPPORTS_COOKIES': True,
    },
    'android': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '20.10.38',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip',
                'osName': 'Android',
                'osVersion': '11',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 3,
        'REQUIRE_JS_PLAYER': False,
        'GVS_PO_TOKEN_POLICY': {
            StreamingProtocol.HTTPS: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_with_player_token=True,
            ),
            StreamingProtocol.DASH: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_with_player_token=True,
            ),
            StreamingProtocol.HLS: GvsPoTokenPolicy(
                required=False,
                recommended=True,
                not_required_with_player_token=True,
            ),
        },
        'PLAYER_PO_TOKEN_POLICY': PlayerPoTokenPolicy(required=False, recommended=True),
    },
    # YouTube Kids videos aren't returned on this client for some reason
    'android_vr': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_VR',
                'clientVersion': '1.62.27',
                'deviceMake': 'Oculus',
                'deviceModel': 'Quest 3',
                'androidSdkVersion': 32,
                'userAgent': 'com.google.android.apps.youtube.vr.oculus/1.62.27 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip',
                'osName': 'Android',
                'osVersion': '12L',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 28,
        'REQUIRE_JS_PLAYER': False,
    },
    # iOS clients have HLS live streams. Setting device model to get 60fps formats.
    # See: https://github.com/TeamNewPipe/NewPipeExtractor/issues/680#issuecomment-1002724558
    'ios': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS',
                'clientVersion': '20.10.4',
                'deviceMake': 'Apple',
                'deviceModel': 'iPhone16,2',
                'userAgent': 'com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)',
                'osName': 'iPhone',
                'osVersion': '18.3.2.22D82',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 5,
        'GVS_PO_TOKEN_POLICY': {
            StreamingProtocol.HTTPS: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_with_player_token=True,
            ),
            # HLS Livestreams require POT 30 seconds in
            # TODO: Rolling out
            StreamingProtocol.HLS: GvsPoTokenPolicy(
                required=False,
                recommended=True,
                not_required_with_player_token=True,
            ),
        },
        'PLAYER_PO_TOKEN_POLICY': PlayerPoTokenPolicy(required=False, recommended=True),
        'REQUIRE_JS_PLAYER': False,
    },
    # mweb has 'ultralow' formats
    # See: https://github.com/yt-dlp/yt-dlp/pull/557
    'mweb': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'MWEB',
                'clientVersion': '2.20250311.03.00',
                # mweb previously did not require PO Token with this UA
                'userAgent': 'Mozilla/5.0 (iPad; CPU OS 16_7_10 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1,gzip(gfe)',
            },
        },
        'PLAYER_PARAMS': '8AEB',
        'INNERTUBE_CONTEXT_CLIENT_NAME': 2,
        'GVS_PO_TOKEN_POLICY': {
            StreamingProtocol.HTTPS: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_for_premium=True,
                not_required_with_player_token=False,
            ),
            StreamingProtocol.DASH: GvsPoTokenPolicy(
                required=True,
                recommended=True,
                not_required_for_premium=True,
                not_required_with_player_token=False,
            ),
            StreamingProtocol.HLS: GvsPoTokenPolicy(
                required=False,
                recommended=True,
            ),
        },
        'SUPPORTS_COOKIES': True,
    },
    'tv': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'TVHTML5',
                'clientVersion': '7.20250312.16.00',
                'userAgent': 'Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 7,
        'SUPPORTS_COOKIES': True,
        'PLAYER_PARAMS': '8AEB',
    },
    'tv_simply': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'TVHTML5_SIMPLY',
                'clientVersion': '1.0',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 75,
    },
    # This client now requires sign-in for every video
    # It was previously an age-gate workaround for videos that were `playable_in_embed`
    # It may still be useful if signed into an EU account that is not age-verified
    'tv_embedded': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                'clientVersion': '2.0',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 85,
        'REQUIRE_AUTH': True,
        'SUPPORTS_COOKIES': True,
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
        ytcfg.setdefault('GVS_PO_TOKEN_POLICY', {})
        for protocol in StreamingProtocol:
            ytcfg['GVS_PO_TOKEN_POLICY'].setdefault(protocol, GvsPoTokenPolicy())
        ytcfg.setdefault('PLAYER_PO_TOKEN_POLICY', PlayerPoTokenPolicy())
        ytcfg.setdefault('SUBS_PO_TOKEN_POLICY', SubsPoTokenPolicy())
        ytcfg.setdefault('REQUIRE_AUTH', False)
        ytcfg.setdefault('SUPPORTS_COOKIES', False)
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


CONFIGURATION_ARG_KEY = 'youtube'


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

    _NETRC_MACHINE = 'youtube'

    _COOKIE_HOWTO_WIKI_URL = 'https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies'

    def ucid_or_none(self, ucid):
        return self._search_regex(rf'^({self._YT_CHANNEL_UCID_RE})$', ucid, 'UC-id', default=None)

    def handle_or_none(self, handle):
        return self._search_regex(rf'^({self._YT_HANDLE_RE})$', urllib.parse.unquote(handle or ''),
                                  '@-handle', default=None)

    def handle_from_url(self, url):
        return self._search_regex(rf'^(?:https?://(?:www\.)?youtube\.com)?/({self._YT_HANDLE_RE})',
                                  urllib.parse.unquote(url or ''), 'channel handle', default=None)

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
        if self._has_auth_cookies:
            return
        socs = self._youtube_cookies.get('SOCS')
        if socs and not socs.value.startswith('CAA'):  # not consented
            return
        self._set_cookie('.youtube.com', 'SOCS', 'CAI', secure=True)  # accept all (required for mixes)

    def _initialize_pref(self):
        pref_cookie = self._youtube_cookies.get('PREF')
        pref = {}
        if pref_cookie:
            try:
                pref = dict(urllib.parse.parse_qsl(pref_cookie.value))
            except ValueError:
                self.report_warning('Failed to parse user PREF cookie' + bug_reports_message())
        pref.update({'hl': self._preferred_lang or 'en', 'tz': 'UTC'})
        self._set_cookie('.youtube.com', name='PREF', value=urllib.parse.urlencode(pref))

    def _initialize_cookie_auth(self):
        self._passed_auth_cookies = False
        if self._has_auth_cookies:
            self._passed_auth_cookies = True
            self.write_debug('Found YouTube account cookies')

    def _real_initialize(self):
        self._initialize_pref()
        self._initialize_consent()
        self._initialize_cookie_auth()
        self._check_login_required()

    def _perform_login(self, username, password):
        if username.startswith('oauth'):
            raise ExtractorError(
                f'Login with OAuth is no longer supported. {self._youtube_login_hint}', expected=True)

        self.report_warning(
            f'Login with password is not supported for YouTube. {self._youtube_login_hint}')

    @property
    def _youtube_login_hint(self):
        return (f'{self._login_hint(method="cookies")}. Also see  {self._COOKIE_HOWTO_WIKI_URL}  '
                'for tips on effectively exporting YouTube cookies')

    def _check_login_required(self):
        if self._LOGIN_REQUIRED and not self.is_authenticated:
            self.raise_login_required(
                f'Login details are needed to download this content. {self._youtube_login_hint}', method=None)

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
        return (self._configuration_arg('innertube_host', [''], ie_key=CONFIGURATION_ARG_KEY)[0]
                or req_api_hostname or self._get_innertube_host(default_client or 'web'))

    def _extract_context(self, ytcfg=None, default_client='web'):
        context = get_first(
            (ytcfg, self._get_default_ytcfg(default_client)), 'INNERTUBE_CONTEXT', expected_type=dict)
        # Enforce language and tz for extraction
        client_context = traverse_obj(context, 'client', expected_type=dict, default={})
        client_context.update({'hl': self._preferred_lang or 'en', 'timeZone': 'UTC', 'utcOffsetMinutes': 0})
        return context

    @staticmethod
    def _make_sid_authorization(scheme, sid, origin, additional_parts):
        timestamp = str(round(time.time()))

        hash_parts = []
        if additional_parts:
            hash_parts.append(':'.join(additional_parts.values()))
        hash_parts.extend([timestamp, sid, origin])
        sidhash = hashlib.sha1(' '.join(hash_parts).encode()).hexdigest()

        parts = [timestamp, sidhash]
        if additional_parts:
            parts.append(''.join(additional_parts))

        return f'{scheme} {"_".join(parts)}'

    @property
    def _youtube_cookies(self):
        return self._get_cookies('https://www.youtube.com')

    def _get_sid_cookies(self):
        """
        Get SAPISID, 1PSAPISID, 3PSAPISID cookie values
        @returns sapisid, 1psapisid, 3psapisid
        """
        yt_cookies = self._youtube_cookies
        yt_sapisid = try_call(lambda: yt_cookies['SAPISID'].value)
        yt_3papisid = try_call(lambda: yt_cookies['__Secure-3PAPISID'].value)
        yt_1papisid = try_call(lambda: yt_cookies['__Secure-1PAPISID'].value)

        # Sometimes SAPISID cookie isn't present but __Secure-3PAPISID is.
        # YouTube also falls back to __Secure-3PAPISID if SAPISID is missing.
        # See: https://github.com/yt-dlp/yt-dlp/issues/393

        return yt_sapisid or yt_3papisid, yt_1papisid, yt_3papisid

    def _get_sid_authorization_header(self, origin='https://www.youtube.com', user_session_id=None):
        """
        Generate API Session ID Authorization for Innertube requests. Assumes all requests are secure (https).
        @param origin: Origin URL
        @param user_session_id: Optional User Session ID
        @return: Authorization header value
        """

        authorizations = []
        additional_parts = {}
        if user_session_id:
            additional_parts['u'] = user_session_id

        yt_sapisid, yt_1psapisid, yt_3psapisid = self._get_sid_cookies()

        for scheme, sid in (('SAPISIDHASH', yt_sapisid),
                            ('SAPISID1PHASH', yt_1psapisid),
                            ('SAPISID3PHASH', yt_3psapisid)):
            if sid:
                authorizations.append(self._make_sid_authorization(scheme, sid, origin, additional_parts))

        if not authorizations:
            return None

        return ' '.join(authorizations)

    @property
    def is_authenticated(self):
        return self._has_auth_cookies

    @property
    def _has_auth_cookies(self):
        yt_sapisid, yt_1psapisid, yt_3psapisid = self._get_sid_cookies()
        # YouTube doesn't appear to clear 3PSAPISID when rotating cookies (as of 2025-04-26)
        # But LOGIN_INFO is cleared and should exist if logged in
        has_login_info = 'LOGIN_INFO' in self._youtube_cookies
        return bool(has_login_info and (yt_sapisid or yt_1psapisid or yt_3psapisid))

    def _request_webpage(self, *args, **kwargs):
        response = super()._request_webpage(*args, **kwargs)

        # Check that we are still logged-in and cookies have not rotated after every request
        if getattr(self, '_passed_auth_cookies', None) and not self._has_auth_cookies:
            self.report_warning(
                'The provided YouTube account cookies are no longer valid. '
                'They have likely been rotated in the browser as a security measure. '
                f'For tips on how to effectively export YouTube cookies, refer to  {self._COOKIE_HOWTO_WIKI_URL} .',
                only_once=False)

        return response

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
                    'innertube_key', [api_key], ie_key=CONFIGURATION_ARG_KEY, casesense=True)[0],
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

    @staticmethod
    def _parse_data_sync_id(data_sync_id):
        """
        Parse data_sync_id into delegated_session_id and user_session_id.

        data_sync_id is of the form "delegated_session_id||user_session_id" for secondary channel
        and just "user_session_id||" for primary channel.

        @param data_sync_id: data_sync_id string
        @return: Tuple of (delegated_session_id, user_session_id)
        """
        if not data_sync_id:
            return None, None
        first, _, second = data_sync_id.partition('||')
        if second:
            return first, second
        return None, first

    def _extract_delegated_session_id(self, *args):
        """
        Extract current delegated session ID required to download private playlists of secondary channels
        @params response and/or ytcfg
        @return: delegated session ID
        """
        # ytcfg includes channel_syncid if on secondary channel
        if delegated_sid := traverse_obj(args, (..., 'DELEGATED_SESSION_ID', {str}, any)):
            return delegated_sid

        data_sync_id = self._extract_data_sync_id(*args)
        return self._parse_data_sync_id(data_sync_id)[0]

    def _extract_user_session_id(self, *args):
        """
        Extract current user session ID
        @params response and/or ytcfg
        @return: user session ID
        """
        if user_sid := traverse_obj(args, (..., 'USER_SESSION_ID', {str}, any)):
            return user_sid

        data_sync_id = self._extract_data_sync_id(*args)
        return self._parse_data_sync_id(data_sync_id)[1]

    def _extract_data_sync_id(self, *args):
        """
        Extract current account dataSyncId.
        In the format DELEGATED_SESSION_ID||USER_SESSION_ID or USER_SESSION_ID||
        @params response and/or ytcfg
        """
        if data_sync_id := self._configuration_arg('data_sync_id', [None], ie_key=CONFIGURATION_ARG_KEY, casesense=True)[0]:
            return data_sync_id

        return traverse_obj(
            args, (..., ('DATASYNC_ID', ('responseContext', 'mainAppWebResponseContext', 'datasyncId')), {str}, any))

    def _extract_visitor_data(self, *args):
        """
        Extracts visitorData from an API response or ytcfg
        Appears to be used to track session state
        """
        if visitor_data := self._configuration_arg('visitor_data', [None], ie_key=CONFIGURATION_ARG_KEY, casesense=True)[0]:
            return visitor_data
        return get_first(
            args, [('VISITOR_DATA', ('INNERTUBE_CONTEXT', 'client', 'visitorData'), ('responseContext', 'visitorData'))],
            expected_type=str)

    def extract_ytcfg(self, video_id, webpage):
        if not webpage:
            return {}
        return self._parse_json(
            self._search_regex(
                r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', webpage, 'ytcfg',
                default='{}'), video_id, fatal=False) or {}

    def _generate_cookie_auth_headers(self, *, ytcfg=None, delegated_session_id=None, user_session_id=None, session_index=None, origin=None, **kwargs):
        headers = {}
        delegated_session_id = delegated_session_id or self._extract_delegated_session_id(ytcfg)
        if delegated_session_id:
            headers['X-Goog-PageId'] = delegated_session_id
        if session_index is None:
            session_index = self._extract_session_index(ytcfg)
        if delegated_session_id or session_index is not None:
            headers['X-Goog-AuthUser'] = session_index if session_index is not None else 0

        auth = self._get_sid_authorization_header(origin, user_session_id=user_session_id or self._extract_user_session_id(ytcfg))
        if auth is not None:
            headers['Authorization'] = auth
            headers['X-Origin'] = origin

        if traverse_obj(ytcfg, 'LOGGED_IN', expected_type=bool):
            headers['X-Youtube-Bootstrap-Logged-In'] = 'true'

        return headers

    def generate_api_headers(
            self, *, ytcfg=None, delegated_session_id=None, user_session_id=None, session_index=None,
            visitor_data=None, api_hostname=None, default_client='web', **kwargs):

        origin = 'https://' + (self._select_api_hostname(api_hostname, default_client))
        headers = {
            'X-YouTube-Client-Name': str(
                self._ytcfg_get_safe(ytcfg, lambda x: x['INNERTUBE_CONTEXT_CLIENT_NAME'], default_client=default_client)),
            'X-YouTube-Client-Version': self._extract_client_version(ytcfg, default_client),
            'Origin': origin,
            'X-Goog-Visitor-Id': visitor_data or self._extract_visitor_data(ytcfg),
            'User-Agent': self._ytcfg_get_safe(ytcfg, lambda x: x['INNERTUBE_CONTEXT']['client']['userAgent'], default_client=default_client),
            **self._generate_cookie_auth_headers(
                ytcfg=ytcfg,
                delegated_session_id=delegated_session_id,
                user_session_id=user_session_id,
                session_index=session_index,
                origin=origin),
        }
        return filter_dict(headers)

    def _download_webpage_with_retries(self, *args, retry_fatal=False, retry_on_status=None, **kwargs):
        for retry in self.RetryManager(fatal=retry_fatal):
            try:
                return self._download_webpage(*args, **kwargs)
            except ExtractorError as e:
                if isinstance(e.cause, network_exceptions):
                    if not isinstance(e.cause, HTTPError) or e.cause.status not in (retry_on_status or (403, 429)):
                        retry.error = e
                        continue
                self._error_or_warning(e, fatal=retry_fatal)
                break

    def _download_ytcfg(self, client, video_id):
        url = {
            'mweb': 'https://m.youtube.com',
            'web': 'https://www.youtube.com',
            'web_music': 'https://music.youtube.com',
            'web_embedded': f'https://www.youtube.com/embed/{video_id}?html5=1',
            'tv': 'https://www.youtube.com/tv',
        }.get(client)
        if not url:
            return {}
        webpage = self._download_webpage_with_retries(
            url, video_id, note=f'Downloading {client.replace("_", " ").strip()} client config',
            headers=traverse_obj(self._get_default_ytcfg(client), {
                'User-Agent': ('INNERTUBE_CONTEXT', 'client', 'userAgent', {str}),
            }))
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
        continuation_commands = traverse_obj(
            continuation_ep, ('commandExecutorCommand', 'commands', ..., {dict}))
        continuation_commands.append(continuation_ep)
        for command in continuation_commands:
            continuation = traverse_obj(command, ('continuationCommand', 'token', {str}))
            if not continuation:
                continue
            ctp = command.get('clickTrackingParams')
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
        raise_for_incomplete = bool(self._configuration_arg('raise_incomplete_data', ie_key=CONFIGURATION_ARG_KEY))
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

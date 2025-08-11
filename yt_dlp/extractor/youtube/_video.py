import base64
import binascii
import collections
import datetime as dt
import functools
import itertools
import json
import math
import os.path
import random
import re
import sys
import threading
import time
import traceback
import urllib.parse

from ._base import (
    INNERTUBE_CLIENTS,
    BadgeType,
    GvsPoTokenPolicy,
    PlayerPoTokenPolicy,
    StreamingProtocol,
    YoutubeBaseInfoExtractor,
    _PoTokenContext,
    _split_innertube_client,
    short_client_name,
)
from .pot._director import initialize_pot_director
from .pot.provider import PoTokenContext, PoTokenRequest
from ..openload import PhantomJSwrapper
from ...jsinterp import JSInterpreter, LocalNameSpace
from ...networking.exceptions import HTTPError
from ...utils import (
    NO_DEFAULT,
    ExtractorError,
    LazyList,
    bug_reports_message,
    clean_html,
    datetime_from_str,
    filesize_from_tbr,
    filter_dict,
    float_or_none,
    format_field,
    get_first,
    int_or_none,
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
    remove_end,
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
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urljoin,
    variadic,
)
from ...utils.networking import clean_headers, clean_proxies, select_proxy

STREAMING_DATA_CLIENT_NAME = '__yt_dlp_client'
STREAMING_DATA_FETCH_SUBS_PO_TOKEN = '__yt_dlp_fetch_subs_po_token'
STREAMING_DATA_FETCH_GVS_PO_TOKEN = '__yt_dlp_fetch_gvs_po_token'
STREAMING_DATA_PLAYER_TOKEN_PROVIDED = '__yt_dlp_player_token_provided'
STREAMING_DATA_INNERTUBE_CONTEXT = '__yt_dlp_innertube_context'
STREAMING_DATA_IS_PREMIUM_SUBSCRIBER = '__yt_dlp_is_premium_subscriber'

PO_TOKEN_GUIDE_URL = 'https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide'


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
        r'/s/player/(?P<id>[a-zA-Z0-9_-]{8,})/(?:tv-)?player',
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
    _SUBTITLE_FORMATS = ('json3', 'srv1', 'srv2', 'srv3', 'ttml', 'srt', 'vtt')
    _DEFAULT_CLIENTS = ('tv', 'ios', 'web')
    _DEFAULT_AUTHED_CLIENTS = ('tv', 'web')
    # Premium does not require POT (except for subtitles)
    _DEFAULT_PREMIUM_CLIENTS = ('tv', 'web')

    _GEO_BYPASS = False

    IE_NAME = 'youtube'
    _TESTS = [{
        'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&t=1s&end=9',
        'info_dict': {
            'id': 'BaW_jenozKc',
            'ext': 'mp4',
            'title': 'youtube-dl test video "\'/\\ä↭𝕐',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Science & Technology'],
            'channel': 'Philipp Hagemeister',
            'channel_follower_count': int,
            'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
            'channel_url': 'https://www.youtube.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
            'comment_count': int,
            'description': 'md5:8fb536f4877b8a7455c2ec23794dbc22',
            'duration': 10,
            'end_time': 9,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'playable_in_embed': True,
            'start_time': 1,
            'tags': 'count:1',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1349198244,
            'upload_date': '20121002',
            'uploader': 'Philipp Hagemeister',
            'uploader_id': '@PhilippHagemeister',
            'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
            'view_count': int,
        },
        'skip': 'Video unavailable',
    }, {
        'note': 'Embed-only video (#1746)',
        'url': '//www.YouTube.com/watch?v=yZIXLfi8CZQ',
        'info_dict': {
            'id': 'yZIXLfi8CZQ',
            'ext': 'mp4',
            'title': 'Principal Sexually Assaults A Teacher - Episode 117 - 8th June 2012',
            'age_limit': 18,
            'description': 'md5:09b78bd971f1e3e289601dfba15ca4f7',
            'upload_date': '20120608',
        },
        'skip': 'Private video',
    }, {
        'note': 'Use the first video ID in the URL',
        'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&v=yZIXLfi8CZQ',
        'info_dict': {
            'id': 'BaW_jenozKc',
            'ext': 'mp4',
            'title': 'youtube-dl test video "\'/\\ä↭𝕐',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Science & Technology'],
            'channel': 'Philipp Hagemeister',
            'channel_follower_count': int,
            'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
            'channel_url': 'https://www.youtube.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
            'comment_count': int,
            'description': 'md5:8fb536f4877b8a7455c2ec23794dbc22',
            'duration': 10,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'playable_in_embed': True,
            'tags': 'count:1',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1349198244,
            'upload_date': '20121002',
            'uploader': 'Philipp Hagemeister',
            'uploader_id': '@PhilippHagemeister',
            'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
            'view_count': int,
        },
        'skip': 'Video unavailable',
    }, {
        'note': '256k DASH audio (format 141) via DASH manifest',
        'url': 'https://www.youtube.com/watch?v=a9LDPn-MO4I',
        'info_dict': {
            'id': 'a9LDPn-MO4I',
            'ext': 'm4a',
            'title': 'UHDTV TEST 8K VIDEO.mp4',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Science & Technology'],
            'channel': '8KVIDEO',
            'channel_follower_count': int,
            'channel_id': 'UC8cn-cnCZ2FnxmjfkoLGpsQ',
            'channel_url': 'https://www.youtube.com/channel/UC8cn-cnCZ2FnxmjfkoLGpsQ',
            'comment_count': int,
            'description': '',
            'duration': 60,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:8',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1349185252,
            'upload_date': '20121002',
            'uploader': '8KVIDEO',
            'uploader_id': '@8KVIDEO',
            'uploader_url': 'https://www.youtube.com/@8KVIDEO',
            'view_count': int,
        },
        'params': {
            'format': '141',
            'skip_download': True,
            'youtube_include_dash_manifest': True,
        },
        'skip': 'format 141 not served anymore',
    }, {
        # DASH manifest with encrypted signature
        'url': 'https://www.youtube.com/watch?v=IB3lcPjvWLA',
        'info_dict': {
            'id': 'IB3lcPjvWLA',
            'ext': 'm4a',
            'title': 'Afrojack, Spree Wilson - The Spark (Official Music Video) ft. Spree Wilson',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'Afrojack',
            'channel_follower_count': int,
            'channel_id': 'UChuZAo1RKL85gev3Eal9_zg',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UChuZAo1RKL85gev3Eal9_zg',
            'comment_count': int,
            'description': 'md5:8f5e2b82460520b619ccac1f509d43bf',
            'duration': 244,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:19',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1381496404,
            'upload_date': '20131011',
            'uploader': 'Afrojack',
            'uploader_id': '@AfrojackVEVO',
            'uploader_url': 'https://www.youtube.com/@AfrojackVEVO',
            'view_count': int,
        },
        'params': {
            'format': '141/bestaudio[ext=m4a]',
            'skip_download': True,
            'youtube_include_dash_manifest': True,
        },
    }, {
        # Age-gated video
        # https://github.com/yt-dlp/yt-dlp/pull/575#issuecomment-888837000
        'note': 'Embed allowed age-gated video; works with web_embedded',
        'url': 'https://youtube.com/watch?v=HtVdAasjOgU',
        'info_dict': {
            'id': 'HtVdAasjOgU',
            'ext': 'mp4',
            'title': 'The Witcher 3: Wild Hunt - The Sword Of Destiny Trailer',
            'age_limit': 18,
            'availability': 'needs_auth',
            'categories': ['Gaming'],
            'channel': 'The Witcher',
            'channel_follower_count': int,
            'channel_id': 'UCzybXLxv08IApdjdN0mJhEg',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCzybXLxv08IApdjdN0mJhEg',
            'comment_count': int,
            'description': 'md5:595a43060c51c2a8cb61dd33c18e5fbd',
            'duration': 142,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:17',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1401991663,
            'upload_date': '20140605',
            'uploader': 'The Witcher',
            'uploader_id': '@thewitcher',
            'uploader_url': 'https://www.youtube.com/@thewitcher',
            'view_count': int,
        },
        'params': {'skip_download': True},
        'skip': 'Age-restricted; requires authentication',
    }, {
        'note': 'Formerly an age-gated video with embed allowed in public site',
        'url': 'https://youtube.com/watch?v=HsUATh_Nc2U',
        'info_dict': {
            'id': 'HsUATh_Nc2U',
            'ext': 'mp4',
            'title': 'Godzilla 2 (Official Video)',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'FlyingKitty',
            'channel_follower_count': int,
            'channel_id': 'UCYQT13AtrJC0gsM1far_zJg',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCYQT13AtrJC0gsM1far_zJg',
            'comment_count': int,
            'description': 'md5:bf77e03fcae5529475e500129b05668a',
            'duration': 177,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:2',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1586358900,
            'upload_date': '20200408',
            'uploader': 'FlyingKitty',
            'uploader_id': '@FlyingKitty900',
            'uploader_url': 'https://www.youtube.com/@FlyingKitty900',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        'note': 'Age-gated video embedable only with clientScreen=EMBED',
        'url': 'https://youtube.com/watch?v=Tq92D6wQ1mg',
        'info_dict': {
            'id': 'Tq92D6wQ1mg',
            'ext': 'mp4',
            'title': '[MMD] Adios - EVERGLOW [+Motion DL]',
            'age_limit': 18,
            'availability': 'needs_auth',
            'categories': ['Entertainment'],
            'channel': 'Projekt Melody',
            'channel_follower_count': int,
            'channel_id': 'UC1yoRdFoFJaCY-AGfD9W0wQ',
            'channel_url': 'https://www.youtube.com/channel/UC1yoRdFoFJaCY-AGfD9W0wQ',
            'comment_count': int,
            'description': 'md5:17eccca93a786d51bc67646756894066',
            'duration': 106,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:5',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1577508724,
            'upload_date': '20191228',
            'uploader': 'Projekt Melody',
            'uploader_id': '@ProjektMelody',
            'uploader_url': 'https://www.youtube.com/@ProjektMelody',
            'view_count': int,
        },
        'skip': 'Age-restricted; requires authentication',
    }, {
        'note': 'Non-age-gated non-embeddable video',
        'url': 'https://youtube.com/watch?v=MeJVWBSsPAY',
        'info_dict': {
            'id': 'MeJVWBSsPAY',
            'ext': 'mp4',
            'title': 'OOMPH! - Such Mich Find Mich (Lyrics)',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'Herr Lurik',
            'channel_follower_count': int,
            'channel_id': 'UCdR3RSDPqub28LjZx0v9-aA',
            'channel_url': 'https://www.youtube.com/channel/UCdR3RSDPqub28LjZx0v9-aA',
            'description': 'md5:205c1049102a4dffa61e4831c1f16851',
            'duration': 210,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': False,
            'tags': 'count:5',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1375214517,
            'upload_date': '20130730',
            'uploader': 'Herr Lurik',
            'uploader_id': '@HerrLurik',
            'uploader_url': 'https://www.youtube.com/@HerrLurik',
            'view_count': int,
        },
    }, {
        'note': 'Non-bypassable age-gated video',
        'url': 'https://youtube.com/watch?v=Cr381pDsSsA',
        'only_matching': True,
    }, {
        # video_info is None
        # https://github.com/ytdl-org/youtube-dl/issues/4421
        # YouTube Red ad is not captured for creator
        'url': '__2ABJjxzNo',
        'info_dict': {
            'id': '__2ABJjxzNo',
            'ext': 'mp4',
            'title': 'Deadmau5 - Some Chords (HD)',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'deadmau5',
            'channel_follower_count': int,
            'channel_id': 'UCYEK6xds6eo-3tr4xRdflmQ',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCYEK6xds6eo-3tr4xRdflmQ',
            'comment_count': int,
            'description': 'md5:c27e1e9e095a3d9dd99de2f0f377ba06',
            'duration': 266,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:14',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1272659179,
            'upload_date': '20100430',
            'uploader': 'deadmau5',
            'uploader_id': '@deadmau5',
            'uploader_url': 'https://www.youtube.com/@deadmau5',
            'view_count': int,
        },
        'expected_warnings': ['DASH manifest missing'],
        'params': {'skip_download': True},
    }, {
        # https://github.com/ytdl-org/youtube-dl/issues/4431
        'url': 'lqQg6PlCWgI',
        'info_dict': {
            'id': 'lqQg6PlCWgI',
            'ext': 'mp4',
            'title': 'Hockey - Women -  GER-AUS - London 2012 Olympic Games',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Sports'],
            'channel': 'Olympics',
            'channel_follower_count': int,
            'channel_id': 'UCTl3QQTvqHFjurroKxexy2Q',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCTl3QQTvqHFjurroKxexy2Q',
            'description': 'md5:04bbbf3ccceb6795947572ca36f45904',
            'duration': 6085,
            'like_count': int,
            'live_status': 'was_live',
            'media_type': 'livestream',
            'playable_in_embed': True,
            'release_date': '20120731',
            'release_timestamp': 1343767800,
            'tags': 'count:10',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1440707674,
            'upload_date': '20150827',
            'uploader': 'Olympics',
            'uploader_id': '@Olympics',
            'uploader_url': 'https://www.youtube.com/@Olympics',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # Non-square pixels
        'url': 'https://www.youtube.com/watch?v=_b-2C3KPAM0',
        'info_dict': {
            'id': '_b-2C3KPAM0',
            'ext': 'mp4',
            'title': '[A-made] 變態妍字幕版 太妍 我就是這樣的人',
            'age_limit': 0,
            'availability': 'unlisted',
            'categories': ['People & Blogs'],
            'channel': '孫ᄋᄅ',
            'channel_follower_count': int,
            'channel_id': 'UCS-xxCmRaA6BFdmgDPA_BIw',
            'channel_url': 'https://www.youtube.com/channel/UCS-xxCmRaA6BFdmgDPA_BIw',
            'comment_count': int,
            'description': 'md5:636f03cf211e7687daffe5bded88a94f',
            'duration': 85,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'stretched_ratio': 16 / 9.,
            'tags': 'count:11',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1299776999,
            'upload_date': '20110310',
            'uploader': '孫ᄋᄅ',
            'uploader_id': '@AllenMeow',
            'uploader_url': 'https://www.youtube.com/@AllenMeow',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # url_encoded_fmt_stream_map is empty string (deprecated)
        # https://github.com/ytdl-org/youtube-dl/commit/3a9fadd6dfc127ed0707b218b11ac10c654af1e2
        # https://github.com/ytdl-org/youtube-dl/commit/67299f23d8b1894120e875edf97440de87e22308
        'url': 'qEJwOuvDf7I',
        'only_matching': True,
    }, {
        # Extraction from multiple DASH manifests
        # https://github.com/ytdl-org/youtube-dl/pull/6097
        'url': 'https://www.youtube.com/watch?v=FIl7x6_3R5Y',
        'info_dict': {
            'id': 'FIl7x6_3R5Y',
            'ext': 'mp4',
            'title': '[60fps] 150614  마마무 솔라 \'Mr. 애매모호\' 라이브 직캠 @대학로 게릴라 콘서트',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['People & Blogs'],
            'channel': 'dorappi2000',
            'channel_follower_count': int,
            'channel_id': 'UCNlmrKRHLHcd2gq6LtPOTlQ',
            'channel_url': 'https://www.youtube.com/channel/UCNlmrKRHLHcd2gq6LtPOTlQ',
            'description': 'md5:116377fd2963b81ec4ce64b542173306',
            'duration': 220,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:12',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1435276932,
            'upload_date': '20150626',
            'uploader': 'dorappi2000',
            'uploader_id': '@dorappi2000',
            'uploader_url': 'https://www.youtube.com/@dorappi2000',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # DASH manifest with segment_list
        # https://github.com/ytdl-org/youtube-dl/pull/5886
        'url': 'https://www.youtube.com/embed/CsmdDsKjzN8',
        'info_dict': {
            'id': 'CsmdDsKjzN8',
            'ext': 'mp4',
            'title': 'Retransmisión XVIII Media maratón Zaragoza 2015',
            'age_limit': 0,
            'availability': 'unlisted',
            'categories': ['Sports'],
            'channel': 'Airtek | LED streaming',
            'channel_follower_count': int,
            'channel_id': 'UCzTzUmjXxxacNnL8I3m4LnQ',
            'channel_url': 'https://www.youtube.com/channel/UCzTzUmjXxxacNnL8I3m4LnQ',
            'comment_count': int,
            'description': 'md5:fcac84e6c545114766f670236fc10196',
            'duration': 4394,
            'like_count': int,
            'live_status': 'was_live',
            'media_type': 'livestream',
            'playable_in_embed': True,
            'release_date': '20150510',
            'release_timestamp': 1431241011,
            'tags': 'count:31',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1430505417,
            'upload_date': '20150501',
            'uploader': 'Airtek | LED streaming',
            'uploader_id': '@airtekledstreaming7916',
            'uploader_url': 'https://www.youtube.com/@airtekledstreaming7916',
            'view_count': int,
        },
        'params': {
            'format': '135',  # bestvideo
            'skip_download': True,
            'youtube_include_dash_manifest': True,
        },
    }, {
        # Multi-camera events (deprecated)
        # https://web.archive.org/web/20200308092705/https://support.google.com/youtube/answer/2853812
        'url': 'https://www.youtube.com/watch?v=zaPI8MvL8pg',
        'only_matching': True,
    }, {
        # Multi-camera events (deprecated)
        # https://github.com/ytdl-org/youtube-dl/issues/8536
        'url': 'https://www.youtube.com/watch?v=gVfLd0zydlo',
        'only_matching': True,
    }, {
        'url': 'https://vid.plus/FlRa-iH7PGw',
        'only_matching': True,
    }, {
        'url': 'https://zwearz.com/watch/9lWxNJF-ufM/electra-woman-dyna-girl-official-trailer-grace-helbig.html',
        'only_matching': True,
    }, {
        # Title with JS-like syntax "};"
        # https://github.com/ytdl-org/youtube-dl/issues/7468
        # Also tests cut-off URL expansion in video description
        # https://github.com/ytdl-org/youtube-dl/issues/1892
        # https://github.com/ytdl-org/youtube-dl/issues/8164
        'url': 'https://www.youtube.com/watch?v=lsguqyKfVQg',
        'info_dict': {
            'id': 'lsguqyKfVQg',
            'ext': 'mp4',
            'title': '{dark walk}; Loki/AC/Dishonored; collab w/Elflover21',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Film & Animation'],
            'channel': 'IronSoulElf',
            'channel_follower_count': int,
            'channel_id': 'UCTSRgz5jylBvFt_S7wnsqLQ',
            'channel_url': 'https://www.youtube.com/channel/UCTSRgz5jylBvFt_S7wnsqLQ',
            'comment_count': int,
            'description': 'md5:8085699c11dc3f597ce0410b0dcbb34a',
            'duration': 133,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:13',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1447959261,
            'upload_date': '20151119',
            'uploader': 'IronSoulElf',
            'uploader_id': '@IronSoulElf',
            'uploader_url': 'https://www.youtube.com/@IronSoulElf',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # Tags with '};'
        # https://github.com/ytdl-org/youtube-dl/issues/7468
        'url': 'https://www.youtube.com/watch?v=Ms7iBXnlUO8',
        'only_matching': True,
    }, {
        # Video with yt:stretch=17:0
        'url': 'https://www.youtube.com/watch?v=Q39EVAstoRM',
        'info_dict': {
            'id': 'Q39EVAstoRM',
            'ext': 'mp4',
            'title': 'Clash Of Clans#14 Dicas De Ataque Para CV 4',
            'description': 'md5:ee18a25c350637c8faff806845bddee9',
            'upload_date': '20151107',
        },
        'skip': 'This video does not exist.',
    }, {
        # Video with incomplete 'yt:stretch=16:'
        'url': 'https://www.youtube.com/watch?v=FRhJzUSJbGI',
        'only_matching': True,
    }, {
        # Video licensed under Creative Commons
        'url': 'https://www.youtube.com/watch?v=M4gD1WSo5mA',
        'info_dict': {
            'id': 'M4gD1WSo5mA',
            'ext': 'mp4',
            'title': 'William Fisher, CopyrightX: Lecture 3.2, The Subject Matter of Copyright: Drama and choreography',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Education'],
            'channel': 'The Berkman Klein Center for Internet & Society',
            'channel_follower_count': int,
            'channel_id': 'UCuLGmD72gJDBwmLw06X58SA',
            'channel_url': 'https://www.youtube.com/channel/UCuLGmD72gJDBwmLw06X58SA',
            'chapters': 'count:4',
            'description': 'md5:a677553cf0840649b731a3024aeff4cc',
            'duration': 721,
            'license': 'Creative Commons Attribution license (reuse allowed)',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:3',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1422422076,
            'upload_date': '20150128',
            'uploader': 'The Berkman Klein Center for Internet & Society',
            'uploader_id': '@BKCHarvard',
            'uploader_url': 'https://www.youtube.com/@BKCHarvard',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # https://github.com/ytdl-org/youtube-dl/commit/fd050249afce1bcc9e7f4a127069375467007b55
        'url': 'https://www.youtube.com/watch?v=eQcmzGIKrzg',
        'info_dict': {
            'id': 'eQcmzGIKrzg',
            'ext': 'mp4',
            'title': 'Democratic Socialism and Foreign Policy | Bernie Sanders',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['News & Politics'],
            'channel': 'Bernie Sanders',
            'channel_follower_count': int,
            'channel_id': 'UCH1dpzjCEiGAt8CXkryhkZg',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCH1dpzjCEiGAt8CXkryhkZg',
            'chapters': 'count:5',
            'comment_count': int,
            'description': 'md5:13a2503d7b5904ef4b223aa101628f39',
            'duration': 4060,
            'heatmap': 'count:100',
            'license': 'Creative Commons Attribution license (reuse allowed)',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:12',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1447987198,
            'upload_date': '20151120',
            'uploader': 'Bernie Sanders',
            'uploader_id': '@BernieSanders',
            'uploader_url': 'https://www.youtube.com/@BernieSanders',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.youtube.com/watch?feature=player_embedded&amp;amp;v=V36LpHqtcDY',
        'only_matching': True,
    }, {
        # YouTube Red paid video
        # https://github.com/ytdl-org/youtube-dl/issues/10059
        'url': 'https://www.youtube.com/watch?v=i1Ko8UG-Tdo',
        'only_matching': True,
    }, {
        # Rental video preview
        # https://github.com/ytdl-org/youtube-dl/commit/fd050249afce1bcc9e7f4a127069375467007b55
        'url': 'https://www.youtube.com/watch?v=yYr8q0y5Jfg',
        'info_dict': {
            'id': 'uGpuVWrhIzE',
            'ext': 'mp4',
            'title': 'Piku - Trailer',
            'description': 'md5:c36bd60c3fd6f1954086c083c72092eb',
            'upload_date': '20150811',
            'license': 'Standard YouTube License',
        },
        'skip': 'This video is not available.',
    }, {
        # YouTube Red video with episode data
        'url': 'https://www.youtube.com/watch?v=iqKdEhx-dD4',
        'info_dict': {
            'id': 'iqKdEhx-dD4',
            'ext': 'mp4',
            'title': 'Isolation - Mind Field (Ep 1)',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'Vsauce',
            'channel_follower_count': int,
            'channel_id': 'UC6nSFpj9HTCZ5t-N3Rm3-HA',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UC6nSFpj9HTCZ5t-N3Rm3-HA',
            'comment_count': int,
            'description': 'md5:f540112edec5d09fc8cc752d3d4ba3cd',
            'duration': 2085,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:12',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1484761047,
            'upload_date': '20170118',
            'uploader': 'Vsauce',
            'uploader_id': '@Vsauce',
            'uploader_url': 'https://www.youtube.com/@Vsauce',
            'view_count': int,
        },
        'expected_warnings': ['Skipping DASH manifest'],
        'params': {'skip_download': True},
    }, {
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
        'skip': 'This video has been removed for violating YouTube\'s policy on hate speech.',
    }, {
        # itag 212
        'url': '1t24XAntNCY',
        'only_matching': True,
    }, {
        # geo restricted to JP
        'url': 'sJL6WA-aGkQ',
        'only_matching': True,
    }, {
        'url': 'https://invidio.us/watch?v=BaW_jenozKc',
        'only_matching': True,
    }, {
        'url': 'https://redirect.invidious.io/watch?v=BaW_jenozKc',
        'only_matching': True,
    }, {
        # from https://nitter.pussthecat.org/YouTube/status/1360363141947944964#m
        'url': 'https://redirect.invidious.io/Yh0AhrY9GjA',
        'only_matching': True,
    }, {
        # DRM protected
        'url': 'https://www.youtube.com/watch?v=s7_qI6_mIXc',
        'only_matching': True,
    }, {
        # Video with unsupported adaptive stream type formats
        # https://github.com/ytdl-org/youtube-dl/commit/4fe54c128a11d394874505af75aaa5a2276aa3ba
        'url': 'https://www.youtube.com/watch?v=Z4Vy8R84T1U',
        'only_matching': True,
    }, {
        # Youtube Music Auto-generated description
        # TODO: fix metadata extraction
        # https://github.com/ytdl-org/youtube-dl/issues/20599
        'url': 'https://music.youtube.com/watch?v=MgNrAu2pzNs',
        'info_dict': {
            'id': 'MgNrAu2pzNs',
            'ext': 'mp4',
            'title': 'Voyeur Girl',
            'age_limit': 0,
            'album': 'it\'s too much love to know my dear',
            'alt_title': 'Voyeur Girl',
            'artists': ['Stephen'],
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'Stephen',  # TODO: should be 'Stephen - Topic'
            'channel_follower_count': int,
            'channel_id': 'UC-pWHpBjdGG69N9mM2auIAA',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UC-pWHpBjdGG69N9mM2auIAA',
            'comment_count': int,
            'creators': ['Stephen'],
            'description': 'md5:7ae382a65843d6df2685993e90a8628f',
            'duration': 169,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'release_date': '20190313',
            'tags': 'count:11',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1552385807,
            'track': 'Voyeur Girl',
            'upload_date': '20190312',
            'uploader': 'Stephen',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.youtubekids.com/watch?v=3b8nCWDgZ6Q',
        'only_matching': True,
    }, {
        # invalid -> valid video id redirection
        # https://github.com/ytdl-org/youtube-dl/pull/25063
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
        'skip': 'Video unavailable',
    }, {
        # empty description results in an empty string
        # https://github.com/ytdl-org/youtube-dl/pull/26575
        'url': 'https://www.youtube.com/watch?v=x41yOUIvK2k',
        'info_dict': {
            'id': 'x41yOUIvK2k',
            'ext': 'mp4',
            'title': 'IMG 3456',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Pets & Animals'],
            'channel': 'l\'Or Vert asbl',
            'channel_follower_count': int,
            'channel_id': 'UCo03ZQPBW5U4UC3regpt1nw',
            'channel_url': 'https://www.youtube.com/channel/UCo03ZQPBW5U4UC3regpt1nw',
            'description': '',
            'duration': 7,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': [],
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1497343210,
            'upload_date': '20170613',
            'uploader': 'l\'Or Vert asbl',
            'uploader_id': '@ElevageOrVert',
            'uploader_url': 'https://www.youtube.com/@ElevageOrVert',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # with '};' inside yt initial data (see [1])
        # see [2] for an example with '};' inside ytInitialPlayerResponse
        # 1. https://github.com/ytdl-org/youtube-dl/issues/27093
        # 2. https://github.com/ytdl-org/youtube-dl/issues/27216
        'url': 'https://www.youtube.com/watch?v=CHqg6qOn4no',
        'info_dict': {
            'id': 'CHqg6qOn4no',
            'ext': 'mp4',
            'title': 'Part 77   Sort a list of simple types in c#',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Education'],
            'channel': 'kudvenkat',
            'channel_follower_count': int,
            'channel_id': 'UCCTVrRB5KpIiK6V2GGVsR1Q',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCCTVrRB5KpIiK6V2GGVsR1Q',
            'chapters': 'count:4',
            'comment_count': int,
            'description': 'md5:b8746fa52e10cdbf47997903f13b20dc',
            'duration': 522,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:12',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1377976349,
            'upload_date': '20130831',
            'uploader': 'kudvenkat',
            'uploader_id': '@Csharp-video-tutorialsBlogspot',
            'uploader_url': 'https://www.youtube.com/@Csharp-video-tutorialsBlogspot',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # another example of '};' in ytInitialData
        'url': 'https://www.youtube.com/watch?v=gVfgbahppCY',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch_popup?v=63RmMXCd_bQ',
        'only_matching': True,
    }, {
        # https://github.com/ytdl-org/youtube-dl/pull/28094
        'url': 'OtqTfy26tG0',
        'info_dict': {
            'id': 'OtqTfy26tG0',
            'ext': 'mp4',
            'title': 'Burn Out',
            'age_limit': 0,
            'album': 'Every Day',
            'alt_title': 'Burn Out',
            'artists': ['The Cinematic Orchestra'],
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'The Cinematic Orchestra',
            'channel_follower_count': int,
            'channel_id': 'UCIzsJBIyo8hhpFm1NK0uLgw',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCIzsJBIyo8hhpFm1NK0uLgw',
            'comment_count': int,
            'creators': ['The Cinematic Orchestra'],
            'description': 'md5:fee8b19b7ba433cc2957d1c7582067ac',
            'duration': 614,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'release_date': '20020513',
            'release_year': 2023,
            'tags': 'count:3',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1416497379,
            'track': 'Burn Out',
            'upload_date': '20141120',
            'uploader': 'The Cinematic Orchestra',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # controversial video, only works with bpctr when authenticated with cookies
        'url': 'https://www.youtube.com/watch?v=nGC3D_FkCmg',
        'only_matching': True,
    }, {
        # controversial video, requires bpctr/contentCheckOk
        'url': 'https://www.youtube.com/watch?v=SZJvDhaSDnc',
        'info_dict': {
            'id': 'SZJvDhaSDnc',
            'ext': 'mp4',
            'title': 'San Diego teen commits suicide after bullying over embarrassing video',
            'age_limit': 18,
            'availability': 'needs_auth',
            'categories': ['News & Politics'],
            'channel': 'CBS Mornings',
            'channel_follower_count': int,
            'channel_id': 'UC-SJ6nODDmufqBzPBwCvYvQ',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UC-SJ6nODDmufqBzPBwCvYvQ',
            'comment_count': int,
            'description': 'md5:acde3a73d3f133fc97e837a9f76b53b7',
            'duration': 170,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:5',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1405513526,
            'upload_date': '20140716',
            'uploader': 'CBS Mornings',
            'uploader_id': '@CBSMornings',
            'uploader_url': 'https://www.youtube.com/@CBSMornings',
            'view_count': int,
        },
        'skip': 'Age-restricted; requires authentication',
    }, {
        # restricted location
        # https://github.com/ytdl-org/youtube-dl/issues/28685
        'url': 'cBvYw8_A0vQ',
        'info_dict': {
            'id': 'cBvYw8_A0vQ',
            'ext': 'mp4',
            'title': '4K Ueno Okachimachi  Street  Scenes  上野御徒町歩き',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Travel & Events'],
            'channel': 'Walk around Japan',
            'channel_follower_count': int,
            'channel_id': 'UC3o_t8PzBmXf5S9b7GLx1Mw',
            'channel_url': 'https://www.youtube.com/channel/UC3o_t8PzBmXf5S9b7GLx1Mw',
            'description': 'md5:ea770e474b7cd6722b4c95b833c03630',
            'duration': 1456,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:5',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1605884416,
            'upload_date': '20201120',
            'uploader': 'Walk around Japan',
            'uploader_id': '@walkaroundjapan7124',
            'uploader_url': 'https://www.youtube.com/@walkaroundjapan7124',
            'view_count': int,
        },
        'params': {'skip_download': True},
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
            'ext': '3gp',
            'title': 'DIGGING A SECRET TUNNEL Part 1',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'colinfurze',
            'channel_follower_count': int,
            'channel_id': 'UCp68_FLety0O-n9QU6phsgw',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCp68_FLety0O-n9QU6phsgw',
            'chapters': 'count:4',
            'comment_count': int,
            'description': 'md5:5d5991195d599b56cd0c4148907eec50',
            'duration': 596,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:6',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1624546829,
            'upload_date': '20210624',
            'uploader': 'colinfurze',
            'uploader_id': '@colinfurze',
            'uploader_url': 'https://www.youtube.com/@colinfurze',
            'view_count': int,
        },
        'params': {
            'extractor_args': {'youtube': {'player_client': ['android']}},
            'format': '17',  # 3gp format available on android
            'skip_download': True,
        },
        'skip': 'Android client broken',
    }, {
        # Skip download of additional client configs (remix client config in this case)
        'url': 'https://music.youtube.com/watch?v=MgNrAu2pzNs',
        'only_matching': True,
        'params': {'extractor_args': {'youtube': {'player_skip': ['configs']}}},
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
            'title': 'Your Brain is Plastic',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Education'],
            'channel': 'SciShow',
            'channel_follower_count': int,
            'channel_id': 'UCZYTClx2T1of7BRZ86-8fow',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCZYTClx2T1of7BRZ86-8fow',
            'chapters': 'count:5',
            'comment_count': int,
            'description': 'md5:89cd86034bdb5466cd87c6ba206cd2bc',
            'duration': 248,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:12',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1395685455,
            'upload_date': '20140324',
            'uploader': 'SciShow',
            'uploader_id': '@SciShow',
            'uploader_url': 'https://www.youtube.com/@SciShow',
            'view_count': int,
        },
        'params': {
            'format': 'mhtml',
            'skip_download': True,
        },
    }, {
        # Ensure video upload_date is in UTC timezone (video was uploaded 1641170939)
        'url': 'https://www.youtube.com/watch?v=2NUZ8W2llS4',
        'info_dict': {
            'id': '2NUZ8W2llS4',
            'ext': 'mp4',
            'title': 'The NP that test your phone performance 🙂',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Gaming'],
            'channel': 'Leon Nguyen',
            'channel_follower_count': int,
            'channel_id': 'UCRqNBSOHgilHfAczlUmlWHA',
            'channel_url': 'https://www.youtube.com/channel/UCRqNBSOHgilHfAczlUmlWHA',
            'comment_count': int,
            'description': 'md5:144494b24d4f9dfacb97c1bbef5de84d',
            'duration': 21,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:23',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1641170939,
            'upload_date': '20220103',
            'uploader': 'Leon Nguyen',
            'uploader_id': '@LeonNguyen',
            'uploader_url': 'https://www.youtube.com/@LeonNguyen',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # date text is premiered video, ensure upload date in UTC (published 1641172509)
        'url': 'https://www.youtube.com/watch?v=mzZzzBU6lrM',
        'info_dict': {
            'id': 'mzZzzBU6lrM',
            'ext': 'mp4',
            'title': 'I Met GeorgeNotFound In Real Life...',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'Quackity',
            'channel_follower_count': int,
            'channel_id': 'UC_8NknAFiyhOUaZqHR3lq3Q',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UC_8NknAFiyhOUaZqHR3lq3Q',
            'comment_count': int,
            'description': 'md5:42e72df3d4d5965903a2b9359c3ccd25',
            'duration': 955,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'release_date': '20220103',
            'release_timestamp': 1641172509,
            'tags': 'count:26',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1641172509,
            'upload_date': '20220103',
            'uploader': 'Quackity',
            'uploader_id': '@Quackity',
            'uploader_url': 'https://www.youtube.com/@Quackity',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # continuous livestream.
        # Upload date was 2022-07-12T05:12:29-07:00, while stream start is 2022-07-12T15:59:30+00:00
        'url': 'https://www.youtube.com/watch?v=jfKfPfyJRdk',
        'info_dict': {
            'id': 'jfKfPfyJRdk',
            'ext': 'mp4',
            'title': str,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'Lofi Girl',
            'channel_follower_count': int,
            'channel_id': 'UCSJ4gkVC6NrvII8umztf0Ow',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCSJ4gkVC6NrvII8umztf0Ow',
            'concurrent_view_count': int,
            'description': 'md5:48841fcfc1be6131d729fa7b4a7784cb',
            'like_count': int,
            'live_status': 'is_live',
            'media_type': 'livestream',
            'playable_in_embed': True,
            'release_date': '20220712',
            'release_timestamp': 1657641570,
            'tags': 'count:32',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1657627949,
            'upload_date': '20220712',
            'uploader': 'Lofi Girl',
            'uploader_id': '@LofiGirl',
            'uploader_url': 'https://www.youtube.com/@LofiGirl',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.youtube.com/watch?v=tjjjtzRLHvA',
        'info_dict': {
            'id': 'tjjjtzRLHvA',
            'ext': 'mp4',
            'title': 'ハッシュタグ無し };if window.ytcsi',
            'age_limit': 0,
            'availability': 'unlisted',
            'categories': ['Music'],
            'channel': 'Lesmiscore',
            'channel_follower_count': int,
            'channel_id': 'UCdqltm_7iv1Vs6kp6Syke5A',
            'channel_url': 'https://www.youtube.com/channel/UCdqltm_7iv1Vs6kp6Syke5A',
            'description': '',
            'duration': 6,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'short',
            'playable_in_embed': True,
            'tags': [],
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1648005313,
            'upload_date': '20220323',
            'uploader': 'Lesmiscore',
            'uploader_id': '@lesmiscore',
            'uploader_url': 'https://www.youtube.com/@lesmiscore',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # Prefer primary title+description language metadata by default
        # Do not prefer translated description if primary is empty
        'url': 'https://www.youtube.com/watch?v=el3E4MbxRqQ',
        'info_dict': {
            'id': 'el3E4MbxRqQ',
            'ext': 'mp4',
            'title': 'dlp test video 2 - primary sv no desc',
            'age_limit': 0,
            'availability': 'unlisted',
            'categories': ['People & Blogs'],
            'channel': 'cole-dlp-test-acc',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'description': '',
            'duration': 5,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': [],
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1662677394,
            'upload_date': '20220908',
            'uploader': 'cole-dlp-test-acc',
            'uploader_id': '@coletdjnz',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # Extractor argument: prefer translated title+description
        'url': 'https://www.youtube.com/watch?v=gHKT4uU8Zng',
        'info_dict': {
            'id': 'gHKT4uU8Zng',
            'ext': 'mp4',
            'title': 'dlp test video title primary (en-GB)',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['People & Blogs'],
            'channel': 'cole-dlp-test-acc',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'description': 'md5:e8c098ba19888e08554f960ffbf6f90e',
            'duration': 5,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': [],
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1659073275,
            'upload_date': '20220729',
            'uploader': 'cole-dlp-test-acc',
            'uploader_id': '@coletdjnz',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'view_count': int,
        },
        'params': {
            'extractor_args': {'youtube': {'lang': ['fr']}},
            'skip_download': True,
        },
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
            'title': 'Last To Take Hand Off Jet, Keeps It!',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'MrBeast',
            'channel_follower_count': int,
            'channel_id': 'UCX6OQ3DkcsbYNE6H8uQQuVA',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA',
            'comment_count': int,
            'description': 'md5:42731fced13eff2c48c099fbb5c1b3a0',
            'duration': 937,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': [],
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1668286800,
            'upload_date': '20221112',
            'uploader': 'MrBeast',
            'uploader_id': '@MrBeast',
            'uploader_url': 'https://www.youtube.com/@MrBeast',
            'view_count': int,
        },
        'params': {
            'extractor_args': {'youtube': {'player_client': ['ios']}},
            'format': '233-1',
            'skip_download': True,
        },
        'skip': 'PO Token Required',
    }, {
        'note': 'Audio formats with Dynamic Range Compression',
        'url': 'https://www.youtube.com/watch?v=Tq92D6wQ1mg',
        'info_dict': {
            'id': 'Tq92D6wQ1mg',
            'ext': 'webm',
            'title': '[MMD] Adios - EVERGLOW [+Motion DL]',
            'age_limit': 18,
            'availability': 'needs_auth',
            'categories': ['Entertainment'],
            'channel': 'Projekt Melody',
            'channel_follower_count': int,
            'channel_id': 'UC1yoRdFoFJaCY-AGfD9W0wQ',
            'channel_url': 'https://www.youtube.com/channel/UC1yoRdFoFJaCY-AGfD9W0wQ',
            'comment_count': int,
            'description': 'md5:17eccca93a786d51bc67646756894066',
            'duration': 106,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:5',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1577508724,
            'upload_date': '20191228',
            'uploader': 'Projekt Melody',
            'uploader_id': '@ProjektMelody',
            'uploader_url': 'https://www.youtube.com/@ProjektMelody',
            'view_count': int,
        },
        'params': {
            'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
            'format': '251-drc',
            'skip_download': True,
        },
        'skip': 'Age-restricted; requires authentication',
    }, {
        'note': 'Support /live/ URL + media type for post-live content',
        'url': 'https://www.youtube.com/live/qVv6vCqciTM',
        'info_dict': {
            'id': 'qVv6vCqciTM',
            'ext': 'mp4',
            'title': '【 #インターネット女クリスマス 】3Dで歌ってはしゃぐインターネットの女たち【月ノ美兎/名取さな】',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'さなちゃんねる',
            'channel_follower_count': int,
            'channel_id': 'UCIdEIHpS0TdkqRkHL5OkLtA',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCIdEIHpS0TdkqRkHL5OkLtA',
            'chapters': 'count:13',
            'comment_count': int,
            'description': 'md5:6aebf95cc4a1d731aebc01ad6cc9806d',
            'duration': 4438,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'was_live',
            'media_type': 'livestream',
            'playable_in_embed': True,
            'release_date': '20221223',
            'release_timestamp': 1671793345,
            'tags': 'count:6',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1671798112,
            'upload_date': '20221223',
            'uploader': 'さなちゃんねる',
            'uploader_id': '@sana_natori',
            'uploader_url': 'https://www.youtube.com/@sana_natori',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # Fallbacks when webpage and web client is unavailable
        'url': 'https://www.youtube.com/watch?v=wSSmNUl9Snw',
        'info_dict': {
            'id': 'wSSmNUl9Snw',
            'ext': 'webm',
            'title': 'The Computer Hack That Saved Apollo 14',
            'age_limit': 0,
            # 'availability': 'public',
            # 'categories': ['Science & Technology'],
            'channel': 'Scott Manley',
            'channel_follower_count': int,
            'channel_id': 'UCxzC4EngIsMrPmbm6Nxvb-A',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCxzC4EngIsMrPmbm6Nxvb-A',
            'chapters': 'count:2',
            'comment_count': int,
            'description': 'md5:f4bed7b200404b72a394c2f97b782c02',
            'duration': 682,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:8',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1504198713,
            'upload_date': '20170831',
            'uploader': 'Scott Manley',
            'uploader_id': '@scottmanley',
            'uploader_url': 'https://www.youtube.com/@scottmanley',
            'view_count': int,
        },
        'params': {
            'extractor_args': {'youtube': {
                'player_client': ['ios'],
                'player_skip': ['webpage'],
            }},
            'skip_download': True,
        },
        'skip': 'PO Token Required',
    }, {
        # uploader_id has non-ASCII characters that are percent-encoded in YT's JSON
        # https://github.com/yt-dlp/yt-dlp/pull/11818
        'url': 'https://www.youtube.com/shorts/18NGQq7p3LY',
        'info_dict': {
            'id': '18NGQq7p3LY',
            'ext': 'mp4',
            'title': '아이브 이서 장원영 리즈 삐끼삐끼 챌린지',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['People & Blogs'],
            'channel': 'ㅇㅇ',
            'channel_follower_count': int,
            'channel_id': 'UCC25oTm2J7ZVoi5TngOHg9g',
            'channel_url': 'https://www.youtube.com/channel/UCC25oTm2J7ZVoi5TngOHg9g',
            'description': '',
            'duration': 3,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'short',
            'playable_in_embed': True,
            'tags': [],
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1724306170,
            'upload_date': '20240822',
            'uploader': 'ㅇㅇ',
            'uploader_id': '@으아-v1k',
            'uploader_url': 'https://www.youtube.com/@으아-v1k',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }]
    _WEBPAGE_TESTS = [{
        # <object>
        # https://github.com/ytdl-org/youtube-dl/pull/12696
        'url': 'http://www.improbable.com/2017/04/03/untrained-modern-youths-and-ancient-masters-in-selfie-portraits/',
        'info_dict': {
            'id': 'msN87y-iEx0',
            'ext': 'mp4',
            'title': 'Feynman: Mirrors FUN TO IMAGINE 6',
            'upload_date': '20080526',
            'description': 'md5:873c81d308b979f0e23ee7e620b312a3',
            'age_limit': 0,
            'tags': 'count:8',
            'channel_id': 'UCCeo--lls1vna5YJABWAcVA',
            'playable_in_embed': True,
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
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
            'media_type': 'video',
        },
        'params': {'skip_download': True},
    }, {
        # <embed>
        # https://github.com/ytdl-org/youtube-dl/commit/2b88feedf7993c24b03e0a7ff169a548794de70c
        'url': 'https://badzine.de/news/als-marc-zwiebler-taufik-hidayat-schlug',
        'info_dict': {
            'id': 'bSVcWOq397g',
            'ext': 'mp4',
            'title': 'TAUFIK TUNJUKKAN KELASNYA !!! : Taufik Hidayat VS Marc Zwiebler Canada Open 2011',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Sports'],
            'channel': 'Badminton Addict Id',
            'channel_follower_count': int,
            'channel_id': 'UCfCpKOwQGUe2FUJzYNadQcQ',
            'channel_url': 'https://www.youtube.com/channel/UCfCpKOwQGUe2FUJzYNadQcQ',
            'comment_count': int,
            'description': 'md5:2c3737da9a575f301a8380b4d60592a8',
            'duration': 756,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:9',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1621418412,
            'upload_date': '20210519',
            'uploader': 'Badminton Addict Id',
            'uploader_id': '@badmintonaddictid8958',
            'uploader_url': 'https://www.youtube.com/@badmintonaddictid8958',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # WordPress Plugin: YouTube Video Importer
        # https://github.com/ytdl-org/youtube-dl/commit/7deef1ba6743bf11247565e63ed7e31d2e8a9382
        'url': 'https://lothype.com/2025-chino-hills-hs-snare-quad-features-wgi2025-drumline/',
        'info_dict': {
            'id': 'lC21AX_pCfA',
            'ext': 'mp4',
            'title': '2025 Chino Hills HS Snare & Quad Features! #wgi2025 #drumline',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Music'],
            'channel': 'DrumlineAV',
            'channel_follower_count': int,
            'channel_id': 'UCqdfUdyiQOZMvW5PcTTYikQ',
            'channel_url': 'https://www.youtube.com/channel/UCqdfUdyiQOZMvW5PcTTYikQ',
            'comment_count': int,
            'description': '',
            'duration': 48,
            'like_count': int,
            'live_status': 'not_live',
            'location': 'WESTMINSTER',
            'media_type': 'short',
            'playable_in_embed': True,
            'tags': 'count:72',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1739910835,
            'upload_date': '20250218',
            'uploader': 'DrumlineAV',
            'uploader_id': '@DrumlineAV',
            'uploader_url': 'https://www.youtube.com/@DrumlineAV',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # lazyYT
        # https://github.com/ytdl-org/youtube-dl/commit/65f3a228b16c55fee959eee055767a796479270f
        'url': 'https://rabota7.ru/%D0%91%D1%83%D1%85%D0%B3%D0%B0%D0%BB%D1%82%D0%B5%D1%80',
        'info_dict': {
            'id': 'DexR8_tTSsQ',
            'ext': 'mp4',
            'title': 'Работа бухгалтером в Москве',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['People & Blogs'],
            'channel': 'Работа в Москве свежие вакансии',
            'channel_follower_count': int,
            'channel_id': 'UCG3qz_gefGaMiSBvmaxN5WQ',
            'channel_url': 'https://www.youtube.com/channel/UCG3qz_gefGaMiSBvmaxN5WQ',
            'description': 'md5:b779d3d70af4efda26cf62b76808c0e3',
            'duration': 42,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:7',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1496398980,
            'upload_date': '20170602',
            'uploader': 'Работа в Москве свежие вакансии',
            'uploader_id': '@РаботавМосквесвежиевакансии',
            'uploader_url': 'https://www.youtube.com/@РаботавМосквесвежиевакансии',
            'view_count': int,
        },
        'params': {
            'extractor_args': {'generic': {'impersonate': ['chrome']}},
            'skip_download': True,
        },
    }, {
        # data-video-url=
        # https://github.com/ytdl-org/youtube-dl/pull/2948
        'url': 'https://www.uca.ac.uk/',
        'info_dict': {
            'id': 'www.uca.ac',
            'title': 'UCA | Creative Arts Degrees UK | University for the Creative Arts',
            'age_limit': 0,
            'description': 'md5:179c7a06ea1ed01b94ff5d56cb18d73b',
            'thumbnail': '/media/uca-2020/hero-headers/2025-prospectus-all-2x2.jpg',
        },
        'playlist_count': 10,
        'params': {'skip_download': True},
    }]

    _PLAYER_JS_VARIANT_MAP = {
        'main': 'player_ias.vflset/en_US/base.js',
        'tce': 'player_ias_tce.vflset/en_US/base.js',
        'tv': 'tv-player-ias.vflset/tv-player-ias.js',
        'tv_es6': 'tv-player-es6.vflset/tv-player-es6.js',
        'phone': 'player-plasma-ias-phone-en_US.vflset/base.js',
        'tablet': 'player-plasma-ias-tablet-en_US.vflset/base.js',
    }
    _INVERSE_PLAYER_JS_VARIANT_MAP = {v: k for k, v in _PLAYER_JS_VARIANT_MAP.items()}
    _NSIG_FUNC_CACHE_ID = 'nsig func'
    _DUMMY_STRING = 'dlp_wins'

    @classmethod
    def suitable(cls, url):
        from yt_dlp.utils import parse_qs

        qs = parse_qs(url)
        if qs.get('list', [None])[0]:
            return False
        return super().suitable(url)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._code_cache = {}
        self._player_cache = {}
        self._pot_director = None

    def _real_initialize(self):
        super()._real_initialize()
        self._pot_director = initialize_pot_director(self)

    def _prepare_live_from_start_formats(self, formats, video_id, live_start_time, url, webpage_url, smuggled_data, is_live):
        lock = threading.Lock()
        start_time = time.time()
        formats = [f for f in formats if f.get('is_from_start')]

        def refetch_manifest(format_id, delay):
            nonlocal formats, start_time, is_live
            if time.time() <= start_time + delay:
                return

            _, _, _, _, prs, player_url = self._initial_extract(
                url, smuggled_data, webpage_url, 'web', video_id)
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

                # Formats from ended premieres will be missing a manifest_url
                # See https://github.com/yt-dlp/yt-dlp/issues/8543
                if not f.get('manifest_url'):
                    break

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
            expire_fast = immediate or (last_error and isinstance(last_error, HTTPError) and last_error.status == 403)
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

        requested_js_variant = self._configuration_arg('player_js_variant', [''])[0] or 'actual'
        if requested_js_variant in self._PLAYER_JS_VARIANT_MAP:
            player_id = self._extract_player_info(player_url)
            original_url = player_url
            player_url = f'/s/player/{player_id}/{self._PLAYER_JS_VARIANT_MAP[requested_js_variant]}'
            if original_url != player_url:
                self.write_debug(
                    f'Forcing "{requested_js_variant}" player JS variant for player {player_id}\n'
                    f'        original url = {original_url}', only_once=True)
        elif requested_js_variant != 'actual':
            self.report_warning(
                f'Invalid player JS variant name "{requested_js_variant}" requested. '
                f'Valid choices are: {", ".join(self._PLAYER_JS_VARIANT_MAP)}', only_once=True)

        return urljoin('https://www.youtube.com', player_url)

    def _download_player_url(self, video_id, fatal=False):
        iframe_webpage = self._download_webpage_with_retries(
            'https://www.youtube.com/iframe_api',
            note='Downloading iframe API JS',
            video_id=video_id, retry_fatal=fatal)

        if iframe_webpage:
            player_version = self._search_regex(
                r'player\\?/([0-9a-fA-F]{8})\\?/', iframe_webpage, 'player version', fatal=fatal)
            if player_version:
                return f'https://www.youtube.com/s/player/{player_version}/player_ias.vflset/en_US/base.js'

    def _player_js_cache_key(self, player_url):
        player_id = self._extract_player_info(player_url)
        player_path = remove_start(urllib.parse.urlparse(player_url).path, f'/s/player/{player_id}/')
        variant = self._INVERSE_PLAYER_JS_VARIANT_MAP.get(player_path) or next((
            v for k, v in self._INVERSE_PLAYER_JS_VARIANT_MAP.items()
            if re.fullmatch(re.escape(k).replace('en_US', r'[a-zA-Z0-9_]+'), player_path)), None)
        if not variant:
            self.write_debug(
                f'Unable to determine player JS variant\n'
                f'        player = {player_url}', only_once=True)
            variant = re.sub(r'[^a-zA-Z0-9]', '_', remove_end(player_path, '.js'))
        return join_nonempty(player_id, variant)

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
        player_js_key = self._player_js_cache_key(player_url)
        if player_js_key not in self._code_cache:
            code = self._download_webpage(
                player_url, video_id, fatal=fatal,
                note=f'Downloading player {player_js_key}',
                errnote=f'Download of {player_js_key} failed')
            if code:
                self._code_cache[player_js_key] = code
        return self._code_cache.get(player_js_key)

    def _extract_signature_function(self, video_id, player_url, example_sig):
        # Read from filesystem cache
        func_id = join_nonempty(
            self._player_js_cache_key(player_url), self._signature_cache_id(example_sig))
        assert os.path.basename(func_id) == func_id

        self.write_debug(f'Extracting signature function {func_id}')
        cache_spec, code = self.cache.load('youtube-sigfuncs', func_id, min_ver='2025.07.21'), None

        if not cache_spec:
            code = self._load_player(video_id, player_url)
        if code:
            res = self._parse_sig_js(code, player_url)
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

    def _parse_sig_js(self, jscode, player_url):
        # Examples where `sig` is funcname:
        # sig=function(a){a=a.split(""); ... ;return a.join("")};
        # ;c&&(c=sig(decodeURIComponent(c)),a.set(b,encodeURIComponent(c)));return a};
        # {var l=f,m=h.sp,n=sig(decodeURIComponent(h.s));l.set(m,encodeURIComponent(n))}
        # sig=function(J){J=J.split(""); ... ;return J.join("")};
        # ;N&&(N=sig(decodeURIComponent(N)),J.set(R,encodeURIComponent(N)));return J};
        # {var H=u,k=f.sp,v=sig(decodeURIComponent(f.s));H.set(k,encodeURIComponent(v))}
        funcname = self._search_regex(
            (r'\b(?P<var>[a-zA-Z0-9_$]+)&&\((?P=var)=(?P<sig>[a-zA-Z0-9_$]{2,})\(decodeURIComponent\((?P=var)\)\)',
             r'(?P<sig>[a-zA-Z0-9_$]+)\s*=\s*function\(\s*(?P<arg>[a-zA-Z0-9_$]+)\s*\)\s*{\s*(?P=arg)\s*=\s*(?P=arg)\.split\(\s*""\s*\)\s*;\s*[^}]+;\s*return\s+(?P=arg)\.join\(\s*""\s*\)',
             r'(?:\b|[^a-zA-Z0-9_$])(?P<sig>[a-zA-Z0-9_$]{2,})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)(?:;[a-zA-Z0-9_$]{2}\.[a-zA-Z0-9_$]{2}\(a,\d+\))?',
             # Old patterns
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bm=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(h\.s\)\)',
             # Obsolete patterns
             r'("|\')signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(',
             r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\('),
            jscode, 'Initial JS player signature function name', group='sig')

        varname, global_list = self._interpret_player_js_global_var(jscode, player_url)
        jsi = JSInterpreter(jscode)
        initial_function = jsi.extract_function(funcname, filter_dict({varname: global_list}))
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

    def _load_player_data_from_cache(self, name, player_url):
        cache_id = (f'youtube-{name}', self._player_js_cache_key(player_url))

        if data := self._player_cache.get(cache_id):
            return data

        data = self.cache.load(*cache_id, min_ver='2025.07.21')
        if data:
            self._player_cache[cache_id] = data

        return data

    def _store_player_data_to_cache(self, name, player_url, data):
        cache_id = (f'youtube-{name}', self._player_js_cache_key(player_url))
        if cache_id not in self._player_cache:
            self.cache.store(*cache_id, data)
            self._player_cache[cache_id] = data

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
            extract_nsig = self._cached(self._extract_n_function_from_code, self._NSIG_FUNC_CACHE_ID, player_url)
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
        # Only cache nsig func JS code to disk if successful, and only once
        self._store_player_data_to_cache('nsig', player_url, func_code)
        return ret

    def _extract_n_function_name(self, jscode, player_url=None):
        varname, global_list = self._interpret_player_js_global_var(jscode, player_url)
        if debug_str := traverse_obj(global_list, (lambda _, v: v.endswith('-_w8_'), any)):
            pattern = r'''(?x)
                \{\s*return\s+%s\[%d\]\s*\+\s*(?P<argname>[a-zA-Z0-9_$]+)\s*\}
            ''' % (re.escape(varname), global_list.index(debug_str))
            if match := re.search(pattern, jscode):
                pattern = r'''(?x)
                    \{\s*\)%s\(\s*
                    (?:
                        (?P<funcname_a>[a-zA-Z0-9_$]+)\s*noitcnuf\s*
                        |noitcnuf\s*=\s*(?P<funcname_b>[a-zA-Z0-9_$]+)(?:\s+rav)?
                    )[;\n]
                ''' % re.escape(match.group('argname')[::-1])
                if match := re.search(pattern, jscode[match.start()::-1]):
                    a, b = match.group('funcname_a', 'funcname_b')
                    return (a or b)[::-1]
            self.write_debug(join_nonempty(
                'Initial search was unable to find nsig function name',
                player_url and f'        player = {player_url}', delim='\n'), only_once=True)

        # Examples (with placeholders nfunc, narray, idx):
        # *  .get("n"))&&(b=nfunc(b)
        # *  .get("n"))&&(b=narray[idx](b)
        # *  b=String.fromCharCode(110),c=a.get(b))&&c=narray[idx](c)
        # *  a.D&&(b="nn"[+a.D],c=a.get(b))&&(c=narray[idx](c),a.set(b,c),narray.length||nfunc("")
        # *  a.D&&(PL(a),b=a.j.n||null)&&(b=narray[0](b),a.set("n",b),narray.length||nfunc("")
        # *  a.D&&(b="nn"[+a.D],vL(a),c=a.j[b]||null)&&(c=narray[idx](c),a.set(b,c),narray.length||nfunc("")
        # *  J.J="";J.url="";J.Z&&(R="nn"[+J.Z],mW(J),N=J.K[R]||null)&&(N=narray[idx](N),J.set(R,N))}};
        funcname, idx = self._search_regex(
            r'''(?x)
            (?:
                \.get\("n"\)\)&&\(b=|
                (?:
                    b=String\.fromCharCode\(110\)|
                    (?P<str_idx>[a-zA-Z0-9_$.]+)&&\(b="nn"\[\+(?P=str_idx)\]
                )
                (?:
                    ,[a-zA-Z0-9_$]+\(a\))?,c=a\.
                    (?:
                        get\(b\)|
                        [a-zA-Z0-9_$]+\[b\]\|\|null
                    )\)&&\(c=|
                \b(?P<var>[a-zA-Z0-9_$]+)=
            )(?P<nfunc>[a-zA-Z0-9_$]+)(?:\[(?P<idx>\d+)\])?\([a-zA-Z]\)
            (?(var),[a-zA-Z0-9_$]+\.set\((?:"n+"|[a-zA-Z0-9_$]+)\,(?P=var)\))''',
            jscode, 'n function name', group=('nfunc', 'idx'), default=(None, None))
        if not funcname:
            self.report_warning(join_nonempty(
                'Falling back to generic n function search',
                player_url and f'         player = {player_url}', delim='\n'), only_once=True)
            return self._search_regex(
                r'''(?xs)
                ;\s*(?P<name>[a-zA-Z0-9_$]+)\s*=\s*function\([a-zA-Z0-9_$]+\)
                \s*\{(?:(?!};).)+?return\s*(?P<q>["'])[\w-]+_w8_(?P=q)\s*\+\s*[a-zA-Z0-9_$]+''',
                jscode, 'Initial JS player n function name', group='name')
        elif not idx:
            return funcname

        return json.loads(js_to_json(self._search_regex(
            rf'var {re.escape(funcname)}\s*=\s*(\[.+?\])\s*[,;]', jscode,
            f'Initial JS player n function list ({funcname}.{idx})')))[int(idx)]

    def _interpret_player_js_global_var(self, jscode, player_url):
        """Returns tuple of: variable name string, variable value list"""
        extract_global_var = self._cached(self._search_regex, 'js global array', player_url)
        varcode, varname, varvalue = extract_global_var(
            r'''(?x)
                (?P<q1>["\'])use\s+strict(?P=q1);\s*
                (?P<code>
                    var\s+(?P<name>[a-zA-Z0-9_$]+)\s*=\s*
                    (?P<value>
                        (?P<q2>["\'])(?:(?!(?P=q2)).|\\.)+(?P=q2)
                        \.split\((?P<q3>["\'])(?:(?!(?P=q3)).)+(?P=q3)\)
                        |\[\s*(?:(?P<q4>["\'])(?:(?!(?P=q4)).|\\.)*(?P=q4)\s*,?\s*)+\]
                    )
                )[;,]
            ''', jscode, 'global variable', group=('code', 'name', 'value'), default=(None, None, None))
        if not varcode:
            self.write_debug(join_nonempty(
                'No global array variable found in player JS',
                player_url and f'        player = {player_url}', delim='\n'), only_once=True)
            return None, None

        jsi = JSInterpreter(varcode)
        interpret_global_var = self._cached(jsi.interpret_expression, 'js global list', player_url)
        return varname, interpret_global_var(varvalue, LocalNameSpace(), allow_recursion=10)

    def _fixup_n_function_code(self, argnames, nsig_code, jscode, player_url):
        # Fixup global array
        varname, global_list = self._interpret_player_js_global_var(jscode, player_url)
        if varname and global_list:
            nsig_code = f'var {varname}={json.dumps(global_list)}; {nsig_code}'
        else:
            varname = self._DUMMY_STRING
            global_list = []

        # Fixup typeof check
        undefined_idx = global_list.index('undefined') if 'undefined' in global_list else r'\d+'
        fixed_code = re.sub(
            fr'''(?x)
                ;\s*if\s*\(\s*typeof\s+[a-zA-Z0-9_$]+\s*===?\s*(?:
                    (["\'])undefined\1|
                    {re.escape(varname)}\[{undefined_idx}\]
                )\s*\)\s*return\s+{re.escape(argnames[0])};
            ''', ';', nsig_code)
        if fixed_code == nsig_code:
            self.write_debug(join_nonempty(
                'No typeof statement found in nsig function code',
                player_url and f'        player = {player_url}', delim='\n'), only_once=True)

        # Fixup global funcs
        jsi = JSInterpreter(fixed_code)
        cache_id = (self._NSIG_FUNC_CACHE_ID, player_url)
        try:
            self._cached(
                self._extract_n_function_from_code, *cache_id)(jsi, (argnames, fixed_code))(self._DUMMY_STRING)
        except JSInterpreter.Exception:
            self._player_cache.pop(cache_id, None)

        global_funcnames = jsi._undefined_varnames
        debug_names = []
        jsi = JSInterpreter(jscode)
        for func_name in global_funcnames:
            try:
                func_args, func_code = jsi.extract_function_code(func_name)
                fixed_code = f'var {func_name} = function({", ".join(func_args)}) {{ {func_code} }}; {fixed_code}'
                debug_names.append(func_name)
            except Exception:
                self.report_warning(join_nonempty(
                    f'Unable to extract global nsig function {func_name} from player JS',
                    player_url and f'        player = {player_url}', delim='\n'), only_once=True)

        if debug_names:
            self.write_debug(f'Extracted global nsig functions: {", ".join(debug_names)}')

        return argnames, fixed_code

    def _extract_n_function_code(self, video_id, player_url):
        player_id = self._extract_player_info(player_url)
        func_code = self._load_player_data_from_cache('nsig', player_url)
        jscode = func_code or self._load_player(video_id, player_url)
        jsi = JSInterpreter(jscode)

        if func_code:
            return jsi, player_id, func_code

        func_name = self._extract_n_function_name(jscode, player_url=player_url)

        # XXX: Work around (a) global array variable, (b) `typeof` short-circuit, (c) global functions
        func_code = self._fixup_n_function_code(*jsi.extract_function_code(func_name), jscode, player_url)

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

            if ret.startswith('enhanced_except_') or ret.endswith(s):
                raise JSInterpreter.Exception('Signature function returned an exception')
            return ret

        return extract_nsig

    def _extract_signature_timestamp(self, video_id, player_url, ytcfg=None, fatal=False):
        """
        Extract signatureTimestamp (sts)
        Required to tell API what sig/player version is in use.
        """
        if sts := traverse_obj(ytcfg, ('STS', {int_or_none})):
            return sts

        if not player_url:
            error_msg = 'Cannot extract signature timestamp without player url'
            if fatal:
                raise ExtractorError(error_msg)
            self.report_warning(error_msg)
            return None

        sts = self._load_player_data_from_cache('sts', player_url)
        if sts:
            return sts

        if code := self._load_player(video_id, player_url, fatal=fatal):
            sts = int_or_none(self._search_regex(
                r'(?:signatureTimestamp|sts)\s*:\s*(?P<sts>[0-9]{5})', code,
                'JS player signature timestamp', group='sts', fatal=fatal))
            if sts:
                self._store_player_data_to_cache('sts', player_url, sts)

        return sts

    def _mark_watched(self, video_id, player_responses):
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join(CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(16))

        for is_full, key in enumerate(('videostatsPlaybackUrl', 'videostatsWatchtimeUrl')):
            label = 'fully ' if is_full else ''
            url = get_first(player_responses, ('playbackTracking', key, 'baseUrl'),
                            expected_type=url_or_none)
            if not url:
                self.report_warning(f'Unable to mark {label}watched')
                return
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)

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
                'start_time': ('startMillis', {float_or_none(scale=1000)}),
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
                ), {urljoin('https://www.youtube.com')}),
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

    def _get_config_po_token(self, client: str, context: _PoTokenContext):
        po_token_strs = self._configuration_arg('po_token', [], ie_key=YoutubeIE, casesense=True)
        for token_str in po_token_strs:
            po_token_meta, sep, po_token = token_str.partition('+')
            if not sep:
                self.report_warning(
                    f'Invalid po_token configuration format. '
                    f'Expected "CLIENT.CONTEXT+PO_TOKEN", got "{token_str}"', only_once=True)
                continue

            po_token_client, sep, po_token_context = po_token_meta.partition('.')
            if po_token_client.lower() != client:
                continue

            if not sep:
                # TODO(future): deprecate the old format?
                self.write_debug(
                    f'po_token configuration for {client} client is missing a context; assuming GVS. '
                    'You can provide a context with the format "CLIENT.CONTEXT+PO_TOKEN"',
                    only_once=True)
                po_token_context = _PoTokenContext.GVS.value

            if po_token_context.lower() != context.value:
                continue

            # Clean and validate the PO Token. This will strip invalid characters off
            # (e.g. additional url params the user may accidentally include)
            try:
                return base64.urlsafe_b64encode(base64.urlsafe_b64decode(urllib.parse.unquote(po_token))).decode()
            except (binascii.Error, ValueError):
                self.report_warning(
                    f'Invalid po_token configuration for {client} client: '
                    f'{po_token_context} PO Token should be a base64url-encoded string.',
                    only_once=True)
                continue

    def fetch_po_token(self, client='web', context: _PoTokenContext = _PoTokenContext.GVS, ytcfg=None, visitor_data=None,
                       data_sync_id=None, session_index=None, player_url=None, video_id=None, webpage=None,
                       required=False, **kwargs):
        """
        Fetch a PO Token for a given client and context. This function will validate required parameters for a given context and client.

        EXPERIMENTAL: This method is unstable and may change or be removed without notice.

        @param client: The client to fetch the PO Token for.
        @param context: The context in which the PO Token is used.
        @param ytcfg: The ytcfg for the client.
        @param visitor_data: visitor data.
        @param data_sync_id: data sync ID.
        @param session_index: session index.
        @param player_url: player URL.
        @param video_id: video ID.
        @param webpage: video webpage.
        @param required: Whether the PO Token is required (i.e. try to fetch unless policy is "never").
        @param kwargs: Additional arguments to pass down. May be more added in the future.
        @return: The fetched PO Token. None if it could not be fetched.
        """

        # TODO(future): This validation should be moved into pot framework.
        #  Some sort of middleware or validation provider perhaps?

        # GVS WebPO Token is bound to visitor_data / Visitor ID when logged out.
        # Must have visitor_data for it to function.
        if player_url and context == _PoTokenContext.GVS and not visitor_data and not self.is_authenticated:
            self.report_warning(
                f'Unable to fetch GVS PO Token for {client} client: Missing required Visitor Data. '
                f'You may need to pass Visitor Data with --extractor-args "youtube:visitor_data=XXX"')
            return

        if context == _PoTokenContext.PLAYER and not video_id:
            self.report_warning(
                f'Unable to fetch Player PO Token for {client} client: Missing required Video ID')
            return

        config_po_token = self._get_config_po_token(client, context)
        if config_po_token:
            # GVS WebPO token is bound to data_sync_id / account Session ID when logged in.
            if player_url and context == _PoTokenContext.GVS and not data_sync_id and self.is_authenticated:
                self.report_warning(
                    f'Got a GVS PO Token for {client} client, but missing Data Sync ID for account. Formats may not work.'
                    f'You may need to pass a Data Sync ID with --extractor-args "youtube:data_sync_id=XXX"')

            self.write_debug(f'{video_id}: Retrieved a {context.value} PO Token for {client} client from config')
            return config_po_token

        # Require GVS WebPO Token if logged in for external fetching
        if player_url and context == _PoTokenContext.GVS and not data_sync_id and self.is_authenticated:
            self.report_warning(
                f'Unable to fetch GVS PO Token for {client} client: Missing required Data Sync ID for account. '
                f'You may need to pass a Data Sync ID with --extractor-args "youtube:data_sync_id=XXX"')
            return

        po_token = self._fetch_po_token(
            client=client,
            context=context.value,
            ytcfg=ytcfg,
            visitor_data=visitor_data,
            data_sync_id=data_sync_id,
            session_index=session_index,
            player_url=player_url,
            video_id=video_id,
            video_webpage=webpage,
            required=required,
            **kwargs,
        )

        if po_token:
            self.write_debug(f'{video_id}: Retrieved a {context.value} PO Token for {client} client')
            return po_token

    def _fetch_po_token(self, client, **kwargs):
        context = kwargs.get('context')

        # Avoid fetching PO Tokens when not required
        fetch_pot_policy = self._configuration_arg('fetch_pot', [''], ie_key=YoutubeIE)[0]
        if fetch_pot_policy not in ('never', 'auto', 'always'):
            fetch_pot_policy = 'auto'
        if (
            fetch_pot_policy == 'never'
            or (
                fetch_pot_policy == 'auto'
                and not kwargs.get('required', False)
            )
        ):
            return None

        headers = self.get_param('http_headers').copy()
        proxies = self._downloader.proxies.copy()
        clean_headers(headers)
        clean_proxies(proxies, headers)

        innertube_host = self._select_api_hostname(None, default_client=client)

        pot_request = PoTokenRequest(
            context=PoTokenContext(context),
            innertube_context=traverse_obj(kwargs, ('ytcfg', 'INNERTUBE_CONTEXT')),
            innertube_host=innertube_host,
            internal_client_name=client,
            session_index=kwargs.get('session_index'),
            player_url=kwargs.get('player_url'),
            video_webpage=kwargs.get('video_webpage'),
            is_authenticated=self.is_authenticated,
            visitor_data=kwargs.get('visitor_data'),
            data_sync_id=kwargs.get('data_sync_id'),
            video_id=kwargs.get('video_id'),
            request_cookiejar=self._downloader.cookiejar,

            # All requests that would need to be proxied should be in the
            # context of www.youtube.com or the innertube host
            request_proxy=(
                select_proxy('https://www.youtube.com', proxies)
                or select_proxy(f'https://{innertube_host}', proxies)
            ),
            request_headers=headers,
            request_timeout=self.get_param('socket_timeout'),
            request_verify_tls=not self.get_param('nocheckcertificate'),
            request_source_address=self.get_param('source_address'),

            bypass_cache=False,
        )

        return self._pot_director.get_po_token(pot_request)

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

    def _extract_player_response(self, client, video_id, webpage_ytcfg, player_ytcfg, player_url, initial_pr, visitor_data, data_sync_id, po_token):
        headers = self.generate_api_headers(
            ytcfg=player_ytcfg,
            default_client=client,
            visitor_data=visitor_data,
            session_index=self._extract_session_index(webpage_ytcfg, player_ytcfg),
            delegated_session_id=(
                self._parse_data_sync_id(data_sync_id)[0]
                or self._extract_delegated_session_id(webpage_ytcfg, initial_pr, player_ytcfg)
            ),
            user_session_id=(
                self._parse_data_sync_id(data_sync_id)[1]
                or self._extract_user_session_id(webpage_ytcfg, initial_pr, player_ytcfg)
            ),
        )

        yt_query = {
            'videoId': video_id,
        }

        default_pp = traverse_obj(
            INNERTUBE_CLIENTS, (_split_innertube_client(client)[0], 'PLAYER_PARAMS', {str}))
        if player_params := self._configuration_arg('player_params', [default_pp], casesense=True)[0]:
            yt_query['params'] = player_params

        if po_token:
            yt_query['serviceIntegrityDimensions'] = {'poToken': po_token}

        sts = self._extract_signature_timestamp(video_id, player_url, webpage_ytcfg, fatal=False) if player_url else None
        yt_query.update(self._generate_player_context(sts))
        return self._extract_response(
            item_id=video_id, ep='player', query=yt_query,
            ytcfg=player_ytcfg, headers=headers, fatal=True,
            default_client=client,
            note='Downloading {} player API JSON'.format(client.replace('_', ' ').strip()),
        ) or None

    def _get_requested_clients(self, url, smuggled_data, is_premium_subscriber):
        requested_clients = []
        excluded_clients = []
        default_clients = (
            self._DEFAULT_PREMIUM_CLIENTS if is_premium_subscriber
            else self._DEFAULT_AUTHED_CLIENTS if self.is_authenticated
            else self._DEFAULT_CLIENTS
        )
        allowed_clients = sorted(
            (client for client in INNERTUBE_CLIENTS if client[:1] != '_'),
            key=lambda client: INNERTUBE_CLIENTS[client]['priority'], reverse=True)
        for client in self._configuration_arg('player_client'):
            if client == 'default':
                requested_clients.extend(default_clients)
            elif client == 'all':
                requested_clients.extend(allowed_clients)
            elif client.startswith('-'):
                excluded_clients.append(client[1:])
            elif client not in allowed_clients:
                self.report_warning(f'Skipping unsupported client "{client}"')
            else:
                requested_clients.append(client)
        if not requested_clients:
            requested_clients.extend(default_clients)
        for excluded_client in excluded_clients:
            if excluded_client in requested_clients:
                requested_clients.remove(excluded_client)
        if not requested_clients:
            raise ExtractorError('No player clients have been requested', expected=True)

        if self.is_authenticated:
            if (smuggled_data.get('is_music_url') or self.is_music_url(url)) and 'web_music' not in requested_clients:
                requested_clients.append('web_music')

            unsupported_clients = [
                client for client in requested_clients if not INNERTUBE_CLIENTS[client]['SUPPORTS_COOKIES']
            ]
            for client in unsupported_clients:
                self.report_warning(f'Skipping client "{client}" since it does not support cookies', only_once=True)
                requested_clients.remove(client)

        return orderedSet(requested_clients)

    def _invalid_player_response(self, pr, video_id):
        # YouTube may return a different video player response than expected.
        # See: https://github.com/TeamNewPipe/NewPipe/issues/8713
        if (pr_id := traverse_obj(pr, ('videoDetails', 'videoId'))) != video_id:
            return pr_id

    def _extract_player_responses(self, clients, video_id, webpage, webpage_client, webpage_ytcfg, is_premium_subscriber):
        initial_pr = None
        if webpage:
            initial_pr = self._search_json(
                self._YT_INITIAL_PLAYER_RESPONSE_RE, webpage,
                f'{webpage_client} client initial player response', video_id, fatal=False)

        prs = []
        deprioritized_prs = []

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
        player_url = visitor_data = data_sync_id = None
        skipped_clients = {}
        while clients:
            deprioritize_pr = False
            client, base_client, variant = _split_innertube_client(clients.pop())
            player_ytcfg = webpage_ytcfg if client == webpage_client else {}
            if 'configs' not in self._configuration_arg('player_skip') and client != webpage_client:
                player_ytcfg = self._download_ytcfg(client, video_id) or player_ytcfg

            player_url = player_url or self._extract_player_url(webpage_ytcfg, player_ytcfg, webpage=webpage)
            require_js_player = self._get_default_ytcfg(client).get('REQUIRE_JS_PLAYER')
            if 'js' in self._configuration_arg('player_skip'):
                require_js_player = False
                player_url = None

            if not player_url and not tried_iframe_fallback and require_js_player:
                player_url = self._download_player_url(video_id)
                tried_iframe_fallback = True

            pr = None
            if client == webpage_client and 'player_response' not in self._configuration_arg('webpage_skip'):
                pr = initial_pr

            visitor_data = visitor_data or self._extract_visitor_data(webpage_ytcfg, initial_pr, player_ytcfg)
            data_sync_id = data_sync_id or self._extract_data_sync_id(webpage_ytcfg, initial_pr, player_ytcfg)

            fetch_po_token_args = {
                'client': client,
                'visitor_data': visitor_data,
                'video_id': video_id,
                'data_sync_id': data_sync_id if self.is_authenticated else None,
                'player_url': player_url if require_js_player else None,
                'webpage': webpage,
                'session_index': self._extract_session_index(webpage_ytcfg, player_ytcfg),
                'ytcfg': player_ytcfg or self._get_default_ytcfg(client),
            }

            # Don't need a player PO token for WEB if using player response from webpage
            player_pot_policy: PlayerPoTokenPolicy = self._get_default_ytcfg(client)['PLAYER_PO_TOKEN_POLICY']
            player_po_token = None if pr else self.fetch_po_token(
                context=_PoTokenContext.PLAYER, **fetch_po_token_args,
                required=player_pot_policy.required or player_pot_policy.recommended)

            fetch_gvs_po_token_func = functools.partial(
                self.fetch_po_token, context=_PoTokenContext.GVS, **fetch_po_token_args)

            fetch_subs_po_token_func = functools.partial(
                self.fetch_po_token, context=_PoTokenContext.SUBS, **fetch_po_token_args)

            try:
                pr = pr or self._extract_player_response(
                    client, video_id,
                    webpage_ytcfg=player_ytcfg or webpage_ytcfg,
                    player_ytcfg=player_ytcfg,
                    player_url=player_url,
                    initial_pr=initial_pr,
                    visitor_data=visitor_data,
                    data_sync_id=data_sync_id,
                    po_token=player_po_token)
            except ExtractorError as e:
                self.report_warning(e)
                continue

            if pr_id := self._invalid_player_response(pr, video_id):
                skipped_clients[client] = pr_id
            elif pr:
                # Save client details for introspection later
                innertube_context = traverse_obj(player_ytcfg or self._get_default_ytcfg(client), 'INNERTUBE_CONTEXT')
                sd = pr.setdefault('streamingData', {})
                sd[STREAMING_DATA_CLIENT_NAME] = client
                sd[STREAMING_DATA_FETCH_GVS_PO_TOKEN] = fetch_gvs_po_token_func
                sd[STREAMING_DATA_PLAYER_TOKEN_PROVIDED] = bool(player_po_token)
                sd[STREAMING_DATA_INNERTUBE_CONTEXT] = innertube_context
                sd[STREAMING_DATA_FETCH_SUBS_PO_TOKEN] = fetch_subs_po_token_func
                sd[STREAMING_DATA_IS_PREMIUM_SUBSCRIBER] = is_premium_subscriber
                for f in traverse_obj(sd, (('formats', 'adaptiveFormats'), ..., {dict})):
                    f[STREAMING_DATA_CLIENT_NAME] = client
                    f[STREAMING_DATA_FETCH_GVS_PO_TOKEN] = fetch_gvs_po_token_func
                    f[STREAMING_DATA_IS_PREMIUM_SUBSCRIBER] = is_premium_subscriber
                    f[STREAMING_DATA_PLAYER_TOKEN_PROVIDED] = bool(player_po_token)
                if deprioritize_pr:
                    deprioritized_prs.append(pr)
                else:
                    prs.append(pr)

            # web_embedded can work around age-gate and age-verification for some embeddable videos
            if self._is_agegated(pr) and variant != 'web_embedded':
                append_client(f'web_embedded.{base_client}')
            # Unauthenticated users will only get web_embedded client formats if age-gated
            if self._is_agegated(pr) and not self.is_authenticated:
                self.to_screen(
                    f'{video_id}: This video is age-restricted; some formats may be missing '
                    f'without authentication. {self._youtube_login_hint}', only_once=True)

            # EU countries require age-verification for accounts to access age-restricted videos
            # If account is not age-verified, _is_agegated() will be truthy for non-embedded clients
            embedding_is_disabled = variant == 'web_embedded' and self._is_unplayable(pr)
            if self.is_authenticated and (self._is_agegated(pr) or embedding_is_disabled):
                self.to_screen(
                    f'{video_id}: This video is age-restricted and YouTube is requiring '
                    'account age-verification; some formats may be missing', only_once=True)
                # tv_embedded can work around the age-verification requirement for embeddable videos
                # web_creator may work around age-verification for all videos but requires PO token
                append_client('tv_embedded', 'web_creator')

            status = traverse_obj(pr, ('playabilityStatus', 'status', {str}))
            if status not in ('OK', 'LIVE_STREAM_OFFLINE', 'AGE_CHECK_REQUIRED', 'AGE_VERIFICATION_REQUIRED'):
                self.write_debug(f'{video_id}: {client} player response playability status: {status}')

        prs.extend(deprioritized_prs)

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
        if ((live_status == 'is_live' and self.get_param('live_from_start'))
                or (live_status == 'post_live' and (duration or 0) > 2 * 3600)):
            return live_status

    def _report_pot_format_skipped(self, video_id, client_name, proto):
        msg = (
            f'{video_id}: {client_name} client {proto} formats require a GVS PO Token which was not provided. '
            'They will be skipped as they may yield HTTP Error 403. '
            f'You can manually pass a GVS PO Token for this client with --extractor-args "youtube:po_token={client_name}.gvs+XXX". '
            f'For more information, refer to  {PO_TOKEN_GUIDE_URL} . '
            'To enable these broken formats anyway, pass --extractor-args "youtube:formats=missing_pot"')

        # Only raise a warning for non-default clients, to not confuse users.
        # iOS HLS formats still work without PO Token, so we don't need to warn about them.
        if client_name in (*self._DEFAULT_CLIENTS, *self._DEFAULT_AUTHED_CLIENTS):
            self.write_debug(msg, only_once=True)
        else:
            self.report_warning(msg, only_once=True)

    def _report_pot_subtitles_skipped(self, video_id, client_name, msg=None):
        msg = msg or (
            f'{video_id}: Some {client_name} client subtitles require a PO Token which was not provided. '
            'They will be discarded since they are not downloadable as-is. '
            f'You can manually pass a Subtitles PO Token for this client with '
            f'--extractor-args "youtube:po_token={client_name}.subs+XXX" . '
            f'For more information, refer to  {PO_TOKEN_GUIDE_URL}')

        subs_wanted = any((
            self.get_param('writesubtitles'),
            self.get_param('writeautomaticsub'),
            self.get_param('listsubtitles')))

        # Only raise a warning for non-default clients, to not confuse users.
        if not subs_wanted or client_name in (*self._DEFAULT_CLIENTS, *self._DEFAULT_AUTHED_CLIENTS):
            self.write_debug(msg, only_once=True)
        else:
            self.report_warning(msg, only_once=True)

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

        def gvs_pot_required(policy, is_premium_subscriber, has_player_token):
            return (
                policy.required
                and not (policy.not_required_with_player_token and has_player_token)
                and not (policy.not_required_for_premium and is_premium_subscriber))

        # save pots per client to avoid fetching again
        gvs_pots = {}

        for fmt in streaming_formats:
            client_name = fmt[STREAMING_DATA_CLIENT_NAME]
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

            display_name = audio_track.get('displayName') or ''
            is_original = 'original' in display_name.lower()
            is_descriptive = 'descriptive' in display_name.lower()
            is_default = audio_track.get('audioIsDefault')
            language_code = audio_track.get('id', '').split('.')[0]
            if language_code and (is_original or (is_default and not original_language)):
                original_language = language_code

            has_drm = bool(fmt.get('drmFamilies'))

            # FORMAT_STREAM_TYPE_OTF(otf=1) requires downloading the init fragment
            # (adding `&sq=0` to the URL) and parsing emsg box to determine the
            # number of fragment that would subsequently requested with (`&sq=N`)
            if fmt.get('type') == 'FORMAT_STREAM_TYPE_OTF' and not has_drm:
                continue

            if has_drm:
                msg = f'Some {client_name} client https formats have been skipped as they are DRM protected. '
                if client_name == 'tv':
                    msg += (
                        f'{"Your account" if self.is_authenticated else "The current session"} may have '
                        f'an experiment that applies DRM to all videos on the tv client. '
                        f'See  https://github.com/yt-dlp/yt-dlp/issues/12563  for more details.'
                    )
                self.report_warning(msg, video_id, only_once=True)

            fmt_url = fmt.get('url')
            if not fmt_url:
                sc = urllib.parse.parse_qs(fmt.get('signatureCipher'))
                fmt_url = url_or_none(try_get(sc, lambda x: x['url'][0]))
                encrypted_sig = try_get(sc, lambda x: x['s'][0])
                if not all((sc, fmt_url, player_url, encrypted_sig)):
                    msg = f'Some {client_name} client https formats have been skipped as they are missing a url. '
                    if client_name in ('web', 'web_safari'):
                        msg += 'YouTube is forcing SABR streaming for this client. '
                    else:
                        msg += (
                            f'YouTube may have enabled the SABR-only or Server-Side Ad Placement experiment for '
                            f'{"your account" if self.is_authenticated else "the current session"}. '
                        )
                    msg += 'See  https://github.com/yt-dlp/yt-dlp/issues/12482  for more details'
                    self.report_warning(msg, video_id, only_once=True)
                    continue
                try:
                    fmt_url += '&{}={}'.format(
                        traverse_obj(sc, ('sp', -1)) or 'signature',
                        self._decrypt_signature(encrypted_sig, video_id, player_url),
                    )
                except ExtractorError as e:
                    self.report_warning(
                        f'Signature extraction failed: Some formats may be missing\n'
                        f'         player = {player_url}\n'
                        f'         {bug_reports_message(before="")}',
                        video_id=video_id, only_once=True)
                    self.write_debug(
                        f'{video_id}: Signature extraction failure info:\n'
                        f'         encrypted sig = {encrypted_sig}\n'
                        f'         player = {player_url}')
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
                    if player_url:
                        self.report_warning(
                            f'nsig extraction failed: Some formats may be missing\n'
                            f'         n = {query["n"][0]} ; player = {player_url}\n'
                            f'         {bug_reports_message(before="")}',
                            video_id=video_id, only_once=True)
                        self.write_debug(e, only_once=True)
                    else:
                        self.report_warning(
                            'Cannot decrypt nsig without player_url: Some formats may be missing',
                            video_id=video_id, only_once=True)
                    continue

            tbr = float_or_none(fmt.get('averageBitrate') or fmt.get('bitrate'), 1000)
            format_duration = traverse_obj(fmt, ('approxDurationMs', {float_or_none(scale=1000)}))
            # Some formats may have much smaller duration than others (possibly damaged during encoding)
            # E.g. 2-nOtRESiUc Ref: https://github.com/yt-dlp/yt-dlp/issues/2823
            # Make sure to avoid false positives with small duration differences.
            # E.g. __2ABJjxzNo, ySuUZEjARPY
            is_damaged = try_call(lambda: format_duration < duration // 2)
            if is_damaged:
                self.report_warning(
                    'Some formats are possibly damaged. They will be deprioritized', video_id, only_once=True)

            fetch_po_token_func = fmt[STREAMING_DATA_FETCH_GVS_PO_TOKEN]
            pot_policy: GvsPoTokenPolicy = self._get_default_ytcfg(client_name)['GVS_PO_TOKEN_POLICY'][StreamingProtocol.HTTPS]

            require_po_token = (
                itag not in ['18']
                and gvs_pot_required(
                    pot_policy, fmt[STREAMING_DATA_IS_PREMIUM_SUBSCRIBER],
                    fmt[STREAMING_DATA_PLAYER_TOKEN_PROVIDED]))

            po_token = (
                gvs_pots.get(client_name)
                or fetch_po_token_func(required=require_po_token or pot_policy.recommended))

            if po_token:
                fmt_url = update_url_query(fmt_url, {'pot': po_token})
                if client_name not in gvs_pots:
                    gvs_pots[client_name] = po_token

            if not po_token and require_po_token and 'missing_pot' not in self._configuration_arg('formats'):
                self._report_pot_format_skipped(video_id, client_name, 'https')
                continue

            name = fmt.get('qualityLabel') or quality.replace('audio_quality_', '') or ''
            fps = int_or_none(fmt.get('fps')) or 0
            dct = {
                'asr': int_or_none(fmt.get('audioSampleRate')),
                'filesize': int_or_none(fmt.get('contentLength')),
                'format_id': f'{itag}{"-drc" if fmt.get("isDrc") else ""}',
                'format_note': join_nonempty(
                    join_nonempty(display_name, is_default and ' (default)', delim=''),
                    name, fmt.get('isDrc') and 'DRC',
                    try_get(fmt, lambda x: x['projectionType'].replace('RECTANGULAR', '').lower()),
                    try_get(fmt, lambda x: x['spatialAudioType'].replace('SPATIAL_AUDIO_TYPE_', '').lower()),
                    is_damaged and 'DAMAGED', require_po_token and not po_token and 'MISSING POT',
                    (self.get_param('verbose') or all_formats) and short_client_name(client_name),
                    delim=', '),
                # Format 22 is likely to be damaged. See https://github.com/yt-dlp/yt-dlp/issues/3372
                'source_preference': (-5 if itag == '22' else -1) + (100 if 'Premium' in name else 0),
                'fps': fps if fps > 1 else None,  # For some formats, fps is wrongly returned as 1
                'audio_channels': fmt.get('audioChannels'),
                'height': height,
                'quality': q(quality) - bool(fmt.get('isDrc')) / 2,
                'has_drm': has_drm,
                'tbr': tbr,
                'filesize_approx': filesize_from_tbr(tbr, format_duration),
                'url': fmt_url,
                'width': int_or_none(fmt.get('width')),
                'language': join_nonempty(language_code, 'desc' if is_descriptive else '') or None,
                'language_preference': PREFERRED_LANG_VALUE if is_original else 5 if is_default else -10 if is_descriptive else -1,
                # Strictly de-prioritize damaged and 3gp formats
                'preference': -10 if is_damaged else -2 if itag == '17' else None,
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
                or (needs_live_processing and skip_bad_formats)):
            skip_manifests.add('hls')

        if not self.get_param('youtube_include_dash_manifest', True):
            skip_manifests.add('dash')
        if self._configuration_arg('include_live_dash'):
            self._downloader.deprecated_feature('[youtube] include_live_dash extractor argument is deprecated. '
                                                'Use formats=incomplete extractor argument instead')
        elif skip_bad_formats and live_status == 'is_live' and needs_live_processing != 'is_live':
            skip_manifests.add('dash')

        def process_manifest_format(f, proto, client_name, itag, missing_pot):
            key = (proto, f.get('language'))
            if not all_formats and key in itags[itag]:
                return False

            if f.get('source_preference') is None:
                f['source_preference'] = -1

            if missing_pot:
                f['format_note'] = join_nonempty(f.get('format_note'), 'MISSING POT', delim=' ')
                f['source_preference'] -= 20

            # XXX: Check if IOS HLS formats are affected by PO token enforcement; temporary
            # See https://github.com/yt-dlp/yt-dlp/issues/13511
            if proto == 'hls' and client_name == 'ios':
                f['__needs_testing'] = True

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

            if itag in ('616', '235'):
                f['format_note'] = join_nonempty(f.get('format_note'), 'Premium', delim=' ')
                f['source_preference'] += 100

            f['quality'] = q(itag_qualities.get(try_get(f, lambda f: f['format_id'].split('-')[0]), -1))
            if f['quality'] == -1 and f.get('height'):
                f['quality'] = q(res_qualities[min(res_qualities, key=lambda x: abs(x - f['height']))])
            if self.get_param('verbose') or all_formats:
                f['format_note'] = join_nonempty(
                    f.get('format_note'), short_client_name(client_name), delim=', ')
            if f.get('fps') and f['fps'] <= 1:
                del f['fps']

            if proto == 'hls' and f.get('has_drm'):
                f['has_drm'] = 'maybe'
                f['source_preference'] -= 5
            return True

        subtitles = {}
        for sd in streaming_data:
            client_name = sd[STREAMING_DATA_CLIENT_NAME]
            fetch_pot_func = sd[STREAMING_DATA_FETCH_GVS_PO_TOKEN]
            is_premium_subscriber = sd[STREAMING_DATA_IS_PREMIUM_SUBSCRIBER]
            has_player_token = sd[STREAMING_DATA_PLAYER_TOKEN_PROVIDED]

            hls_manifest_url = 'hls' not in skip_manifests and sd.get('hlsManifestUrl')
            if hls_manifest_url:
                pot_policy: GvsPoTokenPolicy = self._get_default_ytcfg(
                    client_name)['GVS_PO_TOKEN_POLICY'][StreamingProtocol.HLS]
                require_po_token = gvs_pot_required(pot_policy, is_premium_subscriber, has_player_token)
                po_token = gvs_pots.get(client_name, fetch_pot_func(required=require_po_token or pot_policy.recommended))
                if po_token:
                    hls_manifest_url = hls_manifest_url.rstrip('/') + f'/pot/{po_token}'
                    if client_name not in gvs_pots:
                        gvs_pots[client_name] = po_token
                if require_po_token and not po_token and 'missing_pot' not in self._configuration_arg('formats'):
                    self._report_pot_format_skipped(video_id, client_name, 'hls')
                else:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        hls_manifest_url, video_id, 'mp4', fatal=False, live=live_status == 'is_live')
                    for sub in traverse_obj(subs, (..., ..., {dict})):
                        # TODO: If HLS video requires a PO Token, do the subs also require pot?
                        # Save client name for debugging
                        sub[STREAMING_DATA_CLIENT_NAME] = client_name
                    subtitles = self._merge_subtitles(subs, subtitles)
                    for f in fmts:
                        if process_manifest_format(f, 'hls', client_name, self._search_regex(
                                r'/itag/(\d+)', f['url'], 'itag', default=None), require_po_token and not po_token):
                            yield f

            dash_manifest_url = 'dash' not in skip_manifests and sd.get('dashManifestUrl')
            if dash_manifest_url:
                pot_policy: GvsPoTokenPolicy = self._get_default_ytcfg(
                    client_name)['GVS_PO_TOKEN_POLICY'][StreamingProtocol.DASH]
                require_po_token = gvs_pot_required(pot_policy, is_premium_subscriber, has_player_token)
                po_token = gvs_pots.get(client_name, fetch_pot_func(required=require_po_token or pot_policy.recommended))
                if po_token:
                    dash_manifest_url = dash_manifest_url.rstrip('/') + f'/pot/{po_token}'
                    if client_name not in gvs_pots:
                        gvs_pots[client_name] = po_token
                if require_po_token and not po_token and 'missing_pot' not in self._configuration_arg('formats'):
                    self._report_pot_format_skipped(video_id, client_name, 'dash')
                else:
                    formats, subs = self._extract_mpd_formats_and_subtitles(dash_manifest_url, video_id, fatal=False)
                    for sub in traverse_obj(subs, (..., ..., {dict})):
                        # TODO: If DASH video requires a PO Token, do the subs also require pot?
                        # Save client name for debugging
                        sub[STREAMING_DATA_CLIENT_NAME] = client_name
                    subtitles = self._merge_subtitles(subs, subtitles)  # Prioritize HLS subs over DASH
                    for f in formats:
                        if process_manifest_format(f, 'dash', client_name, f['format_id'], require_po_token and not po_token):
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

    def _download_initial_webpage(self, webpage_url, webpage_client, video_id):
        webpage = None
        if webpage_url and 'webpage' not in self._configuration_arg('player_skip'):
            query = {'bpctr': '9999999999', 'has_verified': '1'}
            pp = (
                self._configuration_arg('player_params', [None], casesense=True)[0]
                or traverse_obj(INNERTUBE_CLIENTS, (webpage_client, 'PLAYER_PARAMS', {str}))
            )
            if pp:
                query['pp'] = pp
            webpage = self._download_webpage_with_retries(
                webpage_url, video_id, query=query,
                headers=traverse_obj(self._get_default_ytcfg(webpage_client), {
                    'User-Agent': ('INNERTUBE_CONTEXT', 'client', 'userAgent', {str}),
                }))
        return webpage

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

    def _download_initial_data(self, video_id, webpage, webpage_client, webpage_ytcfg):
        initial_data = None
        if webpage and 'initial_data' not in self._configuration_arg('webpage_skip'):
            initial_data = self.extract_yt_initial_data(video_id, webpage, fatal=False)
            if not traverse_obj(initial_data, 'contents'):
                self.report_warning('Incomplete data received in embedded initial data; re-fetching using API.')
                initial_data = None
        if not initial_data and 'initial_data' not in self._configuration_arg('player_skip'):
            query = {'videoId': video_id}
            query.update(self._get_checkok_params())
            initial_data = self._extract_response(
                item_id=video_id, ep='next', fatal=False,
                ytcfg=webpage_ytcfg, query=query, check_get_keys='contents',
                note='Downloading initial data API JSON', default_client=webpage_client)
        return initial_data

    def _is_premium_subscriber(self, initial_data):
        if not self.is_authenticated or not initial_data:
            return False

        tlr = traverse_obj(
            initial_data, ('topbar', 'desktopTopbarRenderer', 'logo', 'topbarLogoRenderer'))
        return (
            traverse_obj(tlr, ('iconImage', 'iconType')) == 'YOUTUBE_PREMIUM_LOGO'
            or 'premium' in (self._get_text(tlr, 'tooltipText') or '').lower()
        )

    def _initial_extract(self, url, smuggled_data, webpage_url, webpage_client, video_id):
        # This function is also used by live-from-start refresh
        webpage = self._download_initial_webpage(webpage_url, webpage_client, video_id)
        webpage_ytcfg = self.extract_ytcfg(video_id, webpage) or self._get_default_ytcfg(webpage_client)

        initial_data = self._download_initial_data(video_id, webpage, webpage_client, webpage_ytcfg)

        is_premium_subscriber = self._is_premium_subscriber(initial_data)
        if is_premium_subscriber:
            self.write_debug('Detected YouTube Premium subscription')

        player_responses, player_url = self._extract_player_responses(
            self._get_requested_clients(url, smuggled_data, is_premium_subscriber),
            video_id, webpage, webpage_client, webpage_ytcfg, is_premium_subscriber)

        return webpage, webpage_ytcfg, initial_data, is_premium_subscriber, player_responses, player_url

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)

        base_url = self.http_scheme() + '//www.youtube.com/'
        webpage_url = base_url + 'watch?v=' + video_id
        webpage_client = 'web'

        webpage, webpage_ytcfg, initial_data, is_premium_subscriber, player_responses, player_url = self._initial_extract(
            url, smuggled_data, webpage_url, webpage_client, video_id)

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
        video_title = ((self._preferred_lang and translated_title)
                       or get_first(video_details, 'title')  # primary
                       or translated_title
                       or search_meta(['og:title', 'twitter:title', 'title']))
        translated_description = self._get_text(microformats, (..., 'description'))
        original_description = get_first(video_details, 'shortDescription')
        video_description = (
            (self._preferred_lang and translated_description)
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
                if subreason.startswith('The uploader has not made this video available in your country'):
                    countries = get_first(microformats, 'availableCountries')
                    if not countries:
                        regions_allowed = search_meta('regionsAllowed')
                        countries = regions_allowed.split(',') if regions_allowed else None
                    self.raise_geo_restricted(subreason, countries, metadata_available=True)
                reason += f'. {subreason}'
            if reason:
                if 'sign in' in reason.lower():
                    reason = remove_end(reason, 'This helps protect our community. Learn more')
                    reason = f'{remove_end(reason.strip(), ".")}. {self._youtube_login_hint}'
                elif get_first(playability_statuses, ('errorScreen', 'playerCaptchaViewModel', {dict})):
                    reason += '. YouTube is requiring a captcha challenge before playback'
                elif "This content isn't available, try again later" in reason:
                    reason = (
                        f'{remove_end(reason.strip(), ".")}. {"Your account" if self.is_authenticated else "The current session"} '
                        f'has been rate-limited by YouTube for up to an hour. It is recommended to use `-t sleep` to add a delay '
                        f'between video requests to avoid exceeding the rate limit. For more information, refer to  '
                        f'https://github.com/yt-dlp/yt-dlp/wiki/Extractors#this-content-isnt-available-try-again-later'
                    )
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
            'media_type': (
                'livestream' if get_first(video_details, 'isLiveContent')
                else 'short' if get_first(microformats, 'isShortsEligible')
                else 'video'),
            'release_timestamp': live_start_time,
            '_format_sort_fields': (  # source_preference is lower for potentially damaged formats
                'quality', 'res', 'fps', 'hdr:12', 'source', 'vcodec', 'channels', 'acodec', 'lang', 'proto'),
        }

        def get_lang_code(track):
            return (remove_start(track.get('vssId') or '', '.').replace('.', '-')
                    or track.get('languageCode'))

        def process_language(container, base_url, lang_code, sub_name, client_name, query):
            lang_subs = container.setdefault(lang_code, [])
            for fmt in self._SUBTITLE_FORMATS:
                # xosf=1 results in undesirable text position data for vtt, json3 & srv* subtitles
                # See: https://github.com/yt-dlp/yt-dlp/issues/13654
                query = {**query, 'fmt': fmt, 'xosf': []}
                lang_subs.append({
                    'ext': fmt,
                    'url': urljoin('https://www.youtube.com', update_url_query(base_url, query)),
                    'name': sub_name,
                    'impersonate': True,
                    STREAMING_DATA_CLIENT_NAME: client_name,
                })

        subtitles = {}
        skipped_subs_clients = set()

        # Only web/mweb clients provide translationLanguages, so include initial_pr in the traversal
        translation_languages = {
            lang['languageCode']: self._get_text(lang['languageName'], max_runs=1)
            for lang in traverse_obj(player_responses, (
                ..., 'captions', 'playerCaptionsTracklistRenderer', 'translationLanguages',
                lambda _, v: v['languageCode'] and v['languageName']))
        }
        # NB: Constructing the full subtitle dictionary is slow
        get_translated_subs = 'translated_subs' not in self._configuration_arg('skip') and (
            self.get_param('writeautomaticsub', False) or self.get_param('listsubtitles'))

        # Filter out initial_pr which does not have streamingData (smuggled client context)
        prs = traverse_obj(player_responses, (
            lambda _, v: v['streamingData'] and v['captions']['playerCaptionsTracklistRenderer']))
        all_captions = traverse_obj(prs, (
            ..., 'captions', 'playerCaptionsTracklistRenderer', 'captionTracks', ..., {dict}))
        need_subs_langs = {get_lang_code(sub) for sub in all_captions if sub.get('kind') != 'asr'}
        need_caps_langs = {
            remove_start(get_lang_code(sub), 'a-')
            for sub in all_captions if sub.get('kind') == 'asr'}

        for pr in prs:
            pctr = pr['captions']['playerCaptionsTracklistRenderer']
            client_name = pr['streamingData'][STREAMING_DATA_CLIENT_NAME]
            innertube_client_name = pr['streamingData'][STREAMING_DATA_INNERTUBE_CONTEXT]['client']['clientName']
            pot_policy: GvsPoTokenPolicy = self._get_default_ytcfg(client_name)['SUBS_PO_TOKEN_POLICY']
            fetch_subs_po_token_func = pr['streamingData'][STREAMING_DATA_FETCH_SUBS_PO_TOKEN]

            pot_params = {}
            already_fetched_pot = False

            for caption_track in traverse_obj(pctr, ('captionTracks', lambda _, v: v['baseUrl'])):
                base_url = caption_track['baseUrl']
                qs = parse_qs(base_url)
                lang_code = get_lang_code(caption_track)
                requires_pot = (
                    # We can detect the experiment for now
                    any(e in traverse_obj(qs, ('exp', ...)) for e in ('xpe', 'xpv'))
                    or (pot_policy.required and not (pot_policy.not_required_for_premium and is_premium_subscriber)))

                if not already_fetched_pot:
                    already_fetched_pot = True
                    if subs_po_token := fetch_subs_po_token_func(required=requires_pot or pot_policy.recommended):
                        pot_params.update({
                            'pot': subs_po_token,
                            'potc': '1',
                            'c': innertube_client_name,
                        })

                if not pot_params and requires_pot:
                    skipped_subs_clients.add(client_name)
                    self._report_pot_subtitles_skipped(video_id, client_name)
                    break

                orig_lang = qs.get('lang', [None])[-1]
                lang_name = self._get_text(caption_track, 'name', max_runs=1)
                if caption_track.get('kind') != 'asr':
                    if not lang_code:
                        continue
                    process_language(
                        subtitles, base_url, lang_code, lang_name, client_name, pot_params)
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
                            automatic_captions, base_url, f'{trans_code}-orig',
                            f'{trans_name} (Original)', client_name, pot_params)
                    # Setting tlang=lang returns damaged subtitles.
                    process_language(
                        automatic_captions, base_url, trans_code, trans_name, client_name,
                        pot_params if orig_lang == orig_trans_code else {'tlang': trans_code, **pot_params})

            # Avoid duplication if we've already got everything we need
            need_subs_langs.difference_update(subtitles)
            need_caps_langs.difference_update(automatic_captions)
            if not (need_subs_langs or need_caps_langs):
                break

        if skipped_subs_clients and (need_subs_langs or need_caps_langs):
            self._report_pot_subtitles_skipped(video_id, True, msg=join_nonempty(
                f'{video_id}: There are missing subtitles languages because a PO token was not provided.',
                need_subs_langs and f'Subtitles for these languages are missing: {", ".join(need_subs_langs)}.',
                need_caps_langs and f'Automatic captions for {len(need_caps_langs)} languages are missing.',
                delim=' '))

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
                    (?:.+?Released\ on\s*:\s*(?P<release_date>\d{4}-\d{2}-\d{2}))?
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

        COMMENTS_SECTION_IDS = ('comment-item-section', 'engagement-panel-comments-section')
        info['comment_count'] = traverse_obj(initial_data, (
            'contents', 'twoColumnWatchNextResults', 'results', 'results', 'contents', ..., 'itemSectionRenderer',
            'contents', ..., 'commentsEntryPointHeaderRenderer', 'commentCount',
        ), (
            'engagementPanels', lambda _, v: v['engagementPanelSectionListRenderer']['panelIdentifier'] in COMMENTS_SECTION_IDS,
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
            # XXX: This is redundant for as long as we are already checking all IOS HLS formats
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

        info['__post_extractor'] = self.extract_comments(webpage_ytcfg, video_id, contents, webpage)

        self.mark_watched(video_id, player_responses)

        return info

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
    YoutubeBaseInfoExtractor,
    _PoTokenContext,
    _split_innertube_client,
    short_client_name,
)
from ..openload import PhantomJSwrapper
from ...jsinterp import JSInterpreter
from ...networking.exceptions import HTTPError
from ...utils import (
    NO_DEFAULT,
    ExtractorError,
    LazyList,
    bug_reports_message,
    clean_html,
    datetime_from_str,
    filesize_from_tbr,
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

STREAMING_DATA_CLIENT_NAME = '__yt_dlp_client'
STREAMING_DATA_INITIAL_PO_TOKEN = '__yt_dlp_po_token'
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
    _SUBTITLE_FORMATS = ('json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt')
    _DEFAULT_CLIENTS = ('tv', 'ios', 'web')
    _DEFAULT_AUTHED_CLIENTS = ('tv', 'web')

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
            'note': 'Embed allowed age-gate video; works with web_embedded',
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
            'skip': 'Age-restricted; requires authentication',
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
            'skip': 'Age-restricted; requires authentication',
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
            'skip': 'Age-restricted; requires authentication',
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
                'description': 'md5:452d5c82f72bb7e62a4e0297c3f01c23',
                'age_limit': 0,
                'thumbnail': 'https://i.ytimg.com/vi/jfKfPfyJRdk/maxresdefault.jpg',
                'release_timestamp': 1657641570,
                'uploader_url': 'https://www.youtube.com/@LofiGirl',
                'channel_follower_count': int,
                'channel_is_verified': True,
                'title': r're:^lofi hip hop radio 📚 beats to relax/study to',
                'view_count': int,
                'live_status': 'is_live',
                'media_type': 'livestream',
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
            'skip': 'Age-restricted; requires authentication',
        },
        {
            'note': 'Support /live/ URL + media type for post-live content',
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
                'media_type': 'livestream',
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
        {
            # uploader_id has non-ASCII characters that are percent-encoded in YT's JSON
            'url': 'https://www.youtube.com/shorts/18NGQq7p3LY',
            'info_dict': {
                'id': '18NGQq7p3LY',
                'ext': 'mp4',
                'title': '아이브 이서 장원영 리즈 삐끼삐끼 챌린지',
                'description': '',
                'uploader': 'ㅇㅇ',
                'uploader_id': '@으아-v1k',
                'uploader_url': 'https://www.youtube.com/@으아-v1k',
                'channel': 'ㅇㅇ',
                'channel_id': 'UCC25oTm2J7ZVoi5TngOHg9g',
                'channel_url': 'https://www.youtube.com/channel/UCC25oTm2J7ZVoi5TngOHg9g',
                'thumbnail': r're:https?://.+/.+\.jpg',
                'playable_in_embed': True,
                'age_limit': 0,
                'duration': 3,
                'timestamp': 1724306170,
                'upload_date': '20240822',
                'availability': 'public',
                'live_status': 'not_live',
                'view_count': int,
                'like_count': int,
                'channel_follower_count': int,
                'categories': ['People & Blogs'],
                'tags': [],
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
        from yt_dlp.utils import parse_qs

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

        jsi = JSInterpreter(jscode)
        global_var_map = {}
        _, varname, value = self._extract_player_js_global_var(jscode)
        if varname:
            global_var_map[varname] = jsi.interpret_expression(value, {}, allow_recursion=100)
        initial_function = jsi.extract_function(funcname, global_var_map)
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

    def _extract_n_function_name(self, jscode, player_url=None):
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
                player_url and f'         player = {player_url}', delim='\n'))
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

    def _extract_player_js_global_var(self, jscode):
        """Returns tuple of strings: variable assignment code, variable name, variable value code"""
        return self._search_regex(
            r'''(?x)
                \'use\s+strict\';\s*
                (?P<code>
                    var\s+(?P<name>[a-zA-Z0-9_$]+)\s*=\s*
                    (?P<value>"(?:[^"\\]|\\.)+"\.split\("[^"]+"\))
                )[;,]
            ''', jscode, 'global variable', group=('code', 'name', 'value'), default=(None, None, None))

    def _fixup_n_function_code(self, argnames, code, full_code):
        global_var, varname, _ = self._extract_player_js_global_var(full_code)
        if global_var:
            self.write_debug(f'Prepending n function code with global array variable "{varname}"')
            code = global_var + ', ' + code
        else:
            self.write_debug('No global array variable found in player JS')
        return argnames, re.sub(
            rf';\s*if\s*\(\s*typeof\s+[a-zA-Z0-9_$]+\s*===?\s*(?:(["\'])undefined\1|{varname}\[\d+\])\s*\)\s*return\s+{argnames[0]};',
            ';', code)

    def _extract_n_function_code(self, video_id, player_url):
        player_id = self._extract_player_info(player_url)
        func_code = self.cache.load('youtube-nsig', player_id, min_ver='2025.03.21')
        jscode = func_code or self._load_player(video_id, player_url)
        jsi = JSInterpreter(jscode)

        if func_code:
            return jsi, player_id, func_code

        func_name = self._extract_n_function_name(jscode, player_url=player_url)

        # XXX: Workaround for the global array variable and lack of `typeof` implementation
        func_code = self._fixup_n_function_code(*jsi.extract_function_code(func_name), jscode)

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

            if ret.startswith('enhanced_except_') or ret.endswith(s):
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

    def fetch_po_token(self, client='web', context=_PoTokenContext.GVS, ytcfg=None, visitor_data=None,
                       data_sync_id=None, session_index=None, player_url=None, video_id=None, **kwargs):
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
        @param kwargs: Additional arguments to pass down. May be more added in the future.
        @return: The fetched PO Token. None if it could not be fetched.
        """

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

            return config_po_token

        # Require GVS WebPO Token if logged in for external fetching
        if player_url and context == _PoTokenContext.GVS and not data_sync_id and self.is_authenticated:
            self.report_warning(
                f'Unable to fetch GVS PO Token for {client} client: Missing required Data Sync ID for account. '
                f'You may need to pass a Data Sync ID with --extractor-args "youtube:data_sync_id=XXX"')
            return

        return self._fetch_po_token(
            client=client,
            context=context.value,
            ytcfg=ytcfg,
            visitor_data=visitor_data,
            data_sync_id=data_sync_id,
            session_index=session_index,
            player_url=player_url,
            video_id=video_id,
            **kwargs,
        )

    def _fetch_po_token(self, client, **kwargs):
        """(Unstable) External PO Token fetch stub"""

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

    def _extract_player_response(self, client, video_id, master_ytcfg, player_ytcfg, player_url, initial_pr, visitor_data, data_sync_id, po_token):
        headers = self.generate_api_headers(
            ytcfg=player_ytcfg,
            default_client=client,
            visitor_data=visitor_data,
            session_index=self._extract_session_index(master_ytcfg, player_ytcfg),
            delegated_session_id=(
                self._parse_data_sync_id(data_sync_id)[0]
                or self._extract_delegated_session_id(master_ytcfg, initial_pr, player_ytcfg)
            ),
            user_session_id=(
                self._parse_data_sync_id(data_sync_id)[1]
                or self._extract_user_session_id(master_ytcfg, initial_pr, player_ytcfg)
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

        sts = self._extract_signature_timestamp(video_id, player_url, master_ytcfg, fatal=False) if player_url else None
        yt_query.update(self._generate_player_context(sts))
        return self._extract_response(
            item_id=video_id, ep='player', query=yt_query,
            ytcfg=player_ytcfg, headers=headers, fatal=True,
            default_client=client,
            note='Downloading {} player API JSON'.format(client.replace('_', ' ').strip()),
        ) or None

    def _get_requested_clients(self, url, smuggled_data):
        requested_clients = []
        excluded_clients = []
        default_clients = self._DEFAULT_AUTHED_CLIENTS if self.is_authenticated else self._DEFAULT_CLIENTS
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

    def _extract_player_responses(self, clients, video_id, webpage, master_ytcfg, smuggled_data):
        initial_pr = None
        if webpage:
            initial_pr = self._search_json(
                self._YT_INITIAL_PLAYER_RESPONSE_RE, webpage, 'initial player response', video_id, fatal=False)

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
            player_ytcfg = master_ytcfg if client == 'web' else {}
            if 'configs' not in self._configuration_arg('player_skip') and client != 'web':
                player_ytcfg = self._download_ytcfg(client, video_id) or player_ytcfg

            player_url = player_url or self._extract_player_url(master_ytcfg, player_ytcfg, webpage=webpage)
            require_js_player = self._get_default_ytcfg(client).get('REQUIRE_JS_PLAYER')
            if 'js' in self._configuration_arg('player_skip'):
                require_js_player = False
                player_url = None

            if not player_url and not tried_iframe_fallback and require_js_player:
                player_url = self._download_player_url(video_id)
                tried_iframe_fallback = True

            visitor_data = visitor_data or self._extract_visitor_data(master_ytcfg, initial_pr, player_ytcfg)
            data_sync_id = data_sync_id or self._extract_data_sync_id(master_ytcfg, initial_pr, player_ytcfg)

            fetch_po_token_args = {
                'client': client,
                'visitor_data': visitor_data,
                'video_id': video_id,
                'data_sync_id': data_sync_id if self.is_authenticated else None,
                'player_url': player_url if require_js_player else None,
                'session_index': self._extract_session_index(master_ytcfg, player_ytcfg),
                'ytcfg': player_ytcfg,
            }

            player_po_token = self.fetch_po_token(
                context=_PoTokenContext.PLAYER, **fetch_po_token_args)

            gvs_po_token = self.fetch_po_token(
                context=_PoTokenContext.GVS, **fetch_po_token_args)

            required_pot_contexts = self._get_default_ytcfg(client)['PO_TOKEN_REQUIRED_CONTEXTS']

            if (
                not player_po_token
                and _PoTokenContext.PLAYER in required_pot_contexts
            ):
                # TODO: may need to skip player response request. Unsure yet..
                self.report_warning(
                    f'No Player PO Token provided for {client} client, '
                    f'which may be required for working {client} formats. This client will be deprioritized'
                    f'You can manually pass a Player PO Token for this client with --extractor-args "youtube:po_token={client}.player+XXX". '
                    f'For more information, refer to {PO_TOKEN_GUIDE_URL} .', only_once=True)
                deprioritize_pr = True

            if (
                not gvs_po_token
                and _PoTokenContext.GVS in required_pot_contexts
                and 'missing_pot' in self._configuration_arg('formats')
            ):
                # note: warning with help message is provided later during format processing
                self.report_warning(
                    f'No GVS PO Token provided for {client} client, '
                    f'which may be required for working {client} formats. This client will be deprioritized',
                    only_once=True)
                deprioritize_pr = True

            pr = initial_pr if client == 'web' else None
            try:
                pr = pr or self._extract_player_response(
                    client, video_id,
                    master_ytcfg=player_ytcfg or master_ytcfg,
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
                # Save client name for introspection later
                sd = traverse_obj(pr, ('streamingData', {dict})) or {}
                sd[STREAMING_DATA_CLIENT_NAME] = client
                sd[STREAMING_DATA_INITIAL_PO_TOKEN] = gvs_po_token
                for f in traverse_obj(sd, (('formats', 'adaptiveFormats'), ..., {dict})):
                    f[STREAMING_DATA_CLIENT_NAME] = client
                    f[STREAMING_DATA_INITIAL_PO_TOKEN] = gvs_po_token
                if deprioritize_pr:
                    deprioritized_prs.append(pr)
                else:
                    prs.append(pr)

            # EU countries require age-verification for accounts to access age-restricted videos
            # If account is not age-verified, _is_agegated() will be truthy for non-embedded clients
            if self.is_authenticated and self._is_agegated(pr):
                self.to_screen(
                    f'{video_id}: This video is age-restricted and YouTube is requiring '
                    'account age-verification; some formats may be missing', only_once=True)
                # tv_embedded can work around the age-verification requirement for embeddable videos
                # web_creator may work around age-verification for all videos but requires PO token
                append_client('tv_embedded', 'web_creator')

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
                    self.report_warning(
                        f'Some {client_name} client https formats have been skipped as they are missing a url. '
                        f'{"Your account" if self.is_authenticated else "The current session"} may have '
                        f'the SSAP (server-side ads) experiment which interferes with yt-dlp. '
                        f'Please see  https://github.com/yt-dlp/yt-dlp/issues/12482  for more details.',
                        video_id, only_once=True)
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
                    if player_url:
                        self.report_warning(
                            f'nsig extraction failed: Some formats may be missing\n'
                            f'         n = {query["n"][0]} ; player = {player_url}',
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
                    f'{video_id}: Some formats are possibly damaged. They will be deprioritized', only_once=True)

            po_token = fmt.get(STREAMING_DATA_INITIAL_PO_TOKEN)

            if po_token:
                fmt_url = update_url_query(fmt_url, {'pot': po_token})

            # Clients that require PO Token return videoplayback URLs that may return 403
            require_po_token = (
                not po_token
                and _PoTokenContext.GVS in self._get_default_ytcfg(client_name)['PO_TOKEN_REQUIRED_CONTEXTS']
                and itag not in ['18'])  # these formats do not require PO Token

            if require_po_token and 'missing_pot' not in self._configuration_arg('formats'):
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
                    is_damaged and 'DAMAGED', require_po_token and 'MISSING POT',
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
                # Strictly de-prioritize broken, damaged and 3gp formats
                'preference': -20 if require_po_token else -10 if is_damaged else -2 if itag == '17' else None,
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

        def process_manifest_format(f, proto, client_name, itag, po_token):
            key = (proto, f.get('language'))
            if not all_formats and key in itags[itag]:
                return False

            if f.get('source_preference') is None:
                f['source_preference'] = -1

            # Clients that require PO Token return videoplayback URLs that may return 403
            # hls does not currently require PO Token
            if (
                not po_token
                and _PoTokenContext.GVS in self._get_default_ytcfg(client_name)['PO_TOKEN_REQUIRED_CONTEXTS']
                and proto != 'hls'
            ):
                if 'missing_pot' not in self._configuration_arg('formats'):
                    self._report_pot_format_skipped(video_id, client_name, proto)
                    return False
                f['format_note'] = join_nonempty(f.get('format_note'), 'MISSING POT', delim=' ')
                f['source_preference'] -= 20

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
            po_token = sd.get(STREAMING_DATA_INITIAL_PO_TOKEN)
            hls_manifest_url = 'hls' not in skip_manifests and sd.get('hlsManifestUrl')
            if hls_manifest_url:
                if po_token:
                    hls_manifest_url = hls_manifest_url.rstrip('/') + f'/pot/{po_token}'
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    hls_manifest_url, video_id, 'mp4', fatal=False, live=live_status == 'is_live')
                subtitles = self._merge_subtitles(subs, subtitles)
                for f in fmts:
                    if process_manifest_format(f, 'hls', client_name, self._search_regex(
                            r'/itag/(\d+)', f['url'], 'itag', default=None), po_token):
                        yield f

            dash_manifest_url = 'dash' not in skip_manifests and sd.get('dashManifestUrl')
            if dash_manifest_url:
                if po_token:
                    dash_manifest_url = dash_manifest_url.rstrip('/') + f'/pot/{po_token}'
                formats, subs = self._extract_mpd_formats_and_subtitles(dash_manifest_url, video_id, fatal=False)
                subtitles = self._merge_subtitles(subs, subtitles)  # Prioritize HLS subs over DASH
                for f in formats:
                    if process_manifest_format(f, 'dash', client_name, f['format_id'], po_token):
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
            webpage = self._download_webpage_with_retries(webpage_url, video_id, query=query)

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
                if subreason == 'The uploader has not made this video available in your country.':
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
            'media_type': 'livestream' if get_first(video_details, 'isLiveContent') else None,
            'release_timestamp': live_start_time,
            '_format_sort_fields': (  # source_preference is lower for potentially damaged formats
                'quality', 'res', 'fps', 'hdr:12', 'source', 'vcodec', 'channels', 'acodec', 'lang', 'proto'),
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

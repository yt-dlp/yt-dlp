import base64
import collections
import functools
import getpass
import http.client
import http.cookiejar
import http.cookies
import inspect
import itertools
import json
import math
import netrc
import os
import random
import re
import subprocess
import sys
import time
import types
import urllib.parse
import urllib.request
import xml.etree.ElementTree

from ..compat import (
    compat_etree_fromstring,
    compat_expanduser,
    urllib_req_to_req,
)
from ..cookies import LenientSimpleCookie
from ..downloader.f4m import get_base_url, remove_encrypted_media
from ..downloader.hls import HlsFD
from ..networking import HEADRequest, Request
from ..networking.exceptions import (
    HTTPError,
    IncompleteRead,
    TransportError,
    network_exceptions,
)
from ..networking.impersonate import ImpersonateTarget
from ..utils import (
    IDENTITY,
    JSON_LD_RE,
    NO_DEFAULT,
    ExtractorError,
    FormatSorter,
    GeoRestrictedError,
    GeoUtils,
    ISO639Utils,
    LenientJSONDecoder,
    Popen,
    RegexNotFoundError,
    RetryManager,
    UnsupportedError,
    age_restricted,
    base_url,
    bug_reports_message,
    classproperty,
    clean_html,
    deprecation_warning,
    determine_ext,
    dict_get,
    encode_data_uri,
    extract_attributes,
    filter_dict,
    fix_xml_ampersands,
    float_or_none,
    format_field,
    int_or_none,
    join_nonempty,
    js_to_json,
    mimetype2ext,
    netrc_from_content,
    orderedSet,
    parse_bitrate,
    parse_codecs,
    parse_duration,
    parse_iso8601,
    parse_m3u8_attributes,
    parse_resolution,
    sanitize_url,
    smuggle_url,
    str_or_none,
    str_to_int,
    strip_or_none,
    traverse_obj,
    truncate_string,
    try_call,
    try_get,
    unescapeHTML,
    unified_strdate,
    unified_timestamp,
    url_basename,
    url_or_none,
    urlhandle_detect_ext,
    urljoin,
    variadic,
    xpath_element,
    xpath_text,
    xpath_with_ns,
)
from ..utils._utils import _request_dump_filename


class InfoExtractor:
    """Information Extractor class.

    Information extractors are the classes that, given a URL, extract
    information about the video (or videos) the URL refers to. This
    information includes the real video URL, the video title, author and
    others. The information is stored in a dictionary which is then
    passed to the YoutubeDL. The YoutubeDL processes this
    information possibly downloading the video to the file system, among
    other possible outcomes.

    The type field determines the type of the result.
    By far the most common value (and the default if _type is missing) is
    "video", which indicates a single video.

    For a video, the dictionaries must include the following fields:

    id:             Video identifier.
    title:          Video title, unescaped. Set to an empty string if video has
                    no title as opposed to "None" which signifies that the
                    extractor failed to obtain a title

    Additionally, it must contain either a formats entry or a url one:

    formats:        A list of dictionaries for each format available, ordered
                    from worst to best quality.

                    Potential fields:
                    * url        The mandatory URL representing the media:
                                   for plain file media - HTTP URL of this file,
                                   for RTMP - RTMP URL,
                                   for HLS - URL of the M3U8 media playlist,
                                   for HDS - URL of the F4M manifest,
                                   for DASH
                                     - HTTP URL to plain file media (in case of
                                       unfragmented media)
                                     - URL of the MPD manifest or base URL
                                       representing the media if MPD manifest
                                       is parsed from a string (in case of
                                       fragmented media)
                                   for MSS - URL of the ISM manifest.
                    * request_data  Data to send in POST request to the URL
                    * manifest_url
                                 The URL of the manifest file in case of
                                 fragmented media:
                                   for HLS - URL of the M3U8 master playlist,
                                   for HDS - URL of the F4M manifest,
                                   for DASH - URL of the MPD manifest,
                                   for MSS - URL of the ISM manifest.
                    * manifest_stream_number  (For internal use only)
                                 The index of the stream in the manifest file
                    * ext        Will be calculated from URL if missing
                    * format     A human-readable description of the format
                                 ("mp4 container with h264/opus").
                                 Calculated from the format_id, width, height.
                                 and format_note fields if missing.
                    * format_id  A short description of the format
                                 ("mp4_h264_opus" or "19").
                                Technically optional, but strongly recommended.
                    * format_note Additional info about the format
                                 ("3D" or "DASH video")
                    * width      Width of the video, if known
                    * height     Height of the video, if known
                    * aspect_ratio  Aspect ratio of the video, if known
                                 Automatically calculated from width and height
                    * resolution Textual description of width and height
                                 Automatically calculated from width and height
                    * dynamic_range The dynamic range of the video. One of:
                                 "SDR" (None), "HDR10", "HDR10+, "HDR12", "HLG, "DV"
                    * tbr        Average bitrate of audio and video in kbps (1000 bits/sec)
                    * abr        Average audio bitrate in kbps (1000 bits/sec)
                    * acodec     Name of the audio codec in use
                    * asr        Audio sampling rate in Hertz
                    * audio_channels  Number of audio channels
                    * vbr        Average video bitrate in kbps (1000 bits/sec)
                    * fps        Frame rate
                    * vcodec     Name of the video codec in use
                    * container  Name of the container format
                    * filesize   The number of bytes, if known in advance
                    * filesize_approx  An estimate for the number of bytes
                    * player_url SWF Player URL (used for rtmpdump).
                    * protocol   The protocol that will be used for the actual
                                 download, lower-case. One of "http", "https" or
                                 one of the protocols defined in downloader.PROTOCOL_MAP
                    * fragment_base_url
                                 Base URL for fragments. Each fragment's path
                                 value (if present) will be relative to
                                 this URL.
                    * fragments  A list of fragments of a fragmented media.
                                 Each fragment entry must contain either an url
                                 or a path. If an url is present it should be
                                 considered by a client. Otherwise both path and
                                 fragment_base_url must be present. Here is
                                 the list of all potential fields:
                                 * "url" - fragment's URL
                                 * "path" - fragment's path relative to
                                            fragment_base_url
                                 * "duration" (optional, int or float)
                                 * "filesize" (optional, int)
                    * hls_media_playlist_data
                                 The M3U8 media playlist data as a string.
                                 Only use if the data must be modified during extraction and
                                 the native HLS downloader should bypass requesting the URL.
                                 Does not apply if ffmpeg is used as external downloader
                    * is_from_start  Is a live format that can be downloaded
                                from the start. Boolean
                    * preference Order number of this format. If this field is
                                 present and not None, the formats get sorted
                                 by this field, regardless of all other values.
                                 -1 for default (order by other properties),
                                 -2 or smaller for less than default.
                                 < -1000 to hide the format (if there is
                                    another one which is strictly better)
                    * language   Language code, e.g. "de" or "en-US".
                    * language_preference  Is this in the language mentioned in
                                 the URL?
                                 10 if it's what the URL is about,
                                 -1 for default (don't know),
                                 -10 otherwise, other values reserved for now.
                    * quality    Order number of the video quality of this
                                 format, irrespective of the file format.
                                 -1 for default (order by other properties),
                                 -2 or smaller for less than default.
                    * source_preference  Order number for this video source
                                  (quality takes higher priority)
                                 -1 for default (order by other properties),
                                 -2 or smaller for less than default.
                    * http_headers  A dictionary of additional HTTP headers
                                 to add to the request.
                    * stretched_ratio  If given and not 1, indicates that the
                                 video's pixels are not square.
                                 width : height ratio as float.
                    * no_resume  The server does not support resuming the
                                 (HTTP or RTMP) download. Boolean.
                    * has_drm    True if the format has DRM and cannot be downloaded.
                                 'maybe' if the format may have DRM and has to be tested before download.
                    * extra_param_to_segment_url  A query string to append to each
                                 fragment's URL, or to update each existing query string
                                 with. If it is an HLS stream with an AES-128 decryption key,
                                 the query paramaters will be passed to the key URI as well,
                                 unless there is an `extra_param_to_key_url` given,
                                 or unless an external key URI is provided via `hls_aes`.
                                 Only applied by the native HLS/DASH downloaders.
                    * extra_param_to_key_url  A query string to append to the URL
                                 of the format's HLS AES-128 decryption key.
                                 Only applied by the native HLS downloader.
                    * hls_aes    A dictionary of HLS AES-128 decryption information
                                 used by the native HLS downloader to override the
                                 values in the media playlist when an '#EXT-X-KEY' tag
                                 is present in the playlist:
                                 * uri  The URI from which the key will be downloaded
                                 * key  The key (as hex) used to decrypt fragments.
                                        If `key` is given, any key URI will be ignored
                                 * iv   The IV (as hex) used to decrypt fragments
                    * downloader_options  A dictionary of downloader options
                                 (For internal use only)
                                 * http_chunk_size Chunk size for HTTP downloads
                                 * ffmpeg_args     Extra arguments for ffmpeg downloader (input)
                                 * ffmpeg_args_out Extra arguments for ffmpeg downloader (output)
                    * is_dash_periods  Whether the format is a result of merging
                                 multiple DASH periods.
                    RTMP formats can also have the additional fields: page_url,
                    app, play_path, tc_url, flash_version, rtmp_live, rtmp_conn,
                    rtmp_protocol, rtmp_real_time

    url:            Final video URL.
    ext:            Video filename extension.
    format:         The video format, defaults to ext (used for --get-format)
    player_url:     SWF Player URL (used for rtmpdump).

    The following fields are optional:

    direct:         True if a direct video file was given (must only be set by GenericIE)
    alt_title:      A secondary title of the video.
    display_id:     An alternative identifier for the video, not necessarily
                    unique, but available before title. Typically, id is
                    something like "4234987", title "Dancing naked mole rats",
                    and display_id "dancing-naked-mole-rats"
    thumbnails:     A list of dictionaries, with the following entries:
                        * "id" (optional, string) - Thumbnail format ID
                        * "url"
                        * "ext" (optional, string) - actual image extension if not given in URL
                        * "preference" (optional, int) - quality of the image
                        * "width" (optional, int)
                        * "height" (optional, int)
                        * "resolution" (optional, string "{width}x{height}",
                                        deprecated)
                        * "filesize" (optional, int)
                        * "http_headers" (dict) - HTTP headers for the request
    thumbnail:      Full URL to a video thumbnail image.
    description:    Full video description.
    uploader:       Full name of the video uploader.
    license:        License name the video is licensed under.
    creators:       List of creators of the video.
    timestamp:      UNIX timestamp of the moment the video was uploaded
    upload_date:    Video upload date in UTC (YYYYMMDD).
                    If not explicitly set, calculated from timestamp
    release_timestamp: UNIX timestamp of the moment the video was released.
                    If it is not clear whether to use timestamp or this, use the former
    release_date:   The date (YYYYMMDD) when the video was released in UTC.
                    If not explicitly set, calculated from release_timestamp
    release_year:   Year (YYYY) as integer when the video or album was released.
                    To be used if no exact release date is known.
                    If not explicitly set, calculated from release_date.
    modified_timestamp: UNIX timestamp of the moment the video was last modified.
    modified_date:   The date (YYYYMMDD) when the video was last modified in UTC.
                    If not explicitly set, calculated from modified_timestamp
    uploader_id:    Nickname or id of the video uploader.
    uploader_url:   Full URL to a personal webpage of the video uploader.
    channel:        Full name of the channel the video is uploaded on.
                    Note that channel fields may or may not repeat uploader
                    fields. This depends on a particular extractor.
    channel_id:     Id of the channel.
    channel_url:    Full URL to a channel webpage.
    channel_follower_count: Number of followers of the channel.
    channel_is_verified: Whether the channel is verified on the platform.
    location:       Physical location where the video was filmed.
    subtitles:      The available subtitles as a dictionary in the format
                    {tag: subformats}. "tag" is usually a language code, and
                    "subformats" is a list sorted from lower to higher
                    preference, each element is a dictionary with the "ext"
                    entry and one of:
                        * "data": The subtitles file contents
                        * "url": A URL pointing to the subtitles file
                    It can optionally also have:
                        * "name": Name or description of the subtitles
                        * "http_headers": A dictionary of additional HTTP headers
                                  to add to the request.
                    "ext" will be calculated from URL if missing
    automatic_captions: Like 'subtitles'; contains automatically generated
                    captions instead of normal subtitles
    duration:       Length of the video in seconds, as an integer or float.
    view_count:     How many users have watched the video on the platform.
    concurrent_view_count: How many users are currently watching the video on the platform.
    like_count:     Number of positive ratings of the video
    dislike_count:  Number of negative ratings of the video
    repost_count:   Number of reposts of the video
    average_rating: Average rating given by users, the scale used depends on the webpage
    comment_count:  Number of comments on the video
    comments:       A list of comments, each with one or more of the following
                    properties (all but one of text or html optional):
                        * "author" - human-readable name of the comment author
                        * "author_id" - user ID of the comment author
                        * "author_thumbnail" - The thumbnail of the comment author
                        * "author_url" - The url to the comment author's page
                        * "author_is_verified" - Whether the author is verified
                                                 on the platform
                        * "author_is_uploader" - Whether the comment is made by
                                                 the video uploader
                        * "id" - Comment ID
                        * "html" - Comment as HTML
                        * "text" - Plain text of the comment
                        * "timestamp" - UNIX timestamp of comment
                        * "parent" - ID of the comment this one is replying to.
                                     Set to "root" to indicate that this is a
                                     comment to the original video.
                        * "like_count" - Number of positive ratings of the comment
                        * "dislike_count" - Number of negative ratings of the comment
                        * "is_favorited" - Whether the comment is marked as
                                           favorite by the video uploader
                        * "is_pinned" - Whether the comment is pinned to
                                        the top of the comments
    age_limit:      Age restriction for the video, as an integer (years)
    webpage_url:    The URL to the video webpage, if given to yt-dlp it
                    should allow to get the same result again. (It will be set
                    by YoutubeDL if it's missing)
    categories:     A list of categories that the video falls in, for example
                    ["Sports", "Berlin"]
    tags:           A list of tags assigned to the video, e.g. ["sweden", "pop music"]
    cast:           A list of the video cast
    is_live:        True, False, or None (=unknown). Whether this video is a
                    live stream that goes on instead of a fixed-length video.
    was_live:       True, False, or None (=unknown). Whether this video was
                    originally a live stream.
    live_status:    None (=unknown), 'is_live', 'is_upcoming', 'was_live', 'not_live',
                    or 'post_live' (was live, but VOD is not yet processed)
                    If absent, automatically set from is_live, was_live
    start_time:     Time in seconds where the reproduction should start, as
                    specified in the URL.
    end_time:       Time in seconds where the reproduction should end, as
                    specified in the URL.
    chapters:       A list of dictionaries, with the following entries:
                        * "start_time" - The start time of the chapter in seconds
                        * "end_time" - The end time of the chapter in seconds
                        * "title" (optional, string)
    heatmap:        A list of dictionaries, with the following entries:
                        * "start_time" - The start time of the data point in seconds
                        * "end_time" - The end time of the data point in seconds
                        * "value" - The normalized value of the data point (float between 0 and 1)
    playable_in_embed: Whether this video is allowed to play in embedded
                    players on other sites. Can be True (=always allowed),
                    False (=never allowed), None (=unknown), or a string
                    specifying the criteria for embedability; e.g. 'whitelist'
    availability:   Under what condition the video is available. One of
                    'private', 'premium_only', 'subscriber_only', 'needs_auth',
                    'unlisted' or 'public'. Use 'InfoExtractor._availability'
                    to set it
    media_type:     The type of media as classified by the site, e.g. "episode", "clip", "trailer"
    _old_archive_ids: A list of old archive ids needed for backward compatibility
    _format_sort_fields: A list of fields to use for sorting formats
    __post_extractor: A function to be called just before the metadata is
                    written to either disk, logger or console. The function
                    must return a dict which will be added to the info_dict.
                    This is usefull for additional information that is
                    time-consuming to extract. Note that the fields thus
                    extracted will not be available to output template and
                    match_filter. So, only "comments" and "comment_count" are
                    currently allowed to be extracted via this method.

    The following fields should only be used when the video belongs to some logical
    chapter or section:

    chapter:        Name or title of the chapter the video belongs to.
    chapter_number: Number of the chapter the video belongs to, as an integer.
    chapter_id:     Id of the chapter the video belongs to, as a unicode string.

    The following fields should only be used when the video is an episode of some
    series, programme or podcast:

    series:         Title of the series or programme the video episode belongs to.
    series_id:      Id of the series or programme the video episode belongs to, as a unicode string.
    season:         Title of the season the video episode belongs to.
    season_number:  Number of the season the video episode belongs to, as an integer.
    season_id:      Id of the season the video episode belongs to, as a unicode string.
    episode:        Title of the video episode. Unlike mandatory video title field,
                    this field should denote the exact title of the video episode
                    without any kind of decoration.
    episode_number: Number of the video episode within a season, as an integer.
    episode_id:     Id of the video episode, as a unicode string.

    The following fields should only be used when the media is a track or a part of
    a music album:

    track:          Title of the track.
    track_number:   Number of the track within an album or a disc, as an integer.
    track_id:       Id of the track (useful in case of custom indexing, e.g. 6.iii),
                    as a unicode string.
    artists:        List of artists of the track.
    composers:      List of composers of the piece.
    genres:         List of genres of the track.
    album:          Title of the album the track belongs to.
    album_type:     Type of the album (e.g. "Demo", "Full-length", "Split", "Compilation", etc).
    album_artists:  List of all artists appeared on the album.
                    E.g. ["Ash Borer", "Fell Voices"] or ["Various Artists"].
                    Useful for splits and compilations.
    disc_number:    Number of the disc or other physical medium the track belongs to,
                    as an integer.

    The following fields should only be set for clips that should be cut from the original video:

    section_start:  Start time of the section in seconds
    section_end:    End time of the section in seconds

    The following fields should only be set for storyboards:
    rows:           Number of rows in each storyboard fragment, as an integer
    columns:        Number of columns in each storyboard fragment, as an integer

    The following fields are deprecated and should not be set by new code:
    composer:       Use "composers" instead.
                    Composer(s) of the piece, comma-separated.
    artist:         Use "artists" instead.
                    Artist(s) of the track, comma-separated.
    genre:          Use "genres" instead.
                    Genre(s) of the track, comma-separated.
    album_artist:   Use "album_artists" instead.
                    All artists appeared on the album, comma-separated.
    creator:        Use "creators" instead.
                    The creator of the video.

    Unless mentioned otherwise, the fields should be Unicode strings.

    Unless mentioned otherwise, None is equivalent to absence of information.


    _type "playlist" indicates multiple videos.
    There must be a key "entries", which is a list, an iterable, or a PagedList
    object, each element of which is a valid dictionary by this specification.

    Additionally, playlists can have "id", "title", and any other relevant
    attributes with the same semantics as videos (see above).

    It can also have the following optional fields:

    playlist_count: The total number of videos in a playlist. If not given,
                    YoutubeDL tries to calculate it from "entries"


    _type "multi_video" indicates that there are multiple videos that
    form a single show, for examples multiple acts of an opera or TV episode.
    It must have an entries key like a playlist and contain all the keys
    required for a video at the same time.


    _type "url" indicates that the video must be extracted from another
    location, possibly by a different extractor. Its only required key is:
    "url" - the next URL to extract.
    The key "ie_key" can be set to the class name (minus the trailing "IE",
    e.g. "Youtube") if the extractor class is known in advance.
    Additionally, the dictionary may have any properties of the resolved entity
    known in advance, for example "title" if the title of the referred video is
    known ahead of time.


    _type "url_transparent" entities have the same specification as "url", but
    indicate that the given additional information is more precise than the one
    associated with the resolved URL.
    This is useful when a site employs a video service that hosts the video and
    its technical metadata, but that video service does not embed a useful
    title, description etc.


    Subclasses of this should also be added to the list of extractors and
    should define _VALID_URL as a regexp or a Sequence of regexps, and
    re-define the _real_extract() and (optionally) _real_initialize() methods.

    Subclasses may also override suitable() if necessary, but ensure the function
    signature is preserved and that this function imports everything it needs
    (except other extractors), so that lazy_extractors works correctly.

    Subclasses can define a list of _EMBED_REGEX, which will be searched for in
    the HTML of Generic webpages. It may also override _extract_embed_urls
    or _extract_from_webpage as necessary. While these are normally classmethods,
    _extract_from_webpage is allowed to be an instance method.

    _extract_from_webpage may raise self.StopExtraction to stop further
    processing of the webpage and obtain exclusive rights to it. This is useful
    when the extractor cannot reliably be matched using just the URL,
    e.g. invidious/peertube instances

    Embed-only extractors can be defined by setting _VALID_URL = False.

    To support username + password (or netrc) login, the extractor must define a
    _NETRC_MACHINE and re-define _perform_login(username, password) and
    (optionally) _initialize_pre_login() methods. The _perform_login method will
    be called between _initialize_pre_login and _real_initialize if credentials
    are passed by the user. In cases where it is necessary to have the login
    process as part of the extraction rather than initialization, _perform_login
    can be left undefined.

    _GEO_BYPASS attribute may be set to False in order to disable
    geo restriction bypass mechanisms for a particular extractor.
    Though it won't disable explicit geo restriction bypass based on
    country code provided with geo_bypass_country.

    _GEO_COUNTRIES attribute may contain a list of presumably geo unrestricted
    countries for this extractor. One of these countries will be used by
    geo restriction bypass mechanism right away in order to bypass
    geo restriction, of course, if the mechanism is not disabled.

    _GEO_IP_BLOCKS attribute may contain a list of presumably geo unrestricted
    IP blocks in CIDR notation for this extractor. One of these IP blocks
    will be used by geo restriction bypass mechanism similarly
    to _GEO_COUNTRIES.

    The _ENABLED attribute should be set to False for IEs that
    are disabled by default and must be explicitly enabled.

    The _WORKING attribute should be set to False for broken IEs
    in order to warn the users and skip the tests.
    """

    _ready = False
    _downloader = None
    _x_forwarded_for_ip = None
    _GEO_BYPASS = True
    _GEO_COUNTRIES = None
    _GEO_IP_BLOCKS = None
    _WORKING = True
    _ENABLED = True
    _NETRC_MACHINE = None
    IE_DESC = None
    SEARCH_KEY = None
    _VALID_URL = None
    _EMBED_REGEX = []

    def _login_hint(self, method=NO_DEFAULT, netrc=None):
        password_hint = f'--username and --password, --netrc-cmd, or --netrc ({netrc or self._NETRC_MACHINE}) to provide account credentials'
        cookies_hint = 'See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies'
        return {
            None: '',
            'any': f'Use --cookies, --cookies-from-browser, {password_hint}. {cookies_hint}',
            'password': f'Use {password_hint}',
            'cookies': f'Use --cookies-from-browser or --cookies for the authentication. {cookies_hint}',
            'session_cookies': f'Use --cookies for the authentication (--cookies-from-browser might not work). {cookies_hint}',
        }[method if method is not NO_DEFAULT else 'any' if self.supports_login() else 'cookies']

    def __init__(self, downloader=None):
        """Constructor. Receives an optional downloader (a YoutubeDL instance).
        If a downloader is not passed during initialization,
        it must be set using "set_downloader()" before "extract()" is called"""
        self._ready = False
        self._x_forwarded_for_ip = None
        self._printed_messages = set()
        self.set_downloader(downloader)

    @classmethod
    def _match_valid_url(cls, url):
        if cls._VALID_URL is False:
            return None
        # This does not use has/getattr intentionally - we want to know whether
        # we have cached the regexp for *this* class, whereas getattr would also
        # match the superclass
        if '_VALID_URL_RE' not in cls.__dict__:
            cls._VALID_URL_RE = tuple(map(re.compile, variadic(cls._VALID_URL)))
        return next(filter(None, (regex.match(url) for regex in cls._VALID_URL_RE)), None)

    @classmethod
    def suitable(cls, url):
        """Receives a URL and returns True if suitable for this IE."""
        # This function must import everything it needs (except other extractors),
        # so that lazy_extractors works correctly
        return cls._match_valid_url(url) is not None

    @classmethod
    def _match_id(cls, url):
        return cls._match_valid_url(url).group('id')

    @classmethod
    def get_temp_id(cls, url):
        try:
            return cls._match_id(url)
        except (IndexError, AttributeError):
            return None

    @classmethod
    def working(cls):
        """Getter method for _WORKING."""
        return cls._WORKING

    @classmethod
    def supports_login(cls):
        return bool(cls._NETRC_MACHINE)

    def initialize(self):
        """Initializes an instance (authentication, etc)."""
        self._printed_messages = set()
        self._initialize_geo_bypass({
            'countries': self._GEO_COUNTRIES,
            'ip_blocks': self._GEO_IP_BLOCKS,
        })
        if not self._ready:
            self._initialize_pre_login()
            if self.supports_login():
                username, password = self._get_login_info()
                if username:
                    self._perform_login(username, password)
            elif self.get_param('username') and False not in (self.IE_DESC, self._NETRC_MACHINE):
                self.report_warning(f'Login with password is not supported for this website. {self._login_hint("cookies")}')
            self._real_initialize()
            self._ready = True

    def _initialize_geo_bypass(self, geo_bypass_context):
        """
        Initialize geo restriction bypass mechanism.

        This method is used to initialize geo bypass mechanism based on faking
        X-Forwarded-For HTTP header. A random country from provided country list
        is selected and a random IP belonging to this country is generated. This
        IP will be passed as X-Forwarded-For HTTP header in all subsequent
        HTTP requests.

        This method will be used for initial geo bypass mechanism initialization
        during the instance initialization with _GEO_COUNTRIES and
        _GEO_IP_BLOCKS.

        You may also manually call it from extractor's code if geo bypass
        information is not available beforehand (e.g. obtained during
        extraction) or due to some other reason. In this case you should pass
        this information in geo bypass context passed as first argument. It may
        contain following fields:

        countries:  List of geo unrestricted countries (similar
                    to _GEO_COUNTRIES)
        ip_blocks:  List of geo unrestricted IP blocks in CIDR notation
                    (similar to _GEO_IP_BLOCKS)

        """
        if not self._x_forwarded_for_ip:

            # Geo bypass mechanism is explicitly disabled by user
            if not self.get_param('geo_bypass', True):
                return

            if not geo_bypass_context:
                geo_bypass_context = {}

            # Backward compatibility: previously _initialize_geo_bypass
            # expected a list of countries, some 3rd party code may still use
            # it this way
            if isinstance(geo_bypass_context, (list, tuple)):
                geo_bypass_context = {
                    'countries': geo_bypass_context,
                }

            # The whole point of geo bypass mechanism is to fake IP
            # as X-Forwarded-For HTTP header based on some IP block or
            # country code.

            # Path 1: bypassing based on IP block in CIDR notation

            # Explicit IP block specified by user, use it right away
            # regardless of whether extractor is geo bypassable or not
            ip_block = self.get_param('geo_bypass_ip_block', None)

            # Otherwise use random IP block from geo bypass context but only
            # if extractor is known as geo bypassable
            if not ip_block:
                ip_blocks = geo_bypass_context.get('ip_blocks')
                if self._GEO_BYPASS and ip_blocks:
                    ip_block = random.choice(ip_blocks)

            if ip_block:
                self._x_forwarded_for_ip = GeoUtils.random_ipv4(ip_block)
                self.write_debug(f'Using fake IP {self._x_forwarded_for_ip} as X-Forwarded-For')
                return

            # Path 2: bypassing based on country code

            # Explicit country code specified by user, use it right away
            # regardless of whether extractor is geo bypassable or not
            country = self.get_param('geo_bypass_country', None)

            # Otherwise use random country code from geo bypass context but
            # only if extractor is known as geo bypassable
            if not country:
                countries = geo_bypass_context.get('countries')
                if self._GEO_BYPASS and countries:
                    country = random.choice(countries)

            if country:
                self._x_forwarded_for_ip = GeoUtils.random_ipv4(country)
                self._downloader.write_debug(
                    f'Using fake IP {self._x_forwarded_for_ip} ({country.upper()}) as X-Forwarded-For')

    def extract(self, url):
        """Extracts URL information and returns it in list of dicts."""
        try:
            for _ in range(2):
                try:
                    self.initialize()
                    self.to_screen('Extracting URL: %s' % (
                        url if self.get_param('verbose') else truncate_string(url, 100, 20)))
                    ie_result = self._real_extract(url)
                    if ie_result is None:
                        return None
                    if self._x_forwarded_for_ip:
                        ie_result['__x_forwarded_for_ip'] = self._x_forwarded_for_ip
                    subtitles = ie_result.get('subtitles') or {}
                    if 'no-live-chat' in self.get_param('compat_opts'):
                        for lang in ('live_chat', 'comments', 'danmaku'):
                            subtitles.pop(lang, None)
                    return ie_result
                except GeoRestrictedError as e:
                    if self.__maybe_fake_ip_and_retry(e.countries):
                        continue
                    raise
        except UnsupportedError:
            raise
        except ExtractorError as e:
            e.video_id = e.video_id or self.get_temp_id(url)
            e.ie = e.ie or self.IE_NAME
            e.traceback = e.traceback or sys.exc_info()[2]
            raise
        except IncompleteRead as e:
            raise ExtractorError('A network error has occurred.', cause=e, expected=True, video_id=self.get_temp_id(url))
        except (KeyError, StopIteration) as e:
            raise ExtractorError('An extractor error has occurred.', cause=e, video_id=self.get_temp_id(url))

    def __maybe_fake_ip_and_retry(self, countries):
        if (not self.get_param('geo_bypass_country', None)
                and self._GEO_BYPASS
                and self.get_param('geo_bypass', True)
                and not self._x_forwarded_for_ip
                and countries):
            country_code = random.choice(countries)
            self._x_forwarded_for_ip = GeoUtils.random_ipv4(country_code)
            if self._x_forwarded_for_ip:
                self.report_warning(
                    'Video is geo restricted. Retrying extraction with fake IP '
                    f'{self._x_forwarded_for_ip} ({country_code.upper()}) as X-Forwarded-For.')
                return True
        return False

    def set_downloader(self, downloader):
        """Sets a YoutubeDL instance as the downloader for this IE."""
        self._downloader = downloader

    @property
    def cache(self):
        return self._downloader.cache

    @property
    def cookiejar(self):
        return self._downloader.cookiejar

    def _initialize_pre_login(self):
        """ Initialization before login. Redefine in subclasses."""
        pass

    def _perform_login(self, username, password):
        """ Login with username and password. Redefine in subclasses."""
        pass

    def _real_initialize(self):
        """Real initialization process. Redefine in subclasses."""
        pass

    def _real_extract(self, url):
        """Real extraction process. Redefine in subclasses."""
        raise NotImplementedError('This method must be implemented by subclasses')

    @classmethod
    def ie_key(cls):
        """A string for getting the InfoExtractor with get_info_extractor"""
        return cls.__name__[:-2]

    @classproperty
    def IE_NAME(cls):
        return cls.__name__[:-2]

    @staticmethod
    def __can_accept_status_code(err, expected_status):
        assert isinstance(err, HTTPError)
        if expected_status is None:
            return False
        elif callable(expected_status):
            return expected_status(err.status) is True
        else:
            return err.status in variadic(expected_status)

    def _create_request(self, url_or_request, data=None, headers=None, query=None, extensions=None):
        if isinstance(url_or_request, urllib.request.Request):
            self._downloader.deprecation_warning(
                'Passing a urllib.request.Request to _create_request() is deprecated. '
                'Use yt_dlp.networking.common.Request instead.')
            url_or_request = urllib_req_to_req(url_or_request)
        elif not isinstance(url_or_request, Request):
            url_or_request = Request(url_or_request)

        url_or_request.update(data=data, headers=headers, query=query, extensions=extensions)
        return url_or_request

    def _request_webpage(self, url_or_request, video_id, note=None, errnote=None, fatal=True, data=None,
                         headers=None, query=None, expected_status=None, impersonate=None, require_impersonation=False):
        """
        Return the response handle.

        See _download_webpage docstring for arguments specification.
        """
        if not self._downloader._first_webpage_request:
            sleep_interval = self.get_param('sleep_interval_requests') or 0
            if sleep_interval > 0:
                self.to_screen(f'Sleeping {sleep_interval} seconds ...')
                time.sleep(sleep_interval)
        else:
            self._downloader._first_webpage_request = False

        if note is None:
            self.report_download_webpage(video_id)
        elif note is not False:
            if video_id is None:
                self.to_screen(str(note))
            else:
                self.to_screen(f'{video_id}: {note}')

        # Some sites check X-Forwarded-For HTTP header in order to figure out
        # the origin of the client behind proxy. This allows bypassing geo
        # restriction by faking this header's value to IP that belongs to some
        # geo unrestricted country. We will do so once we encounter any
        # geo restriction error.
        if self._x_forwarded_for_ip:
            headers = (headers or {}).copy()
            headers.setdefault('X-Forwarded-For', self._x_forwarded_for_ip)

        extensions = {}

        if impersonate in (True, ''):
            impersonate = ImpersonateTarget()
        requested_targets = [
            t if isinstance(t, ImpersonateTarget) else ImpersonateTarget.from_str(t)
            for t in variadic(impersonate)
        ] if impersonate else []

        available_target = next(filter(self._downloader._impersonate_target_available, requested_targets), None)
        if available_target:
            extensions['impersonate'] = available_target
        elif requested_targets:
            message = 'The extractor is attempting impersonation, but '
            message += (
                'no impersonate target is available' if not str(impersonate)
                else f'none of these impersonate targets are available: "{", ".join(map(str, requested_targets))}"')
            info_msg = ('see  https://github.com/yt-dlp/yt-dlp#impersonation  '
                        'for information on installing the required dependencies')
            if require_impersonation:
                raise ExtractorError(f'{message}; {info_msg}', expected=True)
            self.report_warning(f'{message}; if you encounter errors, then {info_msg}', only_once=True)

        try:
            return self._downloader.urlopen(self._create_request(url_or_request, data, headers, query, extensions))
        except network_exceptions as err:
            if isinstance(err, HTTPError):
                if self.__can_accept_status_code(err, expected_status):
                    return err.response

            if errnote is False:
                return False
            if errnote is None:
                errnote = 'Unable to download webpage'

            errmsg = f'{errnote}: {err}'
            if fatal:
                raise ExtractorError(errmsg, cause=err)
            else:
                self.report_warning(errmsg)
                return False

    def _download_webpage_handle(self, url_or_request, video_id, note=None, errnote=None, fatal=True,
                                 encoding=None, data=None, headers={}, query={}, expected_status=None,
                                 impersonate=None, require_impersonation=False):
        """
        Return a tuple (page content as string, URL handle).

        Arguments:
        url_or_request -- plain text URL as a string or
            a yt_dlp.networking.Request object
        video_id -- Video/playlist/item identifier (string)

        Keyword arguments:
        note -- note printed before downloading (string)
        errnote -- note printed in case of an error (string)
        fatal -- flag denoting whether error should be considered fatal,
            i.e. whether it should cause ExtractionError to be raised,
            otherwise a warning will be reported and extraction continued
        encoding -- encoding for a page content decoding, guessed automatically
            when not explicitly specified
        data -- POST data (bytes)
        headers -- HTTP headers (dict)
        query -- URL query (dict)
        expected_status -- allows to accept failed HTTP requests (non 2xx
            status code) by explicitly specifying a set of accepted status
            codes. Can be any of the following entities:
                - an integer type specifying an exact failed status code to
                  accept
                - a list or a tuple of integer types specifying a list of
                  failed status codes to accept
                - a callable accepting an actual failed status code and
                  returning True if it should be accepted
            Note that this argument does not affect success status codes (2xx)
            which are always accepted.
        impersonate -- the impersonate target. Can be any of the following entities:
                - an instance of yt_dlp.networking.impersonate.ImpersonateTarget
                - a string in the format of CLIENT[:OS]
                - a list or a tuple of CLIENT[:OS] strings or ImpersonateTarget instances
                - a boolean value; True means any impersonate target is sufficient
        require_impersonation -- flag to toggle whether the request should raise an error
            if impersonation is not possible (bool, default: False)
        """

        # Strip hashes from the URL (#1038)
        if isinstance(url_or_request, str):
            url_or_request = url_or_request.partition('#')[0]

        urlh = self._request_webpage(url_or_request, video_id, note, errnote, fatal, data=data,
                                     headers=headers, query=query, expected_status=expected_status,
                                     impersonate=impersonate, require_impersonation=require_impersonation)
        if urlh is False:
            assert not fatal
            return False
        content = self._webpage_read_content(urlh, url_or_request, video_id, note, errnote, fatal,
                                             encoding=encoding, data=data)
        if content is False:
            assert not fatal
            return False
        return (content, urlh)

    @staticmethod
    def _guess_encoding_from_content(content_type, webpage_bytes):
        m = re.match(r'[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+\s*;\s*charset=(.+)', content_type)
        if m:
            encoding = m.group(1)
        else:
            m = re.search(br'<meta[^>]+charset=[\'"]?([^\'")]+)[ /\'">]',
                          webpage_bytes[:1024])
            if m:
                encoding = m.group(1).decode('ascii')
            elif webpage_bytes.startswith(b'\xff\xfe'):
                encoding = 'utf-16'
            else:
                encoding = 'utf-8'

        return encoding

    def __check_blocked(self, content):
        first_block = content[:512]
        if ('<title>Access to this site is blocked</title>' in content
                and 'Websense' in first_block):
            msg = 'Access to this webpage has been blocked by Websense filtering software in your network.'
            blocked_iframe = self._html_search_regex(
                r'<iframe src="([^"]+)"', content,
                'Websense information URL', default=None)
            if blocked_iframe:
                msg += f' Visit {blocked_iframe} for more details'
            raise ExtractorError(msg, expected=True)
        if '<title>The URL you requested has been blocked</title>' in first_block:
            msg = (
                'Access to this webpage has been blocked by Indian censorship. '
                'Use a VPN or proxy server (with --proxy) to route around it.')
            block_msg = self._html_search_regex(
                r'</h1><p>(.*?)</p>',
                content, 'block message', default=None)
            if block_msg:
                msg += ' (Message: "{}")'.format(block_msg.replace('\n', ' '))
            raise ExtractorError(msg, expected=True)
        if ('<title>TTK :: Доступ к ресурсу ограничен</title>' in content
                and 'blocklist.rkn.gov.ru' in content):
            raise ExtractorError(
                'Access to this webpage has been blocked by decision of the Russian government. '
                'Visit http://blocklist.rkn.gov.ru/ for a block reason.',
                expected=True)

    def __decode_webpage(self, webpage_bytes, encoding, headers):
        if not encoding:
            encoding = self._guess_encoding_from_content(headers.get('Content-Type', ''), webpage_bytes)
        try:
            return webpage_bytes.decode(encoding, 'replace')
        except LookupError:
            return webpage_bytes.decode('utf-8', 'replace')

    def _webpage_read_content(self, urlh, url_or_request, video_id, note=None, errnote=None, fatal=True,
                              prefix=None, encoding=None, data=None):
        try:
            webpage_bytes = urlh.read()
        except TransportError as err:
            errmsg = f'{video_id}: Error reading response: {err.msg}'
            if fatal:
                raise ExtractorError(errmsg, cause=err)
            self.report_warning(errmsg)
            return False

        if prefix is not None:
            webpage_bytes = prefix + webpage_bytes
        if self.get_param('dump_intermediate_pages', False):
            self.to_screen('Dumping request to ' + urlh.url)
            dump = base64.b64encode(webpage_bytes).decode('ascii')
            self._downloader.to_screen(dump)
        if self.get_param('write_pages'):
            if isinstance(url_or_request, Request):
                data = self._create_request(url_or_request, data).data
            filename = _request_dump_filename(
                urlh.url, video_id, data,
                trim_length=self.get_param('trim_file_name'))
            self.to_screen(f'Saving request to {filename}')
            with open(filename, 'wb') as outf:
                outf.write(webpage_bytes)

        content = self.__decode_webpage(webpage_bytes, encoding, urlh.headers)
        self.__check_blocked(content)

        return content

    def __print_error(self, errnote, fatal, video_id, err):
        if fatal:
            raise ExtractorError(f'{video_id}: {errnote}', cause=err)
        elif errnote:
            self.report_warning(f'{video_id}: {errnote}: {err}')

    def _parse_xml(self, xml_string, video_id, transform_source=None, fatal=True, errnote=None):
        if transform_source:
            xml_string = transform_source(xml_string)
        try:
            return compat_etree_fromstring(xml_string.encode())
        except xml.etree.ElementTree.ParseError as ve:
            self.__print_error('Failed to parse XML' if errnote is None else errnote, fatal, video_id, ve)

    def _parse_json(self, json_string, video_id, transform_source=None, fatal=True, errnote=None, **parser_kwargs):
        try:
            return json.loads(
                json_string, cls=LenientJSONDecoder, strict=False, transform_source=transform_source, **parser_kwargs)
        except ValueError as ve:
            self.__print_error('Failed to parse JSON' if errnote is None else errnote, fatal, video_id, ve)

    def _parse_socket_response_as_json(self, data, *args, **kwargs):
        return self._parse_json(data[data.find('{'):data.rfind('}') + 1], *args, **kwargs)

    def __create_download_methods(name, parser, note, errnote, return_value):

        def parse(ie, content, *args, errnote=errnote, **kwargs):
            if parser is None:
                return content
            if errnote is False:
                kwargs['errnote'] = errnote
            # parser is fetched by name so subclasses can override it
            return getattr(ie, parser)(content, *args, **kwargs)

        def download_handle(self, url_or_request, video_id, note=note, errnote=errnote, transform_source=None,
                            fatal=True, encoding=None, data=None, headers={}, query={}, expected_status=None,
                            impersonate=None, require_impersonation=False):
            res = self._download_webpage_handle(
                url_or_request, video_id, note=note, errnote=errnote, fatal=fatal, encoding=encoding,
                data=data, headers=headers, query=query, expected_status=expected_status,
                impersonate=impersonate, require_impersonation=require_impersonation)
            if res is False:
                return res
            content, urlh = res
            return parse(self, content, video_id, transform_source=transform_source, fatal=fatal, errnote=errnote), urlh

        def download_content(self, url_or_request, video_id, note=note, errnote=errnote, transform_source=None,
                             fatal=True, encoding=None, data=None, headers={}, query={}, expected_status=None,
                             impersonate=None, require_impersonation=False):
            if self.get_param('load_pages'):
                url_or_request = self._create_request(url_or_request, data, headers, query)
                filename = _request_dump_filename(
                    url_or_request.url, video_id, url_or_request.data,
                    trim_length=self.get_param('trim_file_name'))
                self.to_screen(f'Loading request from {filename}')
                try:
                    with open(filename, 'rb') as dumpf:
                        webpage_bytes = dumpf.read()
                except OSError as e:
                    self.report_warning(f'Unable to load request from disk: {e}')
                else:
                    content = self.__decode_webpage(webpage_bytes, encoding, url_or_request.headers)
                    return parse(self, content, video_id, transform_source=transform_source, fatal=fatal, errnote=errnote)
            kwargs = {
                'note': note,
                'errnote': errnote,
                'transform_source': transform_source,
                'fatal': fatal,
                'encoding': encoding,
                'data': data,
                'headers': headers,
                'query': query,
                'expected_status': expected_status,
                'impersonate': impersonate,
                'require_impersonation': require_impersonation,
            }
            if parser is None:
                kwargs.pop('transform_source')
            # The method is fetched by name so subclasses can override _download_..._handle
            res = getattr(self, download_handle.__name__)(url_or_request, video_id, **kwargs)
            return res if res is False else res[0]

        def impersonate(func, name, return_value):
            func.__name__, func.__qualname__ = name, f'InfoExtractor.{name}'
            func.__doc__ = f'''
                @param transform_source     Apply this transformation before parsing
                @returns                    {return_value}

                See _download_webpage_handle docstring for other arguments specification
            '''

        impersonate(download_handle, f'_download_{name}_handle', f'({return_value}, URL handle)')
        impersonate(download_content, f'_download_{name}', f'{return_value}')
        return download_handle, download_content

    _download_xml_handle, _download_xml = __create_download_methods(
        'xml', '_parse_xml', 'Downloading XML', 'Unable to download XML', 'xml as an xml.etree.ElementTree.Element')
    _download_json_handle, _download_json = __create_download_methods(
        'json', '_parse_json', 'Downloading JSON metadata', 'Unable to download JSON metadata', 'JSON object as a dict')
    _download_socket_json_handle, _download_socket_json = __create_download_methods(
        'socket_json', '_parse_socket_response_as_json', 'Polling socket', 'Unable to poll socket', 'JSON object as a dict')
    __download_webpage = __create_download_methods('webpage', None, None, None, 'data of the page as a string')[1]

    def _download_webpage(
            self, url_or_request, video_id, note=None, errnote=None,
            fatal=True, tries=1, timeout=NO_DEFAULT, *args, **kwargs):
        """
        Return the data of the page as a string.

        Keyword arguments:
        tries -- number of tries
        timeout -- sleep interval between tries

        See _download_webpage_handle docstring for other arguments specification.
        """

        R''' # NB: These are unused; should they be deprecated?
        if tries != 1:
            self._downloader.deprecation_warning('tries argument is deprecated in InfoExtractor._download_webpage')
        if timeout is NO_DEFAULT:
            timeout = 5
        else:
            self._downloader.deprecation_warning('timeout argument is deprecated in InfoExtractor._download_webpage')
        '''

        try_count = 0
        while True:
            try:
                return self.__download_webpage(url_or_request, video_id, note, errnote, None, fatal, *args, **kwargs)
            except IncompleteRead as e:
                try_count += 1
                if try_count >= tries:
                    raise e
                self._sleep(timeout, video_id)

    def report_warning(self, msg, video_id=None, *args, only_once=False, **kwargs):
        idstr = format_field(video_id, None, '%s: ')
        msg = f'[{self.IE_NAME}] {idstr}{msg}'
        if only_once:
            if f'WARNING: {msg}' in self._printed_messages:
                return
            self._printed_messages.add(f'WARNING: {msg}')
        self._downloader.report_warning(msg, *args, **kwargs)

    def to_screen(self, msg, *args, **kwargs):
        """Print msg to screen, prefixing it with '[ie_name]'"""
        self._downloader.to_screen(f'[{self.IE_NAME}] {msg}', *args, **kwargs)

    def write_debug(self, msg, *args, **kwargs):
        self._downloader.write_debug(f'[{self.IE_NAME}] {msg}', *args, **kwargs)

    def get_param(self, name, default=None, *args, **kwargs):
        if self._downloader:
            return self._downloader.params.get(name, default, *args, **kwargs)
        return default

    def report_drm(self, video_id, partial=NO_DEFAULT):
        if partial is not NO_DEFAULT:
            self._downloader.deprecation_warning('InfoExtractor.report_drm no longer accepts the argument partial')
        self.raise_no_formats('This video is DRM protected', expected=True, video_id=video_id)

    def report_extraction(self, id_or_name):
        """Report information extraction."""
        self.to_screen(f'{id_or_name}: Extracting information')

    def report_download_webpage(self, video_id):
        """Report webpage download."""
        self.to_screen(f'{video_id}: Downloading webpage')

    def report_age_confirmation(self):
        """Report attempt to confirm age."""
        self.to_screen('Confirming age')

    def report_login(self):
        """Report attempt to log in."""
        self.to_screen('Logging in')

    def raise_login_required(
            self, msg='This video is only available for registered users',
            metadata_available=False, method=NO_DEFAULT):
        if metadata_available and (
                self.get_param('ignore_no_formats_error') or self.get_param('wait_for_video')):
            self.report_warning(msg)
            return
        msg += format_field(self._login_hint(method), None, '. %s')
        raise ExtractorError(msg, expected=True)

    def raise_geo_restricted(
            self, msg='This video is not available from your location due to geo restriction',
            countries=None, metadata_available=False):
        if metadata_available and (
                self.get_param('ignore_no_formats_error') or self.get_param('wait_for_video')):
            self.report_warning(msg)
        else:
            raise GeoRestrictedError(msg, countries=countries)

    def raise_no_formats(self, msg, expected=False, video_id=None):
        if expected and (
                self.get_param('ignore_no_formats_error') or self.get_param('wait_for_video')):
            self.report_warning(msg, video_id)
        elif isinstance(msg, ExtractorError):
            raise msg
        else:
            raise ExtractorError(msg, expected=expected, video_id=video_id)

    # Methods for following #608
    @staticmethod
    def url_result(url, ie=None, video_id=None, video_title=None, *, url_transparent=False, **kwargs):
        """Returns a URL that points to a page that should be processed"""
        if ie is not None:
            kwargs['ie_key'] = ie if isinstance(ie, str) else ie.ie_key()
        if video_id is not None:
            kwargs['id'] = video_id
        if video_title is not None:
            kwargs['title'] = video_title
        return {
            **kwargs,
            '_type': 'url_transparent' if url_transparent else 'url',
            'url': url,
        }

    @classmethod
    def playlist_from_matches(cls, matches, playlist_id=None, playlist_title=None,
                              getter=IDENTITY, ie=None, video_kwargs=None, **kwargs):
        return cls.playlist_result(
            (cls.url_result(m, ie, **(video_kwargs or {})) for m in orderedSet(map(getter, matches), lazy=True)),
            playlist_id, playlist_title, **kwargs)

    @staticmethod
    def playlist_result(entries, playlist_id=None, playlist_title=None, playlist_description=None, *, multi_video=False, **kwargs):
        """Returns a playlist"""
        if playlist_id:
            kwargs['id'] = playlist_id
        if playlist_title:
            kwargs['title'] = playlist_title
        if playlist_description is not None:
            kwargs['description'] = playlist_description
        return {
            **kwargs,
            '_type': 'multi_video' if multi_video else 'playlist',
            'entries': entries,
        }

    def _search_regex(self, pattern, string, name, default=NO_DEFAULT, fatal=True, flags=0, group=None):
        """
        Perform a regex search on the given string, using a single or a list of
        patterns returning the first matching group.
        In case of failure return a default value or raise a WARNING or a
        RegexNotFoundError, depending on fatal, specifying the field name.
        """
        if string is None:
            mobj = None
        elif isinstance(pattern, (str, re.Pattern)):
            mobj = re.search(pattern, string, flags)
        else:
            for p in pattern:
                mobj = re.search(p, string, flags)
                if mobj:
                    break

        _name = self._downloader._format_err(name, self._downloader.Styles.EMPHASIS)

        if mobj:
            if group is None:
                # return the first matching group
                return next(g for g in mobj.groups() if g is not None)
            elif isinstance(group, (list, tuple)):
                return tuple(mobj.group(g) for g in group)
            else:
                return mobj.group(group)
        elif default is not NO_DEFAULT:
            return default
        elif fatal:
            raise RegexNotFoundError(f'Unable to extract {_name}')
        else:
            self.report_warning(f'unable to extract {_name}' + bug_reports_message())
            return None

    def _search_json(self, start_pattern, string, name, video_id, *, end_pattern='',
                     contains_pattern=r'{(?s:.+)}', fatal=True, default=NO_DEFAULT, **kwargs):
        """Searches string for the JSON object specified by start_pattern"""
        # NB: end_pattern is only used to reduce the size of the initial match
        if default is NO_DEFAULT:
            default, has_default = {}, False
        else:
            fatal, has_default = False, True

        json_string = self._search_regex(
            rf'(?:{start_pattern})\s*(?P<json>{contains_pattern})\s*(?:{end_pattern})',
            string, name, group='json', fatal=fatal, default=None if has_default else NO_DEFAULT)
        if not json_string:
            return default

        _name = self._downloader._format_err(name, self._downloader.Styles.EMPHASIS)
        try:
            return self._parse_json(json_string, video_id, ignore_extra=True, **kwargs)
        except ExtractorError as e:
            if fatal:
                raise ExtractorError(
                    f'Unable to extract {_name} - Failed to parse JSON', cause=e.cause, video_id=video_id)
            elif not has_default:
                self.report_warning(
                    f'Unable to extract {_name} - Failed to parse JSON: {e}', video_id=video_id)
        return default

    def _html_search_regex(self, pattern, string, name, default=NO_DEFAULT, fatal=True, flags=0, group=None):
        """
        Like _search_regex, but strips HTML tags and unescapes entities.
        """
        res = self._search_regex(pattern, string, name, default, fatal, flags, group)
        if isinstance(res, tuple):
            return tuple(map(clean_html, res))
        return clean_html(res)

    def _get_netrc_login_info(self, netrc_machine=None):
        netrc_machine = netrc_machine or self._NETRC_MACHINE

        cmd = self.get_param('netrc_cmd')
        if cmd:
            cmd = cmd.replace('{}', netrc_machine)
            self.to_screen(f'Executing command: {cmd}')
            stdout, _, ret = Popen.run(cmd, text=True, shell=True, stdout=subprocess.PIPE)
            if ret != 0:
                raise OSError(f'Command returned error code {ret}')
            info = netrc_from_content(stdout).authenticators(netrc_machine)

        elif self.get_param('usenetrc', False):
            netrc_file = compat_expanduser(self.get_param('netrc_location') or '~')
            if os.path.isdir(netrc_file):
                netrc_file = os.path.join(netrc_file, '.netrc')
            info = netrc.netrc(netrc_file).authenticators(netrc_machine)

        else:
            return None, None
        if not info:
            self.to_screen(f'No authenticators for {netrc_machine}')
            return None, None

        self.write_debug(f'Using netrc for {netrc_machine} authentication')

        # compat: <=py3.10: netrc cannot parse tokens as empty strings, will return `""` instead
        # Ref: https://github.com/yt-dlp/yt-dlp/issues/11413
        #      https://github.com/python/cpython/commit/15409c720be0503131713e3d3abc1acd0da07378
        if sys.version_info < (3, 11):
            return tuple(x if x != '""' else '' for x in info[::2])

        return info[0], info[2]

    def _get_login_info(self, username_option='username', password_option='password', netrc_machine=None):
        """
        Get the login info as (username, password)
        First look for the manually specified credentials using username_option
        and password_option as keys in params dictionary. If no such credentials
        are available try the netrc_cmd if it is defined or look in the
        netrc file using the netrc_machine or _NETRC_MACHINE value.
        If there's no info available, return (None, None)
        """

        username = self.get_param(username_option)
        if username is not None:
            password = self.get_param(password_option)
        else:
            try:
                username, password = self._get_netrc_login_info(netrc_machine)
            except (OSError, netrc.NetrcParseError) as err:
                self.report_warning(f'Failed to parse .netrc: {err}')
                return None, None
        return username, password

    def _get_tfa_info(self, note='two-factor verification code'):
        """
        Get the two-factor authentication info
        TODO - asking the user will be required for sms/phone verify
        currently just uses the command line option
        If there's no info available, return None
        """

        tfa = self.get_param('twofactor')
        if tfa is not None:
            return tfa

        return getpass.getpass(f'Type {note} and press [Return]: ')

    # Helper functions for extracting OpenGraph info
    @staticmethod
    def _og_regexes(prop):
        content_re = r'content=(?:"([^"]+?)"|\'([^\']+?)\'|\s*([^\s"\'=<>`]+?)(?=\s|/?>))'
        property_re = r'(?:name|property)=(?:\'og{sep}{prop}\'|"og{sep}{prop}"|\s*og{sep}{prop}\b)'.format(
            prop=re.escape(prop), sep='(?:&#x3A;|[:-])')
        template = r'<meta[^>]+?%s[^>]+?%s'
        return [
            template % (property_re, content_re),
            template % (content_re, property_re),
        ]

    @staticmethod
    def _meta_regex(prop):
        return rf'''(?isx)<meta
                    (?=[^>]+(?:itemprop|name|property|id|http-equiv)=(["\']?){re.escape(prop)}\1)
                    [^>]+?content=(["\'])(?P<content>.*?)\2'''

    def _og_search_property(self, prop, html, name=None, **kargs):
        prop = variadic(prop)
        if name is None:
            name = f'OpenGraph {prop[0]}'
        og_regexes = []
        for p in prop:
            og_regexes.extend(self._og_regexes(p))
        escaped = self._search_regex(og_regexes, html, name, flags=re.DOTALL, **kargs)
        if escaped is None:
            return None
        return unescapeHTML(escaped)

    def _og_search_thumbnail(self, html, **kargs):
        return self._og_search_property('image', html, 'thumbnail URL', fatal=False, **kargs)

    def _og_search_description(self, html, **kargs):
        return self._og_search_property('description', html, fatal=False, **kargs)

    def _og_search_title(self, html, *, fatal=False, **kargs):
        return self._og_search_property('title', html, fatal=fatal, **kargs)

    def _og_search_video_url(self, html, name='video url', secure=True, **kargs):
        regexes = self._og_regexes('video') + self._og_regexes('video:url')
        if secure:
            regexes = self._og_regexes('video:secure_url') + regexes
        return self._html_search_regex(regexes, html, name, **kargs)

    def _og_search_url(self, html, **kargs):
        return self._og_search_property('url', html, **kargs)

    def _html_extract_title(self, html, name='title', *, fatal=False, **kwargs):
        return self._html_search_regex(r'(?s)<title\b[^>]*>([^<]+)</title>', html, name, fatal=fatal, **kwargs)

    def _html_search_meta(self, name, html, display_name=None, fatal=False, **kwargs):
        name = variadic(name)
        if display_name is None:
            display_name = name[0]
        return self._html_search_regex(
            [self._meta_regex(n) for n in name],
            html, display_name, fatal=fatal, group='content', **kwargs)

    def _dc_search_uploader(self, html):
        return self._html_search_meta('dc.creator', html, 'uploader')

    @staticmethod
    def _rta_search(html):
        # See http://www.rtalabel.org/index.php?content=howtofaq#single
        if re.search(r'(?ix)<meta\s+name="rating"\s+'
                     r'     content="RTA-5042-1996-1400-1577-RTA"',
                     html):
            return 18

        # And then there are the jokers who advertise that they use RTA, but actually don't.
        AGE_LIMIT_MARKERS = [
            r'Proudly Labeled <a href="http://www\.rtalabel\.org/" title="Restricted to Adults">RTA</a>',
            r'>[^<]*you acknowledge you are at least (\d+) years old',
            r'>\s*(?:18\s+U(?:\.S\.C\.|SC)\s+)?(?:§+\s*)?2257\b',
        ]

        age_limit = 0
        for marker in AGE_LIMIT_MARKERS:
            mobj = re.search(marker, html)
            if mobj:
                age_limit = max(age_limit, int(traverse_obj(mobj, 1, default=18)))
        return age_limit

    def _media_rating_search(self, html):
        # See http://www.tjg-designs.com/WP/metadata-code-examples-adding-metadata-to-your-web-pages/
        rating = self._html_search_meta('rating', html)

        if not rating:
            return None

        RATING_TABLE = {
            'safe for kids': 0,
            'general': 8,
            '14 years': 14,
            'mature': 17,
            'restricted': 19,
        }
        return RATING_TABLE.get(rating.lower())

    def _family_friendly_search(self, html):
        # See http://schema.org/VideoObject
        family_friendly = self._html_search_meta(
            'isFamilyFriendly', html, default=None)

        if not family_friendly:
            return None

        RATING_TABLE = {
            '1': 0,
            'true': 0,
            '0': 18,
            'false': 18,
        }
        return RATING_TABLE.get(family_friendly.lower())

    def _twitter_search_player(self, html):
        return self._html_search_meta('twitter:player', html,
                                      'twitter card player')

    def _yield_json_ld(self, html, video_id, *, fatal=True, default=NO_DEFAULT):
        """Yield all json ld objects in the html"""
        if default is not NO_DEFAULT:
            fatal = False
        for mobj in re.finditer(JSON_LD_RE, html):
            json_ld_item = self._parse_json(
                mobj.group('json_ld'), video_id, fatal=fatal,
                errnote=False if default is not NO_DEFAULT else None)
            for json_ld in variadic(json_ld_item):
                if isinstance(json_ld, dict):
                    yield json_ld

    def _search_json_ld(self, html, video_id, expected_type=None, *, fatal=True, default=NO_DEFAULT):
        """Search for a video in any json ld in the html"""
        if default is not NO_DEFAULT:
            fatal = False
        info = self._json_ld(
            list(self._yield_json_ld(html, video_id, fatal=fatal, default=default)),
            video_id, fatal=fatal, expected_type=expected_type)
        if info:
            return info
        if default is not NO_DEFAULT:
            return default
        elif fatal:
            raise RegexNotFoundError('Unable to extract JSON-LD')
        else:
            self.report_warning(f'unable to extract JSON-LD {bug_reports_message()}')
            return {}

    def _json_ld(self, json_ld, video_id, fatal=True, expected_type=None):
        if isinstance(json_ld, str):
            json_ld = self._parse_json(json_ld, video_id, fatal=fatal)
        if not json_ld:
            return {}
        info = {}

        INTERACTION_TYPE_MAP = {
            'CommentAction': 'comment',
            'AgreeAction': 'like',
            'DisagreeAction': 'dislike',
            'LikeAction': 'like',
            'DislikeAction': 'dislike',
            'ListenAction': 'view',
            'WatchAction': 'view',
            'ViewAction': 'view',
        }

        def is_type(e, *expected_types):
            type_ = variadic(traverse_obj(e, '@type'))
            return any(x in type_ for x in expected_types)

        def extract_interaction_type(e):
            interaction_type = e.get('interactionType')
            if isinstance(interaction_type, dict):
                interaction_type = interaction_type.get('@type')
            return str_or_none(interaction_type)

        def extract_interaction_statistic(e):
            interaction_statistic = e.get('interactionStatistic')
            if isinstance(interaction_statistic, dict):
                interaction_statistic = [interaction_statistic]
            if not isinstance(interaction_statistic, list):
                return
            for is_e in interaction_statistic:
                if not is_type(is_e, 'InteractionCounter'):
                    continue
                interaction_type = extract_interaction_type(is_e)
                if not interaction_type:
                    continue
                # For interaction count some sites provide string instead of
                # an integer (as per spec) with non digit characters (e.g. ",")
                # so extracting count with more relaxed str_to_int
                interaction_count = str_to_int(is_e.get('userInteractionCount'))
                if interaction_count is None:
                    continue
                count_kind = INTERACTION_TYPE_MAP.get(interaction_type.split('/')[-1])
                if not count_kind:
                    continue
                count_key = f'{count_kind}_count'
                if info.get(count_key) is not None:
                    continue
                info[count_key] = interaction_count

        def extract_chapter_information(e):
            chapters = [{
                'title': part.get('name'),
                'start_time': part.get('startOffset'),
                'end_time': part.get('endOffset'),
            } for part in variadic(e.get('hasPart') or []) if part.get('@type') == 'Clip']
            for idx, (last_c, current_c, next_c) in enumerate(zip(
                    [{'end_time': 0}, *chapters], chapters, chapters[1:])):
                current_c['end_time'] = current_c['end_time'] or next_c['start_time']
                current_c['start_time'] = current_c['start_time'] or last_c['end_time']
                if None in current_c.values():
                    self.report_warning(f'Chapter {idx} contains broken data. Not extracting chapters')
                    return
            if chapters:
                chapters[-1]['end_time'] = chapters[-1]['end_time'] or info['duration']
                info['chapters'] = chapters

        def extract_video_object(e):
            author = e.get('author')
            info.update({
                'url': url_or_none(e.get('contentUrl')),
                'ext': mimetype2ext(e.get('encodingFormat')),
                'title': unescapeHTML(e.get('name')),
                'description': unescapeHTML(e.get('description')),
                'thumbnails': [{'url': unescapeHTML(url)}
                               for url in variadic(traverse_obj(e, 'thumbnailUrl', 'thumbnailURL'))
                               if url_or_none(url)],
                'duration': parse_duration(e.get('duration')),
                'timestamp': unified_timestamp(e.get('uploadDate')),
                # author can be an instance of 'Organization' or 'Person' types.
                # both types can have 'name' property(inherited from 'Thing' type). [1]
                # however some websites are using 'Text' type instead.
                # 1. https://schema.org/VideoObject
                'uploader': author.get('name') if isinstance(author, dict) else author if isinstance(author, str) else None,
                'artist': traverse_obj(e, ('byArtist', 'name'), expected_type=str),
                'filesize': int_or_none(float_or_none(e.get('contentSize'))),
                'tbr': int_or_none(e.get('bitrate')),
                'width': int_or_none(e.get('width')),
                'height': int_or_none(e.get('height')),
                'view_count': int_or_none(e.get('interactionCount')),
                'tags': try_call(lambda: e.get('keywords').split(',')),
            })
            if is_type(e, 'AudioObject'):
                info.update({
                    'vcodec': 'none',
                    'abr': int_or_none(e.get('bitrate')),
                })
            extract_interaction_statistic(e)
            extract_chapter_information(e)

        def traverse_json_ld(json_ld, at_top_level=True):
            for e in variadic(json_ld):
                if not isinstance(e, dict):
                    continue
                if at_top_level and '@context' not in e:
                    continue
                if at_top_level and set(e.keys()) == {'@context', '@graph'}:
                    traverse_json_ld(e['@graph'], at_top_level=False)
                    continue
                if expected_type is not None and not is_type(e, expected_type):
                    continue
                rating = traverse_obj(e, ('aggregateRating', 'ratingValue'), expected_type=float_or_none)
                if rating is not None:
                    info['average_rating'] = rating
                if is_type(e, 'TVEpisode', 'Episode', 'PodcastEpisode'):
                    episode_name = unescapeHTML(e.get('name'))
                    info.update({
                        'episode': episode_name,
                        'episode_number': int_or_none(e.get('episodeNumber')),
                        'description': unescapeHTML(e.get('description')),
                    })
                    if not info.get('title') and episode_name:
                        info['title'] = episode_name
                    part_of_season = e.get('partOfSeason')
                    if is_type(part_of_season, 'TVSeason', 'Season', 'CreativeWorkSeason'):
                        info.update({
                            'season': unescapeHTML(part_of_season.get('name')),
                            'season_number': int_or_none(part_of_season.get('seasonNumber')),
                        })
                    part_of_series = e.get('partOfSeries') or e.get('partOfTVSeries')
                    if is_type(part_of_series, 'TVSeries', 'Series', 'CreativeWorkSeries'):
                        info['series'] = unescapeHTML(part_of_series.get('name'))
                elif is_type(e, 'Movie'):
                    info.update({
                        'title': unescapeHTML(e.get('name')),
                        'description': unescapeHTML(e.get('description')),
                        'duration': parse_duration(e.get('duration')),
                        'timestamp': unified_timestamp(e.get('dateCreated')),
                    })
                elif is_type(e, 'Article', 'NewsArticle'):
                    info.update({
                        'timestamp': parse_iso8601(e.get('datePublished')),
                        'title': unescapeHTML(e.get('headline')),
                        'description': unescapeHTML(e.get('articleBody') or e.get('description')),
                    })
                    if is_type(traverse_obj(e, ('video', 0)), 'VideoObject'):
                        extract_video_object(e['video'][0])
                    elif is_type(traverse_obj(e, ('subjectOf', 0)), 'VideoObject'):
                        extract_video_object(e['subjectOf'][0])
                elif is_type(e, 'VideoObject', 'AudioObject'):
                    extract_video_object(e)
                    if expected_type is None:
                        continue
                    else:
                        break
                video = e.get('video')
                if is_type(video, 'VideoObject'):
                    extract_video_object(video)
                if expected_type is None:
                    continue
                else:
                    break

        traverse_json_ld(json_ld)
        return filter_dict(info)

    def _search_nextjs_data(self, webpage, video_id, *, fatal=True, default=NO_DEFAULT, **kw):
        if default == '{}':
            self._downloader.deprecation_warning('using `default=\'{}\'` is deprecated, use `default={}` instead')
            default = {}
        if default is not NO_DEFAULT:
            fatal = False

        return self._search_json(
            r'<script[^>]+id=[\'"]__NEXT_DATA__[\'"][^>]*>', webpage, 'next.js data',
            video_id, end_pattern='</script>', fatal=fatal, default=default, **kw)

    def _search_nuxt_data(self, webpage, video_id, context_name='__NUXT__', *, fatal=True, traverse=('data', 0)):
        """Parses Nuxt.js metadata. This works as long as the function __NUXT__ invokes is a pure function"""
        rectx = re.escape(context_name)
        FUNCTION_RE = r'\(function\((?P<arg_keys>.*?)\){.*?\breturn\s+(?P<js>{.*?})\s*;?\s*}\((?P<arg_vals>.*?)\)'
        js, arg_keys, arg_vals = self._search_regex(
            (rf'<script>\s*window\.{rectx}={FUNCTION_RE}\s*\)\s*;?\s*</script>', rf'{rectx}\(.*?{FUNCTION_RE}'),
            webpage, context_name, group=('js', 'arg_keys', 'arg_vals'),
            default=NO_DEFAULT if fatal else (None, None, None))
        if js is None:
            return {}

        args = dict(zip(arg_keys.split(','), map(json.dumps, self._parse_json(
            f'[{arg_vals}]', video_id, transform_source=js_to_json, fatal=fatal) or ())))

        ret = self._parse_json(js, video_id, transform_source=functools.partial(js_to_json, vars=args), fatal=fatal)
        return traverse_obj(ret, traverse) or {}

    @staticmethod
    def _hidden_inputs(html):
        html = re.sub(r'<!--(?:(?!<!--).)*-->', '', html)
        hidden_inputs = {}
        for input_el in re.findall(r'(?i)(<input[^>]+>)', html):
            attrs = extract_attributes(input_el)
            if not input_el:
                continue
            if attrs.get('type') not in ('hidden', 'submit'):
                continue
            name = attrs.get('name') or attrs.get('id')
            value = attrs.get('value')
            if name and value is not None:
                hidden_inputs[name] = value
        return hidden_inputs

    def _form_hidden_inputs(self, form_id, html):
        form = self._search_regex(
            rf'(?is)<form[^>]+?id=(["\']){form_id}\1[^>]*>(?P<form>.+?)</form>',
            html, f'{form_id} form', group='form')
        return self._hidden_inputs(form)

    @classproperty(cache=True)
    def FormatSort(cls):
        class FormatSort(FormatSorter):
            def __init__(ie, *args, **kwargs):
                super().__init__(ie._downloader, *args, **kwargs)

        deprecation_warning(
            'yt_dlp.InfoExtractor.FormatSort is deprecated and may be removed in the future. '
            'Use yt_dlp.utils.FormatSorter instead')
        return FormatSort

    def _sort_formats(self, formats, field_preference=[]):
        if not field_preference:
            self._downloader.deprecation_warning(
                'yt_dlp.InfoExtractor._sort_formats is deprecated and is no longer required')
            return
        self._downloader.deprecation_warning(
            'yt_dlp.InfoExtractor._sort_formats is deprecated and no longer works as expected. '
            'Return _format_sort_fields in the info_dict instead')
        if formats:
            formats[0]['__sort_fields'] = field_preference

    def _check_formats(self, formats, video_id):
        if formats:
            formats[:] = filter(
                lambda f: self._is_valid_url(
                    f['url'], video_id,
                    item='{} video format'.format(f.get('format_id')) if f.get('format_id') else 'video'),
                formats)

    @staticmethod
    def _remove_duplicate_formats(formats):
        seen_urls = set()
        seen_fragment_urls = set()
        unique_formats = []
        for f in formats:
            fragments = f.get('fragments')
            if callable(fragments):
                unique_formats.append(f)

            elif fragments:
                fragment_urls = frozenset(
                    fragment.get('url') or urljoin(f['fragment_base_url'], fragment['path'])
                    for fragment in fragments)
                if fragment_urls not in seen_fragment_urls:
                    seen_fragment_urls.add(fragment_urls)
                    unique_formats.append(f)

            elif f['url'] not in seen_urls:
                seen_urls.add(f['url'])
                unique_formats.append(f)

        formats[:] = unique_formats

    def _is_valid_url(self, url, video_id, item='video', headers={}):
        url = self._proto_relative_url(url, scheme='http:')
        # For now assume non HTTP(S) URLs always valid
        if not url.startswith(('http://', 'https://')):
            return True
        try:
            self._request_webpage(url, video_id, f'Checking {item} URL', headers=headers)
            return True
        except ExtractorError as e:
            self.to_screen(
                f'{video_id}: {item} URL is invalid, skipping: {e.cause!s}')
            return False

    def http_scheme(self):
        """ Either "http:" or "https:", depending on the user's preferences """
        return (
            'http:'
            if self.get_param('prefer_insecure', False)
            else 'https:')

    def _proto_relative_url(self, url, scheme=None):
        scheme = scheme or self.http_scheme()
        assert scheme.endswith(':')
        return sanitize_url(url, scheme=scheme[:-1])

    def _sleep(self, timeout, video_id, msg_template=None):
        if msg_template is None:
            msg_template = '%(video_id)s: Waiting for %(timeout)s seconds'
        msg = msg_template % {'video_id': video_id, 'timeout': timeout}
        self.to_screen(msg)
        time.sleep(timeout)

    def _extract_f4m_formats(self, manifest_url, video_id, preference=None, quality=None, f4m_id=None,
                             transform_source=lambda s: fix_xml_ampersands(s).strip(),
                             fatal=True, m3u8_id=None, data=None, headers={}, query={}):
        if self.get_param('ignore_no_formats_error'):
            fatal = False

        res = self._download_xml_handle(
            manifest_url, video_id, 'Downloading f4m manifest',
            'Unable to download f4m manifest',
            # Some manifests may be malformed, e.g. prosiebensat1 generated manifests
            # (see https://github.com/ytdl-org/youtube-dl/issues/6215#issuecomment-121704244)
            transform_source=transform_source,
            fatal=fatal, data=data, headers=headers, query=query)
        if res is False:
            return []

        manifest, urlh = res
        manifest_url = urlh.url

        return self._parse_f4m_formats(
            manifest, manifest_url, video_id, preference=preference, quality=quality, f4m_id=f4m_id,
            transform_source=transform_source, fatal=fatal, m3u8_id=m3u8_id)

    def _parse_f4m_formats(self, manifest, manifest_url, video_id, preference=None, quality=None, f4m_id=None,
                           transform_source=lambda s: fix_xml_ampersands(s).strip(),
                           fatal=True, m3u8_id=None):
        if not isinstance(manifest, xml.etree.ElementTree.Element) and not fatal:
            return []

        # currently yt-dlp cannot decode the playerVerificationChallenge as Akamai uses Adobe Alchemy
        akamai_pv = manifest.find('{http://ns.adobe.com/f4m/1.0}pv-2.0')
        if akamai_pv is not None and ';' in akamai_pv.text:
            player_verification_challenge = akamai_pv.text.split(';')[0]
            if player_verification_challenge.strip() != '':
                return []

        formats = []
        manifest_version = '1.0'
        media_nodes = manifest.findall('{http://ns.adobe.com/f4m/1.0}media')
        if not media_nodes:
            manifest_version = '2.0'
            media_nodes = manifest.findall('{http://ns.adobe.com/f4m/2.0}media')
        # Remove unsupported DRM protected media from final formats
        # rendition (see https://github.com/ytdl-org/youtube-dl/issues/8573).
        media_nodes = remove_encrypted_media(media_nodes)
        if not media_nodes:
            return formats

        manifest_base_url = get_base_url(manifest)

        bootstrap_info = xpath_element(
            manifest, ['{http://ns.adobe.com/f4m/1.0}bootstrapInfo', '{http://ns.adobe.com/f4m/2.0}bootstrapInfo'],
            'bootstrap info', default=None)

        vcodec = None
        mime_type = xpath_text(
            manifest, ['{http://ns.adobe.com/f4m/1.0}mimeType', '{http://ns.adobe.com/f4m/2.0}mimeType'],
            'base URL', default=None)
        if mime_type and mime_type.startswith('audio/'):
            vcodec = 'none'

        for i, media_el in enumerate(media_nodes):
            tbr = int_or_none(media_el.attrib.get('bitrate'))
            width = int_or_none(media_el.attrib.get('width'))
            height = int_or_none(media_el.attrib.get('height'))
            format_id = join_nonempty(f4m_id, tbr or i)
            # If <bootstrapInfo> is present, the specified f4m is a
            # stream-level manifest, and only set-level manifests may refer to
            # external resources.  See section 11.4 and section 4 of F4M spec
            if bootstrap_info is None:
                media_url = None
                # @href is introduced in 2.0, see section 11.6 of F4M spec
                if manifest_version == '2.0':
                    media_url = media_el.attrib.get('href')
                if media_url is None:
                    media_url = media_el.attrib.get('url')
                if not media_url:
                    continue
                manifest_url = (
                    media_url if media_url.startswith(('http://', 'https://'))
                    else ((manifest_base_url or '/'.join(manifest_url.split('/')[:-1])) + '/' + media_url))
                # If media_url is itself a f4m manifest do the recursive extraction
                # since bitrates in parent manifest (this one) and media_url manifest
                # may differ leading to inability to resolve the format by requested
                # bitrate in f4m downloader
                ext = determine_ext(manifest_url)
                if ext == 'f4m':
                    f4m_formats = self._extract_f4m_formats(
                        manifest_url, video_id, preference=preference, quality=quality, f4m_id=f4m_id,
                        transform_source=transform_source, fatal=fatal)
                    # Sometimes stream-level manifest contains single media entry that
                    # does not contain any quality metadata (e.g. http://matchtv.ru/#live-player).
                    # At the same time parent's media entry in set-level manifest may
                    # contain it. We will copy it from parent in such cases.
                    if len(f4m_formats) == 1:
                        f = f4m_formats[0]
                        f.update({
                            'tbr': f.get('tbr') or tbr,
                            'width': f.get('width') or width,
                            'height': f.get('height') or height,
                            'format_id': f.get('format_id') if not tbr else format_id,
                            'vcodec': vcodec,
                        })
                    formats.extend(f4m_formats)
                    continue
                elif ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        manifest_url, video_id, 'mp4', preference=preference,
                        quality=quality, m3u8_id=m3u8_id, fatal=fatal))
                    continue
            formats.append({
                'format_id': format_id,
                'url': manifest_url,
                'manifest_url': manifest_url,
                'ext': 'flv' if bootstrap_info is not None else None,
                'protocol': 'f4m',
                'tbr': tbr,
                'width': width,
                'height': height,
                'vcodec': vcodec,
                'preference': preference,
                'quality': quality,
            })
        return formats

    def _m3u8_meta_format(self, m3u8_url, ext=None, preference=None, quality=None, m3u8_id=None):
        return {
            'format_id': join_nonempty(m3u8_id, 'meta'),
            'url': m3u8_url,
            'ext': ext,
            'protocol': 'm3u8',
            'preference': preference - 100 if preference else -100,
            'quality': quality,
            'resolution': 'multiple',
            'format_note': 'Quality selection URL',
        }

    def _report_ignoring_subs(self, name):
        self.report_warning(bug_reports_message(
            f'Ignoring subtitle tracks found in the {name} manifest; '
            'if any subtitle tracks are missing,',
        ), only_once=True)

    def _extract_m3u8_formats(self, *args, **kwargs):
        fmts, subs = self._extract_m3u8_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('HLS')
        return fmts

    def _extract_m3u8_formats_and_subtitles(
            self, m3u8_url, video_id, ext=None, entry_protocol='m3u8_native',
            preference=None, quality=None, m3u8_id=None, note=None,
            errnote=None, fatal=True, live=False, data=None, headers={},
            query={}):

        if self.get_param('ignore_no_formats_error'):
            fatal = False

        if not m3u8_url:
            if errnote is not False:
                errnote = errnote or 'Failed to obtain m3u8 URL'
                if fatal:
                    raise ExtractorError(errnote, video_id=video_id)
                self.report_warning(f'{errnote}{bug_reports_message()}')
            return [], {}

        res = self._download_webpage_handle(
            m3u8_url, video_id,
            note='Downloading m3u8 information' if note is None else note,
            errnote='Failed to download m3u8 information' if errnote is None else errnote,
            fatal=fatal, data=data, headers=headers, query=query)

        if res is False:
            return [], {}

        m3u8_doc, urlh = res
        m3u8_url = urlh.url

        return self._parse_m3u8_formats_and_subtitles(
            m3u8_doc, m3u8_url, ext=ext, entry_protocol=entry_protocol,
            preference=preference, quality=quality, m3u8_id=m3u8_id,
            note=note, errnote=errnote, fatal=fatal, live=live, data=data,
            headers=headers, query=query, video_id=video_id)

    def _parse_m3u8_formats_and_subtitles(
            self, m3u8_doc, m3u8_url=None, ext=None, entry_protocol='m3u8_native',
            preference=None, quality=None, m3u8_id=None, live=False, note=None,
            errnote=None, fatal=True, data=None, headers={}, query={},
            video_id=None):
        formats, subtitles = [], {}
        has_drm = HlsFD._has_drm(m3u8_doc)

        def format_url(url):
            return url if re.match(r'https?://', url) else urllib.parse.urljoin(m3u8_url, url)

        if self.get_param('hls_split_discontinuity', False):
            def _extract_m3u8_playlist_indices(manifest_url=None, m3u8_doc=None):
                if not m3u8_doc:
                    if not manifest_url:
                        return []
                    m3u8_doc = self._download_webpage(
                        manifest_url, video_id, fatal=fatal, data=data, headers=headers,
                        note=False, errnote='Failed to download m3u8 playlist information')
                    if m3u8_doc is False:
                        return []
                return range(1 + sum(line.startswith('#EXT-X-DISCONTINUITY') for line in m3u8_doc.splitlines()))

        else:
            def _extract_m3u8_playlist_indices(*args, **kwargs):
                return [None]

        # References:
        # 1. https://tools.ietf.org/html/draft-pantos-http-live-streaming-21
        # 2. https://github.com/ytdl-org/youtube-dl/issues/12211
        # 3. https://github.com/ytdl-org/youtube-dl/issues/18923

        # We should try extracting formats only from master playlists [1, 4.3.4],
        # i.e. playlists that describe available qualities. On the other hand
        # media playlists [1, 4.3.3] should be returned as is since they contain
        # just the media without qualities renditions.
        # Fortunately, master playlist can be easily distinguished from media
        # playlist based on particular tags availability. As of [1, 4.3.3, 4.3.4]
        # master playlist tags MUST NOT appear in a media playlist and vice versa.
        # As of [1, 4.3.3.1] #EXT-X-TARGETDURATION tag is REQUIRED for every
        # media playlist and MUST NOT appear in master playlist thus we can
        # clearly detect media playlist with this criterion.

        if '#EXT-X-TARGETDURATION' in m3u8_doc:  # media playlist, return as is
            formats = [{
                'format_id': join_nonempty(m3u8_id, idx),
                'format_index': idx,
                'url': m3u8_url or encode_data_uri(m3u8_doc.encode(), 'application/x-mpegurl'),
                'ext': ext,
                'protocol': entry_protocol,
                'preference': preference,
                'quality': quality,
                'has_drm': has_drm,
            } for idx in _extract_m3u8_playlist_indices(m3u8_doc=m3u8_doc)]

            return formats, subtitles

        groups = {}
        last_stream_inf = {}

        def extract_media(x_media_line):
            media = parse_m3u8_attributes(x_media_line)
            # As per [1, 4.3.4.1] TYPE, GROUP-ID and NAME are REQUIRED
            media_type, group_id, name = media.get('TYPE'), media.get('GROUP-ID'), media.get('NAME')
            if not (media_type and group_id and name):
                return
            groups.setdefault(group_id, []).append(media)
            # <https://tools.ietf.org/html/rfc8216#section-4.3.4.1>
            if media_type == 'SUBTITLES':
                # According to RFC 8216 §4.3.4.2.1, URI is REQUIRED in the
                # EXT-X-MEDIA tag if the media type is SUBTITLES.
                # However, lack of URI has been spotted in the wild.
                # e.g. NebulaIE; see https://github.com/yt-dlp/yt-dlp/issues/339
                if not media.get('URI'):
                    return
                url = format_url(media['URI'])
                sub_info = {
                    'url': url,
                    'ext': determine_ext(url),
                }
                if sub_info['ext'] == 'm3u8':
                    # Per RFC 8216 §3.1, the only possible subtitle format m3u8
                    # files may contain is WebVTT:
                    # <https://tools.ietf.org/html/rfc8216#section-3.1>
                    sub_info['ext'] = 'vtt'
                    sub_info['protocol'] = 'm3u8_native'
                lang = media.get('LANGUAGE') or 'und'
                subtitles.setdefault(lang, []).append(sub_info)
            if media_type not in ('VIDEO', 'AUDIO'):
                return
            media_url = media.get('URI')
            if media_url:
                manifest_url = format_url(media_url)
                formats.extend({
                    'format_id': join_nonempty(m3u8_id, group_id, name, idx),
                    'format_note': name,
                    'format_index': idx,
                    'url': manifest_url,
                    'manifest_url': m3u8_url,
                    'language': media.get('LANGUAGE'),
                    'ext': ext,
                    'protocol': entry_protocol,
                    'preference': preference,
                    'quality': quality,
                    'has_drm': has_drm,
                    'vcodec': 'none' if media_type == 'AUDIO' else None,
                } for idx in _extract_m3u8_playlist_indices(manifest_url))

        def build_stream_name():
            # Despite specification does not mention NAME attribute for
            # EXT-X-STREAM-INF tag it still sometimes may be present (see [1]
            # or vidio test in TestInfoExtractor.test_parse_m3u8_formats)
            # 1. http://www.vidio.com/watch/165683-dj_ambred-booyah-live-2015
            stream_name = last_stream_inf.get('NAME')
            if stream_name:
                return stream_name
            # If there is no NAME in EXT-X-STREAM-INF it will be obtained
            # from corresponding rendition group
            stream_group_id = last_stream_inf.get('VIDEO')
            if not stream_group_id:
                return
            stream_group = groups.get(stream_group_id)
            if not stream_group:
                return stream_group_id
            rendition = stream_group[0]
            return rendition.get('NAME') or stream_group_id

        # parse EXT-X-MEDIA tags before EXT-X-STREAM-INF in order to have the
        # chance to detect video only formats when EXT-X-STREAM-INF tags
        # precede EXT-X-MEDIA tags in HLS manifest such as [3].
        for line in m3u8_doc.splitlines():
            if line.startswith('#EXT-X-MEDIA:'):
                extract_media(line)

        for line in m3u8_doc.splitlines():
            if line.startswith('#EXT-X-STREAM-INF:'):
                last_stream_inf = parse_m3u8_attributes(line)
            elif line.startswith('#') or not line.strip():
                continue
            else:
                tbr = float_or_none(
                    last_stream_inf.get('AVERAGE-BANDWIDTH')
                    or last_stream_inf.get('BANDWIDTH'), scale=1000)
                manifest_url = format_url(line.strip())

                for idx in _extract_m3u8_playlist_indices(manifest_url):
                    format_id = [m3u8_id, None, idx]
                    # Bandwidth of live streams may differ over time thus making
                    # format_id unpredictable. So it's better to keep provided
                    # format_id intact.
                    if not live:
                        stream_name = build_stream_name()
                        format_id[1] = stream_name or '%d' % (tbr or len(formats))
                    f = {
                        'format_id': join_nonempty(*format_id),
                        'format_index': idx,
                        'url': manifest_url,
                        'manifest_url': m3u8_url,
                        'tbr': tbr,
                        'ext': ext,
                        'fps': float_or_none(last_stream_inf.get('FRAME-RATE')),
                        'protocol': entry_protocol,
                        'preference': preference,
                        'quality': quality,
                        'has_drm': has_drm,
                    }

                    # YouTube-specific
                    if yt_audio_content_id := last_stream_inf.get('YT-EXT-AUDIO-CONTENT-ID'):
                        f['language'] = yt_audio_content_id.split('.')[0]

                    resolution = last_stream_inf.get('RESOLUTION')
                    if resolution:
                        mobj = re.search(r'(?P<width>\d+)[xX](?P<height>\d+)', resolution)
                        if mobj:
                            f['width'] = int(mobj.group('width'))
                            f['height'] = int(mobj.group('height'))
                    # Unified Streaming Platform
                    mobj = re.search(
                        r'audio.*?(?:%3D|=)(\d+)(?:-video.*?(?:%3D|=)(\d+))?', f['url'])
                    if mobj:
                        abr, vbr = mobj.groups()
                        abr, vbr = float_or_none(abr, 1000), float_or_none(vbr, 1000)
                        f.update({
                            'vbr': vbr,
                            'abr': abr,
                        })
                    codecs = parse_codecs(last_stream_inf.get('CODECS'))
                    f.update(codecs)
                    audio_group_id = last_stream_inf.get('AUDIO')
                    # As per [1, 4.3.4.1.1] any EXT-X-STREAM-INF tag which
                    # references a rendition group MUST have a CODECS attribute.
                    # However, this is not always respected. E.g. [2]
                    # contains EXT-X-STREAM-INF tag which references AUDIO
                    # rendition group but does not have CODECS and despite
                    # referencing an audio group it represents a complete
                    # (with audio and video) format. So, for such cases we will
                    # ignore references to rendition groups and treat them
                    # as complete formats.
                    if audio_group_id and codecs and f.get('vcodec') != 'none':
                        audio_group = groups.get(audio_group_id)
                        if audio_group and audio_group[0].get('URI'):
                            # TODO: update acodec for audio only formats with
                            # the same GROUP-ID
                            f['acodec'] = 'none'
                    if not f.get('ext'):
                        f['ext'] = 'm4a' if f.get('vcodec') == 'none' else 'mp4'
                    formats.append(f)

                    # for DailyMotion
                    progressive_uri = last_stream_inf.get('PROGRESSIVE-URI')
                    if progressive_uri:
                        http_f = f.copy()
                        del http_f['manifest_url']
                        http_f.update({
                            'format_id': f['format_id'].replace('hls-', 'http-'),
                            'protocol': 'http',
                            'url': progressive_uri,
                        })
                        formats.append(http_f)

                last_stream_inf = {}
        return formats, subtitles

    def _extract_m3u8_vod_duration(
            self, m3u8_vod_url, video_id, note=None, errnote=None, data=None, headers={}, query={}):

        m3u8_vod = self._download_webpage(
            m3u8_vod_url, video_id,
            note='Downloading m3u8 VOD manifest' if note is None else note,
            errnote='Failed to download VOD manifest' if errnote is None else errnote,
            fatal=False, data=data, headers=headers, query=query)

        return self._parse_m3u8_vod_duration(m3u8_vod or '', video_id)

    def _parse_m3u8_vod_duration(self, m3u8_vod, video_id):
        if '#EXT-X-ENDLIST' not in m3u8_vod:
            return None

        return int(sum(
            float(line[len('#EXTINF:'):].split(',')[0])
            for line in m3u8_vod.splitlines() if line.startswith('#EXTINF:'))) or None

    def _extract_mpd_vod_duration(
            self, mpd_url, video_id, note=None, errnote=None, data=None, headers={}, query={}):

        mpd_doc = self._download_xml(
            mpd_url, video_id,
            note='Downloading MPD VOD manifest' if note is None else note,
            errnote='Failed to download VOD manifest' if errnote is None else errnote,
            fatal=False, data=data, headers=headers, query=query)
        if not isinstance(mpd_doc, xml.etree.ElementTree.Element):
            return None
        return int_or_none(parse_duration(mpd_doc.get('mediaPresentationDuration')))

    @staticmethod
    def _xpath_ns(path, namespace=None):
        if not namespace:
            return path
        out = []
        for c in path.split('/'):
            if not c or c == '.':
                out.append(c)
            else:
                out.append(f'{{{namespace}}}{c}')
        return '/'.join(out)

    def _extract_smil_formats_and_subtitles(self, smil_url, video_id, fatal=True, f4m_params=None, transform_source=None):
        if self.get_param('ignore_no_formats_error'):
            fatal = False

        res = self._download_smil(smil_url, video_id, fatal=fatal, transform_source=transform_source)
        if res is False:
            assert not fatal
            return [], {}
        smil, urlh = res

        return self._parse_smil_formats_and_subtitles(smil, urlh.url, video_id, f4m_params=f4m_params,
                                                      namespace=self._parse_smil_namespace(smil))

    def _extract_smil_formats(self, *args, **kwargs):
        fmts, subs = self._extract_smil_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('SMIL')
        return fmts

    def _extract_smil_info(self, smil_url, video_id, fatal=True, f4m_params=None):
        res = self._download_smil(smil_url, video_id, fatal=fatal)
        if res is False:
            return {}

        smil, urlh = res
        smil_url = urlh.url

        return self._parse_smil(smil, smil_url, video_id, f4m_params=f4m_params)

    def _download_smil(self, smil_url, video_id, fatal=True, transform_source=None):
        return self._download_xml_handle(
            smil_url, video_id, 'Downloading SMIL file',
            'Unable to download SMIL file', fatal=fatal, transform_source=transform_source)

    def _parse_smil(self, smil, smil_url, video_id, f4m_params=None):
        namespace = self._parse_smil_namespace(smil)

        formats, subtitles = self._parse_smil_formats_and_subtitles(
            smil, smil_url, video_id, namespace=namespace, f4m_params=f4m_params)

        video_id = os.path.splitext(url_basename(smil_url))[0]
        title = None
        description = None
        upload_date = None
        for meta in smil.findall(self._xpath_ns('./head/meta', namespace)):
            name = meta.attrib.get('name')
            content = meta.attrib.get('content')
            if not name or not content:
                continue
            if not title and name == 'title':
                title = content
            elif not description and name in ('description', 'abstract'):
                description = content
            elif not upload_date and name == 'date':
                upload_date = unified_strdate(content)

        thumbnails = [{
            'id': image.get('type'),
            'url': image.get('src'),
            'width': int_or_none(image.get('width')),
            'height': int_or_none(image.get('height')),
        } for image in smil.findall(self._xpath_ns('.//image', namespace)) if image.get('src')]

        return {
            'id': video_id,
            'title': title or video_id,
            'description': description,
            'upload_date': upload_date,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _parse_smil_namespace(self, smil):
        return self._search_regex(
            r'(?i)^{([^}]+)?}smil$', smil.tag, 'namespace', default=None)

    def _parse_smil_formats(self, *args, **kwargs):
        fmts, subs = self._parse_smil_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('SMIL')
        return fmts

    def _parse_smil_formats_and_subtitles(
            self, smil, smil_url, video_id, namespace=None, f4m_params=None, transform_rtmp_url=None):
        base = smil_url
        for meta in smil.findall(self._xpath_ns('./head/meta', namespace)):
            b = meta.get('base') or meta.get('httpBase')
            if b:
                base = b
                break

        formats, subtitles = [], {}
        rtmp_count = 0
        http_count = 0
        m3u8_count = 0
        imgs_count = 0

        srcs = set()
        media = itertools.chain.from_iterable(
            smil.findall(self._xpath_ns(arg, namespace))
            for arg in ['.//video', './/audio', './/media'])
        for medium in media:
            src = medium.get('src')
            if not src or src in srcs:
                continue
            srcs.add(src)

            bitrate = float_or_none(medium.get('system-bitrate') or medium.get('systemBitrate'), 1000)
            filesize = int_or_none(medium.get('size') or medium.get('fileSize'))
            width = int_or_none(medium.get('width'))
            height = int_or_none(medium.get('height'))
            proto = medium.get('proto')
            ext = medium.get('ext')
            src_ext = determine_ext(src, default_ext=None) or ext or urlhandle_detect_ext(
                self._request_webpage(HEADRequest(src), video_id, note='Requesting extension info', fatal=False))
            streamer = medium.get('streamer') or base

            if proto == 'rtmp' or streamer.startswith('rtmp'):
                rtmp_count += 1
                formats.append({
                    'url': streamer,
                    'play_path': src,
                    'ext': 'flv',
                    'format_id': 'rtmp-%d' % (rtmp_count if bitrate is None else bitrate),
                    'tbr': bitrate,
                    'filesize': filesize,
                    'width': width,
                    'height': height,
                })
                if transform_rtmp_url:
                    streamer, src = transform_rtmp_url(streamer, src)
                    formats[-1].update({
                        'url': streamer,
                        'play_path': src,
                    })
                continue

            src_url = src if src.startswith('http') else urllib.parse.urljoin(f'{base}/', src)
            src_url = src_url.strip()

            if proto == 'm3u8' or src_ext == 'm3u8':
                m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    src_url, video_id, ext or 'mp4', m3u8_id='hls', fatal=False)
                self._merge_subtitles(m3u8_subs, target=subtitles)
                if len(m3u8_formats) == 1:
                    m3u8_count += 1
                    m3u8_formats[0].update({
                        'format_id': 'hls-%d' % (m3u8_count if bitrate is None else bitrate),
                        'tbr': bitrate,
                        'width': width,
                        'height': height,
                    })
                formats.extend(m3u8_formats)
            elif src_ext == 'f4m':
                f4m_url = src_url
                if not f4m_params:
                    f4m_params = {
                        'hdcore': '3.2.0',
                        'plugin': 'flowplayer-3.2.0.1',
                    }
                f4m_url += '&' if '?' in f4m_url else '?'
                f4m_url += urllib.parse.urlencode(f4m_params)
                formats.extend(self._extract_f4m_formats(f4m_url, video_id, f4m_id='hds', fatal=False))
            elif src_ext == 'mpd':
                mpd_formats, mpd_subs = self._extract_mpd_formats_and_subtitles(
                    src_url, video_id, mpd_id='dash', fatal=False)
                formats.extend(mpd_formats)
                self._merge_subtitles(mpd_subs, target=subtitles)
            elif re.search(r'\.ism/[Mm]anifest', src_url):
                ism_formats, ism_subs = self._extract_ism_formats_and_subtitles(
                    src_url, video_id, ism_id='mss', fatal=False)
                formats.extend(ism_formats)
                self._merge_subtitles(ism_subs, target=subtitles)
            elif src_url.startswith('http') and self._is_valid_url(src, video_id):
                http_count += 1
                formats.append({
                    'url': src_url,
                    'ext': ext or src_ext or 'flv',
                    'format_id': 'http-%d' % (bitrate or http_count),
                    'tbr': bitrate,
                    'filesize': filesize,
                    'width': width,
                    'height': height,
                })

        for medium in smil.findall(self._xpath_ns('.//imagestream', namespace)):
            src = medium.get('src')
            if not src or src in srcs:
                continue
            srcs.add(src)

            imgs_count += 1
            formats.append({
                'format_id': f'imagestream-{imgs_count}',
                'url': src,
                'ext': mimetype2ext(medium.get('type')),
                'acodec': 'none',
                'vcodec': 'none',
                'width': int_or_none(medium.get('width')),
                'height': int_or_none(medium.get('height')),
                'format_note': 'SMIL storyboards',
            })

        smil_subs = self._parse_smil_subtitles(smil, namespace=namespace)
        self._merge_subtitles(smil_subs, target=subtitles)

        return formats, subtitles

    def _parse_smil_subtitles(self, smil, namespace=None, subtitles_lang='en'):
        urls = []
        subtitles = {}
        for textstream in smil.findall(self._xpath_ns('.//textstream', namespace)):
            src = textstream.get('src')
            if not src or src in urls:
                continue
            urls.append(src)
            ext = textstream.get('ext') or mimetype2ext(textstream.get('type')) or determine_ext(src)
            lang = textstream.get('systemLanguage') or textstream.get('systemLanguageName') or textstream.get('lang') or subtitles_lang
            subtitles.setdefault(lang, []).append({
                'url': src,
                'ext': ext,
            })
        return subtitles

    def _extract_xspf_playlist(self, xspf_url, playlist_id, fatal=True):
        res = self._download_xml_handle(
            xspf_url, playlist_id, 'Downloading xpsf playlist',
            'Unable to download xspf manifest', fatal=fatal)
        if res is False:
            return []

        xspf, urlh = res
        xspf_url = urlh.url

        return self._parse_xspf(
            xspf, playlist_id, xspf_url=xspf_url,
            xspf_base_url=base_url(xspf_url))

    def _parse_xspf(self, xspf_doc, playlist_id, xspf_url=None, xspf_base_url=None):
        NS_MAP = {
            'xspf': 'http://xspf.org/ns/0/',
            's1': 'http://static.streamone.nl/player/ns/0',
        }

        entries = []
        for track in xspf_doc.findall(xpath_with_ns('./xspf:trackList/xspf:track', NS_MAP)):
            title = xpath_text(
                track, xpath_with_ns('./xspf:title', NS_MAP), 'title', default=playlist_id)
            description = xpath_text(
                track, xpath_with_ns('./xspf:annotation', NS_MAP), 'description')
            thumbnail = xpath_text(
                track, xpath_with_ns('./xspf:image', NS_MAP), 'thumbnail')
            duration = float_or_none(
                xpath_text(track, xpath_with_ns('./xspf:duration', NS_MAP), 'duration'), 1000)

            formats = []
            for location in track.findall(xpath_with_ns('./xspf:location', NS_MAP)):
                format_url = urljoin(xspf_base_url, location.text)
                if not format_url:
                    continue
                formats.append({
                    'url': format_url,
                    'manifest_url': xspf_url,
                    'format_id': location.get(xpath_with_ns('s1:label', NS_MAP)),
                    'width': int_or_none(location.get(xpath_with_ns('s1:width', NS_MAP))),
                    'height': int_or_none(location.get(xpath_with_ns('s1:height', NS_MAP))),
                })

            entries.append({
                'id': playlist_id,
                'title': title,
                'description': description,
                'thumbnail': thumbnail,
                'duration': duration,
                'formats': formats,
            })
        return entries

    def _extract_mpd_formats(self, *args, **kwargs):
        fmts, subs = self._extract_mpd_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('DASH')
        return fmts

    def _extract_mpd_formats_and_subtitles(self, *args, **kwargs):
        periods = self._extract_mpd_periods(*args, **kwargs)
        return self._merge_mpd_periods(periods)

    def _extract_mpd_periods(
            self, mpd_url, video_id, mpd_id=None, note=None, errnote=None,
            fatal=True, data=None, headers={}, query={}):

        if self.get_param('ignore_no_formats_error'):
            fatal = False

        res = self._download_xml_handle(
            mpd_url, video_id,
            note='Downloading MPD manifest' if note is None else note,
            errnote='Failed to download MPD manifest' if errnote is None else errnote,
            fatal=fatal, data=data, headers=headers, query=query)
        if res is False:
            return []
        mpd_doc, urlh = res
        if mpd_doc is None:
            return []

        # We could have been redirected to a new url when we retrieved our mpd file.
        mpd_url = urlh.url
        mpd_base_url = base_url(mpd_url)

        return self._parse_mpd_periods(mpd_doc, mpd_id, mpd_base_url, mpd_url)

    def _parse_mpd_formats(self, *args, **kwargs):
        fmts, subs = self._parse_mpd_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('DASH')
        return fmts

    def _parse_mpd_formats_and_subtitles(self, *args, **kwargs):
        periods = self._parse_mpd_periods(*args, **kwargs)
        return self._merge_mpd_periods(periods)

    def _merge_mpd_periods(self, periods):
        """
        Combine all formats and subtitles from an MPD manifest into a single list,
        by concatenate streams with similar formats.
        """
        formats, subtitles = {}, {}
        for period in periods:
            for f in period['formats']:
                assert 'is_dash_periods' not in f, 'format already processed'
                f['is_dash_periods'] = True
                format_key = tuple(v for k, v in f.items() if k not in (
                    ('format_id', 'fragments', 'manifest_stream_number')))
                if format_key not in formats:
                    formats[format_key] = f
                elif 'fragments' in f:
                    formats[format_key].setdefault('fragments', []).extend(f['fragments'])

            if subtitles and period['subtitles']:
                self.report_warning(bug_reports_message(
                    'Found subtitles in multiple periods in the DASH manifest; '
                    'if part of the subtitles are missing,',
                ), only_once=True)

            for sub_lang, sub_info in period['subtitles'].items():
                subtitles.setdefault(sub_lang, []).extend(sub_info)

        return list(formats.values()), subtitles

    def _parse_mpd_periods(self, mpd_doc, mpd_id=None, mpd_base_url='', mpd_url=None):
        """
        Parse formats from MPD manifest.
        References:
         1. MPEG-DASH Standard, ISO/IEC 23009-1:2014(E),
            http://standards.iso.org/ittf/PubliclyAvailableStandards/c065274_ISO_IEC_23009-1_2014.zip
         2. https://en.wikipedia.org/wiki/Dynamic_Adaptive_Streaming_over_HTTP
        """
        if not self.get_param('dynamic_mpd', True):
            if mpd_doc.get('type') == 'dynamic':
                return [], {}

        namespace = self._search_regex(r'(?i)^{([^}]+)?}MPD$', mpd_doc.tag, 'namespace', default=None)

        def _add_ns(path):
            return self._xpath_ns(path, namespace)

        def is_drm_protected(element):
            return element.find(_add_ns('ContentProtection')) is not None

        def extract_multisegment_info(element, ms_parent_info):
            ms_info = ms_parent_info.copy()

            # As per [1, 5.3.9.2.2] SegmentList and SegmentTemplate share some
            # common attributes and elements.  We will only extract relevant
            # for us.
            def extract_common(source):
                segment_timeline = source.find(_add_ns('SegmentTimeline'))
                if segment_timeline is not None:
                    s_e = segment_timeline.findall(_add_ns('S'))
                    if s_e:
                        ms_info['total_number'] = 0
                        ms_info['s'] = []
                        for s in s_e:
                            r = int(s.get('r', 0))
                            ms_info['total_number'] += 1 + r
                            ms_info['s'].append({
                                't': int(s.get('t', 0)),
                                # @d is mandatory (see [1, 5.3.9.6.2, Table 17, page 60])
                                'd': int(s.attrib['d']),
                                'r': r,
                            })
                start_number = source.get('startNumber')
                if start_number:
                    ms_info['start_number'] = int(start_number)
                timescale = source.get('timescale')
                if timescale:
                    ms_info['timescale'] = int(timescale)
                segment_duration = source.get('duration')
                if segment_duration:
                    ms_info['segment_duration'] = float(segment_duration)

            def extract_Initialization(source):
                initialization = source.find(_add_ns('Initialization'))
                if initialization is not None:
                    ms_info['initialization_url'] = initialization.attrib['sourceURL']

            segment_list = element.find(_add_ns('SegmentList'))
            if segment_list is not None:
                extract_common(segment_list)
                extract_Initialization(segment_list)
                segment_urls_e = segment_list.findall(_add_ns('SegmentURL'))
                if segment_urls_e:
                    ms_info['segment_urls'] = [segment.attrib['media'] for segment in segment_urls_e]
            else:
                segment_template = element.find(_add_ns('SegmentTemplate'))
                if segment_template is not None:
                    extract_common(segment_template)
                    media = segment_template.get('media')
                    if media:
                        ms_info['media'] = media
                    initialization = segment_template.get('initialization')
                    if initialization:
                        ms_info['initialization'] = initialization
                    else:
                        extract_Initialization(segment_template)
            return ms_info

        mpd_duration = parse_duration(mpd_doc.get('mediaPresentationDuration'))
        stream_numbers = collections.defaultdict(int)
        for period_idx, period in enumerate(mpd_doc.findall(_add_ns('Period'))):
            period_entry = {
                'id': period.get('id', f'period-{period_idx}'),
                'formats': [],
                'subtitles': collections.defaultdict(list),
            }
            period_duration = parse_duration(period.get('duration')) or mpd_duration
            period_ms_info = extract_multisegment_info(period, {
                'start_number': 1,
                'timescale': 1,
            })
            for adaptation_set in period.findall(_add_ns('AdaptationSet')):
                adaption_set_ms_info = extract_multisegment_info(adaptation_set, period_ms_info)
                for representation in adaptation_set.findall(_add_ns('Representation')):
                    representation_attrib = adaptation_set.attrib.copy()
                    representation_attrib.update(representation.attrib)
                    # According to [1, 5.3.7.2, Table 9, page 41], @mimeType is mandatory
                    mime_type = representation_attrib['mimeType']
                    content_type = representation_attrib.get('contentType', mime_type.split('/')[0])

                    codec_str = representation_attrib.get('codecs', '')
                    # Some kind of binary subtitle found in some youtube livestreams
                    if mime_type == 'application/x-rawcc':
                        codecs = {'scodec': codec_str}
                    else:
                        codecs = parse_codecs(codec_str)
                    if content_type not in ('video', 'audio', 'text'):
                        if mime_type == 'image/jpeg':
                            content_type = mime_type
                        elif codecs.get('vcodec', 'none') != 'none':
                            content_type = 'video'
                        elif codecs.get('acodec', 'none') != 'none':
                            content_type = 'audio'
                        elif codecs.get('scodec', 'none') != 'none':
                            content_type = 'text'
                        elif mimetype2ext(mime_type) in ('tt', 'dfxp', 'ttml', 'xml', 'json'):
                            content_type = 'text'
                        else:
                            self.report_warning(f'Unknown MIME type {mime_type} in DASH manifest')
                            continue

                    base_url = ''
                    for element in (representation, adaptation_set, period, mpd_doc):
                        base_url_e = element.find(_add_ns('BaseURL'))
                        if try_call(lambda: base_url_e.text) is not None:
                            base_url = base_url_e.text + base_url
                            if re.match(r'https?://', base_url):
                                break
                    if mpd_base_url and base_url.startswith('/'):
                        base_url = urllib.parse.urljoin(mpd_base_url, base_url)
                    elif mpd_base_url and not re.match(r'https?://', base_url):
                        if not mpd_base_url.endswith('/'):
                            mpd_base_url += '/'
                        base_url = mpd_base_url + base_url
                    representation_id = representation_attrib.get('id')
                    lang = representation_attrib.get('lang')
                    url_el = representation.find(_add_ns('BaseURL'))
                    filesize = int_or_none(url_el.attrib.get('{http://youtube.com/yt/2012/10/10}contentLength') if url_el is not None else None)
                    bandwidth = int_or_none(representation_attrib.get('bandwidth'))
                    if representation_id is not None:
                        format_id = representation_id
                    else:
                        format_id = content_type
                    if mpd_id:
                        format_id = mpd_id + '-' + format_id
                    if content_type in ('video', 'audio'):
                        f = {
                            'format_id': format_id,
                            'manifest_url': mpd_url,
                            'ext': mimetype2ext(mime_type),
                            'width': int_or_none(representation_attrib.get('width')),
                            'height': int_or_none(representation_attrib.get('height')),
                            'tbr': float_or_none(bandwidth, 1000),
                            'asr': int_or_none(representation_attrib.get('audioSamplingRate')),
                            'fps': int_or_none(representation_attrib.get('frameRate')),
                            'language': lang if lang not in ('mul', 'und', 'zxx', 'mis') else None,
                            'format_note': f'DASH {content_type}',
                            'filesize': filesize,
                            'container': mimetype2ext(mime_type) + '_dash',
                            **codecs,
                        }
                    elif content_type == 'text':
                        f = {
                            'ext': mimetype2ext(mime_type),
                            'manifest_url': mpd_url,
                            'filesize': filesize,
                        }
                    elif content_type == 'image/jpeg':
                        # See test case in VikiIE
                        # https://www.viki.com/videos/1175236v-choosing-spouse-by-lottery-episode-1
                        f = {
                            'format_id': format_id,
                            'ext': 'mhtml',
                            'manifest_url': mpd_url,
                            'format_note': 'DASH storyboards (jpeg)',
                            'acodec': 'none',
                            'vcodec': 'none',
                        }
                    if is_drm_protected(adaptation_set) or is_drm_protected(representation):
                        f['has_drm'] = True
                    representation_ms_info = extract_multisegment_info(representation, adaption_set_ms_info)

                    def prepare_template(template_name, identifiers):
                        tmpl = representation_ms_info[template_name]
                        if representation_id is not None:
                            tmpl = tmpl.replace('$RepresentationID$', representation_id)
                        # First of, % characters outside $...$ templates
                        # must be escaped by doubling for proper processing
                        # by % operator string formatting used further (see
                        # https://github.com/ytdl-org/youtube-dl/issues/16867).
                        t = ''
                        in_template = False
                        for c in tmpl:
                            t += c
                            if c == '$':
                                in_template = not in_template
                            elif c == '%' and not in_template:
                                t += c
                        # Next, $...$ templates are translated to their
                        # %(...) counterparts to be used with % operator
                        t = re.sub(r'\$({})\$'.format('|'.join(identifiers)), r'%(\1)d', t)
                        t = re.sub(r'\$({})%([^$]+)\$'.format('|'.join(identifiers)), r'%(\1)\2', t)
                        t.replace('$$', '$')
                        return t

                    # @initialization is a regular template like @media one
                    # so it should be handled just the same way (see
                    # https://github.com/ytdl-org/youtube-dl/issues/11605)
                    if 'initialization' in representation_ms_info:
                        initialization_template = prepare_template(
                            'initialization',
                            # As per [1, 5.3.9.4.2, Table 15, page 54] $Number$ and
                            # $Time$ shall not be included for @initialization thus
                            # only $Bandwidth$ remains
                            ('Bandwidth', ))
                        representation_ms_info['initialization_url'] = initialization_template % {
                            'Bandwidth': bandwidth,
                        }

                    def location_key(location):
                        return 'url' if re.match(r'https?://', location) else 'path'

                    if 'segment_urls' not in representation_ms_info and 'media' in representation_ms_info:

                        media_template = prepare_template('media', ('Number', 'Bandwidth', 'Time'))
                        media_location_key = location_key(media_template)

                        # As per [1, 5.3.9.4.4, Table 16, page 55] $Number$ and $Time$
                        # can't be used at the same time
                        if '%(Number' in media_template and 's' not in representation_ms_info:
                            segment_duration = None
                            if 'total_number' not in representation_ms_info and 'segment_duration' in representation_ms_info:
                                segment_duration = float_or_none(representation_ms_info['segment_duration'], representation_ms_info['timescale'])
                                representation_ms_info['total_number'] = int(math.ceil(
                                    float_or_none(period_duration, segment_duration, default=0)))
                            representation_ms_info['fragments'] = [{
                                media_location_key: media_template % {
                                    'Number': segment_number,
                                    'Bandwidth': bandwidth,
                                },
                                'duration': segment_duration,
                            } for segment_number in range(
                                representation_ms_info['start_number'],
                                representation_ms_info['total_number'] + representation_ms_info['start_number'])]
                        else:
                            # $Number*$ or $Time$ in media template with S list available
                            # Example $Number*$: http://www.svtplay.se/klipp/9023742/stopptid-om-bjorn-borg
                            # Example $Time$: https://play.arkena.com/embed/avp/v2/player/media/b41dda37-d8e7-4d3f-b1b5-9a9db578bdfe/1/129411
                            representation_ms_info['fragments'] = []
                            segment_time = 0
                            segment_d = None
                            segment_number = representation_ms_info['start_number']

                            def add_segment_url():
                                segment_url = media_template % {
                                    'Time': segment_time,
                                    'Bandwidth': bandwidth,
                                    'Number': segment_number,
                                }
                                representation_ms_info['fragments'].append({
                                    media_location_key: segment_url,
                                    'duration': float_or_none(segment_d, representation_ms_info['timescale']),
                                })

                            for s in representation_ms_info['s']:
                                segment_time = s.get('t') or segment_time
                                segment_d = s['d']
                                add_segment_url()
                                segment_number += 1
                                for _ in range(s.get('r', 0)):
                                    segment_time += segment_d
                                    add_segment_url()
                                    segment_number += 1
                                segment_time += segment_d
                    elif 'segment_urls' in representation_ms_info and 's' in representation_ms_info:
                        # No media template,
                        # e.g. https://www.youtube.com/watch?v=iXZV5uAYMJI
                        # or any YouTube dashsegments video
                        fragments = []
                        segment_index = 0
                        timescale = representation_ms_info['timescale']
                        for s in representation_ms_info['s']:
                            duration = float_or_none(s['d'], timescale)
                            for _ in range(s.get('r', 0) + 1):
                                segment_uri = representation_ms_info['segment_urls'][segment_index]
                                fragments.append({
                                    location_key(segment_uri): segment_uri,
                                    'duration': duration,
                                })
                                segment_index += 1
                        representation_ms_info['fragments'] = fragments
                    elif 'segment_urls' in representation_ms_info:
                        # Segment URLs with no SegmentTimeline
                        # E.g. https://www.seznam.cz/zpravy/clanek/cesko-zasahne-vitr-o-sile-vichrice-muze-byt-i-zivotu-nebezpecny-39091
                        # https://github.com/ytdl-org/youtube-dl/pull/14844
                        fragments = []
                        segment_duration = float_or_none(
                            representation_ms_info['segment_duration'],
                            representation_ms_info['timescale']) if 'segment_duration' in representation_ms_info else None
                        for segment_url in representation_ms_info['segment_urls']:
                            fragment = {
                                location_key(segment_url): segment_url,
                            }
                            if segment_duration:
                                fragment['duration'] = segment_duration
                            fragments.append(fragment)
                        representation_ms_info['fragments'] = fragments
                    # If there is a fragments key available then we correctly recognized fragmented media.
                    # Otherwise we will assume unfragmented media with direct access. Technically, such
                    # assumption is not necessarily correct since we may simply have no support for
                    # some forms of fragmented media renditions yet, but for now we'll use this fallback.
                    if 'fragments' in representation_ms_info:
                        f.update({
                            # NB: mpd_url may be empty when MPD manifest is parsed from a string
                            'url': mpd_url or base_url,
                            'fragment_base_url': base_url,
                            'fragments': [],
                            'protocol': 'http_dash_segments' if mime_type != 'image/jpeg' else 'mhtml',
                        })
                        if 'initialization_url' in representation_ms_info:
                            initialization_url = representation_ms_info['initialization_url']
                            if not f.get('url'):
                                f['url'] = initialization_url
                            f['fragments'].append({location_key(initialization_url): initialization_url})
                        f['fragments'].extend(representation_ms_info['fragments'])
                        if not period_duration:
                            period_duration = try_get(
                                representation_ms_info,
                                lambda r: sum(frag['duration'] for frag in r['fragments']), float)
                    else:
                        # Assuming direct URL to unfragmented media.
                        f['url'] = base_url
                    if content_type in ('video', 'audio', 'image/jpeg'):
                        f['manifest_stream_number'] = stream_numbers[f['url']]
                        stream_numbers[f['url']] += 1
                        period_entry['formats'].append(f)
                    elif content_type == 'text':
                        period_entry['subtitles'][lang or 'und'].append(f)
            yield period_entry

    def _extract_ism_formats(self, *args, **kwargs):
        fmts, subs = self._extract_ism_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('ISM')
        return fmts

    def _extract_ism_formats_and_subtitles(self, ism_url, video_id, ism_id=None, note=None, errnote=None, fatal=True, data=None, headers={}, query={}):
        if self.get_param('ignore_no_formats_error'):
            fatal = False

        res = self._download_xml_handle(
            ism_url, video_id,
            note='Downloading ISM manifest' if note is None else note,
            errnote='Failed to download ISM manifest' if errnote is None else errnote,
            fatal=fatal, data=data, headers=headers, query=query)
        if res is False:
            return [], {}
        ism_doc, urlh = res
        if ism_doc is None:
            return [], {}

        return self._parse_ism_formats_and_subtitles(ism_doc, urlh.url, ism_id)

    def _parse_ism_formats_and_subtitles(self, ism_doc, ism_url, ism_id=None):
        """
        Parse formats from ISM manifest.
        References:
         1. [MS-SSTR]: Smooth Streaming Protocol,
            https://msdn.microsoft.com/en-us/library/ff469518.aspx
        """
        if ism_doc.get('IsLive') == 'TRUE':
            return [], {}

        duration = int(ism_doc.attrib['Duration'])
        timescale = int_or_none(ism_doc.get('TimeScale')) or 10000000

        formats = []
        subtitles = {}
        for stream in ism_doc.findall('StreamIndex'):
            stream_type = stream.get('Type')
            if stream_type not in ('video', 'audio', 'text'):
                continue
            url_pattern = stream.attrib['Url']
            stream_timescale = int_or_none(stream.get('TimeScale')) or timescale
            stream_name = stream.get('Name')
            # IsmFD expects ISO 639 Set 2 language codes (3-character length)
            # See: https://github.com/yt-dlp/yt-dlp/issues/11356
            stream_language = stream.get('Language') or 'und'
            if len(stream_language) != 3:
                stream_language = ISO639Utils.short2long(stream_language) or 'und'
            for track in stream.findall('QualityLevel'):
                KNOWN_TAGS = {'255': 'AACL', '65534': 'EC-3'}
                fourcc = track.get('FourCC') or KNOWN_TAGS.get(track.get('AudioTag'))
                # TODO: add support for WVC1 and WMAP
                if fourcc not in ('H264', 'AVC1', 'AACL', 'TTML', 'EC-3'):
                    self.report_warning(f'{fourcc} is not a supported codec')
                    continue
                tbr = int(track.attrib['Bitrate']) // 1000
                # [1] does not mention Width and Height attributes. However,
                # they're often present while MaxWidth and MaxHeight are
                # missing, so should be used as fallbacks
                width = int_or_none(track.get('MaxWidth') or track.get('Width'))
                height = int_or_none(track.get('MaxHeight') or track.get('Height'))
                sampling_rate = int_or_none(track.get('SamplingRate'))

                track_url_pattern = re.sub(r'{[Bb]itrate}', track.attrib['Bitrate'], url_pattern)
                track_url_pattern = urllib.parse.urljoin(ism_url, track_url_pattern)

                fragments = []
                fragment_ctx = {
                    'time': 0,
                }
                stream_fragments = stream.findall('c')
                for stream_fragment_index, stream_fragment in enumerate(stream_fragments):
                    fragment_ctx['time'] = int_or_none(stream_fragment.get('t')) or fragment_ctx['time']
                    fragment_repeat = int_or_none(stream_fragment.get('r')) or 1
                    fragment_ctx['duration'] = int_or_none(stream_fragment.get('d'))
                    if not fragment_ctx['duration']:
                        try:
                            next_fragment_time = int(stream_fragment[stream_fragment_index + 1].attrib['t'])
                        except IndexError:
                            next_fragment_time = duration
                        fragment_ctx['duration'] = (next_fragment_time - fragment_ctx['time']) / fragment_repeat
                    for _ in range(fragment_repeat):
                        fragments.append({
                            'url': re.sub(r'{start[ _]time}', str(fragment_ctx['time']), track_url_pattern),
                            'duration': fragment_ctx['duration'] / stream_timescale,
                        })
                        fragment_ctx['time'] += fragment_ctx['duration']

                if stream_type == 'text':
                    subtitles.setdefault(stream_language, []).append({
                        'ext': 'ismt',
                        'protocol': 'ism',
                        'url': ism_url,
                        'manifest_url': ism_url,
                        'fragments': fragments,
                        '_download_params': {
                            'stream_type': stream_type,
                            'duration': duration,
                            'timescale': stream_timescale,
                            'fourcc': fourcc,
                            'language': stream_language,
                            'codec_private_data': track.get('CodecPrivateData'),
                        },
                    })
                elif stream_type in ('video', 'audio'):
                    formats.append({
                        'format_id': join_nonempty(ism_id, stream_name, tbr),
                        'url': ism_url,
                        'manifest_url': ism_url,
                        'ext': 'ismv' if stream_type == 'video' else 'isma',
                        'width': width,
                        'height': height,
                        'tbr': tbr,
                        'asr': sampling_rate,
                        'vcodec': 'none' if stream_type == 'audio' else fourcc,
                        'acodec': 'none' if stream_type == 'video' else fourcc,
                        'protocol': 'ism',
                        'fragments': fragments,
                        'has_drm': ism_doc.find('Protection') is not None,
                        'language': stream_language,
                        'audio_channels': int_or_none(track.get('Channels')),
                        '_download_params': {
                            'stream_type': stream_type,
                            'duration': duration,
                            'timescale': stream_timescale,
                            'width': width or 0,
                            'height': height or 0,
                            'fourcc': fourcc,
                            'language': stream_language,
                            'codec_private_data': track.get('CodecPrivateData'),
                            'sampling_rate': sampling_rate,
                            'channels': int_or_none(track.get('Channels', 2)),
                            'bits_per_sample': int_or_none(track.get('BitsPerSample', 16)),
                            'nal_unit_length_field': int_or_none(track.get('NALUnitLengthField', 4)),
                        },
                    })
        return formats, subtitles

    def _parse_html5_media_entries(self, base_url, webpage, video_id, m3u8_id=None, m3u8_entry_protocol='m3u8_native', mpd_id=None, preference=None, quality=None, _headers=None):
        def absolute_url(item_url):
            return urljoin(base_url, item_url)

        def parse_content_type(content_type):
            if not content_type:
                return {}
            ctr = re.search(r'(?P<mimetype>[^/]+/[^;]+)(?:;\s*codecs="?(?P<codecs>[^"]+))?', content_type)
            if ctr:
                mimetype, codecs = ctr.groups()
                f = parse_codecs(codecs)
                f['ext'] = mimetype2ext(mimetype)
                return f
            return {}

        def _media_formats(src, cur_media_type, type_info=None):
            type_info = type_info or {}
            full_url = absolute_url(src)
            ext = type_info.get('ext') or determine_ext(full_url)
            if ext == 'm3u8':
                is_plain_url = False
                formats = self._extract_m3u8_formats(
                    full_url, video_id, ext='mp4',
                    entry_protocol=m3u8_entry_protocol, m3u8_id=m3u8_id,
                    preference=preference, quality=quality, fatal=False, headers=_headers)
            elif ext == 'mpd':
                is_plain_url = False
                formats = self._extract_mpd_formats(
                    full_url, video_id, mpd_id=mpd_id, fatal=False, headers=_headers)
            else:
                is_plain_url = True
                formats = [{
                    'url': full_url,
                    'vcodec': 'none' if cur_media_type == 'audio' else None,
                    'ext': ext,
                }]
            return is_plain_url, formats

        entries = []
        # amp-video and amp-audio are very similar to their HTML5 counterparts
        # so we will include them right here (see
        # https://www.ampproject.org/docs/reference/components/amp-video)
        # For dl8-* tags see https://delight-vr.com/documentation/dl8-video/
        _MEDIA_TAG_NAME_RE = r'(?:(?:amp|dl8(?:-live)?)-)?(video|audio)'
        media_tags = [(media_tag, media_tag_name, media_type, '')
                      for media_tag, media_tag_name, media_type
                      in re.findall(rf'(?s)(<({_MEDIA_TAG_NAME_RE})[^>]*/>)', webpage)]
        media_tags.extend(re.findall(
            # We only allow video|audio followed by a whitespace or '>'.
            # Allowing more characters may end up in significant slow down (see
            # https://github.com/ytdl-org/youtube-dl/issues/11979,
            # e.g. http://www.porntrex.com/maps/videositemap.xml).
            rf'(?s)(<(?P<tag>{_MEDIA_TAG_NAME_RE})(?:\s+[^>]*)?>)(.*?)</(?P=tag)>', webpage))
        for media_tag, _, media_type, media_content in media_tags:
            media_info = {
                'formats': [],
                'subtitles': {},
            }
            media_attributes = extract_attributes(media_tag)
            src = strip_or_none(dict_get(media_attributes, ('src', 'data-video-src', 'data-src', 'data-source')))
            if src:
                f = parse_content_type(media_attributes.get('type'))
                _, formats = _media_formats(src, media_type, f)
                media_info['formats'].extend(formats)
            media_info['thumbnail'] = absolute_url(media_attributes.get('poster'))
            if media_content:
                for source_tag in re.findall(r'<source[^>]+>', media_content):
                    s_attr = extract_attributes(source_tag)
                    # data-video-src and data-src are non standard but seen
                    # several times in the wild
                    src = strip_or_none(dict_get(s_attr, ('src', 'data-video-src', 'data-src', 'data-source')))
                    if not src:
                        continue
                    f = parse_content_type(s_attr.get('type'))
                    is_plain_url, formats = _media_formats(src, media_type, f)
                    if is_plain_url:
                        # width, height, res, label and title attributes are
                        # all not standard but seen several times in the wild
                        labels = [
                            s_attr.get(lbl)
                            for lbl in ('label', 'title')
                            if str_or_none(s_attr.get(lbl))
                        ]
                        width = int_or_none(s_attr.get('width'))
                        height = (int_or_none(s_attr.get('height'))
                                  or int_or_none(s_attr.get('res')))
                        if not width or not height:
                            for lbl in labels:
                                resolution = parse_resolution(lbl)
                                if not resolution:
                                    continue
                                width = width or resolution.get('width')
                                height = height or resolution.get('height')
                        for lbl in labels:
                            tbr = parse_bitrate(lbl)
                            if tbr:
                                break
                        else:
                            tbr = None
                        f.update({
                            'width': width,
                            'height': height,
                            'tbr': tbr,
                            'format_id': s_attr.get('label') or s_attr.get('title'),
                        })
                        f.update(formats[0])
                        media_info['formats'].append(f)
                    else:
                        media_info['formats'].extend(formats)
                for track_tag in re.findall(r'<track[^>]+>', media_content):
                    track_attributes = extract_attributes(track_tag)
                    kind = track_attributes.get('kind')
                    if not kind or kind in ('subtitles', 'captions'):
                        src = strip_or_none(track_attributes.get('src'))
                        if not src:
                            continue
                        lang = track_attributes.get('srclang') or track_attributes.get('lang') or track_attributes.get('label')
                        media_info['subtitles'].setdefault(lang, []).append({
                            'url': absolute_url(src),
                        })
            for f in media_info['formats']:
                f.setdefault('http_headers', {})['Referer'] = base_url
                if _headers:
                    f['http_headers'].update(_headers)
            if media_info['formats'] or media_info['subtitles']:
                entries.append(media_info)
        return entries

    def _extract_akamai_formats(self, *args, **kwargs):
        fmts, subs = self._extract_akamai_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('akamai')
        return fmts

    def _extract_akamai_formats_and_subtitles(self, manifest_url, video_id, hosts={}):
        signed = 'hdnea=' in manifest_url
        if not signed:
            # https://learn.akamai.com/en-us/webhelp/media-services-on-demand/stream-packaging-user-guide/GUID-BE6C0F73-1E06-483B-B0EA-57984B91B7F9.html
            manifest_url = re.sub(
                r'(?:b=[\d,-]+|(?:__a__|attributes)=off|__b__=\d+)&?',
                '', manifest_url).strip('?')

        formats = []
        subtitles = {}

        hdcore_sign = 'hdcore=3.7.0'
        f4m_url = re.sub(r'(https?://[^/]+)/i/', r'\1/z/', manifest_url).replace('/master.m3u8', '/manifest.f4m')
        hds_host = hosts.get('hds')
        if hds_host:
            f4m_url = re.sub(r'(https?://)[^/]+', r'\1' + hds_host, f4m_url)
        if 'hdcore=' not in f4m_url:
            f4m_url += ('&' if '?' in f4m_url else '?') + hdcore_sign
        f4m_formats = self._extract_f4m_formats(
            f4m_url, video_id, f4m_id='hds', fatal=False)
        for entry in f4m_formats:
            entry.update({'extra_param_to_segment_url': hdcore_sign})
        formats.extend(f4m_formats)

        m3u8_url = re.sub(r'(https?://[^/]+)/z/', r'\1/i/', manifest_url).replace('/manifest.f4m', '/master.m3u8')
        hls_host = hosts.get('hls')
        if hls_host:
            m3u8_url = re.sub(r'(https?://)[^/]+', r'\1' + hls_host, m3u8_url)
        m3u8_formats, m3u8_subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', 'm3u8_native',
            m3u8_id='hls', fatal=False)
        formats.extend(m3u8_formats)
        subtitles = self._merge_subtitles(subtitles, m3u8_subtitles)

        http_host = hosts.get('http')
        if http_host and m3u8_formats and not signed:
            REPL_REGEX = r'https?://[^/]+/i/([^,]+),([^/]+),([^/]+)\.csmil/.+'
            qualities = re.match(REPL_REGEX, m3u8_url).group(2).split(',')
            qualities_length = len(qualities)
            if len(m3u8_formats) in (qualities_length, qualities_length + 1):
                i = 0
                for f in m3u8_formats:
                    if f['vcodec'] != 'none':
                        for protocol in ('http', 'https'):
                            http_f = f.copy()
                            del http_f['manifest_url']
                            http_url = re.sub(
                                REPL_REGEX, protocol + fr'://{http_host}/\g<1>{qualities[i]}\3', f['url'])
                            http_f.update({
                                'format_id': http_f['format_id'].replace('hls-', protocol + '-'),
                                'url': http_url,
                                'protocol': protocol,
                            })
                            formats.append(http_f)
                        i += 1

        return formats, subtitles

    def _extract_wowza_formats(self, url, video_id, m3u8_entry_protocol='m3u8_native', skip_protocols=[]):
        query = urllib.parse.urlparse(url).query
        url = re.sub(r'/(?:manifest|playlist|jwplayer)\.(?:m3u8|f4m|mpd|smil)', '', url)
        mobj = re.search(
            r'(?:(?:http|rtmp|rtsp)(?P<s>s)?:)?(?P<url>//[^?]+)', url)
        url_base = mobj.group('url')
        http_base_url = '{}{}:{}'.format('http', mobj.group('s') or '', url_base)
        formats = []

        def manifest_url(manifest):
            m_url = f'{http_base_url}/{manifest}'
            if query:
                m_url += f'?{query}'
            return m_url

        if 'm3u8' not in skip_protocols:
            formats.extend(self._extract_m3u8_formats(
                manifest_url('playlist.m3u8'), video_id, 'mp4',
                m3u8_entry_protocol, m3u8_id='hls', fatal=False))
        if 'f4m' not in skip_protocols:
            formats.extend(self._extract_f4m_formats(
                manifest_url('manifest.f4m'),
                video_id, f4m_id='hds', fatal=False))
        if 'dash' not in skip_protocols:
            formats.extend(self._extract_mpd_formats(
                manifest_url('manifest.mpd'),
                video_id, mpd_id='dash', fatal=False))
        if re.search(r'(?:/smil:|\.smil)', url_base):
            if 'smil' not in skip_protocols:
                rtmp_formats = self._extract_smil_formats(
                    manifest_url('jwplayer.smil'),
                    video_id, fatal=False)
                for rtmp_format in rtmp_formats:
                    rtsp_format = rtmp_format.copy()
                    rtsp_format['url'] = '{}/{}'.format(rtmp_format['url'], rtmp_format['play_path'])
                    del rtsp_format['play_path']
                    del rtsp_format['ext']
                    rtsp_format.update({
                        'url': rtsp_format['url'].replace('rtmp://', 'rtsp://'),
                        'format_id': rtmp_format['format_id'].replace('rtmp', 'rtsp'),
                        'protocol': 'rtsp',
                    })
                    formats.extend([rtmp_format, rtsp_format])
        else:
            for protocol in ('rtmp', 'rtsp'):
                if protocol not in skip_protocols:
                    formats.append({
                        'url': f'{protocol}:{url_base}',
                        'format_id': protocol,
                        'protocol': protocol,
                    })
        return formats

    def _find_jwplayer_data(self, webpage, video_id=None, transform_source=js_to_json):
        return self._search_json(
            r'''(?<!-)\bjwplayer\s*\(\s*(?P<q>'|")(?!(?P=q)).+(?P=q)\s*\)(?:(?!</script>).)*?\.\s*(?:setup\s*\(|(?P<load>load)\s*\(\s*\[)''',
            webpage, 'JWPlayer data', video_id,
            # must be a {...} or sequence, ending
            contains_pattern=r'\{(?s:.*)}(?(load)(?:\s*,\s*\{(?s:.*)})*)', end_pattern=r'(?(load)\]|\))',
            transform_source=transform_source, default=None)

    def _extract_jwplayer_data(self, webpage, video_id, *args, transform_source=js_to_json, **kwargs):
        jwplayer_data = self._find_jwplayer_data(
            webpage, video_id, transform_source=transform_source)
        return self._parse_jwplayer_data(
            jwplayer_data, video_id, *args, **kwargs)

    def _parse_jwplayer_data(self, jwplayer_data, video_id=None, require_title=True,
                             m3u8_id=None, mpd_id=None, rtmp_params=None, base_url=None):
        entries = []
        if not isinstance(jwplayer_data, dict):
            return entries

        playlist_items = jwplayer_data.get('playlist')
        # JWPlayer backward compatibility: single playlist item/flattened playlists
        # https://github.com/jwplayer/jwplayer/blob/v7.7.0/src/js/playlist/playlist.js#L10
        # https://github.com/jwplayer/jwplayer/blob/v7.4.3/src/js/api/config.js#L81-L96
        if not isinstance(playlist_items, list):
            playlist_items = (playlist_items or jwplayer_data, )

        for video_data in playlist_items:
            if not isinstance(video_data, dict):
                continue
            # JWPlayer backward compatibility: flattened sources
            # https://github.com/jwplayer/jwplayer/blob/v7.4.3/src/js/playlist/item.js#L29-L35
            if 'sources' not in video_data:
                video_data['sources'] = [video_data]

            this_video_id = video_id or video_data['mediaid']

            formats = self._parse_jwplayer_formats(
                video_data['sources'], video_id=this_video_id, m3u8_id=m3u8_id,
                mpd_id=mpd_id, rtmp_params=rtmp_params, base_url=base_url)

            subtitles = {}
            for track in traverse_obj(video_data, (
                    'tracks', lambda _, v: v['kind'].lower() in ('captions', 'subtitles'))):
                track_url = urljoin(base_url, track.get('file'))
                if not track_url:
                    continue
                subtitles.setdefault(track.get('label') or 'en', []).append({
                    'url': self._proto_relative_url(track_url),
                })

            entry = {
                'id': this_video_id,
                'title': unescapeHTML(video_data['title'] if require_title else video_data.get('title')),
                'description': clean_html(video_data.get('description')),
                'thumbnail': urljoin(base_url, self._proto_relative_url(video_data.get('image'))),
                'timestamp': int_or_none(video_data.get('pubdate')),
                'duration': float_or_none(jwplayer_data.get('duration') or video_data.get('duration')),
                'subtitles': subtitles,
                'alt_title': clean_html(video_data.get('subtitle')),  # attributes used e.g. by Tele5 ...
                'genre': clean_html(video_data.get('genre')),
                'channel': clean_html(dict_get(video_data, ('category', 'channel'))),
                'season_number': int_or_none(video_data.get('season')),
                'episode_number': int_or_none(video_data.get('episode')),
                'release_year': int_or_none(video_data.get('releasedate')),
                'age_limit': int_or_none(video_data.get('age_restriction')),
            }
            # https://github.com/jwplayer/jwplayer/blob/master/src/js/utils/validator.js#L32
            if len(formats) == 1 and re.search(r'^(?:http|//).*(?:youtube\.com|youtu\.be)/.+', formats[0]['url']):
                entry.update({
                    '_type': 'url_transparent',
                    'url': formats[0]['url'],
                })
            else:
                entry['formats'] = formats
            entries.append(entry)
        if len(entries) == 1:
            return entries[0]
        else:
            return self.playlist_result(entries)

    def _parse_jwplayer_formats(self, jwplayer_sources_data, video_id=None,
                                m3u8_id=None, mpd_id=None, rtmp_params=None, base_url=None):
        urls = set()
        formats = []
        for source in jwplayer_sources_data:
            if not isinstance(source, dict):
                continue
            source_url = urljoin(
                base_url, self._proto_relative_url(source.get('file')))
            if not source_url or source_url in urls:
                continue
            urls.add(source_url)
            source_type = source.get('type') or ''
            ext = determine_ext(source_url, default_ext=mimetype2ext(source_type))
            if source_type == 'hls' or ext == 'm3u8' or 'format=m3u8-aapl' in source_url:
                formats.extend(self._extract_m3u8_formats(
                    source_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id=m3u8_id, fatal=False))
            elif source_type == 'dash' or ext == 'mpd' or 'format=mpd-time-csf' in source_url:
                formats.extend(self._extract_mpd_formats(
                    source_url, video_id, mpd_id=mpd_id, fatal=False))
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(
                    source_url, video_id, fatal=False))
            # https://github.com/jwplayer/jwplayer/blob/master/src/js/providers/default.js#L67
            elif source_type.startswith('audio') or ext in (
                    'oga', 'aac', 'mp3', 'mpeg', 'vorbis'):
                formats.append({
                    'url': source_url,
                    'vcodec': 'none',
                    'ext': ext,
                })
            else:
                format_id = str_or_none(source.get('label'))
                height = int_or_none(source.get('height'))
                if height is None and format_id:
                    # Often no height is provided but there is a label in
                    # format like "1080p", "720p SD", or 1080.
                    height = parse_resolution(format_id).get('height')
                a_format = {
                    'url': source_url,
                    'width': int_or_none(source.get('width')),
                    'height': height,
                    'tbr': int_or_none(source.get('bitrate'), scale=1000),
                    'filesize': int_or_none(source.get('filesize')),
                    'ext': ext,
                    'format_id': format_id,
                }
                if source_url.startswith('rtmp'):
                    a_format['ext'] = 'flv'
                    # See com/longtailvideo/jwplayer/media/RTMPMediaProvider.as
                    # of jwplayer.flash.swf
                    rtmp_url_parts = re.split(
                        r'((?:mp4|mp3|flv):)', source_url, maxsplit=1)
                    if len(rtmp_url_parts) == 3:
                        rtmp_url, prefix, play_path = rtmp_url_parts
                        a_format.update({
                            'url': rtmp_url,
                            'play_path': prefix + play_path,
                        })
                    if rtmp_params:
                        a_format.update(rtmp_params)
                formats.append(a_format)
        return formats

    def _live_title(self, name):
        self._downloader.deprecation_warning('yt_dlp.InfoExtractor._live_title is deprecated and does not work as expected')
        return name

    def _int(self, v, name, fatal=False, **kwargs):
        res = int_or_none(v, **kwargs)
        if res is None:
            msg = f'Failed to extract {name}: Could not parse value {v!r}'
            if fatal:
                raise ExtractorError(msg)
            else:
                self.report_warning(msg)
        return res

    def _float(self, v, name, fatal=False, **kwargs):
        res = float_or_none(v, **kwargs)
        if res is None:
            msg = f'Failed to extract {name}: Could not parse value {v!r}'
            if fatal:
                raise ExtractorError(msg)
            else:
                self.report_warning(msg)
        return res

    def _set_cookie(self, domain, name, value, expire_time=None, port=None,
                    path='/', secure=False, discard=False, rest={}, **kwargs):
        cookie = http.cookiejar.Cookie(
            0, name, value, port, port is not None, domain, True,
            domain.startswith('.'), path, True, secure, expire_time,
            discard, None, None, rest)
        self.cookiejar.set_cookie(cookie)

    def _get_cookies(self, url):
        """ Return a http.cookies.SimpleCookie with the cookies for the url """
        return LenientSimpleCookie(self._downloader.cookiejar.get_cookie_header(url))

    def _apply_first_set_cookie_header(self, url_handle, cookie):
        """
        Apply first Set-Cookie header instead of the last. Experimental.

        Some sites (e.g. [1-3]) may serve two cookies under the same name
        in Set-Cookie header and expect the first (old) one to be set rather
        than second (new). However, as of RFC6265 the newer one cookie
        should be set into cookie store what actually happens.
        We will workaround this issue by resetting the cookie to
        the first one manually.
        1. https://new.vk.com/
        2. https://github.com/ytdl-org/youtube-dl/issues/9841#issuecomment-227871201
        3. https://learning.oreilly.com/
        """
        for header, cookies in url_handle.headers.items():
            if header.lower() != 'set-cookie':
                continue
            cookies = cookies.encode('iso-8859-1').decode('utf-8')
            cookie_value = re.search(
                rf'{cookie}=(.+?);.*?\b[Dd]omain=(.+?)(?:[,;]|$)', cookies)
            if cookie_value:
                value, domain = cookie_value.groups()
                self._set_cookie(domain, cookie, value)
                break

    @classmethod
    def get_testcases(cls, include_onlymatching=False):
        # Do not look in super classes
        t = vars(cls).get('_TEST')
        if t:
            assert not hasattr(cls, '_TESTS'), f'{cls.ie_key()}IE has _TEST and _TESTS'
            tests = [t]
        else:
            tests = vars(cls).get('_TESTS', [])
        for t in tests:
            if not include_onlymatching and t.get('only_matching', False):
                continue
            t['name'] = cls.ie_key()
            yield t
        if getattr(cls, '__wrapped__', None):
            yield from cls.__wrapped__.get_testcases(include_onlymatching)

    @classmethod
    def get_webpage_testcases(cls):
        tests = vars(cls).get('_WEBPAGE_TESTS', [])
        for t in tests:
            t['name'] = cls.ie_key()
            yield t
        if getattr(cls, '__wrapped__', None):
            yield from cls.__wrapped__.get_webpage_testcases()

    @classproperty(cache=True)
    def age_limit(cls):
        """Get age limit from the testcases"""
        return max(traverse_obj(
            (*cls.get_testcases(include_onlymatching=False), *cls.get_webpage_testcases()),
            (..., (('playlist', 0), None), 'info_dict', 'age_limit')) or [0])

    @classproperty(cache=True)
    def _RETURN_TYPE(cls):
        """What the extractor returns: "video", "playlist", "any", or None (Unknown)"""
        tests = tuple(cls.get_testcases(include_onlymatching=False))
        if not tests:
            return None
        elif not any(k.startswith('playlist') for test in tests for k in test):
            return 'video'
        elif all(any(k.startswith('playlist') for k in test) for test in tests):
            return 'playlist'
        return 'any'

    @classmethod
    def is_single_video(cls, url):
        """Returns whether the URL is of a single video, None if unknown"""
        if cls.suitable(url):
            return {'video': True, 'playlist': False}.get(cls._RETURN_TYPE)

    @classmethod
    def is_suitable(cls, age_limit):
        """Test whether the extractor is generally suitable for the given age limit"""
        return not age_restricted(cls.age_limit, age_limit)

    @classmethod
    def description(cls, *, markdown=True, search_examples=None):
        """Description of the extractor"""
        desc = ''
        if cls._NETRC_MACHINE:
            if markdown:
                desc += f' [*{cls._NETRC_MACHINE}*](## "netrc machine")'
            else:
                desc += f' [{cls._NETRC_MACHINE}]'
        if cls.IE_DESC is False:
            desc += ' [HIDDEN]'
        elif cls.IE_DESC:
            desc += f' {cls.IE_DESC}'
        if cls.SEARCH_KEY:
            desc += f'{";" if cls.IE_DESC else ""} "{cls.SEARCH_KEY}:" prefix'
            if search_examples:
                _COUNTS = ('', '5', '10', 'all')
                desc += f' (e.g. "{cls.SEARCH_KEY}{random.choice(_COUNTS)}:{random.choice(search_examples)}")'
        if not cls.working():
            desc += ' (**Currently broken**)' if markdown else ' (Currently broken)'

        # Escape emojis. Ref: https://github.com/github/markup/issues/1153
        name = (' - **{}**'.format(re.sub(r':(\w+:)', ':\u200B\\g<1>', cls.IE_NAME))) if markdown else cls.IE_NAME
        return f'{name}:{desc}' if desc else name

    def extract_subtitles(self, *args, **kwargs):
        if (self.get_param('writesubtitles', False)
                or self.get_param('listsubtitles')):
            return self._get_subtitles(*args, **kwargs)
        return {}

    def _get_subtitles(self, *args, **kwargs):
        raise NotImplementedError('This method must be implemented by subclasses')

    class CommentsDisabled(Exception):
        """Raise in _get_comments if comments are disabled for the video"""

    def extract_comments(self, *args, **kwargs):
        if not self.get_param('getcomments'):
            return None
        generator = self._get_comments(*args, **kwargs)

        def extractor():
            comments = []
            interrupted = True
            try:
                while True:
                    comments.append(next(generator))
            except StopIteration:
                interrupted = False
            except KeyboardInterrupt:
                self.to_screen('Interrupted by user')
            except self.CommentsDisabled:
                return {'comments': None, 'comment_count': None}
            except Exception as e:
                if self.get_param('ignoreerrors') is not True:
                    raise
                self._downloader.report_error(e)
            comment_count = len(comments)
            self.to_screen(f'Extracted {comment_count} comments')
            return {
                'comments': comments,
                'comment_count': None if interrupted else comment_count,
            }
        return extractor

    def _get_comments(self, *args, **kwargs):
        raise NotImplementedError('This method must be implemented by subclasses')

    @staticmethod
    def _merge_subtitle_items(subtitle_list1, subtitle_list2):
        """ Merge subtitle items for one language. Items with duplicated URLs/data
        will be dropped. """
        list1_data = {(item.get('url'), item.get('data')) for item in subtitle_list1}
        ret = list(subtitle_list1)
        ret.extend(item for item in subtitle_list2 if (item.get('url'), item.get('data')) not in list1_data)
        return ret

    @classmethod
    def _merge_subtitles(cls, *dicts, target=None):
        """ Merge subtitle dictionaries, language by language. """
        if target is None:
            target = {}
        for d in filter(None, dicts):
            for lang, subs in d.items():
                target[lang] = cls._merge_subtitle_items(target.get(lang, []), subs)
        return target

    def extract_automatic_captions(self, *args, **kwargs):
        if (self.get_param('writeautomaticsub', False)
                or self.get_param('listsubtitles')):
            return self._get_automatic_captions(*args, **kwargs)
        return {}

    def _get_automatic_captions(self, *args, **kwargs):
        raise NotImplementedError('This method must be implemented by subclasses')

    @functools.cached_property
    def _cookies_passed(self):
        """Whether cookies have been passed to YoutubeDL"""
        return self.get_param('cookiefile') is not None or self.get_param('cookiesfrombrowser') is not None

    def mark_watched(self, *args, **kwargs):
        if not self.get_param('mark_watched', False):
            return
        if (self.supports_login() and self._get_login_info()[0] is not None) or self._cookies_passed:
            self._mark_watched(*args, **kwargs)

    def _mark_watched(self, *args, **kwargs):
        raise NotImplementedError('This method must be implemented by subclasses')

    def geo_verification_headers(self):
        headers = {}
        geo_verification_proxy = self.get_param('geo_verification_proxy')
        if geo_verification_proxy:
            headers['Ytdl-request-proxy'] = geo_verification_proxy
        return headers

    @staticmethod
    def _generic_id(url):
        return urllib.parse.unquote(os.path.splitext(url.rstrip('/').split('/')[-1])[0])

    def _generic_title(self, url='', webpage='', *, default=None):
        return (self._og_search_title(webpage, default=None)
                or self._html_extract_title(webpage, default=None)
                or urllib.parse.unquote(os.path.splitext(url_basename(url))[0])
                or default)

    def _extract_chapters_helper(self, chapter_list, start_function, title_function, duration, strict=True):
        if not duration:
            return
        chapter_list = [{
            'start_time': start_function(chapter),
            'title': title_function(chapter),
        } for chapter in chapter_list or []]
        if strict:
            warn = self.report_warning
        else:
            warn = self.write_debug
            chapter_list.sort(key=lambda c: c['start_time'] or 0)

        chapters = [{'start_time': 0}]
        for idx, chapter in enumerate(chapter_list):
            if chapter['start_time'] is None:
                warn(f'Incomplete chapter {idx}')
            elif chapters[-1]['start_time'] <= chapter['start_time'] <= duration:
                chapters.append(chapter)
            elif chapter not in chapters:
                issue = (f'{chapter["start_time"]} > {duration}' if chapter['start_time'] > duration
                         else f'{chapter["start_time"]} < {chapters[-1]["start_time"]}')
                warn(f'Invalid start time ({issue}) for chapter "{chapter["title"]}"')
        return chapters[1:]

    def _extract_chapters_from_description(self, description, duration):
        duration_re = r'(?:\d+:)?\d{1,2}:\d{2}'
        sep_re = r'(?m)^\s*(%s)\b\W*\s(%s)\s*$'
        return self._extract_chapters_helper(
            re.findall(sep_re % (duration_re, r'.+?'), description or ''),
            start_function=lambda x: parse_duration(x[0]), title_function=lambda x: x[1],
            duration=duration, strict=False) or self._extract_chapters_helper(
            re.findall(sep_re % (r'.+?', duration_re), description or ''),
            start_function=lambda x: parse_duration(x[1]), title_function=lambda x: x[0],
            duration=duration, strict=False)

    @staticmethod
    def _availability(is_private=None, needs_premium=None, needs_subscription=None, needs_auth=None, is_unlisted=None):
        all_known = all(
            x is not None for x in
            (is_private, needs_premium, needs_subscription, needs_auth, is_unlisted))
        return (
            'private' if is_private
            else 'premium_only' if needs_premium
            else 'subscriber_only' if needs_subscription
            else 'needs_auth' if needs_auth
            else 'unlisted' if is_unlisted
            else 'public' if all_known
            else None)

    def _configuration_arg(self, key, default=NO_DEFAULT, *, ie_key=None, casesense=False):
        '''
        @returns            A list of values for the extractor argument given by "key"
                            or "default" if no such key is present
        @param default      The default value to return when the key is not present (default: [])
        @param casesense    When false, the values are converted to lower case
        '''
        ie_key = ie_key if isinstance(ie_key, str) else (ie_key or self).ie_key()
        val = traverse_obj(self._downloader.params, ('extractor_args', ie_key.lower(), key))
        if val is None:
            return [] if default is NO_DEFAULT else default
        return list(val) if casesense else [x.lower() for x in val]

    def _yes_playlist(self, playlist_id, video_id, smuggled_data=None, *, playlist_label='playlist', video_label='video'):
        if not playlist_id or not video_id:
            return not video_id

        no_playlist = (smuggled_data or {}).get('force_noplaylist')
        if no_playlist is not None:
            return not no_playlist

        video_id = '' if video_id is True else f' {video_id}'
        playlist_id = '' if playlist_id is True else f' {playlist_id}'
        if self.get_param('noplaylist'):
            self.to_screen(f'Downloading just the {video_label}{video_id} because of --no-playlist')
            return False
        self.to_screen(f'Downloading {playlist_label}{playlist_id} - add --no-playlist to download just the {video_label}{video_id}')
        return True

    def _error_or_warning(self, err, _count=None, _retries=0, *, fatal=True):
        RetryManager.report_retry(
            err, _count or int(fatal), _retries,
            info=self.to_screen, warn=self.report_warning, error=None if fatal else self.report_warning,
            sleep_func=self.get_param('retry_sleep_functions', {}).get('extractor'))

    def RetryManager(self, **kwargs):
        return RetryManager(self.get_param('extractor_retries', 3), self._error_or_warning, **kwargs)

    def _extract_generic_embeds(self, url, *args, info_dict={}, note='Extracting generic embeds', **kwargs):
        display_id = traverse_obj(info_dict, 'display_id', 'id')
        self.to_screen(f'{format_field(display_id, None, "%s: ")}{note}')
        return self._downloader.get_info_extractor('Generic')._extract_embeds(
            smuggle_url(url, {'block_ies': [self.ie_key()]}), *args, **kwargs)

    @classmethod
    def extract_from_webpage(cls, ydl, url, webpage):
        ie = (cls if isinstance(cls._extract_from_webpage, types.MethodType)
              else ydl.get_info_extractor(cls.ie_key()))
        for info in ie._extract_from_webpage(url, webpage) or []:
            # url = None since we do not want to set (webpage/original)_url
            ydl.add_default_extra_info(info, ie, None)
            yield info

    @classmethod
    def _extract_from_webpage(cls, url, webpage):
        for embed_url in orderedSet(
                cls._extract_embed_urls(url, webpage) or [], lazy=True):
            yield cls.url_result(embed_url, None if cls._VALID_URL is False else cls)

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        """@returns all the embed urls on the webpage"""
        if '_EMBED_URL_RE' not in cls.__dict__:
            assert isinstance(cls._EMBED_REGEX, (list, tuple))
            for idx, regex in enumerate(cls._EMBED_REGEX):
                assert regex.count('(?P<url>') == 1, \
                    f'{cls.__name__}._EMBED_REGEX[{idx}] must have exactly 1 url group\n\t{regex}'
            cls._EMBED_URL_RE = tuple(map(re.compile, cls._EMBED_REGEX))

        for regex in cls._EMBED_URL_RE:
            for mobj in regex.finditer(webpage):
                embed_url = urllib.parse.urljoin(url, unescapeHTML(mobj.group('url')))
                if cls._VALID_URL is False or cls.suitable(embed_url):
                    yield embed_url

    class StopExtraction(Exception):
        pass

    @classmethod
    def _extract_url(cls, webpage):  # TODO: Remove
        """Only for compatibility with some older extractors"""
        return next(iter(cls._extract_embed_urls(None, webpage) or []), None)

    @classmethod
    def __init_subclass__(cls, *, plugin_name=None, **kwargs):
        if plugin_name:
            mro = inspect.getmro(cls)
            super_class = cls.__wrapped__ = mro[mro.index(cls) + 1]
            cls.PLUGIN_NAME, cls.ie_key = plugin_name, super_class.ie_key
            cls.IE_NAME = f'{super_class.IE_NAME}+{plugin_name}'
            while getattr(super_class, '__wrapped__', None):
                super_class = super_class.__wrapped__
            setattr(sys.modules[super_class.__module__], super_class.__name__, cls)
            _PLUGIN_OVERRIDES[super_class].append(cls)

        return super().__init_subclass__(**kwargs)


class SearchInfoExtractor(InfoExtractor):
    """
    Base class for paged search queries extractors.
    They accept URLs in the format _SEARCH_KEY(|all|[0-9]):{query}
    Instances should define _SEARCH_KEY and optionally _MAX_RESULTS
    """

    _MAX_RESULTS = float('inf')
    _RETURN_TYPE = 'playlist'

    @classproperty
    def _VALID_URL(cls):
        return rf'{cls._SEARCH_KEY}(?P<prefix>|[1-9][0-9]*|all):(?P<query>[\s\S]+)'

    def _real_extract(self, query):
        prefix, query = self._match_valid_url(query).group('prefix', 'query')
        if prefix == '':
            return self._get_n_results(query, 1)
        elif prefix == 'all':
            return self._get_n_results(query, self._MAX_RESULTS)
        else:
            n = int(prefix)
            if n <= 0:
                raise ExtractorError(f'invalid download number {n} for query "{query}"')
            elif n > self._MAX_RESULTS:
                self.report_warning('%s returns max %i results (you requested %i)' % (self._SEARCH_KEY, self._MAX_RESULTS, n))
                n = self._MAX_RESULTS
            return self._get_n_results(query, n)

    def _get_n_results(self, query, n):
        """Get a specified number of results for a query.
        Either this function or _search_results must be overridden by subclasses """
        return self.playlist_result(
            itertools.islice(self._search_results(query), 0, None if n == float('inf') else n),
            query, query)

    def _search_results(self, query):
        """Returns an iterator of search results"""
        raise NotImplementedError('This method must be implemented by subclasses')

    @classproperty
    def SEARCH_KEY(cls):
        return cls._SEARCH_KEY


class UnsupportedURLIE(InfoExtractor):
    _VALID_URL = '.*'
    _ENABLED = False
    IE_DESC = False

    def _real_extract(self, url):
        raise UnsupportedError(url)


_PLUGIN_OVERRIDES = collections.defaultdict(list)

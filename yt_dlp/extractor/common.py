import base64
import collections
import hashlib
import itertools
import json
import math
import netrc
import os
import random
import sys
import time
import xml.etree.ElementTree

from ..compat import functools, re  # isort: split
from ..compat import (
    compat_cookiejar_Cookie,
    compat_cookies_SimpleCookie,
    compat_etree_fromstring,
    compat_expanduser,
    compat_getpass,
    compat_http_client,
    compat_os_name,
    compat_str,
    compat_urllib_error,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlencode,
    compat_urllib_request,
    compat_urlparse,
)
from ..downloader import FileDownloader
from ..downloader.f4m import get_base_url, remove_encrypted_media
from ..utils import (
    JSON_LD_RE,
    NO_DEFAULT,
    ExtractorError,
    GeoRestrictedError,
    GeoUtils,
    RegexNotFoundError,
    UnsupportedError,
    age_restricted,
    base_url,
    bug_reports_message,
    classproperty,
    clean_html,
    determine_ext,
    determine_protocol,
    dict_get,
    encode_data_uri,
    error_to_compat_str,
    extract_attributes,
    filter_dict,
    fix_xml_ampersands,
    float_or_none,
    format_field,
    int_or_none,
    join_nonempty,
    js_to_json,
    mimetype2ext,
    network_exceptions,
    orderedSet,
    parse_bitrate,
    parse_codecs,
    parse_duration,
    parse_iso8601,
    parse_m3u8_attributes,
    parse_resolution,
    sanitize_filename,
    sanitized_Request,
    str_or_none,
    str_to_int,
    strip_or_none,
    traverse_obj,
    try_get,
    unescapeHTML,
    unified_strdate,
    unified_timestamp,
    update_Request,
    update_url_query,
    url_basename,
    url_or_none,
    urljoin,
    variadic,
    xpath_element,
    xpath_text,
    xpath_with_ns,
)


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
                    * resolution Textual description of width and height
                    * dynamic_range The dynamic range of the video. One of:
                                 "SDR" (None), "HDR10", "HDR10+, "HDR12", "HLG, "DV"
                    * tbr        Average bitrate of audio and video in KBit/s
                    * abr        Average audio bitrate in KBit/s
                    * acodec     Name of the audio codec in use
                    * asr        Audio sampling rate in Hertz
                    * vbr        Average video bitrate in KBit/s
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
                    * has_drm    The format has DRM and cannot be downloaded. Boolean
                    * downloader_options  A dictionary of downloader options
                                 (For internal use only)
                                 * http_chunk_size Chunk size for HTTP downloads
                                 * ffmpeg_args     Extra arguments for ffmpeg downloader
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
    display_id      An alternative identifier for the video, not necessarily
                    unique, but available before title. Typically, id is
                    something like "4234987", title "Dancing naked mole rats",
                    and display_id "dancing-naked-mole-rats"
    thumbnails:     A list of dictionaries, with the following entries:
                        * "id" (optional, string) - Thumbnail format ID
                        * "url"
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
    creator:        The creator of the video.
    timestamp:      UNIX timestamp of the moment the video was uploaded
    upload_date:    Video upload date in UTC (YYYYMMDD).
                    If not explicitly set, calculated from timestamp
    release_timestamp: UNIX timestamp of the moment the video was released.
                    If it is not clear whether to use timestamp or this, use the former
    release_date:   The date (YYYYMMDD) when the video was released in UTC.
                    If not explicitly set, calculated from release_timestamp
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
    like_count:     Number of positive ratings of the video
    dislike_count:  Number of negative ratings of the video
    repost_count:   Number of reposts of the video
    average_rating: Average rating give by users, the scale used depends on the webpage
    comment_count:  Number of comments on the video
    comments:       A list of comments, each with one or more of the following
                    properties (all but one of text or html optional):
                        * "author" - human-readable name of the comment author
                        * "author_id" - user ID of the comment author
                        * "author_thumbnail" - The thumbnail of the comment author
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
                        * "author_is_uploader" - Whether the comment is made by
                                                 the video uploader
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
    live_status:    'is_live', 'is_upcoming', 'was_live', 'not_live' or None (=unknown)
                    If absent, automatically set from is_live, was_live
    start_time:     Time in seconds where the reproduction should start, as
                    specified in the URL.
    end_time:       Time in seconds where the reproduction should end, as
                    specified in the URL.
    chapters:       A list of dictionaries, with the following entries:
                        * "start_time" - The start time of the chapter in seconds
                        * "end_time" - The end time of the chapter in seconds
                        * "title" (optional, string)
    playable_in_embed: Whether this video is allowed to play in embedded
                    players on other sites. Can be True (=always allowed),
                    False (=never allowed), None (=unknown), or a string
                    specifying the criteria for embedability (Eg: 'whitelist')
    availability:   Under what condition the video is available. One of
                    'private', 'premium_only', 'subscriber_only', 'needs_auth',
                    'unlisted' or 'public'. Use 'InfoExtractor._availability'
                    to set it
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
    artist:         Artist(s) of the track.
    genre:          Genre(s) of the track.
    album:          Title of the album the track belongs to.
    album_type:     Type of the album (e.g. "Demo", "Full-length", "Split", "Compilation", etc).
    album_artist:   List of all artists appeared on the album (e.g.
                    "Ash Borer / Fell Voices" or "Various Artists", useful for splits
                    and compilations).
    disc_number:    Number of the disc or other physical medium the track belongs to,
                    as an integer.
    release_year:   Year (YYYY) when the album was released.
    composer:       Composer of the piece

    Unless mentioned otherwise, the fields should be Unicode strings.

    Unless mentioned otherwise, None is equivalent to absence of information.


    _type "playlist" indicates multiple videos.
    There must be a key "entries", which is a list, an iterable, or a PagedList
    object, each element of which is a valid dictionary by this specification.

    Additionally, playlists can have "id", "title", and any other relevent
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


    Subclasses of this should define a _VALID_URL regexp and, re-define the
    _real_extract() and (optionally) _real_initialize() methods.
    Probably, they should also be added to the list of extractors.

    Subclasses may also override suitable() if necessary, but ensure the function
    signature is preserved and that this function imports everything it needs
    (except other extractors), so that lazy_extractors works correctly.

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
    _NETRC_MACHINE = None
    IE_DESC = None
    SEARCH_KEY = None

    def _login_hint(self, method=NO_DEFAULT, netrc=None):
        password_hint = f'--username and --password, or --netrc ({netrc or self._NETRC_MACHINE}) to provide account credentials'
        return {
            None: '',
            'any': f'Use --cookies, --cookies-from-browser, {password_hint}',
            'password': f'Use {password_hint}',
            'cookies': (
                'Use --cookies-from-browser or --cookies for the authentication. '
                'See  https://github.com/ytdl-org/youtube-dl#how-do-i-pass-cookies-to-youtube-dl  for how to manually pass cookies'),
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
        # This does not use has/getattr intentionally - we want to know whether
        # we have cached the regexp for *this* class, whereas getattr would also
        # match the superclass
        if '_VALID_URL_RE' not in cls.__dict__:
            if '_VALID_URL' not in cls.__dict__:
                cls._VALID_URL = cls._make_valid_url()
            cls._VALID_URL_RE = re.compile(cls._VALID_URL)
        return cls._VALID_URL_RE.match(url)

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
                    self.write_debug('Extracting URL: %s' % url)
                    ie_result = self._real_extract(url)
                    if ie_result is None:
                        return None
                    if self._x_forwarded_for_ip:
                        ie_result['__x_forwarded_for_ip'] = self._x_forwarded_for_ip
                    subtitles = ie_result.get('subtitles')
                    if (subtitles and 'live_chat' in subtitles
                            and 'no-live-chat' in self.get_param('compat_opts', [])):
                        del subtitles['live_chat']
                    return ie_result
                except GeoRestrictedError as e:
                    if self.__maybe_fake_ip_and_retry(e.countries):
                        continue
                    raise
        except UnsupportedError:
            raise
        except ExtractorError as e:
            kwargs = {
                'video_id': e.video_id or self.get_temp_id(url),
                'ie': self.IE_NAME,
                'tb': e.traceback or sys.exc_info()[2],
                'expected': e.expected,
                'cause': e.cause
            }
            if hasattr(e, 'countries'):
                kwargs['countries'] = e.countries
            raise type(e)(e.orig_msg, **kwargs)
        except compat_http_client.IncompleteRead as e:
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
                    'Video is geo restricted. Retrying extraction with fake IP %s (%s) as X-Forwarded-For.'
                    % (self._x_forwarded_for_ip, country_code.upper()))
                return True
        return False

    def set_downloader(self, downloader):
        """Sets a YoutubeDL instance as the downloader for this IE."""
        self._downloader = downloader

    def _initialize_pre_login(self):
        """ Intialization before login. Redefine in subclasses."""
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
        assert isinstance(err, compat_urllib_error.HTTPError)
        if expected_status is None:
            return False
        elif callable(expected_status):
            return expected_status(err.code) is True
        else:
            return err.code in variadic(expected_status)

    def _request_webpage(self, url_or_request, video_id, note=None, errnote=None, fatal=True, data=None, headers={}, query={}, expected_status=None):
        """
        Return the response handle.

        See _download_webpage docstring for arguments specification.
        """
        if not self._downloader._first_webpage_request:
            sleep_interval = self.get_param('sleep_interval_requests') or 0
            if sleep_interval > 0:
                self.to_screen('Sleeping %s seconds ...' % sleep_interval)
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
            if 'X-Forwarded-For' not in headers:
                headers['X-Forwarded-For'] = self._x_forwarded_for_ip

        if isinstance(url_or_request, compat_urllib_request.Request):
            url_or_request = update_Request(
                url_or_request, data=data, headers=headers, query=query)
        else:
            if query:
                url_or_request = update_url_query(url_or_request, query)
            if data is not None or headers:
                url_or_request = sanitized_Request(url_or_request, data, headers)
        try:
            return self._downloader.urlopen(url_or_request)
        except network_exceptions as err:
            if isinstance(err, compat_urllib_error.HTTPError):
                if self.__can_accept_status_code(err, expected_status):
                    # Retain reference to error to prevent file object from
                    # being closed before it can be read. Works around the
                    # effects of <https://bugs.python.org/issue15002>
                    # introduced in Python 3.4.1.
                    err.fp._error = err
                    return err.fp

            if errnote is False:
                return False
            if errnote is None:
                errnote = 'Unable to download webpage'

            errmsg = f'{errnote}: {error_to_compat_str(err)}'
            if fatal:
                raise ExtractorError(errmsg, cause=err)
            else:
                self.report_warning(errmsg)
                return False

    def _download_webpage_handle(self, url_or_request, video_id, note=None, errnote=None, fatal=True, encoding=None, data=None, headers={}, query={}, expected_status=None):
        """
        Return a tuple (page content as string, URL handle).

        See _download_webpage docstring for arguments specification.
        """
        # Strip hashes from the URL (#1038)
        if isinstance(url_or_request, (compat_str, str)):
            url_or_request = url_or_request.partition('#')[0]

        urlh = self._request_webpage(url_or_request, video_id, note, errnote, fatal, data=data, headers=headers, query=query, expected_status=expected_status)
        if urlh is False:
            assert not fatal
            return False
        content = self._webpage_read_content(urlh, url_or_request, video_id, note, errnote, fatal, encoding=encoding)
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
                msg += ' Visit %s for more details' % blocked_iframe
            raise ExtractorError(msg, expected=True)
        if '<title>The URL you requested has been blocked</title>' in first_block:
            msg = (
                'Access to this webpage has been blocked by Indian censorship. '
                'Use a VPN or proxy server (with --proxy) to route around it.')
            block_msg = self._html_search_regex(
                r'</h1><p>(.*?)</p>',
                content, 'block message', default=None)
            if block_msg:
                msg += ' (Message: "%s")' % block_msg.replace('\n', ' ')
            raise ExtractorError(msg, expected=True)
        if ('<title>TTK :: Доступ к ресурсу ограничен</title>' in content
                and 'blocklist.rkn.gov.ru' in content):
            raise ExtractorError(
                'Access to this webpage has been blocked by decision of the Russian government. '
                'Visit http://blocklist.rkn.gov.ru/ for a block reason.',
                expected=True)

    def _webpage_read_content(self, urlh, url_or_request, video_id, note=None, errnote=None, fatal=True, prefix=None, encoding=None):
        content_type = urlh.headers.get('Content-Type', '')
        webpage_bytes = urlh.read()
        if prefix is not None:
            webpage_bytes = prefix + webpage_bytes
        if not encoding:
            encoding = self._guess_encoding_from_content(content_type, webpage_bytes)
        if self.get_param('dump_intermediate_pages', False):
            self.to_screen('Dumping request to ' + urlh.geturl())
            dump = base64.b64encode(webpage_bytes).decode('ascii')
            self._downloader.to_screen(dump)
        if self.get_param('write_pages', False):
            basen = f'{video_id}_{urlh.geturl()}'
            trim_length = self.get_param('trim_file_name') or 240
            if len(basen) > trim_length:
                h = '___' + hashlib.md5(basen.encode('utf-8')).hexdigest()
                basen = basen[:trim_length - len(h)] + h
            raw_filename = basen + '.dump'
            filename = sanitize_filename(raw_filename, restricted=True)
            self.to_screen('Saving request to ' + filename)
            # Working around MAX_PATH limitation on Windows (see
            # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx)
            if compat_os_name == 'nt':
                absfilepath = os.path.abspath(filename)
                if len(absfilepath) > 259:
                    filename = '\\\\?\\' + absfilepath
            with open(filename, 'wb') as outf:
                outf.write(webpage_bytes)

        try:
            content = webpage_bytes.decode(encoding, 'replace')
        except LookupError:
            content = webpage_bytes.decode('utf-8', 'replace')

        self.__check_blocked(content)

        return content

    def _download_webpage(
            self, url_or_request, video_id, note=None, errnote=None,
            fatal=True, tries=1, timeout=5, encoding=None, data=None,
            headers={}, query={}, expected_status=None):
        """
        Return the data of the page as a string.

        Arguments:
        url_or_request -- plain text URL as a string or
            a compat_urllib_request.Requestobject
        video_id -- Video/playlist/item identifier (string)

        Keyword arguments:
        note -- note printed before downloading (string)
        errnote -- note printed in case of an error (string)
        fatal -- flag denoting whether error should be considered fatal,
            i.e. whether it should cause ExtractionError to be raised,
            otherwise a warning will be reported and extraction continued
        tries -- number of tries
        timeout -- sleep interval between tries
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
        """

        success = False
        try_count = 0
        while success is False:
            try:
                res = self._download_webpage_handle(
                    url_or_request, video_id, note, errnote, fatal,
                    encoding=encoding, data=data, headers=headers, query=query,
                    expected_status=expected_status)
                success = True
            except compat_http_client.IncompleteRead as e:
                try_count += 1
                if try_count >= tries:
                    raise e
                self._sleep(timeout, video_id)
        if res is False:
            return res
        else:
            content, _ = res
            return content

    def _download_xml_handle(
            self, url_or_request, video_id, note='Downloading XML',
            errnote='Unable to download XML', transform_source=None,
            fatal=True, encoding=None, data=None, headers={}, query={},
            expected_status=None):
        """
        Return a tuple (xml as an xml.etree.ElementTree.Element, URL handle).

        See _download_webpage docstring for arguments specification.
        """
        res = self._download_webpage_handle(
            url_or_request, video_id, note, errnote, fatal=fatal,
            encoding=encoding, data=data, headers=headers, query=query,
            expected_status=expected_status)
        if res is False:
            return res
        xml_string, urlh = res
        return self._parse_xml(
            xml_string, video_id, transform_source=transform_source,
            fatal=fatal), urlh

    def _download_xml(
            self, url_or_request, video_id,
            note='Downloading XML', errnote='Unable to download XML',
            transform_source=None, fatal=True, encoding=None,
            data=None, headers={}, query={}, expected_status=None):
        """
        Return the xml as an xml.etree.ElementTree.Element.

        See _download_webpage docstring for arguments specification.
        """
        res = self._download_xml_handle(
            url_or_request, video_id, note=note, errnote=errnote,
            transform_source=transform_source, fatal=fatal, encoding=encoding,
            data=data, headers=headers, query=query,
            expected_status=expected_status)
        return res if res is False else res[0]

    def _parse_xml(self, xml_string, video_id, transform_source=None, fatal=True):
        if transform_source:
            xml_string = transform_source(xml_string)
        try:
            return compat_etree_fromstring(xml_string.encode('utf-8'))
        except xml.etree.ElementTree.ParseError as ve:
            errmsg = '%s: Failed to parse XML ' % video_id
            if fatal:
                raise ExtractorError(errmsg, cause=ve)
            else:
                self.report_warning(errmsg + str(ve))

    def _download_json_handle(
            self, url_or_request, video_id, note='Downloading JSON metadata',
            errnote='Unable to download JSON metadata', transform_source=None,
            fatal=True, encoding=None, data=None, headers={}, query={},
            expected_status=None):
        """
        Return a tuple (JSON object, URL handle).

        See _download_webpage docstring for arguments specification.
        """
        res = self._download_webpage_handle(
            url_or_request, video_id, note, errnote, fatal=fatal,
            encoding=encoding, data=data, headers=headers, query=query,
            expected_status=expected_status)
        if res is False:
            return res
        json_string, urlh = res
        return self._parse_json(
            json_string, video_id, transform_source=transform_source,
            fatal=fatal), urlh

    def _download_json(
            self, url_or_request, video_id, note='Downloading JSON metadata',
            errnote='Unable to download JSON metadata', transform_source=None,
            fatal=True, encoding=None, data=None, headers={}, query={},
            expected_status=None):
        """
        Return the JSON object as a dict.

        See _download_webpage docstring for arguments specification.
        """
        res = self._download_json_handle(
            url_or_request, video_id, note=note, errnote=errnote,
            transform_source=transform_source, fatal=fatal, encoding=encoding,
            data=data, headers=headers, query=query,
            expected_status=expected_status)
        return res if res is False else res[0]

    def _parse_json(self, json_string, video_id, transform_source=None, fatal=True):
        if transform_source:
            json_string = transform_source(json_string)
        try:
            return json.loads(json_string, strict=False)
        except ValueError as ve:
            errmsg = '%s: Failed to parse JSON ' % video_id
            if fatal:
                raise ExtractorError(errmsg, cause=ve)
            else:
                self.report_warning(errmsg + str(ve))

    def _parse_socket_response_as_json(self, data, video_id, transform_source=None, fatal=True):
        return self._parse_json(
            data[data.find('{'):data.rfind('}') + 1],
            video_id, transform_source, fatal)

    def _download_socket_json_handle(
            self, url_or_request, video_id, note='Polling socket',
            errnote='Unable to poll socket', transform_source=None,
            fatal=True, encoding=None, data=None, headers={}, query={},
            expected_status=None):
        """
        Return a tuple (JSON object, URL handle).

        See _download_webpage docstring for arguments specification.
        """
        res = self._download_webpage_handle(
            url_or_request, video_id, note, errnote, fatal=fatal,
            encoding=encoding, data=data, headers=headers, query=query,
            expected_status=expected_status)
        if res is False:
            return res
        webpage, urlh = res
        return self._parse_socket_response_as_json(
            webpage, video_id, transform_source=transform_source,
            fatal=fatal), urlh

    def _download_socket_json(
            self, url_or_request, video_id, note='Polling socket',
            errnote='Unable to poll socket', transform_source=None,
            fatal=True, encoding=None, data=None, headers={}, query={},
            expected_status=None):
        """
        Return the JSON object as a dict.

        See _download_webpage docstring for arguments specification.
        """
        res = self._download_socket_json_handle(
            url_or_request, video_id, note=note, errnote=errnote,
            transform_source=transform_source, fatal=fatal, encoding=encoding,
            data=data, headers=headers, query=query,
            expected_status=expected_status)
        return res if res is False else res[0]

    def report_warning(self, msg, video_id=None, *args, only_once=False, **kwargs):
        idstr = format_field(video_id, template='%s: ')
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

    def report_drm(self, video_id, partial=False):
        self.raise_no_formats('This video is DRM protected', expected=True, video_id=video_id)

    def report_extraction(self, id_or_name):
        """Report information extraction."""
        self.to_screen('%s: Extracting information' % id_or_name)

    def report_download_webpage(self, video_id):
        """Report webpage download."""
        self.to_screen('%s: Downloading webpage' % video_id)

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
        msg += format_field(self._login_hint(method), template='. %s')
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

    def playlist_from_matches(self, matches, playlist_id=None, playlist_title=None, getter=None, ie=None, video_kwargs=None, **kwargs):
        urls = (self.url_result(self._proto_relative_url(m), ie, **(video_kwargs or {}))
                for m in orderedSet(map(getter, matches) if getter else matches))
        return self.playlist_result(urls, playlist_id, playlist_title, **kwargs)

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
            raise RegexNotFoundError('Unable to extract %s' % _name)
        else:
            self.report_warning('unable to extract %s' % _name + bug_reports_message())
            return None

    def _html_search_regex(self, pattern, string, name, default=NO_DEFAULT, fatal=True, flags=0, group=None):
        """
        Like _search_regex, but strips HTML tags and unescapes entities.
        """
        res = self._search_regex(pattern, string, name, default, fatal, flags, group)
        if res:
            return clean_html(res).strip()
        else:
            return res

    def _get_netrc_login_info(self, netrc_machine=None):
        username = None
        password = None
        netrc_machine = netrc_machine or self._NETRC_MACHINE

        if self.get_param('usenetrc', False):
            try:
                netrc_file = compat_expanduser(self.get_param('netrc_location') or '~')
                if os.path.isdir(netrc_file):
                    netrc_file = os.path.join(netrc_file, '.netrc')
                info = netrc.netrc(file=netrc_file).authenticators(netrc_machine)
                if info is not None:
                    username = info[0]
                    password = info[2]
                else:
                    raise netrc.NetrcParseError(
                        'No authenticators for %s' % netrc_machine)
            except (OSError, netrc.NetrcParseError) as err:
                self.report_warning(
                    'parsing .netrc: %s' % error_to_compat_str(err))

        return username, password

    def _get_login_info(self, username_option='username', password_option='password', netrc_machine=None):
        """
        Get the login info as (username, password)
        First look for the manually specified credentials using username_option
        and password_option as keys in params dictionary. If no such credentials
        available look in the netrc file using the netrc_machine or _NETRC_MACHINE
        value.
        If there's no info available, return (None, None)
        """

        # Attempt to use provided username and password or .netrc data
        username = self.get_param(username_option)
        if username is not None:
            password = self.get_param(password_option)
        else:
            username, password = self._get_netrc_login_info(netrc_machine)

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

        return compat_getpass('Type %s and press [Return]: ' % note)

    # Helper functions for extracting OpenGraph info
    @staticmethod
    def _og_regexes(prop):
        content_re = r'content=(?:"([^"]+?)"|\'([^\']+?)\'|\s*([^\s"\'=<>`]+?))'
        property_re = (r'(?:name|property)=(?:\'og%(sep)s%(prop)s\'|"og%(sep)s%(prop)s"|\s*og%(sep)s%(prop)s\b)'
                       % {'prop': re.escape(prop), 'sep': '(?:&#x3A;|[:-])'})
        template = r'<meta[^>]+?%s[^>]+?%s'
        return [
            template % (property_re, content_re),
            template % (content_re, property_re),
        ]

    @staticmethod
    def _meta_regex(prop):
        return r'''(?isx)<meta
                    (?=[^>]+(?:itemprop|name|property|id|http-equiv)=(["\']?)%s\1)
                    [^>]+?content=(["\'])(?P<content>.*?)\2''' % re.escape(prop)

    def _og_search_property(self, prop, html, name=None, **kargs):
        prop = variadic(prop)
        if name is None:
            name = 'OpenGraph %s' % prop[0]
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

    def _rta_search(self, html):
        # See http://www.rtalabel.org/index.php?content=howtofaq#single
        if re.search(r'(?ix)<meta\s+name="rating"\s+'
                     r'     content="RTA-5042-1996-1400-1577-RTA"',
                     html):
            return 18
        return 0

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

    def _search_json_ld(self, html, video_id, expected_type=None, **kwargs):
        json_ld_list = list(re.finditer(JSON_LD_RE, html))
        default = kwargs.get('default', NO_DEFAULT)
        # JSON-LD may be malformed and thus `fatal` should be respected.
        # At the same time `default` may be passed that assumes `fatal=False`
        # for _search_regex. Let's simulate the same behavior here as well.
        fatal = kwargs.get('fatal', True) if default is NO_DEFAULT else False
        json_ld = []
        for mobj in json_ld_list:
            json_ld_item = self._parse_json(
                mobj.group('json_ld'), video_id, fatal=fatal)
            if not json_ld_item:
                continue
            if isinstance(json_ld_item, dict):
                json_ld.append(json_ld_item)
            elif isinstance(json_ld_item, (list, tuple)):
                json_ld.extend(json_ld_item)
        if json_ld:
            json_ld = self._json_ld(json_ld, video_id, fatal=fatal, expected_type=expected_type)
        if json_ld:
            return json_ld
        if default is not NO_DEFAULT:
            return default
        elif fatal:
            raise RegexNotFoundError('Unable to extract JSON-LD')
        else:
            self.report_warning('unable to extract JSON-LD %s' % bug_reports_message())
            return {}

    def _json_ld(self, json_ld, video_id, fatal=True, expected_type=None):
        if isinstance(json_ld, compat_str):
            json_ld = self._parse_json(json_ld, video_id, fatal=fatal)
        if not json_ld:
            return {}
        info = {}
        if not isinstance(json_ld, (list, tuple, dict)):
            return info
        if isinstance(json_ld, dict):
            json_ld = [json_ld]

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
                if not isinstance(is_e, dict):
                    continue
                if is_e.get('@type') != 'InteractionCounter':
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
                count_key = '%s_count' % count_kind
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
                    [{'end_time': 0}] + chapters, chapters, chapters[1:])):
                current_c['end_time'] = current_c['end_time'] or next_c['start_time']
                current_c['start_time'] = current_c['start_time'] or last_c['end_time']
                if None in current_c.values():
                    self.report_warning(f'Chapter {idx} contains broken data. Not extracting chapters')
                    return
            if chapters:
                chapters[-1]['end_time'] = chapters[-1]['end_time'] or info['duration']
                info['chapters'] = chapters

        def extract_video_object(e):
            assert e['@type'] == 'VideoObject'
            author = e.get('author')
            info.update({
                'url': url_or_none(e.get('contentUrl')),
                'title': unescapeHTML(e.get('name')),
                'description': unescapeHTML(e.get('description')),
                'thumbnails': [{'url': url}
                               for url in variadic(traverse_obj(e, 'thumbnailUrl', 'thumbnailURL'))
                               if url_or_none(url)],
                'duration': parse_duration(e.get('duration')),
                'timestamp': unified_timestamp(e.get('uploadDate')),
                # author can be an instance of 'Organization' or 'Person' types.
                # both types can have 'name' property(inherited from 'Thing' type). [1]
                # however some websites are using 'Text' type instead.
                # 1. https://schema.org/VideoObject
                'uploader': author.get('name') if isinstance(author, dict) else author if isinstance(author, compat_str) else None,
                'filesize': float_or_none(e.get('contentSize')),
                'tbr': int_or_none(e.get('bitrate')),
                'width': int_or_none(e.get('width')),
                'height': int_or_none(e.get('height')),
                'view_count': int_or_none(e.get('interactionCount')),
            })
            extract_interaction_statistic(e)
            extract_chapter_information(e)

        def traverse_json_ld(json_ld, at_top_level=True):
            for e in json_ld:
                if at_top_level and '@context' not in e:
                    continue
                if at_top_level and set(e.keys()) == {'@context', '@graph'}:
                    traverse_json_ld(variadic(e['@graph'], allowed_types=(dict,)), at_top_level=False)
                    break
                item_type = e.get('@type')
                if expected_type is not None and expected_type != item_type:
                    continue
                rating = traverse_obj(e, ('aggregateRating', 'ratingValue'), expected_type=float_or_none)
                if rating is not None:
                    info['average_rating'] = rating
                if item_type in ('TVEpisode', 'Episode'):
                    episode_name = unescapeHTML(e.get('name'))
                    info.update({
                        'episode': episode_name,
                        'episode_number': int_or_none(e.get('episodeNumber')),
                        'description': unescapeHTML(e.get('description')),
                    })
                    if not info.get('title') and episode_name:
                        info['title'] = episode_name
                    part_of_season = e.get('partOfSeason')
                    if isinstance(part_of_season, dict) and part_of_season.get('@type') in ('TVSeason', 'Season', 'CreativeWorkSeason'):
                        info.update({
                            'season': unescapeHTML(part_of_season.get('name')),
                            'season_number': int_or_none(part_of_season.get('seasonNumber')),
                        })
                    part_of_series = e.get('partOfSeries') or e.get('partOfTVSeries')
                    if isinstance(part_of_series, dict) and part_of_series.get('@type') in ('TVSeries', 'Series', 'CreativeWorkSeries'):
                        info['series'] = unescapeHTML(part_of_series.get('name'))
                elif item_type == 'Movie':
                    info.update({
                        'title': unescapeHTML(e.get('name')),
                        'description': unescapeHTML(e.get('description')),
                        'duration': parse_duration(e.get('duration')),
                        'timestamp': unified_timestamp(e.get('dateCreated')),
                    })
                elif item_type in ('Article', 'NewsArticle'):
                    info.update({
                        'timestamp': parse_iso8601(e.get('datePublished')),
                        'title': unescapeHTML(e.get('headline')),
                        'description': unescapeHTML(e.get('articleBody') or e.get('description')),
                    })
                    if traverse_obj(e, ('video', 0, '@type')) == 'VideoObject':
                        extract_video_object(e['video'][0])
                elif item_type == 'VideoObject':
                    extract_video_object(e)
                    if expected_type is None:
                        continue
                    else:
                        break
                video = e.get('video')
                if isinstance(video, dict) and video.get('@type') == 'VideoObject':
                    extract_video_object(video)
                if expected_type is None:
                    continue
                else:
                    break
        traverse_json_ld(json_ld)

        return filter_dict(info)

    def _search_nextjs_data(self, webpage, video_id, *, transform_source=None, fatal=True, **kw):
        return self._parse_json(
            self._search_regex(
                r'(?s)<script[^>]+id=[\'"]__NEXT_DATA__[\'"][^>]*>([^<]+)</script>',
                webpage, 'next.js data', fatal=fatal, **kw),
            video_id, transform_source=transform_source, fatal=fatal)

    def _search_nuxt_data(self, webpage, video_id, context_name='__NUXT__'):
        ''' Parses Nuxt.js metadata. This works as long as the function __NUXT__ invokes is a pure function. '''
        # not all website do this, but it can be changed
        # https://stackoverflow.com/questions/67463109/how-to-change-or-hide-nuxt-and-nuxt-keyword-in-page-source
        rectx = re.escape(context_name)
        js, arg_keys, arg_vals = self._search_regex(
            (r'<script>window\.%s=\(function\((?P<arg_keys>.*?)\)\{return\s(?P<js>\{.*?\})\}\((?P<arg_vals>.+?)\)\);?</script>' % rectx,
             r'%s\(.*?\(function\((?P<arg_keys>.*?)\)\{return\s(?P<js>\{.*?\})\}\((?P<arg_vals>.*?)\)' % rectx),
            webpage, context_name, group=['js', 'arg_keys', 'arg_vals'])

        args = dict(zip(arg_keys.split(','), arg_vals.split(',')))

        for key, val in args.items():
            if val in ('undefined', 'void 0'):
                args[key] = 'null'

        return self._parse_json(js_to_json(js, args), video_id)['data'][0]

    @staticmethod
    def _hidden_inputs(html):
        html = re.sub(r'<!--(?:(?!<!--).)*-->', '', html)
        hidden_inputs = {}
        for input in re.findall(r'(?i)(<input[^>]+>)', html):
            attrs = extract_attributes(input)
            if not input:
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
            r'(?is)<form[^>]+?id=(["\'])%s\1[^>]*>(?P<form>.+?)</form>' % form_id,
            html, '%s form' % form_id, group='form')
        return self._hidden_inputs(form)

    class FormatSort:
        regex = r' *((?P<reverse>\+)?(?P<field>[a-zA-Z0-9_]+)((?P<separator>[~:])(?P<limit>.*?))?)? *$'

        default = ('hidden', 'aud_or_vid', 'hasvid', 'ie_pref', 'lang', 'quality',
                   'res', 'fps', 'hdr:12', 'codec:vp9.2', 'size', 'br', 'asr',
                   'proto', 'ext', 'hasaud', 'source', 'id')  # These must not be aliases
        ytdl_default = ('hasaud', 'lang', 'quality', 'tbr', 'filesize', 'vbr',
                        'height', 'width', 'proto', 'vext', 'abr', 'aext',
                        'fps', 'fs_approx', 'source', 'id')

        settings = {
            'vcodec': {'type': 'ordered', 'regex': True,
                       'order': ['av0?1', 'vp0?9.2', 'vp0?9', '[hx]265|he?vc?', '[hx]264|avc', 'vp0?8', 'mp4v|h263', 'theora', '', None, 'none']},
            'acodec': {'type': 'ordered', 'regex': True,
                       'order': ['[af]lac', 'wav|aiff', 'opus', 'vorbis|ogg', 'aac', 'mp?4a?', 'mp3', 'e-?a?c-?3', 'ac-?3', 'dts', '', None, 'none']},
            'hdr': {'type': 'ordered', 'regex': True, 'field': 'dynamic_range',
                    'order': ['dv', '(hdr)?12', r'(hdr)?10\+', '(hdr)?10', 'hlg', '', 'sdr', None]},
            'proto': {'type': 'ordered', 'regex': True, 'field': 'protocol',
                      'order': ['(ht|f)tps', '(ht|f)tp$', 'm3u8.*', '.*dash', 'websocket_frag', 'rtmpe?', '', 'mms|rtsp', 'ws|websocket', 'f4']},
            'vext': {'type': 'ordered', 'field': 'video_ext',
                     'order': ('mp4', 'webm', 'flv', '', 'none'),
                     'order_free': ('webm', 'mp4', 'flv', '', 'none')},
            'aext': {'type': 'ordered', 'field': 'audio_ext',
                     'order': ('m4a', 'aac', 'mp3', 'ogg', 'opus', 'webm', '', 'none'),
                     'order_free': ('opus', 'ogg', 'webm', 'm4a', 'mp3', 'aac', '', 'none')},
            'hidden': {'visible': False, 'forced': True, 'type': 'extractor', 'max': -1000},
            'aud_or_vid': {'visible': False, 'forced': True, 'type': 'multiple',
                           'field': ('vcodec', 'acodec'),
                           'function': lambda it: int(any(v != 'none' for v in it))},
            'ie_pref': {'priority': True, 'type': 'extractor'},
            'hasvid': {'priority': True, 'field': 'vcodec', 'type': 'boolean', 'not_in_list': ('none',)},
            'hasaud': {'field': 'acodec', 'type': 'boolean', 'not_in_list': ('none',)},
            'lang': {'convert': 'float', 'field': 'language_preference', 'default': -1},
            'quality': {'convert': 'float', 'default': -1},
            'filesize': {'convert': 'bytes'},
            'fs_approx': {'convert': 'bytes', 'field': 'filesize_approx'},
            'id': {'convert': 'string', 'field': 'format_id'},
            'height': {'convert': 'float_none'},
            'width': {'convert': 'float_none'},
            'fps': {'convert': 'float_none'},
            'tbr': {'convert': 'float_none'},
            'vbr': {'convert': 'float_none'},
            'abr': {'convert': 'float_none'},
            'asr': {'convert': 'float_none'},
            'source': {'convert': 'float', 'field': 'source_preference', 'default': -1},

            'codec': {'type': 'combined', 'field': ('vcodec', 'acodec')},
            'br': {'type': 'combined', 'field': ('tbr', 'vbr', 'abr'), 'same_limit': True},
            'size': {'type': 'combined', 'same_limit': True, 'field': ('filesize', 'fs_approx')},
            'ext': {'type': 'combined', 'field': ('vext', 'aext')},
            'res': {'type': 'multiple', 'field': ('height', 'width'),
                    'function': lambda it: (lambda l: min(l) if l else 0)(tuple(filter(None, it)))},

            # For compatibility with youtube-dl
            'format_id': {'type': 'alias', 'field': 'id'},
            'preference': {'type': 'alias', 'field': 'ie_pref'},
            'language_preference': {'type': 'alias', 'field': 'lang'},
            'source_preference': {'type': 'alias', 'field': 'source'},
            'protocol': {'type': 'alias', 'field': 'proto'},
            'filesize_approx': {'type': 'alias', 'field': 'fs_approx'},

            # Deprecated
            'dimension': {'type': 'alias', 'field': 'res', 'deprecated': True},
            'resolution': {'type': 'alias', 'field': 'res', 'deprecated': True},
            'extension': {'type': 'alias', 'field': 'ext', 'deprecated': True},
            'bitrate': {'type': 'alias', 'field': 'br', 'deprecated': True},
            'total_bitrate': {'type': 'alias', 'field': 'tbr', 'deprecated': True},
            'video_bitrate': {'type': 'alias', 'field': 'vbr', 'deprecated': True},
            'audio_bitrate': {'type': 'alias', 'field': 'abr', 'deprecated': True},
            'framerate': {'type': 'alias', 'field': 'fps', 'deprecated': True},
            'filesize_estimate': {'type': 'alias', 'field': 'size', 'deprecated': True},
            'samplerate': {'type': 'alias', 'field': 'asr', 'deprecated': True},
            'video_ext': {'type': 'alias', 'field': 'vext', 'deprecated': True},
            'audio_ext': {'type': 'alias', 'field': 'aext', 'deprecated': True},
            'video_codec': {'type': 'alias', 'field': 'vcodec', 'deprecated': True},
            'audio_codec': {'type': 'alias', 'field': 'acodec', 'deprecated': True},
            'video': {'type': 'alias', 'field': 'hasvid', 'deprecated': True},
            'has_video': {'type': 'alias', 'field': 'hasvid', 'deprecated': True},
            'audio': {'type': 'alias', 'field': 'hasaud', 'deprecated': True},
            'has_audio': {'type': 'alias', 'field': 'hasaud', 'deprecated': True},
            'extractor': {'type': 'alias', 'field': 'ie_pref', 'deprecated': True},
            'extractor_preference': {'type': 'alias', 'field': 'ie_pref', 'deprecated': True},
        }

        def __init__(self, ie, field_preference):
            self._order = []
            self.ydl = ie._downloader
            self.evaluate_params(self.ydl.params, field_preference)
            if ie.get_param('verbose'):
                self.print_verbose_info(self.ydl.write_debug)

        def _get_field_setting(self, field, key):
            if field not in self.settings:
                if key in ('forced', 'priority'):
                    return False
                self.ydl.deprecation_warning(
                    f'Using arbitrary fields ({field}) for format sorting is deprecated '
                    'and may be removed in a future version')
                self.settings[field] = {}
            propObj = self.settings[field]
            if key not in propObj:
                type = propObj.get('type')
                if key == 'field':
                    default = 'preference' if type == 'extractor' else (field,) if type in ('combined', 'multiple') else field
                elif key == 'convert':
                    default = 'order' if type == 'ordered' else 'float_string' if field else 'ignore'
                else:
                    default = {'type': 'field', 'visible': True, 'order': [], 'not_in_list': (None,)}.get(key, None)
                propObj[key] = default
            return propObj[key]

        def _resolve_field_value(self, field, value, convertNone=False):
            if value is None:
                if not convertNone:
                    return None
            else:
                value = value.lower()
            conversion = self._get_field_setting(field, 'convert')
            if conversion == 'ignore':
                return None
            if conversion == 'string':
                return value
            elif conversion == 'float_none':
                return float_or_none(value)
            elif conversion == 'bytes':
                return FileDownloader.parse_bytes(value)
            elif conversion == 'order':
                order_list = (self._use_free_order and self._get_field_setting(field, 'order_free')) or self._get_field_setting(field, 'order')
                use_regex = self._get_field_setting(field, 'regex')
                list_length = len(order_list)
                empty_pos = order_list.index('') if '' in order_list else list_length + 1
                if use_regex and value is not None:
                    for i, regex in enumerate(order_list):
                        if regex and re.match(regex, value):
                            return list_length - i
                    return list_length - empty_pos  # not in list
                else:  # not regex or  value = None
                    return list_length - (order_list.index(value) if value in order_list else empty_pos)
            else:
                if value.isnumeric():
                    return float(value)
                else:
                    self.settings[field]['convert'] = 'string'
                    return value

        def evaluate_params(self, params, sort_extractor):
            self._use_free_order = params.get('prefer_free_formats', False)
            self._sort_user = params.get('format_sort', [])
            self._sort_extractor = sort_extractor

            def add_item(field, reverse, closest, limit_text):
                field = field.lower()
                if field in self._order:
                    return
                self._order.append(field)
                limit = self._resolve_field_value(field, limit_text)
                data = {
                    'reverse': reverse,
                    'closest': False if limit is None else closest,
                    'limit_text': limit_text,
                    'limit': limit}
                if field in self.settings:
                    self.settings[field].update(data)
                else:
                    self.settings[field] = data

            sort_list = (
                tuple(field for field in self.default if self._get_field_setting(field, 'forced'))
                + (tuple() if params.get('format_sort_force', False)
                   else tuple(field for field in self.default if self._get_field_setting(field, 'priority')))
                + tuple(self._sort_user) + tuple(sort_extractor) + self.default)

            for item in sort_list:
                match = re.match(self.regex, item)
                if match is None:
                    raise ExtractorError('Invalid format sort string "%s" given by extractor' % item)
                field = match.group('field')
                if field is None:
                    continue
                if self._get_field_setting(field, 'type') == 'alias':
                    alias, field = field, self._get_field_setting(field, 'field')
                    if self._get_field_setting(alias, 'deprecated'):
                        self.ydl.deprecation_warning(
                            f'Format sorting alias {alias} is deprecated '
                            f'and may be removed in a future version. Please use {field} instead')
                reverse = match.group('reverse') is not None
                closest = match.group('separator') == '~'
                limit_text = match.group('limit')

                has_limit = limit_text is not None
                has_multiple_fields = self._get_field_setting(field, 'type') == 'combined'
                has_multiple_limits = has_limit and has_multiple_fields and not self._get_field_setting(field, 'same_limit')

                fields = self._get_field_setting(field, 'field') if has_multiple_fields else (field,)
                limits = limit_text.split(':') if has_multiple_limits else (limit_text,) if has_limit else tuple()
                limit_count = len(limits)
                for (i, f) in enumerate(fields):
                    add_item(f, reverse, closest,
                             limits[i] if i < limit_count
                             else limits[0] if has_limit and not has_multiple_limits
                             else None)

        def print_verbose_info(self, write_debug):
            if self._sort_user:
                write_debug('Sort order given by user: %s' % ', '.join(self._sort_user))
            if self._sort_extractor:
                write_debug('Sort order given by extractor: %s' % ', '.join(self._sort_extractor))
            write_debug('Formats sorted by: %s' % ', '.join(['%s%s%s' % (
                '+' if self._get_field_setting(field, 'reverse') else '', field,
                '%s%s(%s)' % ('~' if self._get_field_setting(field, 'closest') else ':',
                              self._get_field_setting(field, 'limit_text'),
                              self._get_field_setting(field, 'limit'))
                if self._get_field_setting(field, 'limit_text') is not None else '')
                for field in self._order if self._get_field_setting(field, 'visible')]))

        def _calculate_field_preference_from_value(self, format, field, type, value):
            reverse = self._get_field_setting(field, 'reverse')
            closest = self._get_field_setting(field, 'closest')
            limit = self._get_field_setting(field, 'limit')

            if type == 'extractor':
                maximum = self._get_field_setting(field, 'max')
                if value is None or (maximum is not None and value >= maximum):
                    value = -1
            elif type == 'boolean':
                in_list = self._get_field_setting(field, 'in_list')
                not_in_list = self._get_field_setting(field, 'not_in_list')
                value = 0 if ((in_list is None or value in in_list) and (not_in_list is None or value not in not_in_list)) else -1
            elif type == 'ordered':
                value = self._resolve_field_value(field, value, True)

            # try to convert to number
            val_num = float_or_none(value, default=self._get_field_setting(field, 'default'))
            is_num = self._get_field_setting(field, 'convert') != 'string' and val_num is not None
            if is_num:
                value = val_num

            return ((-10, 0) if value is None
                    else (1, value, 0) if not is_num  # if a field has mixed strings and numbers, strings are sorted higher
                    else (0, -abs(value - limit), value - limit if reverse else limit - value) if closest
                    else (0, value, 0) if not reverse and (limit is None or value <= limit)
                    else (0, -value, 0) if limit is None or (reverse and value == limit) or value > limit
                    else (-1, value, 0))

        def _calculate_field_preference(self, format, field):
            type = self._get_field_setting(field, 'type')  # extractor, boolean, ordered, field, multiple
            get_value = lambda f: format.get(self._get_field_setting(f, 'field'))
            if type == 'multiple':
                type = 'field'  # Only 'field' is allowed in multiple for now
                actual_fields = self._get_field_setting(field, 'field')

                value = self._get_field_setting(field, 'function')(get_value(f) for f in actual_fields)
            else:
                value = get_value(field)
            return self._calculate_field_preference_from_value(format, field, type, value)

        def calculate_preference(self, format):
            # Determine missing protocol
            if not format.get('protocol'):
                format['protocol'] = determine_protocol(format)

            # Determine missing ext
            if not format.get('ext') and 'url' in format:
                format['ext'] = determine_ext(format['url'])
            if format.get('vcodec') == 'none':
                format['audio_ext'] = format['ext'] if format.get('acodec') != 'none' else 'none'
                format['video_ext'] = 'none'
            else:
                format['video_ext'] = format['ext']
                format['audio_ext'] = 'none'
            # if format.get('preference') is None and format.get('ext') in ('f4f', 'f4m'):  # Not supported?
            #    format['preference'] = -1000

            # Determine missing bitrates
            if format.get('tbr') is None:
                if format.get('vbr') is not None and format.get('abr') is not None:
                    format['tbr'] = format.get('vbr', 0) + format.get('abr', 0)
            else:
                if format.get('vcodec') != 'none' and format.get('vbr') is None:
                    format['vbr'] = format.get('tbr') - format.get('abr', 0)
                if format.get('acodec') != 'none' and format.get('abr') is None:
                    format['abr'] = format.get('tbr') - format.get('vbr', 0)

            return tuple(self._calculate_field_preference(format, field) for field in self._order)

    def _sort_formats(self, formats, field_preference=[]):
        if not formats:
            return
        formats.sort(key=self.FormatSort(self, field_preference).calculate_preference)

    def _check_formats(self, formats, video_id):
        if formats:
            formats[:] = filter(
                lambda f: self._is_valid_url(
                    f['url'], video_id,
                    item='%s video format' % f.get('format_id') if f.get('format_id') else 'video'),
                formats)

    @staticmethod
    def _remove_duplicate_formats(formats):
        format_urls = set()
        unique_formats = []
        for f in formats:
            if f['url'] not in format_urls:
                format_urls.add(f['url'])
                unique_formats.append(f)
        formats[:] = unique_formats

    def _is_valid_url(self, url, video_id, item='video', headers={}):
        url = self._proto_relative_url(url, scheme='http:')
        # For now assume non HTTP(S) URLs always valid
        if not (url.startswith('http://') or url.startswith('https://')):
            return True
        try:
            self._request_webpage(url, video_id, 'Checking %s URL' % item, headers=headers)
            return True
        except ExtractorError as e:
            self.to_screen(
                '%s: %s URL is invalid, skipping: %s'
                % (video_id, item, error_to_compat_str(e.cause)))
            return False

    def http_scheme(self):
        """ Either "http:" or "https:", depending on the user's preferences """
        return (
            'http:'
            if self.get_param('prefer_insecure', False)
            else 'https:')

    def _proto_relative_url(self, url, scheme=None):
        if url is None:
            return url
        if url.startswith('//'):
            if scheme is None:
                scheme = self.http_scheme()
            return scheme + url
        else:
            return url

    def _sleep(self, timeout, video_id, msg_template=None):
        if msg_template is None:
            msg_template = '%(video_id)s: Waiting for %(timeout)s seconds'
        msg = msg_template % {'video_id': video_id, 'timeout': timeout}
        self.to_screen(msg)
        time.sleep(timeout)

    def _extract_f4m_formats(self, manifest_url, video_id, preference=None, quality=None, f4m_id=None,
                             transform_source=lambda s: fix_xml_ampersands(s).strip(),
                             fatal=True, m3u8_id=None, data=None, headers={}, query={}):
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
        manifest_url = urlh.geturl()

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
            playerVerificationChallenge = akamai_pv.text.split(';')[0]
            if playerVerificationChallenge.strip() != '':
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
                    media_url if media_url.startswith('http://') or media_url.startswith('https://')
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
            'if any subtitle tracks are missing,'
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

        res = self._download_webpage_handle(
            m3u8_url, video_id,
            note='Downloading m3u8 information' if note is None else note,
            errnote='Failed to download m3u8 information' if errnote is None else errnote,
            fatal=fatal, data=data, headers=headers, query=query)

        if res is False:
            return [], {}

        m3u8_doc, urlh = res
        m3u8_url = urlh.geturl()

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

        has_drm = re.search('|'.join([
            r'#EXT-X-FAXS-CM:',  # Adobe Flash Access
            r'#EXT-X-(?:SESSION-)?KEY:.*?URI="skd://',  # Apple FairPlay
        ]), m3u8_doc)

        def format_url(url):
            return url if re.match(r'^https?://', url) else compat_urlparse.urljoin(m3u8_url, url)

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
                'url': m3u8_url or encode_data_uri(m3u8_doc.encode('utf-8'), 'application/x-mpegurl'),
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
                    }
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
                    # However, this is not always respected, for example, [2]
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
        if '#EXT-X-PLAYLIST-TYPE:VOD' not in m3u8_vod:
            return None

        return int(sum(
            float(line[len('#EXTINF:'):].split(',')[0])
            for line in m3u8_vod.splitlines() if line.startswith('#EXTINF:'))) or None

    @staticmethod
    def _xpath_ns(path, namespace=None):
        if not namespace:
            return path
        out = []
        for c in path.split('/'):
            if not c or c == '.':
                out.append(c)
            else:
                out.append('{%s}%s' % (namespace, c))
        return '/'.join(out)

    def _extract_smil_formats_and_subtitles(self, smil_url, video_id, fatal=True, f4m_params=None, transform_source=None):
        res = self._download_smil(smil_url, video_id, fatal=fatal, transform_source=transform_source)
        if res is False:
            assert not fatal
            return [], {}

        smil, urlh = res
        smil_url = urlh.geturl()

        namespace = self._parse_smil_namespace(smil)

        fmts = self._parse_smil_formats(
            smil, smil_url, video_id, namespace=namespace, f4m_params=f4m_params)
        subs = self._parse_smil_subtitles(
            smil, namespace=namespace)

        return fmts, subs

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
        smil_url = urlh.geturl()

        return self._parse_smil(smil, smil_url, video_id, f4m_params=f4m_params)

    def _download_smil(self, smil_url, video_id, fatal=True, transform_source=None):
        return self._download_xml_handle(
            smil_url, video_id, 'Downloading SMIL file',
            'Unable to download SMIL file', fatal=fatal, transform_source=transform_source)

    def _parse_smil(self, smil, smil_url, video_id, f4m_params=None):
        namespace = self._parse_smil_namespace(smil)

        formats = self._parse_smil_formats(
            smil, smil_url, video_id, namespace=namespace, f4m_params=f4m_params)
        subtitles = self._parse_smil_subtitles(smil, namespace=namespace)

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

    def _parse_smil_formats(self, smil, smil_url, video_id, namespace=None, f4m_params=None, transform_rtmp_url=None):
        base = smil_url
        for meta in smil.findall(self._xpath_ns('./head/meta', namespace)):
            b = meta.get('base') or meta.get('httpBase')
            if b:
                base = b
                break

        formats = []
        rtmp_count = 0
        http_count = 0
        m3u8_count = 0
        imgs_count = 0

        srcs = set()
        media = smil.findall(self._xpath_ns('.//video', namespace)) + smil.findall(self._xpath_ns('.//audio', namespace))
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
            src_ext = determine_ext(src)
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

            src_url = src if src.startswith('http') else compat_urlparse.urljoin(base, src)
            src_url = src_url.strip()

            if proto == 'm3u8' or src_ext == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    src_url, video_id, ext or 'mp4', m3u8_id='hls', fatal=False)
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
                f4m_url += compat_urllib_parse_urlencode(f4m_params)
                formats.extend(self._extract_f4m_formats(f4m_url, video_id, f4m_id='hds', fatal=False))
            elif src_ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    src_url, video_id, mpd_id='dash', fatal=False))
            elif re.search(r'\.ism/[Mm]anifest', src_url):
                formats.extend(self._extract_ism_formats(
                    src_url, video_id, ism_id='mss', fatal=False))
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
                'format_id': 'imagestream-%d' % (imgs_count),
                'url': src,
                'ext': mimetype2ext(medium.get('type')),
                'acodec': 'none',
                'vcodec': 'none',
                'width': int_or_none(medium.get('width')),
                'height': int_or_none(medium.get('height')),
                'format_note': 'SMIL storyboards',
            })

        return formats

    def _parse_smil_subtitles(self, smil, namespace=None, subtitles_lang='en'):
        urls = []
        subtitles = {}
        for num, textstream in enumerate(smil.findall(self._xpath_ns('.//textstream', namespace))):
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
        xspf_url = urlh.geturl()

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
            self._sort_formats(formats)

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

    def _extract_mpd_formats_and_subtitles(
            self, mpd_url, video_id, mpd_id=None, note=None, errnote=None,
            fatal=True, data=None, headers={}, query={}):
        res = self._download_xml_handle(
            mpd_url, video_id,
            note='Downloading MPD manifest' if note is None else note,
            errnote='Failed to download MPD manifest' if errnote is None else errnote,
            fatal=fatal, data=data, headers=headers, query=query)
        if res is False:
            return [], {}
        mpd_doc, urlh = res
        if mpd_doc is None:
            return [], {}

        # We could have been redirected to a new url when we retrieved our mpd file.
        mpd_url = urlh.geturl()
        mpd_base_url = base_url(mpd_url)

        return self._parse_mpd_formats_and_subtitles(
            mpd_doc, mpd_id, mpd_base_url, mpd_url)

    def _parse_mpd_formats(self, *args, **kwargs):
        fmts, subs = self._parse_mpd_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('DASH')
        return fmts

    def _parse_mpd_formats_and_subtitles(
            self, mpd_doc, mpd_id=None, mpd_base_url='', mpd_url=None):
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
        formats, subtitles = [], {}
        stream_numbers = collections.defaultdict(int)
        for period in mpd_doc.findall(_add_ns('Period')):
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
                            self.report_warning('Unknown MIME type %s in DASH manifest' % mime_type)
                            continue

                    base_url = ''
                    for element in (representation, adaptation_set, period, mpd_doc):
                        base_url_e = element.find(_add_ns('BaseURL'))
                        if base_url_e is not None:
                            base_url = base_url_e.text + base_url
                            if re.match(r'^https?://', base_url):
                                break
                    if mpd_base_url and base_url.startswith('/'):
                        base_url = compat_urlparse.urljoin(mpd_base_url, base_url)
                    elif mpd_base_url and not re.match(r'^https?://', base_url):
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
                            'format_note': 'DASH %s' % content_type,
                            'filesize': filesize,
                            'container': mimetype2ext(mime_type) + '_dash',
                            **codecs
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
                        if representation_id is not None:
                            t = t.replace('$RepresentationID$', representation_id)
                        t = re.sub(r'\$(%s)\$' % '|'.join(identifiers), r'%(\1)d', t)
                        t = re.sub(r'\$(%s)%%([^$]+)\$' % '|'.join(identifiers), r'%(\1)\2', t)
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
                        return 'url' if re.match(r'^https?://', location) else 'path'

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

                            for num, s in enumerate(representation_ms_info['s']):
                                segment_time = s.get('t') or segment_time
                                segment_d = s['d']
                                add_segment_url()
                                segment_number += 1
                                for r in range(s.get('r', 0)):
                                    segment_time += segment_d
                                    add_segment_url()
                                    segment_number += 1
                                segment_time += segment_d
                    elif 'segment_urls' in representation_ms_info and 's' in representation_ms_info:
                        # No media template
                        # Example: https://www.youtube.com/watch?v=iXZV5uAYMJI
                        # or any YouTube dashsegments video
                        fragments = []
                        segment_index = 0
                        timescale = representation_ms_info['timescale']
                        for s in representation_ms_info['s']:
                            duration = float_or_none(s['d'], timescale)
                            for r in range(s.get('r', 0) + 1):
                                segment_uri = representation_ms_info['segment_urls'][segment_index]
                                fragments.append({
                                    location_key(segment_uri): segment_uri,
                                    'duration': duration,
                                })
                                segment_index += 1
                        representation_ms_info['fragments'] = fragments
                    elif 'segment_urls' in representation_ms_info:
                        # Segment URLs with no SegmentTimeline
                        # Example: https://www.seznam.cz/zpravy/clanek/cesko-zasahne-vitr-o-sile-vichrice-muze-byt-i-zivotu-nebezpecny-39091
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
                        formats.append(f)
                    elif content_type == 'text':
                        subtitles.setdefault(lang or 'und', []).append(f)

        return formats, subtitles

    def _extract_ism_formats(self, *args, **kwargs):
        fmts, subs = self._extract_ism_formats_and_subtitles(*args, **kwargs)
        if subs:
            self._report_ignoring_subs('ISM')
        return fmts

    def _extract_ism_formats_and_subtitles(self, ism_url, video_id, ism_id=None, note=None, errnote=None, fatal=True, data=None, headers={}, query={}):
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

        return self._parse_ism_formats_and_subtitles(ism_doc, urlh.geturl(), ism_id)

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
            stream_language = stream.get('Language', 'und')
            for track in stream.findall('QualityLevel'):
                fourcc = track.get('FourCC') or ('AACL' if track.get('AudioTag') == '255' else None)
                # TODO: add support for WVC1 and WMAP
                if fourcc not in ('H264', 'AVC1', 'AACL', 'TTML'):
                    self.report_warning('%s is not a supported codec' % fourcc)
                    continue
                tbr = int(track.attrib['Bitrate']) // 1000
                # [1] does not mention Width and Height attributes. However,
                # they're often present while MaxWidth and MaxHeight are
                # missing, so should be used as fallbacks
                width = int_or_none(track.get('MaxWidth') or track.get('Width'))
                height = int_or_none(track.get('MaxHeight') or track.get('Height'))
                sampling_rate = int_or_none(track.get('SamplingRate'))

                track_url_pattern = re.sub(r'{[Bb]itrate}', track.attrib['Bitrate'], url_pattern)
                track_url_pattern = compat_urlparse.urljoin(ism_url, track_url_pattern)

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
                            'url': re.sub(r'{start[ _]time}', compat_str(fragment_ctx['time']), track_url_pattern),
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
                        }
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

    def _parse_html5_media_entries(self, base_url, webpage, video_id, m3u8_id=None, m3u8_entry_protocol='m3u8_native', mpd_id=None, preference=None, quality=None):
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

        def _media_formats(src, cur_media_type, type_info={}):
            full_url = absolute_url(src)
            ext = type_info.get('ext') or determine_ext(full_url)
            if ext == 'm3u8':
                is_plain_url = False
                formats = self._extract_m3u8_formats(
                    full_url, video_id, ext='mp4',
                    entry_protocol=m3u8_entry_protocol, m3u8_id=m3u8_id,
                    preference=preference, quality=quality, fatal=False)
            elif ext == 'mpd':
                is_plain_url = False
                formats = self._extract_mpd_formats(
                    full_url, video_id, mpd_id=mpd_id, fatal=False)
            else:
                is_plain_url = True
                formats = [{
                    'url': full_url,
                    'vcodec': 'none' if cur_media_type == 'audio' else None,
                }]
            return is_plain_url, formats

        entries = []
        # amp-video and amp-audio are very similar to their HTML5 counterparts
        # so we wll include them right here (see
        # https://www.ampproject.org/docs/reference/components/amp-video)
        # For dl8-* tags see https://delight-vr.com/documentation/dl8-video/
        _MEDIA_TAG_NAME_RE = r'(?:(?:amp|dl8(?:-live)?)-)?(video|audio)'
        media_tags = [(media_tag, media_tag_name, media_type, '')
                      for media_tag, media_tag_name, media_type
                      in re.findall(r'(?s)(<(%s)[^>]*/>)' % _MEDIA_TAG_NAME_RE, webpage)]
        media_tags.extend(re.findall(
            # We only allow video|audio followed by a whitespace or '>'.
            # Allowing more characters may end up in significant slow down (see
            # https://github.com/ytdl-org/youtube-dl/issues/11979, example URL:
            # http://www.porntrex.com/maps/videositemap.xml).
            r'(?s)(<(?P<tag>%s)(?:\s+[^>]*)?>)(.*?)</(?P=tag)>' % _MEDIA_TAG_NAME_RE, webpage))
        for media_tag, _, media_type, media_content in media_tags:
            media_info = {
                'formats': [],
                'subtitles': {},
            }
            media_attributes = extract_attributes(media_tag)
            src = strip_or_none(media_attributes.get('src'))
            if src:
                _, formats = _media_formats(src, media_type)
                media_info['formats'].extend(formats)
            media_info['thumbnail'] = absolute_url(media_attributes.get('poster'))
            if media_content:
                for source_tag in re.findall(r'<source[^>]+>', media_content):
                    s_attr = extract_attributes(source_tag)
                    # data-video-src and data-src are non standard but seen
                    # several times in the wild
                    src = strip_or_none(dict_get(s_attr, ('src', 'data-video-src', 'data-src')))
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
        query = compat_urlparse.urlparse(url).query
        url = re.sub(r'/(?:manifest|playlist|jwplayer)\.(?:m3u8|f4m|mpd|smil)', '', url)
        mobj = re.search(
            r'(?:(?:http|rtmp|rtsp)(?P<s>s)?:)?(?P<url>//[^?]+)', url)
        url_base = mobj.group('url')
        http_base_url = '%s%s:%s' % ('http', mobj.group('s') or '', url_base)
        formats = []

        def manifest_url(manifest):
            m_url = f'{http_base_url}/{manifest}'
            if query:
                m_url += '?%s' % query
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
                    rtsp_format['url'] = '%s/%s' % (rtmp_format['url'], rtmp_format['play_path'])
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
        mobj = re.search(
            r'(?s)jwplayer\((?P<quote>[\'"])[^\'" ]+(?P=quote)\)(?!</script>).*?\.setup\s*\((?P<options>[^)]+)\)',
            webpage)
        if mobj:
            try:
                jwplayer_data = self._parse_json(mobj.group('options'),
                                                 video_id=video_id,
                                                 transform_source=transform_source)
            except ExtractorError:
                pass
            else:
                if isinstance(jwplayer_data, dict):
                    return jwplayer_data

    def _extract_jwplayer_data(self, webpage, video_id, *args, **kwargs):
        jwplayer_data = self._find_jwplayer_data(
            webpage, video_id, transform_source=js_to_json)
        return self._parse_jwplayer_data(
            jwplayer_data, video_id, *args, **kwargs)

    def _parse_jwplayer_data(self, jwplayer_data, video_id=None, require_title=True,
                             m3u8_id=None, mpd_id=None, rtmp_params=None, base_url=None):
        # JWPlayer backward compatibility: flattened playlists
        # https://github.com/jwplayer/jwplayer/blob/v7.4.3/src/js/api/config.js#L81-L96
        if 'playlist' not in jwplayer_data:
            jwplayer_data = {'playlist': [jwplayer_data]}

        entries = []

        # JWPlayer backward compatibility: single playlist item
        # https://github.com/jwplayer/jwplayer/blob/v7.7.0/src/js/playlist/playlist.js#L10
        if not isinstance(jwplayer_data['playlist'], list):
            jwplayer_data['playlist'] = [jwplayer_data['playlist']]

        for video_data in jwplayer_data['playlist']:
            # JWPlayer backward compatibility: flattened sources
            # https://github.com/jwplayer/jwplayer/blob/v7.4.3/src/js/playlist/item.js#L29-L35
            if 'sources' not in video_data:
                video_data['sources'] = [video_data]

            this_video_id = video_id or video_data['mediaid']

            formats = self._parse_jwplayer_formats(
                video_data['sources'], video_id=this_video_id, m3u8_id=m3u8_id,
                mpd_id=mpd_id, rtmp_params=rtmp_params, base_url=base_url)

            subtitles = {}
            tracks = video_data.get('tracks')
            if tracks and isinstance(tracks, list):
                for track in tracks:
                    if not isinstance(track, dict):
                        continue
                    track_kind = track.get('kind')
                    if not track_kind or not isinstance(track_kind, compat_str):
                        continue
                    if track_kind.lower() not in ('captions', 'subtitles'):
                        continue
                    track_url = urljoin(base_url, track.get('file'))
                    if not track_url:
                        continue
                    subtitles.setdefault(track.get('label') or 'en', []).append({
                        'url': self._proto_relative_url(track_url)
                    })

            entry = {
                'id': this_video_id,
                'title': unescapeHTML(video_data['title'] if require_title else video_data.get('title')),
                'description': clean_html(video_data.get('description')),
                'thumbnail': urljoin(base_url, self._proto_relative_url(video_data.get('image'))),
                'timestamp': int_or_none(video_data.get('pubdate')),
                'duration': float_or_none(jwplayer_data.get('duration') or video_data.get('duration')),
                'subtitles': subtitles,
            }
            # https://github.com/jwplayer/jwplayer/blob/master/src/js/utils/validator.js#L32
            if len(formats) == 1 and re.search(r'^(?:http|//).*(?:youtube\.com|youtu\.be)/.+', formats[0]['url']):
                entry.update({
                    '_type': 'url_transparent',
                    'url': formats[0]['url'],
                })
            else:
                self._sort_formats(formats)
                entry['formats'] = formats
            entries.append(entry)
        if len(entries) == 1:
            return entries[0]
        else:
            return self.playlist_result(entries)

    def _parse_jwplayer_formats(self, jwplayer_sources_data, video_id=None,
                                m3u8_id=None, mpd_id=None, rtmp_params=None, base_url=None):
        urls = []
        formats = []
        for source in jwplayer_sources_data:
            if not isinstance(source, dict):
                continue
            source_url = urljoin(
                base_url, self._proto_relative_url(source.get('file')))
            if not source_url or source_url in urls:
                continue
            urls.append(source_url)
            source_type = source.get('type') or ''
            ext = mimetype2ext(source_type) or determine_ext(source_url)
            if source_type == 'hls' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    source_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id=m3u8_id, fatal=False))
            elif source_type == 'dash' or ext == 'mpd':
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
                height = int_or_none(source.get('height'))
                if height is None:
                    # Often no height is provided but there is a label in
                    # format like "1080p", "720p SD", or 1080.
                    height = int_or_none(self._search_regex(
                        r'^(\d{3,4})[pP]?(?:\b|$)', compat_str(source.get('label') or ''),
                        'height', default=None))
                a_format = {
                    'url': source_url,
                    'width': int_or_none(source.get('width')),
                    'height': height,
                    'tbr': int_or_none(source.get('bitrate')),
                    'ext': ext,
                }
                if source_url.startswith('rtmp'):
                    a_format['ext'] = 'flv'
                    # See com/longtailvideo/jwplayer/media/RTMPMediaProvider.as
                    # of jwplayer.flash.swf
                    rtmp_url_parts = re.split(
                        r'((?:mp4|mp3|flv):)', source_url, 1)
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
        cookie = compat_cookiejar_Cookie(
            0, name, value, port, port is not None, domain, True,
            domain.startswith('.'), path, True, secure, expire_time,
            discard, None, None, rest)
        self._downloader.cookiejar.set_cookie(cookie)

    def _get_cookies(self, url):
        """ Return a compat_cookies_SimpleCookie with the cookies for the url """
        return compat_cookies_SimpleCookie(self._downloader._calc_cookies(url))

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
                r'%s=(.+?);.*?\b[Dd]omain=(.+?)(?:[,;]|$)' % cookie, cookies)
            if cookie_value:
                value, domain = cookie_value.groups()
                self._set_cookie(domain, cookie, value)
                break

    @classmethod
    def get_testcases(cls, include_onlymatching=False):
        t = getattr(cls, '_TEST', None)
        if t:
            assert not hasattr(cls, '_TESTS'), f'{cls.ie_key()}IE has _TEST and _TESTS'
            tests = [t]
        else:
            tests = getattr(cls, '_TESTS', [])
        for t in tests:
            if not include_onlymatching and t.get('only_matching', False):
                continue
            t['name'] = cls.ie_key()
            yield t

    @classproperty
    def age_limit(cls):
        """Get age limit from the testcases"""
        return max(traverse_obj(
            tuple(cls.get_testcases(include_onlymatching=False)),
            (..., (('playlist', 0), None), 'info_dict', 'age_limit')) or [0])

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
                desc += f' [<abbr title="netrc machine"><em>{cls._NETRC_MACHINE}</em></abbr>]'
            else:
                desc += f' [{cls._NETRC_MACHINE}]'
        if cls.IE_DESC is False:
            desc += ' [HIDDEN]'
        elif cls.IE_DESC:
            desc += f' {cls.IE_DESC}'
        if cls.SEARCH_KEY:
            desc += f'; "{cls.SEARCH_KEY}:" prefix'
            if search_examples:
                _COUNTS = ('', '5', '10', 'all')
                desc += f' (Example: "{cls.SEARCH_KEY}{random.choice(_COUNTS)}:{random.choice(search_examples)}")'
        if not cls.working():
            desc += ' (**Currently broken**)' if markdown else ' (Currently broken)'

        name = f' - **{cls.IE_NAME}**' if markdown else cls.IE_NAME
        return f'{name}:{desc}' if desc else name

    def extract_subtitles(self, *args, **kwargs):
        if (self.get_param('writesubtitles', False)
                or self.get_param('listsubtitles')):
            return self._get_subtitles(*args, **kwargs)
        return {}

    def _get_subtitles(self, *args, **kwargs):
        raise NotImplementedError('This method must be implemented by subclasses')

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
            except Exception as e:
                if self.get_param('ignoreerrors') is not True:
                    raise
                self._downloader.report_error(e)
            comment_count = len(comments)
            self.to_screen(f'Extracted {comment_count} comments')
            return {
                'comments': comments,
                'comment_count': None if interrupted else comment_count
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
        for d in dicts:
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
        if self.supports_login() and self._get_login_info()[0] is not None or self._cookies_passed:
            self._mark_watched(*args, **kwargs)

    def _mark_watched(self, *args, **kwargs):
        raise NotImplementedError('This method must be implemented by subclasses')

    def geo_verification_headers(self):
        headers = {}
        geo_verification_proxy = self.get_param('geo_verification_proxy')
        if geo_verification_proxy:
            headers['Ytdl-request-proxy'] = geo_verification_proxy
        return headers

    def _generic_id(self, url):
        return compat_urllib_parse_unquote(os.path.splitext(url.rstrip('/').split('/')[-1])[0])

    def _generic_title(self, url):
        return compat_urllib_parse_unquote(os.path.splitext(url_basename(url))[0])

    @staticmethod
    def _availability(is_private=None, needs_premium=None, needs_subscription=None, needs_auth=None, is_unlisted=None):
        all_known = all(map(
            lambda x: x is not None,
            (is_private, needs_premium, needs_subscription, needs_auth, is_unlisted)))
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
        val = traverse_obj(
            self._downloader.params, ('extractor_args', (ie_key or self.ie_key()).lower(), key))
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


class SearchInfoExtractor(InfoExtractor):
    """
    Base class for paged search queries extractors.
    They accept URLs in the format _SEARCH_KEY(|all|[0-9]):{query}
    Instances should define _SEARCH_KEY and optionally _MAX_RESULTS
    """

    _MAX_RESULTS = float('inf')

    @classmethod
    def _make_valid_url(cls):
        return r'%s(?P<prefix>|[1-9][0-9]*|all):(?P<query>[\s\S]+)' % cls._SEARCH_KEY

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

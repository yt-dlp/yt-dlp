import collections
import contextlib
import copy
import datetime as dt
import errno
import fileinput
import functools
import http.cookiejar
import io
import itertools
import json
import locale
import operator
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import time
import tokenize
import traceback
import unicodedata

from .cache import Cache
from .compat import urllib  # isort: split
from .compat import compat_os_name, urllib_req_to_req
from .cookies import CookieLoadError, LenientSimpleCookie, load_cookies
from .downloader import FFmpegFD, get_suitable_downloader, shorten_protocol_name
from .downloader.rtmp import rtmpdump_version
from .extractor import gen_extractor_classes, get_info_extractor
from .extractor.common import UnsupportedURLIE
from .extractor.openload import PhantomJSwrapper
from .minicurses import format_text
from .networking import HEADRequest, Request, RequestDirector
from .networking.common import _REQUEST_HANDLERS, _RH_PREFERENCES
from .networking.exceptions import (
    HTTPError,
    NoSupportingHandlers,
    RequestError,
    SSLError,
    network_exceptions,
)
from .networking.impersonate import ImpersonateRequestHandler
from .plugins import directories as plugin_directories
from .postprocessor import _PLUGIN_CLASSES as plugin_pps
from .postprocessor import (
    EmbedThumbnailPP,
    FFmpegFixupDuplicateMoovPP,
    FFmpegFixupDurationPP,
    FFmpegFixupM3u8PP,
    FFmpegFixupM4aPP,
    FFmpegFixupStretchedPP,
    FFmpegFixupTimestampPP,
    FFmpegMergerPP,
    FFmpegPostProcessor,
    FFmpegVideoConvertorPP,
    MoveFilesAfterDownloadPP,
    get_postprocessor,
)
from .postprocessor.ffmpeg import resolve_mapping as resolve_recode_mapping
from .update import (
    REPOSITORY,
    _get_system_deprecation,
    _make_label,
    current_git_head,
    detect_variant,
)
from .utils import (
    DEFAULT_OUTTMPL,
    IDENTITY,
    LINK_TEMPLATES,
    MEDIA_EXTENSIONS,
    NO_DEFAULT,
    NUMBER_RE,
    OUTTMPL_TYPES,
    POSTPROCESS_WHEN,
    STR_FORMAT_RE_TMPL,
    STR_FORMAT_TYPES,
    ContentTooShortError,
    DateRange,
    DownloadCancelled,
    DownloadError,
    EntryNotInPlaylist,
    ExistingVideoReached,
    ExtractorError,
    FormatSorter,
    GeoRestrictedError,
    ISO3166Utils,
    LazyList,
    MaxDownloadsReached,
    Namespace,
    PagedList,
    PlaylistEntries,
    Popen,
    PostProcessingError,
    ReExtractInfo,
    RejectedVideoReached,
    SameFileError,
    UnavailableVideoError,
    UserNotLive,
    YoutubeDLError,
    age_restricted,
    bug_reports_message,
    date_from_str,
    deprecation_warning,
    determine_ext,
    determine_protocol,
    encode_compat_str,
    encodeFilename,
    escapeHTML,
    expand_path,
    extract_basic_auth,
    filter_dict,
    float_or_none,
    format_bytes,
    format_decimal_suffix,
    format_field,
    formatSeconds,
    get_compatible_ext,
    get_domain,
    int_or_none,
    iri_to_uri,
    is_path_like,
    join_nonempty,
    locked_file,
    make_archive_id,
    make_dir,
    number_of_digits,
    orderedSet,
    orderedSet_from_options,
    parse_filesize,
    preferredencoding,
    prepend_extension,
    remove_terminal_sequences,
    render_table,
    replace_extension,
    sanitize_filename,
    sanitize_path,
    sanitize_url,
    shell_quote,
    str_or_none,
    strftime_or_none,
    subtitles_filename,
    supports_terminal_sequences,
    system_identifier,
    filesize_from_tbr,
    timetuple_from_msec,
    to_high_limit_path,
    traverse_obj,
    try_call,
    try_get,
    url_basename,
    variadic,
    version_tuple,
    windows_enable_vt_mode,
    write_json_file,
    write_string,
)
from .utils._utils import _UnsafeExtensionError, _YDLLogger
from .utils.networking import (
    HTTPHeaderDict,
    clean_headers,
    clean_proxies,
    std_headers,
)
from .version import CHANNEL, ORIGIN, RELEASE_GIT_HEAD, VARIANT, __version__

if compat_os_name == 'nt':
    import ctypes


def _catch_unsafe_extension_error(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except _UnsafeExtensionError as error:
            self.report_error(
                f'The extracted extension ({error.extension!r}) is unusual '
                'and will be skipped for safety reasons. '
                f'If you believe this is an error{bug_reports_message(",")}')

    return wrapper


class YoutubeDL:
    """YoutubeDL class.

    YoutubeDL objects are the ones responsible of downloading the
    actual video file and writing it to disk if the user has requested
    it, among some other tasks. In most cases there should be one per
    program. As, given a video URL, the downloader doesn't know how to
    extract all the needed information, task that InfoExtractors do, it
    has to pass the URL to one of them.

    For this, YoutubeDL objects have a method that allows
    InfoExtractors to be registered in a given order. When it is passed
    a URL, the YoutubeDL object handles it to the first InfoExtractor it
    finds that reports being able to handle it. The InfoExtractor extracts
    all the information about the video or videos the URL refers to, and
    YoutubeDL process the extracted information, possibly using a File
    Downloader to download the video.

    YoutubeDL objects accept a lot of parameters. In order not to saturate
    the object constructor with arguments, it receives a dictionary of
    options instead. These options are available through the params
    attribute for the InfoExtractors to use. The YoutubeDL also
    registers itself as the downloader in charge for the InfoExtractors
    that are added to it, so this is a "mutual registration".

    Available options:

    username:          Username for authentication purposes.
    password:          Password for authentication purposes.
    videopassword:     Password for accessing a video.
    ap_mso:            Adobe Pass multiple-system operator identifier.
    ap_username:       Multiple-system operator account username.
    ap_password:       Multiple-system operator account password.
    usenetrc:          Use netrc for authentication instead.
    netrc_location:    Location of the netrc file. Defaults to ~/.netrc.
    netrc_cmd:         Use a shell command to get credentials
    verbose:           Print additional info to stdout.
    quiet:             Do not print messages to stdout.
    no_warnings:       Do not print out anything for warnings.
    forceprint:        A dict with keys WHEN mapped to a list of templates to
                       print to stdout. The allowed keys are video or any of the
                       items in utils.POSTPROCESS_WHEN.
                       For compatibility, a single list is also accepted
    print_to_file:     A dict with keys WHEN (same as forceprint) mapped to
                       a list of tuples with (template, filename)
    forcejson:         Force printing info_dict as JSON.
    dump_single_json:  Force printing the info_dict of the whole playlist
                       (or video) as a single JSON line.
    force_write_download_archive: Force writing download archive regardless
                       of 'skip_download' or 'simulate'.
    simulate:          Do not download the video files. If unset (or None),
                       simulate only if listsubtitles, listformats or list_thumbnails is used
    format:            Video format code. see "FORMAT SELECTION" for more details.
                       You can also pass a function. The function takes 'ctx' as
                       argument and returns the formats to download.
                       See "build_format_selector" for an implementation
    allow_unplayable_formats:   Allow unplayable formats to be extracted and downloaded.
    ignore_no_formats_error: Ignore "No video formats" error. Usefull for
                       extracting metadata even if the video is not actually
                       available for download (experimental)
    format_sort:       A list of fields by which to sort the video formats.
                       See "Sorting Formats" for more details.
    format_sort_force: Force the given format_sort. see "Sorting Formats"
                       for more details.
    prefer_free_formats: Whether to prefer video formats with free containers
                       over non-free ones of same quality.
    allow_multiple_video_streams:   Allow multiple video streams to be merged
                       into a single file
    allow_multiple_audio_streams:   Allow multiple audio streams to be merged
                       into a single file
    check_formats      Whether to test if the formats are downloadable.
                       Can be True (check all), False (check none),
                       'selected' (check selected formats),
                       or None (check only if requested by extractor)
    paths:             Dictionary of output paths. The allowed keys are 'home'
                       'temp' and the keys of OUTTMPL_TYPES (in utils/_utils.py)
    outtmpl:           Dictionary of templates for output names. Allowed keys
                       are 'default' and the keys of OUTTMPL_TYPES (in utils/_utils.py).
                       For compatibility with youtube-dl, a single string can also be used
    outtmpl_na_placeholder: Placeholder for unavailable meta fields.
    restrictfilenames: Do not allow "&" and spaces in file names
    trim_file_name:    Limit length of filename (extension excluded)
    windowsfilenames:  Force the filenames to be windows compatible
    ignoreerrors:      Do not stop on download/postprocessing errors.
                       Can be 'only_download' to ignore only download errors.
                       Default is 'only_download' for CLI, but False for API
    skip_playlist_after_errors: Number of allowed failures until the rest of
                       the playlist is skipped
    allowed_extractors:  List of regexes to match against extractor names that are allowed
    overwrites:        Overwrite all video and metadata files if True,
                       overwrite only non-video files if None
                       and don't overwrite any file if False
    playlist_items:    Specific indices of playlist to download.
    playlistrandom:    Download playlist items in random order.
    lazy_playlist:     Process playlist entries as they are received.
    matchtitle:        Download only matching titles.
    rejecttitle:       Reject downloads for matching titles.
    logger:            Log messages to a logging.Logger instance.
    logtostderr:       Print everything to stderr instead of stdout.
    consoletitle:      Display progress in console window's titlebar.
    writedescription:  Write the video description to a .description file
    writeinfojson:     Write the video description to a .info.json file
    clean_infojson:    Remove internal metadata from the infojson
    getcomments:       Extract video comments. This will not be written to disk
                       unless writeinfojson is also given
    writeannotations:  Write the video annotations to a .annotations.xml file
    writethumbnail:    Write the thumbnail image to a file
    allow_playlist_files: Whether to write playlists' description, infojson etc
                       also to disk when using the 'write*' options
    write_all_thumbnails:  Write all thumbnail formats to files
    writelink:         Write an internet shortcut file, depending on the
                       current platform (.url/.webloc/.desktop)
    writeurllink:      Write a Windows internet shortcut file (.url)
    writewebloclink:   Write a macOS internet shortcut file (.webloc)
    writedesktoplink:  Write a Linux internet shortcut file (.desktop)
    writesubtitles:    Write the video subtitles to a file
    writeautomaticsub: Write the automatically generated subtitles to a file
    listsubtitles:     Lists all available subtitles for the video
    subtitlesformat:   The format code for subtitles
    subtitleslangs:    List of languages of the subtitles to download (can be regex).
                       The list may contain "all" to refer to all the available
                       subtitles. The language can be prefixed with a "-" to
                       exclude it from the requested languages, e.g. ['all', '-live_chat']
    keepvideo:         Keep the video file after post-processing
    daterange:         A utils.DateRange object, download only if the upload_date is in the range.
    skip_download:     Skip the actual download of the video file
    cachedir:          Location of the cache files in the filesystem.
                       False to disable filesystem cache.
    noplaylist:        Download single video instead of a playlist if in doubt.
    age_limit:         An integer representing the user's age in years.
                       Unsuitable videos for the given age are skipped.
    min_views:         An integer representing the minimum view count the video
                       must have in order to not be skipped.
                       Videos without view count information are always
                       downloaded. None for no limit.
    max_views:         An integer representing the maximum view count.
                       Videos that are more popular than that are not
                       downloaded.
                       Videos without view count information are always
                       downloaded. None for no limit.
    download_archive:  A set, or the name of a file where all downloads are recorded.
                       Videos already present in the file are not downloaded again.
    break_on_existing: Stop the download process after attempting to download a
                       file that is in the archive.
    break_per_url:     Whether break_on_reject and break_on_existing
                       should act on each input URL as opposed to for the entire queue
    cookiefile:        File name or text stream from where cookies should be read and dumped to
    cookiesfrombrowser:  A tuple containing the name of the browser, the profile
                       name/path from where cookies are loaded, the name of the keyring,
                       and the container name, e.g. ('chrome', ) or
                       ('vivaldi', 'default', 'BASICTEXT') or ('firefox', 'default', None, 'Meta')
    legacyserverconnect: Explicitly allow HTTPS connection to servers that do not
                       support RFC 5746 secure renegotiation
    nocheckcertificate:  Do not verify SSL certificates
    client_certificate:  Path to client certificate file in PEM format. May include the private key
    client_certificate_key:  Path to private key file for client certificate
    client_certificate_password:  Password for client certificate private key, if encrypted.
                        If not provided and the key is encrypted, yt-dlp will ask interactively
    prefer_insecure:   Use HTTP instead of HTTPS to retrieve information.
                       (Only supported by some extractors)
    enable_file_urls:  Enable file:// URLs. This is disabled by default for security reasons.
    http_headers:      A dictionary of custom headers to be used for all requests
    proxy:             URL of the proxy server to use
    geo_verification_proxy:  URL of the proxy to use for IP address verification
                       on geo-restricted sites.
    socket_timeout:    Time to wait for unresponsive hosts, in seconds
    bidi_workaround:   Work around buggy terminals without bidirectional text
                       support, using fridibi
    debug_printtraffic:Print out sent and received HTTP traffic
    default_search:    Prepend this string if an input url is not valid.
                       'auto' for elaborate guessing
    encoding:          Use this encoding instead of the system-specified.
    extract_flat:      Whether to resolve and process url_results further
                       * False:     Always process. Default for API
                       * True:      Never process
                       * 'in_playlist': Do not process inside playlist/multi_video
                       * 'discard': Always process, but don't return the result
                                    from inside playlist/multi_video
                       * 'discard_in_playlist': Same as "discard", but only for
                                    playlists (not multi_video). Default for CLI
    wait_for_video:    If given, wait for scheduled streams to become available.
                       The value should be a tuple containing the range
                       (min_secs, max_secs) to wait between retries
    postprocessors:    A list of dictionaries, each with an entry
                       * key:  The name of the postprocessor. See
                               yt_dlp/postprocessor/__init__.py for a list.
                       * when: When to run the postprocessor. Allowed values are
                               the entries of utils.POSTPROCESS_WHEN
                               Assumed to be 'post_process' if not given
    progress_hooks:    A list of functions that get called on download
                       progress, with a dictionary with the entries
                       * status: One of "downloading", "error", or "finished".
                                 Check this first and ignore unknown values.
                       * info_dict: The extracted info_dict

                       If status is one of "downloading", or "finished", the
                       following properties may also be present:
                       * filename: The final filename (always present)
                       * tmpfilename: The filename we're currently writing to
                       * downloaded_bytes: Bytes on disk
                       * total_bytes: Size of the whole file, None if unknown
                       * total_bytes_estimate: Guess of the eventual file size,
                                               None if unavailable.
                       * elapsed: The number of seconds since download started.
                       * eta: The estimated time in seconds, None if unknown
                       * speed: The download speed in bytes/second, None if
                                unknown
                       * fragment_index: The counter of the currently
                                         downloaded video fragment.
                       * fragment_count: The number of fragments (= individual
                                         files that will be merged)

                       Progress hooks are guaranteed to be called at least once
                       (with status "finished") if the download is successful.
    postprocessor_hooks:  A list of functions that get called on postprocessing
                       progress, with a dictionary with the entries
                       * status: One of "started", "processing", or "finished".
                                 Check this first and ignore unknown values.
                       * postprocessor: Name of the postprocessor
                       * info_dict: The extracted info_dict

                       Progress hooks are guaranteed to be called at least twice
                       (with status "started" and "finished") if the processing is successful.
    merge_output_format: "/" separated list of extensions to use when merging formats.
    final_ext:         Expected final extension; used to detect when the file was
                       already downloaded and converted
    fixup:             Automatically correct known faults of the file.
                       One of:
                       - "never": do nothing
                       - "warn": only emit a warning
                       - "detect_or_warn": check whether we can do anything
                                           about it, warn otherwise (default)
    source_address:    Client-side IP address to bind to.
    impersonate:       Client to impersonate for requests.
                       An ImpersonateTarget (from yt_dlp.networking.impersonate)
    sleep_interval_requests: Number of seconds to sleep between requests
                       during extraction
    sleep_interval:    Number of seconds to sleep before each download when
                       used alone or a lower bound of a range for randomized
                       sleep before each download (minimum possible number
                       of seconds to sleep) when used along with
                       max_sleep_interval.
    max_sleep_interval:Upper bound of a range for randomized sleep before each
                       download (maximum possible number of seconds to sleep).
                       Must only be used along with sleep_interval.
                       Actual sleep time will be a random float from range
                       [sleep_interval; max_sleep_interval].
    sleep_interval_subtitles: Number of seconds to sleep before each subtitle download
    listformats:       Print an overview of available video formats and exit.
    list_thumbnails:   Print a table of all thumbnails and exit.
    match_filter:      A function that gets called for every video with the signature
                       (info_dict, *, incomplete: bool) -> Optional[str]
                       For backward compatibility with youtube-dl, the signature
                       (info_dict) -> Optional[str] is also allowed.
                       - If it returns a message, the video is ignored.
                       - If it returns None, the video is downloaded.
                       - If it returns utils.NO_DEFAULT, the user is interactively
                         asked whether to download the video.
                       - Raise utils.DownloadCancelled(msg) to abort remaining
                         downloads when a video is rejected.
                       match_filter_func in utils/_utils.py is one example for this.
    color:             A Dictionary with output stream names as keys
                       and their respective color policy as values.
                       Can also just be a single color policy,
                       in which case it applies to all outputs.
                       Valid stream names are 'stdout' and 'stderr'.
                       Valid color policies are one of 'always', 'auto',
                       'no_color', 'never', 'auto-tty' or 'no_color-tty'.
    geo_bypass:        Bypass geographic restriction via faking X-Forwarded-For
                       HTTP header
    geo_bypass_country:
                       Two-letter ISO 3166-2 country code that will be used for
                       explicit geographic restriction bypassing via faking
                       X-Forwarded-For HTTP header
    geo_bypass_ip_block:
                       IP range in CIDR notation that will be used similarly to
                       geo_bypass_country
    external_downloader: A dictionary of protocol keys and the executable of the
                       external downloader to use for it. The allowed protocols
                       are default|http|ftp|m3u8|dash|rtsp|rtmp|mms.
                       Set the value to 'native' to use the native downloader
    compat_opts:       Compatibility options. See "Differences in default behavior".
                       The following options do not work when used through the API:
                       filename, abort-on-error, multistreams, no-live-chat,
                       format-sort, no-clean-infojson, no-playlist-metafiles,
                       no-keep-subs, no-attach-info-json, allow-unsafe-ext.
                       Refer __init__.py for their implementation
    progress_template: Dictionary of templates for progress outputs.
                       Allowed keys are 'download', 'postprocess',
                       'download-title' (console title) and 'postprocess-title'.
                       The template is mapped on a dictionary with keys 'progress' and 'info'
    retry_sleep_functions: Dictionary of functions that takes the number of attempts
                       as argument and returns the time to sleep in seconds.
                       Allowed keys are 'http', 'fragment', 'file_access'
    download_ranges:   A callback function that gets called for every video with
                       the signature (info_dict, ydl) -> Iterable[Section].
                       Only the returned sections will be downloaded.
                       Each Section is a dict with the following keys:
                       * start_time: Start time of the section in seconds
                       * end_time: End time of the section in seconds
                       * title: Section title (Optional)
                       * index: Section number (Optional)
    force_keyframes_at_cuts: Re-encode the video when downloading ranges to get precise cuts
    noprogress:        Do not print the progress bar
    live_from_start:   Whether to download livestreams videos from the start

    The following parameters are not used by YoutubeDL itself, they are used by
    the downloader (see yt_dlp/downloader/common.py):
    nopart, updatetime, buffersize, ratelimit, throttledratelimit, min_filesize,
    max_filesize, test, noresizebuffer, retries, file_access_retries, fragment_retries,
    continuedl, xattr_set_filesize, hls_use_mpegts, http_chunk_size,
    external_downloader_args, concurrent_fragment_downloads, progress_delta.

    The following options are used by the post processors:
    ffmpeg_location:   Location of the ffmpeg/avconv binary; either the path
                       to the binary or its containing directory.
    postprocessor_args: A dictionary of postprocessor/executable keys (in lower case)
                       and a list of additional command-line arguments for the
                       postprocessor/executable. The dict can also have "PP+EXE" keys
                       which are used when the given exe is used by the given PP.
                       Use 'default' as the name for arguments to passed to all PP
                       For compatibility with youtube-dl, a single list of args
                       can also be used

    The following options are used by the extractors:
    extractor_retries: Number of times to retry for known errors (default: 3)
    dynamic_mpd:       Whether to process dynamic DASH manifests (default: True)
    hls_split_discontinuity: Split HLS playlists to different formats at
                       discontinuities such as ad breaks (default: False)
    extractor_args:    A dictionary of arguments to be passed to the extractors.
                       See "EXTRACTOR ARGUMENTS" for details.
                       E.g. {'youtube': {'skip': ['dash', 'hls']}}
    mark_watched:      Mark videos watched (even with --simulate). Only for YouTube

    The following options are deprecated and may be removed in the future:

    break_on_reject:   Stop the download process when encountering a video that
                       has been filtered out.
                       - `raise DownloadCancelled(msg)` in match_filter instead
    force_generic_extractor: Force downloader to use the generic extractor
                       - Use allowed_extractors = ['generic', 'default']
    playliststart:     - Use playlist_items
                       Playlist item to start at.
    playlistend:       - Use playlist_items
                       Playlist item to end at.
    playlistreverse:   - Use playlist_items
                       Download playlist items in reverse order.
    forceurl:          - Use forceprint
                       Force printing final URL.
    forcetitle:        - Use forceprint
                       Force printing title.
    forceid:           - Use forceprint
                       Force printing ID.
    forcethumbnail:    - Use forceprint
                       Force printing thumbnail URL.
    forcedescription:  - Use forceprint
                       Force printing description.
    forcefilename:     - Use forceprint
                       Force printing final filename.
    forceduration:     - Use forceprint
                       Force printing duration.
    allsubtitles:      - Use subtitleslangs = ['all']
                       Downloads all the subtitles of the video
                       (requires writesubtitles or writeautomaticsub)
    include_ads:       - Doesn't work
                       Download ads as well
    call_home:         - Not implemented
                       Boolean, true iff we are allowed to contact the
                       yt-dlp servers for debugging.
    post_hooks:        - Register a custom postprocessor
                       A list of functions that get called as the final step
                       for each video file, after all postprocessors have been
                       called. The filename will be passed as the only argument.
    hls_prefer_native: - Use external_downloader = {'m3u8': 'native'} or {'m3u8': 'ffmpeg'}.
                       Use the native HLS downloader instead of ffmpeg/avconv
                       if True, otherwise use ffmpeg/avconv if False, otherwise
                       use downloader suggested by extractor if None.
    prefer_ffmpeg:     - avconv support is deprecated
                       If False, use avconv instead of ffmpeg if both are available,
                       otherwise prefer ffmpeg.
    youtube_include_dash_manifest: - Use extractor_args
                       If True (default), DASH manifests and related
                       data will be downloaded and processed by extractor.
                       You can reduce network I/O by disabling it if you don't
                       care about DASH. (only for youtube)
    youtube_include_hls_manifest: - Use extractor_args
                       If True (default), HLS manifests and related
                       data will be downloaded and processed by extractor.
                       You can reduce network I/O by disabling it if you don't
                       care about HLS. (only for youtube)
    no_color:          Same as `color='no_color'`
    no_overwrites:     Same as `overwrites=False`
    """

    _NUMERIC_FIELDS = {
        'width', 'height', 'asr', 'audio_channels', 'fps',
        'tbr', 'abr', 'vbr', 'filesize', 'filesize_approx',
        'timestamp', 'release_timestamp',
        'duration', 'view_count', 'like_count', 'dislike_count', 'repost_count',
        'average_rating', 'comment_count', 'age_limit',
        'start_time', 'end_time',
        'chapter_number', 'season_number', 'episode_number',
        'track_number', 'disc_number', 'release_year',
    }

    _format_fields = {
        # NB: Keep in sync with the docstring of extractor/common.py
        'url', 'manifest_url', 'manifest_stream_number', 'ext', 'format', 'format_id', 'format_note',
        'width', 'height', 'aspect_ratio', 'resolution', 'dynamic_range', 'tbr', 'abr', 'acodec', 'asr', 'audio_channels',
        'vbr', 'fps', 'vcodec', 'container', 'filesize', 'filesize_approx', 'rows', 'columns',
        'player_url', 'protocol', 'fragment_base_url', 'fragments', 'is_from_start', 'is_dash_periods', 'request_data',
        'preference', 'language', 'language_preference', 'quality', 'source_preference', 'cookies',
        'http_headers', 'stretched_ratio', 'no_resume', 'has_drm', 'extra_param_to_segment_url', 'extra_param_to_key_url',
        'hls_aes', 'downloader_options', 'page_url', 'app', 'play_path', 'tc_url', 'flash_version',
        'rtmp_live', 'rtmp_conn', 'rtmp_protocol', 'rtmp_real_time',
    }
    _deprecated_multivalue_fields = {
        'album_artist': 'album_artists',
        'artist': 'artists',
        'composer': 'composers',
        'creator': 'creators',
        'genre': 'genres',
    }
    _format_selection_exts = {
        'audio': set(MEDIA_EXTENSIONS.common_audio),
        'video': {*MEDIA_EXTENSIONS.common_video, '3gp'},
        'storyboards': set(MEDIA_EXTENSIONS.storyboards),
    }

    def __init__(self, params=None, auto_init=True):
        """Create a FileDownloader object with the given options.
        @param auto_init    Whether to load the default extractors and print header (if verbose).
                            Set to 'no_verbose_header' to not print the header
        """
        if params is None:
            params = {}
        self.params = params
        self._ies = {}
        self._ies_instances = {}
        self._pps = {k: [] for k in POSTPROCESS_WHEN}
        self._printed_messages = set()
        self._first_webpage_request = True
        self._post_hooks = []
        self._progress_hooks = []
        self._postprocessor_hooks = []
        self._download_retcode = 0
        self._num_downloads = 0
        self._num_videos = 0
        self._playlist_level = 0
        self._playlist_urls = set()
        self.cache = Cache(self)
        self.__header_cookies = []

        stdout = sys.stderr if self.params.get('logtostderr') else sys.stdout
        self._out_files = Namespace(
            out=stdout,
            error=sys.stderr,
            screen=sys.stderr if self.params.get('quiet') else stdout,
            console=None if compat_os_name == 'nt' else next(
                filter(supports_terminal_sequences, (sys.stderr, sys.stdout)), None),
        )

        try:
            windows_enable_vt_mode()
        except Exception as e:
            self.write_debug(f'Failed to enable VT mode: {e}')

        if self.params.get('no_color'):
            if self.params.get('color') is not None:
                self.params.setdefault('_warnings', []).append(
                    'Overwriting params from "color" with "no_color"')
            self.params['color'] = 'no_color'

        term_allow_color = os.getenv('TERM', '').lower() != 'dumb'
        base_no_color = bool(os.getenv('NO_COLOR'))

        def process_color_policy(stream):
            stream_name = {sys.stdout: 'stdout', sys.stderr: 'stderr'}[stream]
            policy = traverse_obj(self.params, ('color', (stream_name, None), {str}, any)) or 'auto'
            if policy in ('auto', 'auto-tty', 'no_color-tty'):
                no_color = base_no_color
                if policy.endswith('tty'):
                    no_color = policy.startswith('no_color')
                if term_allow_color and supports_terminal_sequences(stream):
                    return 'no_color' if no_color else True
                return False
            assert policy in ('always', 'never', 'no_color'), policy
            return {'always': True, 'never': False}.get(policy, policy)

        self._allow_colors = Namespace(**{
            name: process_color_policy(stream)
            for name, stream in self._out_files.items_ if name != 'console'
        })

        system_deprecation = _get_system_deprecation()
        if system_deprecation:
            self.deprecated_feature(system_deprecation.replace('\n', '\n                    '))

        if self.params.get('allow_unplayable_formats'):
            self.report_warning(
                f'You have asked for {self._format_err("UNPLAYABLE", self.Styles.EMPHASIS)} formats to be listed/downloaded. '
                'This is a developer option intended for debugging. \n'
                '         If you experience any issues while using this option, '
                f'{self._format_err("DO NOT", self.Styles.ERROR)} open a bug report')

        if self.params.get('bidi_workaround', False):
            try:
                import pty
                master, slave = pty.openpty()
                width = shutil.get_terminal_size().columns
                width_args = [] if width is None else ['-w', str(width)]
                sp_kwargs = {'stdin': subprocess.PIPE, 'stdout': slave, 'stderr': self._out_files.error}
                try:
                    self._output_process = Popen(['bidiv', *width_args], **sp_kwargs)
                except OSError:
                    self._output_process = Popen(['fribidi', '-c', 'UTF-8', *width_args], **sp_kwargs)
                self._output_channel = os.fdopen(master, 'rb')
            except OSError as ose:
                if ose.errno == errno.ENOENT:
                    self.report_warning(
                        'Could not find fribidi executable, ignoring --bidi-workaround. '
                        'Make sure that  fribidi  is an executable file in one of the directories in your $PATH.')
                else:
                    raise

        self.params['compat_opts'] = set(self.params.get('compat_opts', ()))
        self.params['http_headers'] = HTTPHeaderDict(std_headers, self.params.get('http_headers'))
        self._load_cookies(self.params['http_headers'].get('Cookie'))  # compat
        self.params['http_headers'].pop('Cookie', None)

        if auto_init and auto_init != 'no_verbose_header':
            self.print_debug_header()

        def check_deprecated(param, option, suggestion):
            if self.params.get(param) is not None:
                self.report_warning(f'{option} is deprecated. Use {suggestion} instead')
                return True
            return False

        if check_deprecated('cn_verification_proxy', '--cn-verification-proxy', '--geo-verification-proxy'):
            if self.params.get('geo_verification_proxy') is None:
                self.params['geo_verification_proxy'] = self.params['cn_verification_proxy']

        check_deprecated('autonumber', '--auto-number', '-o "%(autonumber)s-%(title)s.%(ext)s"')
        check_deprecated('usetitle', '--title', '-o "%(title)s-%(id)s.%(ext)s"')
        check_deprecated('useid', '--id', '-o "%(id)s.%(ext)s"')

        for msg in self.params.get('_warnings', []):
            self.report_warning(msg)
        for msg in self.params.get('_deprecation_warnings', []):
            self.deprecated_feature(msg)

        if impersonate_target := self.params.get('impersonate'):
            if not self._impersonate_target_available(impersonate_target):
                raise YoutubeDLError(
                    f'Impersonate target "{impersonate_target}" is not available. '
                    f'Use --list-impersonate-targets to see available targets. '
                    f'You may be missing dependencies required to support this target.')

        if 'list-formats' in self.params['compat_opts']:
            self.params['listformats_table'] = False

        if 'overwrites' not in self.params and self.params.get('nooverwrites') is not None:
            # nooverwrites was unnecessarily changed to overwrites
            # in 0c3d0f51778b153f65c21906031c2e091fcfb641
            # This ensures compatibility with both keys
            self.params['overwrites'] = not self.params['nooverwrites']
        elif self.params.get('overwrites') is None:
            self.params.pop('overwrites', None)
        else:
            self.params['nooverwrites'] = not self.params['overwrites']

        if self.params.get('simulate') is None and any((
            self.params.get('list_thumbnails'),
            self.params.get('listformats'),
            self.params.get('listsubtitles'),
        )):
            self.params['simulate'] = 'list_only'

        self.params.setdefault('forceprint', {})
        self.params.setdefault('print_to_file', {})

        # Compatibility with older syntax
        if not isinstance(params['forceprint'], dict):
            self.params['forceprint'] = {'video': params['forceprint']}

        if auto_init:
            self.add_default_info_extractors()

        if (sys.platform != 'win32'
                and sys.getfilesystemencoding() in ['ascii', 'ANSI_X3.4-1968']
                and not self.params.get('restrictfilenames', False)):
            # Unicode filesystem API will throw errors (#1474, #13027)
            self.report_warning(
                'Assuming --restrict-filenames since file system encoding '
                'cannot encode all characters. '
                'Set the LC_ALL environment variable to fix this.')
            self.params['restrictfilenames'] = True

        self._parse_outtmpl()

        # Creating format selector here allows us to catch syntax errors before the extraction
        self.format_selector = (
            self.params.get('format') if self.params.get('format') in (None, '-')
            else self.params['format'] if callable(self.params['format'])
            else self.build_format_selector(self.params['format']))

        hooks = {
            'post_hooks': self.add_post_hook,
            'progress_hooks': self.add_progress_hook,
            'postprocessor_hooks': self.add_postprocessor_hook,
        }
        for opt, fn in hooks.items():
            for ph in self.params.get(opt, []):
                fn(ph)

        for pp_def_raw in self.params.get('postprocessors', []):
            pp_def = dict(pp_def_raw)
            when = pp_def.pop('when', 'post_process')
            self.add_post_processor(
                get_postprocessor(pp_def.pop('key'))(self, **pp_def),
                when=when)

        def preload_download_archive(fn):
            """Preload the archive, if any is specified"""
            archive = set()
            if fn is None:
                return archive
            elif not is_path_like(fn):
                return fn

            self.write_debug(f'Loading archive file {fn!r}')
            try:
                with locked_file(fn, 'r', encoding='utf-8') as archive_file:
                    for line in archive_file:
                        archive.add(line.strip())
            except OSError as ioe:
                if ioe.errno != errno.ENOENT:
                    raise
            return archive

        self.archive = preload_download_archive(self.params.get('download_archive'))

    def warn_if_short_id(self, argv):
        # short YouTube ID starting with dash?
        idxs = [
            i for i, a in enumerate(argv)
            if re.match(r'^-[0-9A-Za-z_-]{10}$', a)]
        if idxs:
            correct_argv = (
                ['yt-dlp']
                + [a for i, a in enumerate(argv) if i not in idxs]
                + ['--'] + [argv[i] for i in idxs]
            )
            self.report_warning(
                'Long argument string detected. '
                f'Use -- to separate parameters and URLs, like this:\n{shell_quote(correct_argv)}')

    def add_info_extractor(self, ie):
        """Add an InfoExtractor object to the end of the list."""
        ie_key = ie.ie_key()
        self._ies[ie_key] = ie
        if not isinstance(ie, type):
            self._ies_instances[ie_key] = ie
            ie.set_downloader(self)

    def get_info_extractor(self, ie_key):
        """
        Get an instance of an IE with name ie_key, it will try to get one from
        the _ies list, if there's no instance it will create a new one and add
        it to the extractor list.
        """
        ie = self._ies_instances.get(ie_key)
        if ie is None:
            ie = get_info_extractor(ie_key)()
            self.add_info_extractor(ie)
        return ie

    def add_default_info_extractors(self):
        """
        Add the InfoExtractors returned by gen_extractors to the end of the list
        """
        all_ies = {ie.IE_NAME.lower(): ie for ie in gen_extractor_classes()}
        all_ies['end'] = UnsupportedURLIE()
        try:
            ie_names = orderedSet_from_options(
                self.params.get('allowed_extractors', ['default']), {
                    'all': list(all_ies),
                    'default': [name for name, ie in all_ies.items() if ie._ENABLED],
                }, use_regex=True)
        except re.error as e:
            raise ValueError(f'Wrong regex for allowed_extractors: {e.pattern}')
        for name in ie_names:
            self.add_info_extractor(all_ies[name])
        self.write_debug(f'Loaded {len(ie_names)} extractors')

    def add_post_processor(self, pp, when='post_process'):
        """Add a PostProcessor object to the end of the chain."""
        assert when in POSTPROCESS_WHEN, f'Invalid when={when}'
        self._pps[when].append(pp)
        pp.set_downloader(self)

    def add_post_hook(self, ph):
        """Add the post hook"""
        self._post_hooks.append(ph)

    def add_progress_hook(self, ph):
        """Add the download progress hook"""
        self._progress_hooks.append(ph)

    def add_postprocessor_hook(self, ph):
        """Add the postprocessing progress hook"""
        self._postprocessor_hooks.append(ph)
        for pps in self._pps.values():
            for pp in pps:
                pp.add_progress_hook(ph)

    def _bidi_workaround(self, message):
        if not hasattr(self, '_output_channel'):
            return message

        assert hasattr(self, '_output_process')
        assert isinstance(message, str)
        line_count = message.count('\n') + 1
        self._output_process.stdin.write((message + '\n').encode())
        self._output_process.stdin.flush()
        res = ''.join(self._output_channel.readline().decode()
                      for _ in range(line_count))
        return res[:-len('\n')]

    def _write_string(self, message, out=None, only_once=False):
        if only_once:
            if message in self._printed_messages:
                return
            self._printed_messages.add(message)
        write_string(message, out=out, encoding=self.params.get('encoding'))

    def to_stdout(self, message, skip_eol=False, quiet=None):
        """Print message to stdout"""
        if quiet is not None:
            self.deprecation_warning('"YoutubeDL.to_stdout" no longer accepts the argument quiet. '
                                     'Use "YoutubeDL.to_screen" instead')
        if skip_eol is not False:
            self.deprecation_warning('"YoutubeDL.to_stdout" no longer accepts the argument skip_eol. '
                                     'Use "YoutubeDL.to_screen" instead')
        self._write_string(f'{self._bidi_workaround(message)}\n', self._out_files.out)

    def to_screen(self, message, skip_eol=False, quiet=None, only_once=False):
        """Print message to screen if not in quiet mode"""
        if self.params.get('logger'):
            self.params['logger'].debug(message)
            return
        if (self.params.get('quiet') if quiet is None else quiet) and not self.params.get('verbose'):
            return
        self._write_string(
            '{}{}'.format(self._bidi_workaround(message), ('' if skip_eol else '\n')),
            self._out_files.screen, only_once=only_once)

    def to_stderr(self, message, only_once=False):
        """Print message to stderr"""
        assert isinstance(message, str)
        if self.params.get('logger'):
            self.params['logger'].error(message)
        else:
            self._write_string(f'{self._bidi_workaround(message)}\n', self._out_files.error, only_once=only_once)

    def _send_console_code(self, code):
        if compat_os_name == 'nt' or not self._out_files.console:
            return
        self._write_string(code, self._out_files.console)

    def to_console_title(self, message):
        if not self.params.get('consoletitle', False):
            return
        message = remove_terminal_sequences(message)
        if compat_os_name == 'nt':
            if ctypes.windll.kernel32.GetConsoleWindow():
                # c_wchar_p() might not be necessary if `message` is
                # already of type unicode()
                ctypes.windll.kernel32.SetConsoleTitleW(ctypes.c_wchar_p(message))
        else:
            self._send_console_code(f'\033]0;{message}\007')

    def save_console_title(self):
        if not self.params.get('consoletitle') or self.params.get('simulate'):
            return
        self._send_console_code('\033[22;0t')  # Save the title on stack

    def restore_console_title(self):
        if not self.params.get('consoletitle') or self.params.get('simulate'):
            return
        self._send_console_code('\033[23;0t')  # Restore the title from stack

    def __enter__(self):
        self.save_console_title()
        return self

    def save_cookies(self):
        if self.params.get('cookiefile') is not None:
            self.cookiejar.save()

    def __exit__(self, *args):
        self.restore_console_title()
        self.close()

    def close(self):
        self.save_cookies()
        if '_request_director' in self.__dict__:
            self._request_director.close()
            del self._request_director

    def trouble(self, message=None, tb=None, is_error=True):
        """Determine action to take when a download problem appears.

        Depending on if the downloader has been configured to ignore
        download errors or not, this method may throw an exception or
        not when errors are found, after printing the message.

        @param tb          If given, is additional traceback information
        @param is_error    Whether to raise error according to ignorerrors
        """
        if message is not None:
            self.to_stderr(message)
        if self.params.get('verbose'):
            if tb is None:
                if sys.exc_info()[0]:  # if .trouble has been called from an except block
                    tb = ''
                    if hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                        tb += ''.join(traceback.format_exception(*sys.exc_info()[1].exc_info))
                    tb += encode_compat_str(traceback.format_exc())
                else:
                    tb_data = traceback.format_list(traceback.extract_stack())
                    tb = ''.join(tb_data)
            if tb:
                self.to_stderr(tb)
        if not is_error:
            return
        if not self.params.get('ignoreerrors'):
            if sys.exc_info()[0] and hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                exc_info = sys.exc_info()[1].exc_info
            else:
                exc_info = sys.exc_info()
            raise DownloadError(message, exc_info)
        self._download_retcode = 1

    Styles = Namespace(
        HEADERS='yellow',
        EMPHASIS='light blue',
        FILENAME='green',
        ID='green',
        DELIM='blue',
        ERROR='red',
        BAD_FORMAT='light red',
        WARNING='yellow',
        SUPPRESS='light black',
    )

    def _format_text(self, handle, allow_colors, text, f, fallback=None, *, test_encoding=False):
        text = str(text)
        if test_encoding:
            original_text = text
            # handle.encoding can be None. See https://github.com/yt-dlp/yt-dlp/issues/2711
            encoding = self.params.get('encoding') or getattr(handle, 'encoding', None) or 'ascii'
            text = text.encode(encoding, 'ignore').decode(encoding)
            if fallback is not None and text != original_text:
                text = fallback
        return format_text(text, f) if allow_colors is True else text if fallback is None else fallback

    def _format_out(self, *args, **kwargs):
        return self._format_text(self._out_files.out, self._allow_colors.out, *args, **kwargs)

    def _format_screen(self, *args, **kwargs):
        return self._format_text(self._out_files.screen, self._allow_colors.screen, *args, **kwargs)

    def _format_err(self, *args, **kwargs):
        return self._format_text(self._out_files.error, self._allow_colors.error, *args, **kwargs)

    def report_warning(self, message, only_once=False):
        """
        Print the message to stderr, it will be prefixed with 'WARNING:'
        If stderr is a tty file the 'WARNING:' will be colored
        """
        if self.params.get('logger') is not None:
            self.params['logger'].warning(message)
        else:
            if self.params.get('no_warnings'):
                return
            self.to_stderr(f'{self._format_err("WARNING:", self.Styles.WARNING)} {message}', only_once)

    def deprecation_warning(self, message, *, stacklevel=0):
        deprecation_warning(
            message, stacklevel=stacklevel + 1, printer=self.report_error, is_error=False)

    def deprecated_feature(self, message):
        if self.params.get('logger') is not None:
            self.params['logger'].warning(f'Deprecated Feature: {message}')
        self.to_stderr(f'{self._format_err("Deprecated Feature:", self.Styles.ERROR)} {message}', True)

    def report_error(self, message, *args, **kwargs):
        """
        Do the same as trouble, but prefixes the message with 'ERROR:', colored
        in red if stderr is a tty file.
        """
        self.trouble(f'{self._format_err("ERROR:", self.Styles.ERROR)} {message}', *args, **kwargs)

    def write_debug(self, message, only_once=False):
        """Log debug message or Print message to stderr"""
        if not self.params.get('verbose', False):
            return
        message = f'[debug] {message}'
        if self.params.get('logger'):
            self.params['logger'].debug(message)
        else:
            self.to_stderr(message, only_once)

    def report_file_already_downloaded(self, file_name):
        """Report file has already been fully downloaded."""
        try:
            self.to_screen(f'[download] {file_name} has already been downloaded')
        except UnicodeEncodeError:
            self.to_screen('[download] The file has already been downloaded')

    def report_file_delete(self, file_name):
        """Report that existing file will be deleted."""
        try:
            self.to_screen(f'Deleting existing file {file_name}')
        except UnicodeEncodeError:
            self.to_screen('Deleting existing file')

    def raise_no_formats(self, info, forced=False, *, msg=None):
        has_drm = info.get('_has_drm')
        ignored, expected = self.params.get('ignore_no_formats_error'), bool(msg)
        msg = msg or has_drm and 'This video is DRM protected' or 'No video formats found!'
        if forced or not ignored:
            raise ExtractorError(msg, video_id=info['id'], ie=info['extractor'],
                                 expected=has_drm or ignored or expected)
        else:
            self.report_warning(msg)

    def parse_outtmpl(self):
        self.deprecation_warning('"YoutubeDL.parse_outtmpl" is deprecated and may be removed in a future version')
        self._parse_outtmpl()
        return self.params['outtmpl']

    def _parse_outtmpl(self):
        sanitize = IDENTITY
        if self.params.get('restrictfilenames'):  # Remove spaces in the default template
            sanitize = lambda x: x.replace(' - ', ' ').replace(' ', '-')

        outtmpl = self.params.setdefault('outtmpl', {})
        if not isinstance(outtmpl, dict):
            self.params['outtmpl'] = outtmpl = {'default': outtmpl}
        outtmpl.update({k: sanitize(v) for k, v in DEFAULT_OUTTMPL.items() if outtmpl.get(k) is None})

    def get_output_path(self, dir_type='', filename=None):
        paths = self.params.get('paths', {})
        assert isinstance(paths, dict), '"paths" parameter must be a dictionary'
        path = os.path.join(
            expand_path(paths.get('home', '').strip()),
            expand_path(paths.get(dir_type, '').strip()) if dir_type else '',
            filename or '')
        return sanitize_path(path, force=self.params.get('windowsfilenames'))

    @staticmethod
    def _outtmpl_expandpath(outtmpl):
        # expand_path translates '%%' into '%' and '$$' into '$'
        # correspondingly that is not what we want since we need to keep
        # '%%' intact for template dict substitution step. Working around
        # with boundary-alike separator hack.
        sep = ''.join(random.choices(string.ascii_letters, k=32))
        outtmpl = outtmpl.replace('%%', f'%{sep}%').replace('$$', f'${sep}$')

        # outtmpl should be expand_path'ed before template dict substitution
        # because meta fields may contain env variables we don't want to
        # be expanded. E.g. for outtmpl "%(title)s.%(ext)s" and
        # title "Hello $PATH", we don't want `$PATH` to be expanded.
        return expand_path(outtmpl).replace(sep, '')

    @staticmethod
    def escape_outtmpl(outtmpl):
        """ Escape any remaining strings like %s, %abc% etc. """
        return re.sub(
            STR_FORMAT_RE_TMPL.format('', '(?![%(\0])'),
            lambda mobj: ('' if mobj.group('has_key') else '%') + mobj.group(0),
            outtmpl)

    @classmethod
    def validate_outtmpl(cls, outtmpl):
        """ @return None or Exception object """
        outtmpl = re.sub(
            STR_FORMAT_RE_TMPL.format('[^)]*', '[ljhqBUDS]'),
            lambda mobj: f'{mobj.group(0)[:-1]}s',
            cls._outtmpl_expandpath(outtmpl))
        try:
            cls.escape_outtmpl(outtmpl) % collections.defaultdict(int)
            return None
        except ValueError as err:
            return err

    @staticmethod
    def _copy_infodict(info_dict):
        info_dict = dict(info_dict)
        info_dict.pop('__postprocessors', None)
        info_dict.pop('__pending_error', None)
        return info_dict

    def prepare_outtmpl(self, outtmpl, info_dict, sanitize=False):
        """ Make the outtmpl and info_dict suitable for substitution: ydl.escape_outtmpl(outtmpl) % info_dict
        @param sanitize    Whether to sanitize the output as a filename.
                           For backward compatibility, a function can also be passed
        """

        info_dict.setdefault('epoch', int(time.time()))  # keep epoch consistent once set

        info_dict = self._copy_infodict(info_dict)
        info_dict['duration_string'] = (  # %(duration>%H-%M-%S)s is wrong if duration > 24hrs
            formatSeconds(info_dict['duration'], '-' if sanitize else ':')
            if info_dict.get('duration', None) is not None
            else None)
        info_dict['autonumber'] = int(self.params.get('autonumber_start', 1) - 1 + self._num_downloads)
        info_dict['video_autonumber'] = self._num_videos
        if info_dict.get('resolution') is None:
            info_dict['resolution'] = self.format_resolution(info_dict, default=None)

        # For fields playlist_index, playlist_autonumber and autonumber convert all occurrences
        # of %(field)s to %(field)0Nd for backward compatibility
        field_size_compat_map = {
            'playlist_index': number_of_digits(info_dict.get('__last_playlist_index') or 0),
            'playlist_autonumber': number_of_digits(info_dict.get('n_entries') or 0),
            'autonumber': self.params.get('autonumber_size') or 5,
        }

        TMPL_DICT = {}
        EXTERNAL_FORMAT_RE = re.compile(STR_FORMAT_RE_TMPL.format('[^)]*', f'[{STR_FORMAT_TYPES}ljhqBUDS]'))
        MATH_FUNCTIONS = {
            '+': float.__add__,
            '-': float.__sub__,
            '*': float.__mul__,
        }
        # Field is of the form key1.key2...
        # where keys (except first) can be string, int, slice or "{field, ...}"
        FIELD_INNER_RE = r'(?:\w+|%(num)s|%(num)s?(?::%(num)s?){1,2})' % {'num': r'(?:-?\d+)'}  # noqa: UP031
        FIELD_RE = r'\w*(?:\.(?:%(inner)s|{%(field)s(?:,%(field)s)*}))*' % {  # noqa: UP031
            'inner': FIELD_INNER_RE,
            'field': rf'\w*(?:\.{FIELD_INNER_RE})*',
        }
        MATH_FIELD_RE = rf'(?:{FIELD_RE}|-?{NUMBER_RE})'
        MATH_OPERATORS_RE = r'(?:{})'.format('|'.join(map(re.escape, MATH_FUNCTIONS.keys())))
        INTERNAL_FORMAT_RE = re.compile(rf'''(?xs)
            (?P<negate>-)?
            (?P<fields>{FIELD_RE})
            (?P<maths>(?:{MATH_OPERATORS_RE}{MATH_FIELD_RE})*)
            (?:>(?P<strf_format>.+?))?
            (?P<remaining>
                (?P<alternate>(?<!\\),[^|&)]+)?
                (?:&(?P<replacement>.*?))?
                (?:\|(?P<default>.*?))?
            )$''')

        def _from_user_input(field):
            if field == ':':
                return ...
            elif ':' in field:
                return slice(*map(int_or_none, field.split(':')))
            elif int_or_none(field) is not None:
                return int(field)
            return field

        def _traverse_infodict(fields):
            fields = [f for x in re.split(r'\.({.+?})\.?', fields)
                      for f in ([x] if x.startswith('{') else x.split('.'))]
            for i in (0, -1):
                if fields and not fields[i]:
                    fields.pop(i)

            for i, f in enumerate(fields):
                if not f.startswith('{'):
                    fields[i] = _from_user_input(f)
                    continue
                assert f.endswith('}'), f'No closing brace for {f} in {fields}'
                fields[i] = {k: list(map(_from_user_input, k.split('.'))) for k in f[1:-1].split(',')}

            return traverse_obj(info_dict, fields, traverse_string=True)

        def get_value(mdict):
            # Object traversal
            value = _traverse_infodict(mdict['fields'])
            # Negative
            if mdict['negate']:
                value = float_or_none(value)
                if value is not None:
                    value *= -1
            # Do maths
            offset_key = mdict['maths']
            if offset_key:
                value = float_or_none(value)
                operator = None
                while offset_key:
                    item = re.match(
                        MATH_FIELD_RE if operator else MATH_OPERATORS_RE,
                        offset_key).group(0)
                    offset_key = offset_key[len(item):]
                    if operator is None:
                        operator = MATH_FUNCTIONS[item]
                        continue
                    item, multiplier = (item[1:], -1) if item[0] == '-' else (item, 1)
                    offset = float_or_none(item)
                    if offset is None:
                        offset = float_or_none(_traverse_infodict(item))
                    try:
                        value = operator(value, multiplier * offset)
                    except (TypeError, ZeroDivisionError):
                        return None
                    operator = None
            # Datetime formatting
            if mdict['strf_format']:
                value = strftime_or_none(value, mdict['strf_format'].replace('\\,', ','))

            # XXX: Workaround for https://github.com/yt-dlp/yt-dlp/issues/4485
            if sanitize and value == '':
                value = None
            return value

        na = self.params.get('outtmpl_na_placeholder', 'NA')

        def filename_sanitizer(key, value, restricted=self.params.get('restrictfilenames')):
            return sanitize_filename(str(value), restricted=restricted, is_id=(
                bool(re.search(r'(^|[_.])id(\.|$)', key))
                if 'filename-sanitization' in self.params['compat_opts']
                else NO_DEFAULT))

        sanitizer = sanitize if callable(sanitize) else filename_sanitizer
        sanitize = bool(sanitize)

        def _dumpjson_default(obj):
            if isinstance(obj, (set, LazyList)):
                return list(obj)
            return repr(obj)

        class _ReplacementFormatter(string.Formatter):
            def get_field(self, field_name, args, kwargs):
                if field_name.isdigit():
                    return args[0], -1
                raise ValueError('Unsupported field')

        replacement_formatter = _ReplacementFormatter()

        def create_key(outer_mobj):
            if not outer_mobj.group('has_key'):
                return outer_mobj.group(0)
            key = outer_mobj.group('key')
            mobj = re.match(INTERNAL_FORMAT_RE, key)
            value, replacement, default, last_field = None, None, na, ''
            while mobj:
                mobj = mobj.groupdict()
                default = mobj['default'] if mobj['default'] is not None else default
                value = get_value(mobj)
                last_field, replacement = mobj['fields'], mobj['replacement']
                if value is None and mobj['alternate']:
                    mobj = re.match(INTERNAL_FORMAT_RE, mobj['remaining'][1:])
                else:
                    break

            if None not in (value, replacement):
                try:
                    value = replacement_formatter.format(replacement, value)
                except ValueError:
                    value, default = None, na

            fmt = outer_mobj.group('format')
            if fmt == 's' and last_field in field_size_compat_map and isinstance(value, int):
                fmt = f'0{field_size_compat_map[last_field]:d}d'

            flags = outer_mobj.group('conversion') or ''
            str_fmt = f'{fmt[:-1]}s'
            if value is None:
                value, fmt = default, 's'
            elif fmt[-1] == 'l':  # list
                delim = '\n' if '#' in flags else ', '
                value, fmt = delim.join(map(str, variadic(value, allowed_types=(str, bytes)))), str_fmt
            elif fmt[-1] == 'j':  # json
                value, fmt = json.dumps(
                    value, default=_dumpjson_default,
                    indent=4 if '#' in flags else None, ensure_ascii='+' not in flags), str_fmt
            elif fmt[-1] == 'h':  # html
                value, fmt = escapeHTML(str(value)), str_fmt
            elif fmt[-1] == 'q':  # quoted
                value = map(str, variadic(value) if '#' in flags else [value])
                value, fmt = shell_quote(value, shell=True), str_fmt
            elif fmt[-1] == 'B':  # bytes
                value = f'%{str_fmt}'.encode() % str(value).encode()
                value, fmt = value.decode('utf-8', 'ignore'), 's'
            elif fmt[-1] == 'U':  # unicode normalized
                value, fmt = unicodedata.normalize(
                    # "+" = compatibility equivalence, "#" = NFD
                    'NF{}{}'.format('K' if '+' in flags else '', 'D' if '#' in flags else 'C'),
                    value), str_fmt
            elif fmt[-1] == 'D':  # decimal suffix
                num_fmt, fmt = fmt[:-1].replace('#', ''), 's'
                value = format_decimal_suffix(value, f'%{num_fmt}f%s' if num_fmt else '%d%s',
                                              factor=1024 if '#' in flags else 1000)
            elif fmt[-1] == 'S':  # filename sanitization
                value, fmt = filename_sanitizer(last_field, value, restricted='#' in flags), str_fmt
            elif fmt[-1] == 'c':
                if value:
                    value = str(value)[0]
                else:
                    fmt = str_fmt
            elif fmt[-1] not in 'rsa':  # numeric
                value = float_or_none(value)
                if value is None:
                    value, fmt = default, 's'

            if sanitize:
                # If value is an object, sanitize might convert it to a string
                # So we convert it to repr first
                if fmt[-1] == 'r':
                    value, fmt = repr(value), str_fmt
                elif fmt[-1] == 'a':
                    value, fmt = ascii(value), str_fmt
                if fmt[-1] in 'csra':
                    value = sanitizer(last_field, value)

            key = '{}\0{}'.format(key.replace('%', '%\0'), outer_mobj.group('format'))
            TMPL_DICT[key] = value
            return '{prefix}%({key}){fmt}'.format(key=key, fmt=fmt, prefix=outer_mobj.group('prefix'))

        return EXTERNAL_FORMAT_RE.sub(create_key, outtmpl), TMPL_DICT

    def evaluate_outtmpl(self, outtmpl, info_dict, *args, **kwargs):
        outtmpl, info_dict = self.prepare_outtmpl(outtmpl, info_dict, *args, **kwargs)
        return self.escape_outtmpl(outtmpl) % info_dict

    @_catch_unsafe_extension_error
    def _prepare_filename(self, info_dict, *, outtmpl=None, tmpl_type=None):
        assert None in (outtmpl, tmpl_type), 'outtmpl and tmpl_type are mutually exclusive'
        if outtmpl is None:
            outtmpl = self.params['outtmpl'].get(tmpl_type or 'default', self.params['outtmpl']['default'])
        try:
            outtmpl = self._outtmpl_expandpath(outtmpl)
            filename = self.evaluate_outtmpl(outtmpl, info_dict, True)
            if not filename:
                return None

            if tmpl_type in ('', 'temp'):
                final_ext, ext = self.params.get('final_ext'), info_dict.get('ext')
                if final_ext and ext and final_ext != ext and filename.endswith(f'.{final_ext}'):
                    filename = replace_extension(filename, ext, final_ext)
            elif tmpl_type:
                force_ext = OUTTMPL_TYPES[tmpl_type]
                if force_ext:
                    filename = replace_extension(filename, force_ext, info_dict.get('ext'))

            # https://github.com/blackjack4494/youtube-dlc/issues/85
            trim_file_name = self.params.get('trim_file_name', False)
            if trim_file_name:
                no_ext, *ext = filename.rsplit('.', 2)
                filename = join_nonempty(no_ext[:trim_file_name], *ext, delim='.')

            return filename
        except ValueError as err:
            self.report_error('Error in output template: ' + str(err) + ' (encoding: ' + repr(preferredencoding()) + ')')
            return None

    def prepare_filename(self, info_dict, dir_type='', *, outtmpl=None, warn=False):
        """Generate the output filename"""
        if outtmpl:
            assert not dir_type, 'outtmpl and dir_type are mutually exclusive'
            dir_type = None
        filename = self._prepare_filename(info_dict, tmpl_type=dir_type, outtmpl=outtmpl)
        if not filename and dir_type not in ('', 'temp'):
            return ''

        if warn:
            if not self.params.get('paths'):
                pass
            elif filename == '-':
                self.report_warning('--paths is ignored when an outputting to stdout', only_once=True)
            elif os.path.isabs(filename):
                self.report_warning('--paths is ignored since an absolute path is given in output template', only_once=True)
        if filename == '-' or not filename:
            return filename

        return self.get_output_path(dir_type, filename)

    def _match_entry(self, info_dict, incomplete=False, silent=False):
        """Returns None if the file should be downloaded"""
        _type = 'video' if 'playlist-match-filter' in self.params['compat_opts'] else info_dict.get('_type', 'video')
        assert incomplete or _type == 'video', 'Only video result can be considered complete'

        video_title = info_dict.get('title', info_dict.get('id', 'entry'))

        def check_filter():
            if _type in ('playlist', 'multi_video'):
                return
            elif _type in ('url', 'url_transparent') and not try_call(
                    lambda: self.get_info_extractor(info_dict['ie_key']).is_single_video(info_dict['url'])):
                return

            if 'title' in info_dict:
                # This can happen when we're just evaluating the playlist
                title = info_dict['title']
                matchtitle = self.params.get('matchtitle', False)
                if matchtitle:
                    if not re.search(matchtitle, title, re.IGNORECASE):
                        return '"' + title + '" title did not match pattern "' + matchtitle + '"'
                rejecttitle = self.params.get('rejecttitle', False)
                if rejecttitle:
                    if re.search(rejecttitle, title, re.IGNORECASE):
                        return '"' + title + '" title matched reject pattern "' + rejecttitle + '"'

            date = info_dict.get('upload_date')
            if date is not None:
                date_range = self.params.get('daterange', DateRange())
                if date not in date_range:
                    return f'{date_from_str(date).isoformat()} upload date is not in range {date_range}'
            view_count = info_dict.get('view_count')
            if view_count is not None:
                min_views = self.params.get('min_views')
                if min_views is not None and view_count < min_views:
                    return 'Skipping %s, because it has not reached minimum view count (%d/%d)' % (video_title, view_count, min_views)
                max_views = self.params.get('max_views')
                if max_views is not None and view_count > max_views:
                    return 'Skipping %s, because it has exceeded the maximum view count (%d/%d)' % (video_title, view_count, max_views)
            if age_restricted(info_dict.get('age_limit'), self.params.get('age_limit')):
                return f'Skipping "{video_title}" because it is age restricted'

            match_filter = self.params.get('match_filter')
            if match_filter is None:
                return None

            cancelled = None
            try:
                try:
                    ret = match_filter(info_dict, incomplete=incomplete)
                except TypeError:
                    # For backward compatibility
                    ret = None if incomplete else match_filter(info_dict)
            except DownloadCancelled as err:
                if err.msg is not NO_DEFAULT:
                    raise
                ret, cancelled = err.msg, err

            if ret is NO_DEFAULT:
                while True:
                    filename = self._format_screen(self.prepare_filename(info_dict), self.Styles.FILENAME)
                    reply = input(self._format_screen(
                        f'Download "{filename}"? (Y/n): ', self.Styles.EMPHASIS)).lower().strip()
                    if reply in {'y', ''}:
                        return None
                    elif reply == 'n':
                        if cancelled:
                            raise type(cancelled)(f'Skipping {video_title}')
                        return f'Skipping {video_title}'
            return ret

        if self.in_download_archive(info_dict):
            reason = ''.join((
                format_field(info_dict, 'id', f'{self._format_screen("%s", self.Styles.ID)}: '),
                format_field(info_dict, 'title', f'{self._format_screen("%s", self.Styles.EMPHASIS)} '),
                'has already been recorded in the archive'))
            break_opt, break_err = 'break_on_existing', ExistingVideoReached
        else:
            try:
                reason = check_filter()
            except DownloadCancelled as e:
                reason, break_opt, break_err = e.msg, 'match_filter', type(e)
            else:
                break_opt, break_err = 'break_on_reject', RejectedVideoReached
        if reason is not None:
            if not silent:
                self.to_screen('[download] ' + reason)
            if self.params.get(break_opt, False):
                raise break_err()
        return reason

    @staticmethod
    def add_extra_info(info_dict, extra_info):
        """Set the keys from extra_info in info dict if they are missing"""
        for key, value in extra_info.items():
            info_dict.setdefault(key, value)

    def extract_info(self, url, download=True, ie_key=None, extra_info=None,
                     process=True, force_generic_extractor=False):
        """
        Extract and return the information dictionary of the URL

        Arguments:
        @param url          URL to extract

        Keyword arguments:
        @param download     Whether to download videos
        @param process      Whether to resolve all unresolved references (URLs, playlist items).
                            Must be True for download to work
        @param ie_key       Use only the extractor with this key

        @param extra_info   Dictionary containing the extra values to add to the info (For internal use only)
        @force_generic_extractor  Force using the generic extractor (Deprecated; use ie_key='Generic')
        """

        if extra_info is None:
            extra_info = {}

        if not ie_key and force_generic_extractor:
            ie_key = 'Generic'

        if ie_key:
            ies = {ie_key: self._ies[ie_key]} if ie_key in self._ies else {}
        else:
            ies = self._ies

        for key, ie in ies.items():
            if not ie.suitable(url):
                continue

            if not ie.working():
                self.report_warning('The program functionality for this site has been marked as broken, '
                                    'and will probably not work.')

            temp_id = ie.get_temp_id(url)
            if temp_id is not None and self.in_download_archive({'id': temp_id, 'ie_key': key}):
                self.to_screen(f'[download] {self._format_screen(temp_id, self.Styles.ID)}: '
                               'has already been recorded in the archive')
                if self.params.get('break_on_existing', False):
                    raise ExistingVideoReached
                break
            return self.__extract_info(url, self.get_info_extractor(key), download, extra_info, process)
        else:
            extractors_restricted = self.params.get('allowed_extractors') not in (None, ['default'])
            self.report_error(f'No suitable extractor{format_field(ie_key, None, " (%s)")} found for URL {url}',
                              tb=False if extractors_restricted else None)

    def _handle_extraction_exceptions(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            while True:
                try:
                    return func(self, *args, **kwargs)
                except (CookieLoadError, DownloadCancelled, LazyList.IndexError, PagedList.IndexError):
                    raise
                except ReExtractInfo as e:
                    if e.expected:
                        self.to_screen(f'{e}; Re-extracting data')
                    else:
                        self.to_stderr('\r')
                        self.report_warning(f'{e}; Re-extracting data')
                    continue
                except GeoRestrictedError as e:
                    msg = e.msg
                    if e.countries:
                        msg += '\nThis video is available in {}.'.format(', '.join(
                            map(ISO3166Utils.short2full, e.countries)))
                    msg += '\nYou might want to use a VPN or a proxy server (with --proxy) to workaround.'
                    self.report_error(msg)
                except ExtractorError as e:  # An error we somewhat expected
                    self.report_error(str(e), e.format_traceback())
                except Exception as e:
                    if self.params.get('ignoreerrors'):
                        self.report_error(str(e), tb=encode_compat_str(traceback.format_exc()))
                    else:
                        raise
                break
        return wrapper

    def _wait_for_video(self, ie_result={}):
        if (not self.params.get('wait_for_video')
                or ie_result.get('_type', 'video') != 'video'
                or ie_result.get('formats') or ie_result.get('url')):
            return

        format_dur = lambda dur: '%02d:%02d:%02d' % timetuple_from_msec(dur * 1000)[:-1]
        last_msg = ''

        def progress(msg):
            nonlocal last_msg
            full_msg = f'{msg}\n'
            if not self.params.get('noprogress'):
                full_msg = msg + ' ' * (len(last_msg) - len(msg)) + '\r'
            elif last_msg:
                return
            self.to_screen(full_msg, skip_eol=True)
            last_msg = msg

        min_wait, max_wait = self.params.get('wait_for_video')
        diff = try_get(ie_result, lambda x: x['release_timestamp'] - time.time())
        if diff is None and ie_result.get('live_status') == 'is_upcoming':
            diff = round(random.uniform(min_wait, max_wait) if (max_wait and min_wait) else (max_wait or min_wait), 0)
            self.report_warning('Release time of video is not known')
        elif ie_result and (diff or 0) <= 0:
            self.report_warning('Video should already be available according to extracted info')
        diff = min(max(diff or 0, min_wait or 0), max_wait or float('inf'))
        self.to_screen(f'[wait] Waiting for {format_dur(diff)} - Press Ctrl+C to try now')

        wait_till = time.time() + diff
        try:
            while True:
                diff = wait_till - time.time()
                if diff <= 0:
                    progress('')
                    raise ReExtractInfo('[wait] Wait period ended', expected=True)
                progress(f'[wait] Remaining time until next attempt: {self._format_screen(format_dur(diff), self.Styles.EMPHASIS)}')
                time.sleep(1)
        except KeyboardInterrupt:
            progress('')
            raise ReExtractInfo('[wait] Interrupted by user', expected=True)
        except BaseException as e:
            if not isinstance(e, ReExtractInfo):
                self.to_screen('')
            raise

    def _load_cookies(self, data, *, autoscope=True):
        """Loads cookies from a `Cookie` header

        This tries to work around the security vulnerability of passing cookies to every domain.
        See: https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-v8mc-9377-rwjj

        @param data         The Cookie header as string to load the cookies from
        @param autoscope    If `False`, scope cookies using Set-Cookie syntax and error for cookie without domains
                            If `True`, save cookies for later to be stored in the jar with a limited scope
                            If a URL, save cookies in the jar with the domain of the URL
        """
        for cookie in LenientSimpleCookie(data).values():
            if autoscope and any(cookie.values()):
                raise ValueError('Invalid syntax in Cookie Header')

            domain = cookie.get('domain') or ''
            expiry = cookie.get('expires')
            if expiry == '':  # 0 is valid
                expiry = None
            prepared_cookie = http.cookiejar.Cookie(
                cookie.get('version') or 0, cookie.key, cookie.value, None, False,
                domain, True, True, cookie.get('path') or '', bool(cookie.get('path')),
                cookie.get('secure') or False, expiry, False, None, None, {})

            if domain:
                self.cookiejar.set_cookie(prepared_cookie)
            elif autoscope is True:
                self.deprecated_feature(
                    'Passing cookies as a header is a potential security risk; '
                    'they will be scoped to the domain of the downloaded urls. '
                    'Please consider loading cookies from a file or browser instead.')
                self.__header_cookies.append(prepared_cookie)
            elif autoscope:
                self.report_warning(
                    'The extractor result contains an unscoped cookie as an HTTP header. '
                    f'If you are using yt-dlp with an input URL{bug_reports_message(before=",")}',
                    only_once=True)
                self._apply_header_cookies(autoscope, [prepared_cookie])
            else:
                self.report_error('Unscoped cookies are not allowed; please specify some sort of scoping',
                                  tb=False, is_error=False)

    def _apply_header_cookies(self, url, cookies=None):
        """Applies stray header cookies to the provided url

        This loads header cookies and scopes them to the domain provided in `url`.
        While this is not ideal, it helps reduce the risk of them being sent
        to an unintended destination while mostly maintaining compatibility.
        """
        parsed = urllib.parse.urlparse(url)
        if not parsed.hostname:
            return

        for cookie in map(copy.copy, cookies or self.__header_cookies):
            cookie.domain = f'.{parsed.hostname}'
            self.cookiejar.set_cookie(cookie)

    @_handle_extraction_exceptions
    def __extract_info(self, url, ie, download, extra_info, process):
        self._apply_header_cookies(url)

        try:
            ie_result = ie.extract(url)
        except UserNotLive as e:
            if process:
                if self.params.get('wait_for_video'):
                    self.report_warning(e)
                self._wait_for_video()
            raise
        if ie_result is None:  # Finished already (backwards compatibility; listformats and friends should be moved here)
            self.report_warning(f'Extractor {ie.IE_NAME} returned nothing{bug_reports_message()}')
            return
        if isinstance(ie_result, list):
            # Backwards compatibility: old IE result format
            ie_result = {
                '_type': 'compat_list',
                'entries': ie_result,
            }
        if extra_info.get('original_url'):
            ie_result.setdefault('original_url', extra_info['original_url'])
        self.add_default_extra_info(ie_result, ie, url)
        if process:
            self._wait_for_video(ie_result)
            return self.process_ie_result(ie_result, download, extra_info)
        else:
            return ie_result

    def add_default_extra_info(self, ie_result, ie, url):
        if url is not None:
            self.add_extra_info(ie_result, {
                'webpage_url': url,
                'original_url': url,
            })
        webpage_url = ie_result.get('webpage_url')
        if webpage_url:
            self.add_extra_info(ie_result, {
                'webpage_url_basename': url_basename(webpage_url),
                'webpage_url_domain': get_domain(webpage_url),
            })
        if ie is not None:
            self.add_extra_info(ie_result, {
                'extractor': ie.IE_NAME,
                'extractor_key': ie.ie_key(),
            })

    def process_ie_result(self, ie_result, download=True, extra_info=None):
        """
        Take the result of the ie(may be modified) and resolve all unresolved
        references (URLs, playlist items).

        It will also download the videos if 'download'.
        Returns the resolved ie_result.
        """
        if extra_info is None:
            extra_info = {}
        result_type = ie_result.get('_type', 'video')

        if result_type in ('url', 'url_transparent'):
            ie_result['url'] = sanitize_url(
                ie_result['url'], scheme='http' if self.params.get('prefer_insecure') else 'https')
            if ie_result.get('original_url') and not extra_info.get('original_url'):
                extra_info = {'original_url': ie_result['original_url'], **extra_info}

            extract_flat = self.params.get('extract_flat', False)
            if ((extract_flat == 'in_playlist' and 'playlist' in extra_info)
                    or extract_flat is True):
                info_copy = ie_result.copy()
                ie = try_get(ie_result.get('ie_key'), self.get_info_extractor)
                if ie and not ie_result.get('id'):
                    info_copy['id'] = ie.get_temp_id(ie_result['url'])
                self.add_default_extra_info(info_copy, ie, ie_result['url'])
                self.add_extra_info(info_copy, extra_info)
                info_copy, _ = self.pre_process(info_copy)
                self._fill_common_fields(info_copy, False)
                self.__forced_printings(info_copy)
                self._raise_pending_errors(info_copy)
                if self.params.get('force_write_download_archive', False):
                    self.record_download_archive(info_copy)
                return ie_result

        if result_type == 'video':
            self.add_extra_info(ie_result, extra_info)
            ie_result = self.process_video_result(ie_result, download=download)
            self._raise_pending_errors(ie_result)
            additional_urls = (ie_result or {}).get('additional_urls')
            if additional_urls:
                # TODO: Improve MetadataParserPP to allow setting a list
                if isinstance(additional_urls, str):
                    additional_urls = [additional_urls]
                self.to_screen(
                    '[info] {}: {} additional URL(s) requested'.format(ie_result['id'], len(additional_urls)))
                self.write_debug('Additional URLs: "{}"'.format('", "'.join(additional_urls)))
                ie_result['additional_entries'] = [
                    self.extract_info(
                        url, download, extra_info=extra_info,
                        force_generic_extractor=self.params.get('force_generic_extractor'))
                    for url in additional_urls
                ]
            return ie_result
        elif result_type == 'url':
            # We have to add extra_info to the results because it may be
            # contained in a playlist
            return self.extract_info(
                ie_result['url'], download,
                ie_key=ie_result.get('ie_key'),
                extra_info=extra_info)
        elif result_type == 'url_transparent':
            # Use the information from the embedding page
            info = self.extract_info(
                ie_result['url'], ie_key=ie_result.get('ie_key'),
                extra_info=extra_info, download=False, process=False)

            # extract_info may return None when ignoreerrors is enabled and
            # extraction failed with an error, don't crash and return early
            # in this case
            if not info:
                return info

            exempted_fields = {'_type', 'url', 'ie_key'}
            if not ie_result.get('section_end') and ie_result.get('section_start') is None:
                # For video clips, the id etc of the clip extractor should be used
                exempted_fields |= {'id', 'extractor', 'extractor_key'}

            new_result = info.copy()
            new_result.update(filter_dict(ie_result, lambda k, v: v is not None and k not in exempted_fields))

            # Extracted info may not be a video result (i.e.
            # info.get('_type', 'video') != video) but rather an url or
            # url_transparent. In such cases outer metadata (from ie_result)
            # should be propagated to inner one (info). For this to happen
            # _type of info should be overridden with url_transparent. This
            # fixes issue from https://github.com/ytdl-org/youtube-dl/pull/11163.
            if new_result.get('_type') == 'url':
                new_result['_type'] = 'url_transparent'

            return self.process_ie_result(
                new_result, download=download, extra_info=extra_info)
        elif result_type in ('playlist', 'multi_video'):
            # Protect from infinite recursion due to recursively nested playlists
            # (see https://github.com/ytdl-org/youtube-dl/issues/27833)
            webpage_url = ie_result.get('webpage_url')  # Playlists maynot have webpage_url
            if webpage_url and webpage_url in self._playlist_urls:
                self.to_screen(
                    '[download] Skipping already downloaded playlist: {}'.format(
                        ie_result.get('title')) or ie_result.get('id'))
                return

            self._playlist_level += 1
            self._playlist_urls.add(webpage_url)
            self._fill_common_fields(ie_result, False)
            self._sanitize_thumbnails(ie_result)
            try:
                return self.__process_playlist(ie_result, download)
            finally:
                self._playlist_level -= 1
                if not self._playlist_level:
                    self._playlist_urls.clear()
        elif result_type == 'compat_list':
            self.report_warning(
                'Extractor {} returned a compat_list result. '
                'It needs to be updated.'.format(ie_result.get('extractor')))

            def _fixup(r):
                self.add_extra_info(r, {
                    'extractor': ie_result['extractor'],
                    'webpage_url': ie_result['webpage_url'],
                    'webpage_url_basename': url_basename(ie_result['webpage_url']),
                    'webpage_url_domain': get_domain(ie_result['webpage_url']),
                    'extractor_key': ie_result['extractor_key'],
                })
                return r
            ie_result['entries'] = [
                self.process_ie_result(_fixup(r), download, extra_info)
                for r in ie_result['entries']
            ]
            return ie_result
        else:
            raise Exception(f'Invalid result type: {result_type}')

    def _ensure_dir_exists(self, path):
        return make_dir(path, self.report_error)

    @staticmethod
    def _playlist_infodict(ie_result, strict=False, **kwargs):
        info = {
            'playlist_count': ie_result.get('playlist_count'),
            'playlist': ie_result.get('title') or ie_result.get('id'),
            'playlist_id': ie_result.get('id'),
            'playlist_title': ie_result.get('title'),
            'playlist_uploader': ie_result.get('uploader'),
            'playlist_uploader_id': ie_result.get('uploader_id'),
            'playlist_channel': ie_result.get('channel'),
            'playlist_channel_id': ie_result.get('channel_id'),
            **kwargs,
        }
        if strict:
            return info
        if ie_result.get('webpage_url'):
            info.update({
                'webpage_url': ie_result['webpage_url'],
                'webpage_url_basename': url_basename(ie_result['webpage_url']),
                'webpage_url_domain': get_domain(ie_result['webpage_url']),
            })
        return {
            **info,
            'playlist_index': 0,
            '__last_playlist_index': max(ie_result.get('requested_entries') or (0, 0)),
            'extractor': ie_result['extractor'],
            'extractor_key': ie_result['extractor_key'],
        }

    def __process_playlist(self, ie_result, download):
        """Process each entry in the playlist"""
        assert ie_result['_type'] in ('playlist', 'multi_video')

        common_info = self._playlist_infodict(ie_result, strict=True)
        title = common_info.get('playlist') or '<Untitled>'
        if self._match_entry(common_info, incomplete=True) is not None:
            return
        self.to_screen(f'[download] Downloading {ie_result["_type"]}: {title}')

        all_entries = PlaylistEntries(self, ie_result)
        entries = orderedSet(all_entries.get_requested_items(), lazy=True)

        lazy = self.params.get('lazy_playlist')
        if lazy:
            resolved_entries, n_entries = [], 'N/A'
            ie_result['requested_entries'], ie_result['entries'] = None, None
        else:
            entries = resolved_entries = list(entries)
            n_entries = len(resolved_entries)
            ie_result['requested_entries'], ie_result['entries'] = tuple(zip(*resolved_entries)) or ([], [])
        if not ie_result.get('playlist_count'):
            # Better to do this after potentially exhausting entries
            ie_result['playlist_count'] = all_entries.get_full_count()

        extra = self._playlist_infodict(ie_result, n_entries=int_or_none(n_entries))
        ie_copy = collections.ChainMap(ie_result, extra)

        _infojson_written = False
        write_playlist_files = self.params.get('allow_playlist_files', True)
        if write_playlist_files and self.params.get('list_thumbnails'):
            self.list_thumbnails(ie_result)
        if write_playlist_files and not self.params.get('simulate'):
            _infojson_written = self._write_info_json(
                'playlist', ie_result, self.prepare_filename(ie_copy, 'pl_infojson'))
            if _infojson_written is None:
                return
            if self._write_description('playlist', ie_result,
                                       self.prepare_filename(ie_copy, 'pl_description')) is None:
                return
            # TODO: This should be passed to ThumbnailsConvertor if necessary
            self._write_thumbnails('playlist', ie_result, self.prepare_filename(ie_copy, 'pl_thumbnail'))

        if lazy:
            if self.params.get('playlistreverse') or self.params.get('playlistrandom'):
                self.report_warning('playlistreverse and playlistrandom are not supported with lazy_playlist', only_once=True)
        elif self.params.get('playlistreverse'):
            entries.reverse()
        elif self.params.get('playlistrandom'):
            random.shuffle(entries)

        self.to_screen(f'[{ie_result["extractor"]}] Playlist {title}: Downloading {n_entries} items'
                       f'{format_field(ie_result, "playlist_count", " of %s")}')

        keep_resolved_entries = self.params.get('extract_flat') != 'discard'
        if self.params.get('extract_flat') == 'discard_in_playlist':
            keep_resolved_entries = ie_result['_type'] != 'playlist'
        if keep_resolved_entries:
            self.write_debug('The information of all playlist entries will be held in memory')

        failures = 0
        max_failures = self.params.get('skip_playlist_after_errors') or float('inf')
        for i, (playlist_index, entry) in enumerate(entries):
            if lazy:
                resolved_entries.append((playlist_index, entry))
            if not entry:
                continue

            entry['__x_forwarded_for_ip'] = ie_result.get('__x_forwarded_for_ip')
            if not lazy and 'playlist-index' in self.params['compat_opts']:
                playlist_index = ie_result['requested_entries'][i]

            entry_copy = collections.ChainMap(entry, {
                **common_info,
                'n_entries': int_or_none(n_entries),
                'playlist_index': playlist_index,
                'playlist_autonumber': i + 1,
            })

            if self._match_entry(entry_copy, incomplete=True) is not None:
                # For compatabilty with youtube-dl. See https://github.com/yt-dlp/yt-dlp/issues/4369
                resolved_entries[i] = (playlist_index, NO_DEFAULT)
                continue

            self.to_screen(
                f'[download] Downloading item {self._format_screen(i + 1, self.Styles.ID)} '
                f'of {self._format_screen(n_entries, self.Styles.EMPHASIS)}')

            entry_result = self.__process_iterable_entry(entry, download, collections.ChainMap({
                'playlist_index': playlist_index,
                'playlist_autonumber': i + 1,
            }, extra))
            if not entry_result:
                failures += 1
            if failures >= max_failures:
                self.report_error(
                    f'Skipping the remaining entries in playlist "{title}" since {failures} items failed extraction')
                break
            if keep_resolved_entries:
                resolved_entries[i] = (playlist_index, entry_result)

        # Update with processed data
        ie_result['entries'] = [e for _, e in resolved_entries if e is not NO_DEFAULT]
        ie_result['requested_entries'] = [i for i, e in resolved_entries if e is not NO_DEFAULT]
        if ie_result['requested_entries'] == try_call(lambda: list(range(1, ie_result['playlist_count'] + 1))):
            # Do not set for full playlist
            ie_result.pop('requested_entries')

        # Write the updated info to json
        if _infojson_written is True and self._write_info_json(
                'updated playlist', ie_result,
                self.prepare_filename(ie_copy, 'pl_infojson'), overwrite=True) is None:
            return

        ie_result = self.run_all_pps('playlist', ie_result)
        self.to_screen(f'[download] Finished downloading playlist: {title}')
        return ie_result

    @_handle_extraction_exceptions
    def __process_iterable_entry(self, entry, download, extra_info):
        return self.process_ie_result(
            entry, download=download, extra_info=extra_info)

    def _build_format_filter(self, filter_spec):
        " Returns a function to filter the formats according to the filter_spec "

        OPERATORS = {
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            '=': operator.eq,
            '!=': operator.ne,
        }
        operator_rex = re.compile(r'''(?x)\s*
            (?P<key>[\w.-]+)\s*
            (?P<op>{})(?P<none_inclusive>\s*\?)?\s*
            (?P<value>[0-9.]+(?:[kKmMgGtTpPeEzZyY]i?[Bb]?)?)\s*
            '''.format('|'.join(map(re.escape, OPERATORS.keys()))))
        m = operator_rex.fullmatch(filter_spec)
        if m:
            try:
                comparison_value = int(m.group('value'))
            except ValueError:
                comparison_value = parse_filesize(m.group('value'))
                if comparison_value is None:
                    comparison_value = parse_filesize(m.group('value') + 'B')
                if comparison_value is None:
                    raise ValueError(
                        'Invalid value {!r} in format specification {!r}'.format(
                            m.group('value'), filter_spec))
            op = OPERATORS[m.group('op')]

        if not m:
            STR_OPERATORS = {
                '=': operator.eq,
                '^=': lambda attr, value: attr.startswith(value),
                '$=': lambda attr, value: attr.endswith(value),
                '*=': lambda attr, value: value in attr,
                '~=': lambda attr, value: value.search(attr) is not None,
            }
            str_operator_rex = re.compile(r'''(?x)\s*
                (?P<key>[a-zA-Z0-9._-]+)\s*
                (?P<negation>!\s*)?(?P<op>{})\s*(?P<none_inclusive>\?\s*)?
                (?P<quote>["'])?
                (?P<value>(?(quote)(?:(?!(?P=quote))[^\\]|\\.)+|[\w.-]+))
                (?(quote)(?P=quote))\s*
                '''.format('|'.join(map(re.escape, STR_OPERATORS.keys()))))
            m = str_operator_rex.fullmatch(filter_spec)
            if m:
                if m.group('op') == '~=':
                    comparison_value = re.compile(m.group('value'))
                else:
                    comparison_value = re.sub(r'''\\([\\"'])''', r'\1', m.group('value'))
                str_op = STR_OPERATORS[m.group('op')]
                if m.group('negation'):
                    op = lambda attr, value: not str_op(attr, value)
                else:
                    op = str_op

        if not m:
            raise SyntaxError(f'Invalid filter specification {filter_spec!r}')

        def _filter(f):
            actual_value = f.get(m.group('key'))
            if actual_value is None:
                return m.group('none_inclusive')
            return op(actual_value, comparison_value)
        return _filter

    def _check_formats(self, formats):
        for f in formats:
            working = f.get('__working')
            if working is not None:
                if working:
                    yield f
                continue
            self.to_screen('[info] Testing format {}'.format(f['format_id']))
            path = self.get_output_path('temp')
            if not self._ensure_dir_exists(f'{path}/'):
                continue
            temp_file = tempfile.NamedTemporaryFile(suffix='.tmp', delete=False, dir=path or None)
            temp_file.close()
            try:
                success, _ = self.dl(temp_file.name, f, test=True)
            except (DownloadError, OSError, ValueError, *network_exceptions):
                success = False
            finally:
                if os.path.exists(temp_file.name):
                    try:
                        os.remove(temp_file.name)
                    except OSError:
                        self.report_warning(f'Unable to delete temporary file "{temp_file.name}"')
            f['__working'] = success
            if success:
                yield f
            else:
                self.to_screen('[info] Unable to download format {}. Skipping...'.format(f['format_id']))

    def _select_formats(self, formats, selector):
        return list(selector({
            'formats': formats,
            'has_merged_format': any('none' not in (f.get('acodec'), f.get('vcodec')) for f in formats),
            'incomplete_formats': (all(f.get('vcodec') == 'none' for f in formats)  # No formats with video
                                   or all(f.get('acodec') == 'none' for f in formats)),  # OR, No formats with audio
        }))

    def _default_format_spec(self, info_dict):
        prefer_best = (
            self.params['outtmpl']['default'] == '-'
            or info_dict.get('is_live') and not self.params.get('live_from_start'))

        def can_merge():
            merger = FFmpegMergerPP(self)
            return merger.available and merger.can_merge()

        if not prefer_best and not can_merge():
            prefer_best = True
            formats = self._get_formats(info_dict)
            evaluate_formats = lambda spec: self._select_formats(formats, self.build_format_selector(spec))
            if evaluate_formats('b/bv+ba') != evaluate_formats('bv*+ba/b'):
                self.report_warning('ffmpeg not found. The downloaded format may not be the best available. '
                                    'Installing ffmpeg is strongly recommended: https://github.com/yt-dlp/yt-dlp#dependencies')

        compat = (self.params.get('allow_multiple_audio_streams')
                  or 'format-spec' in self.params['compat_opts'])

        return ('best/bestvideo+bestaudio' if prefer_best
                else 'bestvideo+bestaudio/best' if compat
                else 'bestvideo*+bestaudio/best')

    def build_format_selector(self, format_spec):
        def syntax_error(note, start):
            message = (
                'Invalid format specification: '
                '{}\n\t{}\n\t{}^'.format(note, format_spec, ' ' * start[1]))
            return SyntaxError(message)

        PICKFIRST = 'PICKFIRST'
        MERGE = 'MERGE'
        SINGLE = 'SINGLE'
        GROUP = 'GROUP'
        FormatSelector = collections.namedtuple('FormatSelector', ['type', 'selector', 'filters'])

        allow_multiple_streams = {'audio': self.params.get('allow_multiple_audio_streams', False),
                                  'video': self.params.get('allow_multiple_video_streams', False)}

        def _parse_filter(tokens):
            filter_parts = []
            for type_, string_, _start, _, _ in tokens:
                if type_ == tokenize.OP and string_ == ']':
                    return ''.join(filter_parts)
                else:
                    filter_parts.append(string_)

        def _remove_unused_ops(tokens):
            # Remove operators that we don't use and join them with the surrounding strings.
            # E.g. 'mp4' '-' 'baseline' '-' '16x9' is converted to 'mp4-baseline-16x9'
            ALLOWED_OPS = ('/', '+', ',', '(', ')')
            last_string, last_start, last_end, last_line = None, None, None, None
            for type_, string_, start, end, line in tokens:
                if type_ == tokenize.OP and string_ == '[':
                    if last_string:
                        yield tokenize.NAME, last_string, last_start, last_end, last_line
                        last_string = None
                    yield type_, string_, start, end, line
                    # everything inside brackets will be handled by _parse_filter
                    for type_, string_, start, end, line in tokens:
                        yield type_, string_, start, end, line
                        if type_ == tokenize.OP and string_ == ']':
                            break
                elif type_ == tokenize.OP and string_ in ALLOWED_OPS:
                    if last_string:
                        yield tokenize.NAME, last_string, last_start, last_end, last_line
                        last_string = None
                    yield type_, string_, start, end, line
                elif type_ in [tokenize.NAME, tokenize.NUMBER, tokenize.OP]:
                    if not last_string:
                        last_string = string_
                        last_start = start
                        last_end = end
                    else:
                        last_string += string_
            if last_string:
                yield tokenize.NAME, last_string, last_start, last_end, last_line

        def _parse_format_selection(tokens, inside_merge=False, inside_choice=False, inside_group=False):
            selectors = []
            current_selector = None
            for type_, string_, start, _, _ in tokens:
                # ENCODING is only defined in Python 3.x
                if type_ == getattr(tokenize, 'ENCODING', None):
                    continue
                elif type_ in [tokenize.NAME, tokenize.NUMBER]:
                    current_selector = FormatSelector(SINGLE, string_, [])
                elif type_ == tokenize.OP:
                    if string_ == ')':
                        if not inside_group:
                            # ')' will be handled by the parentheses group
                            tokens.restore_last_token()
                        break
                    elif inside_merge and string_ in ['/', ',']:
                        tokens.restore_last_token()
                        break
                    elif inside_choice and string_ == ',':
                        tokens.restore_last_token()
                        break
                    elif string_ == ',':
                        if not current_selector:
                            raise syntax_error('"," must follow a format selector', start)
                        selectors.append(current_selector)
                        current_selector = None
                    elif string_ == '/':
                        if not current_selector:
                            raise syntax_error('"/" must follow a format selector', start)
                        first_choice = current_selector
                        second_choice = _parse_format_selection(tokens, inside_choice=True)
                        current_selector = FormatSelector(PICKFIRST, (first_choice, second_choice), [])
                    elif string_ == '[':
                        if not current_selector:
                            current_selector = FormatSelector(SINGLE, 'best', [])
                        format_filter = _parse_filter(tokens)
                        current_selector.filters.append(format_filter)
                    elif string_ == '(':
                        if current_selector:
                            raise syntax_error('Unexpected "("', start)
                        group = _parse_format_selection(tokens, inside_group=True)
                        current_selector = FormatSelector(GROUP, group, [])
                    elif string_ == '+':
                        if not current_selector:
                            raise syntax_error('Unexpected "+"', start)
                        selector_1 = current_selector
                        selector_2 = _parse_format_selection(tokens, inside_merge=True)
                        if not selector_2:
                            raise syntax_error('Expected a selector', start)
                        current_selector = FormatSelector(MERGE, (selector_1, selector_2), [])
                    else:
                        raise syntax_error(f'Operator not recognized: "{string_}"', start)
                elif type_ == tokenize.ENDMARKER:
                    break
            if current_selector:
                selectors.append(current_selector)
            return selectors

        def _merge(formats_pair):
            format_1, format_2 = formats_pair

            formats_info = []
            formats_info.extend(format_1.get('requested_formats', (format_1,)))
            formats_info.extend(format_2.get('requested_formats', (format_2,)))

            if not allow_multiple_streams['video'] or not allow_multiple_streams['audio']:
                get_no_more = {'video': False, 'audio': False}
                for (i, fmt_info) in enumerate(formats_info):
                    if fmt_info.get('acodec') == fmt_info.get('vcodec') == 'none':
                        formats_info.pop(i)
                        continue
                    for aud_vid in ['audio', 'video']:
                        if not allow_multiple_streams[aud_vid] and fmt_info.get(aud_vid[0] + 'codec') != 'none':
                            if get_no_more[aud_vid]:
                                formats_info.pop(i)
                                break
                            get_no_more[aud_vid] = True

            if len(formats_info) == 1:
                return formats_info[0]

            video_fmts = [fmt_info for fmt_info in formats_info if fmt_info.get('vcodec') != 'none']
            audio_fmts = [fmt_info for fmt_info in formats_info if fmt_info.get('acodec') != 'none']

            the_only_video = video_fmts[0] if len(video_fmts) == 1 else None
            the_only_audio = audio_fmts[0] if len(audio_fmts) == 1 else None

            output_ext = get_compatible_ext(
                vcodecs=[f.get('vcodec') for f in video_fmts],
                acodecs=[f.get('acodec') for f in audio_fmts],
                vexts=[f['ext'] for f in video_fmts],
                aexts=[f['ext'] for f in audio_fmts],
                preferences=(try_call(lambda: self.params['merge_output_format'].split('/'))
                             or self.params.get('prefer_free_formats') and ('webm', 'mkv')))

            filtered = lambda *keys: filter(None, (traverse_obj(fmt, *keys) for fmt in formats_info))

            new_dict = {
                'requested_formats': formats_info,
                'format': '+'.join(filtered('format')),
                'format_id': '+'.join(filtered('format_id')),
                'ext': output_ext,
                'protocol': '+'.join(map(determine_protocol, formats_info)),
                'language': '+'.join(orderedSet(filtered('language'))) or None,
                'format_note': '+'.join(orderedSet(filtered('format_note'))) or None,
                'filesize_approx': sum(filtered('filesize', 'filesize_approx')) or None,
                'tbr': sum(filtered('tbr', 'vbr', 'abr')),
            }

            if the_only_video:
                new_dict.update({
                    'width': the_only_video.get('width'),
                    'height': the_only_video.get('height'),
                    'resolution': the_only_video.get('resolution') or self.format_resolution(the_only_video),
                    'fps': the_only_video.get('fps'),
                    'dynamic_range': the_only_video.get('dynamic_range'),
                    'vcodec': the_only_video.get('vcodec'),
                    'vbr': the_only_video.get('vbr'),
                    'stretched_ratio': the_only_video.get('stretched_ratio'),
                    'aspect_ratio': the_only_video.get('aspect_ratio'),
                })

            if the_only_audio:
                new_dict.update({
                    'acodec': the_only_audio.get('acodec'),
                    'abr': the_only_audio.get('abr'),
                    'asr': the_only_audio.get('asr'),
                    'audio_channels': the_only_audio.get('audio_channels'),
                })

            return new_dict

        def _check_formats(formats):
            if self.params.get('check_formats') == 'selected':
                yield from self._check_formats(formats)
                return
            elif (self.params.get('check_formats') is not None
                    or self.params.get('allow_unplayable_formats')):
                yield from formats
                return

            for f in formats:
                if f.get('has_drm') or f.get('__needs_testing'):
                    yield from self._check_formats([f])
                else:
                    yield f

        def _build_selector_function(selector):
            if isinstance(selector, list):  # ,
                fs = [_build_selector_function(s) for s in selector]

                def selector_function(ctx):
                    for f in fs:
                        yield from f(ctx)
                return selector_function

            elif selector.type == GROUP:  # ()
                selector_function = _build_selector_function(selector.selector)

            elif selector.type == PICKFIRST:  # /
                fs = [_build_selector_function(s) for s in selector.selector]

                def selector_function(ctx):
                    for f in fs:
                        picked_formats = list(f(ctx))
                        if picked_formats:
                            return picked_formats
                    return []

            elif selector.type == MERGE:  # +
                selector_1, selector_2 = map(_build_selector_function, selector.selector)

                def selector_function(ctx):
                    for pair in itertools.product(selector_1(ctx), selector_2(ctx)):
                        yield _merge(pair)

            elif selector.type == SINGLE:  # atom
                format_spec = selector.selector or 'best'

                # TODO: Add allvideo, allaudio etc by generalizing the code with best/worst selector
                if format_spec == 'all':
                    def selector_function(ctx):
                        yield from _check_formats(ctx['formats'][::-1])
                elif format_spec == 'mergeall':
                    def selector_function(ctx):
                        formats = list(_check_formats(
                            f for f in ctx['formats'] if f.get('vcodec') != 'none' or f.get('acodec') != 'none'))
                        if not formats:
                            return
                        merged_format = formats[-1]
                        for f in formats[-2::-1]:
                            merged_format = _merge((merged_format, f))
                        yield merged_format

                else:
                    format_fallback, seperate_fallback, format_reverse, format_idx = False, None, True, 1
                    mobj = re.match(
                        r'(?P<bw>best|worst|b|w)(?P<type>video|audio|v|a)?(?P<mod>\*)?(?:\.(?P<n>[1-9]\d*))?$',
                        format_spec)
                    if mobj is not None:
                        format_idx = int_or_none(mobj.group('n'), default=1)
                        format_reverse = mobj.group('bw')[0] == 'b'
                        format_type = (mobj.group('type') or [None])[0]
                        not_format_type = {'v': 'a', 'a': 'v'}.get(format_type)
                        format_modified = mobj.group('mod') is not None

                        format_fallback = not format_type and not format_modified  # for b, w
                        _filter_f = (
                            (lambda f: f.get(f'{format_type}codec') != 'none')
                            if format_type and format_modified  # bv*, ba*, wv*, wa*
                            else (lambda f: f.get(f'{not_format_type}codec') == 'none')
                            if format_type  # bv, ba, wv, wa
                            else (lambda f: f.get('vcodec') != 'none' and f.get('acodec') != 'none')
                            if not format_modified  # b, w
                            else lambda f: True)  # b*, w*
                        filter_f = lambda f: _filter_f(f) and (
                            f.get('vcodec') != 'none' or f.get('acodec') != 'none')
                    else:
                        if format_spec in self._format_selection_exts['audio']:
                            filter_f = lambda f: f.get('ext') == format_spec and f.get('acodec') != 'none'
                        elif format_spec in self._format_selection_exts['video']:
                            filter_f = lambda f: f.get('ext') == format_spec and f.get('acodec') != 'none' and f.get('vcodec') != 'none'
                            seperate_fallback = lambda f: f.get('ext') == format_spec and f.get('vcodec') != 'none'
                        elif format_spec in self._format_selection_exts['storyboards']:
                            filter_f = lambda f: f.get('ext') == format_spec and f.get('acodec') == 'none' and f.get('vcodec') == 'none'
                        else:
                            filter_f = lambda f: f.get('format_id') == format_spec  # id

                    def selector_function(ctx):
                        formats = list(ctx['formats'])
                        matches = list(filter(filter_f, formats)) if filter_f is not None else formats
                        if not matches:
                            if format_fallback and ctx['incomplete_formats']:
                                # for extractors with incomplete formats (audio only (soundcloud)
                                # or video only (imgur)) best/worst will fallback to
                                # best/worst {video,audio}-only format
                                matches = list(filter(lambda f: f.get('vcodec') != 'none' or f.get('acodec') != 'none', formats))
                            elif seperate_fallback and not ctx['has_merged_format']:
                                # for compatibility with youtube-dl when there is no pre-merged format
                                matches = list(filter(seperate_fallback, formats))
                        matches = LazyList(_check_formats(matches[::-1 if format_reverse else 1]))
                        try:
                            yield matches[format_idx - 1]
                        except LazyList.IndexError:
                            return

            filters = [self._build_format_filter(f) for f in selector.filters]

            def final_selector(ctx):
                ctx_copy = dict(ctx)
                for _filter in filters:
                    ctx_copy['formats'] = list(filter(_filter, ctx_copy['formats']))
                return selector_function(ctx_copy)
            return final_selector

        # HACK: Python 3.12 changed the underlying parser, rendering '7_a' invalid
        #       Prefix numbers with random letters to avoid it being classified as a number
        #       See: https://github.com/yt-dlp/yt-dlp/pulls/8797
        # TODO: Implement parser not reliant on tokenize.tokenize
        prefix = ''.join(random.choices(string.ascii_letters, k=32))
        stream = io.BytesIO(re.sub(r'\d[_\d]*', rf'{prefix}\g<0>', format_spec).encode())
        try:
            tokens = list(_remove_unused_ops(
                token._replace(string=token.string.replace(prefix, ''))
                for token in tokenize.tokenize(stream.readline)))
        except tokenize.TokenError:
            raise syntax_error('Missing closing/opening brackets or parenthesis', (0, len(format_spec)))

        class TokenIterator:
            def __init__(self, tokens):
                self.tokens = tokens
                self.counter = 0

            def __iter__(self):
                return self

            def __next__(self):
                if self.counter >= len(self.tokens):
                    raise StopIteration
                value = self.tokens[self.counter]
                self.counter += 1
                return value

            next = __next__

            def restore_last_token(self):
                self.counter -= 1

        parsed_selector = _parse_format_selection(iter(TokenIterator(tokens)))
        return _build_selector_function(parsed_selector)

    def _calc_headers(self, info_dict, load_cookies=False):
        res = HTTPHeaderDict(self.params['http_headers'], info_dict.get('http_headers'))
        clean_headers(res)

        if load_cookies:  # For --load-info-json
            self._load_cookies(res.get('Cookie'), autoscope=info_dict['url'])  # compat
            self._load_cookies(info_dict.get('cookies'), autoscope=False)
        # The `Cookie` header is removed to prevent leaks and unscoped cookies.
        # See: https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-v8mc-9377-rwjj
        res.pop('Cookie', None)
        cookies = self.cookiejar.get_cookies_for_url(info_dict['url'])
        if cookies:
            encoder = LenientSimpleCookie()
            values = []
            for cookie in cookies:
                _, value = encoder.value_encode(cookie.value)
                values.append(f'{cookie.name}={value}')
                if cookie.domain:
                    values.append(f'Domain={cookie.domain}')
                if cookie.path:
                    values.append(f'Path={cookie.path}')
                if cookie.secure:
                    values.append('Secure')
                if cookie.expires:
                    values.append(f'Expires={cookie.expires}')
                if cookie.version:
                    values.append(f'Version={cookie.version}')
            info_dict['cookies'] = '; '.join(values)

        if 'X-Forwarded-For' not in res:
            x_forwarded_for_ip = info_dict.get('__x_forwarded_for_ip')
            if x_forwarded_for_ip:
                res['X-Forwarded-For'] = x_forwarded_for_ip

        return res

    def _calc_cookies(self, url):
        self.deprecation_warning('"YoutubeDL._calc_cookies" is deprecated and may be removed in a future version')
        return self.cookiejar.get_cookie_header(url)

    def _sort_thumbnails(self, thumbnails):
        thumbnails.sort(key=lambda t: (
            t.get('preference') if t.get('preference') is not None else -1,
            t.get('width') if t.get('width') is not None else -1,
            t.get('height') if t.get('height') is not None else -1,
            t.get('id') if t.get('id') is not None else '',
            t.get('url')))

    def _sanitize_thumbnails(self, info_dict):
        thumbnails = info_dict.get('thumbnails')
        if thumbnails is None:
            thumbnail = info_dict.get('thumbnail')
            if thumbnail:
                info_dict['thumbnails'] = thumbnails = [{'url': thumbnail}]
        if not thumbnails:
            return

        def check_thumbnails(thumbnails):
            for t in thumbnails:
                self.to_screen(f'[info] Testing thumbnail {t["id"]}')
                try:
                    self.urlopen(HEADRequest(t['url']))
                except network_exceptions as err:
                    self.to_screen(f'[info] Unable to connect to thumbnail {t["id"]} URL {t["url"]!r} - {err}. Skipping...')
                    continue
                yield t

        self._sort_thumbnails(thumbnails)
        for i, t in enumerate(thumbnails):
            if t.get('id') is None:
                t['id'] = str(i)
            if t.get('width') and t.get('height'):
                t['resolution'] = '%dx%d' % (t['width'], t['height'])
            t['url'] = sanitize_url(t['url'])

        if self.params.get('check_formats') is True:
            info_dict['thumbnails'] = LazyList(check_thumbnails(thumbnails[::-1]), reverse=True)
        else:
            info_dict['thumbnails'] = thumbnails

    def _fill_common_fields(self, info_dict, final=True):
        # TODO: move sanitization here
        if final:
            title = info_dict['fulltitle'] = info_dict.get('title')
            if not title:
                if title == '':
                    self.write_debug('Extractor gave empty title. Creating a generic title')
                else:
                    self.report_warning('Extractor failed to obtain "title". Creating a generic title instead')
                info_dict['title'] = f'{info_dict["extractor"].replace(":", "-")} video #{info_dict["id"]}'

        if info_dict.get('duration') is not None:
            info_dict['duration_string'] = formatSeconds(info_dict['duration'])

        for ts_key, date_key in (
                ('timestamp', 'upload_date'),
                ('release_timestamp', 'release_date'),
                ('modified_timestamp', 'modified_date'),
        ):
            if info_dict.get(date_key) is None and info_dict.get(ts_key) is not None:
                # Working around out-of-range timestamp values (e.g. negative ones on Windows,
                # see http://bugs.python.org/issue1646728)
                with contextlib.suppress(ValueError, OverflowError, OSError):
                    upload_date = dt.datetime.fromtimestamp(info_dict[ts_key], dt.timezone.utc)
                    info_dict[date_key] = upload_date.strftime('%Y%m%d')

        if not info_dict.get('release_year'):
            info_dict['release_year'] = traverse_obj(info_dict, ('release_date', {lambda x: int(x[:4])}))

        live_keys = ('is_live', 'was_live')
        live_status = info_dict.get('live_status')
        if live_status is None:
            for key in live_keys:
                if info_dict.get(key) is False:
                    continue
                if info_dict.get(key):
                    live_status = key
                break
            if all(info_dict.get(key) is False for key in live_keys):
                live_status = 'not_live'
        if live_status:
            info_dict['live_status'] = live_status
            for key in live_keys:
                if info_dict.get(key) is None:
                    info_dict[key] = (live_status == key)
        if live_status == 'post_live':
            info_dict['was_live'] = True

        # Auto generate title fields corresponding to the *_number fields when missing
        # in order to always have clean titles. This is very common for TV series.
        for field in ('chapter', 'season', 'episode'):
            if final and info_dict.get(f'{field}_number') is not None and not info_dict.get(field):
                info_dict[field] = '%s %d' % (field.capitalize(), info_dict[f'{field}_number'])

        for old_key, new_key in self._deprecated_multivalue_fields.items():
            if new_key in info_dict and old_key in info_dict:
                if '_version' not in info_dict:  # HACK: Do not warn when using --load-info-json
                    self.deprecation_warning(f'Do not return {old_key!r} when {new_key!r} is present')
            elif old_value := info_dict.get(old_key):
                info_dict[new_key] = old_value.split(', ')
            elif new_value := info_dict.get(new_key):
                info_dict[old_key] = ', '.join(v.replace(',', '\N{FULLWIDTH COMMA}') for v in new_value)

    def _raise_pending_errors(self, info):
        err = info.pop('__pending_error', None)
        if err:
            self.report_error(err, tb=False)

    def sort_formats(self, info_dict):
        formats = self._get_formats(info_dict)
        formats.sort(key=FormatSorter(
            self, info_dict.get('_format_sort_fields') or []).calculate_preference)

    def process_video_result(self, info_dict, download=True):
        assert info_dict.get('_type', 'video') == 'video'
        self._num_videos += 1

        if 'id' not in info_dict:
            raise ExtractorError('Missing "id" field in extractor result', ie=info_dict['extractor'])
        elif not info_dict.get('id'):
            raise ExtractorError('Extractor failed to obtain "id"', ie=info_dict['extractor'])

        def report_force_conversion(field, field_not, conversion):
            self.report_warning(
                f'"{field}" field is not {field_not} - forcing {conversion} conversion, '
                'there is an error in extractor')

        def sanitize_string_field(info, string_field):
            field = info.get(string_field)
            if field is None or isinstance(field, str):
                return
            report_force_conversion(string_field, 'a string', 'string')
            info[string_field] = str(field)

        def sanitize_numeric_fields(info):
            for numeric_field in self._NUMERIC_FIELDS:
                field = info.get(numeric_field)
                if field is None or isinstance(field, (int, float)):
                    continue
                report_force_conversion(numeric_field, 'numeric', 'int')
                info[numeric_field] = int_or_none(field)

        sanitize_string_field(info_dict, 'id')
        sanitize_numeric_fields(info_dict)
        if info_dict.get('section_end') and info_dict.get('section_start') is not None:
            info_dict['duration'] = round(info_dict['section_end'] - info_dict['section_start'], 3)
        if (info_dict.get('duration') or 0) <= 0 and info_dict.pop('duration', None):
            self.report_warning('"duration" field is negative, there is an error in extractor')

        chapters = info_dict.get('chapters') or []
        if chapters and chapters[0].get('start_time'):
            chapters.insert(0, {'start_time': 0})

        dummy_chapter = {'end_time': 0, 'start_time': info_dict.get('duration')}
        for idx, (prev, current, next_) in enumerate(zip(
                (dummy_chapter, *chapters), chapters, (*chapters[1:], dummy_chapter)), 1):
            if current.get('start_time') is None:
                current['start_time'] = prev.get('end_time')
            if not current.get('end_time'):
                current['end_time'] = next_.get('start_time')
            if not current.get('title'):
                current['title'] = f'<Untitled Chapter {idx}>'

        if 'playlist' not in info_dict:
            # It isn't part of a playlist
            info_dict['playlist'] = None
            info_dict['playlist_index'] = None

        self._sanitize_thumbnails(info_dict)

        thumbnail = info_dict.get('thumbnail')
        thumbnails = info_dict.get('thumbnails')
        if thumbnail:
            info_dict['thumbnail'] = sanitize_url(thumbnail)
        elif thumbnails:
            info_dict['thumbnail'] = thumbnails[-1]['url']

        if info_dict.get('display_id') is None and 'id' in info_dict:
            info_dict['display_id'] = info_dict['id']

        self._fill_common_fields(info_dict)

        for cc_kind in ('subtitles', 'automatic_captions'):
            cc = info_dict.get(cc_kind)
            if cc:
                for _, subtitle in cc.items():
                    for subtitle_format in subtitle:
                        if subtitle_format.get('url'):
                            subtitle_format['url'] = sanitize_url(subtitle_format['url'])
                        if subtitle_format.get('ext') is None:
                            subtitle_format['ext'] = determine_ext(subtitle_format['url']).lower()

        automatic_captions = info_dict.get('automatic_captions')
        subtitles = info_dict.get('subtitles')

        info_dict['requested_subtitles'] = self.process_subtitles(
            info_dict['id'], subtitles, automatic_captions)

        formats = self._get_formats(info_dict)

        # Backward compatibility with InfoExtractor._sort_formats
        field_preference = (formats or [{}])[0].pop('__sort_fields', None)
        if field_preference:
            info_dict['_format_sort_fields'] = field_preference

        info_dict['_has_drm'] = any(  # or None ensures --clean-infojson removes it
            f.get('has_drm') and f['has_drm'] != 'maybe' for f in formats) or None
        if not self.params.get('allow_unplayable_formats'):
            formats = [f for f in formats if not f.get('has_drm') or f['has_drm'] == 'maybe']

        if formats and all(f.get('acodec') == f.get('vcodec') == 'none' for f in formats):
            self.report_warning(
                f'{"This video is DRM protected and " if info_dict["_has_drm"] else ""}'
                'only images are available for download. Use --list-formats to see them'.capitalize())

        get_from_start = not info_dict.get('is_live') or bool(self.params.get('live_from_start'))
        if not get_from_start:
            info_dict['title'] += ' ' + dt.datetime.now().strftime('%Y-%m-%d %H:%M')
        if info_dict.get('is_live') and formats:
            formats = [f for f in formats if bool(f.get('is_from_start')) == get_from_start]
            if get_from_start and not formats:
                self.raise_no_formats(info_dict, msg=(
                    '--live-from-start is passed, but there are no formats that can be downloaded from the start. '
                    'If you want to download from the current time, use --no-live-from-start'))

        def is_wellformed(f):
            url = f.get('url')
            if not url:
                self.report_warning(
                    '"url" field is missing or empty - skipping format, '
                    'there is an error in extractor')
                return False
            if isinstance(url, bytes):
                sanitize_string_field(f, 'url')
            return True

        # Filter out malformed formats for better extraction robustness
        formats = list(filter(is_wellformed, formats or []))

        if not formats:
            self.raise_no_formats(info_dict)

        for fmt in formats:
            sanitize_string_field(fmt, 'format_id')
            sanitize_numeric_fields(fmt)
            fmt['url'] = sanitize_url(fmt['url'])
            if fmt.get('ext') is None:
                fmt['ext'] = determine_ext(fmt['url']).lower()
            if fmt['ext'] in ('aac', 'opus', 'mp3', 'flac', 'vorbis'):
                if fmt.get('acodec') is None:
                    fmt['acodec'] = fmt['ext']
            if fmt.get('protocol') is None:
                fmt['protocol'] = determine_protocol(fmt)
            if fmt.get('resolution') is None:
                fmt['resolution'] = self.format_resolution(fmt, default=None)
            if fmt.get('dynamic_range') is None and fmt.get('vcodec') != 'none':
                fmt['dynamic_range'] = 'SDR'
            if fmt.get('aspect_ratio') is None:
                fmt['aspect_ratio'] = try_call(lambda: round(fmt['width'] / fmt['height'], 2))
            # For fragmented formats, "tbr" is often max bitrate and not average
            if (('manifest-filesize-approx' in self.params['compat_opts'] or not fmt.get('manifest_url'))
                    and not fmt.get('filesize') and not fmt.get('filesize_approx')):
                fmt['filesize_approx'] = filesize_from_tbr(fmt.get('tbr'), info_dict.get('duration'))
            fmt['http_headers'] = self._calc_headers(collections.ChainMap(fmt, info_dict), load_cookies=True)

        # Safeguard against old/insecure infojson when using --load-info-json
        if info_dict.get('http_headers'):
            info_dict['http_headers'] = HTTPHeaderDict(info_dict['http_headers'])
            info_dict['http_headers'].pop('Cookie', None)

        # This is copied to http_headers by the above _calc_headers and can now be removed
        if '__x_forwarded_for_ip' in info_dict:
            del info_dict['__x_forwarded_for_ip']

        self.sort_formats({
            'formats': formats,
            '_format_sort_fields': info_dict.get('_format_sort_fields'),
        })

        # Sanitize and group by format_id
        formats_dict = {}
        for i, fmt in enumerate(formats):
            if not fmt.get('format_id'):
                fmt['format_id'] = str(i)
            else:
                # Sanitize format_id from characters used in format selector expression
                fmt['format_id'] = re.sub(r'[\s,/+\[\]()]', '_', fmt['format_id'])
            formats_dict.setdefault(fmt['format_id'], []).append(fmt)

        # Make sure all formats have unique format_id
        common_exts = set(itertools.chain(*self._format_selection_exts.values()))
        for format_id, ambiguous_formats in formats_dict.items():
            ambigious_id = len(ambiguous_formats) > 1
            for i, fmt in enumerate(ambiguous_formats):
                if ambigious_id:
                    fmt['format_id'] = f'{format_id}-{i}'
                # Ensure there is no conflict between id and ext in format selection
                # See https://github.com/yt-dlp/yt-dlp/issues/1282
                if fmt['format_id'] != fmt['ext'] and fmt['format_id'] in common_exts:
                    fmt['format_id'] = 'f{}'.format(fmt['format_id'])

                if fmt.get('format') is None:
                    fmt['format'] = '{id} - {res}{note}'.format(
                        id=fmt['format_id'],
                        res=self.format_resolution(fmt),
                        note=format_field(fmt, 'format_note', ' (%s)'),
                    )

        if self.params.get('check_formats') is True:
            formats = LazyList(self._check_formats(formats[::-1]), reverse=True)

        if not formats or formats[0] is not info_dict:
            # only set the 'formats' fields if the original info_dict list them
            # otherwise we end up with a circular reference, the first (and unique)
            # element in the 'formats' field in info_dict is info_dict itself,
            # which can't be exported to json
            info_dict['formats'] = formats

        info_dict, _ = self.pre_process(info_dict)

        if self._match_entry(info_dict, incomplete=self._format_fields) is not None:
            return info_dict

        self.post_extract(info_dict)
        info_dict, _ = self.pre_process(info_dict, 'after_filter')

        # The pre-processors may have modified the formats
        formats = self._get_formats(info_dict)

        list_only = self.params.get('simulate') == 'list_only'
        interactive_format_selection = not list_only and self.format_selector == '-'
        if self.params.get('list_thumbnails'):
            self.list_thumbnails(info_dict)
        if self.params.get('listsubtitles'):
            if 'automatic_captions' in info_dict:
                self.list_subtitles(
                    info_dict['id'], automatic_captions, 'automatic captions')
            self.list_subtitles(info_dict['id'], subtitles, 'subtitles')
        if self.params.get('listformats') or interactive_format_selection:
            self.list_formats(info_dict)
        if list_only:
            # Without this printing, -F --print-json will not work
            self.__forced_printings(info_dict)
            return info_dict

        format_selector = self.format_selector
        while True:
            if interactive_format_selection:
                req_format = input(self._format_screen('\nEnter format selector ', self.Styles.EMPHASIS)
                                   + '(Press ENTER for default, or Ctrl+C to quit)'
                                   + self._format_screen(': ', self.Styles.EMPHASIS))
                try:
                    format_selector = self.build_format_selector(req_format) if req_format else None
                except SyntaxError as err:
                    self.report_error(err, tb=False, is_error=False)
                    continue

            if format_selector is None:
                req_format = self._default_format_spec(info_dict)
                self.write_debug(f'Default format spec: {req_format}')
                format_selector = self.build_format_selector(req_format)

            formats_to_download = self._select_formats(formats, format_selector)
            if interactive_format_selection and not formats_to_download:
                self.report_error('Requested format is not available', tb=False, is_error=False)
                continue
            break

        if not formats_to_download:
            if not self.params.get('ignore_no_formats_error'):
                raise ExtractorError(
                    'Requested format is not available. Use --list-formats for a list of available formats',
                    expected=True, video_id=info_dict['id'], ie=info_dict['extractor'])
            self.report_warning('Requested format is not available')
            # Process what we can, even without any available formats.
            formats_to_download = [{}]

        requested_ranges = tuple(self.params.get('download_ranges', lambda *_: [{}])(info_dict, self))
        best_format, downloaded_formats = formats_to_download[-1], []
        if download:
            if best_format and requested_ranges:
                def to_screen(*msg):
                    self.to_screen(f'[info] {info_dict["id"]}: {" ".join(", ".join(variadic(m)) for m in msg)}')

                to_screen(f'Downloading {len(formats_to_download)} format(s):',
                          (f['format_id'] for f in formats_to_download))
                if requested_ranges != ({}, ):
                    to_screen(f'Downloading {len(requested_ranges)} time ranges:',
                              (f'{c["start_time"]:.1f}-{c["end_time"]:.1f}' for c in requested_ranges))
            max_downloads_reached = False

            for fmt, chapter in itertools.product(formats_to_download, requested_ranges):
                new_info = self._copy_infodict(info_dict)
                new_info.update(fmt)
                offset, duration = info_dict.get('section_start') or 0, info_dict.get('duration') or float('inf')
                end_time = offset + min(chapter.get('end_time', duration), duration)
                # duration may not be accurate. So allow deviations <1sec
                if end_time == float('inf') or end_time > offset + duration + 1:
                    end_time = None
                if chapter or offset:
                    new_info.update({
                        'section_start': offset + chapter.get('start_time', 0),
                        'section_end': end_time,
                        'section_title': chapter.get('title'),
                        'section_number': chapter.get('index'),
                    })
                downloaded_formats.append(new_info)
                try:
                    self.process_info(new_info)
                except MaxDownloadsReached:
                    max_downloads_reached = True
                self._raise_pending_errors(new_info)
                # Remove copied info
                for key, val in tuple(new_info.items()):
                    if info_dict.get(key) == val:
                        new_info.pop(key)
                if max_downloads_reached:
                    break

            write_archive = {f.get('__write_download_archive', False) for f in downloaded_formats}
            assert write_archive.issubset({True, False, 'ignore'})
            if True in write_archive and False not in write_archive:
                self.record_download_archive(info_dict)

            info_dict['requested_downloads'] = downloaded_formats
            info_dict = self.run_all_pps('after_video', info_dict)
            if max_downloads_reached:
                raise MaxDownloadsReached

        # We update the info dict with the selected best quality format (backwards compatibility)
        info_dict.update(best_format)
        return info_dict

    def process_subtitles(self, video_id, normal_subtitles, automatic_captions):
        """Select the requested subtitles and their format"""
        available_subs, normal_sub_langs = {}, []
        if normal_subtitles and self.params.get('writesubtitles'):
            available_subs.update(normal_subtitles)
            normal_sub_langs = tuple(normal_subtitles.keys())
        if automatic_captions and self.params.get('writeautomaticsub'):
            for lang, cap_info in automatic_captions.items():
                if lang not in available_subs:
                    available_subs[lang] = cap_info

        if not available_subs or (
                not self.params.get('writesubtitles')
                and not self.params.get('writeautomaticsub')):
            return None

        all_sub_langs = tuple(available_subs.keys())
        if self.params.get('allsubtitles', False):
            requested_langs = all_sub_langs
        elif self.params.get('subtitleslangs', False):
            try:
                requested_langs = orderedSet_from_options(
                    self.params.get('subtitleslangs'), {'all': all_sub_langs}, use_regex=True)
            except re.error as e:
                raise ValueError(f'Wrong regex for subtitlelangs: {e.pattern}')
        else:
            requested_langs = LazyList(itertools.chain(
                ['en'] if 'en' in normal_sub_langs else [],
                filter(lambda f: f.startswith('en'), normal_sub_langs),
                ['en'] if 'en' in all_sub_langs else [],
                filter(lambda f: f.startswith('en'), all_sub_langs),
                normal_sub_langs, all_sub_langs,
            ))[:1]
        if requested_langs:
            self.to_screen(f'[info] {video_id}: Downloading subtitles: {", ".join(requested_langs)}')

        formats_query = self.params.get('subtitlesformat', 'best')
        formats_preference = formats_query.split('/') if formats_query else []
        subs = {}
        for lang in requested_langs:
            formats = available_subs.get(lang)
            if formats is None:
                self.report_warning(f'{lang} subtitles not available for {video_id}')
                continue
            for ext in formats_preference:
                if ext == 'best':
                    f = formats[-1]
                    break
                matches = list(filter(lambda f: f['ext'] == ext, formats))
                if matches:
                    f = matches[-1]
                    break
            else:
                f = formats[-1]
                self.report_warning(
                    'No subtitle format found matching "{}" for language {}, '
                    'using {}. Use --list-subs for a list of available subtitles'.format(formats_query, lang, f['ext']))
            subs[lang] = f
        return subs

    def _forceprint(self, key, info_dict):
        if info_dict is None:
            return
        info_copy = info_dict.copy()
        info_copy.setdefault('filename', self.prepare_filename(info_dict))
        if info_dict.get('requested_formats') is not None:
            # For RTMP URLs, also include the playpath
            info_copy['urls'] = '\n'.join(f['url'] + f.get('play_path', '') for f in info_dict['requested_formats'])
        elif info_dict.get('url'):
            info_copy['urls'] = info_dict['url'] + info_dict.get('play_path', '')
        info_copy['formats_table'] = self.render_formats_table(info_dict)
        info_copy['thumbnails_table'] = self.render_thumbnails_table(info_dict)
        info_copy['subtitles_table'] = self.render_subtitles_table(info_dict.get('id'), info_dict.get('subtitles'))
        info_copy['automatic_captions_table'] = self.render_subtitles_table(info_dict.get('id'), info_dict.get('automatic_captions'))

        def format_tmpl(tmpl):
            mobj = re.fullmatch(r'([\w.:,]|-\d|(?P<dict>{([\w.:,]|-\d)+}))+=?', tmpl)
            if not mobj:
                return tmpl

            fmt = '%({})s'
            if tmpl.startswith('{'):
                tmpl, fmt = f'.{tmpl}', '%({})j'
            if tmpl.endswith('='):
                tmpl, fmt = tmpl[:-1], '{0} = %({0})#j'
            return '\n'.join(map(fmt.format, [tmpl] if mobj.group('dict') else tmpl.split(',')))

        for tmpl in self.params['forceprint'].get(key, []):
            self.to_stdout(self.evaluate_outtmpl(format_tmpl(tmpl), info_copy))

        for tmpl, file_tmpl in self.params['print_to_file'].get(key, []):
            filename = self.prepare_filename(info_dict, outtmpl=file_tmpl)
            tmpl = format_tmpl(tmpl)
            self.to_screen(f'[info] Writing {tmpl!r} to: {filename}')
            if self._ensure_dir_exists(filename):
                with open(filename, 'a', encoding='utf-8', newline='') as f:
                    f.write(self.evaluate_outtmpl(tmpl, info_copy) + os.linesep)

        return info_copy

    def __forced_printings(self, info_dict, filename=None, incomplete=True):
        if (self.params.get('forcejson')
                or self.params['forceprint'].get('video')
                or self.params['print_to_file'].get('video')):
            self.post_extract(info_dict)
        if filename:
            info_dict['filename'] = filename
        info_copy = self._forceprint('video', info_dict)

        def print_field(field, actual_field=None, optional=False):
            if actual_field is None:
                actual_field = field
            if self.params.get(f'force{field}') and (
                    info_copy.get(field) is not None or (not optional and not incomplete)):
                self.to_stdout(info_copy[actual_field])

        print_field('title')
        print_field('id')
        print_field('url', 'urls')
        print_field('thumbnail', optional=True)
        print_field('description', optional=True)
        print_field('filename')
        if self.params.get('forceduration') and info_copy.get('duration') is not None:
            self.to_stdout(formatSeconds(info_copy['duration']))
        print_field('format')

        if self.params.get('forcejson'):
            self.to_stdout(json.dumps(self.sanitize_info(info_dict)))

    def dl(self, name, info, subtitle=False, test=False):
        if not info.get('url'):
            self.raise_no_formats(info, True)

        if test:
            verbose = self.params.get('verbose')
            quiet = self.params.get('quiet') or not verbose
            params = {
                'test': True,
                'quiet': quiet,
                'verbose': verbose,
                'noprogress': quiet,
                'nopart': True,
                'skip_unavailable_fragments': False,
                'keep_fragments': False,
                'overwrites': True,
                '_no_ytdl_file': True,
            }
        else:
            params = self.params
        fd = get_suitable_downloader(info, params, to_stdout=(name == '-'))(self, params)
        if not test:
            for ph in self._progress_hooks:
                fd.add_progress_hook(ph)
            urls = '", "'.join(
                (f['url'].split(',')[0] + ',<data>' if f['url'].startswith('data:') else f['url'])
                for f in info.get('requested_formats', []) or [info])
            self.write_debug(f'Invoking {fd.FD_NAME} downloader on "{urls}"')

        # Note: Ideally info should be a deep-copied so that hooks cannot modify it.
        # But it may contain objects that are not deep-copyable
        new_info = self._copy_infodict(info)
        if new_info.get('http_headers') is None:
            new_info['http_headers'] = self._calc_headers(new_info)
        return fd.download(name, new_info, subtitle)

    def existing_file(self, filepaths, *, default_overwrite=True):
        existing_files = list(filter(os.path.exists, orderedSet(filepaths)))
        if existing_files and not self.params.get('overwrites', default_overwrite):
            return existing_files[0]

        for file in existing_files:
            self.report_file_delete(file)
            os.remove(file)
        return None

    @_catch_unsafe_extension_error
    def process_info(self, info_dict):
        """Process a single resolved IE result. (Modifies it in-place)"""

        assert info_dict.get('_type', 'video') == 'video'
        original_infodict = info_dict

        if 'format' not in info_dict and 'ext' in info_dict:
            info_dict['format'] = info_dict['ext']

        if self._match_entry(info_dict) is not None:
            info_dict['__write_download_archive'] = 'ignore'
            return

        # Does nothing under normal operation - for backward compatibility of process_info
        self.post_extract(info_dict)

        def replace_info_dict(new_info):
            nonlocal info_dict
            if new_info == info_dict:
                return
            info_dict.clear()
            info_dict.update(new_info)

        new_info, _ = self.pre_process(info_dict, 'video')
        replace_info_dict(new_info)
        self._num_downloads += 1

        # info_dict['_filename'] needs to be set for backward compatibility
        info_dict['_filename'] = full_filename = self.prepare_filename(info_dict, warn=True)
        temp_filename = self.prepare_filename(info_dict, 'temp')
        files_to_move = {}

        # Forced printings
        self.__forced_printings(info_dict, full_filename, incomplete=('format' not in info_dict))

        def check_max_downloads():
            if self._num_downloads >= float(self.params.get('max_downloads') or 'inf'):
                raise MaxDownloadsReached

        if self.params.get('simulate'):
            info_dict['__write_download_archive'] = self.params.get('force_write_download_archive')
            check_max_downloads()
            return

        if full_filename is None:
            return
        if not self._ensure_dir_exists(encodeFilename(full_filename)):
            return
        if not self._ensure_dir_exists(encodeFilename(temp_filename)):
            return

        if self._write_description('video', info_dict,
                                   self.prepare_filename(info_dict, 'description')) is None:
            return

        sub_files = self._write_subtitles(info_dict, temp_filename)
        if sub_files is None:
            return
        files_to_move.update(dict(sub_files))

        thumb_files = self._write_thumbnails(
            'video', info_dict, temp_filename, self.prepare_filename(info_dict, 'thumbnail'))
        if thumb_files is None:
            return
        files_to_move.update(dict(thumb_files))

        infofn = self.prepare_filename(info_dict, 'infojson')
        _infojson_written = self._write_info_json('video', info_dict, infofn)
        if _infojson_written:
            info_dict['infojson_filename'] = infofn
            # For backward compatibility, even though it was a private field
            info_dict['__infojson_filename'] = infofn
        elif _infojson_written is None:
            return

        # Note: Annotations are deprecated
        annofn = None
        if self.params.get('writeannotations', False):
            annofn = self.prepare_filename(info_dict, 'annotation')
        if annofn:
            if not self._ensure_dir_exists(encodeFilename(annofn)):
                return
            if not self.params.get('overwrites', True) and os.path.exists(encodeFilename(annofn)):
                self.to_screen('[info] Video annotations are already present')
            elif not info_dict.get('annotations'):
                self.report_warning('There are no annotations to write.')
            else:
                try:
                    self.to_screen('[info] Writing video annotations to: ' + annofn)
                    with open(encodeFilename(annofn), 'w', encoding='utf-8') as annofile:
                        annofile.write(info_dict['annotations'])
                except (KeyError, TypeError):
                    self.report_warning('There are no annotations to write.')
                except OSError:
                    self.report_error('Cannot write annotations file: ' + annofn)
                    return

        # Write internet shortcut files
        def _write_link_file(link_type):
            url = try_get(info_dict['webpage_url'], iri_to_uri)
            if not url:
                self.report_warning(
                    f'Cannot write internet shortcut file because the actual URL of "{info_dict["webpage_url"]}" is unknown')
                return True
            linkfn = replace_extension(self.prepare_filename(info_dict, 'link'), link_type, info_dict.get('ext'))
            if not self._ensure_dir_exists(encodeFilename(linkfn)):
                return False
            if self.params.get('overwrites', True) and os.path.exists(encodeFilename(linkfn)):
                self.to_screen(f'[info] Internet shortcut (.{link_type}) is already present')
                return True
            try:
                self.to_screen(f'[info] Writing internet shortcut (.{link_type}) to: {linkfn}')
                with open(encodeFilename(to_high_limit_path(linkfn)), 'w', encoding='utf-8',
                          newline='\r\n' if link_type == 'url' else '\n') as linkfile:
                    template_vars = {'url': url}
                    if link_type == 'desktop':
                        template_vars['filename'] = linkfn[:-(len(link_type) + 1)]
                    linkfile.write(LINK_TEMPLATES[link_type] % template_vars)
            except OSError:
                self.report_error(f'Cannot write internet shortcut {linkfn}')
                return False
            return True

        write_links = {
            'url': self.params.get('writeurllink'),
            'webloc': self.params.get('writewebloclink'),
            'desktop': self.params.get('writedesktoplink'),
        }
        if self.params.get('writelink'):
            link_type = ('webloc' if sys.platform == 'darwin'
                         else 'desktop' if sys.platform.startswith('linux')
                         else 'url')
            write_links[link_type] = True

        if any(should_write and not _write_link_file(link_type)
               for link_type, should_write in write_links.items()):
            return

        new_info, files_to_move = self.pre_process(info_dict, 'before_dl', files_to_move)
        replace_info_dict(new_info)

        if self.params.get('skip_download'):
            info_dict['filepath'] = temp_filename
            info_dict['__finaldir'] = os.path.dirname(os.path.abspath(encodeFilename(full_filename)))
            info_dict['__files_to_move'] = files_to_move
            replace_info_dict(self.run_pp(MoveFilesAfterDownloadPP(self, False), info_dict))
            info_dict['__write_download_archive'] = self.params.get('force_write_download_archive')
        else:
            # Download
            info_dict.setdefault('__postprocessors', [])
            try:

                def existing_video_file(*filepaths):
                    ext = info_dict.get('ext')
                    converted = lambda file: replace_extension(file, self.params.get('final_ext') or ext, ext)
                    file = self.existing_file(itertools.chain(*zip(map(converted, filepaths), filepaths)),
                                              default_overwrite=False)
                    if file:
                        info_dict['ext'] = os.path.splitext(file)[1][1:]
                    return file

                fd, success = None, True
                if info_dict.get('protocol') or info_dict.get('url'):
                    fd = get_suitable_downloader(info_dict, self.params, to_stdout=temp_filename == '-')
                    if fd != FFmpegFD and 'no-direct-merge' not in self.params['compat_opts'] and (
                            info_dict.get('section_start') or info_dict.get('section_end')):
                        msg = ('This format cannot be partially downloaded' if FFmpegFD.available()
                               else 'You have requested downloading the video partially, but ffmpeg is not installed')
                        self.report_error(f'{msg}. Aborting')
                        return

                if info_dict.get('requested_formats') is not None:
                    old_ext = info_dict['ext']
                    if self.params.get('merge_output_format') is None:
                        if (info_dict['ext'] == 'webm'
                                and info_dict.get('thumbnails')
                                # check with type instead of pp_key, __name__, or isinstance
                                # since we dont want any custom PPs to trigger this
                                and any(type(pp) == EmbedThumbnailPP for pp in self._pps['post_process'])):  # noqa: E721
                            info_dict['ext'] = 'mkv'
                            self.report_warning(
                                'webm doesn\'t support embedding a thumbnail, mkv will be used')
                    new_ext = info_dict['ext']

                    def correct_ext(filename, ext=new_ext):
                        if filename == '-':
                            return filename
                        filename_real_ext = os.path.splitext(filename)[1][1:]
                        filename_wo_ext = (
                            os.path.splitext(filename)[0]
                            if filename_real_ext in (old_ext, new_ext)
                            else filename)
                        return f'{filename_wo_ext}.{ext}'

                    # Ensure filename always has a correct extension for successful merge
                    full_filename = correct_ext(full_filename)
                    temp_filename = correct_ext(temp_filename)
                    dl_filename = existing_video_file(full_filename, temp_filename)

                    info_dict['__real_download'] = False
                    # NOTE: Copy so that original format dicts are not modified
                    info_dict['requested_formats'] = list(map(dict, info_dict['requested_formats']))

                    merger = FFmpegMergerPP(self)
                    downloaded = []
                    if dl_filename is not None:
                        self.report_file_already_downloaded(dl_filename)
                    elif fd:
                        for f in info_dict['requested_formats'] if fd != FFmpegFD else []:
                            f['filepath'] = fname = prepend_extension(
                                correct_ext(temp_filename, info_dict['ext']),
                                'f{}'.format(f['format_id']), info_dict['ext'])
                            downloaded.append(fname)
                        info_dict['url'] = '\n'.join(f['url'] for f in info_dict['requested_formats'])
                        success, real_download = self.dl(temp_filename, info_dict)
                        info_dict['__real_download'] = real_download
                    else:
                        if self.params.get('allow_unplayable_formats'):
                            self.report_warning(
                                'You have requested merging of multiple formats '
                                'while also allowing unplayable formats to be downloaded. '
                                'The formats won\'t be merged to prevent data corruption.')
                        elif not merger.available:
                            msg = 'You have requested merging of multiple formats but ffmpeg is not installed'
                            if not self.params.get('ignoreerrors'):
                                self.report_error(f'{msg}. Aborting due to --abort-on-error')
                                return
                            self.report_warning(f'{msg}. The formats won\'t be merged')

                        if temp_filename == '-':
                            reason = ('using a downloader other than ffmpeg' if FFmpegFD.can_merge_formats(info_dict, self.params)
                                      else 'but the formats are incompatible for simultaneous download' if merger.available
                                      else 'but ffmpeg is not installed')
                            self.report_warning(
                                f'You have requested downloading multiple formats to stdout {reason}. '
                                'The formats will be streamed one after the other')
                            fname = temp_filename
                        for f in info_dict['requested_formats']:
                            new_info = dict(info_dict)
                            del new_info['requested_formats']
                            new_info.update(f)
                            if temp_filename != '-':
                                fname = prepend_extension(
                                    correct_ext(temp_filename, new_info['ext']),
                                    'f{}'.format(f['format_id']), new_info['ext'])
                                if not self._ensure_dir_exists(fname):
                                    return
                                f['filepath'] = fname
                                downloaded.append(fname)
                            partial_success, real_download = self.dl(fname, new_info)
                            info_dict['__real_download'] = info_dict['__real_download'] or real_download
                            success = success and partial_success

                    if downloaded and merger.available and not self.params.get('allow_unplayable_formats'):
                        info_dict['__postprocessors'].append(merger)
                        info_dict['__files_to_merge'] = downloaded
                        # Even if there were no downloads, it is being merged only now
                        info_dict['__real_download'] = True
                    else:
                        for file in downloaded:
                            files_to_move[file] = None
                else:
                    # Just a single file
                    dl_filename = existing_video_file(full_filename, temp_filename)
                    if dl_filename is None or dl_filename == temp_filename:
                        # dl_filename == temp_filename could mean that the file was partially downloaded with --no-part.
                        # So we should try to resume the download
                        success, real_download = self.dl(temp_filename, info_dict)
                        info_dict['__real_download'] = real_download
                    else:
                        self.report_file_already_downloaded(dl_filename)

                dl_filename = dl_filename or temp_filename
                info_dict['__finaldir'] = os.path.dirname(os.path.abspath(encodeFilename(full_filename)))

            except network_exceptions as err:
                self.report_error(f'unable to download video data: {err}')
                return
            except OSError as err:
                raise UnavailableVideoError(err)
            except ContentTooShortError as err:
                self.report_error(f'content too short (expected {err.expected} bytes and served {err.downloaded})')
                return

            self._raise_pending_errors(info_dict)
            if success and full_filename != '-':

                def fixup():
                    do_fixup = True
                    fixup_policy = self.params.get('fixup')
                    vid = info_dict['id']

                    if fixup_policy in ('ignore', 'never'):
                        return
                    elif fixup_policy == 'warn':
                        do_fixup = 'warn'
                    elif fixup_policy != 'force':
                        assert fixup_policy in ('detect_or_warn', None)
                        if not info_dict.get('__real_download'):
                            do_fixup = False

                    def ffmpeg_fixup(cndn, msg, cls):
                        if not (do_fixup and cndn):
                            return
                        elif do_fixup == 'warn':
                            self.report_warning(f'{vid}: {msg}')
                            return
                        pp = cls(self)
                        if pp.available:
                            info_dict['__postprocessors'].append(pp)
                        else:
                            self.report_warning(f'{vid}: {msg}. Install ffmpeg to fix this automatically')

                    stretched_ratio = info_dict.get('stretched_ratio')
                    ffmpeg_fixup(stretched_ratio not in (1, None),
                                 f'Non-uniform pixel ratio {stretched_ratio}',
                                 FFmpegFixupStretchedPP)

                    downloader = get_suitable_downloader(info_dict, self.params) if 'protocol' in info_dict else None
                    downloader = downloader.FD_NAME if downloader else None

                    ext = info_dict.get('ext')
                    postprocessed_by_ffmpeg = info_dict.get('requested_formats') or any((
                        isinstance(pp, FFmpegVideoConvertorPP)
                        and resolve_recode_mapping(ext, pp.mapping)[0] not in (ext, None)
                    ) for pp in self._pps['post_process'])

                    if not postprocessed_by_ffmpeg:
                        ffmpeg_fixup(fd != FFmpegFD and ext == 'm4a'
                                     and info_dict.get('container') == 'm4a_dash',
                                     'writing DASH m4a. Only some players support this container',
                                     FFmpegFixupM4aPP)
                        ffmpeg_fixup(downloader == 'hlsnative' and not self.params.get('hls_use_mpegts')
                                     or info_dict.get('is_live') and self.params.get('hls_use_mpegts') is None,
                                     'Possible MPEG-TS in MP4 container or malformed AAC timestamps',
                                     FFmpegFixupM3u8PP)
                        ffmpeg_fixup(downloader == 'dashsegments'
                                     and (info_dict.get('is_live') or info_dict.get('is_dash_periods')),
                                     'Possible duplicate MOOV atoms', FFmpegFixupDuplicateMoovPP)

                    ffmpeg_fixup(downloader == 'web_socket_fragment', 'Malformed timestamps detected', FFmpegFixupTimestampPP)
                    ffmpeg_fixup(downloader == 'web_socket_fragment', 'Malformed duration detected', FFmpegFixupDurationPP)

                fixup()
                try:
                    replace_info_dict(self.post_process(dl_filename, info_dict, files_to_move))
                except PostProcessingError as err:
                    self.report_error(f'Postprocessing: {err}')
                    return
                try:
                    for ph in self._post_hooks:
                        ph(info_dict['filepath'])
                except Exception as err:
                    self.report_error(f'post hooks: {err}')
                    return
                info_dict['__write_download_archive'] = True

        assert info_dict is original_infodict  # Make sure the info_dict was modified in-place
        if self.params.get('force_write_download_archive'):
            info_dict['__write_download_archive'] = True
        check_max_downloads()

    def __download_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except CookieLoadError:
                raise
            except UnavailableVideoError as e:
                self.report_error(e)
            except DownloadCancelled as e:
                self.to_screen(f'[info] {e}')
                if not self.params.get('break_per_url'):
                    raise
                self._num_downloads = 0
            else:
                if self.params.get('dump_single_json', False):
                    self.post_extract(res)
                    self.to_stdout(json.dumps(self.sanitize_info(res)))
        return wrapper

    def download(self, url_list):
        """Download a given list of URLs."""
        url_list = variadic(url_list)  # Passing a single URL is a common mistake
        outtmpl = self.params['outtmpl']['default']
        if (len(url_list) > 1
                and outtmpl != '-'
                and '%' not in outtmpl
                and self.params.get('max_downloads') != 1):
            raise SameFileError(outtmpl)

        for url in url_list:
            self.__download_wrapper(self.extract_info)(
                url, force_generic_extractor=self.params.get('force_generic_extractor', False))

        return self._download_retcode

    def download_with_info_file(self, info_filename):
        with contextlib.closing(fileinput.FileInput(
                [info_filename], mode='r',
                openhook=fileinput.hook_encoded('utf-8'))) as f:
            # FileInput doesn't have a read method, we can't call json.load
            infos = [self.sanitize_info(info, self.params.get('clean_infojson', True))
                     for info in variadic(json.loads('\n'.join(f)))]
        for info in infos:
            try:
                self.__download_wrapper(self.process_ie_result)(info, download=True)
            except (DownloadError, EntryNotInPlaylist, ReExtractInfo) as e:
                if not isinstance(e, EntryNotInPlaylist):
                    self.to_stderr('\r')
                webpage_url = info.get('webpage_url')
                if webpage_url is None:
                    raise
                self.report_warning(f'The info failed to download: {e}; trying with URL {webpage_url}')
                self.download([webpage_url])
            except ExtractorError as e:
                self.report_error(e)
        return self._download_retcode

    @staticmethod
    def sanitize_info(info_dict, remove_private_keys=False):
        """ Sanitize the infodict for converting to json """
        if info_dict is None:
            return info_dict
        info_dict.setdefault('epoch', int(time.time()))
        info_dict.setdefault('_type', 'video')
        info_dict.setdefault('_version', {
            'version': __version__,
            'current_git_head': current_git_head(),
            'release_git_head': RELEASE_GIT_HEAD,
            'repository': ORIGIN,
        })

        if remove_private_keys:
            reject = lambda k, v: v is None or k.startswith('__') or k in {
                'requested_downloads', 'requested_formats', 'requested_subtitles', 'requested_entries',
                'entries', 'filepath', '_filename', 'filename', 'infojson_filename', 'original_url',
                'playlist_autonumber',
            }
        else:
            reject = lambda k, v: False

        def filter_fn(obj):
            if isinstance(obj, dict):
                return {k: filter_fn(v) for k, v in obj.items() if not reject(k, v)}
            elif isinstance(obj, (list, tuple, set, LazyList)):
                return list(map(filter_fn, obj))
            elif obj is None or isinstance(obj, (str, int, float, bool)):
                return obj
            else:
                return repr(obj)

        return filter_fn(info_dict)

    @staticmethod
    def filter_requested_info(info_dict, actually_filter=True):
        """ Alias of sanitize_info for backward compatibility """
        return YoutubeDL.sanitize_info(info_dict, actually_filter)

    def _delete_downloaded_files(self, *files_to_delete, info={}, msg=None):
        for filename in set(filter(None, files_to_delete)):
            if msg:
                self.to_screen(msg % filename)
            try:
                os.remove(filename)
            except OSError:
                self.report_warning(f'Unable to delete file {filename}')
            if filename in info.get('__files_to_move', []):  # NB: Delete even if None
                del info['__files_to_move'][filename]

    @staticmethod
    def post_extract(info_dict):
        def actual_post_extract(info_dict):
            if info_dict.get('_type') in ('playlist', 'multi_video'):
                for video_dict in info_dict.get('entries', {}):
                    actual_post_extract(video_dict or {})
                return

            post_extractor = info_dict.pop('__post_extractor', None) or dict
            info_dict.update(post_extractor())

        actual_post_extract(info_dict or {})

    def run_pp(self, pp, infodict):
        files_to_delete = []
        if '__files_to_move' not in infodict:
            infodict['__files_to_move'] = {}
        try:
            files_to_delete, infodict = pp.run(infodict)
        except PostProcessingError as e:
            # Must be True and not 'only_download'
            if self.params.get('ignoreerrors') is True:
                self.report_error(e)
                return infodict
            raise

        if not files_to_delete:
            return infodict
        if self.params.get('keepvideo', False):
            for f in files_to_delete:
                infodict['__files_to_move'].setdefault(f, '')
        else:
            self._delete_downloaded_files(
                *files_to_delete, info=infodict, msg='Deleting original file %s (pass -k to keep)')
        return infodict

    def run_all_pps(self, key, info, *, additional_pps=None):
        if key != 'video':
            self._forceprint(key, info)
        for pp in (additional_pps or []) + self._pps[key]:
            info = self.run_pp(pp, info)
        return info

    def pre_process(self, ie_info, key='pre_process', files_to_move=None):
        info = dict(ie_info)
        info['__files_to_move'] = files_to_move or {}
        try:
            info = self.run_all_pps(key, info)
        except PostProcessingError as err:
            msg = f'Preprocessing: {err}'
            info.setdefault('__pending_error', msg)
            self.report_error(msg, is_error=False)
        return info, info.pop('__files_to_move', None)

    def post_process(self, filename, info, files_to_move=None):
        """Run all the postprocessors on the given file."""
        info['filepath'] = filename
        info['__files_to_move'] = files_to_move or {}
        info = self.run_all_pps('post_process', info, additional_pps=info.get('__postprocessors'))
        info = self.run_pp(MoveFilesAfterDownloadPP(self), info)
        del info['__files_to_move']
        return self.run_all_pps('after_move', info)

    def _make_archive_id(self, info_dict):
        video_id = info_dict.get('id')
        if not video_id:
            return
        # Future-proof against any change in case
        # and backwards compatibility with prior versions
        extractor = info_dict.get('extractor_key') or info_dict.get('ie_key')  # key in a playlist
        if extractor is None:
            url = str_or_none(info_dict.get('url'))
            if not url:
                return
            # Try to find matching extractor for the URL and take its ie_key
            for ie_key, ie in self._ies.items():
                if ie.suitable(url):
                    extractor = ie_key
                    break
            else:
                return
        return make_archive_id(extractor, video_id)

    def in_download_archive(self, info_dict):
        if not self.archive:
            return False

        vid_ids = [self._make_archive_id(info_dict)]
        vid_ids.extend(info_dict.get('_old_archive_ids') or [])
        return any(id_ in self.archive for id_ in vid_ids)

    def record_download_archive(self, info_dict):
        fn = self.params.get('download_archive')
        if fn is None:
            return
        vid_id = self._make_archive_id(info_dict)
        assert vid_id

        self.write_debug(f'Adding to archive: {vid_id}')
        if is_path_like(fn):
            with locked_file(fn, 'a', encoding='utf-8') as archive_file:
                archive_file.write(vid_id + '\n')
        self.archive.add(vid_id)

    @staticmethod
    def format_resolution(format, default='unknown'):
        if format.get('vcodec') == 'none' and format.get('acodec') != 'none':
            return 'audio only'
        if format.get('resolution') is not None:
            return format['resolution']
        if format.get('width') and format.get('height'):
            return '%dx%d' % (format['width'], format['height'])
        elif format.get('height'):
            return '{}p'.format(format['height'])
        elif format.get('width'):
            return '%dx?' % format['width']
        return default

    def _list_format_headers(self, *headers):
        if self.params.get('listformats_table', True) is not False:
            return [self._format_out(header, self.Styles.HEADERS) for header in headers]
        return headers

    def _format_note(self, fdict):
        res = ''
        if fdict.get('ext') in ['f4f', 'f4m']:
            res += '(unsupported)'
        if fdict.get('language'):
            if res:
                res += ' '
            res += '[{}]'.format(fdict['language'])
        if fdict.get('format_note') is not None:
            if res:
                res += ' '
            res += fdict['format_note']
        if fdict.get('tbr') is not None:
            if res:
                res += ', '
            res += '%4dk' % fdict['tbr']
        if fdict.get('container') is not None:
            if res:
                res += ', '
            res += '{} container'.format(fdict['container'])
        if (fdict.get('vcodec') is not None
                and fdict.get('vcodec') != 'none'):
            if res:
                res += ', '
            res += fdict['vcodec']
            if fdict.get('vbr') is not None:
                res += '@'
        elif fdict.get('vbr') is not None and fdict.get('abr') is not None:
            res += 'video@'
        if fdict.get('vbr') is not None:
            res += '%4dk' % fdict['vbr']
        if fdict.get('fps') is not None:
            if res:
                res += ', '
            res += '{}fps'.format(fdict['fps'])
        if fdict.get('acodec') is not None:
            if res:
                res += ', '
            if fdict['acodec'] == 'none':
                res += 'video only'
            else:
                res += '%-5s' % fdict['acodec']
        elif fdict.get('abr') is not None:
            if res:
                res += ', '
            res += 'audio'
        if fdict.get('abr') is not None:
            res += '@%3dk' % fdict['abr']
        if fdict.get('asr') is not None:
            res += ' (%5dHz)' % fdict['asr']
        if fdict.get('filesize') is not None:
            if res:
                res += ', '
            res += format_bytes(fdict['filesize'])
        elif fdict.get('filesize_approx') is not None:
            if res:
                res += ', '
            res += '~' + format_bytes(fdict['filesize_approx'])
        return res

    def _get_formats(self, info_dict):
        if info_dict.get('formats') is None:
            if info_dict.get('url') and info_dict.get('_type', 'video') == 'video':
                return [info_dict]
            return []
        return info_dict['formats']

    def render_formats_table(self, info_dict):
        formats = self._get_formats(info_dict)
        if not formats:
            return
        if not self.params.get('listformats_table', True) is not False:
            table = [
                [
                    format_field(f, 'format_id'),
                    format_field(f, 'ext'),
                    self.format_resolution(f),
                    self._format_note(f),
                ] for f in formats if (f.get('preference') or 0) >= -1000]
            return render_table(['format code', 'extension', 'resolution', 'note'], table, extra_gap=1)

        def simplified_codec(f, field):
            assert field in ('acodec', 'vcodec')
            codec = f.get(field)
            if not codec:
                return 'unknown'
            elif codec != 'none':
                return '.'.join(codec.split('.')[:4])

            if field == 'vcodec' and f.get('acodec') == 'none':
                return 'images'
            elif field == 'acodec' and f.get('vcodec') == 'none':
                return ''
            return self._format_out('audio only' if field == 'vcodec' else 'video only',
                                    self.Styles.SUPPRESS)

        delim = self._format_out('\u2502', self.Styles.DELIM, '|', test_encoding=True)
        table = [
            [
                self._format_out(format_field(f, 'format_id'), self.Styles.ID),
                format_field(f, 'ext'),
                format_field(f, func=self.format_resolution, ignore=('audio only', 'images')),
                format_field(f, 'fps', '\t%d', func=round),
                format_field(f, 'dynamic_range', '%s', ignore=(None, 'SDR')).replace('HDR', ''),
                format_field(f, 'audio_channels', '\t%s'),
                delim, (
                    format_field(f, 'filesize', ' \t%s', func=format_bytes)
                    or format_field(f, 'filesize_approx', '≈\t%s', func=format_bytes)
                    or format_field(filesize_from_tbr(f.get('tbr'), info_dict.get('duration')), None,
                                    self._format_out('~\t%s', self.Styles.SUPPRESS), func=format_bytes)),
                format_field(f, 'tbr', '\t%dk', func=round),
                shorten_protocol_name(f.get('protocol', '')),
                delim,
                simplified_codec(f, 'vcodec'),
                format_field(f, 'vbr', '\t%dk', func=round),
                simplified_codec(f, 'acodec'),
                format_field(f, 'abr', '\t%dk', func=round),
                format_field(f, 'asr', '\t%s', func=format_decimal_suffix),
                join_nonempty(format_field(f, 'language', '[%s]'), join_nonempty(
                    self._format_out('UNSUPPORTED', self.Styles.BAD_FORMAT) if f.get('ext') in ('f4f', 'f4m') else None,
                    (self._format_out('Maybe DRM', self.Styles.WARNING) if f.get('has_drm') == 'maybe'
                     else self._format_out('DRM', self.Styles.BAD_FORMAT) if f.get('has_drm') else None),
                    format_field(f, 'format_note'),
                    format_field(f, 'container', ignore=(None, f.get('ext'))),
                    delim=', '), delim=' '),
            ] for f in formats if f.get('preference') is None or f['preference'] >= -1000]
        header_line = self._list_format_headers(
            'ID', 'EXT', 'RESOLUTION', '\tFPS', 'HDR', 'CH', delim, '\tFILESIZE', '\tTBR', 'PROTO',
            delim, 'VCODEC', '\tVBR', 'ACODEC', '\tABR', '\tASR', 'MORE INFO')

        return render_table(
            header_line, table, hide_empty=True,
            delim=self._format_out('\u2500', self.Styles.DELIM, '-', test_encoding=True))

    def render_thumbnails_table(self, info_dict):
        thumbnails = list(info_dict.get('thumbnails') or [])
        if not thumbnails:
            return None
        return render_table(
            self._list_format_headers('ID', 'Width', 'Height', 'URL'),
            [[t.get('id'), t.get('width') or 'unknown', t.get('height') or 'unknown', t['url']] for t in thumbnails])

    def render_subtitles_table(self, video_id, subtitles):
        def _row(lang, formats):
            exts, names = zip(*((f['ext'], f.get('name') or 'unknown') for f in reversed(formats)))
            if len(set(names)) == 1:
                names = [] if names[0] == 'unknown' else names[:1]
            return [lang, ', '.join(names), ', '.join(exts)]

        if not subtitles:
            return None
        return render_table(
            self._list_format_headers('Language', 'Name', 'Formats'),
            [_row(lang, formats) for lang, formats in subtitles.items()],
            hide_empty=True)

    def __list_table(self, video_id, name, func, *args):
        table = func(*args)
        if not table:
            self.to_screen(f'{video_id} has no {name}')
            return
        self.to_screen(f'[info] Available {name} for {video_id}:')
        self.to_stdout(table)

    def list_formats(self, info_dict):
        self.__list_table(info_dict['id'], 'formats', self.render_formats_table, info_dict)

    def list_thumbnails(self, info_dict):
        self.__list_table(info_dict['id'], 'thumbnails', self.render_thumbnails_table, info_dict)

    def list_subtitles(self, video_id, subtitles, name='subtitles'):
        self.__list_table(video_id, name, self.render_subtitles_table, video_id, subtitles)

    def print_debug_header(self):
        if not self.params.get('verbose'):
            return

        from . import _IN_CLI  # Must be delayed import

        # These imports can be slow. So import them only as needed
        from .extractor.extractors import _LAZY_LOADER
        from .extractor.extractors import (
            _PLUGIN_CLASSES as plugin_ies,
            _PLUGIN_OVERRIDES as plugin_ie_overrides,
        )

        def get_encoding(stream):
            ret = str(getattr(stream, 'encoding', f'missing ({type(stream).__name__})'))
            additional_info = []
            if os.environ.get('TERM', '').lower() == 'dumb':
                additional_info.append('dumb')
            if not supports_terminal_sequences(stream):
                from .utils import WINDOWS_VT_MODE  # Must be imported locally
                additional_info.append('No VT' if WINDOWS_VT_MODE is False else 'No ANSI')
            if additional_info:
                ret = f'{ret} ({",".join(additional_info)})'
            return ret

        encoding_str = 'Encodings: locale {}, fs {}, pref {}, {}'.format(
            locale.getpreferredencoding(),
            sys.getfilesystemencoding(),
            self.get_encoding(),
            ', '.join(
                f'{key} {get_encoding(stream)}' for key, stream in self._out_files.items_
                if stream is not None and key != 'console'),
        )

        logger = self.params.get('logger')
        if logger:
            write_debug = lambda msg: logger.debug(f'[debug] {msg}')
            write_debug(encoding_str)
        else:
            write_string(f'[debug] {encoding_str}\n', encoding=None)
            write_debug = lambda msg: self._write_string(f'[debug] {msg}\n')

        source = detect_variant()
        if VARIANT not in (None, 'pip'):
            source += '*'
        klass = type(self)
        write_debug(join_nonempty(
            f'{REPOSITORY.rpartition("/")[2]} version',
            _make_label(ORIGIN, CHANNEL.partition('@')[2] or __version__, __version__),
            f'[{RELEASE_GIT_HEAD[:9]}]' if RELEASE_GIT_HEAD else '',
            '' if source == 'unknown' else f'({source})',
            '' if _IN_CLI else 'API' if klass == YoutubeDL else f'API:{self.__module__}.{klass.__qualname__}',
            delim=' '))

        if not _IN_CLI:
            write_debug(f'params: {self.params}')

        if not _LAZY_LOADER:
            if os.environ.get('YTDLP_NO_LAZY_EXTRACTORS'):
                write_debug('Lazy loading extractors is forcibly disabled')
            else:
                write_debug('Lazy loading extractors is disabled')
        if self.params['compat_opts']:
            write_debug('Compatibility options: {}'.format(', '.join(self.params['compat_opts'])))

        if current_git_head():
            write_debug(f'Git HEAD: {current_git_head()}')
        write_debug(system_identifier())

        exe_versions, ffmpeg_features = FFmpegPostProcessor.get_versions_and_features(self)
        ffmpeg_features = {key for key, val in ffmpeg_features.items() if val}
        if ffmpeg_features:
            exe_versions['ffmpeg'] += ' ({})'.format(','.join(sorted(ffmpeg_features)))

        exe_versions['rtmpdump'] = rtmpdump_version()
        exe_versions['phantomjs'] = PhantomJSwrapper._version()
        exe_str = ', '.join(
            f'{exe} {v}' for exe, v in sorted(exe_versions.items()) if v
        ) or 'none'
        write_debug(f'exe versions: {exe_str}')

        from .compat.compat_utils import get_package_info
        from .dependencies import available_dependencies

        write_debug('Optional libraries: %s' % (', '.join(sorted({
            join_nonempty(*get_package_info(m)) for m in available_dependencies.values()
        })) or 'none'))

        write_debug(f'Proxy map: {self.proxies}')
        write_debug(f'Request Handlers: {", ".join(rh.RH_NAME for rh in self._request_director.handlers.values())}')
        for plugin_type, plugins in {'Extractor': plugin_ies, 'Post-Processor': plugin_pps}.items():
            display_list = ['{}{}'.format(
                klass.__name__, '' if klass.__name__ == name else f' as {name}')
                for name, klass in plugins.items()]
            if plugin_type == 'Extractor':
                display_list.extend(f'{plugins[-1].IE_NAME.partition("+")[2]} ({parent.__name__})'
                                    for parent, plugins in plugin_ie_overrides.items())
            if not display_list:
                continue
            write_debug(f'{plugin_type} Plugins: {", ".join(sorted(display_list))}')

        plugin_dirs = plugin_directories()
        if plugin_dirs:
            write_debug(f'Plugin directories: {plugin_dirs}')

        # Not implemented
        if False and self.params.get('call_home'):
            ipaddr = self.urlopen('https://yt-dl.org/ip').read().decode()
            write_debug(f'Public IP address: {ipaddr}')
            latest_version = self.urlopen(
                'https://yt-dl.org/latest/version').read().decode()
            if version_tuple(latest_version) > version_tuple(__version__):
                self.report_warning(
                    f'You are using an outdated version (newest version: {latest_version})! '
                    'See https://yt-dl.org/update if you need help updating.')

    @functools.cached_property
    def proxies(self):
        """Global proxy configuration"""
        opts_proxy = self.params.get('proxy')
        if opts_proxy is not None:
            if opts_proxy == '':
                opts_proxy = '__noproxy__'
            proxies = {'all': opts_proxy}
        else:
            proxies = urllib.request.getproxies()
            # compat. Set HTTPS_PROXY to __noproxy__ to revert
            if 'http' in proxies and 'https' not in proxies:
                proxies['https'] = proxies['http']

        return proxies

    @functools.cached_property
    def cookiejar(self):
        """Global cookiejar instance"""
        try:
            return load_cookies(
                self.params.get('cookiefile'), self.params.get('cookiesfrombrowser'), self)
        except CookieLoadError as error:
            cause = error.__context__
            self.report_error(str(cause), tb=''.join(traceback.format_exception(cause)))
            raise

    @property
    def _opener(self):
        """
        Get a urllib OpenerDirector from the Urllib handler (deprecated).
        """
        self.deprecation_warning('YoutubeDL._opener is deprecated, use YoutubeDL.urlopen()')
        handler = self._request_director.handlers['Urllib']
        return handler._get_instance(cookiejar=self.cookiejar, proxies=self.proxies)

    def _get_available_impersonate_targets(self):
        # TODO(future): make available as public API
        return [
            (target, rh.RH_NAME)
            for rh in self._request_director.handlers.values()
            if isinstance(rh, ImpersonateRequestHandler)
            for target in rh.supported_targets
        ]

    def _impersonate_target_available(self, target):
        # TODO(future): make available as public API
        return any(
            rh.is_supported_target(target)
            for rh in self._request_director.handlers.values()
            if isinstance(rh, ImpersonateRequestHandler))

    def urlopen(self, req):
        """ Start an HTTP download """
        if isinstance(req, str):
            req = Request(req)
        elif isinstance(req, urllib.request.Request):
            self.deprecation_warning(
                'Passing a urllib.request.Request object to YoutubeDL.urlopen() is deprecated. '
                'Use yt_dlp.networking.common.Request instead.')
            req = urllib_req_to_req(req)
        assert isinstance(req, Request)

        # compat: Assume user:pass url params are basic auth
        url, basic_auth_header = extract_basic_auth(req.url)
        if basic_auth_header:
            req.headers['Authorization'] = basic_auth_header
        req.url = sanitize_url(url)

        clean_proxies(proxies=req.proxies, headers=req.headers)
        clean_headers(req.headers)

        try:
            return self._request_director.send(req)
        except NoSupportingHandlers as e:
            for ue in e.unsupported_errors:
                # FIXME: This depends on the order of errors.
                if not (ue.handler and ue.msg):
                    continue
                if ue.handler.RH_KEY == 'Urllib' and 'unsupported url scheme: "file"' in ue.msg.lower():
                    raise RequestError(
                        'file:// URLs are disabled by default in yt-dlp for security reasons. '
                        'Use --enable-file-urls to enable at your own risk.', cause=ue) from ue
                if (
                    'unsupported proxy type: "https"' in ue.msg.lower()
                    and 'requests' not in self._request_director.handlers
                    and 'curl_cffi' not in self._request_director.handlers
                ):
                    raise RequestError(
                        'To use an HTTPS proxy for this request, one of the following dependencies needs to be installed: requests, curl_cffi')

                elif (
                    re.match(r'unsupported url scheme: "wss?"', ue.msg.lower())
                    and 'websockets' not in self._request_director.handlers
                ):
                    raise RequestError(
                        'This request requires WebSocket support. '
                        'Ensure one of the following dependencies are installed: websockets',
                        cause=ue) from ue

                elif re.match(r'unsupported (?:extensions: impersonate|impersonate target)', ue.msg.lower()):
                    raise RequestError(
                        f'Impersonate target "{req.extensions["impersonate"]}" is not available.'
                        f' See --list-impersonate-targets for available targets.'
                        f' This request requires browser impersonation, however you may be missing dependencies'
                        f' required to support this target.')
            raise
        except SSLError as e:
            if 'UNSAFE_LEGACY_RENEGOTIATION_DISABLED' in str(e):
                raise RequestError('UNSAFE_LEGACY_RENEGOTIATION_DISABLED: Try using --legacy-server-connect', cause=e) from e
            elif 'SSLV3_ALERT_HANDSHAKE_FAILURE' in str(e):
                raise RequestError(
                    'SSLV3_ALERT_HANDSHAKE_FAILURE: The server may not support the current cipher list. '
                    'Try using --legacy-server-connect', cause=e) from e
            raise

    def build_request_director(self, handlers, preferences=None):
        logger = _YDLLogger(self)
        headers = self.params['http_headers'].copy()
        proxies = self.proxies.copy()
        clean_headers(headers)
        clean_proxies(proxies, headers)

        director = RequestDirector(logger=logger, verbose=self.params.get('debug_printtraffic'))
        for handler in handlers:
            director.add_handler(handler(
                logger=logger,
                headers=headers,
                cookiejar=self.cookiejar,
                proxies=proxies,
                prefer_system_certs='no-certifi' in self.params['compat_opts'],
                verify=not self.params.get('nocheckcertificate'),
                **traverse_obj(self.params, {
                    'verbose': 'debug_printtraffic',
                    'source_address': 'source_address',
                    'timeout': 'socket_timeout',
                    'legacy_ssl_support': 'legacyserverconnect',
                    'enable_file_urls': 'enable_file_urls',
                    'impersonate': 'impersonate',
                    'client_cert': {
                        'client_certificate': 'client_certificate',
                        'client_certificate_key': 'client_certificate_key',
                        'client_certificate_password': 'client_certificate_password',
                    },
                }),
            ))
        director.preferences.update(preferences or [])
        if 'prefer-legacy-http-handler' in self.params['compat_opts']:
            director.preferences.add(lambda rh, _: 500 if rh.RH_KEY == 'Urllib' else 0)
        return director

    @functools.cached_property
    def _request_director(self):
        return self.build_request_director(_REQUEST_HANDLERS.values(), _RH_PREFERENCES)

    def encode(self, s):
        if isinstance(s, bytes):
            return s  # Already encoded

        try:
            return s.encode(self.get_encoding())
        except UnicodeEncodeError as err:
            err.reason = err.reason + '. Check your system encoding configuration or use the --encoding option.'
            raise

    def get_encoding(self):
        encoding = self.params.get('encoding')
        if encoding is None:
            encoding = preferredencoding()
        return encoding

    def _write_info_json(self, label, ie_result, infofn, overwrite=None):
        """ Write infojson and returns True = written, 'exists' = Already exists, False = skip, None = error """
        if overwrite is None:
            overwrite = self.params.get('overwrites', True)
        if not self.params.get('writeinfojson'):
            return False
        elif not infofn:
            self.write_debug(f'Skipping writing {label} infojson')
            return False
        elif not self._ensure_dir_exists(infofn):
            return None
        elif not overwrite and os.path.exists(infofn):
            self.to_screen(f'[info] {label.title()} metadata is already present')
            return 'exists'

        self.to_screen(f'[info] Writing {label} metadata as JSON to: {infofn}')
        try:
            write_json_file(self.sanitize_info(ie_result, self.params.get('clean_infojson', True)), infofn)
            return True
        except OSError:
            self.report_error(f'Cannot write {label} metadata to JSON file {infofn}')
            return None

    def _write_description(self, label, ie_result, descfn):
        """ Write description and returns True = written, False = skip, None = error """
        if not self.params.get('writedescription'):
            return False
        elif not descfn:
            self.write_debug(f'Skipping writing {label} description')
            return False
        elif not self._ensure_dir_exists(descfn):
            return None
        elif not self.params.get('overwrites', True) and os.path.exists(descfn):
            self.to_screen(f'[info] {label.title()} description is already present')
        elif ie_result.get('description') is None:
            self.to_screen(f'[info] There\'s no {label} description to write')
            return False
        else:
            try:
                self.to_screen(f'[info] Writing {label} description to: {descfn}')
                with open(encodeFilename(descfn), 'w', encoding='utf-8') as descfile:
                    descfile.write(ie_result['description'])
            except OSError:
                self.report_error(f'Cannot write {label} description file {descfn}')
                return None
        return True

    def _write_subtitles(self, info_dict, filename):
        """ Write subtitles to file and return list of (sub_filename, final_sub_filename); or None if error"""
        ret = []
        subtitles = info_dict.get('requested_subtitles')
        if not (self.params.get('writesubtitles') or self.params.get('writeautomaticsub')):
            # subtitles download errors are already managed as troubles in relevant IE
            # that way it will silently go on when used with unsupporting IE
            return ret
        elif not subtitles:
            self.to_screen('[info] There are no subtitles for the requested languages')
            return ret
        sub_filename_base = self.prepare_filename(info_dict, 'subtitle')
        if not sub_filename_base:
            self.to_screen('[info] Skipping writing video subtitles')
            return ret

        for sub_lang, sub_info in subtitles.items():
            sub_format = sub_info['ext']
            sub_filename = subtitles_filename(filename, sub_lang, sub_format, info_dict.get('ext'))
            sub_filename_final = subtitles_filename(sub_filename_base, sub_lang, sub_format, info_dict.get('ext'))
            existing_sub = self.existing_file((sub_filename_final, sub_filename))
            if existing_sub:
                self.to_screen(f'[info] Video subtitle {sub_lang}.{sub_format} is already present')
                sub_info['filepath'] = existing_sub
                ret.append((existing_sub, sub_filename_final))
                continue

            self.to_screen(f'[info] Writing video subtitles to: {sub_filename}')
            if sub_info.get('data') is not None:
                try:
                    # Use newline='' to prevent conversion of newline characters
                    # See https://github.com/ytdl-org/youtube-dl/issues/10268
                    with open(sub_filename, 'w', encoding='utf-8', newline='') as subfile:
                        subfile.write(sub_info['data'])
                    sub_info['filepath'] = sub_filename
                    ret.append((sub_filename, sub_filename_final))
                    continue
                except OSError:
                    self.report_error(f'Cannot write video subtitles file {sub_filename}')
                    return None

            try:
                sub_copy = sub_info.copy()
                sub_copy.setdefault('http_headers', info_dict.get('http_headers'))
                self.dl(sub_filename, sub_copy, subtitle=True)
                sub_info['filepath'] = sub_filename
                ret.append((sub_filename, sub_filename_final))
            except (DownloadError, ExtractorError, OSError, ValueError, *network_exceptions) as err:
                msg = f'Unable to download video subtitles for {sub_lang!r}: {err}'
                if self.params.get('ignoreerrors') is not True:  # False or 'only_download'
                    if not self.params.get('ignoreerrors'):
                        self.report_error(msg)
                    raise DownloadError(msg)
                self.report_warning(msg)
        return ret

    def _write_thumbnails(self, label, info_dict, filename, thumb_filename_base=None):
        """ Write thumbnails to file and return list of (thumb_filename, final_thumb_filename); or None if error """
        write_all = self.params.get('write_all_thumbnails', False)
        thumbnails, ret = [], []
        if write_all or self.params.get('writethumbnail', False):
            thumbnails = info_dict.get('thumbnails') or []
            if not thumbnails:
                self.to_screen(f'[info] There are no {label} thumbnails to download')
                return ret
        multiple = write_all and len(thumbnails) > 1

        if thumb_filename_base is None:
            thumb_filename_base = filename
        if thumbnails and not thumb_filename_base:
            self.write_debug(f'Skipping writing {label} thumbnail')
            return ret

        if thumbnails and not self._ensure_dir_exists(filename):
            return None

        for idx, t in list(enumerate(thumbnails))[::-1]:
            thumb_ext = (f'{t["id"]}.' if multiple else '') + determine_ext(t['url'], 'jpg')
            thumb_display_id = f'{label} thumbnail {t["id"]}'
            thumb_filename = replace_extension(filename, thumb_ext, info_dict.get('ext'))
            thumb_filename_final = replace_extension(thumb_filename_base, thumb_ext, info_dict.get('ext'))

            existing_thumb = self.existing_file((thumb_filename_final, thumb_filename))
            if existing_thumb:
                self.to_screen('[info] {} is already present'.format((
                    thumb_display_id if multiple else f'{label} thumbnail').capitalize()))
                t['filepath'] = existing_thumb
                ret.append((existing_thumb, thumb_filename_final))
            else:
                self.to_screen(f'[info] Downloading {thumb_display_id} ...')
                try:
                    uf = self.urlopen(Request(t['url'], headers=t.get('http_headers', {})))
                    self.to_screen(f'[info] Writing {thumb_display_id} to: {thumb_filename}')
                    with open(encodeFilename(thumb_filename), 'wb') as thumbf:
                        shutil.copyfileobj(uf, thumbf)
                    ret.append((thumb_filename, thumb_filename_final))
                    t['filepath'] = thumb_filename
                except network_exceptions as err:
                    if isinstance(err, HTTPError) and err.status == 404:
                        self.to_screen(f'[info] {thumb_display_id.title()} does not exist')
                    else:
                        self.report_warning(f'Unable to download {thumb_display_id}: {err}')
                    thumbnails.pop(idx)
            if ret and not write_all:
                break
        return ret

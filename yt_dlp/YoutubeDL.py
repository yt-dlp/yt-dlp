#!/usr/bin/env python3
# coding: utf-8

from __future__ import absolute_import, unicode_literals

import collections
import contextlib
import datetime
import errno
import fileinput
import functools
import io
import itertools
import json
import locale
import operator
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize
import traceback
import random
import unicodedata

from enum import Enum
from string import ascii_letters

from .compat import (
    compat_basestring,
    compat_get_terminal_size,
    compat_kwargs,
    compat_numeric_types,
    compat_os_name,
    compat_pycrypto_AES,
    compat_shlex_quote,
    compat_str,
    compat_tokenize_tokenize,
    compat_urllib_error,
    compat_urllib_request,
    compat_urllib_request_DataHandler,
    windows_enable_vt_mode,
)
from .cookies import load_cookies
from .utils import (
    age_restricted,
    args_to_str,
    ContentTooShortError,
    date_from_str,
    DateRange,
    DEFAULT_OUTTMPL,
    determine_ext,
    determine_protocol,
    DownloadCancelled,
    DownloadError,
    encode_compat_str,
    encodeFilename,
    EntryNotInPlaylist,
    error_to_compat_str,
    ExistingVideoReached,
    expand_path,
    ExtractorError,
    float_or_none,
    format_bytes,
    format_field,
    format_decimal_suffix,
    formatSeconds,
    GeoRestrictedError,
    get_domain,
    HEADRequest,
    InAdvancePagedList,
    int_or_none,
    iri_to_uri,
    ISO3166Utils,
    join_nonempty,
    LazyList,
    LINK_TEMPLATES,
    locked_file,
    make_dir,
    make_HTTPS_handler,
    MaxDownloadsReached,
    network_exceptions,
    number_of_digits,
    orderedSet,
    OUTTMPL_TYPES,
    PagedList,
    parse_filesize,
    PerRequestProxyHandler,
    platform_name,
    Popen,
    POSTPROCESS_WHEN,
    PostProcessingError,
    preferredencoding,
    prepend_extension,
    ReExtractInfo,
    register_socks_protocols,
    RejectedVideoReached,
    remove_terminal_sequences,
    render_table,
    replace_extension,
    SameFileError,
    sanitize_filename,
    sanitize_path,
    sanitize_url,
    sanitized_Request,
    std_headers,
    STR_FORMAT_RE_TMPL,
    STR_FORMAT_TYPES,
    str_or_none,
    strftime_or_none,
    subtitles_filename,
    supports_terminal_sequences,
    timetuple_from_msec,
    to_high_limit_path,
    traverse_obj,
    try_get,
    UnavailableVideoError,
    url_basename,
    variadic,
    version_tuple,
    write_json_file,
    write_string,
    YoutubeDLCookieProcessor,
    YoutubeDLHandler,
    YoutubeDLRedirectHandler,
)
from .cache import Cache
from .minicurses import format_text
from .extractor import (
    gen_extractor_classes,
    get_info_extractor,
    _LAZY_LOADER,
    _PLUGIN_CLASSES as plugin_extractors
)
from .extractor.openload import PhantomJSwrapper
from .downloader import (
    FFmpegFD,
    get_suitable_downloader,
    shorten_protocol_name
)
from .downloader.rtmp import rtmpdump_version
from .postprocessor import (
    get_postprocessor,
    EmbedThumbnailPP,
    FFmpegFixupDuplicateMoovPP,
    FFmpegFixupDurationPP,
    FFmpegFixupM3u8PP,
    FFmpegFixupM4aPP,
    FFmpegFixupStretchedPP,
    FFmpegFixupTimestampPP,
    FFmpegMergerPP,
    FFmpegPostProcessor,
    MoveFilesAfterDownloadPP,
    _PLUGIN_CLASSES as plugin_postprocessors
)
from .update import detect_variant
from .version import __version__, RELEASE_GIT_HEAD

if compat_os_name == 'nt':
    import ctypes


class YoutubeDL(object):
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
    verbose:           Print additional info to stdout.
    quiet:             Do not print messages to stdout.
    no_warnings:       Do not print out anything for warnings.
    forceprint:        A dict with keys WHEN mapped to a list of templates to
                       print to stdout. The allowed keys are video or any of the
                       items in utils.POSTPROCESS_WHEN.
                       For compatibility, a single list is also accepted
    print_to_file:     A dict with keys WHEN (same as forceprint) mapped to
                       a list of tuples with (template, filename)
    forceurl:          Force printing final URL. (Deprecated)
    forcetitle:        Force printing title. (Deprecated)
    forceid:           Force printing ID. (Deprecated)
    forcethumbnail:    Force printing thumbnail URL. (Deprecated)
    forcedescription:  Force printing description. (Deprecated)
    forcefilename:     Force printing final filename. (Deprecated)
    forceduration:     Force printing duration. (Deprecated)
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
    allow_multiple_video_streams:   Allow multiple video streams to be merged
                       into a single file
    allow_multiple_audio_streams:   Allow multiple audio streams to be merged
                       into a single file
    check_formats      Whether to test if the formats are downloadable.
                       Can be True (check all), False (check none),
                       'selected' (check selected formats),
                       or None (check only if requested by extractor)
    paths:             Dictionary of output paths. The allowed keys are 'home'
                       'temp' and the keys of OUTTMPL_TYPES (in utils.py)
    outtmpl:           Dictionary of templates for output names. Allowed keys
                       are 'default' and the keys of OUTTMPL_TYPES (in utils.py).
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
    force_generic_extractor: Force downloader to use the generic extractor
    overwrites:        Overwrite all video and metadata files if True,
                       overwrite only non-video files if None
                       and don't overwrite any file if False
                       For compatibility with youtube-dl,
                       "nooverwrites" may also be used instead
    playliststart:     Playlist item to start at.
    playlistend:       Playlist item to end at.
    playlist_items:    Specific indices of playlist to download.
    playlistreverse:   Download playlist items in reverse order.
    playlistrandom:    Download playlist items in random order.
    matchtitle:        Download only matching titles.
    rejecttitle:       Reject downloads for matching titles.
    logger:            Log messages to a logging.Logger instance.
    logtostderr:       Log messages to stderr instead of stdout.
    consoletitle:       Display progress in console window's titlebar.
    writedescription:  Write the video description to a .description file
    writeinfojson:     Write the video description to a .info.json file
    clean_infojson:    Remove private fields from the infojson
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
    allsubtitles:      Deprecated - Use subtitleslangs = ['all']
                       Downloads all the subtitles of the video
                       (requires writesubtitles or writeautomaticsub)
    listsubtitles:     Lists all available subtitles for the video
    subtitlesformat:   The format code for subtitles
    subtitleslangs:    List of languages of the subtitles to download (can be regex).
                       The list may contain "all" to refer to all the available
                       subtitles. The language can be prefixed with a "-" to
                       exclude it from the requested languages. Eg: ['all', '-live_chat']
    keepvideo:         Keep the video file after post-processing
    daterange:         A DateRange object, download only if the upload_date is in the range.
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
    download_archive:  File name of a file where all downloads are recorded.
                       Videos already present in the file are not downloaded
                       again.
    break_on_existing: Stop the download process after attempting to download a
                       file that is in the archive.
    break_on_reject:   Stop the download process when encountering a video that
                       has been filtered out.
    break_per_url:     Whether break_on_reject and break_on_existing
                       should act on each input URL as opposed to for the entire queue
    cookiefile:        File name where cookies should be read from and dumped to
    cookiesfrombrowser:  A tuple containing the name of the browser, the profile
                       name/pathfrom where cookies are loaded, and the name of the
                       keyring. Eg: ('chrome', ) or ('vivaldi', 'default', 'BASICTEXT')
    legacyserverconnect: Explicitly allow HTTPS connection to servers that do not
                       support RFC 5746 secure renegotiation
    nocheckcertificate:  Do not verify SSL certificates
    prefer_insecure:   Use HTTP instead of HTTPS to retrieve information.
                       At the moment, this is only supported by YouTube.
    proxy:             URL of the proxy server to use
    geo_verification_proxy:  URL of the proxy to use for IP address verification
                       on geo-restricted sites.
    socket_timeout:    Time to wait for unresponsive hosts, in seconds
    bidi_workaround:   Work around buggy terminals without bidirectional text
                       support, using fridibi
    debug_printtraffic:Print out sent and received HTTP traffic
    include_ads:       Download ads as well (deprecated)
    default_search:    Prepend this string if an input url is not valid.
                       'auto' for elaborate guessing
    encoding:          Use this encoding instead of the system-specified.
    extract_flat:      Do not resolve URLs, return the immediate result.
                       Pass in 'in_playlist' to only show this behavior for
                       playlist items.
    wait_for_video:    If given, wait for scheduled streams to become available.
                       The value should be a tuple containing the range
                       (min_secs, max_secs) to wait between retries
    postprocessors:    A list of dictionaries, each with an entry
                       * key:  The name of the postprocessor. See
                               yt_dlp/postprocessor/__init__.py for a list.
                       * when: When to run the postprocessor. Allowed values are
                               the entries of utils.POSTPROCESS_WHEN
                               Assumed to be 'post_process' if not given
    post_hooks:        Deprecated - Register a custom postprocessor instead
                       A list of functions that get called as the final step
                       for each video file, after all postprocessors have been
                       called. The filename will be passed as the only argument.
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
    merge_output_format: Extension to use when merging formats.
    final_ext:         Expected final extension; used to detect when the file was
                       already downloaded and converted
    fixup:             Automatically correct known faults of the file.
                       One of:
                       - "never": do nothing
                       - "warn": only emit a warning
                       - "detect_or_warn": check whether we can do anything
                                           about it, warn otherwise (default)
    source_address:    Client-side IP address to bind to.
    call_home:         Boolean, true iff we are allowed to contact the
                       yt-dlp servers for debugging. (BROKEN)
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
    match_filter:      A function that gets called with the info_dict of
                       every video.
                       If it returns a message, the video is ignored.
                       If it returns None, the video is downloaded.
                       match_filter_func in utils.py is one example for this.
    no_color:          Do not emit color codes in output.
    geo_bypass:        Bypass geographic restriction via faking X-Forwarded-For
                       HTTP header
    geo_bypass_country:
                       Two-letter ISO 3166-2 country code that will be used for
                       explicit geographic restriction bypassing via faking
                       X-Forwarded-For HTTP header
    geo_bypass_ip_block:
                       IP range in CIDR notation that will be used similarly to
                       geo_bypass_country

    The following options determine which downloader is picked:
    external_downloader: A dictionary of protocol keys and the executable of the
                       external downloader to use for it. The allowed protocols
                       are default|http|ftp|m3u8|dash|rtsp|rtmp|mms.
                       Set the value to 'native' to use the native downloader
    hls_prefer_native: Deprecated - Use external_downloader = {'m3u8': 'native'}
                       or {'m3u8': 'ffmpeg'} instead.
                       Use the native HLS downloader instead of ffmpeg/avconv
                       if True, otherwise use ffmpeg/avconv if False, otherwise
                       use downloader suggested by extractor if None.
    compat_opts:       Compatibility options. See "Differences in default behavior".
                       The following options do not work when used through the API:
                       filename, abort-on-error, multistreams, no-live-chat, format-sort
                       no-clean-infojson, no-playlist-metafiles, no-keep-subs, no-attach-info-json.
                       Refer __init__.py for their implementation
    progress_template: Dictionary of templates for progress outputs.
                       Allowed keys are 'download', 'postprocess',
                       'download-title' (console title) and 'postprocess-title'.
                       The template is mapped on a dictionary with keys 'progress' and 'info'

    The following parameters are not used by YoutubeDL itself, they are used by
    the downloader (see yt_dlp/downloader/common.py):
    nopart, updatetime, buffersize, ratelimit, throttledratelimit, min_filesize,
    max_filesize, test, noresizebuffer, retries, file_access_retries, fragment_retries,
    continuedl, noprogress, xattr_set_filesize, hls_use_mpegts, http_chunk_size,
    external_downloader_args, concurrent_fragment_downloads.

    The following options are used by the post processors:
    prefer_ffmpeg:     If False, use avconv instead of ffmpeg if both are available,
                       otherwise prefer ffmpeg. (avconv support is deprecated)
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
    extractor_retries: Number of times to retry for known errors
    dynamic_mpd:       Whether to process dynamic DASH manifests (default: True)
    hls_split_discontinuity: Split HLS playlists to different formats at
                       discontinuities such as ad breaks (default: False)
    extractor_args:    A dictionary of arguments to be passed to the extractors.
                       See "EXTRACTOR ARGUMENTS" for details.
                       Eg: {'youtube': {'skip': ['dash', 'hls']}}
    mark_watched:      Mark videos watched (even with --simulate). Only for YouTube
    youtube_include_dash_manifest: Deprecated - Use extractor_args instead.
                       If True (default), DASH manifests and related
                       data will be downloaded and processed by extractor.
                       You can reduce network I/O by disabling it if you don't
                       care about DASH. (only for youtube)
    youtube_include_hls_manifest: Deprecated - Use extractor_args instead.
                       If True (default), HLS manifests and related
                       data will be downloaded and processed by extractor.
                       You can reduce network I/O by disabling it if you don't
                       care about HLS. (only for youtube)
    """

    _NUMERIC_FIELDS = set((
        'width', 'height', 'tbr', 'abr', 'asr', 'vbr', 'fps', 'filesize', 'filesize_approx',
        'timestamp', 'release_timestamp',
        'duration', 'view_count', 'like_count', 'dislike_count', 'repost_count',
        'average_rating', 'comment_count', 'age_limit',
        'start_time', 'end_time',
        'chapter_number', 'season_number', 'episode_number',
        'track_number', 'disc_number', 'release_year',
    ))

    _format_selection_exts = {
        'audio': {'m4a', 'mp3', 'ogg', 'aac'},
        'video': {'mp4', 'flv', 'webm', '3gp'},
        'storyboards': {'mhtml'},
    }

    params = None
    _ies = {}
    _pps = {k: [] for k in POSTPROCESS_WHEN}
    _printed_messages = set()
    _first_webpage_request = True
    _download_retcode = None
    _num_downloads = None
    _playlist_level = 0
    _playlist_urls = set()
    _screen_file = None

    def __init__(self, params=None, auto_init=True):
        """Create a FileDownloader object with the given options.
        @param auto_init    Whether to load the default extractors and print header (if verbose).
                            Set to 'no_verbose_header' to not print the header
        """
        if params is None:
            params = {}
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
        self._screen_file = [sys.stdout, sys.stderr][params.get('logtostderr', False)]
        self._err_file = sys.stderr
        self.params = params
        self.cache = Cache(self)

        windows_enable_vt_mode()
        self._allow_colors = {
            'screen': not self.params.get('no_color') and supports_terminal_sequences(self._screen_file),
            'err': not self.params.get('no_color') and supports_terminal_sequences(self._err_file),
        }

        if sys.version_info < (3, 6):
            self.report_warning(
                'Python version %d.%d is not supported! Please update to Python 3.6 or above' % sys.version_info[:2])

        if self.params.get('allow_unplayable_formats'):
            self.report_warning(
                f'You have asked for {self._format_err("UNPLAYABLE", self.Styles.EMPHASIS)} formats to be listed/downloaded. '
                'This is a developer option intended for debugging. \n'
                '         If you experience any issues while using this option, '
                f'{self._format_err("DO NOT", self.Styles.ERROR)} open a bug report')

        def check_deprecated(param, option, suggestion):
            if self.params.get(param) is not None:
                self.report_warning('%s is deprecated. Use %s instead' % (option, suggestion))
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
            self.deprecation_warning(msg)

        if 'list-formats' in self.params.get('compat_opts', []):
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

        self.params.setdefault('forceprint', {})
        self.params.setdefault('print_to_file', {})

        # Compatibility with older syntax
        if not isinstance(params['forceprint'], dict):
            self.params['forceprint'] = {'video': params['forceprint']}

        if self.params.get('bidi_workaround', False):
            try:
                import pty
                master, slave = pty.openpty()
                width = compat_get_terminal_size().columns
                if width is None:
                    width_args = []
                else:
                    width_args = ['-w', str(width)]
                sp_kwargs = dict(
                    stdin=subprocess.PIPE,
                    stdout=slave,
                    stderr=self._err_file)
                try:
                    self._output_process = Popen(['bidiv'] + width_args, **sp_kwargs)
                except OSError:
                    self._output_process = Popen(['fribidi', '-c', 'UTF-8'] + width_args, **sp_kwargs)
                self._output_channel = os.fdopen(master, 'rb')
            except OSError as ose:
                if ose.errno == errno.ENOENT:
                    self.report_warning(
                        'Could not find fribidi executable, ignoring --bidi-workaround. '
                        'Make sure that  fribidi  is an executable file in one of the directories in your $PATH.')
                else:
                    raise

        if (sys.platform != 'win32'
                and sys.getfilesystemencoding() in ['ascii', 'ANSI_X3.4-1968']
                and not self.params.get('restrictfilenames', False)):
            # Unicode filesystem API will throw errors (#1474, #13027)
            self.report_warning(
                'Assuming --restrict-filenames since file system encoding '
                'cannot encode all characters. '
                'Set the LC_ALL environment variable to fix this.')
            self.params['restrictfilenames'] = True

        self.outtmpl_dict = self.parse_outtmpl()

        # Creating format selector here allows us to catch syntax errors before the extraction
        self.format_selector = (
            self.params.get('format') if self.params.get('format') in (None, '-')
            else self.params['format'] if callable(self.params['format'])
            else self.build_format_selector(self.params['format']))

        self._setup_opener()

        if auto_init:
            if auto_init != 'no_verbose_header':
                self.print_debug_header()
            self.add_default_info_extractors()

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
                get_postprocessor(pp_def.pop('key'))(self, **compat_kwargs(pp_def)),
                when=when)

        register_socks_protocols()

        def preload_download_archive(fn):
            """Preload the archive, if any is specified"""
            if fn is None:
                return False
            self.write_debug(f'Loading archive file {fn!r}')
            try:
                with locked_file(fn, 'r', encoding='utf-8') as archive_file:
                    for line in archive_file:
                        self.archive.add(line.strip())
            except IOError as ioe:
                if ioe.errno != errno.ENOENT:
                    raise
                return False
            return True

        self.archive = set()
        preload_download_archive(self.params.get('download_archive'))

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
                'Use -- to separate parameters and URLs, like this:\n%s' %
                args_to_str(correct_argv))

    def add_info_extractor(self, ie):
        """Add an InfoExtractor object to the end of the list."""
        ie_key = ie.ie_key()
        self._ies[ie_key] = ie
        if not isinstance(ie, type):
            self._ies_instances[ie_key] = ie
            ie.set_downloader(self)

    def _get_info_extractor_class(self, ie_key):
        ie = self._ies.get(ie_key)
        if ie is None:
            ie = get_info_extractor(ie_key)
            self.add_info_extractor(ie)
        return ie

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
        for ie in gen_extractor_classes():
            self.add_info_extractor(ie)

    def add_post_processor(self, pp, when='post_process'):
        """Add a PostProcessor object to the end of the chain."""
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
        assert isinstance(message, compat_str)
        line_count = message.count('\n') + 1
        self._output_process.stdin.write((message + '\n').encode('utf-8'))
        self._output_process.stdin.flush()
        res = ''.join(self._output_channel.readline().decode('utf-8')
                      for _ in range(line_count))
        return res[:-len('\n')]

    def _write_string(self, message, out=None, only_once=False):
        if only_once:
            if message in self._printed_messages:
                return
            self._printed_messages.add(message)
        write_string(message, out=out, encoding=self.params.get('encoding'))

    def to_stdout(self, message, skip_eol=False, quiet=False):
        """Print message to stdout"""
        if self.params.get('logger'):
            self.params['logger'].debug(message)
        elif not quiet or self.params.get('verbose'):
            self._write_string(
                '%s%s' % (self._bidi_workaround(message), ('' if skip_eol else '\n')),
                self._err_file if quiet else self._screen_file)

    def to_stderr(self, message, only_once=False):
        """Print message to stderr"""
        assert isinstance(message, compat_str)
        if self.params.get('logger'):
            self.params['logger'].error(message)
        else:
            self._write_string('%s\n' % self._bidi_workaround(message), self._err_file, only_once=only_once)

    def to_console_title(self, message):
        if not self.params.get('consoletitle', False):
            return
        message = remove_terminal_sequences(message)
        if compat_os_name == 'nt':
            if ctypes.windll.kernel32.GetConsoleWindow():
                # c_wchar_p() might not be necessary if `message` is
                # already of type unicode()
                ctypes.windll.kernel32.SetConsoleTitleW(ctypes.c_wchar_p(message))
        elif 'TERM' in os.environ:
            self._write_string('\033]0;%s\007' % message, self._screen_file)

    def save_console_title(self):
        if not self.params.get('consoletitle', False):
            return
        if self.params.get('simulate'):
            return
        if compat_os_name != 'nt' and 'TERM' in os.environ:
            # Save the title on stack
            self._write_string('\033[22;0t', self._screen_file)

    def restore_console_title(self):
        if not self.params.get('consoletitle', False):
            return
        if self.params.get('simulate'):
            return
        if compat_os_name != 'nt' and 'TERM' in os.environ:
            # Restore the title from stack
            self._write_string('\033[23;0t', self._screen_file)

    def __enter__(self):
        self.save_console_title()
        return self

    def __exit__(self, *args):
        self.restore_console_title()

        if self.params.get('cookiefile') is not None:
            self.cookiejar.save(ignore_discard=True, ignore_expires=True)

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

    def to_screen(self, message, skip_eol=False):
        """Print message to stdout if not in quiet mode"""
        self.to_stdout(
            message, skip_eol, quiet=self.params.get('quiet', False))

    class Styles(Enum):
        HEADERS = 'yellow'
        EMPHASIS = 'light blue'
        ID = 'green'
        DELIM = 'blue'
        ERROR = 'red'
        WARNING = 'yellow'
        SUPPRESS = 'light black'

    def _format_text(self, handle, allow_colors, text, f, fallback=None, *, test_encoding=False):
        if test_encoding:
            original_text = text
            encoding = self.params.get('encoding') or getattr(handle, 'encoding', 'ascii')
            text = text.encode(encoding, 'ignore').decode(encoding)
            if fallback is not None and text != original_text:
                text = fallback
        if isinstance(f, self.Styles):
            f = f.value
        return format_text(text, f) if allow_colors else text if fallback is None else fallback

    def _format_screen(self, *args, **kwargs):
        return self._format_text(
            self._screen_file, self._allow_colors['screen'], *args, **kwargs)

    def _format_err(self, *args, **kwargs):
        return self._format_text(
            self._err_file, self._allow_colors['err'], *args, **kwargs)

    def report_warning(self, message, only_once=False):
        '''
        Print the message to stderr, it will be prefixed with 'WARNING:'
        If stderr is a tty file the 'WARNING:' will be colored
        '''
        if self.params.get('logger') is not None:
            self.params['logger'].warning(message)
        else:
            if self.params.get('no_warnings'):
                return
            self.to_stderr(f'{self._format_err("WARNING:", self.Styles.WARNING)} {message}', only_once)

    def deprecation_warning(self, message):
        if self.params.get('logger') is not None:
            self.params['logger'].warning('DeprecationWarning: {message}')
        else:
            self.to_stderr(f'{self._format_err("DeprecationWarning:", self.Styles.ERROR)} {message}', True)

    def report_error(self, message, *args, **kwargs):
        '''
        Do the same as trouble, but prefixes the message with 'ERROR:', colored
        in red if stderr is a tty file.
        '''
        self.trouble(f'{self._format_err("ERROR:", self.Styles.ERROR)} {message}', *args, **kwargs)

    def write_debug(self, message, only_once=False):
        '''Log debug message or Print message to stderr'''
        if not self.params.get('verbose', False):
            return
        message = '[debug] %s' % message
        if self.params.get('logger'):
            self.params['logger'].debug(message)
        else:
            self.to_stderr(message, only_once)

    def report_file_already_downloaded(self, file_name):
        """Report file has already been fully downloaded."""
        try:
            self.to_screen('[download] %s has already been downloaded' % file_name)
        except UnicodeEncodeError:
            self.to_screen('[download] The file has already been downloaded')

    def report_file_delete(self, file_name):
        """Report that existing file will be deleted."""
        try:
            self.to_screen('Deleting existing file %s' % file_name)
        except UnicodeEncodeError:
            self.to_screen('Deleting existing file')

    def raise_no_formats(self, info, forced=False):
        has_drm = info.get('__has_drm')
        msg = 'This video is DRM protected' if has_drm else 'No video formats found!'
        expected = self.params.get('ignore_no_formats_error')
        if forced or not expected:
            raise ExtractorError(msg, video_id=info['id'], ie=info['extractor'],
                                 expected=has_drm or expected)
        else:
            self.report_warning(msg)

    def parse_outtmpl(self):
        outtmpl_dict = self.params.get('outtmpl', {})
        if not isinstance(outtmpl_dict, dict):
            outtmpl_dict = {'default': outtmpl_dict}
        # Remove spaces in the default template
        if self.params.get('restrictfilenames'):
            sanitize = lambda x: x.replace(' - ', ' ').replace(' ', '-')
        else:
            sanitize = lambda x: x
        outtmpl_dict.update({
            k: sanitize(v) for k, v in DEFAULT_OUTTMPL.items()
            if outtmpl_dict.get(k) is None})
        for key, val in outtmpl_dict.items():
            if isinstance(val, bytes):
                self.report_warning(
                    'Parameter outtmpl is bytes, but should be a unicode string. '
                    'Put  from __future__ import unicode_literals  at the top of your code file or consider switching to Python 3.x.')
        return outtmpl_dict

    def get_output_path(self, dir_type='', filename=None):
        paths = self.params.get('paths', {})
        assert isinstance(paths, dict)
        path = os.path.join(
            expand_path(paths.get('home', '').strip()),
            expand_path(paths.get(dir_type, '').strip()) if dir_type else '',
            filename or '')

        # Temporary fix for #4787
        # 'Treat' all problem characters by passing filename through preferredencoding
        # to workaround encoding issues with subprocess on python2 @ Windows
        if sys.version_info < (3, 0) and sys.platform == 'win32':
            path = encodeFilename(path, True).decode(preferredencoding())
        return sanitize_path(path, force=self.params.get('windowsfilenames'))

    @staticmethod
    def _outtmpl_expandpath(outtmpl):
        # expand_path translates '%%' into '%' and '$$' into '$'
        # correspondingly that is not what we want since we need to keep
        # '%%' intact for template dict substitution step. Working around
        # with boundary-alike separator hack.
        sep = ''.join([random.choice(ascii_letters) for _ in range(32)])
        outtmpl = outtmpl.replace('%%', '%{0}%'.format(sep)).replace('$$', '${0}$'.format(sep))

        # outtmpl should be expand_path'ed before template dict substitution
        # because meta fields may contain env variables we don't want to
        # be expanded. For example, for outtmpl "%(title)s.%(ext)s" and
        # title "Hello $PATH", we don't want `$PATH` to be expanded.
        return expand_path(outtmpl).replace(sep, '')

    @staticmethod
    def escape_outtmpl(outtmpl):
        ''' Escape any remaining strings like %s, %abc% etc. '''
        return re.sub(
            STR_FORMAT_RE_TMPL.format('', '(?![%(\0])'),
            lambda mobj: ('' if mobj.group('has_key') else '%') + mobj.group(0),
            outtmpl)

    @classmethod
    def validate_outtmpl(cls, outtmpl):
        ''' @return None or Exception object '''
        outtmpl = re.sub(
            STR_FORMAT_RE_TMPL.format('[^)]*', '[ljqBUDS]'),
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
        for key in ('__original_infodict', '__postprocessors'):
            info_dict.pop(key, None)
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
        info_dict['autonumber'] = self.params.get('autonumber_start', 1) - 1 + self._num_downloads
        info_dict['video_autonumber'] = self._num_videos
        if info_dict.get('resolution') is None:
            info_dict['resolution'] = self.format_resolution(info_dict, default=None)

        # For fields playlist_index, playlist_autonumber and autonumber convert all occurrences
        # of %(field)s to %(field)0Nd for backward compatibility
        field_size_compat_map = {
            'playlist_index': number_of_digits(info_dict.get('_last_playlist_index') or 0),
            'playlist_autonumber': number_of_digits(info_dict.get('n_entries') or 0),
            'autonumber': self.params.get('autonumber_size') or 5,
        }

        TMPL_DICT = {}
        EXTERNAL_FORMAT_RE = re.compile(STR_FORMAT_RE_TMPL.format('[^)]*', f'[{STR_FORMAT_TYPES}ljqBUDS]'))
        MATH_FUNCTIONS = {
            '+': float.__add__,
            '-': float.__sub__,
        }
        # Field is of the form key1.key2...
        # where keys (except first) can be string, int or slice
        FIELD_RE = r'\w*(?:\.(?:\w+|{num}|{num}?(?::{num}?){{1,2}}))*'.format(num=r'(?:-?\d+)')
        MATH_FIELD_RE = r'''(?:{field}|{num})'''.format(field=FIELD_RE, num=r'-?\d+(?:.\d+)?')
        MATH_OPERATORS_RE = r'(?:%s)' % '|'.join(map(re.escape, MATH_FUNCTIONS.keys()))
        INTERNAL_FORMAT_RE = re.compile(r'''(?x)
            (?P<negate>-)?
            (?P<fields>{field})
            (?P<maths>(?:{math_op}{math_field})*)
            (?:>(?P<strf_format>.+?))?
            (?P<alternate>(?<!\\),[^|&)]+)?
            (?:&(?P<replacement>.*?))?
            (?:\|(?P<default>.*?))?
            $'''.format(field=FIELD_RE, math_op=MATH_OPERATORS_RE, math_field=MATH_FIELD_RE))

        def _traverse_infodict(k):
            k = k.split('.')
            if k[0] == '':
                k.pop(0)
            return traverse_obj(info_dict, k, is_user_input=True, traverse_string=True)

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

            return value

        na = self.params.get('outtmpl_na_placeholder', 'NA')

        def filename_sanitizer(key, value, restricted=self.params.get('restrictfilenames')):
            return sanitize_filename(str(value), restricted=restricted,
                                     is_id=re.search(r'(^|[_.])id(\.|$)', key))

        sanitizer = sanitize if callable(sanitize) else filename_sanitizer
        sanitize = bool(sanitize)

        def _dumpjson_default(obj):
            if isinstance(obj, (set, LazyList)):
                return list(obj)
            return repr(obj)

        def create_key(outer_mobj):
            if not outer_mobj.group('has_key'):
                return outer_mobj.group(0)
            key = outer_mobj.group('key')
            mobj = re.match(INTERNAL_FORMAT_RE, key)
            initial_field = mobj.group('fields') if mobj else ''
            value, replacement, default = None, None, na
            while mobj:
                mobj = mobj.groupdict()
                default = mobj['default'] if mobj['default'] is not None else default
                value = get_value(mobj)
                replacement = mobj['replacement']
                if value is None and mobj['alternate']:
                    mobj = re.match(INTERNAL_FORMAT_RE, mobj['alternate'][1:])
                else:
                    break

            fmt = outer_mobj.group('format')
            if fmt == 's' and value is not None and key in field_size_compat_map.keys():
                fmt = '0{:d}d'.format(field_size_compat_map[key])

            value = default if value is None else value if replacement is None else replacement

            flags = outer_mobj.group('conversion') or ''
            str_fmt = f'{fmt[:-1]}s'
            if fmt[-1] == 'l':  # list
                delim = '\n' if '#' in flags else ', '
                value, fmt = delim.join(map(str, variadic(value, allowed_types=(str, bytes)))), str_fmt
            elif fmt[-1] == 'j':  # json
                value, fmt = json.dumps(value, default=_dumpjson_default, indent=4 if '#' in flags else None), str_fmt
            elif fmt[-1] == 'q':  # quoted
                value = map(str, variadic(value) if '#' in flags else [value])
                value, fmt = ' '.join(map(compat_shlex_quote, value)), str_fmt
            elif fmt[-1] == 'B':  # bytes
                value = f'%{str_fmt}'.encode('utf-8') % str(value).encode('utf-8')
                value, fmt = value.decode('utf-8', 'ignore'), 's'
            elif fmt[-1] == 'U':  # unicode normalized
                value, fmt = unicodedata.normalize(
                    # "+" = compatibility equivalence, "#" = NFD
                    'NF%s%s' % ('K' if '+' in flags else '', 'D' if '#' in flags else 'C'),
                    value), str_fmt
            elif fmt[-1] == 'D':  # decimal suffix
                num_fmt, fmt = fmt[:-1].replace('#', ''), 's'
                value = format_decimal_suffix(value, f'%{num_fmt}f%s' if num_fmt else '%d%s',
                                              factor=1024 if '#' in flags else 1000)
            elif fmt[-1] == 'S':  # filename sanitization
                value, fmt = filename_sanitizer(initial_field, value, restricted='#' in flags), str_fmt
            elif fmt[-1] == 'c':
                if value:
                    value = str(value)[0]
                else:
                    fmt = str_fmt
            elif fmt[-1] not in 'rs':  # numeric
                value = float_or_none(value)
                if value is None:
                    value, fmt = default, 's'

            if sanitize:
                if fmt[-1] == 'r':
                    # If value is an object, sanitize might convert it to a string
                    # So we convert it to repr first
                    value, fmt = repr(value), str_fmt
                if fmt[-1] in 'csr':
                    value = sanitizer(initial_field, value)

            key = '%s\0%s' % (key.replace('%', '%\0'), outer_mobj.group('format'))
            TMPL_DICT[key] = value
            return '{prefix}%({key}){fmt}'.format(key=key, fmt=fmt, prefix=outer_mobj.group('prefix'))

        return EXTERNAL_FORMAT_RE.sub(create_key, outtmpl), TMPL_DICT

    def evaluate_outtmpl(self, outtmpl, info_dict, *args, **kwargs):
        outtmpl, info_dict = self.prepare_outtmpl(outtmpl, info_dict, *args, **kwargs)
        return self.escape_outtmpl(outtmpl) % info_dict

    def _prepare_filename(self, info_dict, tmpl_type='default'):
        try:
            outtmpl = self._outtmpl_expandpath(self.outtmpl_dict.get(tmpl_type, self.outtmpl_dict['default']))
            filename = self.evaluate_outtmpl(outtmpl, info_dict, True)
            if not filename:
                return None

            if tmpl_type in ('default', 'temp'):
                final_ext, ext = self.params.get('final_ext'), info_dict.get('ext')
                if final_ext and ext and final_ext != ext and filename.endswith(f'.{final_ext}'):
                    filename = replace_extension(filename, ext, final_ext)
            else:
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

    def prepare_filename(self, info_dict, dir_type='', warn=False):
        """Generate the output filename."""

        filename = self._prepare_filename(info_dict, dir_type or 'default')
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
        """ Returns None if the file should be downloaded """

        video_title = info_dict.get('title', info_dict.get('id', 'video'))

        def check_filter():
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
                dateRange = self.params.get('daterange', DateRange())
                if date not in dateRange:
                    return '%s upload date is not in range %s' % (date_from_str(date).isoformat(), dateRange)
            view_count = info_dict.get('view_count')
            if view_count is not None:
                min_views = self.params.get('min_views')
                if min_views is not None and view_count < min_views:
                    return 'Skipping %s, because it has not reached minimum view count (%d/%d)' % (video_title, view_count, min_views)
                max_views = self.params.get('max_views')
                if max_views is not None and view_count > max_views:
                    return 'Skipping %s, because it has exceeded the maximum view count (%d/%d)' % (video_title, view_count, max_views)
            if age_restricted(info_dict.get('age_limit'), self.params.get('age_limit')):
                return 'Skipping "%s" because it is age restricted' % video_title

            match_filter = self.params.get('match_filter')
            if match_filter is not None:
                try:
                    ret = match_filter(info_dict, incomplete=incomplete)
                except TypeError:
                    # For backward compatibility
                    ret = None if incomplete else match_filter(info_dict)
                if ret is not None:
                    return ret
            return None

        if self.in_download_archive(info_dict):
            reason = '%s has already been recorded in the archive' % video_title
            break_opt, break_err = 'break_on_existing', ExistingVideoReached
        else:
            reason = check_filter()
            break_opt, break_err = 'break_on_reject', RejectedVideoReached
        if reason is not None:
            if not silent:
                self.to_screen('[download] ' + reason)
            if self.params.get(break_opt, False):
                raise break_err()
        return reason

    @staticmethod
    def add_extra_info(info_dict, extra_info):
        '''Set the keys from extra_info in info dict if they are missing'''
        for key, value in extra_info.items():
            info_dict.setdefault(key, value)

    def extract_info(self, url, download=True, ie_key=None, extra_info=None,
                     process=True, force_generic_extractor=False):
        """
        Return a list with a dictionary for each video extracted.

        Arguments:
        url -- URL to extract

        Keyword arguments:
        download -- whether to download videos during extraction
        ie_key -- extractor key hint
        extra_info -- dictionary containing the extra values to add to each result
        process -- whether to resolve all unresolved references (URLs, playlist items),
            must be True for download to work.
        force_generic_extractor -- force using the generic extractor
        """

        if extra_info is None:
            extra_info = {}

        if not ie_key and force_generic_extractor:
            ie_key = 'Generic'

        if ie_key:
            ies = {ie_key: self._get_info_extractor_class(ie_key)}
        else:
            ies = self._ies

        for ie_key, ie in ies.items():
            if not ie.suitable(url):
                continue

            if not ie.working():
                self.report_warning('The program functionality for this site has been marked as broken, '
                                    'and will probably not work.')

            temp_id = ie.get_temp_id(url)
            if temp_id is not None and self.in_download_archive({'id': temp_id, 'ie_key': ie_key}):
                self.to_screen(f'[{ie_key}] {temp_id}: has already been recorded in the archive')
                if self.params.get('break_on_existing', False):
                    raise ExistingVideoReached()
                break
            return self.__extract_info(url, self.get_info_extractor(ie_key), download, extra_info, process)
        else:
            self.report_error('no suitable InfoExtractor for URL %s' % url)

    def __handle_extraction_exceptions(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            while True:
                try:
                    return func(self, *args, **kwargs)
                except (DownloadCancelled, LazyList.IndexError, PagedList.IndexError):
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
                        msg += '\nThis video is available in %s.' % ', '.join(
                            map(ISO3166Utils.short2full, e.countries))
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

    def _wait_for_video(self, ie_result):
        if (not self.params.get('wait_for_video')
                or ie_result.get('_type', 'video') != 'video'
                or ie_result.get('formats') or ie_result.get('url')):
            return

        format_dur = lambda dur: '%02d:%02d:%02d' % timetuple_from_msec(dur * 1000)[:-1]
        last_msg = ''

        def progress(msg):
            nonlocal last_msg
            self.to_screen(msg + ' ' * (len(last_msg) - len(msg)) + '\r', skip_eol=True)
            last_msg = msg

        min_wait, max_wait = self.params.get('wait_for_video')
        diff = try_get(ie_result, lambda x: x['release_timestamp'] - time.time())
        if diff is None and ie_result.get('live_status') == 'is_upcoming':
            diff = random.randrange(min_wait, max_wait) if (max_wait and min_wait) else (max_wait or min_wait)
            self.report_warning('Release time of video is not known')
        elif (diff or 0) <= 0:
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

    @__handle_extraction_exceptions
    def __extract_info(self, url, ie, download, extra_info, process):
        ie_result = ie.extract(url)
        if ie_result is None:  # Finished already (backwards compatibility; listformats and friends should be moved here)
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
                'webpage_url_basename': url_basename(url),
                'webpage_url_domain': get_domain(url),
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
            ie_result['url'] = sanitize_url(ie_result['url'])
            if ie_result.get('original_url'):
                extra_info.setdefault('original_url', ie_result['original_url'])

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
                self.__forced_printings(info_copy, self.prepare_filename(info_copy), incomplete=True)
                if self.params.get('force_write_download_archive', False):
                    self.record_download_archive(info_copy)
                return ie_result

        if result_type == 'video':
            self.add_extra_info(ie_result, extra_info)
            ie_result = self.process_video_result(ie_result, download=download)
            additional_urls = (ie_result or {}).get('additional_urls')
            if additional_urls:
                # TODO: Improve MetadataParserPP to allow setting a list
                if isinstance(additional_urls, compat_str):
                    additional_urls = [additional_urls]
                self.to_screen(
                    '[info] %s: %d additional URL(s) requested' % (ie_result['id'], len(additional_urls)))
                self.write_debug('Additional URLs: "%s"' % '", "'.join(additional_urls))
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

            force_properties = dict(
                (k, v) for k, v in ie_result.items() if v is not None)
            for f in ('_type', 'url', 'id', 'extractor', 'extractor_key', 'ie_key'):
                if f in force_properties:
                    del force_properties[f]
            new_result = info.copy()
            new_result.update(force_properties)

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
            webpage_url = ie_result['webpage_url']
            if webpage_url in self._playlist_urls:
                self.to_screen(
                    '[download] Skipping already downloaded playlist: %s'
                    % ie_result.get('title') or ie_result.get('id'))
                return

            self._playlist_level += 1
            self._playlist_urls.add(webpage_url)
            self._sanitize_thumbnails(ie_result)
            try:
                return self.__process_playlist(ie_result, download)
            finally:
                self._playlist_level -= 1
                if not self._playlist_level:
                    self._playlist_urls.clear()
        elif result_type == 'compat_list':
            self.report_warning(
                'Extractor %s returned a compat_list result. '
                'It needs to be updated.' % ie_result.get('extractor'))

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
            raise Exception('Invalid result type: %s' % result_type)

    def _ensure_dir_exists(self, path):
        return make_dir(path, self.report_error)

    @staticmethod
    def _playlist_infodict(ie_result, **kwargs):
        return {
            **ie_result,
            'playlist': ie_result.get('title') or ie_result.get('id'),
            'playlist_id': ie_result.get('id'),
            'playlist_title': ie_result.get('title'),
            'playlist_uploader': ie_result.get('uploader'),
            'playlist_uploader_id': ie_result.get('uploader_id'),
            'playlist_index': 0,
            **kwargs,
        }

    def __process_playlist(self, ie_result, download):
        # We process each entry in the playlist
        playlist = ie_result.get('title') or ie_result.get('id')
        self.to_screen('[download] Downloading playlist: %s' % playlist)

        if 'entries' not in ie_result:
            raise EntryNotInPlaylist('There are no entries')

        MissingEntry = object()
        incomplete_entries = bool(ie_result.get('requested_entries'))
        if incomplete_entries:
            def fill_missing_entries(entries, indices):
                ret = [MissingEntry] * max(indices)
                for i, entry in zip(indices, entries):
                    ret[i - 1] = entry
                return ret
            ie_result['entries'] = fill_missing_entries(ie_result['entries'], ie_result['requested_entries'])

        playlist_results = []

        playliststart = self.params.get('playliststart', 1)
        playlistend = self.params.get('playlistend')
        # For backwards compatibility, interpret -1 as whole list
        if playlistend == -1:
            playlistend = None

        playlistitems_str = self.params.get('playlist_items')
        playlistitems = None
        if playlistitems_str is not None:
            def iter_playlistitems(format):
                for string_segment in format.split(','):
                    if '-' in string_segment:
                        start, end = string_segment.split('-')
                        for item in range(int(start), int(end) + 1):
                            yield int(item)
                    else:
                        yield int(string_segment)
            playlistitems = orderedSet(iter_playlistitems(playlistitems_str))

        ie_entries = ie_result['entries']
        if isinstance(ie_entries, list):
            playlist_count = len(ie_entries)
            msg = f'Collected {playlist_count} videos; downloading %d of them'
            ie_result['playlist_count'] = ie_result.get('playlist_count') or playlist_count

            def get_entry(i):
                return ie_entries[i - 1]
        else:
            msg = 'Downloading %d videos'
            if not isinstance(ie_entries, (PagedList, LazyList)):
                ie_entries = LazyList(ie_entries)
            elif isinstance(ie_entries, InAdvancePagedList):
                if ie_entries._pagesize == 1:
                    playlist_count = ie_entries._pagecount

            def get_entry(i):
                return YoutubeDL.__handle_extraction_exceptions(
                    lambda self, i: ie_entries[i - 1]
                )(self, i)

        entries, broken = [], False
        items = playlistitems if playlistitems is not None else itertools.count(playliststart)
        for i in items:
            if i == 0:
                continue
            if playlistitems is None and playlistend is not None and playlistend < i:
                break
            entry = None
            try:
                entry = get_entry(i)
                if entry is MissingEntry:
                    raise EntryNotInPlaylist()
            except (IndexError, EntryNotInPlaylist):
                if incomplete_entries:
                    raise EntryNotInPlaylist(f'Entry {i} cannot be found')
                elif not playlistitems:
                    break
            entries.append(entry)
            try:
                if entry is not None:
                    self._match_entry(entry, incomplete=True, silent=True)
            except (ExistingVideoReached, RejectedVideoReached):
                broken = True
                break
        ie_result['entries'] = entries

        # Save playlist_index before re-ordering
        entries = [
            ((playlistitems[i - 1] if playlistitems else i + playliststart - 1), entry)
            for i, entry in enumerate(entries, 1)
            if entry is not None]
        n_entries = len(entries)

        if not (ie_result.get('playlist_count') or broken or playlistitems or playlistend):
            ie_result['playlist_count'] = n_entries

        if not playlistitems and (playliststart != 1 or playlistend):
            playlistitems = list(range(playliststart, playliststart + n_entries))
        ie_result['requested_entries'] = playlistitems

        _infojson_written = False
        write_playlist_files = self.params.get('allow_playlist_files', True)
        if write_playlist_files and self.params.get('list_thumbnails'):
            self.list_thumbnails(ie_result)
        if write_playlist_files and not self.params.get('simulate'):
            ie_copy = self._playlist_infodict(ie_result, n_entries=n_entries)
            _infojson_written = self._write_info_json(
                'playlist', ie_result, self.prepare_filename(ie_copy, 'pl_infojson'))
            if _infojson_written is None:
                return
            if self._write_description('playlist', ie_result,
                                       self.prepare_filename(ie_copy, 'pl_description')) is None:
                return
            # TODO: This should be passed to ThumbnailsConvertor if necessary
            self._write_thumbnails('playlist', ie_copy, self.prepare_filename(ie_copy, 'pl_thumbnail'))

        if self.params.get('playlistreverse', False):
            entries = entries[::-1]
        if self.params.get('playlistrandom', False):
            random.shuffle(entries)

        x_forwarded_for = ie_result.get('__x_forwarded_for_ip')

        self.to_screen('[%s] playlist %s: %s' % (ie_result['extractor'], playlist, msg % n_entries))
        failures = 0
        max_failures = self.params.get('skip_playlist_after_errors') or float('inf')
        for i, entry_tuple in enumerate(entries, 1):
            playlist_index, entry = entry_tuple
            if 'playlist-index' in self.params.get('compat_opts', []):
                playlist_index = playlistitems[i - 1] if playlistitems else i + playliststart - 1
            self.to_screen('[download] Downloading video %s of %s' % (i, n_entries))
            # This __x_forwarded_for_ip thing is a bit ugly but requires
            # minimal changes
            if x_forwarded_for:
                entry['__x_forwarded_for_ip'] = x_forwarded_for
            extra = {
                'n_entries': n_entries,
                '_last_playlist_index': max(playlistitems) if playlistitems else (playlistend or n_entries),
                'playlist_count': ie_result.get('playlist_count'),
                'playlist_index': playlist_index,
                'playlist_autonumber': i,
                'playlist': playlist,
                'playlist_id': ie_result.get('id'),
                'playlist_title': ie_result.get('title'),
                'playlist_uploader': ie_result.get('uploader'),
                'playlist_uploader_id': ie_result.get('uploader_id'),
                'extractor': ie_result['extractor'],
                'webpage_url': ie_result['webpage_url'],
                'webpage_url_basename': url_basename(ie_result['webpage_url']),
                'webpage_url_domain': get_domain(ie_result['webpage_url']),
                'extractor_key': ie_result['extractor_key'],
            }

            if self._match_entry(entry, incomplete=True) is not None:
                continue

            entry_result = self.__process_iterable_entry(entry, download, extra)
            if not entry_result:
                failures += 1
            if failures >= max_failures:
                self.report_error(
                    'Skipping the remaining entries in playlist "%s" since %d items failed extraction' % (playlist, failures))
                break
            playlist_results.append(entry_result)
        ie_result['entries'] = playlist_results

        # Write the updated info to json
        if _infojson_written and self._write_info_json(
                'updated playlist', ie_result,
                self.prepare_filename(ie_copy, 'pl_infojson'), overwrite=True) is None:
            return

        ie_result = self.run_all_pps('playlist', ie_result)
        self.to_screen(f'[download] Finished downloading playlist: {playlist}')
        return ie_result

    @__handle_extraction_exceptions
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
            (?P<key>width|height|tbr|abr|vbr|asr|filesize|filesize_approx|fps)\s*
            (?P<op>%s)(?P<none_inclusive>\s*\?)?\s*
            (?P<value>[0-9.]+(?:[kKmMgGtTpPeEzZyY]i?[Bb]?)?)\s*
            ''' % '|'.join(map(re.escape, OPERATORS.keys())))
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
                        'Invalid value %r in format specification %r' % (
                            m.group('value'), filter_spec))
            op = OPERATORS[m.group('op')]

        if not m:
            STR_OPERATORS = {
                '=': operator.eq,
                '^=': lambda attr, value: attr.startswith(value),
                '$=': lambda attr, value: attr.endswith(value),
                '*=': lambda attr, value: value in attr,
            }
            str_operator_rex = re.compile(r'''(?x)\s*
                (?P<key>[a-zA-Z0-9._-]+)\s*
                (?P<negation>!\s*)?(?P<op>%s)(?P<none_inclusive>\s*\?)?\s*
                (?P<value>[a-zA-Z0-9._-]+)\s*
                ''' % '|'.join(map(re.escape, STR_OPERATORS.keys())))
            m = str_operator_rex.fullmatch(filter_spec)
            if m:
                comparison_value = m.group('value')
                str_op = STR_OPERATORS[m.group('op')]
                if m.group('negation'):
                    op = lambda attr, value: not str_op(attr, value)
                else:
                    op = str_op

        if not m:
            raise SyntaxError('Invalid filter specification %r' % filter_spec)

        def _filter(f):
            actual_value = f.get(m.group('key'))
            if actual_value is None:
                return m.group('none_inclusive')
            return op(actual_value, comparison_value)
        return _filter

    def _check_formats(self, formats):
        for f in formats:
            self.to_screen('[info] Testing format %s' % f['format_id'])
            path = self.get_output_path('temp')
            if not self._ensure_dir_exists(f'{path}/'):
                continue
            temp_file = tempfile.NamedTemporaryFile(suffix='.tmp', delete=False, dir=path or None)
            temp_file.close()
            try:
                success, _ = self.dl(temp_file.name, f, test=True)
            except (DownloadError, IOError, OSError, ValueError) + network_exceptions:
                success = False
            finally:
                if os.path.exists(temp_file.name):
                    try:
                        os.remove(temp_file.name)
                    except OSError:
                        self.report_warning('Unable to delete temporary file "%s"' % temp_file.name)
            if success:
                yield f
            else:
                self.to_screen('[info] Unable to download format %s. Skipping...' % f['format_id'])

    def _default_format_spec(self, info_dict, download=True):

        def can_merge():
            merger = FFmpegMergerPP(self)
            return merger.available and merger.can_merge()

        prefer_best = (
            not self.params.get('simulate')
            and download
            and (
                not can_merge()
                or info_dict.get('is_live', False)
                or self.outtmpl_dict['default'] == '-'))
        compat = (
            prefer_best
            or self.params.get('allow_multiple_audio_streams', False)
            or 'format-spec' in self.params.get('compat_opts', []))

        return (
            'best/bestvideo+bestaudio' if prefer_best
            else 'bestvideo*+bestaudio/best' if not compat
            else 'bestvideo+bestaudio/best')

    def build_format_selector(self, format_spec):
        def syntax_error(note, start):
            message = (
                'Invalid format specification: '
                '{0}\n\t{1}\n\t{2}^'.format(note, format_spec, ' ' * start[1]))
            return SyntaxError(message)

        PICKFIRST = 'PICKFIRST'
        MERGE = 'MERGE'
        SINGLE = 'SINGLE'
        GROUP = 'GROUP'
        FormatSelector = collections.namedtuple('FormatSelector', ['type', 'selector', 'filters'])

        allow_multiple_streams = {'audio': self.params.get('allow_multiple_audio_streams', False),
                                  'video': self.params.get('allow_multiple_video_streams', False)}

        check_formats = self.params.get('check_formats') == 'selected'

        def _parse_filter(tokens):
            filter_parts = []
            for type, string, start, _, _ in tokens:
                if type == tokenize.OP and string == ']':
                    return ''.join(filter_parts)
                else:
                    filter_parts.append(string)

        def _remove_unused_ops(tokens):
            # Remove operators that we don't use and join them with the surrounding strings
            # for example: 'mp4' '-' 'baseline' '-' '16x9' is converted to 'mp4-baseline-16x9'
            ALLOWED_OPS = ('/', '+', ',', '(', ')')
            last_string, last_start, last_end, last_line = None, None, None, None
            for type, string, start, end, line in tokens:
                if type == tokenize.OP and string == '[':
                    if last_string:
                        yield tokenize.NAME, last_string, last_start, last_end, last_line
                        last_string = None
                    yield type, string, start, end, line
                    # everything inside brackets will be handled by _parse_filter
                    for type, string, start, end, line in tokens:
                        yield type, string, start, end, line
                        if type == tokenize.OP and string == ']':
                            break
                elif type == tokenize.OP and string in ALLOWED_OPS:
                    if last_string:
                        yield tokenize.NAME, last_string, last_start, last_end, last_line
                        last_string = None
                    yield type, string, start, end, line
                elif type in [tokenize.NAME, tokenize.NUMBER, tokenize.OP]:
                    if not last_string:
                        last_string = string
                        last_start = start
                        last_end = end
                    else:
                        last_string += string
            if last_string:
                yield tokenize.NAME, last_string, last_start, last_end, last_line

        def _parse_format_selection(tokens, inside_merge=False, inside_choice=False, inside_group=False):
            selectors = []
            current_selector = None
            for type, string, start, _, _ in tokens:
                # ENCODING is only defined in python 3.x
                if type == getattr(tokenize, 'ENCODING', None):
                    continue
                elif type in [tokenize.NAME, tokenize.NUMBER]:
                    current_selector = FormatSelector(SINGLE, string, [])
                elif type == tokenize.OP:
                    if string == ')':
                        if not inside_group:
                            # ')' will be handled by the parentheses group
                            tokens.restore_last_token()
                        break
                    elif inside_merge and string in ['/', ',']:
                        tokens.restore_last_token()
                        break
                    elif inside_choice and string == ',':
                        tokens.restore_last_token()
                        break
                    elif string == ',':
                        if not current_selector:
                            raise syntax_error('"," must follow a format selector', start)
                        selectors.append(current_selector)
                        current_selector = None
                    elif string == '/':
                        if not current_selector:
                            raise syntax_error('"/" must follow a format selector', start)
                        first_choice = current_selector
                        second_choice = _parse_format_selection(tokens, inside_choice=True)
                        current_selector = FormatSelector(PICKFIRST, (first_choice, second_choice), [])
                    elif string == '[':
                        if not current_selector:
                            current_selector = FormatSelector(SINGLE, 'best', [])
                        format_filter = _parse_filter(tokens)
                        current_selector.filters.append(format_filter)
                    elif string == '(':
                        if current_selector:
                            raise syntax_error('Unexpected "("', start)
                        group = _parse_format_selection(tokens, inside_group=True)
                        current_selector = FormatSelector(GROUP, group, [])
                    elif string == '+':
                        if not current_selector:
                            raise syntax_error('Unexpected "+"', start)
                        selector_1 = current_selector
                        selector_2 = _parse_format_selection(tokens, inside_merge=True)
                        if not selector_2:
                            raise syntax_error('Expected a selector', start)
                        current_selector = FormatSelector(MERGE, (selector_1, selector_2), [])
                    else:
                        raise syntax_error('Operator not recognized: "{0}"'.format(string), start)
                elif type == tokenize.ENDMARKER:
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

            output_ext = self.params.get('merge_output_format')
            if not output_ext:
                if the_only_video:
                    output_ext = the_only_video['ext']
                elif the_only_audio and not video_fmts:
                    output_ext = the_only_audio['ext']
                else:
                    output_ext = 'mkv'

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
                })

            if the_only_audio:
                new_dict.update({
                    'acodec': the_only_audio.get('acodec'),
                    'abr': the_only_audio.get('abr'),
                    'asr': the_only_audio.get('asr'),
                })

            return new_dict

        def _check_formats(formats):
            if not check_formats:
                yield from formats
                return
            yield from self._check_formats(formats)

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
                        formats = list(_check_formats(ctx['formats']))
                        if not formats:
                            return
                        merged_format = formats[-1]
                        for f in formats[-2::-1]:
                            merged_format = _merge((merged_format, f))
                        yield merged_format

                else:
                    format_fallback, format_reverse, format_idx = False, True, 1
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
                            (lambda f: f.get('%scodec' % format_type) != 'none')
                            if format_type and format_modified  # bv*, ba*, wv*, wa*
                            else (lambda f: f.get('%scodec' % not_format_type) == 'none')
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
                        elif format_spec in self._format_selection_exts['storyboards']:
                            filter_f = lambda f: f.get('ext') == format_spec and f.get('acodec') == 'none' and f.get('vcodec') == 'none'
                        else:
                            filter_f = lambda f: f.get('format_id') == format_spec  # id

                    def selector_function(ctx):
                        formats = list(ctx['formats'])
                        matches = list(filter(filter_f, formats)) if filter_f is not None else formats
                        if format_fallback and ctx['incomplete_formats'] and not matches:
                            # for extractors with incomplete formats (audio only (soundcloud)
                            # or video only (imgur)) best/worst will fallback to
                            # best/worst {video,audio}-only format
                            matches = formats
                        matches = LazyList(_check_formats(matches[::-1 if format_reverse else 1]))
                        try:
                            yield matches[format_idx - 1]
                        except IndexError:
                            return

            filters = [self._build_format_filter(f) for f in selector.filters]

            def final_selector(ctx):
                ctx_copy = dict(ctx)
                for _filter in filters:
                    ctx_copy['formats'] = list(filter(_filter, ctx_copy['formats']))
                return selector_function(ctx_copy)
            return final_selector

        stream = io.BytesIO(format_spec.encode('utf-8'))
        try:
            tokens = list(_remove_unused_ops(compat_tokenize_tokenize(stream.readline)))
        except tokenize.TokenError:
            raise syntax_error('Missing closing/opening brackets or parenthesis', (0, len(format_spec)))

        class TokenIterator(object):
            def __init__(self, tokens):
                self.tokens = tokens
                self.counter = 0

            def __iter__(self):
                return self

            def __next__(self):
                if self.counter >= len(self.tokens):
                    raise StopIteration()
                value = self.tokens[self.counter]
                self.counter += 1
                return value

            next = __next__

            def restore_last_token(self):
                self.counter -= 1

        parsed_selector = _parse_format_selection(iter(TokenIterator(tokens)))
        return _build_selector_function(parsed_selector)

    def _calc_headers(self, info_dict):
        res = std_headers.copy()
        res.update(info_dict.get('http_headers') or {})

        cookies = self._calc_cookies(info_dict)
        if cookies:
            res['Cookie'] = cookies

        if 'X-Forwarded-For' not in res:
            x_forwarded_for_ip = info_dict.get('__x_forwarded_for_ip')
            if x_forwarded_for_ip:
                res['X-Forwarded-For'] = x_forwarded_for_ip

        return res

    def _calc_cookies(self, info_dict):
        pr = sanitized_Request(info_dict['url'])
        self.cookiejar.add_cookie_header(pr)
        return pr.get_header('Cookie')

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
                t['id'] = '%d' % i
            if t.get('width') and t.get('height'):
                t['resolution'] = '%dx%d' % (t['width'], t['height'])
            t['url'] = sanitize_url(t['url'])

        if self.params.get('check_formats') is True:
            info_dict['thumbnails'] = LazyList(check_thumbnails(thumbnails[::-1]), reverse=True)
        else:
            info_dict['thumbnails'] = thumbnails

    def process_video_result(self, info_dict, download=True):
        assert info_dict.get('_type', 'video') == 'video'
        self._num_videos += 1

        if 'id' not in info_dict:
            raise ExtractorError('Missing "id" field in extractor result', ie=info_dict['extractor'])
        elif not info_dict.get('id'):
            raise ExtractorError('Extractor failed to obtain "id"', ie=info_dict['extractor'])

        info_dict['fulltitle'] = info_dict.get('title')
        if 'title' not in info_dict:
            raise ExtractorError('Missing "title" field in extractor result',
                                 video_id=info_dict['id'], ie=info_dict['extractor'])
        elif not info_dict.get('title'):
            self.report_warning('Extractor failed to obtain "title". Creating a generic title instead')
            info_dict['title'] = f'{info_dict["extractor"]} video #{info_dict["id"]}'

        def report_force_conversion(field, field_not, conversion):
            self.report_warning(
                '"%s" field is not %s - forcing %s conversion, there is an error in extractor'
                % (field, field_not, conversion))

        def sanitize_string_field(info, string_field):
            field = info.get(string_field)
            if field is None or isinstance(field, compat_str):
                return
            report_force_conversion(string_field, 'a string', 'string')
            info[string_field] = compat_str(field)

        def sanitize_numeric_fields(info):
            for numeric_field in self._NUMERIC_FIELDS:
                field = info.get(numeric_field)
                if field is None or isinstance(field, compat_numeric_types):
                    continue
                report_force_conversion(numeric_field, 'numeric', 'int')
                info[numeric_field] = int_or_none(field)

        sanitize_string_field(info_dict, 'id')
        sanitize_numeric_fields(info_dict)

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
                try:
                    upload_date = datetime.datetime.utcfromtimestamp(info_dict[ts_key])
                    info_dict[date_key] = upload_date.strftime('%Y%m%d')
                except (ValueError, OverflowError, OSError):
                    pass

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

        # Auto generate title fields corresponding to the *_number fields when missing
        # in order to always have clean titles. This is very common for TV series.
        for field in ('chapter', 'season', 'episode'):
            if info_dict.get('%s_number' % field) is not None and not info_dict.get(field):
                info_dict[field] = '%s %d' % (field.capitalize(), info_dict['%s_number' % field])

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

        if info_dict.get('formats') is None:
            # There's only one format available
            formats = [info_dict]
        else:
            formats = info_dict['formats']

        info_dict['__has_drm'] = any(f.get('has_drm') for f in formats)
        if not self.params.get('allow_unplayable_formats'):
            formats = [f for f in formats if not f.get('has_drm')]

        if info_dict.get('is_live'):
            get_from_start = bool(self.params.get('live_from_start'))
            formats = [f for f in formats if bool(f.get('is_from_start')) == get_from_start]
            if not get_from_start:
                info_dict['title'] += ' ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        if not formats:
            self.raise_no_formats(info_dict)

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
        formats = list(filter(is_wellformed, formats))

        formats_dict = {}

        # We check that all the formats have the format and format_id fields
        for i, format in enumerate(formats):
            sanitize_string_field(format, 'format_id')
            sanitize_numeric_fields(format)
            format['url'] = sanitize_url(format['url'])
            if not format.get('format_id'):
                format['format_id'] = compat_str(i)
            else:
                # Sanitize format_id from characters used in format selector expression
                format['format_id'] = re.sub(r'[\s,/+\[\]()]', '_', format['format_id'])
            format_id = format['format_id']
            if format_id not in formats_dict:
                formats_dict[format_id] = []
            formats_dict[format_id].append(format)

        # Make sure all formats have unique format_id
        common_exts = set(itertools.chain(*self._format_selection_exts.values()))
        for format_id, ambiguous_formats in formats_dict.items():
            ambigious_id = len(ambiguous_formats) > 1
            for i, format in enumerate(ambiguous_formats):
                if ambigious_id:
                    format['format_id'] = '%s-%d' % (format_id, i)
                if format.get('ext') is None:
                    format['ext'] = determine_ext(format['url']).lower()
                # Ensure there is no conflict between id and ext in format selection
                # See https://github.com/yt-dlp/yt-dlp/issues/1282
                if format['format_id'] != format['ext'] and format['format_id'] in common_exts:
                    format['format_id'] = 'f%s' % format['format_id']

        for i, format in enumerate(formats):
            if format.get('format') is None:
                format['format'] = '{id} - {res}{note}'.format(
                    id=format['format_id'],
                    res=self.format_resolution(format),
                    note=format_field(format, 'format_note', ' (%s)'),
                )
            if format.get('protocol') is None:
                format['protocol'] = determine_protocol(format)
            if format.get('resolution') is None:
                format['resolution'] = self.format_resolution(format, default=None)
            if format.get('dynamic_range') is None and format.get('vcodec') != 'none':
                format['dynamic_range'] = 'SDR'
            if (info_dict.get('duration') and format.get('tbr')
                    and not format.get('filesize') and not format.get('filesize_approx')):
                format['filesize_approx'] = info_dict['duration'] * format['tbr'] * (1024 / 8)

            # Add HTTP headers, so that external programs can use them from the
            # json output
            full_format_info = info_dict.copy()
            full_format_info.update(format)
            format['http_headers'] = self._calc_headers(full_format_info)
        # Remove private housekeeping stuff
        if '__x_forwarded_for_ip' in info_dict:
            del info_dict['__x_forwarded_for_ip']

        # TODO Central sorting goes here

        if self.params.get('check_formats') is True:
            formats = LazyList(self._check_formats(formats[::-1]), reverse=True)

        if not formats or formats[0] is not info_dict:
            # only set the 'formats' fields if the original info_dict list them
            # otherwise we end up with a circular reference, the first (and unique)
            # element in the 'formats' field in info_dict is info_dict itself,
            # which can't be exported to json
            info_dict['formats'] = formats

        info_dict, _ = self.pre_process(info_dict)

        # The pre-processors may have modified the formats
        formats = info_dict.get('formats', [info_dict])

        list_only = self.params.get('simulate') is None and (
            self.params.get('list_thumbnails') or self.params.get('listformats') or self.params.get('listsubtitles'))
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
            self.__forced_printings(info_dict, self.prepare_filename(info_dict), incomplete=True)
            return

        format_selector = self.format_selector
        if format_selector is None:
            req_format = self._default_format_spec(info_dict, download=download)
            self.write_debug('Default format spec: %s' % req_format)
            format_selector = self.build_format_selector(req_format)

        while True:
            if interactive_format_selection:
                req_format = input(
                    self._format_screen('\nEnter format selector: ', self.Styles.EMPHASIS))
                try:
                    format_selector = self.build_format_selector(req_format)
                except SyntaxError as err:
                    self.report_error(err, tb=False, is_error=False)
                    continue

            # While in format selection we may need to have an access to the original
            # format set in order to calculate some metrics or do some processing.
            # For now we need to be able to guess whether original formats provided
            # by extractor are incomplete or not (i.e. whether extractor provides only
            # video-only or audio-only formats) for proper formats selection for
            # extractors with such incomplete formats (see
            # https://github.com/ytdl-org/youtube-dl/pull/5556).
            # Since formats may be filtered during format selection and may not match
            # the original formats the results may be incorrect. Thus original formats
            # or pre-calculated metrics should be passed to format selection routines
            # as well.
            # We will pass a context object containing all necessary additional data
            # instead of just formats.
            # This fixes incorrect format selection issue (see
            # https://github.com/ytdl-org/youtube-dl/issues/10083).
            incomplete_formats = (
                # All formats are video-only or
                all(f.get('vcodec') != 'none' and f.get('acodec') == 'none' for f in formats)
                # all formats are audio-only
                or all(f.get('vcodec') == 'none' and f.get('acodec') != 'none' for f in formats))

            ctx = {
                'formats': formats,
                'incomplete_formats': incomplete_formats,
            }

            formats_to_download = list(format_selector(ctx))
            if interactive_format_selection and not formats_to_download:
                self.report_error('Requested format is not available', tb=False, is_error=False)
                continue
            break

        if not formats_to_download:
            if not self.params.get('ignore_no_formats_error'):
                raise ExtractorError('Requested format is not available', expected=True,
                                     video_id=info_dict['id'], ie=info_dict['extractor'])
            self.report_warning('Requested format is not available')
            # Process what we can, even without any available formats.
            formats_to_download = [{}]

        best_format = formats_to_download[-1]
        if download:
            if best_format:
                self.to_screen(
                    f'[info] {info_dict["id"]}: Downloading {len(formats_to_download)} format(s): '
                    + ', '.join([f['format_id'] for f in formats_to_download]))
            max_downloads_reached = False
            for i, fmt in enumerate(formats_to_download):
                formats_to_download[i] = new_info = dict(info_dict)
                # Save a reference to the original info_dict so that it can be modified in process_info if needed
                new_info.update(fmt)
                new_info['__original_infodict'] = info_dict
                try:
                    self.process_info(new_info)
                except MaxDownloadsReached:
                    max_downloads_reached = True
                new_info.pop('__original_infodict')
                # Remove copied info
                for key, val in tuple(new_info.items()):
                    if info_dict.get(key) == val:
                        new_info.pop(key)
                if max_downloads_reached:
                    break

            write_archive = set(f.get('__write_download_archive', False) for f in formats_to_download)
            assert write_archive.issubset({True, False, 'ignore'})
            if True in write_archive and False not in write_archive:
                self.record_download_archive(info_dict)

            info_dict['requested_downloads'] = formats_to_download
            info_dict = self.run_all_pps('after_video', info_dict)
            if max_downloads_reached:
                raise MaxDownloadsReached()

        # We update the info dict with the selected best quality format (backwards compatibility)
        info_dict.update(best_format)
        return info_dict

    def process_subtitles(self, video_id, normal_subtitles, automatic_captions):
        """Select the requested subtitles and their format"""
        available_subs = {}
        if normal_subtitles and self.params.get('writesubtitles'):
            available_subs.update(normal_subtitles)
        if automatic_captions and self.params.get('writeautomaticsub'):
            for lang, cap_info in automatic_captions.items():
                if lang not in available_subs:
                    available_subs[lang] = cap_info

        if (not self.params.get('writesubtitles') and not
                self.params.get('writeautomaticsub') or not
                available_subs):
            return None

        all_sub_langs = available_subs.keys()
        if self.params.get('allsubtitles', False):
            requested_langs = all_sub_langs
        elif self.params.get('subtitleslangs', False):
            # A list is used so that the order of languages will be the same as
            # given in subtitleslangs. See https://github.com/yt-dlp/yt-dlp/issues/1041
            requested_langs = []
            for lang_re in self.params.get('subtitleslangs'):
                if lang_re == 'all':
                    requested_langs.extend(all_sub_langs)
                    continue
                discard = lang_re[0] == '-'
                if discard:
                    lang_re = lang_re[1:]
                current_langs = filter(re.compile(lang_re + '$').match, all_sub_langs)
                if discard:
                    for lang in current_langs:
                        while lang in requested_langs:
                            requested_langs.remove(lang)
                else:
                    requested_langs.extend(current_langs)
            requested_langs = orderedSet(requested_langs)
        elif 'en' in available_subs:
            requested_langs = ['en']
        else:
            requested_langs = [list(all_sub_langs)[0]]
        if requested_langs:
            self.write_debug('Downloading subtitles: %s' % ', '.join(requested_langs))

        formats_query = self.params.get('subtitlesformat', 'best')
        formats_preference = formats_query.split('/') if formats_query else []
        subs = {}
        for lang in requested_langs:
            formats = available_subs.get(lang)
            if formats is None:
                self.report_warning('%s subtitles not available for %s' % (lang, video_id))
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
                    'No subtitle format found matching "%s" for language %s, '
                    'using %s' % (formats_query, lang, f['ext']))
            subs[lang] = f
        return subs

    def _forceprint(self, key, info_dict):
        if info_dict is None:
            return
        info_copy = info_dict.copy()
        info_copy['formats_table'] = self.render_formats_table(info_dict)
        info_copy['thumbnails_table'] = self.render_thumbnails_table(info_dict)
        info_copy['subtitles_table'] = self.render_subtitles_table(info_dict.get('id'), info_dict.get('subtitles'))
        info_copy['automatic_captions_table'] = self.render_subtitles_table(info_dict.get('id'), info_dict.get('automatic_captions'))

        def format_tmpl(tmpl):
            mobj = re.match(r'\w+(=?)$', tmpl)
            if mobj and mobj.group(1):
                return f'{tmpl[:-1]} = %({tmpl[:-1]})r'
            elif mobj:
                return f'%({tmpl})s'
            return tmpl

        for tmpl in self.params['forceprint'].get(key, []):
            self.to_stdout(self.evaluate_outtmpl(format_tmpl(tmpl), info_copy))

        for tmpl, file_tmpl in self.params['print_to_file'].get(key, []):
            filename = self.evaluate_outtmpl(file_tmpl, info_dict)
            tmpl = format_tmpl(tmpl)
            self.to_screen(f'[info] Writing {tmpl!r} to: {filename}')
            with io.open(filename, 'a', encoding='utf-8') as f:
                f.write(self.evaluate_outtmpl(tmpl, info_copy) + '\n')

    def __forced_printings(self, info_dict, filename, incomplete):
        def print_mandatory(field, actual_field=None):
            if actual_field is None:
                actual_field = field
            if (self.params.get('force%s' % field, False)
                    and (not incomplete or info_dict.get(actual_field) is not None)):
                self.to_stdout(info_dict[actual_field])

        def print_optional(field):
            if (self.params.get('force%s' % field, False)
                    and info_dict.get(field) is not None):
                self.to_stdout(info_dict[field])

        info_dict = info_dict.copy()
        if filename is not None:
            info_dict['filename'] = filename
        if info_dict.get('requested_formats') is not None:
            # For RTMP URLs, also include the playpath
            info_dict['urls'] = '\n'.join(f['url'] + f.get('play_path', '') for f in info_dict['requested_formats'])
        elif 'url' in info_dict:
            info_dict['urls'] = info_dict['url'] + info_dict.get('play_path', '')

        if (self.params.get('forcejson')
                or self.params['forceprint'].get('video')
                or self.params['print_to_file'].get('video')):
            self.post_extract(info_dict)
        self._forceprint('video', info_dict)

        print_mandatory('title')
        print_mandatory('id')
        print_mandatory('url', 'urls')
        print_optional('thumbnail')
        print_optional('description')
        print_optional('filename')
        if self.params.get('forceduration') and info_dict.get('duration') is not None:
            self.to_stdout(formatSeconds(info_dict['duration']))
        print_mandatory('format')

        if self.params.get('forcejson'):
            self.to_stdout(json.dumps(self.sanitize_info(info_dict)))

    def dl(self, name, info, subtitle=False, test=False):
        if not info.get('url'):
            self.raise_no_formats(info, True)

        if test:
            verbose = self.params.get('verbose')
            params = {
                'test': True,
                'quiet': self.params.get('quiet') or not verbose,
                'verbose': verbose,
                'noprogress': not verbose,
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
            self.write_debug('Invoking downloader on "%s"' % urls)

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

    def process_info(self, info_dict):
        """Process a single resolved IE result. (Modified it in-place)"""

        assert info_dict.get('_type', 'video') == 'video'
        original_infodict = info_dict

        if 'format' not in info_dict and 'ext' in info_dict:
            info_dict['format'] = info_dict['ext']

        if self._match_entry(info_dict) is not None:
            info_dict['__write_download_archive'] = 'ignore'
            return

        self.post_extract(info_dict)
        self._num_downloads += 1

        # info_dict['_filename'] needs to be set for backward compatibility
        info_dict['_filename'] = full_filename = self.prepare_filename(info_dict, warn=True)
        temp_filename = self.prepare_filename(info_dict, 'temp')
        files_to_move = {}

        # Forced printings
        self.__forced_printings(info_dict, full_filename, incomplete=('format' not in info_dict))

        if self.params.get('simulate'):
            info_dict['__write_download_archive'] = self.params.get('force_write_download_archive')
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
                    with io.open(encodeFilename(annofn), 'w', encoding='utf-8') as annofile:
                        annofile.write(info_dict['annotations'])
                except (KeyError, TypeError):
                    self.report_warning('There are no annotations to write.')
                except (OSError, IOError):
                    self.report_error('Cannot write annotations file: ' + annofn)
                    return

        # Write internet shortcut files
        def _write_link_file(link_type):
            if 'webpage_url' not in info_dict:
                self.report_error('Cannot write internet shortcut file because the "webpage_url" field is missing in the media information')
                return False
            linkfn = replace_extension(self.prepare_filename(info_dict, 'link'), link_type, info_dict.get('ext'))
            if not self._ensure_dir_exists(encodeFilename(linkfn)):
                return False
            if self.params.get('overwrites', True) and os.path.exists(encodeFilename(linkfn)):
                self.to_screen(f'[info] Internet shortcut (.{link_type}) is already present')
                return True
            try:
                self.to_screen(f'[info] Writing internet shortcut (.{link_type}) to: {linkfn}')
                with io.open(encodeFilename(to_high_limit_path(linkfn)), 'w', encoding='utf-8',
                             newline='\r\n' if link_type == 'url' else '\n') as linkfile:
                    template_vars = {'url': iri_to_uri(info_dict['webpage_url'])}
                    if link_type == 'desktop':
                        template_vars['filename'] = linkfn[:-(len(link_type) + 1)]
                    linkfile.write(LINK_TEMPLATES[link_type] % template_vars)
            except (OSError, IOError):
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

        def replace_info_dict(new_info):
            nonlocal info_dict
            if new_info == info_dict:
                return
            info_dict.clear()
            info_dict.update(new_info)

        try:
            new_info, files_to_move = self.pre_process(info_dict, 'before_dl', files_to_move)
            replace_info_dict(new_info)
        except PostProcessingError as err:
            self.report_error('Preprocessing: %s' % str(err))
            return

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

                success = True
                if info_dict.get('requested_formats') is not None:

                    def compatible_formats(formats):
                        # TODO: some formats actually allow this (mkv, webm, ogg, mp4), but not all of them.
                        video_formats = [format for format in formats if format.get('vcodec') != 'none']
                        audio_formats = [format for format in formats if format.get('acodec') != 'none']
                        if len(video_formats) > 2 or len(audio_formats) > 2:
                            return False

                        # Check extension
                        exts = set(format.get('ext') for format in formats)
                        COMPATIBLE_EXTS = (
                            set(('mp3', 'mp4', 'm4a', 'm4p', 'm4b', 'm4r', 'm4v', 'ismv', 'isma')),
                            set(('webm',)),
                        )
                        for ext_sets in COMPATIBLE_EXTS:
                            if ext_sets.issuperset(exts):
                                return True
                        # TODO: Check acodec/vcodec
                        return False

                    requested_formats = info_dict['requested_formats']
                    old_ext = info_dict['ext']
                    if self.params.get('merge_output_format') is None:
                        if not compatible_formats(requested_formats):
                            info_dict['ext'] = 'mkv'
                            self.report_warning(
                                'Requested formats are incompatible for merge and will be merged into mkv')
                        if (info_dict['ext'] == 'webm'
                                and info_dict.get('thumbnails')
                                # check with type instead of pp_key, __name__, or isinstance
                                # since we dont want any custom PPs to trigger this
                                and any(type(pp) == EmbedThumbnailPP for pp in self._pps['post_process'])):
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
                        return '%s.%s' % (filename_wo_ext, ext)

                    # Ensure filename always has a correct extension for successful merge
                    full_filename = correct_ext(full_filename)
                    temp_filename = correct_ext(temp_filename)
                    dl_filename = existing_video_file(full_filename, temp_filename)
                    info_dict['__real_download'] = False

                    downloaded = []
                    merger = FFmpegMergerPP(self)

                    fd = get_suitable_downloader(info_dict, self.params, to_stdout=temp_filename == '-')
                    if dl_filename is not None:
                        self.report_file_already_downloaded(dl_filename)
                    elif fd:
                        for f in requested_formats if fd != FFmpegFD else []:
                            f['filepath'] = fname = prepend_extension(
                                correct_ext(temp_filename, info_dict['ext']),
                                'f%s' % f['format_id'], info_dict['ext'])
                            downloaded.append(fname)
                        info_dict['url'] = '\n'.join(f['url'] for f in requested_formats)
                        success, real_download = self.dl(temp_filename, info_dict)
                        info_dict['__real_download'] = real_download
                    else:
                        if self.params.get('allow_unplayable_formats'):
                            self.report_warning(
                                'You have requested merging of multiple formats '
                                'while also allowing unplayable formats to be downloaded. '
                                'The formats won\'t be merged to prevent data corruption.')
                        elif not merger.available:
                            self.report_warning(
                                'You have requested merging of multiple formats but ffmpeg is not installed. '
                                'The formats won\'t be merged.')

                        if temp_filename == '-':
                            reason = ('using a downloader other than ffmpeg' if FFmpegFD.can_merge_formats(info_dict, self.params)
                                      else 'but the formats are incompatible for simultaneous download' if merger.available
                                      else 'but ffmpeg is not installed')
                            self.report_warning(
                                f'You have requested downloading multiple formats to stdout {reason}. '
                                'The formats will be streamed one after the other')
                            fname = temp_filename
                        for f in requested_formats:
                            new_info = dict(info_dict)
                            del new_info['requested_formats']
                            new_info.update(f)
                            if temp_filename != '-':
                                fname = prepend_extension(
                                    correct_ext(temp_filename, new_info['ext']),
                                    'f%s' % f['format_id'], new_info['ext'])
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
                self.report_error('unable to download video data: %s' % error_to_compat_str(err))
                return
            except (OSError, IOError) as err:
                raise UnavailableVideoError(err)
            except (ContentTooShortError, ) as err:
                self.report_error('content too short (expected %s bytes and served %s)' % (err.expected, err.downloaded))
                return

            if success and full_filename != '-':

                def fixup():
                    do_fixup = True
                    fixup_policy = self.params.get('fixup')
                    vid = info_dict['id']

                    if fixup_policy in ('ignore', 'never'):
                        return
                    elif fixup_policy == 'warn':
                        do_fixup = False
                    elif fixup_policy != 'force':
                        assert fixup_policy in ('detect_or_warn', None)
                        if not info_dict.get('__real_download'):
                            do_fixup = False

                    def ffmpeg_fixup(cndn, msg, cls):
                        if not cndn:
                            return
                        if not do_fixup:
                            self.report_warning(f'{vid}: {msg}')
                            return
                        pp = cls(self)
                        if pp.available:
                            info_dict['__postprocessors'].append(pp)
                        else:
                            self.report_warning(f'{vid}: {msg}. Install ffmpeg to fix this automatically')

                    stretched_ratio = info_dict.get('stretched_ratio')
                    ffmpeg_fixup(
                        stretched_ratio not in (1, None),
                        f'Non-uniform pixel ratio {stretched_ratio}',
                        FFmpegFixupStretchedPP)

                    ffmpeg_fixup(
                        (info_dict.get('requested_formats') is None
                         and info_dict.get('container') == 'm4a_dash'
                         and info_dict.get('ext') == 'm4a'),
                        'writing DASH m4a. Only some players support this container',
                        FFmpegFixupM4aPP)

                    downloader = get_suitable_downloader(info_dict, self.params) if 'protocol' in info_dict else None
                    downloader = downloader.__name__ if downloader else None

                    if info_dict.get('requested_formats') is None:  # Not necessary if doing merger
                        ffmpeg_fixup(downloader == 'HlsFD',
                                     'Possible MPEG-TS in MP4 container or malformed AAC timestamps',
                                     FFmpegFixupM3u8PP)
                        ffmpeg_fixup(info_dict.get('is_live') and downloader == 'DashSegmentsFD',
                                     'Possible duplicate MOOV atoms', FFmpegFixupDuplicateMoovPP)

                    ffmpeg_fixup(downloader == 'WebSocketFragmentFD', 'Malformed timestamps detected', FFmpegFixupTimestampPP)
                    ffmpeg_fixup(downloader == 'WebSocketFragmentFD', 'Malformed duration detected', FFmpegFixupDurationPP)

                fixup()
                try:
                    replace_info_dict(self.post_process(dl_filename, info_dict, files_to_move))
                except PostProcessingError as err:
                    self.report_error('Postprocessing: %s' % str(err))
                    return
                try:
                    for ph in self._post_hooks:
                        ph(info_dict['filepath'])
                except Exception as err:
                    self.report_error('post hooks: %s' % str(err))
                    return
                info_dict['__write_download_archive'] = True

        if self.params.get('force_write_download_archive'):
            info_dict['__write_download_archive'] = True

        # Make sure the info_dict was modified in-place
        assert info_dict is original_infodict

        max_downloads = self.params.get('max_downloads')
        if max_downloads is not None and self._num_downloads >= int(max_downloads):
            raise MaxDownloadsReached()

    def __download_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except UnavailableVideoError as e:
                self.report_error(e)
            except MaxDownloadsReached as e:
                self.to_screen(f'[info] {e}')
                raise
            except DownloadCancelled as e:
                self.to_screen(f'[info] {e}')
                if not self.params.get('break_per_url'):
                    raise
            else:
                if self.params.get('dump_single_json', False):
                    self.post_extract(res)
                    self.to_stdout(json.dumps(self.sanitize_info(res)))
        return wrapper

    def download(self, url_list):
        """Download a given list of URLs."""
        url_list = variadic(url_list)  # Passing a single URL is a common mistake
        outtmpl = self.outtmpl_dict['default']
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
            info = self.sanitize_info(json.loads('\n'.join(f)), self.params.get('clean_infojson', True))
        try:
            self.__download_wrapper(self.process_ie_result)(info, download=True)
        except (DownloadError, EntryNotInPlaylist, ReExtractInfo) as e:
            if not isinstance(e, EntryNotInPlaylist):
                self.to_stderr('\r')
            webpage_url = info.get('webpage_url')
            if webpage_url is not None:
                self.report_warning(f'The info failed to download: {e}; trying with URL {webpage_url}')
                return self.download([webpage_url])
            else:
                raise
        return self._download_retcode

    @staticmethod
    def sanitize_info(info_dict, remove_private_keys=False):
        ''' Sanitize the infodict for converting to json '''
        if info_dict is None:
            return info_dict
        info_dict.setdefault('epoch', int(time.time()))
        info_dict.setdefault('_type', 'video')
        remove_keys = {'__original_infodict'}  # Always remove this since this may contain a copy of the entire dict
        keep_keys = ['_type']  # Always keep this to facilitate load-info-json
        if remove_private_keys:
            remove_keys |= {
                'requested_downloads', 'requested_formats', 'requested_subtitles', 'requested_entries',
                'entries', 'filepath', 'infojson_filename', 'original_url', 'playlist_autonumber',
            }
            reject = lambda k, v: k not in keep_keys and (
                k.startswith('_') or k in remove_keys or v is None)
        else:
            reject = lambda k, v: k in remove_keys

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
        ''' Alias of sanitize_info for backward compatibility '''
        return YoutubeDL.sanitize_info(info_dict, actually_filter)

    @staticmethod
    def post_extract(info_dict):
        def actual_post_extract(info_dict):
            if info_dict.get('_type') in ('playlist', 'multi_video'):
                for video_dict in info_dict.get('entries', {}):
                    actual_post_extract(video_dict or {})
                return

            post_extractor = info_dict.get('__post_extractor') or (lambda: {})
            extra = post_extractor().items()
            info_dict.update(extra)
            info_dict.pop('__post_extractor', None)

            original_infodict = info_dict.get('__original_infodict') or {}
            original_infodict.update(extra)
            original_infodict.pop('__post_extractor', None)

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
            for old_filename in set(files_to_delete):
                self.to_screen('Deleting original file %s (pass -k to keep)' % old_filename)
                try:
                    os.remove(encodeFilename(old_filename))
                except (IOError, OSError):
                    self.report_warning('Unable to remove downloaded original file')
                if old_filename in infodict['__files_to_move']:
                    del infodict['__files_to_move'][old_filename]
        return infodict

    def run_all_pps(self, key, info, *, additional_pps=None):
        self._forceprint(key, info)
        for pp in (additional_pps or []) + self._pps[key]:
            info = self.run_pp(pp, info)
        return info

    def pre_process(self, ie_info, key='pre_process', files_to_move=None):
        info = dict(ie_info)
        info['__files_to_move'] = files_to_move or {}
        info = self.run_all_pps(key, info)
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
        return '%s %s' % (extractor.lower(), video_id)

    def in_download_archive(self, info_dict):
        fn = self.params.get('download_archive')
        if fn is None:
            return False

        vid_id = self._make_archive_id(info_dict)
        if not vid_id:
            return False  # Incomplete video information

        return vid_id in self.archive

    def record_download_archive(self, info_dict):
        fn = self.params.get('download_archive')
        if fn is None:
            return
        vid_id = self._make_archive_id(info_dict)
        assert vid_id
        self.write_debug(f'Adding to archive: {vid_id}')
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
            return '%sp' % format['height']
        elif format.get('width'):
            return '%dx?' % format['width']
        return default

    def _list_format_headers(self, *headers):
        if self.params.get('listformats_table', True) is not False:
            return [self._format_screen(header, self.Styles.HEADERS) for header in headers]
        return headers

    def _format_note(self, fdict):
        res = ''
        if fdict.get('ext') in ['f4f', 'f4m']:
            res += '(unsupported)'
        if fdict.get('language'):
            if res:
                res += ' '
            res += '[%s]' % fdict['language']
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
            res += '%s container' % fdict['container']
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
            res += '%sfps' % fdict['fps']
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

    def render_formats_table(self, info_dict):
        if not info_dict.get('formats') and not info_dict.get('url'):
            return None

        formats = info_dict.get('formats', [info_dict])
        if not self.params.get('listformats_table', True) is not False:
            table = [
                [
                    format_field(f, 'format_id'),
                    format_field(f, 'ext'),
                    self.format_resolution(f),
                    self._format_note(f)
                ] for f in formats if f.get('preference') is None or f['preference'] >= -1000]
            return render_table(['format code', 'extension', 'resolution', 'note'], table, extra_gap=1)

        delim = self._format_screen('\u2502', self.Styles.DELIM, '|', test_encoding=True)
        table = [
            [
                self._format_screen(format_field(f, 'format_id'), self.Styles.ID),
                format_field(f, 'ext'),
                format_field(f, func=self.format_resolution, ignore=('audio only', 'images')),
                format_field(f, 'fps', '\t%d'),
                format_field(f, 'dynamic_range', '%s', ignore=(None, 'SDR')).replace('HDR', ''),
                delim,
                format_field(f, 'filesize', ' \t%s', func=format_bytes) + format_field(f, 'filesize_approx', '~\t%s', func=format_bytes),
                format_field(f, 'tbr', '\t%dk'),
                shorten_protocol_name(f.get('protocol', '')),
                delim,
                format_field(f, 'vcodec', default='unknown').replace(
                    'none', 'images' if f.get('acodec') == 'none'
                            else self._format_screen('audio only', self.Styles.SUPPRESS)),
                format_field(f, 'vbr', '\t%dk'),
                format_field(f, 'acodec', default='unknown').replace(
                    'none', '' if f.get('vcodec') == 'none'
                            else self._format_screen('video only', self.Styles.SUPPRESS)),
                format_field(f, 'abr', '\t%dk'),
                format_field(f, 'asr', '\t%dHz'),
                join_nonempty(
                    self._format_screen('UNSUPPORTED', 'light red') if f.get('ext') in ('f4f', 'f4m') else None,
                    format_field(f, 'language', '[%s]'),
                    join_nonempty(format_field(f, 'format_note'),
                                  format_field(f, 'container', ignore=(None, f.get('ext'))),
                                  delim=', '),
                    delim=' '),
            ] for f in formats if f.get('preference') is None or f['preference'] >= -1000]
        header_line = self._list_format_headers(
            'ID', 'EXT', 'RESOLUTION', '\tFPS', 'HDR', delim, '\tFILESIZE', '\tTBR', 'PROTO',
            delim, 'VCODEC', '\tVBR', 'ACODEC', '\tABR', '\tASR', 'MORE INFO')

        return render_table(
            header_line, table, hide_empty=True,
            delim=self._format_screen('\u2500', self.Styles.DELIM, '-', test_encoding=True))

    def render_thumbnails_table(self, info_dict):
        thumbnails = list(info_dict.get('thumbnails') or [])
        if not thumbnails:
            return None
        return render_table(
            self._list_format_headers('ID', 'Width', 'Height', 'URL'),
            [[t.get('id'), t.get('width', 'unknown'), t.get('height', 'unknown'), t['url']] for t in thumbnails])

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

    def urlopen(self, req):
        """ Start an HTTP download """
        if isinstance(req, compat_basestring):
            req = sanitized_Request(req)
        return self._opener.open(req, timeout=self._socket_timeout)

    def print_debug_header(self):
        if not self.params.get('verbose'):
            return

        def get_encoding(stream):
            ret = getattr(stream, 'encoding', 'missing (%s)' % type(stream).__name__)
            if not supports_terminal_sequences(stream):
                from .compat import WINDOWS_VT_MODE
                ret += ' (No VT)' if WINDOWS_VT_MODE is False else ' (No ANSI)'
            return ret

        encoding_str = 'Encodings: locale %s, fs %s, out %s, err %s, pref %s' % (
            locale.getpreferredencoding(),
            sys.getfilesystemencoding(),
            get_encoding(self._screen_file), get_encoding(self._err_file),
            self.get_encoding())

        logger = self.params.get('logger')
        if logger:
            write_debug = lambda msg: logger.debug(f'[debug] {msg}')
            write_debug(encoding_str)
        else:
            write_string(f'[debug] {encoding_str}\n', encoding=None)
            write_debug = lambda msg: self._write_string(f'[debug] {msg}\n')

        source = detect_variant()
        write_debug(join_nonempty(
            'yt-dlp version', __version__,
            f'[{RELEASE_GIT_HEAD}]' if RELEASE_GIT_HEAD else '',
            '' if source == 'unknown' else f'({source})',
            delim=' '))
        if not _LAZY_LOADER:
            if os.environ.get('YTDLP_NO_LAZY_EXTRACTORS'):
                write_debug('Lazy loading extractors is forcibly disabled')
            else:
                write_debug('Lazy loading extractors is disabled')
        if plugin_extractors or plugin_postprocessors:
            write_debug('Plugins: %s' % [
                '%s%s' % (klass.__name__, '' if klass.__name__ == name else f' as {name}')
                for name, klass in itertools.chain(plugin_extractors.items(), plugin_postprocessors.items())])
        if self.params.get('compat_opts'):
            write_debug('Compatibility options: %s' % ', '.join(self.params.get('compat_opts')))

        if source == 'source':
            try:
                sp = Popen(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=os.path.dirname(os.path.abspath(__file__)))
                out, err = sp.communicate_or_kill()
                out = out.decode().strip()
                if re.match('[0-9a-f]+', out):
                    write_debug('Git HEAD: %s' % out)
            except Exception:
                try:
                    sys.exc_clear()
                except Exception:
                    pass

        def python_implementation():
            impl_name = platform.python_implementation()
            if impl_name == 'PyPy' and hasattr(sys, 'pypy_version_info'):
                return impl_name + ' version %d.%d.%d' % sys.pypy_version_info[:3]
            return impl_name

        write_debug('Python version %s (%s %s) - %s' % (
            platform.python_version(),
            python_implementation(),
            platform.architecture()[0],
            platform_name()))

        exe_versions, ffmpeg_features = FFmpegPostProcessor.get_versions_and_features(self)
        ffmpeg_features = {key for key, val in ffmpeg_features.items() if val}
        if ffmpeg_features:
            exe_versions['ffmpeg'] += ' (%s)' % ','.join(ffmpeg_features)

        exe_versions['rtmpdump'] = rtmpdump_version()
        exe_versions['phantomjs'] = PhantomJSwrapper._version()
        exe_str = ', '.join(
            f'{exe} {v}' for exe, v in sorted(exe_versions.items()) if v
        ) or 'none'
        write_debug('exe versions: %s' % exe_str)

        from .downloader.websocket import has_websockets
        from .postprocessor.embedthumbnail import has_mutagen
        from .cookies import SQLITE_AVAILABLE, SECRETSTORAGE_AVAILABLE

        lib_str = join_nonempty(
            compat_pycrypto_AES and compat_pycrypto_AES.__name__.split('.')[0],
            SECRETSTORAGE_AVAILABLE and 'secretstorage',
            has_mutagen and 'mutagen',
            SQLITE_AVAILABLE and 'sqlite',
            has_websockets and 'websockets',
            delim=', ') or 'none'
        write_debug('Optional libraries: %s' % lib_str)

        proxy_map = {}
        for handler in self._opener.handlers:
            if hasattr(handler, 'proxies'):
                proxy_map.update(handler.proxies)
        write_debug(f'Proxy map: {proxy_map}')

        # Not implemented
        if False and self.params.get('call_home'):
            ipaddr = self.urlopen('https://yt-dl.org/ip').read().decode('utf-8')
            write_debug('Public IP address: %s' % ipaddr)
            latest_version = self.urlopen(
                'https://yt-dl.org/latest/version').read().decode('utf-8')
            if version_tuple(latest_version) > version_tuple(__version__):
                self.report_warning(
                    'You are using an outdated version (newest version: %s)! '
                    'See https://yt-dl.org/update if you need help updating.' %
                    latest_version)

    def _setup_opener(self):
        timeout_val = self.params.get('socket_timeout')
        self._socket_timeout = 20 if timeout_val is None else float(timeout_val)

        opts_cookiesfrombrowser = self.params.get('cookiesfrombrowser')
        opts_cookiefile = self.params.get('cookiefile')
        opts_proxy = self.params.get('proxy')

        self.cookiejar = load_cookies(opts_cookiefile, opts_cookiesfrombrowser, self)

        cookie_processor = YoutubeDLCookieProcessor(self.cookiejar)
        if opts_proxy is not None:
            if opts_proxy == '':
                proxies = {}
            else:
                proxies = {'http': opts_proxy, 'https': opts_proxy}
        else:
            proxies = compat_urllib_request.getproxies()
            # Set HTTPS proxy to HTTP one if given (https://github.com/ytdl-org/youtube-dl/issues/805)
            if 'http' in proxies and 'https' not in proxies:
                proxies['https'] = proxies['http']
        proxy_handler = PerRequestProxyHandler(proxies)

        debuglevel = 1 if self.params.get('debug_printtraffic') else 0
        https_handler = make_HTTPS_handler(self.params, debuglevel=debuglevel)
        ydlh = YoutubeDLHandler(self.params, debuglevel=debuglevel)
        redirect_handler = YoutubeDLRedirectHandler()
        data_handler = compat_urllib_request_DataHandler()

        # When passing our own FileHandler instance, build_opener won't add the
        # default FileHandler and allows us to disable the file protocol, which
        # can be used for malicious purposes (see
        # https://github.com/ytdl-org/youtube-dl/issues/8227)
        file_handler = compat_urllib_request.FileHandler()

        def file_open(*args, **kwargs):
            raise compat_urllib_error.URLError('file:// scheme is explicitly disabled in yt-dlp for security reasons')
        file_handler.file_open = file_open

        opener = compat_urllib_request.build_opener(
            proxy_handler, https_handler, cookie_processor, ydlh, redirect_handler, data_handler, file_handler)

        # Delete the default user-agent header, which would otherwise apply in
        # cases where our custom HTTP handler doesn't come into play
        # (See https://github.com/ytdl-org/youtube-dl/issues/1309 for details)
        opener.addheaders = []
        self._opener = opener

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
        ''' Write infojson and returns True = written, False = skip, None = error '''
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
        else:
            self.to_screen(f'[info] Writing {label} metadata as JSON to: {infofn}')
            try:
                write_json_file(self.sanitize_info(ie_result, self.params.get('clean_infojson', True)), infofn)
            except (OSError, IOError):
                self.report_error(f'Cannot write {label} metadata to JSON file {infofn}')
                return None
        return True

    def _write_description(self, label, ie_result, descfn):
        ''' Write description and returns True = written, False = skip, None = error '''
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
            self.report_warning(f'There\'s no {label} description to write')
            return False
        else:
            try:
                self.to_screen(f'[info] Writing {label} description to: {descfn}')
                with io.open(encodeFilename(descfn), 'w', encoding='utf-8') as descfile:
                    descfile.write(ie_result['description'])
            except (OSError, IOError):
                self.report_error(f'Cannot write {label} description file {descfn}')
                return None
        return True

    def _write_subtitles(self, info_dict, filename):
        ''' Write subtitles to file and return list of (sub_filename, final_sub_filename); or None if error'''
        ret = []
        subtitles = info_dict.get('requested_subtitles')
        if not subtitles or not (self.params.get('writesubtitles') or self.params.get('writeautomaticsub')):
            # subtitles download errors are already managed as troubles in relevant IE
            # that way it will silently go on when used with unsupporting IE
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
                    with io.open(sub_filename, 'w', encoding='utf-8', newline='') as subfile:
                        subfile.write(sub_info['data'])
                    sub_info['filepath'] = sub_filename
                    ret.append((sub_filename, sub_filename_final))
                    continue
                except (OSError, IOError):
                    self.report_error(f'Cannot write video subtitles file {sub_filename}')
                    return None

            try:
                sub_copy = sub_info.copy()
                sub_copy.setdefault('http_headers', info_dict.get('http_headers'))
                self.dl(sub_filename, sub_copy, subtitle=True)
                sub_info['filepath'] = sub_filename
                ret.append((sub_filename, sub_filename_final))
            except (DownloadError, ExtractorError, IOError, OSError, ValueError) + network_exceptions as err:
                if self.params.get('ignoreerrors') is not True:  # False or 'only_download'
                    raise DownloadError(f'Unable to download video subtitles for {sub_lang!r}: {err}', err)
                self.report_warning(f'Unable to download video subtitles for {sub_lang!r}: {err}')
        return ret

    def _write_thumbnails(self, label, info_dict, filename, thumb_filename_base=None):
        ''' Write thumbnails to file and return list of (thumb_filename, final_thumb_filename) '''
        write_all = self.params.get('write_all_thumbnails', False)
        thumbnails, ret = [], []
        if write_all or self.params.get('writethumbnail', False):
            thumbnails = info_dict.get('thumbnails') or []
        multiple = write_all and len(thumbnails) > 1

        if thumb_filename_base is None:
            thumb_filename_base = filename
        if thumbnails and not thumb_filename_base:
            self.write_debug(f'Skipping writing {label} thumbnail')
            return ret

        for idx, t in list(enumerate(thumbnails))[::-1]:
            thumb_ext = (f'{t["id"]}.' if multiple else '') + determine_ext(t['url'], 'jpg')
            thumb_display_id = f'{label} thumbnail {t["id"]}'
            thumb_filename = replace_extension(filename, thumb_ext, info_dict.get('ext'))
            thumb_filename_final = replace_extension(thumb_filename_base, thumb_ext, info_dict.get('ext'))

            existing_thumb = self.existing_file((thumb_filename_final, thumb_filename))
            if existing_thumb:
                self.to_screen('[info] %s is already present' % (
                    thumb_display_id if multiple else f'{label} thumbnail').capitalize())
                t['filepath'] = existing_thumb
                ret.append((existing_thumb, thumb_filename_final))
            else:
                self.to_screen(f'[info] Downloading {thumb_display_id} ...')
                try:
                    uf = self.urlopen(t['url'])
                    self.to_screen(f'[info] Writing {thumb_display_id} to: {thumb_filename}')
                    with open(encodeFilename(thumb_filename), 'wb') as thumbf:
                        shutil.copyfileobj(uf, thumbf)
                    ret.append((thumb_filename, thumb_filename_final))
                    t['filepath'] = thumb_filename
                except network_exceptions as err:
                    thumbnails.pop(idx)
                    self.report_warning(f'Unable to download {thumb_display_id}: {err}')
            if ret and not write_all:
                break
        return ret

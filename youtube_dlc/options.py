from __future__ import unicode_literals

import os.path
import optparse
import re
import sys

from .downloader.external import list_external_downloaders
from .compat import (
    compat_expanduser,
    compat_get_terminal_size,
    compat_getenv,
    compat_kwargs,
    compat_shlex_split,
)
from .utils import (
    preferredencoding,
    write_string,
)
from .version import __version__


def _hide_login_info(opts):
    PRIVATE_OPTS = set(['-p', '--password', '-u', '--username', '--video-password', '--ap-password', '--ap-username'])
    eqre = re.compile('^(?P<key>' + ('|'.join(re.escape(po) for po in PRIVATE_OPTS)) + ')=.+$')

    def _scrub_eq(o):
        m = eqre.match(o)
        if m:
            return m.group('key') + '=PRIVATE'
        else:
            return o

    opts = list(map(_scrub_eq, opts))
    for idx, opt in enumerate(opts):
        if opt in PRIVATE_OPTS and idx + 1 < len(opts):
            opts[idx + 1] = 'PRIVATE'
    return opts


def parseOpts(overrideArguments=None):
    def _readOptions(filename_bytes, default=[]):
        try:
            optionf = open(filename_bytes)
        except IOError:
            return default  # silently skip if file is not present
        try:
            # FIXME: https://github.com/ytdl-org/youtube-dl/commit/dfe5fa49aed02cf36ba9f743b11b0903554b5e56
            contents = optionf.read()
            if sys.version_info < (3,):
                contents = contents.decode(preferredencoding())
            res = compat_shlex_split(contents, comments=True)
        finally:
            optionf.close()
        return res

    def _readUserConf():
        xdg_config_home = compat_getenv('XDG_CONFIG_HOME')
        if xdg_config_home:
            userConfFile = os.path.join(xdg_config_home, 'youtube-dlc', 'config')
            if not os.path.isfile(userConfFile):
                userConfFile = os.path.join(xdg_config_home, 'youtube-dlc.conf')
        else:
            userConfFile = os.path.join(compat_expanduser('~'), '.config', 'youtube-dlc', 'config')
            if not os.path.isfile(userConfFile):
                userConfFile = os.path.join(compat_expanduser('~'), '.config', 'youtube-dlc.conf')
        userConf = _readOptions(userConfFile, None)

        if userConf is None:
            appdata_dir = compat_getenv('appdata')
            if appdata_dir:
                userConf = _readOptions(
                    os.path.join(appdata_dir, 'youtube-dlc', 'config'),
                    default=None)
                if userConf is None:
                    userConf = _readOptions(
                        os.path.join(appdata_dir, 'youtube-dlc', 'config.txt'),
                        default=None)

        if userConf is None:
            userConf = _readOptions(
                os.path.join(compat_expanduser('~'), 'youtube-dlc.conf'),
                default=None)
        if userConf is None:
            userConf = _readOptions(
                os.path.join(compat_expanduser('~'), 'youtube-dlc.conf.txt'),
                default=None)

        if userConf is None:
            userConf = []

        return userConf

    def _format_option_string(option):
        ''' ('-o', '--option') -> -o, --format METAVAR'''

        opts = []

        if option._short_opts:
            opts.append(option._short_opts[0])
        if option._long_opts:
            opts.append(option._long_opts[0])
        if len(opts) > 1:
            opts.insert(1, ', ')

        if option.takes_value():
            opts.append(' %s' % option.metavar)

        return ''.join(opts)

    def _comma_separated_values_options_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, value.split(','))

    # No need to wrap help messages if we're on a wide console
    columns = compat_get_terminal_size().columns
    max_width = columns if columns else 80
    max_help_position = 80

    fmt = optparse.IndentedHelpFormatter(width=max_width, max_help_position=max_help_position)
    fmt.format_option_strings = _format_option_string

    kw = {
        'version': __version__,
        'formatter': fmt,
        'usage': '%prog [OPTIONS] URL [URL...]',
        'conflict_handler': 'resolve',
    }

    parser = optparse.OptionParser(**compat_kwargs(kw))

    general = optparse.OptionGroup(parser, 'General Options')
    general.add_option(
        '-h', '--help',
        action='help',
        help='Print this help text and exit')
    general.add_option(
        '--version',
        action='version',
        help='Print program version and exit')
    general.add_option(
        '-U', '--update',
        action='store_true', dest='update_self',
        help='Update this program to latest version. Make sure that you have sufficient permissions (run with sudo if needed)')
    general.add_option(
        '-i', '--ignore-errors',
        action='store_true', dest='ignoreerrors', default=False,
        help='Continue on download errors, for example to skip unavailable videos in a playlist')
    general.add_option(
        '--abort-on-error',
        action='store_false', dest='ignoreerrors',
        help='Abort downloading of further videos (in the playlist or the command line) if an error occurs')
    general.add_option(
        '--dump-user-agent',
        action='store_true', dest='dump_user_agent', default=False,
        help='Display the current browser identification')
    general.add_option(
        '--list-extractors',
        action='store_true', dest='list_extractors', default=False,
        help='List all supported extractors')
    general.add_option(
        '--extractor-descriptions',
        action='store_true', dest='list_extractor_descriptions', default=False,
        help='Output descriptions of all supported extractors')
    general.add_option(
        '--force-generic-extractor',
        action='store_true', dest='force_generic_extractor', default=False,
        help='Force extraction to use the generic extractor')
    general.add_option(
        '--default-search',
        dest='default_search', metavar='PREFIX',
        help='Use this prefix for unqualified URLs. For example "gvsearch2:" downloads two videos from google videos for youtube-dlc "large apple". Use the value "auto" to let youtube-dlc guess ("auto_warning" to emit a warning when guessing). "error" just throws an error. The default value "fixup_error" repairs broken URLs, but emits an error if this is not possible instead of searching.')
    general.add_option(
        '--ignore-config',
        action='store_true',
        help='Do not read configuration files. '
        'When given in the global configuration file /etc/youtube-dlc.conf: '
        'Do not read the user configuration in ~/.config/youtube-dlc/config '
        '(%APPDATA%/youtube-dlc/config.txt on Windows)')
    general.add_option(
        '--config-location',
        dest='config_location', metavar='PATH',
        help='Location of the configuration file; either the path to the config or its containing directory.')
    general.add_option(
        '--flat-playlist',
        action='store_const', dest='extract_flat', const='in_playlist',
        default=False,
        help='Do not extract the videos of a playlist, only list them.')
    general.add_option(
        '--mark-watched',
        action='store_true', dest='mark_watched', default=False,
        help='Mark videos watched (YouTube only)')
    general.add_option(
        '--no-mark-watched',
        action='store_false', dest='mark_watched', default=False,
        help='Do not mark videos watched (YouTube only)')
    general.add_option(
        '--no-color', '--no-colors',
        action='store_true', dest='no_color',
        default=False,
        help='Do not emit color codes in output')

    network = optparse.OptionGroup(parser, 'Network Options')
    network.add_option(
        '--proxy', dest='proxy',
        default=None, metavar='URL',
        help='Use the specified HTTP/HTTPS/SOCKS proxy. To enable '
             'SOCKS proxy, specify a proper scheme. For example '
             'socks5://127.0.0.1:1080/. Pass in an empty string (--proxy "") '
             'for direct connection')
    network.add_option(
        '--socket-timeout',
        dest='socket_timeout', type=float, default=None, metavar='SECONDS',
        help='Time to wait before giving up, in seconds')
    network.add_option(
        '--source-address',
        metavar='IP', dest='source_address', default=None,
        help='Client-side IP address to bind to',
    )
    network.add_option(
        '-4', '--force-ipv4',
        action='store_const', const='0.0.0.0', dest='source_address',
        help='Make all connections via IPv4',
    )
    network.add_option(
        '-6', '--force-ipv6',
        action='store_const', const='::', dest='source_address',
        help='Make all connections via IPv6',
    )

    geo = optparse.OptionGroup(parser, 'Geo Restriction')
    geo.add_option(
        '--geo-verification-proxy',
        dest='geo_verification_proxy', default=None, metavar='URL',
        help='Use this proxy to verify the IP address for some geo-restricted sites. '
        'The default proxy specified by --proxy (or none, if the option is not present) is used for the actual downloading.')
    geo.add_option(
        '--cn-verification-proxy',
        dest='cn_verification_proxy', default=None, metavar='URL',
        help=optparse.SUPPRESS_HELP)
    geo.add_option(
        '--geo-bypass',
        action='store_true', dest='geo_bypass', default=True,
        help='Bypass geographic restriction via faking X-Forwarded-For HTTP header')
    geo.add_option(
        '--no-geo-bypass',
        action='store_false', dest='geo_bypass', default=True,
        help='Do not bypass geographic restriction via faking X-Forwarded-For HTTP header')
    geo.add_option(
        '--geo-bypass-country', metavar='CODE',
        dest='geo_bypass_country', default=None,
        help='Force bypass geographic restriction with explicitly provided two-letter ISO 3166-2 country code')
    geo.add_option(
        '--geo-bypass-ip-block', metavar='IP_BLOCK',
        dest='geo_bypass_ip_block', default=None,
        help='Force bypass geographic restriction with explicitly provided IP block in CIDR notation')

    selection = optparse.OptionGroup(parser, 'Video Selection')
    selection.add_option(
        '--playlist-start',
        dest='playliststart', metavar='NUMBER', default=1, type=int,
        help='Playlist video to start at (default is %default)')
    selection.add_option(
        '--playlist-end',
        dest='playlistend', metavar='NUMBER', default=None, type=int,
        help='Playlist video to end at (default is last)')
    selection.add_option(
        '--playlist-items',
        dest='playlist_items', metavar='ITEM_SPEC', default=None,
        help='Playlist video items to download. Specify indices of the videos in the playlist separated by commas like: "--playlist-items 1,2,5,8" if you want to download videos indexed 1, 2, 5, 8 in the playlist. You can specify range: "--playlist-items 1-3,7,10-13", it will download the videos at index 1, 2, 3, 7, 10, 11, 12 and 13.')
    selection.add_option(
        '--match-title',
        dest='matchtitle', metavar='REGEX',
        help='Download only matching titles (regex or caseless sub-string)')
    selection.add_option(
        '--reject-title',
        dest='rejecttitle', metavar='REGEX',
        help='Skip download for matching titles (regex or caseless sub-string)')
    selection.add_option(
        '--max-downloads',
        dest='max_downloads', metavar='NUMBER', type=int, default=None,
        help='Abort after downloading NUMBER files')
    selection.add_option(
        '--min-filesize',
        metavar='SIZE', dest='min_filesize', default=None,
        help='Do not download any videos smaller than SIZE (e.g. 50k or 44.6m)')
    selection.add_option(
        '--max-filesize',
        metavar='SIZE', dest='max_filesize', default=None,
        help='Do not download any videos larger than SIZE (e.g. 50k or 44.6m)')
    selection.add_option(
        '--date',
        metavar='DATE', dest='date', default=None,
        help='Download only videos uploaded in this date')
    selection.add_option(
        '--datebefore',
        metavar='DATE', dest='datebefore', default=None,
        help='Download only videos uploaded on or before this date (i.e. inclusive)')
    selection.add_option(
        '--dateafter',
        metavar='DATE', dest='dateafter', default=None,
        help='Download only videos uploaded on or after this date (i.e. inclusive)')
    selection.add_option(
        '--min-views',
        metavar='COUNT', dest='min_views', default=None, type=int,
        help='Do not download any videos with less than COUNT views')
    selection.add_option(
        '--max-views',
        metavar='COUNT', dest='max_views', default=None, type=int,
        help='Do not download any videos with more than COUNT views')
    selection.add_option(
        '--match-filter',
        metavar='FILTER', dest='match_filter', default=None,
        help=(
            'Generic video filter. '
            'Specify any key (see the "OUTPUT TEMPLATE" for a list of available keys) to '
            'match if the key is present, '
            '!key to check if the key is not present, '
            'key > NUMBER (like "comment_count > 12", also works with '
            '>=, <, <=, !=, =) to compare against a number, '
            'key = \'LITERAL\' (like "uploader = \'Mike Smith\'", also works with !=) '
            'to match against a string literal '
            'and & to require multiple matches. '
            'Values which are not known are excluded unless you '
            'put a question mark (?) after the operator. '
            'For example, to only match videos that have been liked more than '
            '100 times and disliked less than 50 times (or the dislike '
            'functionality is not available at the given service), but who '
            'also have a description, use --match-filter '
            '"like_count > 100 & dislike_count <? 50 & description" .'
        ))
    selection.add_option(
        '--no-playlist',
        action='store_true', dest='noplaylist', default=False,
        help='Download only the video, if the URL refers to a video and a playlist.')
    selection.add_option(
        '--yes-playlist',
        action='store_false', dest='noplaylist', default=False,
        help='Download the playlist, if the URL refers to a video and a playlist.')
    selection.add_option(
        '--age-limit',
        metavar='YEARS', dest='age_limit', default=None, type=int,
        help='Download only videos suitable for the given age')
    selection.add_option(
        '--download-archive', metavar='FILE',
        dest='download_archive',
        help='Download only videos not listed in the archive file. Record the IDs of all downloaded videos in it.')
    selection.add_option(
        '--break-on-existing',
        action='store_true', dest='break_on_existing', default=False,
        help="Stop the download process after attempting to download a file that's in the archive.")
    selection.add_option(
        '--include-ads',
        dest='include_ads', action='store_true',
        help='Download advertisements as well (experimental)')

    authentication = optparse.OptionGroup(parser, 'Authentication Options')
    authentication.add_option(
        '-u', '--username',
        dest='username', metavar='USERNAME',
        help='Login with this account ID')
    authentication.add_option(
        '-p', '--password',
        dest='password', metavar='PASSWORD',
        help='Account password. If this option is left out, youtube-dlc will ask interactively.')
    authentication.add_option(
        '-2', '--twofactor',
        dest='twofactor', metavar='TWOFACTOR',
        help='Two-factor authentication code')
    authentication.add_option(
        '-n', '--netrc',
        action='store_true', dest='usenetrc', default=False,
        help='Use .netrc authentication data')
    authentication.add_option(
        '--video-password',
        dest='videopassword', metavar='PASSWORD',
        help='Video password (vimeo, smotri, youku)')

    adobe_pass = optparse.OptionGroup(parser, 'Adobe Pass Options')
    adobe_pass.add_option(
        '--ap-mso',
        dest='ap_mso', metavar='MSO',
        help='Adobe Pass multiple-system operator (TV provider) identifier, use --ap-list-mso for a list of available MSOs')
    adobe_pass.add_option(
        '--ap-username',
        dest='ap_username', metavar='USERNAME',
        help='Multiple-system operator account login')
    adobe_pass.add_option(
        '--ap-password',
        dest='ap_password', metavar='PASSWORD',
        help='Multiple-system operator account password. If this option is left out, youtube-dlc will ask interactively.')
    adobe_pass.add_option(
        '--ap-list-mso',
        action='store_true', dest='ap_list_mso', default=False,
        help='List all supported multiple-system operators')

    video_format = optparse.OptionGroup(parser, 'Video Format Options')
    video_format.add_option(
        '-f', '--format',
        action='store', dest='format', metavar='FORMAT', default=None,
        help='Video format code, see the "FORMAT SELECTION" for all the info')
    video_format.add_option(
        '--all-formats',
        action='store_const', dest='format', const='all',
        help='Download all available video formats')
    video_format.add_option(
        '--prefer-free-formats',
        action='store_true', dest='prefer_free_formats', default=False,
        help='Prefer free video formats unless a specific one is requested')
    video_format.add_option(
        '-F', '--list-formats',
        action='store_true', dest='listformats',
        help='List all available formats of requested videos')
    video_format.add_option(
        '--youtube-include-dash-manifest',
        action='store_true', dest='youtube_include_dash_manifest', default=True,
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--youtube-skip-dash-manifest',
        action='store_false', dest='youtube_include_dash_manifest',
        help='Do not download the DASH manifests and related data on YouTube videos')
    video_format.add_option(
        '--youtube-include-hls-manifest',
        action='store_true', dest='youtube_include_hls_manifest', default=True,
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--youtube-skip-hls-manifest',
        action='store_false', dest='youtube_include_hls_manifest',
        help='Do not download the HLS manifests and related data on YouTube videos')
    video_format.add_option(
        '--merge-output-format',
        action='store', dest='merge_output_format', metavar='FORMAT', default=None,
        help=(
            'If a merge is required (e.g. bestvideo+bestaudio), '
            'output to given container format. One of mkv, mp4, ogg, webm, flv. '
            'Ignored if no merge is required'))

    subtitles = optparse.OptionGroup(parser, 'Subtitle Options')
    subtitles.add_option(
        '--write-sub', '--write-srt',
        action='store_true', dest='writesubtitles', default=False,
        help='Write subtitle file')
    subtitles.add_option(
        '--write-auto-sub', '--write-automatic-sub',
        action='store_true', dest='writeautomaticsub', default=False,
        help='Write automatically generated subtitle file (YouTube only)')
    subtitles.add_option(
        '--all-subs',
        action='store_true', dest='allsubtitles', default=False,
        help='Download all the available subtitles of the video')
    subtitles.add_option(
        '--list-subs',
        action='store_true', dest='listsubtitles', default=False,
        help='List all available subtitles for the video')
    subtitles.add_option(
        '--sub-format',
        action='store', dest='subtitlesformat', metavar='FORMAT', default='best',
        help='Subtitle format, accepts formats preference, for example: "srt" or "ass/srt/best"')
    subtitles.add_option(
        '--sub-lang', '--sub-langs', '--srt-lang',
        action='callback', dest='subtitleslangs', metavar='LANGS', type='str',
        default=[], callback=_comma_separated_values_options_callback,
        help='Languages of the subtitles to download (optional) separated by commas, use --list-subs for available language tags')

    downloader = optparse.OptionGroup(parser, 'Download Options')
    downloader.add_option(
        '-r', '--limit-rate', '--rate-limit',
        dest='ratelimit', metavar='RATE',
        help='Maximum download rate in bytes per second (e.g. 50K or 4.2M)')
    downloader.add_option(
        '-R', '--retries',
        dest='retries', metavar='RETRIES', default=10,
        help='Number of retries (default is %default), or "infinite".')
    downloader.add_option(
        '--fragment-retries',
        dest='fragment_retries', metavar='RETRIES', default=10,
        help='Number of retries for a fragment (default is %default), or "infinite" (DASH, hlsnative and ISM)')
    downloader.add_option(
        '--skip-unavailable-fragments',
        action='store_true', dest='skip_unavailable_fragments', default=True,
        help='Skip unavailable fragments (DASH, hlsnative and ISM)')
    downloader.add_option(
        '--abort-on-unavailable-fragment',
        action='store_false', dest='skip_unavailable_fragments',
        help='Abort downloading when some fragment is not available')
    downloader.add_option(
        '--keep-fragments',
        action='store_true', dest='keep_fragments', default=False,
        help='Keep downloaded fragments on disk after downloading is finished; fragments are erased by default')
    downloader.add_option(
        '--buffer-size',
        dest='buffersize', metavar='SIZE', default='1024',
        help='Size of download buffer (e.g. 1024 or 16K) (default is %default)')
    downloader.add_option(
        '--no-resize-buffer',
        action='store_true', dest='noresizebuffer', default=False,
        help='Do not automatically adjust the buffer size. By default, the buffer size is automatically resized from an initial value of SIZE.')
    downloader.add_option(
        '--http-chunk-size',
        dest='http_chunk_size', metavar='SIZE', default=None,
        help='Size of a chunk for chunk-based HTTP downloading (e.g. 10485760 or 10M) (default is disabled). '
             'May be useful for bypassing bandwidth throttling imposed by a webserver (experimental)')
    downloader.add_option(
        '--test',
        action='store_true', dest='test', default=False,
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--playlist-reverse',
        action='store_true',
        help='Download playlist videos in reverse order')
    downloader.add_option(
        '--playlist-random',
        action='store_true',
        help='Download playlist videos in random order')
    downloader.add_option(
        '--xattr-set-filesize',
        dest='xattr_set_filesize', action='store_true',
        help='Set file xattribute ytdl.filesize with expected file size')
    downloader.add_option(
        '--hls-prefer-native',
        dest='hls_prefer_native', action='store_true', default=None,
        help='Use the native HLS downloader instead of ffmpeg')
    downloader.add_option(
        '--hls-prefer-ffmpeg',
        dest='hls_prefer_native', action='store_false', default=None,
        help='Use ffmpeg instead of the native HLS downloader')
    downloader.add_option(
        '--hls-use-mpegts',
        dest='hls_use_mpegts', action='store_true',
        help='Use the mpegts container for HLS videos, allowing to play the '
             'video while downloading (some players may not be able to play it)')
    downloader.add_option(
        '--external-downloader',
        dest='external_downloader', metavar='COMMAND',
        help='Use the specified external downloader. '
             'Currently supports %s' % ','.join(list_external_downloaders()))
    downloader.add_option(
        '--external-downloader-args',
        dest='external_downloader_args', metavar='ARGS',
        help='Give these arguments to the external downloader')

    workarounds = optparse.OptionGroup(parser, 'Workarounds')
    workarounds.add_option(
        '--encoding',
        dest='encoding', metavar='ENCODING',
        help='Force the specified encoding (experimental)')
    workarounds.add_option(
        '--no-check-certificate',
        action='store_true', dest='no_check_certificate', default=False,
        help='Suppress HTTPS certificate validation')
    workarounds.add_option(
        '--prefer-insecure',
        '--prefer-unsecure', action='store_true', dest='prefer_insecure',
        help='Use an unencrypted connection to retrieve information about the video. (Currently supported only for YouTube)')
    workarounds.add_option(
        '--user-agent',
        metavar='UA', dest='user_agent',
        help='Specify a custom user agent')
    workarounds.add_option(
        '--referer',
        metavar='URL', dest='referer', default=None,
        help='Specify a custom referer, use if the video access is restricted to one domain',
    )
    workarounds.add_option(
        '--add-header',
        metavar='FIELD:VALUE', dest='headers', action='append',
        help='Specify a custom HTTP header and its value, separated by a colon \':\'. You can use this option multiple times',
    )
    workarounds.add_option(
        '--bidi-workaround',
        dest='bidi_workaround', action='store_true',
        help='Work around terminals that lack bidirectional text support. Requires bidiv or fribidi executable in PATH')
    workarounds.add_option(
        '--sleep-interval', '--min-sleep-interval', metavar='SECONDS',
        dest='sleep_interval', type=float,
        help=(
            'Number of seconds to sleep before each download when used alone '
            'or a lower bound of a range for randomized sleep before each download '
            '(minimum possible number of seconds to sleep) when used along with '
            '--max-sleep-interval.'))
    workarounds.add_option(
        '--max-sleep-interval', metavar='SECONDS',
        dest='max_sleep_interval', type=float,
        help=(
            'Upper bound of a range for randomized sleep before each download '
            '(maximum possible number of seconds to sleep). Must only be used '
            'along with --min-sleep-interval.'))
    workarounds.add_option(
        '--sleep-subtitles',
        dest='sleep_interval_subtitles', default=0, type=int,
        help='Enforce sleep interval on subtitles as well')

    verbosity = optparse.OptionGroup(parser, 'Verbosity / Simulation Options')
    verbosity.add_option(
        '-q', '--quiet',
        action='store_true', dest='quiet', default=False,
        help='Activate quiet mode')
    verbosity.add_option(
        '--no-warnings',
        dest='no_warnings', action='store_true', default=False,
        help='Ignore warnings')
    verbosity.add_option(
        '-s', '--simulate',
        action='store_true', dest='simulate', default=False,
        help='Do not download the video and do not write anything to disk')
    verbosity.add_option(
        '--skip-download',
        action='store_true', dest='skip_download', default=False,
        help='Do not download the video')
    verbosity.add_option(
        '-g', '--get-url',
        action='store_true', dest='geturl', default=False,
        help='Simulate, quiet but print URL')
    verbosity.add_option(
        '-e', '--get-title',
        action='store_true', dest='gettitle', default=False,
        help='Simulate, quiet but print title')
    verbosity.add_option(
        '--get-id',
        action='store_true', dest='getid', default=False,
        help='Simulate, quiet but print id')
    verbosity.add_option(
        '--get-thumbnail',
        action='store_true', dest='getthumbnail', default=False,
        help='Simulate, quiet but print thumbnail URL')
    verbosity.add_option(
        '--get-description',
        action='store_true', dest='getdescription', default=False,
        help='Simulate, quiet but print video description')
    verbosity.add_option(
        '--get-duration',
        action='store_true', dest='getduration', default=False,
        help='Simulate, quiet but print video length')
    verbosity.add_option(
        '--get-filename',
        action='store_true', dest='getfilename', default=False,
        help='Simulate, quiet but print output filename')
    verbosity.add_option(
        '--get-format',
        action='store_true', dest='getformat', default=False,
        help='Simulate, quiet but print output format')
    verbosity.add_option(
        '-j', '--dump-json',
        action='store_true', dest='dumpjson', default=False,
        help='Simulate, quiet but print JSON information. See the "OUTPUT TEMPLATE" for a description of available keys.')
    verbosity.add_option(
        '-J', '--dump-single-json',
        action='store_true', dest='dump_single_json', default=False,
        help='Simulate, quiet but print JSON information for each command-line argument. If the URL refers to a playlist, dump the whole playlist information in a single line.')
    verbosity.add_option(
        '--print-json',
        action='store_true', dest='print_json', default=False,
        help='Be quiet and print the video information as JSON (video is still being downloaded).',
    )
    verbosity.add_option(
        '--newline',
        action='store_true', dest='progress_with_newline', default=False,
        help='Output progress bar as new lines')
    verbosity.add_option(
        '--no-progress',
        action='store_true', dest='noprogress', default=False,
        help='Do not print progress bar')
    verbosity.add_option(
        '--console-title',
        action='store_true', dest='consoletitle', default=False,
        help='Display progress in console titlebar')
    verbosity.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print various debugging information')
    verbosity.add_option(
        '--dump-pages', '--dump-intermediate-pages',
        action='store_true', dest='dump_intermediate_pages', default=False,
        help='Print downloaded pages encoded using base64 to debug problems (very verbose)')
    verbosity.add_option(
        '--write-pages',
        action='store_true', dest='write_pages', default=False,
        help='Write downloaded intermediary pages to files in the current directory to debug problems')
    verbosity.add_option(
        '--youtube-print-sig-code',
        action='store_true', dest='youtube_print_sig_code', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--print-traffic', '--dump-headers',
        dest='debug_printtraffic', action='store_true', default=False,
        help='Display sent and read HTTP traffic')
    verbosity.add_option(
        '-C', '--call-home',
        dest='call_home', action='store_true', default=False,
        help='Contact the youtube-dlc server for debugging')
    verbosity.add_option(
        '--no-call-home',
        dest='call_home', action='store_false', default=False,
        help='Do NOT contact the youtube-dlc server for debugging')

    filesystem = optparse.OptionGroup(parser, 'Filesystem Options')
    filesystem.add_option(
        '-a', '--batch-file',
        dest='batchfile', metavar='FILE',
        help="File containing URLs to download ('-' for stdin), one URL per line. "
             "Lines starting with '#', ';' or ']' are considered as comments and ignored.")
    filesystem.add_option(
        '--id', default=False,
        action='store_true', dest='useid', help='Use only video ID in file name')
    filesystem.add_option(
        '-o', '--output',
        dest='outtmpl', metavar='TEMPLATE',
        help=('Output filename template, see the "OUTPUT TEMPLATE" for all the info'))
    filesystem.add_option(
        '--autonumber-size',
        dest='autonumber_size', metavar='NUMBER', type=int,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '--autonumber-start',
        dest='autonumber_start', metavar='NUMBER', default=1, type=int,
        help='Specify the start value for %(autonumber)s (default is %default)')
    filesystem.add_option(
        '--restrict-filenames',
        action='store_true', dest='restrictfilenames', default=False,
        help='Restrict filenames to only ASCII characters, and avoid "&" and spaces in filenames')
    filesystem.add_option(
        '-A', '--auto-number',
        action='store_true', dest='autonumber', default=False,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-t', '--title',
        action='store_true', dest='usetitle', default=False,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-l', '--literal', default=False,
        action='store_true', dest='usetitle',
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-w', '--no-overwrites',
        action='store_true', dest='nooverwrites', default=False,
        help='Do not overwrite files')
    filesystem.add_option(
        '-c', '--continue',
        action='store_true', dest='continue_dl', default=True,
        help='Force resume of partially downloaded files. By default, youtube-dlc will resume downloads if possible.')
    filesystem.add_option(
        '--no-continue',
        action='store_false', dest='continue_dl',
        help='Do not resume partially downloaded files (restart from beginning)')
    filesystem.add_option(
        '--no-part',
        action='store_true', dest='nopart', default=False,
        help='Do not use .part files - write directly into output file')
    filesystem.add_option(
        '--no-mtime',
        action='store_false', dest='updatetime', default=True,
        help='Do not use the Last-modified header to set the file modification time')
    filesystem.add_option(
        '--write-description',
        action='store_true', dest='writedescription', default=False,
        help='Write video description to a .description file')
    filesystem.add_option(
        '--write-info-json',
        action='store_true', dest='writeinfojson', default=False,
        help='Write video metadata to a .info.json file')
    filesystem.add_option(
        '--write-annotations',
        action='store_true', dest='writeannotations', default=False,
        help='Write video annotations to a .annotations.xml file')
    filesystem.add_option(
        '--load-info-json', '--load-info',
        dest='load_info_filename', metavar='FILE',
        help='JSON file containing the video information (created with the "--write-info-json" option)')
    filesystem.add_option(
        '--cookies',
        dest='cookiefile', metavar='FILE',
        help='File to read cookies from and dump cookie jar in')
    filesystem.add_option(
        '--cache-dir', dest='cachedir', default=None, metavar='DIR',
        help='Location in the filesystem where youtube-dlc can store some downloaded information permanently. By default $XDG_CACHE_HOME/youtube-dlc or ~/.cache/youtube-dlc . At the moment, only YouTube player files (for videos with obfuscated signatures) are cached, but that may change.')
    filesystem.add_option(
        '--no-cache-dir', action='store_const', const=False, dest='cachedir',
        help='Disable filesystem caching')
    filesystem.add_option(
        '--rm-cache-dir',
        action='store_true', dest='rm_cachedir',
        help='Delete all filesystem cache files')
    filesystem.add_option(
        '--trim-file-name', dest='trim_file_name', default=0, type=int,
        help='Limit the filename length (extension excluded)')

    thumbnail = optparse.OptionGroup(parser, 'Thumbnail images')
    thumbnail.add_option(
        '--write-thumbnail',
        action='store_true', dest='writethumbnail', default=False,
        help='Write thumbnail image to disk')
    thumbnail.add_option(
        '--write-all-thumbnails',
        action='store_true', dest='write_all_thumbnails', default=False,
        help='Write all thumbnail image formats to disk')
    thumbnail.add_option(
        '--list-thumbnails',
        action='store_true', dest='list_thumbnails', default=False,
        help='Simulate and list all available thumbnail formats')

    postproc = optparse.OptionGroup(parser, 'Post-processing Options')
    postproc.add_option(
        '-x', '--extract-audio',
        action='store_true', dest='extractaudio', default=False,
        help='Convert video files to audio-only files (requires ffmpeg or avconv and ffprobe or avprobe)')
    postproc.add_option(
        '--audio-format', metavar='FORMAT', dest='audioformat', default='best',
        help='Specify audio format: "best", "aac", "flac", "mp3", "m4a", "opus", "vorbis", or "wav"; "%default" by default; No effect without -x')
    postproc.add_option(
        '--audio-quality', metavar='QUALITY',
        dest='audioquality', default='5',
        help='Specify ffmpeg/avconv audio quality, insert a value between 0 (better) and 9 (worse) for VBR or a specific bitrate like 128K (default %default)')
    postproc.add_option(
        '--remux-video',
        metavar='FORMAT', dest='remuxvideo', default=None,
        help='Remux the video to another container format if necessary (currently supported: mp4|mkv, target container format must support video / audio encoding, remuxing may fail)')
    postproc.add_option(
        '--recode-video',
        metavar='FORMAT', dest='recodevideo', default=None,
        help='Encode the video to another format if necessary (currently supported: mp4|flv|ogg|webm|mkv|avi)')
    postproc.add_option(
        '--postprocessor-args',
        dest='postprocessor_args', metavar='ARGS',
        help='Give these arguments to the postprocessor')
    postproc.add_option(
        '-k', '--keep-video',
        action='store_true', dest='keepvideo', default=False,
        help='Keep the video file on disk after the post-processing; the video is erased by default')
    postproc.add_option(
        '--no-post-overwrites',
        action='store_true', dest='nopostoverwrites', default=False,
        help='Do not overwrite post-processed files; the post-processed files are overwritten by default')
    postproc.add_option(
        '--embed-subs',
        action='store_true', dest='embedsubtitles', default=False,
        help='Embed subtitles in the video (only for mp4, webm and mkv videos)')
    postproc.add_option(
        '--embed-thumbnail',
        action='store_true', dest='embedthumbnail', default=False,
        help='Embed thumbnail in the audio as cover art')
    postproc.add_option(
        '--add-metadata',
        action='store_true', dest='addmetadata', default=False,
        help='Write metadata to the video file')
    postproc.add_option(
        '--metadata-from-title',
        metavar='FORMAT', dest='metafromtitle',
        help='Parse additional metadata like song title / artist from the video title. '
             'The format syntax is the same as --output. Regular expression with '
             'named capture groups may also be used. '
             'The parsed parameters replace existing values. '
             'Example: --metadata-from-title "%(artist)s - %(title)s" matches a title like '
             '"Coldplay - Paradise". '
             'Example (regex): --metadata-from-title "(?P<artist>.+?) - (?P<title>.+)"')
    postproc.add_option(
        '--xattrs',
        action='store_true', dest='xattrs', default=False,
        help='Write metadata to the video file\'s xattrs (using dublin core and xdg standards)')
    postproc.add_option(
        '--fixup',
        metavar='POLICY', dest='fixup', default='detect_or_warn',
        help='Automatically correct known faults of the file. '
             'One of never (do nothing), warn (only emit a warning), '
             'detect_or_warn (the default; fix file if we can, warn otherwise)')
    postproc.add_option(
        '--prefer-avconv',
        action='store_false', dest='prefer_ffmpeg',
        help='Prefer avconv over ffmpeg for running the postprocessors')
    postproc.add_option(
        '--prefer-ffmpeg',
        action='store_true', dest='prefer_ffmpeg',
        help='Prefer ffmpeg over avconv for running the postprocessors (default)')
    postproc.add_option(
        '--ffmpeg-location', '--avconv-location', metavar='PATH',
        dest='ffmpeg_location',
        help='Location of the ffmpeg/avconv binary; either the path to the binary or its containing directory.')
    postproc.add_option(
        '--exec',
        metavar='CMD', dest='exec_cmd',
        help='Execute a command on the file after downloading and post-processing, similar to find\'s -exec syntax. Example: --exec \'adb push {} /sdcard/Music/ && rm {}\'')
    postproc.add_option(
        '--convert-subs', '--convert-subtitles',
        metavar='FORMAT', dest='convertsubtitles', default=None,
        help='Convert the subtitles to other format (currently supported: srt|ass|vtt|lrc)')

    extractor = optparse.OptionGroup(parser, 'Extractor Options')
    extractor.add_option(
        '--allow-dynamic-mpd',
        action='store_true', dest='dynamic_mpd', default=True,
        help=optparse.SUPPRESS_HELP)
    extractor.add_option(
        '--ignore-dynamic-mpd',
        action='store_false', dest='dynamic_mpd',
        help='Do not process dynamic DASH manifests')

    parser.add_option_group(general)
    parser.add_option_group(network)
    parser.add_option_group(geo)
    parser.add_option_group(selection)
    parser.add_option_group(downloader)
    parser.add_option_group(filesystem)
    parser.add_option_group(thumbnail)
    parser.add_option_group(verbosity)
    parser.add_option_group(workarounds)
    parser.add_option_group(video_format)
    parser.add_option_group(subtitles)
    parser.add_option_group(authentication)
    parser.add_option_group(adobe_pass)
    parser.add_option_group(postproc)
    parser.add_option_group(extractor)

    if overrideArguments is not None:
        opts, args = parser.parse_args(overrideArguments)
        if opts.verbose:
            write_string('[debug] Override config: ' + repr(overrideArguments) + '\n')
    else:
        def compat_conf(conf):
            if sys.version_info < (3,):
                return [a.decode(preferredencoding(), 'replace') for a in conf]
            return conf

        command_line_conf = compat_conf(sys.argv[1:])
        opts, args = parser.parse_args(command_line_conf)

        system_conf = user_conf = custom_conf = []

        if '--config-location' in command_line_conf:
            location = compat_expanduser(opts.config_location)
            if os.path.isdir(location):
                location = os.path.join(location, 'youtube-dlc.conf')
            if not os.path.exists(location):
                parser.error('config-location %s does not exist.' % location)
            custom_conf = _readOptions(location)
        elif '--ignore-config' in command_line_conf:
            pass
        else:
            system_conf = _readOptions('/etc/youtube-dlc.conf')
            if '--ignore-config' not in system_conf:
                user_conf = _readUserConf()

        argv = system_conf + user_conf + custom_conf + command_line_conf
        opts, args = parser.parse_args(argv)
        if opts.verbose:
            for conf_label, conf in (
                    ('System config', system_conf),
                    ('User config', user_conf),
                    ('Custom config', custom_conf),
                    ('Command-line args', command_line_conf)):
                write_string('[debug] %s: %s\n' % (conf_label, repr(_hide_login_info(conf))))

    return parser, opts, args

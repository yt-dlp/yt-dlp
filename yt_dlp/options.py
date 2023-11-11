import collections
import contextlib
import optparse
import os.path
import re
import shlex
import shutil
import string
import sys

from .compat import compat_expanduser
from .cookies import SUPPORTED_BROWSERS, SUPPORTED_KEYRINGS
from .downloader.external import list_external_downloaders
from .postprocessor import (
    FFmpegExtractAudioPP,
    FFmpegMergerPP,
    FFmpegSubtitlesConvertorPP,
    FFmpegThumbnailsConvertorPP,
    FFmpegVideoRemuxerPP,
    SponsorBlockPP,
)
from .postprocessor.modify_chapters import DEFAULT_SPONSORBLOCK_CHAPTER_TITLE
from .update import UPDATE_SOURCES, detect_variant, is_non_updateable
from .utils import (
    OUTTMPL_TYPES,
    POSTPROCESS_WHEN,
    Config,
    deprecation_warning,
    expand_path,
    format_field,
    get_executable_path,
    get_system_config_dirs,
    get_user_config_dirs,
    join_nonempty,
    orderedSet_from_options,
    remove_end,
    variadic,
    write_string,
)
from .version import CHANNEL, __version__


def parseOpts(overrideArguments=None, ignore_config_files='if_override'):
    PACKAGE_NAME = 'yt-dlp'

    root = Config(create_parser())
    if ignore_config_files == 'if_override':
        ignore_config_files = overrideArguments is not None

    def read_config(*paths):
        path = os.path.join(*paths)
        conf = Config.read_file(path, default=None)
        if conf is not None:
            return conf, path

    def _load_from_config_dirs(config_dirs):
        for config_dir in config_dirs:
            head, tail = os.path.split(config_dir)
            assert tail == PACKAGE_NAME or config_dir == os.path.join(compat_expanduser('~'), f'.{PACKAGE_NAME}')

            yield read_config(head, f'{PACKAGE_NAME}.conf')
            if tail.startswith('.'):  # ~/.PACKAGE_NAME
                yield read_config(head, f'{PACKAGE_NAME}.conf.txt')
            yield read_config(config_dir, 'config')
            yield read_config(config_dir, 'config.txt')

    def add_config(label, path=None, func=None):
        """ Adds config and returns whether to continue """
        if root.parse_known_args()[0].ignoreconfig:
            return False
        elif func:
            assert path is None
            args, current_path = next(
                filter(None, _load_from_config_dirs(func(PACKAGE_NAME))), (None, None))
        else:
            current_path = os.path.join(path, 'yt-dlp.conf')
            args = Config.read_file(current_path, default=None)
        if args is not None:
            root.append_config(args, current_path, label=label)
        return True

    def load_configs():
        yield not ignore_config_files
        yield add_config('Portable', get_executable_path())
        yield add_config('Home', expand_path(root.parse_known_args()[0].paths.get('home', '')).strip())
        yield add_config('User', func=get_user_config_dirs)
        yield add_config('System', func=get_system_config_dirs)

    opts = optparse.Values({'verbose': True, 'print_help': False})
    try:
        try:
            if overrideArguments is not None:
                root.append_config(overrideArguments, label='Override')
            else:
                root.append_config(sys.argv[1:], label='Command-line')
            loaded_all_configs = all(load_configs())
        except ValueError as err:
            raise root.parser.error(err)

        if loaded_all_configs:
            # If ignoreconfig is found inside the system configuration file,
            # the user configuration is removed
            if root.parse_known_args()[0].ignoreconfig:
                user_conf = next((i for i, conf in enumerate(root.configs) if conf.label == 'User'), None)
                if user_conf is not None:
                    root.configs.pop(user_conf)

        try:
            root.configs[0].load_configs()  # Resolve any aliases using --config-location
        except ValueError as err:
            raise root.parser.error(err)

        opts, args = root.parse_args()
    except optparse.OptParseError:
        with contextlib.suppress(optparse.OptParseError):
            opts, _ = root.parse_known_args(strict=False)
        raise
    except (SystemExit, KeyboardInterrupt):
        opts.verbose = False
        raise
    finally:
        verbose = opts.verbose and f'\n{root}'.replace('\n| ', '\n[debug] ')[1:]
        if verbose:
            write_string(f'{verbose}\n')
        if opts.print_help:
            if verbose:
                write_string('\n')
            root.parser.print_help()
    if opts.print_help:
        sys.exit()
    return root.parser, opts, args


class _YoutubeDLHelpFormatter(optparse.IndentedHelpFormatter):
    def __init__(self):
        # No need to wrap help messages if we're on a wide console
        max_width = shutil.get_terminal_size().columns or 80
        # The % is chosen to get a pretty output in README.md
        super().__init__(width=max_width, max_help_position=int(0.45 * max_width))

    @staticmethod
    def format_option_strings(option):
        """ ('-o', '--option') -> -o, --format METAVAR """
        opts = join_nonempty(
            option._short_opts and option._short_opts[0],
            option._long_opts and option._long_opts[0],
            delim=', ')
        if option.takes_value():
            opts += f' {option.metavar}'
        return opts


class _YoutubeDLOptionParser(optparse.OptionParser):
    # optparse is deprecated since python 3.2. So assume a stable interface even for private methods
    ALIAS_DEST = '_triggered_aliases'
    ALIAS_TRIGGER_LIMIT = 100

    def __init__(self):
        super().__init__(
            prog='yt-dlp' if detect_variant() == 'source' else None,
            version=__version__,
            usage='%prog [OPTIONS] URL [URL...]',
            epilog='See full documentation at  https://github.com/yt-dlp/yt-dlp#readme',
            formatter=_YoutubeDLHelpFormatter(),
            conflict_handler='resolve',
        )
        self.set_default(self.ALIAS_DEST, collections.defaultdict(int))

    _UNKNOWN_OPTION = (optparse.BadOptionError, optparse.AmbiguousOptionError)
    _BAD_OPTION = optparse.OptionValueError

    def parse_known_args(self, args=None, values=None, strict=True):
        """Same as parse_args, but ignore unknown switches. Similar to argparse.parse_known_args"""
        self.rargs, self.largs = self._get_args(args), []
        self.values = values or self.get_default_values()
        while self.rargs:
            arg = self.rargs[0]
            try:
                if arg == '--':
                    del self.rargs[0]
                    break
                elif arg.startswith('--'):
                    self._process_long_opt(self.rargs, self.values)
                elif arg.startswith('-') and arg != '-':
                    self._process_short_opts(self.rargs, self.values)
                elif self.allow_interspersed_args:
                    self.largs.append(self.rargs.pop(0))
                else:
                    break
            except optparse.OptParseError as err:
                if isinstance(err, self._UNKNOWN_OPTION):
                    self.largs.append(err.opt_str)
                elif strict:
                    if isinstance(err, self._BAD_OPTION):
                        self.error(str(err))
                    raise
        return self.check_values(self.values, self.largs)

    def error(self, msg):
        msg = f'{self.get_prog_name()}: error: {str(msg).strip()}\n'
        raise optparse.OptParseError(f'{self.get_usage()}\n{msg}' if self.usage else msg)

    def _get_args(self, args):
        return sys.argv[1:] if args is None else list(args)

    def _match_long_opt(self, opt):
        """Improve ambiguous argument resolution by comparing option objects instead of argument strings"""
        try:
            return super()._match_long_opt(opt)
        except optparse.AmbiguousOptionError as e:
            if len({self._long_opt[p] for p in e.possibilities}) == 1:
                return e.possibilities[0]
            raise


def create_parser():
    def _list_from_options_callback(option, opt_str, value, parser, append=True, delim=',', process=str.strip):
        # append can be True, False or -1 (prepend)
        current = list(getattr(parser.values, option.dest)) if append else []
        value = list(filter(None, [process(value)] if delim is None else map(process, value.split(delim))))
        setattr(
            parser.values, option.dest,
            current + value if append is True else value + current)

    def _set_from_options_callback(
            option, opt_str, value, parser, allowed_values, delim=',', aliases={},
            process=lambda x: x.lower().strip()):
        values = [process(value)] if delim is None else map(process, value.split(delim))
        try:
            requested = orderedSet_from_options(values, collections.ChainMap(aliases, {'all': allowed_values}),
                                                start=getattr(parser.values, option.dest))
        except ValueError as e:
            raise optparse.OptionValueError(f'wrong {option.metavar} for {opt_str}: {e.args[0]}')

        setattr(parser.values, option.dest, set(requested))

    def _dict_from_options_callback(
            option, opt_str, value, parser,
            allowed_keys=r'[\w-]+', delimiter=':', default_key=None, process=None, multiple_keys=True,
            process_key=str.lower, append=False):

        out_dict = dict(getattr(parser.values, option.dest))
        multiple_args = not isinstance(value, str)
        if multiple_keys:
            allowed_keys = fr'({allowed_keys})(,({allowed_keys}))*'
        mobj = re.match(
            fr'(?is)(?P<keys>{allowed_keys}){delimiter}(?P<val>.*)$',
            value[0] if multiple_args else value)
        if mobj is not None:
            keys, val = mobj.group('keys').split(','), mobj.group('val')
            if multiple_args:
                val = [val, *value[1:]]
        elif default_key is not None:
            keys, val = variadic(default_key), value
        else:
            raise optparse.OptionValueError(
                f'wrong {opt_str} formatting; it should be {option.metavar}, not "{value}"')
        try:
            keys = map(process_key, keys) if process_key else keys
            val = process(val) if process else val
        except Exception as err:
            raise optparse.OptionValueError(f'wrong {opt_str} formatting; {err}')
        for key in keys:
            out_dict[key] = out_dict.get(key, []) + [val] if append else val
        setattr(parser.values, option.dest, out_dict)

    def when_prefix(default):
        return {
            'default': {},
            'type': 'str',
            'action': 'callback',
            'callback': _dict_from_options_callback,
            'callback_kwargs': {
                'allowed_keys': '|'.join(map(re.escape, POSTPROCESS_WHEN)),
                'default_key': default,
                'multiple_keys': False,
                'append': True,
            },
        }

    parser = _YoutubeDLOptionParser()
    alias_group = optparse.OptionGroup(parser, 'Aliases')
    Formatter = string.Formatter()

    def _create_alias(option, opt_str, value, parser):
        aliases, opts = value
        try:
            nargs = len({i if f == '' else f
                         for i, (_, f, _, _) in enumerate(Formatter.parse(opts)) if f is not None})
            opts.format(*map(str, range(nargs)))  # validate
        except Exception as err:
            raise optparse.OptionValueError(f'wrong {opt_str} OPTIONS formatting; {err}')
        if alias_group not in parser.option_groups:
            parser.add_option_group(alias_group)

        aliases = (x if x.startswith('-') else f'--{x}' for x in map(str.strip, aliases.split(',')))
        try:
            args = [f'ARG{i}' for i in range(nargs)]
            alias_group.add_option(
                *aliases, nargs=nargs, dest=parser.ALIAS_DEST, type='str' if nargs else None,
                metavar=' '.join(args), help=opts.format(*args), action='callback',
                callback=_alias_callback, callback_kwargs={'opts': opts, 'nargs': nargs})
        except Exception as err:
            raise optparse.OptionValueError(f'wrong {opt_str} formatting; {err}')

    def _alias_callback(option, opt_str, value, parser, opts, nargs):
        counter = getattr(parser.values, option.dest)
        counter[opt_str] += 1
        if counter[opt_str] > parser.ALIAS_TRIGGER_LIMIT:
            raise optparse.OptionValueError(f'Alias {opt_str} exceeded invocation limit')
        if nargs == 1:
            value = [value]
        assert (nargs == 0 and value is None) or len(value) == nargs
        parser.rargs[:0] = shlex.split(
            opts if value is None else opts.format(*map(shlex.quote, value)))

    general = optparse.OptionGroup(parser, 'General Options')
    general.add_option(
        '-h', '--help', dest='print_help', action='store_true',
        help='Print this help text and exit')
    general.add_option(
        '--version',
        action='version',
        help='Print program version and exit')
    general.add_option(
        '-U', '--update',
        action='store_const', dest='update_self', const=CHANNEL,
        help=format_field(
            is_non_updateable(), None, 'Check if updates are available. %s',
            default=f'Update this program to the latest {CHANNEL} version'))
    general.add_option(
        '--no-update',
        action='store_false', dest='update_self',
        help='Do not check for updates (default)')
    general.add_option(
        '--update-to',
        action='store', dest='update_self', metavar='[CHANNEL]@[TAG]',
        help=(
            'Upgrade/downgrade to a specific version. CHANNEL can be a repository as well. '
            f'CHANNEL and TAG default to "{CHANNEL.partition("@")[0]}" and "latest" respectively if omitted; '
            f'See "UPDATE" for details. Supported channels: {", ".join(UPDATE_SOURCES)}'))
    general.add_option(
        '-i', '--ignore-errors',
        action='store_true', dest='ignoreerrors',
        help='Ignore download and postprocessing errors. The download will be considered successful even if the postprocessing fails')
    general.add_option(
        '--no-abort-on-error',
        action='store_const', dest='ignoreerrors', const='only_download',
        help='Continue with next video on download errors; e.g. to skip unavailable videos in a playlist (default)')
    general.add_option(
        '--abort-on-error', '--no-ignore-errors',
        action='store_false', dest='ignoreerrors',
        help='Abort downloading of further videos if an error occurs (Alias: --no-ignore-errors)')
    general.add_option(
        '--dump-user-agent',
        action='store_true', dest='dump_user_agent', default=False,
        help='Display the current user-agent and exit')
    general.add_option(
        '--list-extractors',
        action='store_true', dest='list_extractors', default=False,
        help='List all supported extractors and exit')
    general.add_option(
        '--extractor-descriptions',
        action='store_true', dest='list_extractor_descriptions', default=False,
        help='Output descriptions of all supported extractors and exit')
    general.add_option(
        '--use-extractors', '--ies',
        action='callback', dest='allowed_extractors', metavar='NAMES', type='str',
        default=[], callback=_list_from_options_callback,
        help=(
            'Extractor names to use separated by commas. '
            'You can also use regexes, "all", "default" and "end" (end URL matching); '
            'e.g. --ies "holodex.*,end,youtube". '
            'Prefix the name with a "-" to exclude it, e.g. --ies default,-generic. '
            'Use --list-extractors for a list of extractor names. (Alias: --ies)'))
    general.add_option(
        '--force-generic-extractor',
        action='store_true', dest='force_generic_extractor', default=False,
        help=optparse.SUPPRESS_HELP)
    general.add_option(
        '--default-search',
        dest='default_search', metavar='PREFIX',
        help=(
            'Use this prefix for unqualified URLs. '
            'E.g. "gvsearch2:python" downloads two videos from google videos for the search term "python". '
            'Use the value "auto" to let yt-dlp guess ("auto_warning" to emit a warning when guessing). '
            '"error" just throws an error. The default value "fixup_error" repairs broken URLs, '
            'but emits an error if this is not possible instead of searching'))
    general.add_option(
        '--ignore-config', '--no-config',
        action='store_true', dest='ignoreconfig',
        help=(
            'Don\'t load any more configuration files except those given by --config-locations. '
            'For backward compatibility, if this option is found inside the system configuration file, the user configuration is not loaded. '
            '(Alias: --no-config)'))
    general.add_option(
        '--no-config-locations',
        action='store_const', dest='config_locations', const=[],
        help=(
            'Do not load any custom configuration files (default). When given inside a '
            'configuration file, ignore all previous --config-locations defined in the current file'))
    general.add_option(
        '--config-locations',
        dest='config_locations', metavar='PATH', action='append',
        help=(
            'Location of the main configuration file; either the path to the config or its containing directory '
            '("-" for stdin). Can be used multiple times and inside other configuration files'))
    general.add_option(
        '--flat-playlist',
        action='store_const', dest='extract_flat', const='in_playlist', default=False,
        help='Do not extract the videos of a playlist, only list them')
    general.add_option(
        '--no-flat-playlist',
        action='store_false', dest='extract_flat',
        help='Fully extract the videos of a playlist (default)')
    general.add_option(
        '--live-from-start',
        action='store_true', dest='live_from_start',
        help='Download livestreams from the start. Currently only supported for YouTube (Experimental)')
    general.add_option(
        '--no-live-from-start',
        action='store_false', dest='live_from_start',
        help='Download livestreams from the current time (default)')
    general.add_option(
        '--wait-for-video',
        dest='wait_for_video', metavar='MIN[-MAX]', default=None,
        help=(
            'Wait for scheduled streams to become available. '
            'Pass the minimum number of seconds (or range) to wait between retries'))
    general.add_option(
        '--no-wait-for-video',
        dest='wait_for_video', action='store_const', const=None,
        help='Do not wait for scheduled streams (default)')
    general.add_option(
        '--mark-watched',
        action='store_true', dest='mark_watched', default=False,
        help='Mark videos watched (even with --simulate)')
    general.add_option(
        '--no-mark-watched',
        action='store_false', dest='mark_watched',
        help='Do not mark videos watched (default)')
    general.add_option(
        '--no-colors', '--no-colours',
        action='store_const', dest='color', const={
            'stdout': 'no_color',
            'stderr': 'no_color',
        },
        help=optparse.SUPPRESS_HELP)
    general.add_option(
        '--color',
        dest='color', metavar='[STREAM:]POLICY', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': 'stdout|stderr',
            'default_key': ['stdout', 'stderr'],
            'process': str.strip,
        }, help=(
            'Whether to emit color codes in output, optionally prefixed by '
            'the STREAM (stdout or stderr) to apply the setting to. '
            'Can be one of "always", "auto" (default), "never", or '
            '"no_color" (use non color terminal sequences). '
            'Can be used multiple times'))
    general.add_option(
        '--compat-options',
        metavar='OPTS', dest='compat_opts', default=set(), type='str',
        action='callback', callback=_set_from_options_callback,
        callback_kwargs={
            'allowed_values': {
                'filename', 'filename-sanitization', 'format-sort', 'abort-on-error', 'format-spec', 'no-playlist-metafiles',
                'multistreams', 'no-live-chat', 'playlist-index', 'list-formats', 'no-direct-merge', 'playlist-match-filter',
                'no-attach-info-json', 'embed-thumbnail-atomicparsley', 'no-external-downloader-progress',
                'embed-metadata', 'seperate-video-versions', 'no-clean-infojson', 'no-keep-subs', 'no-certifi',
                'no-youtube-channel-redirect', 'no-youtube-unavailable-videos', 'no-youtube-prefer-utc-upload-date',
                'prefer-legacy-http-handler', 'manifest-filesize-approx'
            }, 'aliases': {
                'youtube-dl': ['all', '-multistreams', '-playlist-match-filter', '-manifest-filesize-approx'],
                'youtube-dlc': ['all', '-no-youtube-channel-redirect', '-no-live-chat', '-playlist-match-filter', '-manifest-filesize-approx'],
                '2021': ['2022', 'no-certifi', 'filename-sanitization', 'no-youtube-prefer-utc-upload-date'],
                '2022': ['no-external-downloader-progress', 'playlist-match-filter', 'prefer-legacy-http-handler', 'manifest-filesize-approx'],
            }
        }, help=(
            'Options that can help keep compatibility with youtube-dl or youtube-dlc '
            'configurations by reverting some of the changes made in yt-dlp. '
            'See "Differences in default behavior" for details'))
    general.add_option(
        '--alias', metavar='ALIASES OPTIONS', dest='_', type='str', nargs=2,
        action='callback', callback=_create_alias,
        help=(
            'Create aliases for an option string. Unless an alias starts with a dash "-", it is prefixed with "--". '
            'Arguments are parsed according to the Python string formatting mini-language. '
            'E.g. --alias get-audio,-X "-S=aext:{0},abr -x --audio-format {0}" creates options '
            '"--get-audio" and "-X" that takes an argument (ARG0) and expands to '
            '"-S=aext:ARG0,abr -x --audio-format ARG0". All defined aliases are listed in the --help output. '
            'Alias options can trigger more aliases; so be careful to avoid defining recursive options. '
            f'As a safety measure, each alias may be triggered a maximum of {_YoutubeDLOptionParser.ALIAS_TRIGGER_LIMIT} times. '
            'This option can be used multiple times'))

    network = optparse.OptionGroup(parser, 'Network Options')
    network.add_option(
        '--proxy', dest='proxy',
        default=None, metavar='URL',
        help=(
            'Use the specified HTTP/HTTPS/SOCKS proxy. To enable SOCKS proxy, specify a proper scheme, '
            'e.g. socks5://user:pass@127.0.0.1:1080/. Pass in an empty string (--proxy "") for direct connection'))
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
    network.add_option(
        '--enable-file-urls', action='store_true',
        dest='enable_file_urls', default=False,
        help='Enable file:// URLs. This is disabled by default for security reasons.'
    )

    geo = optparse.OptionGroup(parser, 'Geo-restriction')
    geo.add_option(
        '--geo-verification-proxy',
        dest='geo_verification_proxy', default=None, metavar='URL',
        help=(
            'Use this proxy to verify the IP address for some geo-restricted sites. '
            'The default proxy specified by --proxy (or none, if the option is not present) is used for the actual downloading'))
    geo.add_option(
        '--cn-verification-proxy',
        dest='cn_verification_proxy', default=None, metavar='URL',
        help=optparse.SUPPRESS_HELP)
    geo.add_option(
        '--xff', metavar='VALUE',
        dest='geo_bypass', default='default',
        help=(
            'How to fake X-Forwarded-For HTTP header to try bypassing geographic restriction. '
            'One of "default" (only when known to be useful), "never", '
            'an IP block in CIDR notation, or a two-letter ISO 3166-2 country code'))
    geo.add_option(
        '--geo-bypass',
        action='store_const', dest='geo_bypass', const='default',
        help=optparse.SUPPRESS_HELP)
    geo.add_option(
        '--no-geo-bypass',
        action='store_const', dest='geo_bypass', const='never',
        help=optparse.SUPPRESS_HELP)
    geo.add_option(
        '--geo-bypass-country', metavar='CODE', dest='geo_bypass',
        help=optparse.SUPPRESS_HELP)
    geo.add_option(
        '--geo-bypass-ip-block', metavar='IP_BLOCK', dest='geo_bypass',
        help=optparse.SUPPRESS_HELP)

    selection = optparse.OptionGroup(parser, 'Video Selection')
    selection.add_option(
        '--playlist-start',
        dest='playliststart', metavar='NUMBER', default=1, type=int,
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--playlist-end',
        dest='playlistend', metavar='NUMBER', default=None, type=int,
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '-I', '--playlist-items',
        dest='playlist_items', metavar='ITEM_SPEC', default=None,
        help=(
            'Comma separated playlist_index of the items to download. '
            'You can specify a range using "[START]:[STOP][:STEP]". For backward compatibility, START-STOP is also supported. '
            'Use negative indices to count from the right and negative STEP to download in reverse order. '
            'E.g. "-I 1:3,7,-5::2" used on a playlist of size 15 will download the items at index 1,2,3,7,11,13,15'))
    selection.add_option(
        '--match-title',
        dest='matchtitle', metavar='REGEX',
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--reject-title',
        dest='rejecttitle', metavar='REGEX',
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--min-filesize',
        metavar='SIZE', dest='min_filesize', default=None,
        help='Abort download if filesize is smaller than SIZE, e.g. 50k or 44.6M')
    selection.add_option(
        '--max-filesize',
        metavar='SIZE', dest='max_filesize', default=None,
        help='Abort download if filesize is larger than SIZE, e.g. 50k or 44.6M')
    selection.add_option(
        '--date',
        metavar='DATE', dest='date', default=None,
        help=(
            'Download only videos uploaded on this date. '
            'The date can be "YYYYMMDD" or in the format [now|today|yesterday][-N[day|week|month|year]]. '
            'E.g. "--date today-2weeks" downloads only videos uploaded on the same day two weeks ago'))
    selection.add_option(
        '--datebefore',
        metavar='DATE', dest='datebefore', default=None,
        help=(
            'Download only videos uploaded on or before this date. '
            'The date formats accepted is the same as --date'))
    selection.add_option(
        '--dateafter',
        metavar='DATE', dest='dateafter', default=None,
        help=(
            'Download only videos uploaded on or after this date. '
            'The date formats accepted is the same as --date'))
    selection.add_option(
        '--min-views',
        metavar='COUNT', dest='min_views', default=None, type=int,
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--max-views',
        metavar='COUNT', dest='max_views', default=None, type=int,
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--match-filters',
        metavar='FILTER', dest='match_filter', action='append',
        help=(
            'Generic video filter. Any "OUTPUT TEMPLATE" field can be compared with a '
            'number or a string using the operators defined in "Filtering Formats". '
            'You can also simply specify a field to match if the field is present, '
            'use "!field" to check if the field is not present, and "&" to check multiple conditions. '
            'Use a "\\" to escape "&" or quotes if needed. If used multiple times, '
            'the filter matches if atleast one of the conditions are met. E.g. --match-filter '
            '!is_live --match-filter "like_count>?100 & description~=\'(?i)\\bcats \\& dogs\\b\'" '
            'matches only videos that are not live OR those that have a like count more than 100 '
            '(or the like field is not available) and also has a description '
            'that contains the phrase "cats & dogs" (caseless). '
            'Use "--match-filter -" to interactively ask whether to download each video'))
    selection.add_option(
        '--no-match-filters',
        dest='match_filter', action='store_const', const=None,
        help='Do not use any --match-filter (default)')
    selection.add_option(
        '--break-match-filters',
        metavar='FILTER', dest='breaking_match_filter', action='append',
        help='Same as "--match-filters" but stops the download process when a video is rejected')
    selection.add_option(
        '--no-break-match-filters',
        dest='breaking_match_filter', action='store_const', const=None,
        help='Do not use any --break-match-filters (default)')
    selection.add_option(
        '--no-playlist',
        action='store_true', dest='noplaylist', default=False,
        help='Download only the video, if the URL refers to a video and a playlist')
    selection.add_option(
        '--yes-playlist',
        action='store_false', dest='noplaylist',
        help='Download the playlist, if the URL refers to a video and a playlist')
    selection.add_option(
        '--age-limit',
        metavar='YEARS', dest='age_limit', default=None, type=int,
        help='Download only videos suitable for the given age')
    selection.add_option(
        '--download-archive', metavar='FILE',
        dest='download_archive',
        help='Download only videos not listed in the archive file. Record the IDs of all downloaded videos in it')
    selection.add_option(
        '--no-download-archive',
        dest='download_archive', action="store_const", const=None,
        help='Do not use archive file (default)')
    selection.add_option(
        '--max-downloads',
        dest='max_downloads', metavar='NUMBER', type=int, default=None,
        help='Abort after downloading NUMBER files')
    selection.add_option(
        '--break-on-existing',
        action='store_true', dest='break_on_existing', default=False,
        help='Stop the download process when encountering a file that is in the archive')
    selection.add_option(
        '--break-on-reject',
        action='store_true', dest='break_on_reject', default=False,
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--break-per-input',
        action='store_true', dest='break_per_url', default=False,
        help='Alters --max-downloads, --break-on-existing, --break-match-filter, and autonumber to reset per input URL')
    selection.add_option(
        '--no-break-per-input',
        action='store_false', dest='break_per_url',
        help='--break-on-existing and similar options terminates the entire download queue')
    selection.add_option(
        '--skip-playlist-after-errors', metavar='N',
        dest='skip_playlist_after_errors', default=None, type=int,
        help='Number of allowed failures until the rest of the playlist is skipped')
    selection.add_option(
        '--include-ads',
        dest='include_ads', action='store_true',
        help=optparse.SUPPRESS_HELP)
    selection.add_option(
        '--no-include-ads',
        dest='include_ads', action='store_false',
        help=optparse.SUPPRESS_HELP)

    authentication = optparse.OptionGroup(parser, 'Authentication Options')
    authentication.add_option(
        '-u', '--username',
        dest='username', metavar='USERNAME',
        help='Login with this account ID')
    authentication.add_option(
        '-p', '--password',
        dest='password', metavar='PASSWORD',
        help='Account password. If this option is left out, yt-dlp will ask interactively')
    authentication.add_option(
        '-2', '--twofactor',
        dest='twofactor', metavar='TWOFACTOR',
        help='Two-factor authentication code')
    authentication.add_option(
        '-n', '--netrc',
        action='store_true', dest='usenetrc', default=False,
        help='Use .netrc authentication data')
    authentication.add_option(
        '--netrc-location',
        dest='netrc_location', metavar='PATH',
        help='Location of .netrc authentication data; either the path or its containing directory. Defaults to ~/.netrc')
    authentication.add_option(
        '--netrc-cmd',
        dest='netrc_cmd', metavar='NETRC_CMD',
        help='Command to execute to get the credentials for an extractor.')
    authentication.add_option(
        '--video-password',
        dest='videopassword', metavar='PASSWORD',
        help='Video-specific password')
    authentication.add_option(
        '--ap-mso',
        dest='ap_mso', metavar='MSO',
        help='Adobe Pass multiple-system operator (TV provider) identifier, use --ap-list-mso for a list of available MSOs')
    authentication.add_option(
        '--ap-username',
        dest='ap_username', metavar='USERNAME',
        help='Multiple-system operator account login')
    authentication.add_option(
        '--ap-password',
        dest='ap_password', metavar='PASSWORD',
        help='Multiple-system operator account password. If this option is left out, yt-dlp will ask interactively')
    authentication.add_option(
        '--ap-list-mso',
        action='store_true', dest='ap_list_mso', default=False,
        help='List all supported multiple-system operators')
    authentication.add_option(
        '--client-certificate',
        dest='client_certificate', metavar='CERTFILE',
        help='Path to client certificate file in PEM format. May include the private key')
    authentication.add_option(
        '--client-certificate-key',
        dest='client_certificate_key', metavar='KEYFILE',
        help='Path to private key file for client certificate')
    authentication.add_option(
        '--client-certificate-password',
        dest='client_certificate_password', metavar='PASSWORD',
        help='Password for client certificate private key, if encrypted. '
             'If not provided, and the key is encrypted, yt-dlp will ask interactively')

    video_format = optparse.OptionGroup(parser, 'Video Format Options')
    video_format.add_option(
        '-f', '--format',
        action='store', dest='format', metavar='FORMAT', default=None,
        help='Video format code, see "FORMAT SELECTION" for more details')
    video_format.add_option(
        '-S', '--format-sort', metavar='SORTORDER',
        dest='format_sort', default=[], type='str', action='callback',
        callback=_list_from_options_callback, callback_kwargs={'append': -1},
        help='Sort the formats by the fields given, see "Sorting Formats" for more details')
    video_format.add_option(
        '--format-sort-force', '--S-force',
        action='store_true', dest='format_sort_force', metavar='FORMAT', default=False,
        help=(
            'Force user specified sort order to have precedence over all fields, '
            'see "Sorting Formats" for more details (Alias: --S-force)'))
    video_format.add_option(
        '--no-format-sort-force',
        action='store_false', dest='format_sort_force', metavar='FORMAT', default=False,
        help='Some fields have precedence over the user specified sort order (default)')
    video_format.add_option(
        '--video-multistreams',
        action='store_true', dest='allow_multiple_video_streams', default=None,
        help='Allow multiple video streams to be merged into a single file')
    video_format.add_option(
        '--no-video-multistreams',
        action='store_false', dest='allow_multiple_video_streams',
        help='Only one video stream is downloaded for each output file (default)')
    video_format.add_option(
        '--audio-multistreams',
        action='store_true', dest='allow_multiple_audio_streams', default=None,
        help='Allow multiple audio streams to be merged into a single file')
    video_format.add_option(
        '--no-audio-multistreams',
        action='store_false', dest='allow_multiple_audio_streams',
        help='Only one audio stream is downloaded for each output file (default)')
    video_format.add_option(
        '--all-formats',
        action='store_const', dest='format', const='all',
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--prefer-free-formats',
        action='store_true', dest='prefer_free_formats', default=False,
        help=(
            'Prefer video formats with free containers over non-free ones of same quality. '
            'Use with "-S ext" to strictly prefer free containers irrespective of quality'))
    video_format.add_option(
        '--no-prefer-free-formats',
        action='store_false', dest='prefer_free_formats', default=False,
        help="Don't give any special preference to free containers (default)")
    video_format.add_option(
        '--check-formats',
        action='store_const', const='selected', dest='check_formats', default=None,
        help='Make sure formats are selected only from those that are actually downloadable')
    video_format.add_option(
        '--check-all-formats',
        action='store_true', dest='check_formats',
        help='Check all formats for whether they are actually downloadable')
    video_format.add_option(
        '--no-check-formats',
        action='store_false', dest='check_formats',
        help='Do not check that the formats are actually downloadable')
    video_format.add_option(
        '-F', '--list-formats',
        action='store_true', dest='listformats',
        help='List available formats of each video. Simulate unless --no-simulate is used')
    video_format.add_option(
        '--list-formats-as-table',
        action='store_true', dest='listformats_table', default=True,
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--list-formats-old', '--no-list-formats-as-table',
        action='store_false', dest='listformats_table',
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--merge-output-format',
        action='store', dest='merge_output_format', metavar='FORMAT', default=None,
        help=(
            'Containers that may be used when merging formats, separated by "/", e.g. "mp4/mkv". '
            'Ignored if no merge is required. '
            f'(currently supported: {", ".join(sorted(FFmpegMergerPP.SUPPORTED_EXTS))})'))
    video_format.add_option(
        '--allow-unplayable-formats',
        action='store_true', dest='allow_unplayable_formats', default=False,
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--no-allow-unplayable-formats',
        action='store_false', dest='allow_unplayable_formats',
        help=optparse.SUPPRESS_HELP)

    subtitles = optparse.OptionGroup(parser, 'Subtitle Options')
    subtitles.add_option(
        '--write-subs', '--write-srt',
        action='store_true', dest='writesubtitles', default=False,
        help='Write subtitle file')
    subtitles.add_option(
        '--no-write-subs', '--no-write-srt',
        action='store_false', dest='writesubtitles',
        help='Do not write subtitle file (default)')
    subtitles.add_option(
        '--write-auto-subs', '--write-automatic-subs',
        action='store_true', dest='writeautomaticsub', default=False,
        help='Write automatically generated subtitle file (Alias: --write-automatic-subs)')
    subtitles.add_option(
        '--no-write-auto-subs', '--no-write-automatic-subs',
        action='store_false', dest='writeautomaticsub', default=False,
        help='Do not write auto-generated subtitles (default) (Alias: --no-write-automatic-subs)')
    subtitles.add_option(
        '--all-subs',
        action='store_true', dest='allsubtitles', default=False,
        help=optparse.SUPPRESS_HELP)
    subtitles.add_option(
        '--list-subs',
        action='store_true', dest='listsubtitles', default=False,
        help='List available subtitles of each video. Simulate unless --no-simulate is used')
    subtitles.add_option(
        '--sub-format',
        action='store', dest='subtitlesformat', metavar='FORMAT', default='best',
        help='Subtitle format; accepts formats preference, e.g. "srt" or "ass/srt/best"')
    subtitles.add_option(
        '--sub-langs', '--srt-langs',
        action='callback', dest='subtitleslangs', metavar='LANGS', type='str',
        default=[], callback=_list_from_options_callback,
        help=(
            'Languages of the subtitles to download (can be regex) or "all" separated by commas, e.g. --sub-langs "en.*,ja". '
            'You can prefix the language code with a "-" to exclude it from the requested languages, e.g. --sub-langs all,-live_chat. '
            'Use --list-subs for a list of available language tags'))

    downloader = optparse.OptionGroup(parser, 'Download Options')
    downloader.add_option(
        '-N', '--concurrent-fragments',
        dest='concurrent_fragment_downloads', metavar='N', default=1, type=int,
        help='Number of fragments of a dash/hlsnative video that should be downloaded concurrently (default is %default)')
    downloader.add_option(
        '-r', '--limit-rate', '--rate-limit',
        dest='ratelimit', metavar='RATE',
        help='Maximum download rate in bytes per second, e.g. 50K or 4.2M')
    downloader.add_option(
        '--throttled-rate',
        dest='throttledratelimit', metavar='RATE',
        help='Minimum download rate in bytes per second below which throttling is assumed and the video data is re-extracted, e.g. 100K')
    downloader.add_option(
        '-R', '--retries',
        dest='retries', metavar='RETRIES', default=10,
        help='Number of retries (default is %default), or "infinite"')
    downloader.add_option(
        '--file-access-retries',
        dest='file_access_retries', metavar='RETRIES', default=3,
        help='Number of times to retry on file access error (default is %default), or "infinite"')
    downloader.add_option(
        '--fragment-retries',
        dest='fragment_retries', metavar='RETRIES', default=10,
        help='Number of retries for a fragment (default is %default), or "infinite" (DASH, hlsnative and ISM)')
    downloader.add_option(
        '--retry-sleep',
        dest='retry_sleep', metavar='[TYPE:]EXPR', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': 'http|fragment|file_access|extractor',
            'default_key': 'http',
        }, help=(
            'Time to sleep between retries in seconds (optionally) prefixed by the type of retry '
            '(http (default), fragment, file_access, extractor) to apply the sleep to. '
            'EXPR can be a number, linear=START[:END[:STEP=1]] or exp=START[:END[:BASE=2]]. '
            'This option can be used multiple times to set the sleep for the different retry types, '
            'e.g. --retry-sleep linear=1::2 --retry-sleep fragment:exp=1:20'))
    downloader.add_option(
        '--skip-unavailable-fragments', '--no-abort-on-unavailable-fragments',
        action='store_true', dest='skip_unavailable_fragments', default=True,
        help='Skip unavailable fragments for DASH, hlsnative and ISM downloads (default) (Alias: --no-abort-on-unavailable-fragments)')
    downloader.add_option(
        '--abort-on-unavailable-fragments', '--no-skip-unavailable-fragments',
        action='store_false', dest='skip_unavailable_fragments',
        help='Abort download if a fragment is unavailable (Alias: --no-skip-unavailable-fragments)')
    downloader.add_option(
        '--keep-fragments',
        action='store_true', dest='keep_fragments', default=False,
        help='Keep downloaded fragments on disk after downloading is finished')
    downloader.add_option(
        '--no-keep-fragments',
        action='store_false', dest='keep_fragments',
        help='Delete downloaded fragments after downloading is finished (default)')
    downloader.add_option(
        '--buffer-size',
        dest='buffersize', metavar='SIZE', default='1024',
        help='Size of download buffer, e.g. 1024 or 16K (default is %default)')
    downloader.add_option(
        '--resize-buffer',
        action='store_false', dest='noresizebuffer',
        help='The buffer size is automatically resized from an initial value of --buffer-size (default)')
    downloader.add_option(
        '--no-resize-buffer',
        action='store_true', dest='noresizebuffer', default=False,
        help='Do not automatically adjust the buffer size')
    downloader.add_option(
        '--http-chunk-size',
        dest='http_chunk_size', metavar='SIZE', default=None,
        help=(
            'Size of a chunk for chunk-based HTTP downloading, e.g. 10485760 or 10M (default is disabled). '
            'May be useful for bypassing bandwidth throttling imposed by a webserver (experimental)'))
    downloader.add_option(
        '--test',
        action='store_true', dest='test', default=False,
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--playlist-reverse',
        action='store_true', dest='playlist_reverse',
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--no-playlist-reverse',
        action='store_false', dest='playlist_reverse',
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--playlist-random',
        action='store_true', dest='playlist_random',
        help='Download playlist videos in random order')
    downloader.add_option(
        '--lazy-playlist',
        action='store_true', dest='lazy_playlist',
        help='Process entries in the playlist as they are received. This disables n_entries, --playlist-random and --playlist-reverse')
    downloader.add_option(
        '--no-lazy-playlist',
        action='store_false', dest='lazy_playlist',
        help='Process videos in the playlist only after the entire playlist is parsed (default)')
    downloader.add_option(
        '--xattr-set-filesize',
        dest='xattr_set_filesize', action='store_true',
        help='Set file xattribute ytdl.filesize with expected file size')
    downloader.add_option(
        '--hls-prefer-native',
        dest='hls_prefer_native', action='store_true', default=None,
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--hls-prefer-ffmpeg',
        dest='hls_prefer_native', action='store_false', default=None,
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--hls-use-mpegts',
        dest='hls_use_mpegts', action='store_true', default=None,
        help=(
            'Use the mpegts container for HLS videos; '
            'allowing some players to play the video while downloading, '
            'and reducing the chance of file corruption if download is interrupted. '
            'This is enabled by default for live streams'))
    downloader.add_option(
        '--no-hls-use-mpegts',
        dest='hls_use_mpegts', action='store_false',
        help=(
            'Do not use the mpegts container for HLS videos. '
            'This is default when not downloading live streams'))
    downloader.add_option(
        '--download-sections',
        metavar='REGEX', dest='download_ranges', action='append',
        help=(
            'Download only chapters that match the regular expression. '
            'A "*" prefix denotes time-range instead of chapter. Negative timestamps are calculated from the end. '
            '"*from-url" can be used to download between the "start_time" and "end_time" extracted from the URL. '
            'Needs ffmpeg. This option can be used multiple times to download multiple sections, '
            'e.g. --download-sections "*10:15-inf" --download-sections "intro"'))
    downloader.add_option(
        '--downloader', '--external-downloader',
        dest='external_downloader', metavar='[PROTO:]NAME', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': 'http|ftp|m3u8|dash|rtsp|rtmp|mms',
            'default_key': 'default',
            'process': str.strip
        }, help=(
            'Name or path of the external downloader to use (optionally) prefixed by '
            'the protocols (http, ftp, m3u8, dash, rstp, rtmp, mms) to use it for. '
            f'Currently supports native, {", ".join(sorted(list_external_downloaders()))}. '
            'You can use this option multiple times to set different downloaders for different protocols. '
            'E.g. --downloader aria2c --downloader "dash,m3u8:native" will use '
            'aria2c for http/ftp downloads, and the native downloader for dash/m3u8 downloads '
            '(Alias: --external-downloader)'))
    downloader.add_option(
        '--downloader-args', '--external-downloader-args',
        metavar='NAME:ARGS', dest='external_downloader_args', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': r'ffmpeg_[io]\d*|%s' % '|'.join(map(re.escape, list_external_downloaders())),
            'default_key': 'default',
            'process': shlex.split
        }, help=(
            'Give these arguments to the external downloader. '
            'Specify the downloader name and the arguments separated by a colon ":". '
            'For ffmpeg, arguments can be passed to different positions using the same syntax as --postprocessor-args. '
            'You can use this option multiple times to give different arguments to different downloaders '
            '(Alias: --external-downloader-args)'))

    workarounds = optparse.OptionGroup(parser, 'Workarounds')
    workarounds.add_option(
        '--encoding',
        dest='encoding', metavar='ENCODING',
        help='Force the specified encoding (experimental)')
    workarounds.add_option(
        '--legacy-server-connect',
        action='store_true', dest='legacy_server_connect', default=False,
        help='Explicitly allow HTTPS connection to servers that do not support RFC 5746 secure renegotiation')
    workarounds.add_option(
        '--no-check-certificates',
        action='store_true', dest='no_check_certificate', default=False,
        help='Suppress HTTPS certificate validation')
    workarounds.add_option(
        '--prefer-insecure', '--prefer-unsecure',
        action='store_true', dest='prefer_insecure',
        help='Use an unencrypted connection to retrieve information about the video (Currently supported only for YouTube)')
    workarounds.add_option(
        '--user-agent',
        metavar='UA', dest='user_agent',
        help=optparse.SUPPRESS_HELP)
    workarounds.add_option(
        '--referer',
        metavar='URL', dest='referer', default=None,
        help=optparse.SUPPRESS_HELP)
    workarounds.add_option(
        '--add-headers',
        metavar='FIELD:VALUE', dest='headers', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={'multiple_keys': False},
        help='Specify a custom HTTP header and its value, separated by a colon ":". You can use this option multiple times',
    )
    workarounds.add_option(
        '--bidi-workaround',
        dest='bidi_workaround', action='store_true',
        help='Work around terminals that lack bidirectional text support. Requires bidiv or fribidi executable in PATH')
    workarounds.add_option(
        '--sleep-requests', metavar='SECONDS',
        dest='sleep_interval_requests', type=float,
        help='Number of seconds to sleep between requests during data extraction')
    workarounds.add_option(
        '--sleep-interval', '--min-sleep-interval', metavar='SECONDS',
        dest='sleep_interval', type=float,
        help=(
            'Number of seconds to sleep before each download. '
            'This is the minimum time to sleep when used along with --max-sleep-interval '
            '(Alias: --min-sleep-interval)'))
    workarounds.add_option(
        '--max-sleep-interval', metavar='SECONDS',
        dest='max_sleep_interval', type=float,
        help='Maximum number of seconds to sleep. Can only be used along with --min-sleep-interval')
    workarounds.add_option(
        '--sleep-subtitles', metavar='SECONDS',
        dest='sleep_interval_subtitles', default=0, type=int,
        help='Number of seconds to sleep before each subtitle download')

    verbosity = optparse.OptionGroup(parser, 'Verbosity and Simulation Options')
    verbosity.add_option(
        '-q', '--quiet',
        action='store_true', dest='quiet', default=None,
        help='Activate quiet mode. If used with --verbose, print the log to stderr')
    verbosity.add_option(
        '--no-quiet',
        action='store_false', dest='quiet',
        help='Deactivate quiet mode. (Default)')
    verbosity.add_option(
        '--no-warnings',
        dest='no_warnings', action='store_true', default=False,
        help='Ignore warnings')
    verbosity.add_option(
        '-s', '--simulate',
        action='store_true', dest='simulate', default=None,
        help='Do not download the video and do not write anything to disk')
    verbosity.add_option(
        '--no-simulate',
        action='store_false', dest='simulate',
        help='Download the video even if printing/listing options are used')
    verbosity.add_option(
        '--ignore-no-formats-error',
        action='store_true', dest='ignore_no_formats_error', default=False,
        help=(
            'Ignore "No video formats" error. Useful for extracting metadata '
            'even if the videos are not actually available for download (experimental)'))
    verbosity.add_option(
        '--no-ignore-no-formats-error',
        action='store_false', dest='ignore_no_formats_error',
        help='Throw error when no downloadable video formats are found (default)')
    verbosity.add_option(
        '--skip-download', '--no-download',
        action='store_true', dest='skip_download', default=False,
        help='Do not download the video but write all related files (Alias: --no-download)')
    verbosity.add_option(
        '-O', '--print',
        metavar='[WHEN:]TEMPLATE', dest='forceprint', **when_prefix('video'),
        help=(
            'Field name or output template to print to screen, optionally prefixed with when to print it, separated by a ":". '
            'Supported values of "WHEN" are the same as that of --use-postprocessor (default: video). '
            'Implies --quiet. Implies --simulate unless --no-simulate or later stages of WHEN are used. '
            'This option can be used multiple times'))
    verbosity.add_option(
        '--print-to-file',
        metavar='[WHEN:]TEMPLATE FILE', dest='print_to_file', nargs=2, **when_prefix('video'),
        help=(
            'Append given template to the file. The values of WHEN and TEMPLATE are same as that of --print. '
            'FILE uses the same syntax as the output template. This option can be used multiple times'))
    verbosity.add_option(
        '-g', '--get-url',
        action='store_true', dest='geturl', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '-e', '--get-title',
        action='store_true', dest='gettitle', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--get-id',
        action='store_true', dest='getid', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--get-thumbnail',
        action='store_true', dest='getthumbnail', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--get-description',
        action='store_true', dest='getdescription', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--get-duration',
        action='store_true', dest='getduration', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--get-filename',
        action='store_true', dest='getfilename', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--get-format',
        action='store_true', dest='getformat', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '-j', '--dump-json',
        action='store_true', dest='dumpjson', default=False,
        help='Quiet, but print JSON information for each video. Simulate unless --no-simulate is used. See "OUTPUT TEMPLATE" for a description of available keys')
    verbosity.add_option(
        '-J', '--dump-single-json',
        action='store_true', dest='dump_single_json', default=False,
        help=(
            'Quiet, but print JSON information for each url or infojson passed. Simulate unless --no-simulate is used. '
            'If the URL refers to a playlist, the whole playlist information is dumped in a single line'))
    verbosity.add_option(
        '--print-json',
        action='store_true', dest='print_json', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--force-write-archive', '--force-write-download-archive', '--force-download-archive',
        action='store_true', dest='force_write_download_archive', default=False,
        help=(
            'Force download archive entries to be written as far as no errors occur, '
            'even if -s or another simulation option is used (Alias: --force-download-archive)'))
    verbosity.add_option(
        '--newline',
        action='store_true', dest='progress_with_newline', default=False,
        help='Output progress bar as new lines')
    verbosity.add_option(
        '--no-progress',
        action='store_true', dest='noprogress', default=None,
        help='Do not print progress bar')
    verbosity.add_option(
        '--progress',
        action='store_false', dest='noprogress',
        help='Show progress bar, even if in quiet mode')
    verbosity.add_option(
        '--console-title',
        action='store_true', dest='consoletitle', default=False,
        help='Display progress in console titlebar')
    verbosity.add_option(
        '--progress-template',
        metavar='[TYPES:]TEMPLATE', dest='progress_template', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': '(download|postprocess)(-title)?',
            'default_key': 'download'
        }, help=(
            'Template for progress outputs, optionally prefixed with one of "download:" (default), '
            '"download-title:" (the console title), "postprocess:",  or "postprocess-title:". '
            'The video\'s fields are accessible under the "info" key and '
            'the progress attributes are accessible under "progress" key. E.g. '
            # TODO: Document the fields inside "progress"
            '--console-title --progress-template "download-title:%(info.id)s-%(progress.eta)s"'))
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
        '--load-pages',
        action='store_true', dest='load_pages', default=False,
        help=optparse.SUPPRESS_HELP)
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
        # help='Contact the yt-dlp server for debugging')
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--no-call-home',
        dest='call_home', action='store_false',
        # help='Do not contact the yt-dlp server for debugging (default)')
        help=optparse.SUPPRESS_HELP)

    filesystem = optparse.OptionGroup(parser, 'Filesystem Options')
    filesystem.add_option(
        '-a', '--batch-file',
        dest='batchfile', metavar='FILE',
        help=(
            'File containing URLs to download ("-" for stdin), one URL per line. '
            'Lines starting with "#", ";" or "]" are considered as comments and ignored'))
    filesystem.add_option(
        '--no-batch-file',
        dest='batchfile', action='store_const', const=None,
        help='Do not read URLs from batch file (default)')
    filesystem.add_option(
        '--id', default=False,
        action='store_true', dest='useid', help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-P', '--paths',
        metavar='[TYPES:]PATH', dest='paths', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': 'home|temp|%s' % '|'.join(map(re.escape, OUTTMPL_TYPES.keys())),
            'default_key': 'home'
        }, help=(
            'The paths where the files should be downloaded. '
            'Specify the type of file and the path separated by a colon ":". '
            'All the same TYPES as --output are supported. '
            'Additionally, you can also provide "home" (default) and "temp" paths. '
            'All intermediary files are first downloaded to the temp path and '
            'then the final files are moved over to the home path after download is finished. '
            'This option is ignored if --output is an absolute path'))
    filesystem.add_option(
        '-o', '--output',
        metavar='[TYPES:]TEMPLATE', dest='outtmpl', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': '|'.join(map(re.escape, OUTTMPL_TYPES.keys())),
            'default_key': 'default'
        }, help='Output filename template; see "OUTPUT TEMPLATE" for details')
    filesystem.add_option(
        '--output-na-placeholder',
        dest='outtmpl_na_placeholder', metavar='TEXT', default='NA',
        help=('Placeholder for unavailable fields in "OUTPUT TEMPLATE" (default: "%default")'))
    filesystem.add_option(
        '--autonumber-size',
        dest='autonumber_size', metavar='NUMBER', type=int,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '--autonumber-start',
        dest='autonumber_start', metavar='NUMBER', default=1, type=int,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '--restrict-filenames',
        action='store_true', dest='restrictfilenames', default=False,
        help='Restrict filenames to only ASCII characters, and avoid "&" and spaces in filenames')
    filesystem.add_option(
        '--no-restrict-filenames',
        action='store_false', dest='restrictfilenames',
        help='Allow Unicode characters, "&" and spaces in filenames (default)')
    filesystem.add_option(
        '--windows-filenames',
        action='store_true', dest='windowsfilenames', default=False,
        help='Force filenames to be Windows-compatible')
    filesystem.add_option(
        '--no-windows-filenames',
        action='store_false', dest='windowsfilenames',
        help='Make filenames Windows-compatible only if using Windows (default)')
    filesystem.add_option(
        '--trim-filenames', '--trim-file-names', metavar='LENGTH',
        dest='trim_file_name', default=0, type=int,
        help='Limit the filename length (excluding extension) to the specified number of characters')
    filesystem.add_option(
        '-w', '--no-overwrites',
        action='store_false', dest='overwrites', default=None,
        help='Do not overwrite any files')
    filesystem.add_option(
        '--force-overwrites', '--yes-overwrites',
        action='store_true', dest='overwrites',
        help='Overwrite all video and metadata files. This option includes --no-continue')
    filesystem.add_option(
        '--no-force-overwrites',
        action='store_const', dest='overwrites', const=None,
        help='Do not overwrite the video, but overwrite related files (default)')
    filesystem.add_option(
        '-c', '--continue',
        action='store_true', dest='continue_dl', default=True,
        help='Resume partially downloaded files/fragments (default)')
    filesystem.add_option(
        '--no-continue',
        action='store_false', dest='continue_dl',
        help=(
            'Do not resume partially downloaded fragments. '
            'If the file is not fragmented, restart download of the entire file'))
    filesystem.add_option(
        '--part',
        action='store_false', dest='nopart', default=False,
        help='Use .part files instead of writing directly into output file (default)')
    filesystem.add_option(
        '--no-part',
        action='store_true', dest='nopart',
        help='Do not use .part files - write directly into output file')
    filesystem.add_option(
        '--mtime',
        action='store_true', dest='updatetime', default=True,
        help='Use the Last-modified header to set the file modification time (default)')
    filesystem.add_option(
        '--no-mtime',
        action='store_false', dest='updatetime',
        help='Do not use the Last-modified header to set the file modification time')
    filesystem.add_option(
        '--write-description',
        action='store_true', dest='writedescription', default=False,
        help='Write video description to a .description file')
    filesystem.add_option(
        '--no-write-description',
        action='store_false', dest='writedescription',
        help='Do not write video description (default)')
    filesystem.add_option(
        '--write-info-json',
        action='store_true', dest='writeinfojson', default=None,
        help='Write video metadata to a .info.json file (this may contain personal information)')
    filesystem.add_option(
        '--no-write-info-json',
        action='store_false', dest='writeinfojson',
        help='Do not write video metadata (default)')
    filesystem.add_option(
        '--write-annotations',
        action='store_true', dest='writeannotations', default=False,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '--no-write-annotations',
        action='store_false', dest='writeannotations',
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '--write-playlist-metafiles',
        action='store_true', dest='allow_playlist_files', default=None,
        help=(
            'Write playlist metadata in addition to the video metadata '
            'when using --write-info-json, --write-description etc. (default)'))
    filesystem.add_option(
        '--no-write-playlist-metafiles',
        action='store_false', dest='allow_playlist_files',
        help='Do not write playlist metadata when using --write-info-json, --write-description etc.')
    filesystem.add_option(
        '--clean-info-json', '--clean-infojson',
        action='store_true', dest='clean_infojson', default=None,
        help=(
            'Remove some internal metadata such as filenames from the infojson (default)'))
    filesystem.add_option(
        '--no-clean-info-json', '--no-clean-infojson',
        action='store_false', dest='clean_infojson',
        help='Write all fields to the infojson')
    filesystem.add_option(
        '--write-comments', '--get-comments',
        action='store_true', dest='getcomments', default=False,
        help=(
            'Retrieve video comments to be placed in the infojson. '
            'The comments are fetched even without this option if the extraction is known to be quick (Alias: --get-comments)'))
    filesystem.add_option(
        '--no-write-comments', '--no-get-comments',
        action='store_false', dest='getcomments',
        help='Do not retrieve video comments unless the extraction is known to be quick (Alias: --no-get-comments)')
    filesystem.add_option(
        '--load-info-json', '--load-info',
        dest='load_info_filename', metavar='FILE',
        help='JSON file containing the video information (created with the "--write-info-json" option)')
    filesystem.add_option(
        '--cookies',
        dest='cookiefile', metavar='FILE',
        help='Netscape formatted file to read cookies from and dump cookie jar in')
    filesystem.add_option(
        '--no-cookies',
        action='store_const', const=None, dest='cookiefile', metavar='FILE',
        help='Do not read/dump cookies from/to file (default)')
    filesystem.add_option(
        '--cookies-from-browser',
        dest='cookiesfrombrowser', metavar='BROWSER[+KEYRING][:PROFILE][::CONTAINER]',
        help=(
            'The name of the browser to load cookies from. '
            f'Currently supported browsers are: {", ".join(sorted(SUPPORTED_BROWSERS))}. '
            'Optionally, the KEYRING used for decrypting Chromium cookies on Linux, '
            'the name/path of the PROFILE to load cookies from, '
            'and the CONTAINER name (if Firefox) ("none" for no container) '
            'can be given with their respective seperators. '
            'By default, all containers of the most recently accessed profile are used. '
            f'Currently supported keyrings are: {", ".join(map(str.lower, sorted(SUPPORTED_KEYRINGS)))}'))
    filesystem.add_option(
        '--no-cookies-from-browser',
        action='store_const', const=None, dest='cookiesfrombrowser',
        help='Do not load cookies from browser (default)')
    filesystem.add_option(
        '--cache-dir', dest='cachedir', default=None, metavar='DIR',
        help=(
            'Location in the filesystem where yt-dlp can store some downloaded information '
            '(such as client ids and signatures) permanently. By default ${XDG_CACHE_HOME}/yt-dlp'))
    filesystem.add_option(
        '--no-cache-dir', action='store_false', dest='cachedir',
        help='Disable filesystem caching')
    filesystem.add_option(
        '--rm-cache-dir',
        action='store_true', dest='rm_cachedir',
        help='Delete all filesystem cache files')

    thumbnail = optparse.OptionGroup(parser, 'Thumbnail Options')
    thumbnail.add_option(
        '--write-thumbnail',
        action='callback', dest='writethumbnail', default=False,
        # Should override --no-write-thumbnail, but not --write-all-thumbnail
        callback=lambda option, _, __, parser: setattr(
            parser.values, option.dest, getattr(parser.values, option.dest) or True),
        help='Write thumbnail image to disk')
    thumbnail.add_option(
        '--no-write-thumbnail',
        action='store_false', dest='writethumbnail',
        help='Do not write thumbnail image to disk (default)')
    thumbnail.add_option(
        '--write-all-thumbnails',
        action='store_const', dest='writethumbnail', const='all',
        help='Write all thumbnail image formats to disk')
    thumbnail.add_option(
        '--list-thumbnails',
        action='store_true', dest='list_thumbnails', default=False,
        help='List available thumbnails of each video. Simulate unless --no-simulate is used')

    link = optparse.OptionGroup(parser, 'Internet Shortcut Options')
    link.add_option(
        '--write-link',
        action='store_true', dest='writelink', default=False,
        help='Write an internet shortcut file, depending on the current platform (.url, .webloc or .desktop). The URL may be cached by the OS')
    link.add_option(
        '--write-url-link',
        action='store_true', dest='writeurllink', default=False,
        help='Write a .url Windows internet shortcut. The OS caches the URL based on the file path')
    link.add_option(
        '--write-webloc-link',
        action='store_true', dest='writewebloclink', default=False,
        help='Write a .webloc macOS internet shortcut')
    link.add_option(
        '--write-desktop-link',
        action='store_true', dest='writedesktoplink', default=False,
        help='Write a .desktop Linux internet shortcut')

    postproc = optparse.OptionGroup(parser, 'Post-Processing Options')
    postproc.add_option(
        '-x', '--extract-audio',
        action='store_true', dest='extractaudio', default=False,
        help='Convert video files to audio-only files (requires ffmpeg and ffprobe)')
    postproc.add_option(
        '--audio-format', metavar='FORMAT', dest='audioformat', default='best',
        help=(
            'Format to convert the audio to when -x is used. '
            f'(currently supported: best (default), {", ".join(sorted(FFmpegExtractAudioPP.SUPPORTED_EXTS))}). '
            'You can specify multiple rules using similar syntax as --remux-video'))
    postproc.add_option(
        '--audio-quality', metavar='QUALITY',
        dest='audioquality', default='5',
        help=(
            'Specify ffmpeg audio quality to use when converting the audio with -x. '
            'Insert a value between 0 (best) and 10 (worst) for VBR or a specific bitrate like 128K (default %default)'))
    postproc.add_option(
        '--remux-video',
        metavar='FORMAT', dest='remuxvideo', default=None,
        help=(
            'Remux the video into another container if necessary '
            f'(currently supported: {", ".join(FFmpegVideoRemuxerPP.SUPPORTED_EXTS)}). '
            'If target container does not support the video/audio codec, remuxing will fail. You can specify multiple rules; '
            'e.g. "aac>m4a/mov>mp4/mkv" will remux aac to m4a, mov to mp4 and anything else to mkv'))
    postproc.add_option(
        '--recode-video',
        metavar='FORMAT', dest='recodevideo', default=None,
        help='Re-encode the video into another format if necessary. The syntax and supported formats are the same as --remux-video')
    postproc.add_option(
        '--postprocessor-args', '--ppa',
        metavar='NAME:ARGS', dest='postprocessor_args', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'allowed_keys': r'\w+(?:\+\w+)?',
            'default_key': 'default-compat',
            'process': shlex.split,
            'multiple_keys': False
        }, help=(
            'Give these arguments to the postprocessors. '
            'Specify the postprocessor/executable name and the arguments separated by a colon ":" '
            'to give the argument to the specified postprocessor/executable. Supported PP are: '
            'Merger, ModifyChapters, SplitChapters, ExtractAudio, VideoRemuxer, VideoConvertor, '
            'Metadata, EmbedSubtitle, EmbedThumbnail, SubtitlesConvertor, ThumbnailsConvertor, '
            'FixupStretched, FixupM4a, FixupM3u8, FixupTimestamp and FixupDuration. '
            'The supported executables are: AtomicParsley, FFmpeg and FFprobe. '
            'You can also specify "PP+EXE:ARGS" to give the arguments to the specified executable '
            'only when being used by the specified postprocessor. Additionally, for ffmpeg/ffprobe, '
            '"_i"/"_o" can be appended to the prefix optionally followed by a number to pass the argument '
            'before the specified input/output file, e.g. --ppa "Merger+ffmpeg_i1:-v quiet". '
            'You can use this option multiple times to give different arguments to different '
            'postprocessors. (Alias: --ppa)'))
    postproc.add_option(
        '-k', '--keep-video',
        action='store_true', dest='keepvideo', default=False,
        help='Keep the intermediate video file on disk after post-processing')
    postproc.add_option(
        '--no-keep-video',
        action='store_false', dest='keepvideo',
        help='Delete the intermediate video file after post-processing (default)')
    postproc.add_option(
        '--post-overwrites',
        action='store_false', dest='nopostoverwrites',
        help='Overwrite post-processed files (default)')
    postproc.add_option(
        '--no-post-overwrites',
        action='store_true', dest='nopostoverwrites', default=False,
        help='Do not overwrite post-processed files')
    postproc.add_option(
        '--embed-subs',
        action='store_true', dest='embedsubtitles', default=False,
        help='Embed subtitles in the video (only for mp4, webm and mkv videos)')
    postproc.add_option(
        '--no-embed-subs',
        action='store_false', dest='embedsubtitles',
        help='Do not embed subtitles (default)')
    postproc.add_option(
        '--embed-thumbnail',
        action='store_true', dest='embedthumbnail', default=False,
        help='Embed thumbnail in the video as cover art')
    postproc.add_option(
        '--no-embed-thumbnail',
        action='store_false', dest='embedthumbnail',
        help='Do not embed thumbnail (default)')
    postproc.add_option(
        '--embed-metadata', '--add-metadata',
        action='store_true', dest='addmetadata', default=False,
        help=(
            'Embed metadata to the video file. Also embeds chapters/infojson if present '
            'unless --no-embed-chapters/--no-embed-info-json are used (Alias: --add-metadata)'))
    postproc.add_option(
        '--no-embed-metadata', '--no-add-metadata',
        action='store_false', dest='addmetadata',
        help='Do not add metadata to file (default) (Alias: --no-add-metadata)')
    postproc.add_option(
        '--embed-chapters', '--add-chapters',
        action='store_true', dest='addchapters', default=None,
        help='Add chapter markers to the video file (Alias: --add-chapters)')
    postproc.add_option(
        '--no-embed-chapters', '--no-add-chapters',
        action='store_false', dest='addchapters',
        help='Do not add chapter markers (default) (Alias: --no-add-chapters)')
    postproc.add_option(
        '--embed-info-json',
        action='store_true', dest='embed_infojson', default=None,
        help='Embed the infojson as an attachment to mkv/mka video files')
    postproc.add_option(
        '--no-embed-info-json',
        action='store_false', dest='embed_infojson',
        help='Do not embed the infojson as an attachment to the video file')
    postproc.add_option(
        '--metadata-from-title',
        metavar='FORMAT', dest='metafromtitle',
        help=optparse.SUPPRESS_HELP)
    postproc.add_option(
        '--parse-metadata',
        metavar='[WHEN:]FROM:TO', dest='parse_metadata', **when_prefix('pre_process'),
        help=(
            'Parse additional metadata like title/artist from other fields; see "MODIFYING METADATA" for details. '
            'Supported values of "WHEN" are the same as that of --use-postprocessor (default: pre_process)'))
    postproc.add_option(
        '--replace-in-metadata',
        dest='parse_metadata', metavar='[WHEN:]FIELDS REGEX REPLACE', nargs=3, **when_prefix('pre_process'),
        help=(
            'Replace text in a metadata field using the given regex. This option can be used multiple times. '
            'Supported values of "WHEN" are the same as that of --use-postprocessor (default: pre_process)'))
    postproc.add_option(
        '--xattrs', '--xattr',
        action='store_true', dest='xattrs', default=False,
        help='Write metadata to the video file\'s xattrs (using dublin core and xdg standards)')
    postproc.add_option(
        '--concat-playlist',
        metavar='POLICY', dest='concat_playlist', default='multi_video',
        choices=('never', 'always', 'multi_video'),
        help=(
            'Concatenate videos in a playlist. One of "never", "always", or '
            '"multi_video" (default; only when the videos form a single show). '
            'All the video files must have same codecs and number of streams to be concatable. '
            'The "pl_video:" prefix can be used with "--paths" and "--output" to '
            'set the output filename for the concatenated files. See "OUTPUT TEMPLATE" for details'))
    postproc.add_option(
        '--fixup',
        metavar='POLICY', dest='fixup', default=None,
        choices=('never', 'ignore', 'warn', 'detect_or_warn', 'force'),
        help=(
            'Automatically correct known faults of the file. '
            'One of never (do nothing), warn (only emit a warning), '
            'detect_or_warn (the default; fix file if we can, warn otherwise), '
            'force (try fixing even if file already exists)'))
    postproc.add_option(
        '--prefer-avconv', '--no-prefer-ffmpeg',
        action='store_false', dest='prefer_ffmpeg',
        help=optparse.SUPPRESS_HELP)
    postproc.add_option(
        '--prefer-ffmpeg', '--no-prefer-avconv',
        action='store_true', dest='prefer_ffmpeg', default=True,
        help=optparse.SUPPRESS_HELP)
    postproc.add_option(
        '--ffmpeg-location', '--avconv-location', metavar='PATH',
        dest='ffmpeg_location',
        help='Location of the ffmpeg binary; either the path to the binary or its containing directory')
    postproc.add_option(
        '--exec',
        metavar='[WHEN:]CMD', dest='exec_cmd', **when_prefix('after_move'),
        help=(
            'Execute a command, optionally prefixed with when to execute it, separated by a ":". '
            'Supported values of "WHEN" are the same as that of --use-postprocessor (default: after_move). '
            'Same syntax as the output template can be used to pass any field as arguments to the command. '
            'If no fields are passed, %(filepath,_filename|)q is appended to the end of the command. '
            'This option can be used multiple times'))
    postproc.add_option(
        '--no-exec',
        action='store_const', dest='exec_cmd', const={},
        help='Remove any previously defined --exec')
    postproc.add_option(
        '--exec-before-download', metavar='CMD',
        action='append', dest='exec_before_dl_cmd',
        help=optparse.SUPPRESS_HELP)
    postproc.add_option(
        '--no-exec-before-download',
        action='store_const', dest='exec_before_dl_cmd', const=None,
        help=optparse.SUPPRESS_HELP)
    postproc.add_option(
        '--convert-subs', '--convert-sub', '--convert-subtitles',
        metavar='FORMAT', dest='convertsubtitles', default=None,
        help=(
            'Convert the subtitles to another format (currently supported: %s) '
            '(Alias: --convert-subtitles)' % ', '.join(sorted(FFmpegSubtitlesConvertorPP.SUPPORTED_EXTS))))
    postproc.add_option(
        '--convert-thumbnails',
        metavar='FORMAT', dest='convertthumbnails', default=None,
        help=(
            'Convert the thumbnails to another format '
            f'(currently supported: {", ".join(sorted(FFmpegThumbnailsConvertorPP.SUPPORTED_EXTS))}). '
            'You can specify multiple rules using similar syntax as --remux-video'))
    postproc.add_option(
        '--split-chapters', '--split-tracks',
        dest='split_chapters', action='store_true', default=False,
        help=(
            'Split video into multiple files based on internal chapters. '
            'The "chapter:" prefix can be used with "--paths" and "--output" to '
            'set the output filename for the split files. See "OUTPUT TEMPLATE" for details'))
    postproc.add_option(
        '--no-split-chapters', '--no-split-tracks',
        dest='split_chapters', action='store_false',
        help='Do not split video based on chapters (default)')
    postproc.add_option(
        '--remove-chapters',
        metavar='REGEX', dest='remove_chapters', action='append',
        help=(
            'Remove chapters whose title matches the given regular expression. '
            'The syntax is the same as --download-sections. This option can be used multiple times'))
    postproc.add_option(
        '--no-remove-chapters', dest='remove_chapters', action='store_const', const=None,
        help='Do not remove any chapters from the file (default)')
    postproc.add_option(
        '--force-keyframes-at-cuts',
        action='store_true', dest='force_keyframes_at_cuts', default=False,
        help=(
            'Force keyframes at cuts when downloading/splitting/removing sections. '
            'This is slow due to needing a re-encode, but the resulting video may have fewer artifacts around the cuts'))
    postproc.add_option(
        '--no-force-keyframes-at-cuts',
        action='store_false', dest='force_keyframes_at_cuts',
        help='Do not force keyframes around the chapters when cutting/splitting (default)')
    _postprocessor_opts_parser = lambda key, val='': (
        *(item.split('=', 1) for item in (val.split(';') if val else [])),
        ('key', remove_end(key, 'PP')))
    postproc.add_option(
        '--use-postprocessor',
        metavar='NAME[:ARGS]', dest='add_postprocessors', default=[], type='str',
        action='callback', callback=_list_from_options_callback,
        callback_kwargs={
            'delim': None,
            'process': lambda val: dict(_postprocessor_opts_parser(*val.split(':', 1)))
        }, help=(
            'The (case sensitive) name of plugin postprocessors to be enabled, '
            'and (optionally) arguments to be passed to it, separated by a colon ":". '
            'ARGS are a semicolon ";" delimited list of NAME=VALUE. '
            'The "when" argument determines when the postprocessor is invoked. '
            'It can be one of "pre_process" (after video extraction), "after_filter" (after video passes filter), '
            '"video" (after --format; before --print/--output), "before_dl" (before each video download), '
            '"post_process" (after each video download; default), '
            '"after_move" (after moving video file to it\'s final locations), '
            '"after_video" (after downloading and processing all formats of a video), '
            'or "playlist" (at end of playlist). '
            'This option can be used multiple times to add different postprocessors'))

    sponsorblock = optparse.OptionGroup(parser, 'SponsorBlock Options', description=(
        'Make chapter entries for, or remove various segments (sponsor, introductions, etc.) '
        'from downloaded YouTube videos using the SponsorBlock API (https://sponsor.ajay.app)'))
    sponsorblock.add_option(
        '--sponsorblock-mark', metavar='CATS',
        dest='sponsorblock_mark', default=set(), action='callback', type='str',
        callback=_set_from_options_callback, callback_kwargs={
            'allowed_values': SponsorBlockPP.CATEGORIES.keys(),
            'aliases': {'default': ['all']}
        }, help=(
            'SponsorBlock categories to create chapters for, separated by commas. '
            f'Available categories are {", ".join(SponsorBlockPP.CATEGORIES.keys())}, all and default (=all). '
            'You can prefix the category with a "-" to exclude it. See [1] for description of the categories. '
            'E.g. --sponsorblock-mark all,-preview [1] https://wiki.sponsor.ajay.app/w/Segment_Categories'))
    sponsorblock.add_option(
        '--sponsorblock-remove', metavar='CATS',
        dest='sponsorblock_remove', default=set(), action='callback', type='str',
        callback=_set_from_options_callback, callback_kwargs={
            'allowed_values': set(SponsorBlockPP.CATEGORIES.keys()) - set(SponsorBlockPP.NON_SKIPPABLE_CATEGORIES.keys()),
            # Note: From https://wiki.sponsor.ajay.app/w/Types:
            # The filler category is very aggressive.
            # It is strongly recommended to not use this in a client by default.
            'aliases': {'default': ['all', '-filler']}
        }, help=(
            'SponsorBlock categories to be removed from the video file, separated by commas. '
            'If a category is present in both mark and remove, remove takes precedence. '
            'The syntax and available categories are the same as for --sponsorblock-mark '
            'except that "default" refers to "all,-filler" '
            f'and {", ".join(SponsorBlockPP.NON_SKIPPABLE_CATEGORIES.keys())} are not available'))
    sponsorblock.add_option(
        '--sponsorblock-chapter-title', metavar='TEMPLATE',
        default=DEFAULT_SPONSORBLOCK_CHAPTER_TITLE, dest='sponsorblock_chapter_title',
        help=(
            'An output template for the title of the SponsorBlock chapters created by --sponsorblock-mark. '
            'The only available fields are start_time, end_time, category, categories, name, category_names. '
            'Defaults to "%default"'))
    sponsorblock.add_option(
        '--no-sponsorblock', default=False,
        action='store_true', dest='no_sponsorblock',
        help='Disable both --sponsorblock-mark and --sponsorblock-remove')
    sponsorblock.add_option(
        '--sponsorblock-api', metavar='URL',
        default='https://sponsor.ajay.app', dest='sponsorblock_api',
        help='SponsorBlock API location, defaults to %default')

    sponsorblock.add_option(
        '--sponskrub',
        action='store_true', dest='sponskrub', default=False,
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--no-sponskrub',
        action='store_false', dest='sponskrub',
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--sponskrub-cut', default=False,
        action='store_true', dest='sponskrub_cut',
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--no-sponskrub-cut',
        action='store_false', dest='sponskrub_cut',
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--sponskrub-force', default=False,
        action='store_true', dest='sponskrub_force',
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--no-sponskrub-force',
        action='store_true', dest='sponskrub_force',
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--sponskrub-location', metavar='PATH',
        dest='sponskrub_path', default='',
        help=optparse.SUPPRESS_HELP)
    sponsorblock.add_option(
        '--sponskrub-args', dest='sponskrub_args', metavar='ARGS',
        help=optparse.SUPPRESS_HELP)

    extractor = optparse.OptionGroup(parser, 'Extractor Options')
    extractor.add_option(
        '--extractor-retries',
        dest='extractor_retries', metavar='RETRIES', default=3,
        help='Number of retries for known extractor errors (default is %default), or "infinite"')
    extractor.add_option(
        '--allow-dynamic-mpd', '--no-ignore-dynamic-mpd',
        action='store_true', dest='dynamic_mpd', default=True,
        help='Process dynamic DASH manifests (default) (Alias: --no-ignore-dynamic-mpd)')
    extractor.add_option(
        '--ignore-dynamic-mpd', '--no-allow-dynamic-mpd',
        action='store_false', dest='dynamic_mpd',
        help='Do not process dynamic DASH manifests (Alias: --no-allow-dynamic-mpd)')
    extractor.add_option(
        '--hls-split-discontinuity',
        dest='hls_split_discontinuity', action='store_true', default=False,
        help='Split HLS playlists to different formats at discontinuities such as ad breaks'
    )
    extractor.add_option(
        '--no-hls-split-discontinuity',
        dest='hls_split_discontinuity', action='store_false',
        help='Do not split HLS playlists to different formats at discontinuities such as ad breaks (default)')
    _extractor_arg_parser = lambda key, vals='': (key.strip().lower().replace('-', '_'), [
        val.replace(r'\,', ',').strip() for val in re.split(r'(?<!\\),', vals)])
    extractor.add_option(
        '--extractor-args',
        metavar='IE_KEY:ARGS', dest='extractor_args', default={}, type='str',
        action='callback', callback=_dict_from_options_callback,
        callback_kwargs={
            'multiple_keys': False,
            'process': lambda val: dict(
                _extractor_arg_parser(*arg.split('=', 1)) for arg in val.split(';'))
        }, help=(
            'Pass ARGS arguments to the IE_KEY extractor. See "EXTRACTOR ARGUMENTS" for details. '
            'You can use this option multiple times to give arguments for different extractors'))
    extractor.add_option(
        '--youtube-include-dash-manifest', '--no-youtube-skip-dash-manifest',
        action='store_true', dest='youtube_include_dash_manifest', default=True,
        help=optparse.SUPPRESS_HELP)
    extractor.add_option(
        '--youtube-skip-dash-manifest', '--no-youtube-include-dash-manifest',
        action='store_false', dest='youtube_include_dash_manifest',
        help=optparse.SUPPRESS_HELP)
    extractor.add_option(
        '--youtube-include-hls-manifest', '--no-youtube-skip-hls-manifest',
        action='store_true', dest='youtube_include_hls_manifest', default=True,
        help=optparse.SUPPRESS_HELP)
    extractor.add_option(
        '--youtube-skip-hls-manifest', '--no-youtube-include-hls-manifest',
        action='store_false', dest='youtube_include_hls_manifest',
        help=optparse.SUPPRESS_HELP)

    parser.add_option_group(general)
    parser.add_option_group(network)
    parser.add_option_group(geo)
    parser.add_option_group(selection)
    parser.add_option_group(downloader)
    parser.add_option_group(filesystem)
    parser.add_option_group(thumbnail)
    parser.add_option_group(link)
    parser.add_option_group(verbosity)
    parser.add_option_group(workarounds)
    parser.add_option_group(video_format)
    parser.add_option_group(subtitles)
    parser.add_option_group(authentication)
    parser.add_option_group(postproc)
    parser.add_option_group(sponsorblock)
    parser.add_option_group(extractor)

    return parser


def _hide_login_info(opts):
    deprecation_warning(f'"{__name__}._hide_login_info" is deprecated and may be removed '
                        'in a future version. Use "yt_dlp.utils.Config.hide_login_info" instead')
    return Config.hide_login_info(opts)

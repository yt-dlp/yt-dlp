#!/usr/bin/env python3
# coding: utf-8

from __future__ import unicode_literals

__license__ = 'Public Domain'

import codecs
import io
import itertools
import os
import random
import re
import sys


from .options import (
    parseOpts,
)
from .compat import (
    compat_getpass,
    compat_shlex_quote,
    workaround_optparse_bug9161,
)
from .cookies import SUPPORTED_BROWSERS
from .utils import (
    DateRange,
    decodeOption,
    DownloadError,
    error_to_compat_str,
    ExistingVideoReached,
    expand_path,
    match_filter_func,
    MaxDownloadsReached,
    preferredencoding,
    read_batch_urls,
    RejectedVideoReached,
    render_table,
    SameFileError,
    setproctitle,
    std_headers,
    write_string,
)
from .update import run_update
from .downloader import (
    FileDownloader,
)
from .extractor import gen_extractors, list_extractors
from .extractor.common import InfoExtractor
from .extractor.adobepass import MSO_INFO
from .postprocessor import (
    FFmpegExtractAudioPP,
    FFmpegSubtitlesConvertorPP,
    FFmpegThumbnailsConvertorPP,
    FFmpegVideoConvertorPP,
    FFmpegVideoRemuxerPP,
    MetadataFromFieldPP,
    MetadataParserPP,
)
from .YoutubeDL import YoutubeDL


def _real_main(argv=None):
    # Compatibility fixes for Windows
    if sys.platform == 'win32':
        # https://github.com/ytdl-org/youtube-dl/issues/820
        codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)

    workaround_optparse_bug9161()

    setproctitle('yt-dlp')

    parser, opts, args = parseOpts(argv)
    warnings = []

    # Set user agent
    if opts.user_agent is not None:
        std_headers['User-Agent'] = opts.user_agent

    # Set referer
    if opts.referer is not None:
        std_headers['Referer'] = opts.referer

    # Custom HTTP headers
    std_headers.update(opts.headers)

    # Dump user agent
    if opts.dump_user_agent:
        write_string(std_headers['User-Agent'] + '\n', out=sys.stdout)
        sys.exit(0)

    # Batch file verification
    batch_urls = []
    if opts.batchfile is not None:
        try:
            if opts.batchfile == '-':
                batchfd = sys.stdin
            else:
                batchfd = io.open(
                    expand_path(opts.batchfile),
                    'r', encoding='utf-8', errors='ignore')
            batch_urls = read_batch_urls(batchfd)
            if opts.verbose:
                write_string('[debug] Batch file urls: ' + repr(batch_urls) + '\n')
        except IOError:
            sys.exit('ERROR: batch file %s could not be read' % opts.batchfile)
    all_urls = batch_urls + [url.strip() for url in args]  # batch_urls are already striped in read_batch_urls
    _enc = preferredencoding()
    all_urls = [url.decode(_enc, 'ignore') if isinstance(url, bytes) else url for url in all_urls]

    if opts.list_extractors:
        for ie in list_extractors(opts.age_limit):
            write_string(ie.IE_NAME + (' (CURRENTLY BROKEN)' if not ie._WORKING else '') + '\n', out=sys.stdout)
            matchedUrls = [url for url in all_urls if ie.suitable(url)]
            for mu in matchedUrls:
                write_string('  ' + mu + '\n', out=sys.stdout)
        sys.exit(0)
    if opts.list_extractor_descriptions:
        for ie in list_extractors(opts.age_limit):
            if not ie._WORKING:
                continue
            desc = getattr(ie, 'IE_DESC', ie.IE_NAME)
            if desc is False:
                continue
            if hasattr(ie, 'SEARCH_KEY'):
                _SEARCHES = ('cute kittens', 'slithering pythons', 'falling cat', 'angry poodle', 'purple fish', 'running tortoise', 'sleeping bunny', 'burping cow')
                _COUNTS = ('', '5', '10', 'all')
                desc += ' (Example: "%s%s:%s" )' % (ie.SEARCH_KEY, random.choice(_COUNTS), random.choice(_SEARCHES))
            write_string(desc + '\n', out=sys.stdout)
        sys.exit(0)
    if opts.ap_list_mso:
        table = [[mso_id, mso_info['name']] for mso_id, mso_info in MSO_INFO.items()]
        write_string('Supported TV Providers:\n' + render_table(['mso', 'mso name'], table) + '\n', out=sys.stdout)
        sys.exit(0)

    # Conflicting, missing and erroneous options
    if opts.usenetrc and (opts.username is not None or opts.password is not None):
        parser.error('using .netrc conflicts with giving username/password')
    if opts.password is not None and opts.username is None:
        parser.error('account username missing\n')
    if opts.ap_password is not None and opts.ap_username is None:
        parser.error('TV Provider account username missing\n')
    if opts.autonumber_size is not None:
        if opts.autonumber_size <= 0:
            parser.error('auto number size must be positive')
    if opts.autonumber_start is not None:
        if opts.autonumber_start < 0:
            parser.error('auto number start must be positive or 0')
    if opts.username is not None and opts.password is None:
        opts.password = compat_getpass('Type account password and press [Return]: ')
    if opts.ap_username is not None and opts.ap_password is None:
        opts.ap_password = compat_getpass('Type TV provider account password and press [Return]: ')
    if opts.ratelimit is not None:
        numeric_limit = FileDownloader.parse_bytes(opts.ratelimit)
        if numeric_limit is None:
            parser.error('invalid rate limit specified')
        opts.ratelimit = numeric_limit
    if opts.throttledratelimit is not None:
        numeric_limit = FileDownloader.parse_bytes(opts.throttledratelimit)
        if numeric_limit is None:
            parser.error('invalid rate limit specified')
        opts.throttledratelimit = numeric_limit
    if opts.min_filesize is not None:
        numeric_limit = FileDownloader.parse_bytes(opts.min_filesize)
        if numeric_limit is None:
            parser.error('invalid min_filesize specified')
        opts.min_filesize = numeric_limit
    if opts.max_filesize is not None:
        numeric_limit = FileDownloader.parse_bytes(opts.max_filesize)
        if numeric_limit is None:
            parser.error('invalid max_filesize specified')
        opts.max_filesize = numeric_limit
    if opts.sleep_interval is not None:
        if opts.sleep_interval < 0:
            parser.error('sleep interval must be positive or 0')
    if opts.max_sleep_interval is not None:
        if opts.max_sleep_interval < 0:
            parser.error('max sleep interval must be positive or 0')
        if opts.sleep_interval is None:
            parser.error('min sleep interval must be specified, use --min-sleep-interval')
        if opts.max_sleep_interval < opts.sleep_interval:
            parser.error('max sleep interval must be greater than or equal to min sleep interval')
    else:
        opts.max_sleep_interval = opts.sleep_interval
    if opts.sleep_interval_subtitles is not None:
        if opts.sleep_interval_subtitles < 0:
            parser.error('subtitles sleep interval must be positive or 0')
    if opts.sleep_interval_requests is not None:
        if opts.sleep_interval_requests < 0:
            parser.error('requests sleep interval must be positive or 0')
    if opts.ap_mso and opts.ap_mso not in MSO_INFO:
        parser.error('Unsupported TV Provider, use --ap-list-mso to get a list of supported TV Providers')
    if opts.overwrites:  # --yes-overwrites implies --no-continue
        opts.continue_dl = False
    if opts.concurrent_fragment_downloads <= 0:
        raise ValueError('Concurrent fragments must be positive')

    def parse_retries(retries, name=''):
        if retries in ('inf', 'infinite'):
            parsed_retries = float('inf')
        else:
            try:
                parsed_retries = int(retries)
            except (TypeError, ValueError):
                parser.error('invalid %sretry count specified' % name)
        return parsed_retries
    if opts.retries is not None:
        opts.retries = parse_retries(opts.retries)
    if opts.fragment_retries is not None:
        opts.fragment_retries = parse_retries(opts.fragment_retries, 'fragment ')
    if opts.extractor_retries is not None:
        opts.extractor_retries = parse_retries(opts.extractor_retries, 'extractor ')
    if opts.buffersize is not None:
        numeric_buffersize = FileDownloader.parse_bytes(opts.buffersize)
        if numeric_buffersize is None:
            parser.error('invalid buffer size specified')
        opts.buffersize = numeric_buffersize
    if opts.http_chunk_size is not None:
        numeric_chunksize = FileDownloader.parse_bytes(opts.http_chunk_size)
        if not numeric_chunksize:
            parser.error('invalid http chunk size specified')
        opts.http_chunk_size = numeric_chunksize
    if opts.playliststart <= 0:
        raise ValueError('Playlist start must be positive')
    if opts.playlistend not in (-1, None) and opts.playlistend < opts.playliststart:
        raise ValueError('Playlist end must be greater than playlist start')
    if opts.extractaudio:
        if opts.audioformat not in ['best'] + list(FFmpegExtractAudioPP.SUPPORTED_EXTS):
            parser.error('invalid audio format specified')
    if opts.audioquality:
        opts.audioquality = opts.audioquality.strip('k').strip('K')
        if not opts.audioquality.isdigit():
            parser.error('invalid audio quality specified')
    if opts.recodevideo is not None:
        opts.recodevideo = opts.recodevideo.replace(' ', '')
        if not re.match(FFmpegVideoConvertorPP.FORMAT_RE, opts.recodevideo):
            parser.error('invalid video remux format specified')
    if opts.remuxvideo is not None:
        opts.remuxvideo = opts.remuxvideo.replace(' ', '')
        if not re.match(FFmpegVideoRemuxerPP.FORMAT_RE, opts.remuxvideo):
            parser.error('invalid video remux format specified')
    if opts.convertsubtitles is not None:
        if opts.convertsubtitles not in FFmpegSubtitlesConvertorPP.SUPPORTED_EXTS:
            parser.error('invalid subtitle format specified')
    if opts.convertthumbnails is not None:
        if opts.convertthumbnails not in FFmpegThumbnailsConvertorPP.SUPPORTED_EXTS:
            parser.error('invalid thumbnail format specified')

    if opts.cookiesfrombrowser is not None:
        opts.cookiesfrombrowser = [
            part.strip() or None for part in opts.cookiesfrombrowser.split(':', 1)]
        if opts.cookiesfrombrowser[0] not in SUPPORTED_BROWSERS:
            parser.error('unsupported browser specified for cookies')

    if opts.date is not None:
        date = DateRange.day(opts.date)
    else:
        date = DateRange(opts.dateafter, opts.datebefore)

    def parse_compat_opts():
        parsed_compat_opts, compat_opts = set(), opts.compat_opts[::-1]
        while compat_opts:
            actual_opt = opt = compat_opts.pop().lower()
            if opt == 'youtube-dl':
                compat_opts.extend(['-multistreams', 'all'])
            elif opt == 'youtube-dlc':
                compat_opts.extend(['-no-youtube-channel-redirect', '-no-live-chat', 'all'])
            elif opt == 'all':
                parsed_compat_opts.update(all_compat_opts)
            elif opt == '-all':
                parsed_compat_opts = set()
            else:
                if opt[0] == '-':
                    opt = opt[1:]
                    parsed_compat_opts.discard(opt)
                else:
                    parsed_compat_opts.update([opt])
                if opt not in all_compat_opts:
                    parser.error('Invalid compatibility option %s' % actual_opt)
        return parsed_compat_opts

    all_compat_opts = [
        'filename', 'format-sort', 'abort-on-error', 'format-spec', 'no-playlist-metafiles',
        'multistreams', 'no-live-chat', 'playlist-index', 'list-formats', 'no-direct-merge',
        'no-youtube-channel-redirect', 'no-youtube-unavailable-videos', 'no-attach-info-json',
        'embed-thumbnail-atomicparsley', 'seperate-video-versions', 'no-clean-infojson', 'no-keep-subs',
    ]
    compat_opts = parse_compat_opts()

    def _unused_compat_opt(name):
        if name not in compat_opts:
            return False
        compat_opts.discard(name)
        compat_opts.update(['*%s' % name])
        return True

    def set_default_compat(compat_name, opt_name, default=True, remove_compat=True):
        attr = getattr(opts, opt_name)
        if compat_name in compat_opts:
            if attr is None:
                setattr(opts, opt_name, not default)
                return True
            else:
                if remove_compat:
                    _unused_compat_opt(compat_name)
                return False
        elif attr is None:
            setattr(opts, opt_name, default)
        return None

    set_default_compat('abort-on-error', 'ignoreerrors')
    set_default_compat('no-playlist-metafiles', 'allow_playlist_files')
    set_default_compat('no-clean-infojson', 'clean_infojson')
    if 'format-sort' in compat_opts:
        opts.format_sort.extend(InfoExtractor.FormatSort.ytdl_default)
    _video_multistreams_set = set_default_compat('multistreams', 'allow_multiple_video_streams', False, remove_compat=False)
    _audio_multistreams_set = set_default_compat('multistreams', 'allow_multiple_audio_streams', False, remove_compat=False)
    if _video_multistreams_set is False and _audio_multistreams_set is False:
        _unused_compat_opt('multistreams')
    outtmpl_default = opts.outtmpl.get('default')
    if 'filename' in compat_opts:
        if outtmpl_default is None:
            outtmpl_default = '%(title)s-%(id)s.%(ext)s'
            opts.outtmpl.update({'default': outtmpl_default})
        else:
            _unused_compat_opt('filename')

    def validate_outtmpl(tmpl, msg):
        err = YoutubeDL.validate_outtmpl(tmpl)
        if err:
            parser.error('invalid %s %r: %s' % (msg, tmpl, error_to_compat_str(err)))

    for k, tmpl in opts.outtmpl.items():
        validate_outtmpl(tmpl, '%s output template' % k)
    opts.forceprint = opts.forceprint or []
    for tmpl in opts.forceprint or []:
        validate_outtmpl(tmpl, 'print template')

    if opts.extractaudio and not opts.keepvideo and opts.format is None:
        opts.format = 'bestaudio/best'

    if outtmpl_default is not None and not os.path.splitext(outtmpl_default)[1] and opts.extractaudio:
        parser.error('Cannot download a video and extract audio into the same'
                     ' file! Use "{0}.%(ext)s" instead of "{0}" as the output'
                     ' template'.format(outtmpl_default))

    for f in opts.format_sort:
        if re.match(InfoExtractor.FormatSort.regex, f) is None:
            parser.error('invalid format sort string "%s" specified' % f)

    def metadataparser_actions(f):
        if isinstance(f, str):
            cmd = '--parse-metadata %s' % compat_shlex_quote(f)
            try:
                actions = [MetadataFromFieldPP.to_action(f)]
            except Exception as err:
                parser.error(f'{cmd} is invalid; {err}')
        else:
            cmd = '--replace-in-metadata %s' % ' '.join(map(compat_shlex_quote, f))
            actions = ((MetadataParserPP.Actions.REPLACE, x, *f[1:]) for x in f[0].split(','))

        for action in actions:
            try:
                MetadataParserPP.validate_action(*action)
            except Exception as err:
                parser.error(f'{cmd} is invalid; {err}')
            yield action

    if opts.parse_metadata is None:
        opts.parse_metadata = []
    if opts.metafromtitle is not None:
        opts.parse_metadata.append('title:%s' % opts.metafromtitle)
    opts.parse_metadata = list(itertools.chain(*map(metadataparser_actions, opts.parse_metadata)))

    any_getting = opts.forceprint or opts.geturl or opts.gettitle or opts.getid or opts.getthumbnail or opts.getdescription or opts.getfilename or opts.getformat or opts.getduration or opts.dumpjson or opts.dump_single_json
    any_printing = opts.print_json
    download_archive_fn = expand_path(opts.download_archive) if opts.download_archive is not None else opts.download_archive

    # If JSON is not printed anywhere, but comments are requested, save it to file
    printing_json = opts.dumpjson or opts.print_json or opts.dump_single_json
    if opts.getcomments and not printing_json:
        opts.writeinfojson = True

    def report_conflict(arg1, arg2):
        warnings.append('%s is ignored since %s was given' % (arg2, arg1))

    if opts.remuxvideo and opts.recodevideo:
        report_conflict('--recode-video', '--remux-video')
        opts.remuxvideo = False
    if opts.sponskrub_cut and opts.split_chapters and opts.sponskrub is not False:
        report_conflict('--split-chapter', '--sponskrub-cut')
        opts.sponskrub_cut = False

    if opts.allow_unplayable_formats:
        if opts.extractaudio:
            report_conflict('--allow-unplayable-formats', '--extract-audio')
            opts.extractaudio = False
        if opts.remuxvideo:
            report_conflict('--allow-unplayable-formats', '--remux-video')
            opts.remuxvideo = False
        if opts.recodevideo:
            report_conflict('--allow-unplayable-formats', '--recode-video')
            opts.recodevideo = False
        if opts.addmetadata:
            report_conflict('--allow-unplayable-formats', '--add-metadata')
            opts.addmetadata = False
        if opts.embedsubtitles:
            report_conflict('--allow-unplayable-formats', '--embed-subs')
            opts.embedsubtitles = False
        if opts.embedthumbnail:
            report_conflict('--allow-unplayable-formats', '--embed-thumbnail')
            opts.embedthumbnail = False
        if opts.xattrs:
            report_conflict('--allow-unplayable-formats', '--xattrs')
            opts.xattrs = False
        if opts.fixup and opts.fixup.lower() not in ('never', 'ignore'):
            report_conflict('--allow-unplayable-formats', '--fixup')
        opts.fixup = 'never'
        if opts.sponskrub:
            report_conflict('--allow-unplayable-formats', '--sponskrub')
        opts.sponskrub = False

    # PostProcessors
    postprocessors = []
    if opts.parse_metadata:
        postprocessors.append({
            'key': 'MetadataParser',
            'actions': opts.parse_metadata,
            # Run this immediately after extraction is complete
            'when': 'pre_process'
        })
    if opts.convertsubtitles:
        postprocessors.append({
            'key': 'FFmpegSubtitlesConvertor',
            'format': opts.convertsubtitles,
            # Run this before the actual video download
            'when': 'before_dl'
        })
    if opts.convertthumbnails:
        postprocessors.append({
            'key': 'FFmpegThumbnailsConvertor',
            'format': opts.convertthumbnails,
            # Run this before the actual video download
            'when': 'before_dl'
        })
    # Must be after all other before_dl
    if opts.exec_before_dl_cmd:
        postprocessors.append({
            'key': 'Exec',
            'exec_cmd': opts.exec_before_dl_cmd,
            'when': 'before_dl'
        })
    if opts.extractaudio:
        postprocessors.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': opts.audioformat,
            'preferredquality': opts.audioquality,
            'nopostoverwrites': opts.nopostoverwrites,
        })
    if opts.remuxvideo:
        postprocessors.append({
            'key': 'FFmpegVideoRemuxer',
            'preferedformat': opts.remuxvideo,
        })
    if opts.recodevideo:
        postprocessors.append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': opts.recodevideo,
        })
    # FFmpegMetadataPP should be run after FFmpegVideoConvertorPP and
    # FFmpegExtractAudioPP as containers before conversion may not support
    # metadata (3gp, webm, etc.)
    # And this post-processor should be placed before other metadata
    # manipulating post-processors (FFmpegEmbedSubtitle) to prevent loss of
    # extra metadata. By default ffmpeg preserves metadata applicable for both
    # source and target containers. From this point the container won't change,
    # so metadata can be added here.
    if opts.addmetadata:
        postprocessors.append({'key': 'FFmpegMetadata'})
    if opts.embedsubtitles:
        already_have_subtitle = opts.writesubtitles and 'no-keep-subs' not in compat_opts
        postprocessors.append({
            'key': 'FFmpegEmbedSubtitle',
            # already_have_subtitle = True prevents the file from being deleted after embedding
            'already_have_subtitle': already_have_subtitle
        })
        if not opts.writeautomaticsub and 'no-keep-subs' not in compat_opts:
            opts.writesubtitles = True
    # --all-sub automatically sets --write-sub if --write-auto-sub is not given
    # this was the old behaviour if only --all-sub was given.
    if opts.allsubtitles and not opts.writeautomaticsub:
        opts.writesubtitles = True
    # This should be above EmbedThumbnail since sponskrub removes the thumbnail attachment
    # but must be below EmbedSubtitle and FFmpegMetadata
    # See https://github.com/yt-dlp/yt-dlp/issues/204 , https://github.com/faissaloo/SponSkrub/issues/29
    # If opts.sponskrub is None, sponskrub is used, but it silently fails if the executable can't be found
    if opts.sponskrub is not False:
        postprocessors.append({
            'key': 'SponSkrub',
            'path': opts.sponskrub_path,
            'args': opts.sponskrub_args,
            'cut': opts.sponskrub_cut,
            'force': opts.sponskrub_force,
            'ignoreerror': opts.sponskrub is None,
        })
    if opts.embedthumbnail:
        already_have_thumbnail = opts.writethumbnail or opts.write_all_thumbnails
        postprocessors.append({
            'key': 'EmbedThumbnail',
            # already_have_thumbnail = True prevents the file from being deleted after embedding
            'already_have_thumbnail': already_have_thumbnail
        })
        if not already_have_thumbnail:
            opts.writethumbnail = True
    if opts.split_chapters:
        postprocessors.append({'key': 'FFmpegSplitChapters'})
    # XAttrMetadataPP should be run after post-processors that may change file contents
    if opts.xattrs:
        postprocessors.append({'key': 'XAttrMetadata'})
    # Exec must be the last PP
    if opts.exec_cmd:
        postprocessors.append({
            'key': 'Exec',
            'exec_cmd': opts.exec_cmd,
            # Run this only after the files have been moved to their final locations
            'when': 'after_move'
        })

    def report_args_compat(arg, name):
        warnings.append('%s given without specifying name. The arguments will be given to all %s' % (arg, name))

    if 'default' in opts.external_downloader_args:
        report_args_compat('--downloader-args', 'external downloaders')

    if 'default-compat' in opts.postprocessor_args and 'default' not in opts.postprocessor_args:
        report_args_compat('--post-processor-args', 'post-processors')
        opts.postprocessor_args.setdefault('sponskrub', [])
        opts.postprocessor_args['default'] = opts.postprocessor_args['default-compat']

    final_ext = (
        opts.recodevideo if opts.recodevideo in FFmpegVideoConvertorPP.SUPPORTED_EXTS
        else opts.remuxvideo if opts.remuxvideo in FFmpegVideoRemuxerPP.SUPPORTED_EXTS
        else opts.audioformat if (opts.extractaudio and opts.audioformat != 'best')
        else None)

    match_filter = (
        None if opts.match_filter is None
        else match_filter_func(opts.match_filter))

    ydl_opts = {
        'usenetrc': opts.usenetrc,
        'username': opts.username,
        'password': opts.password,
        'twofactor': opts.twofactor,
        'videopassword': opts.videopassword,
        'ap_mso': opts.ap_mso,
        'ap_username': opts.ap_username,
        'ap_password': opts.ap_password,
        'quiet': (opts.quiet or any_getting or any_printing),
        'no_warnings': opts.no_warnings,
        'forceurl': opts.geturl,
        'forcetitle': opts.gettitle,
        'forceid': opts.getid,
        'forcethumbnail': opts.getthumbnail,
        'forcedescription': opts.getdescription,
        'forceduration': opts.getduration,
        'forcefilename': opts.getfilename,
        'forceformat': opts.getformat,
        'forceprint': opts.forceprint,
        'forcejson': opts.dumpjson or opts.print_json,
        'dump_single_json': opts.dump_single_json,
        'force_write_download_archive': opts.force_write_download_archive,
        'simulate': (any_getting or None) if opts.simulate is None else opts.simulate,
        'skip_download': opts.skip_download,
        'format': opts.format,
        'allow_unplayable_formats': opts.allow_unplayable_formats,
        'ignore_no_formats_error': opts.ignore_no_formats_error,
        'format_sort': opts.format_sort,
        'format_sort_force': opts.format_sort_force,
        'allow_multiple_video_streams': opts.allow_multiple_video_streams,
        'allow_multiple_audio_streams': opts.allow_multiple_audio_streams,
        'check_formats': opts.check_formats,
        'listformats': opts.listformats,
        'listformats_table': opts.listformats_table,
        'outtmpl': opts.outtmpl,
        'outtmpl_na_placeholder': opts.outtmpl_na_placeholder,
        'paths': opts.paths,
        'autonumber_size': opts.autonumber_size,
        'autonumber_start': opts.autonumber_start,
        'restrictfilenames': opts.restrictfilenames,
        'windowsfilenames': opts.windowsfilenames,
        'ignoreerrors': opts.ignoreerrors,
        'force_generic_extractor': opts.force_generic_extractor,
        'ratelimit': opts.ratelimit,
        'throttledratelimit': opts.throttledratelimit,
        'overwrites': opts.overwrites,
        'retries': opts.retries,
        'fragment_retries': opts.fragment_retries,
        'extractor_retries': opts.extractor_retries,
        'skip_unavailable_fragments': opts.skip_unavailable_fragments,
        'keep_fragments': opts.keep_fragments,
        'concurrent_fragment_downloads': opts.concurrent_fragment_downloads,
        'buffersize': opts.buffersize,
        'noresizebuffer': opts.noresizebuffer,
        'http_chunk_size': opts.http_chunk_size,
        'continuedl': opts.continue_dl,
        'noprogress': opts.noprogress,
        'progress_with_newline': opts.progress_with_newline,
        'playliststart': opts.playliststart,
        'playlistend': opts.playlistend,
        'playlistreverse': opts.playlist_reverse,
        'playlistrandom': opts.playlist_random,
        'noplaylist': opts.noplaylist,
        'logtostderr': outtmpl_default == '-',
        'consoletitle': opts.consoletitle,
        'nopart': opts.nopart,
        'updatetime': opts.updatetime,
        'writedescription': opts.writedescription,
        'writeannotations': opts.writeannotations,
        'writeinfojson': opts.writeinfojson,
        'allow_playlist_files': opts.allow_playlist_files,
        'clean_infojson': opts.clean_infojson,
        'getcomments': opts.getcomments,
        'writethumbnail': opts.writethumbnail,
        'write_all_thumbnails': opts.write_all_thumbnails,
        'writelink': opts.writelink,
        'writeurllink': opts.writeurllink,
        'writewebloclink': opts.writewebloclink,
        'writedesktoplink': opts.writedesktoplink,
        'writesubtitles': opts.writesubtitles,
        'writeautomaticsub': opts.writeautomaticsub,
        'allsubtitles': opts.allsubtitles,
        'listsubtitles': opts.listsubtitles,
        'subtitlesformat': opts.subtitlesformat,
        'subtitleslangs': opts.subtitleslangs,
        'matchtitle': decodeOption(opts.matchtitle),
        'rejecttitle': decodeOption(opts.rejecttitle),
        'max_downloads': opts.max_downloads,
        'prefer_free_formats': opts.prefer_free_formats,
        'trim_file_name': opts.trim_file_name,
        'verbose': opts.verbose,
        'dump_intermediate_pages': opts.dump_intermediate_pages,
        'write_pages': opts.write_pages,
        'test': opts.test,
        'keepvideo': opts.keepvideo,
        'min_filesize': opts.min_filesize,
        'max_filesize': opts.max_filesize,
        'min_views': opts.min_views,
        'max_views': opts.max_views,
        'daterange': date,
        'cachedir': opts.cachedir,
        'youtube_print_sig_code': opts.youtube_print_sig_code,
        'age_limit': opts.age_limit,
        'download_archive': download_archive_fn,
        'break_on_existing': opts.break_on_existing,
        'break_on_reject': opts.break_on_reject,
        'skip_playlist_after_errors': opts.skip_playlist_after_errors,
        'cookiefile': opts.cookiefile,
        'cookiesfrombrowser': opts.cookiesfrombrowser,
        'nocheckcertificate': opts.no_check_certificate,
        'prefer_insecure': opts.prefer_insecure,
        'proxy': opts.proxy,
        'socket_timeout': opts.socket_timeout,
        'bidi_workaround': opts.bidi_workaround,
        'debug_printtraffic': opts.debug_printtraffic,
        'prefer_ffmpeg': opts.prefer_ffmpeg,
        'include_ads': opts.include_ads,
        'default_search': opts.default_search,
        'dynamic_mpd': opts.dynamic_mpd,
        'extractor_args': opts.extractor_args,
        'youtube_include_dash_manifest': opts.youtube_include_dash_manifest,
        'youtube_include_hls_manifest': opts.youtube_include_hls_manifest,
        'encoding': opts.encoding,
        'extract_flat': opts.extract_flat,
        'mark_watched': opts.mark_watched,
        'merge_output_format': opts.merge_output_format,
        'final_ext': final_ext,
        'postprocessors': postprocessors,
        'fixup': opts.fixup,
        'source_address': opts.source_address,
        'call_home': opts.call_home,
        'sleep_interval_requests': opts.sleep_interval_requests,
        'sleep_interval': opts.sleep_interval,
        'max_sleep_interval': opts.max_sleep_interval,
        'sleep_interval_subtitles': opts.sleep_interval_subtitles,
        'external_downloader': opts.external_downloader,
        'list_thumbnails': opts.list_thumbnails,
        'playlist_items': opts.playlist_items,
        'xattr_set_filesize': opts.xattr_set_filesize,
        'match_filter': match_filter,
        'no_color': opts.no_color,
        'ffmpeg_location': opts.ffmpeg_location,
        'hls_prefer_native': opts.hls_prefer_native,
        'hls_use_mpegts': opts.hls_use_mpegts,
        'hls_split_discontinuity': opts.hls_split_discontinuity,
        'external_downloader_args': opts.external_downloader_args,
        'postprocessor_args': opts.postprocessor_args,
        'cn_verification_proxy': opts.cn_verification_proxy,
        'geo_verification_proxy': opts.geo_verification_proxy,
        'geo_bypass': opts.geo_bypass,
        'geo_bypass_country': opts.geo_bypass_country,
        'geo_bypass_ip_block': opts.geo_bypass_ip_block,
        'warnings': warnings,
        'compat_opts': compat_opts,
        # just for deprecation check
        'autonumber': opts.autonumber or None,
        'usetitle': opts.usetitle or None,
        'useid': opts.useid or None,
    }

    with YoutubeDL(ydl_opts) as ydl:
        actual_use = len(all_urls) or opts.load_info_filename

        # Remove cache dir
        if opts.rm_cachedir:
            ydl.cache.remove()

        # Update version
        if opts.update_self:
            # If updater returns True, exit. Required for windows
            if run_update(ydl):
                if actual_use:
                    sys.exit('ERROR: The program must exit for the update to complete')
                sys.exit()

        # Maybe do nothing
        if not actual_use:
            if opts.update_self or opts.rm_cachedir:
                sys.exit()

            ydl.warn_if_short_id(sys.argv[1:] if argv is None else argv)
            parser.error(
                'You must provide at least one URL.\n'
                'Type yt-dlp --help to see a list of all options.')

        try:
            if opts.load_info_filename is not None:
                retcode = ydl.download_with_info_file(expand_path(opts.load_info_filename))
            else:
                retcode = ydl.download(all_urls)
        except (MaxDownloadsReached, ExistingVideoReached, RejectedVideoReached):
            ydl.to_screen('Aborting remaining downloads')
            retcode = 101

    sys.exit(retcode)


def main(argv=None):
    try:
        _real_main(argv)
    except DownloadError:
        sys.exit(1)
    except SameFileError:
        sys.exit('ERROR: fixed output name but more than one file to download')
    except KeyboardInterrupt:
        sys.exit('\nERROR: Interrupted by user')
    except BrokenPipeError:
        # https://docs.python.org/3/library/signal.html#note-on-sigpipe
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(r'\nERROR: {err}')


__all__ = ['main', 'YoutubeDL', 'gen_extractors', 'list_extractors']

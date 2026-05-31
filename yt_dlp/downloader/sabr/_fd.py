from __future__ import annotations
import collections
import contextlib
import itertools
import math
import signal
import time
import typing
from yt_dlp.globals import IN_CLI

from yt_dlp.utils import traverse_obj, int_or_none, DownloadError, join_nonempty
from yt_dlp.downloader import FileDownloader

from ._writer import SabrFDFormatWriter
from ._logger import create_sabrfd_logger

from yt_dlp.extractor.youtube._streaming.sabr.part import (
    MediaSegmentEndSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentInitSabrPart,
    FormatInitializedSabrPart,
    LiveStateSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import (
    SabrStream,
    Heartbeat,
    ReloadConfigResponse,
)
from yt_dlp.extractor.youtube._streaming.sabr.models import (
    ConsumedRange,
    AudioSelector,
    VideoSelector,
    CaptionSelector,
    PoTokenStatus, ReloadConfigReason,
)
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrStreamError, BroadcastIdChanged
from yt_dlp.extractor.youtube._proto.innertube import ClientInfo, ClientName
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.extractor.youtube._streaming.sabr.processor import JS_MAX_SAFE_INTEGER

if typing.TYPE_CHECKING:
    from yt_dlp.extractor.youtube._streaming.sabr.stream import (
        PotCallback,
        ReloadCallback,
        HeartbeatCallback,
        ReloadConfigRequest,
    )


USER_FORCE_QUIT_WINDOW_SEC = 2.0


class SabrFdSession:
    def __init__(
        self,
        fd: SabrFD,
        video_id: str | None,
        info_dict: dict,
        video_format: dict | None,
        audio_format: dict | None,
        caption_format: dict | None,
        resume: bool,
        is_test: bool,
        server_abr_streaming_url: str,
        video_playback_ustreamer_config: str,
        initial_po_token: str | None,
        pot_callback: PotCallback | None,
        reload_callback: ReloadCallback | None,
        heartbeat_callback: HeartbeatCallback | None,
        client_info: ClientInfo,
        live_from_start: bool,
        target_duration_sec: int | None,
        live_status: str | None,
    ):
        self.fd = fd
        self.video_id = video_id
        self.info_dict = info_dict
        self.video_format = video_format
        self.audio_format = audio_format
        self.caption_format = caption_format
        self.resume = resume
        self.is_test = is_test
        self.live_from_start = live_from_start
        self.target_duration_sec = target_duration_sec
        self.live_status = live_status
        self.writers: dict[str, SabrFDFormatWriter] = {}
        self.stream = None
        self._logged_dvr_message = False
        self._enable_live_deep_rewind = traverse_obj(
            self.fd.ydl.params, ('extractor_args', 'youtube', 'enable_live_deep_rewind', 0, {str}), get_all=False) == 'true'

        # NOTE: the below may become outdated once callbacks are used
        self.server_abr_streaming_url = server_abr_streaming_url
        self.video_playback_ustreamer_config = video_playback_ustreamer_config
        self.initial_po_token = initial_po_token
        self.pot_callback = pot_callback
        self.reload_callback = reload_callback
        self.heartbeat_callback = heartbeat_callback
        self.client_info = client_info

    @property
    def is_live(self):
        # are we live? (excluding post_live)
        return (
            self.live_status == 'is_live'
            or (self.stream and self.stream.processor.is_live and not self.stream.processor.post_live))

    @property
    def is_post_live(self):
        return self.live_status == 'post_live' or (self.stream and self.stream.processor.post_live)

    def run(self):
        audio_selector, video_selector, caption_selector = self._create_writers()

        # Report the destination files before we start downloading instead of when we initialize the writers,
        # as the formats may not all start at the same time (leading to messy output)
        for writer in self.writers.values():
            self.fd.report_destination(writer.filename)

        start_time_ms = JS_MAX_SAFE_INTEGER if self.is_live and not self.live_from_start else 0

        if self._enable_live_deep_rewind and self.is_live:
            self.fd.report_warning(
                'Enabled live deep rewind. This feature is under development and experimental. '
                'Unexpected behavior may occur and the integrity of the downloaded files cannot be guaranteed.')

        self.stream = SabrStream(
            urlopen=self.fd.ydl.urlopen,
            logger=create_sabrfd_logger(self.fd.ydl, prefix='sabr:stream'),
            server_abr_streaming_url=self.server_abr_streaming_url,
            video_playback_ustreamer_config=self.video_playback_ustreamer_config,
            po_token=self.initial_po_token,
            video_selection=video_selector,
            audio_selection=audio_selector,
            caption_selection=caption_selector,
            start_time_ms=start_time_ms,
            client_info=self.client_info,
            live_segment_target_duration_sec=self.target_duration_sec,
            post_live=self.is_post_live,
            video_id=self.video_id,
            retry_sleep_func=self.fd.params.get('retry_sleep_functions', {}).get('http'),
            heartbeat_callback=self.heartbeat_callback,
            pot_callback=self.pot_callback,
            reload_callback=self.reload_callback,
            enable_live_deep_rewind=self._enable_live_deep_rewind,
        )

        self.fd._prepare_multiline_status(len(self.writers) + 1)

        original_handler = signal.getsignal(signal.SIGINT)
        try:
            if IN_CLI.value:
                # Custom signal handler to allow graceful shutdown on Ctrl+C for livestreams
                # Only used if running in the CLI to avoid conflicts with custom signal handlers
                # that may be registered when using yt-dlp as a library.
                signal.signal(signal.SIGINT, self._create_signal_handler())
            self._download()
        finally:
            if IN_CLI.value:
                signal.signal(signal.SIGINT, original_handler)

            self.stream.close()
            for writer in self.writers.values():
                writer.close()

            self.fd._finish_multiline_status()

    # region: initialization
    def _create_signal_handler(self):
        # Allow livestreams to exit cleanly
        last_interrupt_at = [0.0]

        def handler(signum, frame):
            if not self.is_live:
                raise KeyboardInterrupt

            current_time = time.monotonic()
            if last_interrupt_at[0] > 0.0 and (current_time - last_interrupt_at[0] <= USER_FORCE_QUIT_WINDOW_SEC):
                raise KeyboardInterrupt

            last_interrupt_at[0] = current_time
            with self.fd.break_multiline():
                self.fd.report_warning(
                    'Interrupted by user. Finishing current segments and finalizing formats. Press Ctrl+C again to force quit.')
            self.stream.close()

        return handler

    def _create_writers(self):
        audio_selector = None
        video_selector = None
        caption_selector = None

        if self.audio_format:
            audio_selector = AudioSelector(
                display_name=self.audio_format['display_name'], format_ids=[self.audio_format['format_id']])
            self.writers[audio_selector.display_name] = SabrFDFormatWriter(
                self.fd, self.audio_format.get('filename'),
                self.audio_format['info_dict'], len(self.writers), resume=self.resume)

        if self.video_format:
            video_selector = VideoSelector(
                display_name=self.video_format['display_name'], format_ids=[self.video_format['format_id']])
            self.writers[video_selector.display_name] = SabrFDFormatWriter(
                self.fd, self.video_format.get('filename'),
                self.video_format['info_dict'], len(self.writers), resume=self.resume)

        if self.caption_format:
            caption_selector = CaptionSelector(
                display_name=self.caption_format['display_name'], format_ids=[self.caption_format['format_id']])
            self.writers[caption_selector.display_name] = SabrFDFormatWriter(
                self.fd, self.caption_format.get('filename'),
                self.caption_format['info_dict'], len(self.writers), resume=self.resume)

        return audio_selector, video_selector, caption_selector

    # endregion

    # region: download
    def _download(self):
        try:
            total_bytes = 0  # used for --test
            for part in self.stream:
                if self.is_test and total_bytes >= self.fd._TEST_FILE_SIZE:
                    break
                if isinstance(part, MediaSegmentDataSabrPart):
                    total_bytes += part.content_length
                self._process_sabr_part(part)
            self._finish_formats()
        except BroadcastIdChanged as e:
            # Core does not currently support multiple broadcasts under the same video ID.
            self.fd.write_debug(f'[SABR Debug Info]: {self.stream.create_stats_str()}')
            self.fd.write_debug(f'Got error: {e!r}')
            self.fd.report_warning(
                'The current stream download is complete, however a new stream may have started under the same video ID.')
            self._finish_formats()
        except SabrStreamError as e:
            self.fd.write_debug(f'[SABR Debug Info]: {self.stream.create_stats_str()}')
            raise DownloadError(str(e))

    def _process_sabr_part(self, part) -> None:
        if isinstance(part, FormatInitializedSabrPart):
            writer = self.writers.get(part.format_selector.display_name)
            if not writer:
                self.fd.report_warning(f'Unknown format selector: {part.format_selector}')
                return

            writer.initialize_format(part.format_id, self.stream.broadcast_id if self.is_live else None)
            initialized_format = self.stream.processor.initialized_formats[str(part.format_id)]

            # Resume format, if applicable
            if writer.state.init_sequence:
                initialized_format.init_segment = True

            # Build consumed ranges from the sequences
            consumed_ranges = []
            for sequence in writer.state.sequences:
                consumed_ranges.append(ConsumedRange(
                    start_time_ms=sequence.first_segment.start_time_ms,
                    duration_ms=(sequence.last_segment.start_time_ms + sequence.last_segment.duration_ms) - sequence.first_segment.start_time_ms,
                    start_sequence_number=sequence.first_segment.sequence_number,
                    end_sequence_number=sequence.last_segment.sequence_number,
                ))
            if consumed_ranges:
                initialized_format.consumed_ranges = consumed_ranges
                self.fd.to_screen(f'[download] Resuming download for format {part.format_selector.display_name}')

        elif isinstance(part, MediaSegmentInitSabrPart):
            writer = self.writers.get(part.format_selector.display_name)
            if not writer:
                self.fd.report_warning(f'Unknown init format selector: {part.format_selector}')
                return
            writer.initialize_segment(part)

        elif isinstance(part, MediaSegmentDataSabrPart):
            writer = self.writers.get(part.format_selector.display_name)
            if not writer:
                self.fd.report_warning(f'Unknown data format selector: {part.format_selector}')
                return
            writer.write_segment_data(part)

        elif isinstance(part, MediaSegmentEndSabrPart):
            writer = self.writers.get(part.format_selector.display_name)
            if not writer:
                self.fd.report_warning(f'Unknown end format selector: {part.format_selector}')
                return
            writer.end_segment(part)

        elif isinstance(part, LiveStateSabrPart):
            if not part.full_stream_available:
                self._log_dvr_window_availability(part.available_dvr_window_ms)

    def _log_dvr_window_availability(self, available_dvr_window_ms):
        if self._logged_dvr_message:
            return
        hours = math.ceil(available_dvr_window_ms / (3600 * 1000))
        if self.live_from_start:
            if not hours:
                self.fd.to_screen(
                    '[download] Downloading from the live edge; the streamer has disabled DVR for this stream')
            else:
                self.fd.to_screen(
                    f'[download] Downloading the past {hours} hour(s) of the live stream; full stream is not available')
            # TODO: proper logging
            if self._enable_live_deep_rewind:
                self.fd.to_screen(
                    '[download] Live deep rewind is enabled, will attempt to download as early as possible')
        else:
            self.fd.to_screen(
                '[download] Downloading from the live edge; pass --live-from-start to download from the beginning of the stream')
        self._logged_dvr_message = True

    # endregion

    # region: finalization
    def _count_writer_segments(self, writer):
        return sum(
            sequence.last_segment.sequence_number - sequence.first_segment.sequence_number + 1
            for sequence in writer.state.sequences)

    def _finish_formats(self):
        # Live and Post-Live formats should have the same segment count.
        # If there is a mismatch, likely one format is missing segments.
        # This usually only happens on resuming a livestream download, such as:
        # - when the stream has no DVR
        # - downloading from the start on a 12+ hour stream.
        if len(self.writers) > 1 and (self.is_live or self.is_post_live):
            expected_segment_count = None
            for writer in self.writers.values():
                segment_count = self._count_writer_segments(writer)
                if expected_segment_count is None:
                    expected_segment_count = segment_count
                    continue
                if segment_count != expected_segment_count:
                    self.fd.report_warning(
                        'Detected a segment alignment mismatch across downloaded formats. '
                        'The formats may be out of sync in the merged file.',
                        only_once=True)
                    break
                if segment_count == 0:
                    # Should only occur for non-DVR livestreams if started at the edge after the stream ended.
                    # Other cases should raise a stall error.
                    self.fd.to_screen(f'[SABR Debug Info]: {self.stream.create_stats_str()}')
                    self.fd.report_warning('[download] Did not receive data for one or more formats')
                    break

        for writer in self.writers.values():
            writer.finish()

    # endregion


class SabrFD(FileDownloader):
    @classmethod
    def can_download(cls, info_dict):
        return (
            info_dict.get('requested_formats')
            and all(
                format_info.get('protocol') == 'sabr'
                for format_info in info_dict['requested_formats']))

    def _client_info_from_json(self, client_info_json):
        return ClientInfo(
            **{
                **client_info_json,
                'client_name': traverse_obj(client_info_json, ('client_name', {lambda x: ClientName[x]})),
            })

    def _group_formats_by_client(self, filename, info_dict):
        format_groups = collections.defaultdict(dict, {})
        requested_formats = info_dict.get('requested_formats') or [info_dict]

        for _idx, f in enumerate(requested_formats):
            sabr_config = f.get('_sabr_config')
            client_name = sabr_config.get('client_name')
            client_info = self._client_info_from_json(sabr_config.get('client_info'))
            server_abr_streaming_url = f.get('url')
            video_playback_ustreamer_config = sabr_config.get('video_playback_ustreamer_config')

            if not video_playback_ustreamer_config:
                raise DownloadError('Video playback ustreamer config not found')

            sabr_format_group_config = format_groups.get(client_name)

            if not sabr_format_group_config:
                sabr_format_group_config = format_groups[client_name] = {
                    'server_abr_streaming_url': server_abr_streaming_url,
                    'video_playback_ustreamer_config': video_playback_ustreamer_config,
                    'formats': [],
                    'initial_po_token': sabr_config.get('po_token'),
                    'fetch_po_token_fn': fn if callable(fn := sabr_config.get('fetch_po_token_fn')) else None,
                    'reload_config_fn': fn if callable(fn := sabr_config.get('reload_config_fn')) else None,
                    'extract_heartbeat_fn': fn if callable(fn := sabr_config.get('extract_heartbeat_fn')) else None,
                    'live_status': sabr_config.get('live_status'),
                    'video_id': sabr_config.get('video_id'),
                    'client_info': client_info,
                    'target_duration_sec': sabr_config.get('target_duration_sec'),
                    'live_from_start': f.get('is_from_start', False),
                }
                if not sabr_format_group_config['reload_config_fn']:
                    self.report_warning(
                        f'[download] Some SABR downloader features are not available when using --load-info-json. '
                        f'This may impact the integrity of the download. '
                        f'It is recommended {self.ydl._format_err("NOT", self.ydl.Styles.EMPHASIS)} to use --load-info-json with YouTube.',
                        only_once=True)

            else:
                if sabr_format_group_config['server_abr_streaming_url'] != server_abr_streaming_url:
                    raise DownloadError('Server ABR streaming URL mismatch')

                if sabr_format_group_config['video_playback_ustreamer_config'] != video_playback_ustreamer_config:
                    raise DownloadError('Video playback ustreamer config mismatch')

            itag = int_or_none(sabr_config.get('itag'))
            sabr_format_group_config['formats'].append({
                'display_name': f.get('format_id'),
                'format_id': itag and FormatId(
                    itag=itag, lmt=int_or_none(sabr_config.get('last_modified')), xtags=sabr_config.get('xtags')),
                'format_type': format_type(f),
                'quality': sabr_config.get('quality'),
                'height': sabr_config.get('height'),
                'filename': f.get('filepath', filename),
                'info_dict': f,
            })

        return format_groups

    def real_download(self, filename, info_dict):
        format_groups = self._group_formats_by_client(filename, info_dict)

        is_test = self.params.get('test', False)
        resume = self.params.get('continuedl', True)

        for client_name, format_group in format_groups.items():
            formats = format_group['formats']
            audio_formats = (f for f in formats if f['format_type'] == 'audio')
            video_formats = (f for f in formats if f['format_type'] == 'video')
            caption_formats = (f for f in formats if f['format_type'] == 'caption')
            for audio_format, video_format, caption_format in itertools.zip_longest(audio_formats, video_formats, caption_formats):
                format_str = join_nonempty(*[
                    traverse_obj(audio_format, 'display_name'),
                    traverse_obj(video_format, 'display_name'),
                    traverse_obj(caption_format, 'display_name')], delim='+')
                self.write_debug(f'Downloading formats: {format_str} ({client_name} client)')
                session = SabrFdSession(
                    fd=self,
                    video_id=format_group.get('video_id'),
                    info_dict=info_dict,
                    video_format=video_format,
                    audio_format=audio_format,
                    caption_format=caption_format,
                    resume=resume,
                    is_test=is_test,
                    server_abr_streaming_url=format_group['server_abr_streaming_url'],
                    video_playback_ustreamer_config=format_group['video_playback_ustreamer_config'],
                    initial_po_token=format_group['initial_po_token'],
                    pot_callback=self._create_pot_callback(format_group['fetch_po_token_fn']),
                    reload_callback=self._create_reload_callback(format_group['reload_config_fn']),
                    heartbeat_callback=self._create_heartbeat_callback(format_group['extract_heartbeat_fn']),
                    client_info=format_group['client_info'],
                    live_from_start=format_group['live_from_start'],
                    target_duration_sec=format_group.get('target_duration_sec', None),
                    live_status=format_group.get('live_status'),
                )
                session.run()
        return True

    def _create_heartbeat_callback(self, extract_heartbeat_fn) -> HeartbeatCallback | None:
        if not extract_heartbeat_fn:
            return None
        logger = create_sabrfd_logger(self.ydl, prefix='sabr:heartbeat')

        def callback():
            heartbeat = extract_heartbeat_fn() if extract_heartbeat_fn else None
            if not heartbeat:
                return None
            logger.trace(f'Extracted heartbeat: {heartbeat}')
            playability_status = traverse_obj(heartbeat, 'playabilityStatus')

            lsr = traverse_obj(playability_status, ('liveStreamability', 'liveStreamabilityRenderer'))

            # note: premieres do not have a broadcastId
            broadcast_id = traverse_obj(lsr, ('broadcastId', {str}))
            video_id = traverse_obj(lsr, ('videoId', {str}))
            status = traverse_obj(playability_status, 'status')
            reason = traverse_obj(playability_status, 'reason')

            logger.debug(
                f'Heartbeat status: {status}, reason: {reason or "n/a"}, broadcast_id: {broadcast_id or "n/a"}, video_id: {video_id}')

            if status == 'OK':
                logger.debug('Live stream is online')
                return Heartbeat(is_live=True, broadcast_id=broadcast_id, video_id=video_id)
            elif status == 'LIVE_STREAM_OFFLINE':
                display_endscreen = traverse_obj(lsr, ('displayEndscreen', {bool}))
                offline_slate = traverse_obj(lsr, 'offlineSlate')
                # actionButtons used instead of displayEndscreen on some clients (e.g. mweb).
                offline_slate_actions = traverse_obj(offline_slate, ('liveStreamOfflineSlateRenderer', 'actionButtons'))

                # Streamer disconnected - may come back online shortly
                if offline_slate and not display_endscreen and not offline_slate_actions:
                    logger.debug(
                        'Streamer disconnected - live stream is offline. '
                        'Considering as live until terminal status is reached. ')
                    return Heartbeat(is_live=True, broadcast_id=broadcast_id, video_id=video_id)
                elif lsr and (display_endscreen or offline_slate_actions):
                    # Otherwise, consider live stream offline
                    logger.debug('Live stream is offline')
                    return Heartbeat(is_live=False, broadcast_id=broadcast_id, video_id=video_id)
                elif not lsr and not broadcast_id:
                    # Might be a member's only stream - cannot determine if complete or not.
                    # This could potentially happen if cookies have rotated and auth is not working.
                    logger.warning(
                        'Cannot determine the status of the live stream. '
                        'If this stream requires an account to access, then the provided account cookies are probably no longer valid')
                    return None

            elif status == 'UNPLAYABLE':
                # Stream has gone private. It may have finished and gone private, or temporarily gone private.
                # Cannot determine the status. Note: None will cause it to be treated as ended.
                return None

            # Cannot determine live status from heartbeat
            # TODO(future): consider returning a heartbeat anyways with the broadcast id if we can extract it.
            logger.debug('Unknown status, not returning a heartbeat')
            return None

        return callback

    def _create_reload_callback(self, reload_config_fn) -> ReloadCallback | None:
        if not reload_config_fn:
            return None

        def callback(request: ReloadConfigRequest):
            if not reload_config_fn:
                self._report_reload_callback_unavailable()
                return None

            self._report_reload(request.reason)
            url, sabr_config = reload_config_fn(request.reload_playback_token)
            return ReloadConfigResponse(
                video_id=sabr_config.get('video_id'),
                video_playback_ustreamer_config=sabr_config.get('video_playback_ustreamer_config'),
                server_abr_streaming_url=url,
                po_token=sabr_config.get('po_token'),
                client_info=self._client_info_from_json(sabr_config.get('client_info')),
                pot_callback=self._create_pot_callback(sabr_config.get('fetch_po_token_fn')),
                heartbeat_callback=self._create_heartbeat_callback(sabr_config.get('extract_heartbeat_fn')),
                reload_callback=self._create_reload_callback(sabr_config.get('reload_config_fn')),
            )
        return callback

    def _create_pot_callback(self, fetch_po_token_fn) -> PotCallback | None:
        if not fetch_po_token_fn:
            return None

        def callback(status: PoTokenStatus):
            if not fetch_po_token_fn:
                self._report_pot_callback_unavailable()
                return None
            return fetch_po_token_fn(
                bypass_cache=status in (PoTokenStatus.INVALID, PoTokenStatus.PENDING),
                required=True)
        return callback

    def _report_pot_callback_unavailable(self):
        self.report_warning(
            '[download] Unable to retrieve a new PO Token: no PO Token callback available. '
            'This can occur if --load-info-json is used. '
            'The download will likely fail if a valid PO token is required. ', only_once=True)

    def _report_reload_callback_unavailable(self):
        self.report_warning(
            '[download] Unable to refresh download url: no reload callback available. '
            'This can occur if --load-info-json is used. The download may fail.', only_once=True)

    def _report_reload(self, reason):
        msg = '[download] Refreshing download url'
        if reason == ReloadConfigReason.SABR_URL_EXPIRY:
            msg += ' as it expires soon'
        elif reason == ReloadConfigReason.SABR_RELOAD_PLAYER_RESPONSE:
            msg += ' as requested by the server'
        self.to_screen(msg)

    @contextlib.contextmanager
    def break_multiline(self):
        # TODO: do we have a core solution to this?
        # TODO: apply this to every log message that could occur during the multi-line print.
        # Temporary suppress the multiline status while printing other messages,
        # to avoid messing up the display or losing the message
        lines = self._multiline.maximum + 1
        self._finish_multiline_status()
        try:
            yield
        finally:
            self._prepare_multiline_status(lines)


def format_type(f):
    if f.get('acodec') == 'none':
        return 'video'
    elif f.get('vcodec') == 'none':
        return 'audio'
    elif f.get('vcodec') is None and f.get('acodec') is None:
        return 'caption'
    return None

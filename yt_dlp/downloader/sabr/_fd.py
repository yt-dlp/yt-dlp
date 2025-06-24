from __future__ import annotations
import collections
import itertools

from yt_dlp.networking.exceptions import TransportError, HTTPError
from yt_dlp.utils import traverse_obj, int_or_none, DownloadError, join_nonempty
from yt_dlp.downloader import FileDownloader

from ._writer import SabrFDFormatWriter
from ._logger import create_sabrfd_logger

from yt_dlp.extractor.youtube._streaming.sabr.part import (
    MediaSegmentEndSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentInitSabrPart,
    PoTokenStatusSabrPart,
    RefreshPlayerResponseSabrPart,
    MediaSeekSabrPart,
    FormatInitializedSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.extractor.youtube._streaming.sabr.models import ConsumedRange, AudioSelector, VideoSelector, CaptionSelector
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrStreamError
from yt_dlp.extractor.youtube._proto.innertube import ClientInfo, ClientName
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId


class SabrFD(FileDownloader):

    @classmethod
    def can_download(cls, info_dict):
        return (
            info_dict.get('requested_formats')
            and all(
                format_info.get('protocol') == 'sabr'
                for format_info in info_dict['requested_formats']))

    def _group_formats_by_client(self, filename, info_dict):
        format_groups = collections.defaultdict(dict, {})
        requested_formats = info_dict.get('requested_formats') or [info_dict]

        for _idx, f in enumerate(requested_formats):
            sabr_config = f.get('_sabr_config')
            client_name = sabr_config.get('client_name')
            client_info = sabr_config.get('client_info')
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
                    'live_status': sabr_config.get('live_status'),
                    'video_id': sabr_config.get('video_id'),
                    'client_info': ClientInfo(
                        client_name=traverse_obj(client_info, ('clientName', {lambda x: ClientName[x]})),
                        client_version=traverse_obj(client_info, 'clientVersion'),
                        os_version=traverse_obj(client_info, 'osVersion'),
                        os_name=traverse_obj(client_info, 'osName'),
                        device_model=traverse_obj(client_info, 'deviceModel'),
                        device_make=traverse_obj(client_info, 'deviceMake'),
                    ),
                    'target_duration_sec': sabr_config.get('target_duration_sec'),
                    # Number.MAX_SAFE_INTEGER
                    'start_time_ms': ((2**53) - 1) if info_dict.get('live_status') == 'is_live' and not f.get('is_from_start') else 0,
                }

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
                self._download_sabr_stream(
                    info_dict=info_dict,
                    video_format=video_format,
                    audio_format=audio_format,
                    caption_format=caption_format,
                    resume=resume,
                    is_test=is_test,
                    server_abr_streaming_url=format_group['server_abr_streaming_url'],
                    video_playback_ustreamer_config=format_group['video_playback_ustreamer_config'],
                    initial_po_token=format_group['initial_po_token'],
                    fetch_po_token_fn=format_group['fetch_po_token_fn'],
                    reload_config_fn=format_group['reload_config_fn'],
                    client_info=format_group['client_info'],
                    start_time_ms=format_group['start_time_ms'],
                    target_duration_sec=format_group.get('target_duration_sec', None),
                    live_status=format_group.get('live_status'),
                    video_id=format_group.get('video_id'),
                )
        return True

    def _download_sabr_stream(
        self,
        video_id: str,
        info_dict: dict,
        video_format: dict,
        audio_format: dict,
        caption_format: dict,
        resume: bool,
        is_test: bool,
        server_abr_streaming_url: str,
        video_playback_ustreamer_config: str,
        initial_po_token: str,
        fetch_po_token_fn: callable | None = None,
        reload_config_fn: callable | None = None,
        client_info: ClientInfo | None = None,
        start_time_ms: int = 0,
        target_duration_sec: int | None = None,
        live_status: str | None = None,
    ):

        writers = {}
        audio_selector = None
        video_selector = None
        caption_selector = None

        if audio_format:
            audio_selector = AudioSelector(
                display_name=audio_format['display_name'], format_ids=[audio_format['format_id']])
            writers[audio_selector.display_name] = SabrFDFormatWriter(
                self, audio_format.get('filename'),
                audio_format['info_dict'], len(writers), resume=resume)

        if video_format:
            video_selector = VideoSelector(
                display_name=video_format['display_name'], format_ids=[video_format['format_id']])
            writers[video_selector.display_name] = SabrFDFormatWriter(
                self, video_format.get('filename'),
                video_format['info_dict'], len(writers), resume=resume)

        if caption_format:
            caption_selector = CaptionSelector(
                display_name=caption_format['display_name'], format_ids=[caption_format['format_id']])
            writers[caption_selector.display_name] = SabrFDFormatWriter(
                self, caption_format.get('filename'),
                caption_format['info_dict'], len(writers), resume=resume)

        # Report the destination files before we start downloading instead of when we initialize the writers,
        # as the formats may not all start at the same time (leading to messy output)
        for writer in writers.values():
            self.report_destination(writer.filename)

        stream = SabrStream(
            urlopen=self.ydl.urlopen,
            logger=create_sabrfd_logger(self.ydl, prefix='sabr:stream'),
            server_abr_streaming_url=server_abr_streaming_url,
            video_playback_ustreamer_config=video_playback_ustreamer_config,
            po_token=initial_po_token,
            video_selection=video_selector,
            audio_selection=audio_selector,
            caption_selection=caption_selector,
            start_time_ms=start_time_ms,
            client_info=client_info,
            live_segment_target_duration_sec=target_duration_sec,
            post_live=live_status == 'post_live',
            video_id=video_id,
            retry_sleep_func=self.params.get('retry_sleep_functions', {}).get('http'),
        )

        self._prepare_multiline_status(len(writers) + 1)

        try:
            total_bytes = 0
            for part in stream:
                if is_test and total_bytes >= self._TEST_FILE_SIZE:
                    stream.close()
                    break
                if isinstance(part, PoTokenStatusSabrPart):
                    if not fetch_po_token_fn:
                        self.report_warning(
                            'No fetch PO token function found - this can happen if you use --load-info-json.'
                            ' The download will fail if a valid PO token is required.', only_once=True)
                    if part.status in (
                        part.PoTokenStatus.INVALID,
                        part.PoTokenStatus.PENDING,
                    ):
                        # Fetch a PO token with bypass_cache=True
                        # (ensure we create a new one)
                        po_token = fetch_po_token_fn(bypass_cache=True)
                        if po_token:
                            stream.processor.po_token = po_token
                    elif part.status in (
                        part.PoTokenStatus.MISSING,
                        part.PoTokenStatus.PENDING_MISSING,
                    ):
                        # Fetch a PO Token, bypass_cache=False
                        po_token = fetch_po_token_fn()
                        if po_token:
                            stream.processor.po_token = po_token

                elif isinstance(part, FormatInitializedSabrPart):
                    writer = writers.get(part.format_selector.display_name)
                    if not writer:
                        self.report_warning(f'Unknown format selector: {part.format_selector}')
                        continue

                    writer.initialize_format(part.format_id)
                    initialized_format = stream.processor.initialized_formats[str(part.format_id)]
                    if writer.state.init_sequence:
                        initialized_format.init_segment = True
                        initialized_format.current_segment = None  # allow a seek

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
                        initialized_format.current_segment = None  # allow a seek
                        self.to_screen(f'[download] Resuming download for format {part.format_selector.display_name}')

                elif isinstance(part, MediaSegmentInitSabrPart):
                    writer = writers.get(part.format_selector.display_name)
                    if not writer:
                        self.report_warning(f'Unknown init format selector: {part.format_selector}')
                        continue
                    writer.initialize_segment(part)

                elif isinstance(part, MediaSegmentDataSabrPart):
                    total_bytes += len(part.data)  # TODO: not reliable
                    writer = writers.get(part.format_selector.display_name)
                    if not writer:
                        self.report_warning(f'Unknown data format selector: {part.format_selector}')
                        continue
                    writer.write_segment_data(part)

                elif isinstance(part, MediaSegmentEndSabrPart):
                    writer = writers.get(part.format_selector.display_name)
                    if not writer:
                        self.report_warning(f'Unknown end format selector: {part.format_selector}')
                        continue
                    writer.end_segment(part)

                elif isinstance(part, RefreshPlayerResponseSabrPart):
                    self.to_screen(f'Refreshing player response; Reason: {part.reason}')
                    # In-place refresh - not ideal but should work in most cases
                    # TODO: handle case where live stream changes to non-livestream on refresh?
                    # TODO: if live, allow a seek as for non-DVR streams the reload may be longer than the buffer duration
                    # TODO: handle po token function change
                    if not reload_config_fn:
                        raise self.report_warning(
                            'No reload config function found - cannot refresh SABR streaming URL.'
                            ' The url will expire soon and the download will fail.')
                    try:
                        stream.url, stream.processor.video_playback_ustreamer_config = reload_config_fn(part.reload_playback_token)
                    except (TransportError, HTTPError) as e:
                        self.report_warning(f'Failed to refresh SABR streaming URL: {e}')

                elif isinstance(part, MediaSeekSabrPart):
                    if (
                        not info_dict.get('is_live')
                        and live_status not in ('post_live', 'is_live')
                        and not stream.processor.is_live
                        and part.reason == MediaSeekSabrPart.Reason.SERVER_SEEK
                    ):
                        raise DownloadError('Server tried to seek a video')
                else:
                    self.to_screen(f'Unhandled part type: {part.__class__.__name__}')

            for writer in writers.values():
                writer.finish()
        except SabrStreamError as e:
            raise DownloadError(str(e)) from e
        except KeyboardInterrupt:
            if (
                not info_dict.get('is_live')
                and not live_status == 'is_live'
                and not stream.processor.is_live
            ):
                raise
            self.to_screen('Interrupted by user')
            for writer in writers.values():
                writer.finish()
        finally:
            # TODO: for livestreams, since we cannot resume them, should we finish the writers?
            for writer in writers.values():
                writer.close()


def format_type(f):
    if f.get('acodec') == 'none':
        return 'video'
    elif f.get('vcodec') == 'none':
        return 'audio'
    elif f.get('vcodec') is None and f.get('acodec') is None:
        return 'caption'
    return None

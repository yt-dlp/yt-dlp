import dataclasses
import io

import pytest

from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrStreamError, MediaSegmentMismatchError
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    PoTokenStatusSabrPart,
    FormatInitializedSabrPart,
    MediaSeekSabrPart,
    MediaSegmentInitSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
)

from yt_dlp.extractor.youtube._streaming.sabr.processor import (
    SabrProcessor,
    ProcessStreamProtectionStatusResult,
    ProcessFormatInitializationMetadataResult,
    ProcessLiveMetadataResult,
    ProcessSabrSeekResult,
    ProcessMediaHeaderResult,
    ProcessMediaResult,
    ProcessMediaEndResult,
)
from yt_dlp.extractor.youtube._streaming.sabr.models import (
    AudioSelector,
    VideoSelector,
    CaptionSelector,
    InitializedFormat,
    Segment,
    ConsumedRange,
)
from yt_dlp.extractor.youtube._proto.videostreaming import (
    FormatId,
    StreamProtectionStatus,
    FormatInitializationMetadata,
    LiveMetadata,
    SabrContextUpdate,
    SabrContextSendingPolicy,
    SabrSeek,
    MediaHeader,
    TimeRange,
)
from yt_dlp.extractor.youtube._proto.innertube import NextRequestPolicy, CompressionAlgorithm


@pytest.fixture
def base_args(logger, client_info):
    return {
        'logger': logger,
        'client_info': client_info,
        'video_playback_ustreamer_config': 'dGVzdA==',
    }


example_video_id = 'example_video_id'


def make_selector(selector_type, *, discard_media=False, format_ids=None):
    if selector_type == 'audio':
        return AudioSelector(
            display_name='audio',
            format_ids=format_ids if format_ids is not None else [FormatId(itag=140)],
            discard_media=discard_media,
        )
    elif selector_type == 'video':
        return VideoSelector(
            display_name='video',
            format_ids=format_ids if format_ids is not None else [FormatId(itag=248)],
            discard_media=discard_media,
        )
    elif selector_type == 'caption':
        return CaptionSelector(
            display_name='caption',
            format_ids=format_ids if format_ids is not None else [FormatId(itag=386)],
            discard_media=discard_media,
        )
    raise ValueError(f'Unknown selector_type: {selector_type}')


def selector_factory(selector_type, *, discard_media=False, format_ids=None):
    def factory():
        return make_selector(selector_type, discard_media=discard_media, format_ids=format_ids)
    return factory


def make_format_im(selector=None, video_id=None):
    return FormatInitializationMetadata(
        video_id=video_id or example_video_id,
        format_id=selector.format_ids[0] if selector else FormatId(itag=140),
        end_time_ms=10000,
        total_segments=5,
        mime_type=(selector.mime_prefix + '/mp4') if selector else 'audio/mp4',
        duration_ticks=10000,
        duration_timescale=1000,
    )


def make_init_header(selector=None, video_id=None):
    return MediaHeader(
        video_id=video_id or example_video_id,
        format_id=selector.format_ids[0] if selector else FormatId(itag=140),
        header_id=0,
        is_init_segment=True,
        start_data_range=0,
        content_length=501,
    )


def make_media_header(selector=None, video_id=None, sequence_no=None, header_id=0):
    return MediaHeader(
        video_id=video_id or example_video_id,
        format_id=selector.format_ids[0] if selector else FormatId(itag=140),
        header_id=header_id,
        start_data_range=502,
        content_length=10000,
        sequence_number=sequence_no,
        is_init_segment=False,
        duration_ms=2300,
        start_ms=0,
    )


class TestSabrProcessorInitialization:
    @pytest.mark.parametrize(
        'audio_sel,video_sel,caption_sel,expected_bitfield',
        [
            # audio+video
            (selector_factory('audio'), selector_factory('video'), None, 0),
            # audio+video+caption(discard)
            (
                selector_factory('audio'),
                selector_factory('video'),
                selector_factory('caption', discard_media=True),
                0,
            ),
            # audio only
            (selector_factory('audio'), None, None, 1),
            # audio only (video+caption manual discard)
            (
                selector_factory('audio'),
                selector_factory('video', discard_media=True),
                selector_factory('caption', discard_media=True),
                1,
            ),
            # audio+video+caption
            (
                selector_factory('audio'),
                selector_factory('video'),
                selector_factory('caption'),
                7,
            ),
            # video only
            (None, selector_factory('video'), None, 0),
            # video only (audio+caption manual discard)
            (
                selector_factory('audio', discard_media=True),
                selector_factory('video'),
                selector_factory('caption', discard_media=True),
                0,
            ),
            # caption only
            (None, None, selector_factory('caption'), 7),
            # caption only (audio+video manual discard)
            (
                selector_factory('audio', discard_media=True),
                selector_factory('video', discard_media=True),
                selector_factory('caption'),
                7,
            ),
        ],
    )
    def test_client_abr_state_bitfield(
        self, base_args, audio_sel, video_sel, caption_sel, expected_bitfield,
    ):
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_sel() if audio_sel else None,
            video_selection=video_sel() if video_sel else None,
            caption_selection=caption_sel() if caption_sel else None,
        )
        assert processor.client_abr_state.enabled_track_types_bitfield == expected_bitfield

    @pytest.mark.parametrize(
        'audio_sel,video_sel,caption_sel,expected_audio_ids,expected_video_ids,expected_caption_ids',
        [
            # audio+video
            (
                selector_factory('audio'), selector_factory('video'), None,
                [FormatId(itag=140)], [FormatId(itag=248)], [],
            ),
            # audio only
            (
                selector_factory('audio'), None, None,
                [FormatId(itag=140)], [], [],
            ),
            # video only
            (
                None, selector_factory('video'), None,
                [], [FormatId(itag=248)], [],
            ),
            # caption only
            (
                None, None, selector_factory('caption'),
                [], [], [FormatId(itag=386)],
            ),
            # audio+video+caption
            (
                selector_factory('audio'), selector_factory('video'), selector_factory('caption'),
                [FormatId(itag=140)], [FormatId(itag=248)], [FormatId(itag=386)],
            ),
            # multiple ids
            (
                selector_factory('audio', format_ids=[FormatId(itag=140), FormatId(itag=141)]),
                selector_factory('video', format_ids=[FormatId(itag=248), FormatId(itag=249)]),
                selector_factory('caption', format_ids=[FormatId(itag=386), FormatId(itag=387)]),
                [FormatId(itag=140), FormatId(itag=141)],
                [FormatId(itag=248), FormatId(itag=249)],
                [FormatId(itag=386), FormatId(itag=387)],
            ),
        ],
    )
    def test_selected_format_ids(
        self, base_args, audio_sel, video_sel, caption_sel,
        expected_audio_ids, expected_video_ids, expected_caption_ids,
    ):
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_sel() if audio_sel else None,
            video_selection=video_sel() if video_sel else None,
            caption_selection=caption_sel() if caption_sel else None,
        )
        assert processor.selected_audio_format_ids == expected_audio_ids
        assert processor.selected_video_format_ids == expected_video_ids
        assert processor.selected_caption_format_ids == expected_caption_ids

    @pytest.mark.parametrize(
        'start_time_ms,expected',
        [
            (None, 0),
            (0, 0),
            (12345, 12345),
        ],
    )
    def test_start_time_ms_initialization(self, base_args, start_time_ms, expected):
        processor = SabrProcessor(
            **base_args,
            start_time_ms=start_time_ms,
        )
        assert processor.start_time_ms == expected
        assert processor.client_abr_state.player_time_ms == expected

    @pytest.mark.parametrize('invalid_start_time_ms', [-1, -100])
    def test_start_time_ms_invalid(self, base_args, invalid_start_time_ms):
        with pytest.raises(ValueError, match='start_time_ms must be greater than or equal to 0'):
            SabrProcessor(
                **base_args,
                audio_selection=selector_factory('audio')(),
                video_selection=selector_factory('video')(),
                caption_selection=None,
                start_time_ms=invalid_start_time_ms,
            )

    def test_client_abr_state_defaults(self, base_args):
        processor = SabrProcessor(**base_args)
        # Must be enabled to allow DRC formats to be streamed
        assert processor.client_abr_state.drc_enabled is True

    @pytest.mark.parametrize(
        'duration_sec,tolerance_ms',
        [
            (10, 4999),
            (10, 0),
        ],
    )
    def test_live_segment_target_duration_tolerance_ms_valid(self, base_args, duration_sec, tolerance_ms):
        # Should not raise
        SabrProcessor(
            **base_args,
            live_segment_target_duration_sec=duration_sec,
            live_segment_target_duration_tolerance_ms=tolerance_ms,
        )

    @pytest.mark.parametrize(
        'duration_sec,tolerance_ms',
        [
            (10, 5000),  # exactly half
            (10, 6000),  # more than half
        ],
    )
    def test_live_segment_target_duration_tolerance_ms_validation(self, base_args, duration_sec, tolerance_ms):
        with pytest.raises(ValueError, match='live_segment_target_duration_tolerance_ms must be less than'):
            SabrProcessor(
                **base_args,
                live_segment_target_duration_sec=duration_sec,
                live_segment_target_duration_tolerance_ms=tolerance_ms,
            )

    def test_defaults(self, base_args):
        processor = SabrProcessor(**base_args)
        assert processor.live_segment_target_duration_sec == 5
        assert processor.live_segment_target_duration_tolerance_ms == 100
        assert processor.start_time_ms == 0
        assert processor.post_live is False

    def test_override_defaults(self, base_args):
        processor = SabrProcessor(
            **base_args,
            live_segment_target_duration_sec=8,
            live_segment_target_duration_tolerance_ms=42,
            start_time_ms=123,
            post_live=True,
        )
        assert processor.live_segment_target_duration_sec == 8
        assert processor.live_segment_target_duration_tolerance_ms == 42
        assert processor.start_time_ms == 123
        assert processor.post_live is True


class TestStreamProtectionStatus:

    @pytest.mark.parametrize(
        'sps,po_token,expected_status',
        [
            (StreamProtectionStatus.Status.OK, None, PoTokenStatusSabrPart.PoTokenStatus.NOT_REQUIRED),
            (StreamProtectionStatus.Status.OK, 'valid_token', PoTokenStatusSabrPart.PoTokenStatus.OK),
            (StreamProtectionStatus.Status.ATTESTATION_PENDING, None, PoTokenStatusSabrPart.PoTokenStatus.PENDING_MISSING),
            (StreamProtectionStatus.Status.ATTESTATION_PENDING, 'valid_token', PoTokenStatusSabrPart.PoTokenStatus.PENDING),
            (StreamProtectionStatus.Status.ATTESTATION_REQUIRED, None, PoTokenStatusSabrPart.PoTokenStatus.MISSING),
            (StreamProtectionStatus.Status.ATTESTATION_REQUIRED, 'valid_token', PoTokenStatusSabrPart.PoTokenStatus.INVALID),
        ],
    )
    def test_stream_protection_status_part(self, base_args, sps, po_token, expected_status):
        processor = SabrProcessor(**base_args, po_token=po_token)
        part = StreamProtectionStatus(status=sps)

        result = processor.process_stream_protection_status(part)
        assert isinstance(result, ProcessStreamProtectionStatusResult)
        assert isinstance(result.sabr_part, PoTokenStatusSabrPart)
        assert result.sabr_part.status == expected_status
        assert processor.stream_protection_status == sps

    def test_no_stream_protection_status(self, logger, base_args):
        processor = SabrProcessor(**base_args, po_token='valid_token')
        part = StreamProtectionStatus(status=None)

        result = processor.process_stream_protection_status(part)
        assert isinstance(result, ProcessStreamProtectionStatusResult)
        assert result.sabr_part is None
        assert processor.stream_protection_status is None
        assert logger.warning.call_count == 1
        logger.warning.assert_called_with(
            'Received an unknown StreamProtectionStatus: StreamProtectionStatus(status=None, max_retries=None)',
        )


class TestNextRequestPolicyPart:
    def test_next_request_policy_part(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        next_request_policy = NextRequestPolicy(target_audio_readahead_ms=123)

        result = processor.process_next_request_policy(next_request_policy)
        assert result is None
        assert processor.next_request_policy is next_request_policy

        # Verify it is overridden in the processor on another call
        next_request_policy = NextRequestPolicy(target_video_readahead_ms=456)
        result = processor.process_next_request_policy(next_request_policy)
        assert result is None
        assert processor.next_request_policy is next_request_policy

        # Check logger trace was called
        assert logger.trace.call_count == 2


class TestFormatInitialization:

    def test_initialize_format(self, logger, base_args):
        selector = make_selector('audio')
        format_id = selector.format_ids[0]
        processor = SabrProcessor(**base_args, audio_selection=selector, video_id='test_video')
        format_init_metadata_part = FormatInitializationMetadata(
            video_id='test_video',
            format_id=format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        result = processor.process_format_initialization_metadata(format_init_metadata_part)

        assert isinstance(result, ProcessFormatInitializationMetadataResult)
        assert isinstance(result.sabr_part, FormatInitializedSabrPart)
        assert result.sabr_part.format_selector is selector
        assert result.sabr_part.format_id == format_id
        assert len(processor.initialized_formats) == 1
        assert str(format_id) in processor.initialized_formats
        initialized_format = processor.initialized_formats[str(format_id)]
        expected_initialized_format = InitializedFormat(
            format_id=format_id,
            video_id='test_video',
            mime_type='audio/mp4',
            duration_ms=10000,
            total_segments=5,
            end_time_ms=10000,
            format_selector=selector,
            discard=False,
        )
        assert initialized_format == expected_initialized_format
        logger.debug.assert_called_with(
            f'Initialized Format: {expected_initialized_format}',
        )

    def test_initialize_format_already_initialized(self, logger, base_args):
        selector = make_selector('audio')
        format_id = selector.format_ids[0]
        processor = SabrProcessor(**base_args, audio_selection=selector, video_id='test_video')
        format_init_metadata_part = FormatInitializationMetadata(
            video_id='test_video',
            format_id=format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        assert processor.process_format_initialization_metadata(format_init_metadata_part)

        # Now try to initialize it again
        result = processor.process_format_initialization_metadata(
            dataclasses.replace(format_init_metadata_part, total_segments=10))

        assert isinstance(result, ProcessFormatInitializationMetadataResult)
        assert result.sabr_part is None
        logger.trace.assert_called_with(f'Format {format_id} already initialized')
        assert len(processor.initialized_formats) == 1
        assert str(format_id) in processor.initialized_formats
        initialized_format = processor.initialized_formats[str(format_id)]
        assert initialized_format.total_segments == 5

    def test_initialize_multiple_formats(self, logger, base_args):
        audio_selector = make_selector('audio')
        video_selector = make_selector('video')

        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]

        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_selector,
            video_selection=video_selector,
            video_id=example_video_id,
        )

        audio_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        video_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            end_time_ms=10000,
            total_segments=20,
            mime_type='video/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        # Process audio format initialization
        audio_result = processor.process_format_initialization_metadata(audio_format_init_metadata)
        assert audio_result.sabr_part.format_selector is audio_selector
        assert audio_result.sabr_part.format_id == audio_format_id
        assert len(processor.initialized_formats) == 1
        assert str(audio_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(audio_format_id)].format_id == audio_format_id

        # Process video format initialization
        video_result = processor.process_format_initialization_metadata(video_format_init_metadata)
        assert video_result.sabr_part.format_selector is video_selector
        assert video_result.sabr_part.format_id == video_format_id
        assert len(processor.initialized_formats) == 2
        assert str(video_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(video_format_id)].format_id == video_format_id

    def test_initialized_format_not_match_selector(self, logger, base_args):
        selector = make_selector('audio', format_ids=[FormatId(140)])
        processor = SabrProcessor(
            **base_args,
            video_id=example_video_id,
            audio_selection=selector)

        format_id = FormatId(itag=141)  # Different format id than the selector
        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        with pytest.raises(SabrStreamError, match='does not match any format selector'):
            processor.process_format_initialization_metadata(format_init_metadata_part)

        assert len(processor.initialized_formats) == 0

    def test_initialized_format_match_mimetype(self, logger, base_args):
        selector = make_selector('audio', format_ids=[])
        assert len(selector.format_ids) == 0
        processor = SabrProcessor(
            **base_args,
            video_id=example_video_id,
            audio_selection=selector,
            video_selection=make_selector('caption'),
        )

        format_id = FormatId(itag=251)
        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        result = processor.process_format_initialization_metadata(format_init_metadata_part)
        assert isinstance(result, ProcessFormatInitializationMetadataResult)
        assert isinstance(result.sabr_part, FormatInitializedSabrPart)
        assert result.sabr_part.format_selector is selector
        assert result.sabr_part.format_id == format_id
        assert len(processor.initialized_formats) == 1

        # If mimetype does not match any selector, it should raise an error
        bad_fmt_init_metadata = dataclasses.replace(
            format_init_metadata_part, mime_type='video/mp4', format_id=FormatId(itag=248))
        with pytest.raises(SabrStreamError, match='does not match any format selector'):
            processor.process_format_initialization_metadata(bad_fmt_init_metadata)

        assert len(processor.initialized_formats) == 1

    def test_discard_media(self, logger, base_args):
        # Discard and only match by format id
        audio_selector = make_selector('audio', discard_media=True)
        audio_format_id = audio_selector.format_ids[0]

        # Discard any video
        video_selector = make_selector('video', format_ids=[], discard_media=True)
        assert len(video_selector.format_ids) == 0
        video_format_id = FormatId(itag=248)

        # xxx: Caption selector not specified, should be discarded by default
        processor = SabrProcessor(
            **base_args,
            video_id=example_video_id,
            audio_selection=audio_selector,
            video_selection=video_selector,
        )

        audio_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        # Process audio format initialization
        audio_result = processor.process_format_initialization_metadata(audio_format_init_metadata)
        # When discarding, should not return a sabr_part
        assert isinstance(audio_result, ProcessFormatInitializationMetadataResult)
        assert audio_result.sabr_part is None
        assert len(processor.initialized_formats) == 1
        assert str(audio_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(audio_format_id)].format_id == audio_format_id
        assert processor.initialized_formats[str(audio_format_id)].discard is True

        # The format should be marked as completely buffered
        assert len(processor.initialized_formats[str(audio_format_id)].consumed_ranges) == 1
        consumed_range = processor.initialized_formats[str(audio_format_id)].consumed_ranges[0]
        assert consumed_range.start_sequence_number == 0
        assert consumed_range.end_sequence_number >= 5
        assert consumed_range.start_time_ms == 0
        assert consumed_range.duration_ms >= 10000

        # Process video format initialization. This should match the selector but be discarded.
        video_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            end_time_ms=10000,
            total_segments=20,
            mime_type='video/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        video_result = processor.process_format_initialization_metadata(video_format_init_metadata)
        assert video_result.sabr_part is None
        assert len(processor.initialized_formats) == 2
        assert str(video_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(video_format_id)].format_id == video_format_id
        assert processor.initialized_formats[str(video_format_id)].discard is True

        # The format should be marked as completely buffered
        assert len(processor.initialized_formats[str(video_format_id)].consumed_ranges) == 1
        consumed_range = processor.initialized_formats[str(video_format_id)].consumed_ranges[0]
        assert consumed_range.start_sequence_number == 0
        assert consumed_range.end_sequence_number >= 20
        assert consumed_range.start_time_ms == 0
        assert consumed_range.duration_ms >= 10000

        # Process a caption format initialization. This should be discarded by default as no selector was specified.
        caption_format_id = FormatId(itag=386)
        # Simulate no duration data (for livestreams with no live_metadata)
        caption_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=caption_format_id,
            mime_type='text/mp4',
        )

        caption_result = processor.process_format_initialization_metadata(caption_format_init_metadata)
        assert caption_result.sabr_part is None
        assert len(processor.initialized_formats) == 3
        assert str(caption_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(caption_format_id)].format_id == caption_format_id
        assert processor.initialized_formats[str(caption_format_id)].discard is True

        # The format should be marked as completely buffered
        assert len(processor.initialized_formats[str(caption_format_id)].consumed_ranges) == 1
        consumed_range = processor.initialized_formats[str(caption_format_id)].consumed_ranges[0]
        assert consumed_range.start_sequence_number == 0
        assert consumed_range.end_sequence_number >= 99999999
        assert consumed_range.start_time_ms == 0
        assert consumed_range.duration_ms >= 99999999

    def test_total_duration_ms(self, logger, base_args):
        # Test the duration_ms calculation when end_time_ms and duration_ms are different
        audio_selector = make_selector('audio')
        video_selector = make_selector('video')
        caption_selector = make_selector('caption')
        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]
        caption_format_id = caption_selector.format_ids[0]
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_selector,
            video_selection=video_selector,
            caption_selection=caption_selector,
            video_id=example_video_id,
        )

        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            end_time_ms=15001,  # End time is slightly more than 15 seconds
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=15000,
            duration_timescale=1000,
        )

        assert processor.total_duration_ms is None
        processor.process_format_initialization_metadata(format_init_metadata_part)
        assert str(audio_format_id) in processor.initialized_formats
        assert processor.total_duration_ms == 15001

        # But if duration_ticks is greater, then use that
        video_format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            end_time_ms=15003,  # end time is slightly less
            total_segments=10,
            mime_type='video/mp4',
            duration_ticks=150050,  # Duration ticks is greater than end_time_ms
            duration_timescale=10000,  # slightly different timescale
        )

        processor.process_format_initialization_metadata(video_format_init_metadata_part)
        assert str(video_format_id) in processor.initialized_formats
        assert processor.total_duration_ms == 15005

        # And if total_duration_ms is greater, use that
        caption_format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=caption_format_id,
            end_time_ms=15004,
            total_segments=20,
            mime_type='text/mp4',
            duration_ticks=15004,
            duration_timescale=1000,
        )

        processor.process_format_initialization_metadata(caption_format_init_metadata_part)
        assert str(caption_format_id) in processor.initialized_formats
        assert processor.total_duration_ms == 15005  # should not change

    def test_no_duration(self, logger, base_args):
        # Test the case where no duration is provided
        selector = make_selector('audio')
        format_id = selector.format_ids[0]
        processor = SabrProcessor(**base_args, audio_selection=selector, video_id=example_video_id)

        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=format_id,
            end_time_ms=None,  # No end time
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=None,
            duration_timescale=None,
        )

        assert processor.total_duration_ms is None
        processor.process_format_initialization_metadata(format_init_metadata_part)
        assert str(format_id) in processor.initialized_formats
        assert processor.total_duration_ms == 0  # TODO: should this be None or 0?

    def test_no_duration_total_duration_ms_set(self, logger, base_args):
        # Test the case where no duration is provided but total_duration_ms is set (by e.g. live_metadata)
        selector = make_selector('audio')
        format_id = selector.format_ids[0]
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            video_id=example_video_id,
        )

        processor.total_duration_ms = 10000

        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=format_id,
            end_time_ms=None,  # No end time
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=None,
            duration_timescale=None,
        )

        processor.process_format_initialization_metadata(format_init_metadata_part)
        assert str(format_id) in processor.initialized_formats
        assert processor.total_duration_ms == 10000

    def test_video_id_mismatch(self, logger, base_args):
        selector = make_selector('audio')
        format_id = selector.format_ids[0]
        processor = SabrProcessor(**base_args, audio_selection=selector, video_id='video_1')

        format_init_metadata_part = FormatInitializationMetadata(
            video_id='video_2',
            format_id=format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        with pytest.raises(SabrStreamError, match='Received unexpected Format Initialization Metadata for video video_2'):
            processor.process_format_initialization_metadata(format_init_metadata_part)

        assert len(processor.initialized_formats) == 0

    def test_selector_consumed(self, logger, base_args):
        # Test that if a format selector is already in use, it raises an error
        selector = make_selector('audio', format_ids=[])
        audio_format_id = FormatId(itag=140)
        processor = SabrProcessor(**base_args, audio_selection=selector, video_id=example_video_id)

        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            end_time_ms=10000,
            total_segments=5,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        processor.process_format_initialization_metadata(format_init_metadata_part)
        assert str(audio_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(audio_format_id)].format_selector is selector

        with pytest.raises(SabrStreamError, match='Changing formats is not currently supported'):
            processor.process_format_initialization_metadata(
                dataclasses.replace(format_init_metadata_part, format_id=FormatId(itag=141)))

    def test_no_segment_count(self, logger, base_args):
        selector = make_selector('audio')
        format_id = selector.format_ids[0]
        processor = SabrProcessor(**base_args, audio_selection=selector, video_id=example_video_id)

        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=format_id,
            end_time_ms=10000,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        processor.process_format_initialization_metadata(format_init_metadata_part)
        assert str(format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(format_id)].total_segments is None

    def test_total_segment_count_live_metadata(self, logger, base_args):
        # Test that total_segments is set from live_metadata when not in the format
        audio_selector = make_selector('audio')
        video_selector = make_selector('video')
        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]
        processor = SabrProcessor(
            **base_args, audio_selection=audio_selector, video_selection=video_selector,
            video_id=example_video_id)

        format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            end_time_ms=10000,
            mime_type='audio/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        processor.live_metadata = LiveMetadata(head_sequence_number=10)
        processor.process_format_initialization_metadata(format_init_metadata_part)
        assert str(audio_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(audio_format_id)].total_segments == 10

        # But live metadata should not override total_segments if it is present
        # XXX: when live metadata is updated, it will update the total_segments.
        # However, we can consider the total_segments
        # from the format initialization metadata as the most-up-to-date value until then.

        video_format_init_metadata_part = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            end_time_ms=10000,
            # This should take precedence over live_metadata.
            # Generally, this should only ever be greater than the live_metadata value.
            # Never seen this be present for livestreams at this time.
            # TODO: add a guard to ensure total segments is > live_metadata.head_sequence_number?
            total_segments=9,
            mime_type='video/mp4',
            duration_ticks=10000,
            duration_timescale=1000,
        )

        processor.process_format_initialization_metadata(video_format_init_metadata_part)
        assert str(video_format_id) in processor.initialized_formats
        assert processor.initialized_formats[str(video_format_id)].total_segments == 9


class TestLiveMetadata:

    def test_live_metadata_initialization(self, base_args):
        processor = SabrProcessor(**base_args)
        assert processor.live_metadata is None

    def test_live_metadata_update(self, base_args):
        processor = SabrProcessor(**base_args)
        live_metadata = LiveMetadata(head_sequence_number=10)

        result = processor.process_live_metadata(live_metadata)
        assert isinstance(result, ProcessLiveMetadataResult)
        assert len(result.seek_sabr_parts) == 0
        assert processor.live_metadata is live_metadata

        # Ensure new live_metadata replaces the old one
        live_metadata = dataclasses.replace(live_metadata, head_sequence_number=20)
        result = processor.process_live_metadata(live_metadata)

        assert isinstance(result, ProcessLiveMetadataResult)
        assert len(result.seek_sabr_parts) == 0
        assert processor.live_metadata is live_metadata

    def test_live_metadata_no_head_sequence_time_ms(self, base_args):
        processor = SabrProcessor(**base_args)
        live_metadata = LiveMetadata(head_sequence_number=10, head_sequence_time_ms=None)

        processor.process_live_metadata(live_metadata)
        assert processor.live_metadata is live_metadata
        assert processor.total_duration_ms is None

    def test_live_metadata_with_head_sequence_time_ms(self, base_args):
        processor = SabrProcessor(**base_args)
        live_metadata = LiveMetadata(head_sequence_number=10, head_sequence_time_ms=5000)

        processor.process_live_metadata(live_metadata)
        assert processor.live_metadata is live_metadata
        assert processor.total_duration_ms == 5000

    def test_update_izf_total_segments(self, base_args):

        live_metadata = LiveMetadata(head_sequence_number=10)
        audio_selector = make_selector('audio')
        video_selector = make_selector('video')
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_selector,
            video_selection=video_selector,
            video_id=example_video_id)

        # Initialize both audio and video formats
        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]

        audio_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            mime_type='audio/mp4',
        )

        video_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            mime_type='video/mp4',
        )

        processor.process_format_initialization_metadata(audio_format_init_metadata)
        processor.process_format_initialization_metadata(video_format_init_metadata)
        assert len(processor.initialized_formats) == 2

        # Process live metadata
        processor.process_live_metadata(live_metadata)
        assert processor.live_metadata is live_metadata

        # Check that total_segments is updated in both formats
        assert processor.initialized_formats[str(audio_format_id)].total_segments == 10
        assert processor.initialized_formats[str(video_format_id)].total_segments == 10

    def test_min_seekable_time_ms_less_than_player_time_ms(self, base_args):
        # If min_seekable_time_ms is greater or equal to player time, there should not be a seek
        live_metadata = LiveMetadata(
            head_sequence_number=10,
            head_sequence_time_ms=10000,
            min_seekable_time_ticks=50000,
            min_seekable_timescale=10000)

        audio_selector = make_selector('audio')
        video_selector = make_selector('video')
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_selector,
            video_selection=video_selector,
            video_id=example_video_id,
            start_time_ms=5001)

        assert processor.client_abr_state.player_time_ms == 5001

        # Initialize both audio and video formats
        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]

        audio_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            mime_type='audio/mp4',
        )

        video_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            mime_type='video/mp4',
        )

        processor.process_format_initialization_metadata(audio_format_init_metadata)
        processor.process_format_initialization_metadata(video_format_init_metadata)
        assert len(processor.initialized_formats) == 2

        # Process live metadata
        result = processor.process_live_metadata(live_metadata)
        assert isinstance(result, ProcessLiveMetadataResult)
        assert len(result.seek_sabr_parts) == 0
        assert processor.live_metadata is live_metadata
        assert processor.client_abr_state.player_time_ms == 5001

    def test_min_seekable_time_ms_greater_than_player_time_ms(self, base_args, logger):
        # If min_seekable_time_ms is less than player time, there should be a seek
        live_metadata = LiveMetadata(
            head_sequence_number=10,
            head_sequence_time_ms=10000,
            min_seekable_time_ticks=50000,
            min_seekable_timescale=10000,
        )

        audio_selector = make_selector('audio')
        video_selector = make_selector('video')
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_selector,
            video_selection=video_selector,
            video_id=example_video_id,
            start_time_ms=4999)

        assert processor.client_abr_state.player_time_ms == 4999

        # Initialize both audio and video formats
        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]

        audio_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            mime_type='audio/mp4',
        )

        video_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            mime_type='video/mp4',
        )

        processor.process_format_initialization_metadata(audio_format_init_metadata)
        processor.process_format_initialization_metadata(video_format_init_metadata)
        assert len(processor.initialized_formats) == 2

        # Add a dummy previous segment to each format - this should be cleared on seek
        for izf in processor.initialized_formats.values():
            izf.current_segment = Segment(
                format_id=izf.format_id,
            )

        # Process live metadata
        result = processor.process_live_metadata(live_metadata)
        assert isinstance(result, ProcessLiveMetadataResult)
        assert len(result.seek_sabr_parts) == 2
        assert processor.live_metadata is live_metadata
        assert processor.client_abr_state.player_time_ms == 5000

        for seek_part in result.seek_sabr_parts:
            assert isinstance(seek_part, MediaSeekSabrPart)
            assert seek_part.format_id in (audio_format_id, video_format_id)
            assert seek_part.format_selector in (audio_selector, video_selector)

        # Current segment should be cleared to indicate a seek
        for izf in processor.initialized_formats.values():
            assert izf.current_segment is None

        logger.debug.assert_called_with('Player time 4999 is less than min seekable time 5000, simulating server seek')


class TestSabrContextUpdate:
    def test_initialization(self, base_args):
        processor = SabrProcessor(**base_args)
        assert len(processor.sabr_context_updates) == 0
        assert len(processor.sabr_contexts_to_send) == 0

    def test_invalid_sabr_context_update(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        invalid_update = SabrContextUpdate()
        processor.process_sabr_context_update(invalid_update)

        assert len(processor.sabr_context_updates) == 0
        assert len(processor.sabr_contexts_to_send) == 0
        logger.warning.assert_called_with('Received an invalid SabrContextUpdate, ignoring')

    def test_valid_sabr_context_update(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        valid_update = SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
        )
        processor.process_sabr_context_update(valid_update)

        assert len(processor.sabr_context_updates) == 1
        assert processor.sabr_context_updates[valid_update.type] == valid_update
        assert len(processor.sabr_contexts_to_send) == 1
        assert valid_update.type in processor.sabr_contexts_to_send
        logger.debug.assert_called_with(f'Registered SabrContextUpdate {valid_update}')

    def test_not_send_by_default(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        valid_update = SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "value"}',
            send_by_default=False,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
        )
        processor.process_sabr_context_update(valid_update)
        assert len(processor.sabr_context_updates) == 1
        assert processor.sabr_context_updates[valid_update.type] == valid_update
        assert len(processor.sabr_contexts_to_send) == 0

    def test_write_policy_overwrite(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        first_ctx_update = SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
        )
        processor.process_sabr_context_update(first_ctx_update)

        assert len(processor.sabr_context_updates) == 1
        assert processor.sabr_context_updates[first_ctx_update.type] == first_ctx_update
        assert len(processor.sabr_contexts_to_send) == 1
        assert first_ctx_update.type in processor.sabr_contexts_to_send

        second_ctx_update = SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "new_value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
        )

        processor.process_sabr_context_update(second_ctx_update)
        assert len(processor.sabr_context_updates) == 1
        assert processor.sabr_context_updates[second_ctx_update.type] == second_ctx_update
        assert len(processor.sabr_contexts_to_send) == 1
        assert second_ctx_update.type in processor.sabr_contexts_to_send

    def test_write_policy_keep_existing(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        first_ctx_update = SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_KEEP_EXISTING,
        )
        processor.process_sabr_context_update(first_ctx_update)

        assert len(processor.sabr_context_updates) == 1
        assert processor.sabr_context_updates[first_ctx_update.type] == first_ctx_update
        assert len(processor.sabr_contexts_to_send) == 1
        assert first_ctx_update.type in processor.sabr_contexts_to_send

        second_ctx_update = SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "new_value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_KEEP_EXISTING,
        )

        processor.process_sabr_context_update(second_ctx_update)
        assert len(processor.sabr_context_updates) == 1
        assert processor.sabr_context_updates[first_ctx_update.type] == first_ctx_update
        assert len(processor.sabr_contexts_to_send) == 1
        assert first_ctx_update.type in processor.sabr_contexts_to_send
        logger.debug.assert_called_with(
            'Received a SABR Context Update with write_policy=KEEP_EXISTING'
            'matching an existing SABR Context Update. Ignoring update')

    def test_set_sabr_context_update_sending_policy(self, base_args, logger):
        processor = SabrProcessor(**base_args)

        processor.process_sabr_context_update(SabrContextUpdate(
            type=3,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_PLAYBACK,
            value=b'{"key": "value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
        ))

        processor.process_sabr_context_update(SabrContextUpdate(
            type=4,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_REQUEST,
            value=b'{"key": "value"}',
            send_by_default=True,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_KEEP_EXISTING,
        ))

        processor.process_sabr_context_update(SabrContextUpdate(
            type=5,
            scope=SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS,
            value=b'{"key": "value"}',
            send_by_default=False,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
        ))

        assert len(processor.sabr_context_updates) == 3
        assert len(processor.sabr_contexts_to_send) == 2
        assert 3 in processor.sabr_contexts_to_send
        assert 4 in processor.sabr_contexts_to_send
        assert 5 not in processor.sabr_contexts_to_send

        # Sending policy should update what contexts are sent
        processor.process_sabr_context_sending_policy(
            SabrContextSendingPolicy(
                start_policy=[5, 6],
                stop_policy=[3, 0],
                discard_policy=[4, 7]))

        assert len(processor.sabr_context_updates) == 2
        assert len(processor.sabr_contexts_to_send) == 3
        assert 5 in processor.sabr_contexts_to_send
        assert 4 in processor.sabr_contexts_to_send  # discarding does not remove from contexts to send
        assert 6 in processor.sabr_contexts_to_send
        assert all(n not in processor.sabr_contexts_to_send for n in [3, 0, 7])
        assert 4 not in processor.sabr_context_updates


class TestSabrSeek:
    def test_invalid_sabr_seek(self, logger, base_args):
        processor = SabrProcessor(**base_args)
        invalid_seek = SabrSeek(seek_time_ticks=100, timescale=None)
        with pytest.raises(SabrStreamError, match='Server sent a SabrSeek part that is missing required seek data'):
            processor.process_sabr_seek(invalid_seek)
        assert processor.client_abr_state.player_time_ms == 0

    def test_sabr_seek(self, logger, base_args):
        audio_selector = make_selector('audio')
        video_selector = make_selector('video')
        audio_format_id = audio_selector.format_ids[0]
        video_format_id = video_selector.format_ids[0]
        processor = SabrProcessor(
            **base_args,
            audio_selection=audio_selector,
            video_selection=video_selector,
            video_id=example_video_id)

        assert processor.client_abr_state.player_time_ms == 0

        audio_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=audio_format_id,
            mime_type='audio/mp4',
        )
        video_format_init_metadata = FormatInitializationMetadata(
            video_id=example_video_id,
            format_id=video_format_id,
            mime_type='video/mp4',
        )

        processor.process_format_initialization_metadata(audio_format_init_metadata)
        processor.process_format_initialization_metadata(video_format_init_metadata)
        assert len(processor.initialized_formats) == 2

        # Add a dummy previous segment to each format - this should be cleared on seek
        for izf in processor.initialized_formats.values():
            izf.current_segment = Segment(
                format_id=izf.format_id,
            )

        sabr_seek = SabrSeek(
            seek_time_ticks=56000,
            timescale=10000,
        )

        result = processor.process_sabr_seek(sabr_seek)
        assert isinstance(result, ProcessSabrSeekResult)
        assert len(result.seek_sabr_parts) == 2
        assert processor.client_abr_state.player_time_ms == 5600
        for seek_part in result.seek_sabr_parts:
            assert isinstance(seek_part, MediaSeekSabrPart)
            assert seek_part.format_id in (audio_format_id, video_format_id)
            assert seek_part.format_selector in (audio_selector, video_selector)

        # Current segment should be cleared to indicate a seek
        for izf in processor.initialized_formats.values():
            assert izf.current_segment is None

        logger.debug.assert_called_with('Seeking to 5600ms')


class TestMediaHeader:
    def test_media_header_init_segment(self, base_args):
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_init_header(selector)

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)
        part = result.sabr_part
        # TODO: confirm expected duration/start_ms settings for init segments
        assert part == MediaSegmentInitSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            player_time_ms=0,
            sequence_number=None,
            total_segments=5,
            is_init_segment=True,
            content_length=501,
            start_time_ms=0,
            duration_ms=0,
            duration_estimated=True,  # TODO: confirm expected behavior
            start_bytes=0,
        )
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        # TODO: confirm expected duration/start_ms settings for init segments
        assert segment == Segment(
            format_id=selector.format_ids[0],
            is_init_segment=True,
            duration_ms=0,
            start_ms=0,
            start_data_range=0,
            sequence_number=None,
            content_length=501,
            content_length_estimated=False,
            initialized_format=processor.initialized_formats[str(selector.format_ids[0])],
            duration_estimated=True,
            discard=False,
            consumed=False,
            received_data_length=0,
        )

    def test_media_header_segment(self, base_args):
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)
        part = result.sabr_part
        assert part == MediaSegmentInitSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            player_time_ms=0,
            sequence_number=1,
            total_segments=5,
            is_init_segment=False,
            content_length=10000,
            start_time_ms=0,
            duration_ms=2300,
            start_bytes=502,
        )
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        assert segment == Segment(
            format_id=selector.format_ids[0],
            is_init_segment=False,
            duration_ms=2300,
            start_ms=0,
            start_data_range=502,
            sequence_number=1,
            content_length=10000,
            content_length_estimated=False,
            initialized_format=processor.initialized_formats[str(selector.format_ids[0])],
            duration_estimated=False,
            discard=False,
            consumed=False,
            received_data_length=0,
        )

    def test_media_header_replay(self, base_args):
        # Should be able to replay a media header (e.g. request was retried)
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        result = processor.process_media_header(media_header)
        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)
        segment = processor.partial_segments[media_header.header_id]
        processor.partial_segments.clear()

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)
        assert segment == processor.partial_segments[media_header.header_id]
        assert segment is not processor.partial_segments[media_header.header_id]

    def test_media_header_with_startms(self, base_args):
        # start_ms is provided instead of time_range in media header
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.start_ms = 1002
        media_header.time_range = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.start_time_ms == 1002
        assert processor.partial_segments[media_header.header_id].start_ms == 1002

    def test_media_header_with_time_range(self, base_args):
        # time_range is provided instead of start_ms in media header
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.time_range = TimeRange(start_ticks=10020, timescale=10000)
        media_header.start_ms = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.start_time_ms == 1002
        assert processor.partial_segments[media_header.header_id].start_ms == 1002

    def test_media_header_with_start_ms_and_time_range(self, base_args):
        # time_range and start_ms is provided; start_ms should take precedence
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.time_range = TimeRange(start_ticks=10020, timescale=10000)
        media_header.start_ms = 1004

        result = processor.process_media_header(media_header)

        assert result.sabr_part.start_time_ms == 1004
        assert processor.partial_segments[media_header.header_id].start_ms == 1004

    def test_media_header_duration_ms(self, base_args):
        # only duration_ms is provided in media header
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.duration_ms = 1002
        media_header.time_range = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.duration_ms == 1002
        assert processor.partial_segments[media_header.header_id].duration_ms == 1002

    def test_media_header_duration_ticks(self, base_args):
        # only duration_ticks is provided in media header
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.time_range = TimeRange(duration_ticks=10020, timescale=10000)
        media_header.duration_ms = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.duration_ms == 1002
        assert processor.partial_segments[media_header.header_id].duration_ms == 1002

    def test_media_header_duration_ms_and_ticks(self, base_args):
        # both duration_ms and duration_ticks are provided; duration_ms should take precedence
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.duration_ms = 1004
        media_header.time_range = TimeRange(duration_ticks=10020, timescale=10000)

        result = processor.process_media_header(media_header)

        assert result.sabr_part.duration_ms == 1004
        assert processor.partial_segments[media_header.header_id].duration_ms == 1004

    # init segment duration_ms default to 0 tested in test_media_header_init_segment

    def test_media_header_estimated_duration(self, base_args):
        # Should estimate the duration for livestreams
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            live_segment_target_duration_sec=5,
            live_segment_target_duration_tolerance_ms=200,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.duration_ms = None
        media_header.time_range = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.duration_ms == 4800  # 5 seconds minus tolerance
        assert result.sabr_part.duration_estimated is True
        assert processor.partial_segments[media_header.header_id].duration_ms == 4800
        assert processor.partial_segments[media_header.header_id].duration_estimated is True

    def test_media_header_prefer_actual_duration(self, base_args):
        # Should prefer actual duration over estimated duration
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            live_segment_target_duration_sec=5,
            live_segment_target_duration_tolerance_ms=200,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.duration_ms = 6000

        result = processor.process_media_header(media_header)

        assert result.sabr_part.duration_ms == 6000
        assert result.sabr_part.duration_estimated is False
        assert processor.partial_segments[media_header.header_id].duration_ms == 6000
        assert processor.partial_segments[media_header.header_id].duration_estimated is False

    def test_media_header_estimated_content_length(self, base_args):
        # Should estimate the content length for livestreams
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            live_segment_target_duration_sec=5,
            live_segment_target_duration_tolerance_ms=200,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = None
        media_header.bitrate_bps = 45000
        media_header.duration_ms = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.content_length == 216000
        assert result.sabr_part.content_length_estimated is True
        assert processor.partial_segments[media_header.header_id].content_length == 216000
        assert processor.partial_segments[media_header.header_id].content_length_estimated is True

    def test_media_header_estimated_content_length_with_duration(self, base_args):
        # Should use actual duration over the estimated duration if available
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            live_segment_target_duration_sec=5,
            live_segment_target_duration_tolerance_ms=200,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = None
        media_header.bitrate_bps = 45000
        media_header.duration_ms = 6000

        result = processor.process_media_header(media_header)

        assert result.sabr_part.content_length == 270000
        assert result.sabr_part.content_length_estimated is True
        assert processor.partial_segments[media_header.header_id].content_length == 270000
        assert processor.partial_segments[media_header.header_id].content_length_estimated is True

    def test_media_header_content_length_provided(self, base_args):
        # Should not estimate content length if content_length is provided
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            live_segment_target_duration_sec=5,
            live_segment_target_duration_tolerance_ms=200,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = 100000
        media_header.bitrate_bps = 45000
        media_header.duration_ms = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.content_length == 100000
        assert result.sabr_part.content_length_estimated is False
        assert processor.partial_segments[media_header.header_id].content_length == 100000
        assert processor.partial_segments[media_header.header_id].content_length_estimated is False

    def test_media_header_no_estimated_content_length(self, base_args):
        # Should not estimate content length if bitrate_bps is not available
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            live_segment_target_duration_sec=5,
            live_segment_target_duration_tolerance_ms=200,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = None
        media_header.bitrate_bps = None
        media_header.duration_ms = None

        result = processor.process_media_header(media_header)

        assert result.sabr_part.content_length is None
        assert result.sabr_part.content_length_estimated is False
        assert processor.partial_segments[media_header.header_id].content_length is None
        assert processor.partial_segments[media_header.header_id].content_length_estimated is False

    def test_media_header_non_live_no_estimated_content_length(self, base_args):
        # Should not estimate content length for non-live streams
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = None
        media_header.bitrate_bps = 45000

        result = processor.process_media_header(media_header)

        assert result.sabr_part.content_length is None
        assert result.sabr_part.content_length_estimated is False
        assert processor.partial_segments[media_header.header_id].content_length is None
        assert processor.partial_segments[media_header.header_id].content_length_estimated is False

    # Discard segment handling

    def test_discard_segment_initialized_format_discard(self, base_args):
        # Segment should be discarded if initialized format is marked as discard
        selector = make_selector('audio', discard_media=True)
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        # Clear consumed ranges. We want to also handle the case when we cannot mark the format as entirely consumed.
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.clear()
        media_header = make_media_header(selector, sequence_no=1)

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert result.sabr_part is None
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        assert segment.discard is True
        assert segment.consumed is False

    def test_discard_segment_sequence_number_consumed(self, base_args):
        # Segment should be discarded if sequence number within a consumed range
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=4)
        # Simulate that the sequence number 1 has been consumed
        # Testing with multiple consumed ranges
        consumed_ranges = [
            ConsumedRange(
                start_time_ms=0,
                duration_ms=1000,
                start_sequence_number=1,
                end_sequence_number=2),
            ConsumedRange(
                start_time_ms=0,
                duration_ms=2000,
                start_sequence_number=3,
                end_sequence_number=6)]
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.extend(consumed_ranges)

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert result.sabr_part is None
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        assert segment.discard is True
        assert segment.consumed is True

    def test_discard_segment_already_have_init_segment(self, base_args):
        # Segment should be discarded if already have init segment
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_init_header(selector)

        # Simulate that we already have an init segment for this format
        processor.initialized_formats[str(selector.format_ids[0])].init_segment = Segment(
            is_init_segment=True,
            format_id=selector.format_ids[0],
        )

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert result.sabr_part is None
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        assert segment.discard is True
        assert segment.consumed is True

    def test_previous_ooo_initialized_format_discard(self, base_args):
        # Segment should be discarded if previous segment is not in order and initialized format is marked as discard
        # We are testing that it checks the InitializedFormat.discard flag
        # No error should be raised
        selector = make_selector('audio', discard_media=True)
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)

        # Simulate that the previous segment was not in order
        processor.initialized_formats[str(selector.format_ids[0])].current_segment = Segment(
            format_id=selector.format_ids[0],
            is_init_segment=False,
            sequence_number=10,
            discard=False,  # should not happen but not relying on this
            consumed=False,
        )
        # Clear consumed ranges. We want to also handle the case when we cannot mark the format as entirely consumed.
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.clear()

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert result.sabr_part is None
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        assert segment.discard is True
        assert segment.consumed is False

    def test_previous_ooo_segment_consumed(self, base_args):
        # Segment should be ignored and discarded if previous segment is out of order, and the current segment is already consumed
        # No error should be raised
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)

        # Simulate that the previous segment was discarded and not in order
        processor.initialized_formats[str(selector.format_ids[0])].current_segment = Segment(
            format_id=selector.format_ids[0],
            is_init_segment=False,
            sequence_number=10,
            discard=False,
            consumed=False,
        )
        # Mark segment 1 as consumed
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.append(
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=1,
                start_time_ms=0,
                duration_ms=2300,
            ),
        )

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert result.sabr_part is None
        assert media_header.header_id in processor.partial_segments
        segment = processor.partial_segments[media_header.header_id]
        assert segment.discard is True
        assert segment.consumed is True

    def test_previous_ooo_previous_discarded(self, base_args):
        # Segment should be accepted if previous segment is discarded AND segment is not in order
        # No error should be raised
        # TODO: confirm expected behavior
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)

        # Simulate that the previous segment was discarded and not in order
        processor.initialized_formats[str(selector.format_ids[0])].current_segment = Segment(
            format_id=selector.format_ids[0],
            is_init_segment=False,
            sequence_number=10,
            discard=True,  # Previous segment is discarded
            consumed=False,
        )

        result = processor.process_media_header(media_header)

        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)
        assert media_header.header_id in processor.partial_segments

    def test_media_header_no_video_id(self, base_args):
        # Media header does not have a video id, but processor does
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            video_id='example_video_id',
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.video_id = None

        # Should not raise an error
        result = processor.process_media_header(media_header)
        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)

    def test_processor_no_video_id_media_header_has_video_id(self, base_args):
        # Processor does not have a video id, but media header does
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            video_id=None,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.video_id = 'example_video_id'

        # Should not raise an error
        result = processor.process_media_header(media_header)
        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)

    def test_no_update_consumed_ranges(self, base_args):
        # Media Header should not update the consumed ranges. This is done on media end.
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        result = processor.process_media_header(media_header)
        assert isinstance(result, ProcessMediaHeaderResult)
        assert isinstance(result.sabr_part, MediaSegmentInitSabrPart)
        assert not processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges

    # Error scenarios

    def test_video_id_mismatch(self, base_args):
        # Media header has a different video id than the processor
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
            video_id='example_video_id',
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.video_id = 'different_video_id'

        with pytest.raises(
            SabrStreamError,
            match='Received unexpected MediaHeader for video different_video_id \\(expecting example_video_id\\)',
        ):
            processor.process_media_header(media_header)

    def test_format_id_missing(self, base_args):
        # Media header does not have a format id
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.format_id = None

        with pytest.raises(SabrStreamError, match='FormatId not found in MediaHeader'):
            processor.process_media_header(media_header)

    def test_header_id_in_partial_segments(self, base_args):
        # Media header has a header_id that is already in partial_segments
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)

        processor.process_media_header(media_header)

        with pytest.raises(SabrStreamError, match='Header ID 0 already exists'):
            processor.process_media_header(media_header)

    def test_no_matching_initialized_format(self, base_args):
        # Media header has a format_id that does not match any initialized format
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        media_header = make_media_header(selector, sequence_no=1)

        with pytest.raises(SabrStreamError, match='Initialized format not found'):
            processor.process_media_header(media_header)

    def test_media_header_compression(self, base_args):
        # Media header has a compression algorithm
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.compression = CompressionAlgorithm.COMPRESSION_ALGORITHM_GZIP

        # should raise an error as unsupported
        with pytest.raises(SabrStreamError, match='Compression not supported in MediaHeader'):
            processor.process_media_header(media_header)

    def test_missing_sequence_number_not_init_segment(self, base_args):
        # Media header is not an init segment and does not have a sequence number
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=None)

        with pytest.raises(SabrStreamError, match='Sequence number not found in MediaHeader'):
            processor.process_media_header(media_header)

    def test_no_duration_ms(self, base_args):
        # Media header does not have a duration_ms or time_range with duration_ticks
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.duration_ms = None
        media_header.time_range = TimeRange(timescale=1000, start_ticks=0, duration_ticks=None)

        with pytest.raises(SabrStreamError, match='Cannot determine duration of segment 1'):
            processor.process_media_header(media_header)

    def test_segment_mismatch(self, base_args):
        # Media header segment does not match the current segment
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)

        # Simulate that the current segment is not in order
        processor.initialized_formats[str(selector.format_ids[0])].current_segment = Segment(
            format_id=selector.format_ids[0],
            is_init_segment=False,
            sequence_number=10,
            discard=False,
            consumed=False,
        )

        with pytest.raises(MediaSegmentMismatchError, match='Segment sequence number mismatch') as exc_info:
            processor.process_media_header(media_header)
            assert exc_info.value.expected_sequence_number == 11
            assert exc_info.value.received_sequence_number == 1


class TestMedia:
    def test_valid_media_parts(self, base_args):
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )

        example_payload = b'example-data'
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = len(example_payload)
        processor.process_media_header(media_header)

        result = processor.process_media(
            header_id=media_header.header_id,
            content_length=media_header.content_length,
            data=io.BytesIO(example_payload))

        assert isinstance(result, ProcessMediaResult)
        assert isinstance(result.sabr_part, MediaSegmentDataSabrPart)
        assert result.sabr_part == MediaSegmentDataSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=1,
            is_init_segment=False,
            total_segments=fim.total_segments,
            data=example_payload,
            content_length=len(example_payload),
            segment_start_bytes=0,
        )
        assert processor.partial_segments[media_header.header_id].received_data_length == len(example_payload)

        # Subsequent call should increment received data length
        result = processor.process_media(
            header_id=media_header.header_id,
            content_length=media_header.content_length,
            data=io.BytesIO(example_payload))

        assert isinstance(result, ProcessMediaResult)
        assert isinstance(result.sabr_part, MediaSegmentDataSabrPart)
        assert result.sabr_part == MediaSegmentDataSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=1,
            is_init_segment=False,
            total_segments=fim.total_segments,
            data=example_payload,
            content_length=len(example_payload),
            segment_start_bytes=len(example_payload),
        )
        assert processor.partial_segments[media_header.header_id].received_data_length == len(example_payload) * 2

    def test_no_matching_partial_segment(self, base_args):
        # Should raise an error if no matching partial segment found
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        with pytest.raises(SabrStreamError, match='Header ID 12345 not found in partial segments'):
            processor.process_media(
                header_id=12345,  # Non-existent header ID
                content_length=100,
                data=io.BytesIO(b'example-data'),
            )

    def test_discarded_partial_segment(self, base_args):
        # Should ignore the media part if the segment is marked as discard
        selector = make_selector('audio', discard_media=True)
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        example_payload = b'example-data'
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = len(example_payload)
        processor.process_media_header(media_header)

        result = processor.process_media(
            header_id=media_header.header_id,
            content_length=media_header.content_length,
            data=io.BytesIO(example_payload))

        assert isinstance(result, ProcessMediaResult)
        assert result.sabr_part is None
        assert processor.partial_segments[media_header.header_id].received_data_length == len(example_payload)

    def test_valid_init_segment(self, base_args):
        # Should process init segment correctly and report as such
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        example_payload = b'example-init-data'
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_init_header(selector)
        processor.process_media_header(media_header)

        result = processor.process_media(
            header_id=media_header.header_id,
            content_length=len(example_payload),
            data=io.BytesIO(example_payload))

        assert isinstance(result, ProcessMediaResult)
        assert isinstance(result.sabr_part, MediaSegmentDataSabrPart)
        assert result.sabr_part == MediaSegmentDataSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=None,
            is_init_segment=True,  # Init segment should be True
            total_segments=fim.total_segments,
            data=example_payload,
            content_length=len(example_payload),
            segment_start_bytes=0,
        )
        assert processor.partial_segments[media_header.header_id].received_data_length == len(example_payload)


class TestMediaEnd:

    def test_init_segment_media_end(self, base_args):
        # Should process media end for init segment
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_init_header(selector)
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-init-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert isinstance(result.sabr_part, MediaSegmentEndSabrPart)
        assert result.sabr_part == MediaSegmentEndSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=None,
            is_init_segment=True,
            total_segments=fim.total_segments,
        )
        assert result.is_new_segment is True
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is segment
        assert init_format.current_segment is None
        assert not init_format.consumed_ranges

    def test_media_segment_media_end(self, base_args):
        # Should process media end for a regular media segment
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert isinstance(result.sabr_part, MediaSegmentEndSabrPart)
        assert result.sabr_part == MediaSegmentEndSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=1,
            is_init_segment=False,
            total_segments=fim.total_segments,
        )
        assert result.is_new_segment is True
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is None
        assert init_format.current_segment is segment
        assert len(init_format.consumed_ranges) == 1
        assert init_format.consumed_ranges[0] == ConsumedRange(
            start_sequence_number=1,
            end_sequence_number=1,
            start_time_ms=media_header.start_ms,
            duration_ms=media_header.duration_ms,
        )

    def test_media_segment_update_consumed_range(self, base_args):
        # Should update an existing consumed range the segment belongs to (at the end of)
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        init_format.consumed_ranges.append(
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=3,
                start_time_ms=20,
                duration_ms=3000))
        # Unrelated consumed range
        init_format.consumed_ranges.append(
            ConsumedRange(
                start_sequence_number=6,
                end_sequence_number=10,
                start_time_ms=6000,
                duration_ms=3000))

        media_header = make_media_header(selector, sequence_no=4)
        media_header.start_ms = 3021
        media_header.duration_ms = 1050
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert isinstance(result.sabr_part, MediaSegmentEndSabrPart)
        assert result.sabr_part == MediaSegmentEndSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=4,
            is_init_segment=False,
            total_segments=fim.total_segments,
        )
        assert result.is_new_segment is True
        assert len(init_format.consumed_ranges) == 2
        assert init_format.consumed_ranges[0] == ConsumedRange(
            start_sequence_number=1,
            end_sequence_number=4,
            start_time_ms=20,
            duration_ms=4051,
        )
        assert init_format.consumed_ranges[1] == ConsumedRange(
            start_sequence_number=6,
            end_sequence_number=10,
            start_time_ms=6000,
            duration_ms=3000,
        )
        assert init_format.current_segment is segment

    def test_media_segment_discard(self, base_args):
        # Should discard the segment if it is marked as discard. Consumed ranges should be updated.
        selector = make_selector('audio', discard_media=True)
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        # Clear consumed ranges. We want to also handle the case when we cannot mark the format as entirely consumed.
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.clear()
        media_header = make_media_header(selector, sequence_no=1)
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert result.sabr_part is None
        # New segment created, but discarded. Not previously consumed.
        assert result.is_new_segment is True
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is None
        assert init_format.current_segment is segment
        assert len(init_format.consumed_ranges) == 1

    def test_init_segment_discard(self, base_args):
        # Should discard the init segment if it is marked as discard.
        selector = make_selector('audio', discard_media=True)
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        # Clear consumed ranges. We want to also handle the case when we cannot mark the format as entirely consumed.
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.clear()
        media_header = make_init_header(selector)
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-init-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert result.sabr_part is None
        # New segment created, but discarded. Not previously consumed.
        assert result.is_new_segment is True
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is segment
        assert init_format.current_segment is None
        assert len(init_format.consumed_ranges) == 0

    def test_media_segment_consumed(self, base_args):
        # Should mark the segment as consumed (and discard) if it is already in consumed ranges
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        # Simulate that the segment is already consumed
        processor.initialized_formats[str(selector.format_ids[0])].consumed_ranges.append(
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=2,
                start_time_ms=media_header.start_ms,
                duration_ms=media_header.duration_ms + 500,
            ))
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert result.sabr_part is None
        assert result.is_new_segment is False
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is None
        assert init_format.current_segment is segment
        assert len(init_format.consumed_ranges) == 1
        assert init_format.consumed_ranges[0] == ConsumedRange(
            start_sequence_number=1,
            end_sequence_number=2,
            start_time_ms=media_header.start_ms,
            duration_ms=media_header.duration_ms + 500,
        )

    def test_init_segment_consumed(self, base_args):
        # Should mark the init segment as consumed (and discard) if already seen init segment
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_init_header(selector)
        # Simulate that the init segment is already consumed
        processor.initialized_formats[str(selector.format_ids[0])].init_segment = Segment(
            is_init_segment=True,
            format_id=selector.format_ids[0],
            sequence_number=None,
        )
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, media_header.content_length, io.BytesIO(b'example-init-data'))
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert result.sabr_part is None
        assert result.is_new_segment is False
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is segment  # xxx: Should we be taking the new init segment we discarded?
        assert init_format.current_segment is None
        assert len(init_format.consumed_ranges) == 0

    def test_media_end_no_content_length(self, base_args):
        # Should not raise an error if segment does not have a content length
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = None
        processor.process_media_header(media_header)
        processor.process_media(media_header.header_id, 500, io.BytesIO(b'example-data'))

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert isinstance(result.sabr_part, MediaSegmentEndSabrPart)

    def test_media_end_no_partial_segment(self, base_args):
        # Should raise an error if no partial segment found for the header_id
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)

        with pytest.raises(SabrStreamError, match='Header ID 12345 not found in partial segments'):
            processor.process_media_end(12345)

    def test_content_length_mismatch(self, base_args):
        # Should raise an error if content length does not match the expected length
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        processor.process_media_header(media_header)

        with pytest.raises(SabrStreamError, match='Content length mismatch'):
            processor.process_media_end(media_header.header_id)

        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is None
        assert init_format.current_segment is None

    def test_estimated_content_length_mismatch(self, base_args, logger):
        # Should not raise an error if estimated content length does not match, rather log in trace
        selector = make_selector('audio')
        processor = SabrProcessor(
            **base_args,
            audio_selection=selector,
        )
        processor.is_live = True
        fim = make_format_im(selector)
        processor.process_format_initialization_metadata(fim)
        media_header = make_media_header(selector, sequence_no=1)
        media_header.content_length = None
        media_header.bitrate_bps = 1000000
        media_header.duration_ms = 4000
        processor.process_media_header(media_header)
        processor.process_media(
            media_header.header_id,
            content_length=500,  # Mismatch between what is estimated
            data=io.BytesIO(b'example-data'),
        )
        segment = processor.partial_segments[media_header.header_id]

        result = processor.process_media_end(media_header.header_id)

        assert isinstance(result, ProcessMediaEndResult)
        assert isinstance(result.sabr_part, MediaSegmentEndSabrPart)
        assert result.sabr_part == MediaSegmentEndSabrPart(
            format_selector=selector,
            format_id=selector.format_ids[0],
            sequence_number=1,
            is_init_segment=False,
            total_segments=fim.total_segments,
        )
        assert result.is_new_segment is True
        assert media_header.header_id not in processor.partial_segments
        init_format = processor.initialized_formats[str(selector.format_ids[0])]
        assert init_format.init_segment is None
        assert init_format.current_segment is segment
        assert init_format.current_segment.content_length_estimated is True
        assert init_format.current_segment.content_length == 4000000
        assert init_format.current_segment.received_data_length == 500
        logger.trace.assert_called_with(
            f'Content length for {segment.format_id} (sequence 1) was estimated, '
            f'estimated {segment.content_length} bytes, got {segment.received_data_length} bytes')

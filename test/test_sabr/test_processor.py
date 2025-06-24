import pytest
from unittest.mock import MagicMock

from yt_dlp.extractor.youtube._streaming.sabr.part import PoTokenStatusSabrPart

from yt_dlp.extractor.youtube._streaming.sabr.processor import SabrProcessor, ProcessStreamProtectionStatusResult
from yt_dlp.extractor.youtube._streaming.sabr.models import (
    AudioSelector,
    VideoSelector,
    CaptionSelector,
)
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId, StreamProtectionStatus
from yt_dlp.extractor.youtube._proto.innertube import ClientInfo, NextRequestPolicy


@pytest.fixture
def logger():
    return MagicMock()


@pytest.fixture
def client_info():
    return ClientInfo()


@pytest.fixture
def base_args(logger, client_info):
    return {
        'logger': logger,
        'client_info': client_info,
        'video_playback_ustreamer_config': 'dGVzdA==',
    }


def make_selector(selector_type, *, discard_media=False, format_ids=None):
    if selector_type == 'audio':
        return AudioSelector(
            display_name='audio',
            format_ids=format_ids or [FormatId(itag=140)],
            discard_media=discard_media,
        )
    elif selector_type == 'video':
        return VideoSelector(
            display_name='video',
            format_ids=format_ids or [FormatId(itag=248)],
            discard_media=discard_media,
        )
    elif selector_type == 'caption':
        return CaptionSelector(
            display_name='caption',
            format_ids=format_ids or [FormatId(itag=386)],
            discard_media=discard_media,
        )
    raise ValueError(f'Unknown selector_type: {selector_type}')


def selector_factory(selector_type, *, discard_media=False, format_ids=None):
    def factory():
        return make_selector(selector_type, discard_media=discard_media, format_ids=format_ids)
    return factory


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


class TestStreamProtectionStatusPart:

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

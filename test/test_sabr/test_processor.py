import pytest
from unittest.mock import MagicMock

from yt_dlp.extractor.youtube._streaming.sabr.processor import SabrProcessor
from yt_dlp.extractor.youtube._streaming.sabr.models import (
    AudioSelector,
    VideoSelector,
    CaptionSelector,
)
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.extractor.youtube._proto.innertube import ClientInfo


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
        assert processor.live_end_segment_tolerance == 10
        assert processor.post_live is False

    def test_override_defaults(self, base_args):
        processor = SabrProcessor(
            **base_args,
            live_segment_target_duration_sec=8,
            live_segment_target_duration_tolerance_ms=42,
            start_time_ms=123,
            live_end_segment_tolerance=3,
            post_live=True,
        )
        assert processor.live_segment_target_duration_sec == 8
        assert processor.live_segment_target_duration_tolerance_ms == 42
        assert processor.start_time_ms == 123
        assert processor.live_end_segment_tolerance == 3
        assert processor.post_live is True

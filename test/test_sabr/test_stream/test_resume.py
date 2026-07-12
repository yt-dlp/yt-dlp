from __future__ import annotations
import pytest

from test.test_sabr.test_stream.helpers import (
    DEFAULT_NUM_VIDEO_SEGMENTS,
    BasicAudioVideoProfile,
    assert_media_sequence_in_order,
    setup_sabr_stream_av,
    DEFAULT_VIDEO_FORMAT,
    collect_parts,
    handle_media_init_part,
)

from yt_dlp.extractor.youtube._streaming.sabr.models import (
    ConsumedRange,
)
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    MediaSegmentInitSabrPart,
)


class TestStream:
    def test_resume_both(self, logger, client_info):
        # 1. Get real segments so we can resume some
        init_sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        iter_parts = init_sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == DEFAULT_NUM_VIDEO_SEGMENTS + 1

        # Mark segments 1 and 2 as downloaded
        consumed_ranges = [
            # Note: First segment is init segment with no sequence number
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=1,
                start_time_ms=media_init_parts[1].start_time_ms,
                duration_ms=media_init_parts[1].duration_ms,
            ),
            ConsumedRange(
                start_sequence_number=2,
                end_sequence_number=2,
                start_time_ms=media_init_parts[2].start_time_ms,
                duration_ms=media_init_parts[2].duration_ms,
            ),
        ]

        # 2. Real download with resume
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        _, video_selector = selectors

        parts = []
        for part in sabr_stream:
            handle_media_init_part(part, parts)
            if isinstance(part, FormatInitializedSabrPart):
                # Apply resume state
                sabr_stream.resume_format(part.format_id, has_init_segment=True, consumed_ranges=consumed_ranges)
            parts.append(part)

        # should have only received segments starting at 3, and no init segment
        assert_media_sequence_in_order(
            parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS - 2, start_sequence_number=3)

        logger.debug.assert_any_call(
            'Marked init segment as consumed for resumed format FormatId(itag=248, lmt=456, xtags=None)')
        logger.debug.assert_any_call(
            'Applied consumed ranges for resumed format FormatId(itag=248, lmt=456, xtags=None): '
            '[ConsumedRange(start_sequence_number=1, end_sequence_number=1, start_time_ms=0, duration_ms=1000), '
            'ConsumedRange(start_sequence_number=2, end_sequence_number=2, start_time_ms=1001, duration_ms=1000)]')

    def test_resume_only_init(self, logger, client_info):
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False)

        _, video_selector = selectors

        parts = []
        for part in sabr_stream:
            handle_media_init_part(part, parts)
            if isinstance(part, FormatInitializedSabrPart):
                # Apply resume state
                sabr_stream.resume_format(part.format_id, has_init_segment=True)
            parts.append(part)

        # should have received all segments but init segment
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

        logger.debug.assert_any_call(
            'Marked init segment as consumed for resumed format FormatId(itag=248, lmt=456, xtags=None)')

    def test_resume_only_data(self, logger, client_info):
        # 1. Get real segments so we can resume some
        init_sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        iter_parts = init_sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == DEFAULT_NUM_VIDEO_SEGMENTS + 1

        # Mark segments 1 and 2 as downloaded
        consumed_ranges = [
            # Note: First segment is init segment with no sequence number
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=1,
                start_time_ms=media_init_parts[1].start_time_ms,
                duration_ms=media_init_parts[1].duration_ms,
            ),
            ConsumedRange(
                start_sequence_number=2,
                end_sequence_number=2,
                start_time_ms=media_init_parts[2].start_time_ms,
                duration_ms=media_init_parts[2].duration_ms,
            ),
        ]

        # 2. Real download with resume
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        _, video_selector = selectors

        parts = []
        for part in sabr_stream:
            handle_media_init_part(part, parts)
            if isinstance(part, FormatInitializedSabrPart):
                # Apply resume state with only consumed ranges
                sabr_stream.resume_format(part.format_id, has_init_segment=False, consumed_ranges=consumed_ranges)
            parts.append(part)

        # should have only received segments starting at 3, but have init segment
        assert_media_sequence_in_order(
            parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS - 2 + 1, start_sequence_number=3)

        logger.debug.assert_any_call(
            'Applied consumed ranges for resumed format FormatId(itag=248, lmt=456, xtags=None): '
            '[ConsumedRange(start_sequence_number=1, end_sequence_number=1, start_time_ms=0, duration_ms=1000), '
            'ConsumedRange(start_sequence_number=2, end_sequence_number=2, start_time_ms=1001, duration_ms=1000)]')

    def test_resume_no_matching_izf(self, logger, client_info):
        # should fail to resume if format has yet to be initialized
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        with pytest.raises(ValueError) as exc_info:
            sabr_stream.resume_format(DEFAULT_VIDEO_FORMAT, has_init_segment=True)

        assert str(exc_info.value) == f'Unable to resume format {DEFAULT_VIDEO_FORMAT}: format not yet initialized'

        parts = collect_parts(sabr_stream)
        _, video_selector = selectors
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    def test_resume_already_have_segments(self, logger, client_info):
        # should fail to resume if format already has segments
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        parts = collect_parts(sabr_stream)
        _, video_selector = selectors
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        with pytest.raises(ValueError) as exc_info:
            sabr_stream.resume_format(DEFAULT_VIDEO_FORMAT, has_init_segment=True)

        assert str(exc_info.value) == f'Unable to resume format {DEFAULT_VIDEO_FORMAT}: must be resumed before receiving data'

    def test_resume_with_partial_segment(self, logger, client_info):
        # should fail to resume if format is currently downloading a segment
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        parts = []
        for part in sabr_stream:
            handle_media_init_part(part, parts)
            if isinstance(part, MediaSegmentInitSabrPart):
                with pytest.raises(ValueError) as exc_info:
                    sabr_stream.resume_format(DEFAULT_VIDEO_FORMAT, has_init_segment=True)
            parts.append(part)

        _, video_selector = selectors
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert str(exc_info.value) == f'Unable to resume format {DEFAULT_VIDEO_FORMAT}: must be resumed before receiving data'

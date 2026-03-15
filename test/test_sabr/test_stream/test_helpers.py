from __future__ import annotations
import io
import pytest
from test.test_sabr.test_stream.helpers import assert_media_sequence_in_order, create_inject_read_error
from test.test_sabr.test_stream.helpers import SkipSegmentProfile
import protobug
from yt_dlp.extractor.youtube._proto.videostreaming import MediaHeader
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import FormatInitializedSabrPart, MediaSegmentInitSabrPart, MediaSegmentDataSabrPart, MediaSegmentEndSabrPart
from yt_dlp.extractor.youtube._streaming.ump import UMPPart, UMPPartId
from yt_dlp.networking.exceptions import TransportError

# Test that our test assertion helper works correctly...


class TestAssertMediaSequence:
    def test_valid_sequence(self):
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)

        parts = [
            # unrelated format init should be ignored
            FormatInitializedSabrPart(format_id=FormatId(itag=248, lmt=456), format_selector=VideoSelector(display_name='video')),
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=3),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1),
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=2, total_segments=3),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=2, data=b'd2'),
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=2),
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=3, total_segments=3),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=3, data=b'd3'),
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=3),
        ]

        assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=3)

    def test_data_without_init_raises(self):
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)
        parts = [
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
        ]
        with pytest.raises(AssertionError, match='Media segment data part without init part'):
            assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=1)

    def test_end_without_init_raises(self):
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)
        parts = [
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1),
        ]
        with pytest.raises(AssertionError, match='Media segment end part without init part'):
            assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=1)

    def test_mismatched_data_sequence_raises(self):
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)
        parts = [
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=1),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=2, data=b'd_wrong'),
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1),
        ]
        with pytest.raises(AssertionError, match='Media segment data part sequence number mismatch'):
            assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=1)

    def test_missing_end_on_next_init_raises(self):
        # If a new init arrives without previous end, should raise
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)
        parts = [
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=2),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
            # Missing end for sequence 1
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=2, total_segments=2),
        ]
        with pytest.raises(AssertionError, match='Previous Media segment end part missing'):
            assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=2)

    def test_retry_allowed(self):
        # Allow retry where an init with the same sequence_number appears again
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)
        parts = [
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=1),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
            # Retried init for same sequence (simulates server resending); allowed when allow_retry=True
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=1),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1),
        ]
        assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=1, allow_retry=True)

    def test_retry_not_allowed_raises(self):
        # Disallow retry where an init with the same sequence_number appears again
        audio_selector = AudioSelector(display_name='audio')
        fmt = FormatId(itag=140, lmt=123)
        parts = [
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=1),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
            # Retried init for same sequence (simulates server resending); should raise when allow_retry=False
            MediaSegmentInitSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, total_segments=1),
            MediaSegmentDataSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1, data=b'd1'),
            MediaSegmentEndSabrPart(format_selector=audio_selector, format_id=fmt, sequence_number=1),
        ]
        with pytest.raises(AssertionError, match='Previous Media segment end part missing'):
            assert_media_sequence_in_order(parts, audio_selector, expected_total_segments=1, allow_retry=False)


class TestCreateInjectReadError:
    def make_part(self, part_id: UMPPartId, payload: bytes = b'x'):
        return UMPPart(part_id=part_id, size=len(payload), data=io.BytesIO(payload))

    def test_no_injection_when_request_number_not_matched(self):
        parts = [self.make_part(UMPPartId.MEDIA), self.make_part(UMPPartId.MEDIA_END)]
        injector = create_inject_read_error(request_numbers=[2], part_id=UMPPartId.MEDIA, occurance=1)

        returned = injector(parts, vpabr=None, url='http://example/', request_number=1)

        assert returned == parts

    def test_injects_error_after_nth_occurrence(self):
        parts = [self.make_part(UMPPartId.MEDIA), self.make_part(UMPPartId.MEDIA), self.make_part(UMPPartId.MEDIA_END)]
        injector = create_inject_read_error(request_numbers=[2], part_id=UMPPartId.MEDIA, occurance=2)

        returned = injector(parts, vpabr=None, url='http://example/', request_number=2)

        # Should have exactly one injected TransportError and list length +1
        assert any(isinstance(p, TransportError) for p in returned)
        assert sum(1 for p in returned if isinstance(p, TransportError)) == 1
        assert len(returned) == len(parts) + 1

        # Ensure injection is after the second MEDIA part
        media_indices = [i for i, p in enumerate(returned) if isinstance(p, UMPPart) and p.part_id == UMPPartId.MEDIA]
        assert isinstance(returned[media_indices[1] + 1], TransportError)
        assert str(returned[media_indices[1] + 1]) == 'simulated read error'

    def test_injection_only_once_when_multiple_matches(self):
        parts = [self.make_part(UMPPartId.MEDIA), self.make_part(UMPPartId.MEDIA), self.make_part(UMPPartId.MEDIA)]
        injector = create_inject_read_error(request_numbers=[3], part_id=UMPPartId.MEDIA, occurance=1)

        returned = injector(parts, vpabr=None, url='http://example/', request_number=3)

        # Only one injection
        assert sum(1 for p in returned if isinstance(p, TransportError)) == 1
        # It should be after the first MEDIA
        media_indices = [i for i, p in enumerate(returned) if isinstance(p, UMPPart) and p.part_id == UMPPartId.MEDIA]
        assert isinstance(returned[media_indices[0] + 1], TransportError)

    def test_no_injection_if_occurrence_not_reached(self):
        parts = [self.make_part(UMPPartId.MEDIA), self.make_part(UMPPartId.MEDIA)]
        injector = create_inject_read_error(request_numbers=[2], part_id=UMPPartId.MEDIA, occurance=5)

        returned = injector(parts, vpabr=None, url='http://example/', request_number=2)

        # No TransportError injected because occurance (5) not reached
        assert all(not isinstance(p, TransportError) for p in returned)
        assert returned == parts


def test_mock_time():
    import time as _time
    from .helpers import mock_time

    # Decorated function should not actually sleep (fast) and should advance the fake clock
    start = _time.perf_counter()

    @mock_time
    def _inner():
        t0 = _time.time()
        _time.sleep(1.5)
        assert _time.time() == pytest.approx(t0 + 1.5)

    _inner()
    inner_duration = _time.perf_counter() - start
    assert inner_duration < 0.1, 'decorated function should not perform a real sleep'

    # After decorator returns, original time.sleep should be restored (real sleep observable)
    t_before = _time.perf_counter()
    _time.sleep(0.02)
    elapsed = _time.perf_counter() - t_before
    assert elapsed >= 0.02


class TestSkipSegmentProfile:
    def test_skip_segments_excludes_specified_sequences(self):
        # Skip segment 2 and ensure it's not present in returned media segments
        profile = SkipSegmentProfile(options={
            'skip_segments': {2},
            'max_segments': 3,
        })

        fmt = FormatId(itag=140, lmt=123)

        parts, _ = profile.get_media_segments(
            buffered_segments=set(),
            total_segments=5,
            max_segments=3,
            player_time_ms=0,
            start_header_id=0,
            format_id=fmt,
        )

        # Extract sequence numbers from MEDIA_HEADER parts (non-init)
        seqs = []
        for p in parts:
            if p.part_id == UMPPartId.MEDIA_HEADER:
                mh = protobug.load(p.data, MediaHeader)
                if not mh.is_init_segment:
                    seqs.append(mh.sequence_number)

        assert 2 not in seqs

    def test_init_segment_always_generated_when_no_buffered(self):
        # Even when skip_segments is set, an init segment should be generated when no buffered segments
        profile = SkipSegmentProfile(options={'skip_segments': {1, 2}})
        fmt = FormatId(itag=140, lmt=123)

        parts, _ = profile.get_media_segments(
            buffered_segments=set(),
            total_segments=3,
            max_segments=2,
            player_time_ms=0,
            start_header_id=0,
            format_id=fmt,
        )

        # There should be a MEDIA_HEADER part with is_init_segment == True
        found_init = False
        for p in parts:
            if p.part_id == UMPPartId.MEDIA_HEADER:
                mh = protobug.load(p.data, MediaHeader)
                if mh.is_init_segment:
                    found_init = True
                    break

        assert found_init, 'Expected init segment to be generated when no buffered segments'

    def test_skip_allows_buffering_more_segments_when_skipped(self):
        # When a segment is marked as skipped, the profile should allow buffering
        # additional segments so the caller can still receive the configured
        # `max_segments` worth of media (i.e. skipped sequence gets replaced).
        profile_no_skip = SkipSegmentProfile(options={'max_segments': 2})
        profile_skip = SkipSegmentProfile(options={'max_segments': 2, 'skip_segments': {1, 2}})

        fmt = FormatId(itag=140, lmt=123)

        parts_no_skip, _ = profile_no_skip.get_media_segments(
            buffered_segments=set(),
            total_segments=5,
            max_segments=2,
            player_time_ms=0,
            start_header_id=0,
            format_id=fmt,
        )

        parts_skip, _ = profile_skip.get_media_segments(
            buffered_segments=set(),
            total_segments=5,
            max_segments=2,
            player_time_ms=0,
            start_header_id=0,
            format_id=fmt,
        )

        def extract_seqs(parts):
            seqs = []
            for p in parts:
                if p.part_id == UMPPartId.MEDIA_HEADER:
                    mh = protobug.load(p.data, MediaHeader)
                    if not mh.is_init_segment:
                        seqs.append(mh.sequence_number)
            return seqs

        seqs_no_skip = extract_seqs(parts_no_skip)
        seqs_skip = extract_seqs(parts_skip)

        assert seqs_no_skip == [1]
        assert seqs_skip == [3]

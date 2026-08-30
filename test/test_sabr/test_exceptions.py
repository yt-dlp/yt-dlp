from __future__ import annotations


from yt_dlp.extractor.youtube._proto.videostreaming import FormatId

from yt_dlp.extractor.youtube._streaming.sabr.exceptions import (
    InvalidSabrUrl,
    SabrStreamError,
    SabrStreamConsumedError,
    BroadcastIdChanged,
    MediaSegmentMismatchError,
    UnexpectedConsumedMediaSegment,
    PoTokenError,
    StreamStallError,
    SabrUrlExpired,
)
from yt_dlp.utils import bug_reports_message


def test_sabr_stream_error_default_expected():
    error = SabrStreamError('test error')
    assert error.msg == 'test error'
    assert error.expected is True
    assert str(error) == 'test error'


def test_sabr_stream_error_unexpected():
    error = SabrStreamError('test error', expected=False)
    assert error.msg == 'test error' + bug_reports_message()
    assert error.expected is False
    assert str(error) == 'test error' + bug_reports_message()


def test_sabr_stream_consumed_error():
    error = SabrStreamConsumedError()
    assert str(error) == 'SABR stream has already been consumed'
    assert error.expected is True


def test_invalid_sabr_url_error():
    error = InvalidSabrUrl(reason='my reason', url='ftp://invalid')
    assert str(error) == 'Invalid SABR URL: my reason (url=ftp://invalid)' + bug_reports_message()
    assert error.expected is False
    assert error.url == 'ftp://invalid'


def test_broadcast_id_changed_error():
    error = BroadcastIdChanged(old='old id', new='new id')
    assert str(error) == 'Broadcast ID changed from old id to new id.'
    assert error.expected is True


def test_media_segment_mismatch_error():
    error = MediaSegmentMismatchError(
        format_id=FormatId(itag=123, xtags='1234'),
        expected_sequence_number=2, received_sequence_number=1)
    assert str(error) == 'Segment sequence number mismatch for format FormatId(itag=123, lmt=None, xtags=\'1234\'): expected 2, received 1' + bug_reports_message()
    assert error.expected is False
    assert error.expected_sequence_number == 2
    assert error.received_sequence_number == 1


def test_unexpected_consumed_media_segment_error():
    error = UnexpectedConsumedMediaSegment(
        format_id=FormatId(itag=123, xtags='1234'), sequence_number=67)
    assert str(error) == 'Unexpected consumed segment received for format FormatId(itag=123, lmt=None, xtags=\'1234\'): sequence number 67 (not in expected consumed range)' + bug_reports_message()
    assert error.expected is False
    assert error.sequence_number == 67


def test_po_token_error_not_missing():
    error = PoTokenError()
    assert str(error) == 'This stream requires a GVS PO Token to continue and the one provided is invalid'


def test_po_token_error_missing():
    error = PoTokenError(missing=True)
    assert str(error) == 'This stream requires a GVS PO Token to continue'


def test_stream_stall_error():
    error = StreamStallError('abc')
    assert error.expected is False
    assert str(error) == 'abc' + bug_reports_message()


def test_sabr_url_expired_error():
    error = SabrUrlExpired()
    assert str(error) == 'SABR URL has expired. The download will need to be restarted.'

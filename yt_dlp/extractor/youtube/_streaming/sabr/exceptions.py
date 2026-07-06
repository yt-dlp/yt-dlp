from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.utils import YoutubeDLError, bug_reports_message


class SabrStreamError(YoutubeDLError):
    def __init__(self, msg=None, expected=True):
        super().__init__(msg + ('' if expected else bug_reports_message()))
        self.expected = expected


class SabrStreamConsumedError(SabrStreamError):
    def __init__(self):
        super().__init__('SABR stream has already been consumed', expected=True)


class InvalidSabrUrl(SabrStreamError):
    def __init__(self, reason: str, url: str):
        self.url = url
        super().__init__(f'Invalid SABR URL: {reason} (url={url})', expected=False)


class BroadcastIdChanged(SabrStreamError):
    def __init__(self, old: str, new: str):
        super().__init__(f'Broadcast ID changed from {old} to {new}.', expected=True)


class MediaSegmentMismatchError(SabrStreamError):
    def __init__(self, format_id: FormatId, expected_sequence_number: int, received_sequence_number: int):
        super().__init__(
            f'Segment sequence number mismatch for format {format_id}: '
            f'expected {expected_sequence_number}, received {received_sequence_number}', expected=False)
        self.expected_sequence_number = expected_sequence_number
        self.received_sequence_number = received_sequence_number


class UnexpectedConsumedMediaSegment(SabrStreamError):
    def __init__(self, format_id: FormatId, sequence_number: int):
        super().__init__(
            f'Unexpected consumed segment received for format {format_id}: '
            f'sequence number {sequence_number} (not in expected consumed range)', expected=False)
        self.sequence_number = sequence_number


class PoTokenError(SabrStreamError):
    def __init__(self, missing=False):
        super().__init__(
            f'This stream requires a GVS PO Token to continue'
            f'{" and the one provided is invalid" if not missing else ""}', expected=True)


class StreamStallError(SabrStreamError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, expected=False, **kwargs)


class SabrUrlExpired(SabrStreamError):
    def __init__(self):
        super().__init__('SABR URL has expired. The download will need to be restarted.', expected=True)

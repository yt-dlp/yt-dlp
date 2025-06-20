from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.utils import YoutubeDLError


class SabrStreamConsumedError(YoutubeDLError):
    pass


class SabrStreamError(YoutubeDLError):
    pass


class MediaSegmentMismatchError(SabrStreamError):
    def __init__(self, format_id: FormatId, expected_sequence_number: int, received_sequence_number: int):
        super().__init__(
            f'Segment sequence number mismatch for format {format_id}: '
            f'expected {expected_sequence_number}, received {received_sequence_number}')
        self.expected_sequence_number = expected_sequence_number
        self.received_sequence_number = received_sequence_number


class PoTokenError(SabrStreamError):
    def __init__(self, missing=False):
        super().__init__(
            f'This stream requires a GVS PO Token to continue'
            f'{" and the one provided is invalid" if not missing else ""}')

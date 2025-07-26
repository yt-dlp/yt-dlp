from __future__ import annotations

import dataclasses

from ._io import DiskFormatIOBackend
from ._file import SequenceFile, Sequence, Segment
from ._state import (
    SabrStateSegment,
    SabrStateSequence,
    SabrStateInitSegment,
    SabrState,
    SabrStateFile,
)
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    MediaSegmentInitSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
)

from yt_dlp.utils import DownloadError
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.utils.progress import ProgressCalculator

INIT_SEGMENT_ID = 'i'


@dataclasses.dataclass
class SabrFormatState:
    format_id: FormatId
    init_sequence: Sequence | None = None
    sequences: list[Sequence] = dataclasses.field(default_factory=list)


class SabrFDFormatWriter:
    def __init__(self, fd, filename, infodict, progress_idx=0, resume=False):
        self.fd = fd
        self.info_dict = infodict
        self.filename = filename
        self.progress_idx = progress_idx
        self.resume = resume

        self._progress = None
        self._downloaded_bytes = 0
        self._state = {}
        self._format_id = None

        self.file = DiskFormatIOBackend(
            fd=self.fd,
            filename=self.fd.temp_name(filename),
        )
        self._sabr_state_file = SabrStateFile(format_filename=self.filename, fd=fd)
        self._sequence_files: list[SequenceFile] = []
        self._init_sequence: SequenceFile | None = None

    @property
    def state(self):
        return SabrFormatState(
            format_id=self._format_id,
            init_sequence=self._init_sequence.sequence if self._init_sequence else None,
            sequences=[sf.sequence for sf in self._sequence_files],
        )

    @property
    def downloaded_bytes(self):
        return (sum(
            sequence.current_length for sequence in self._sequence_files)
            + (self._init_sequence.current_length if self._init_sequence else 0))

    def initialize_format(self, format_id):
        if self._format_id:
            raise ValueError('Already initialized')
        self._format_id = format_id

        if not self.resume:
            if self._sabr_state_file.exists:
                self._sabr_state_file.remove()
            return

        document = self._load_sabr_state()

        if document.init_segment:
            init_segment = Segment(
                segment_id=INIT_SEGMENT_ID,
                content_length=document.init_segment.content_length,
                is_init_segment=True,
            )

            try:
                self._init_sequence = SequenceFile(
                    fd=self.fd,
                    format_filename=self.filename,
                    resume=True,
                    sequence=Sequence(
                        sequence_id=INIT_SEGMENT_ID,
                        sequence_content_length=init_segment.content_length,
                        first_segment=init_segment,
                        last_segment=init_segment,
                    ))
            except DownloadError as e:
                self.fd.report_warning(f'Failed to resume init segment for format {self.info_dict.get("format_id")}: {e}')

        for sabr_sequence in list(document.sequences):
            try:
                self._sequence_files.append(SequenceFile(
                    fd=self.fd,
                    format_filename=self.filename,
                    resume=True,
                    sequence=Sequence(
                        sequence_id=str(sabr_sequence.sequence_start_number),
                        sequence_content_length=sabr_sequence.sequence_content_length,
                        first_segment=Segment(
                            segment_id=str(sabr_sequence.first_segment.sequence_number),
                            sequence_number=sabr_sequence.first_segment.sequence_number,
                            content_length=sabr_sequence.first_segment.content_length,
                            start_time_ms=sabr_sequence.first_segment.start_time_ms,
                            duration_ms=sabr_sequence.first_segment.duration_ms,
                            is_init_segment=False,
                        ),
                        last_segment=Segment(
                            segment_id=str(sabr_sequence.last_segment.sequence_number),
                            sequence_number=sabr_sequence.last_segment.sequence_number,
                            content_length=sabr_sequence.last_segment.content_length,
                            start_time_ms=sabr_sequence.last_segment.start_time_ms,
                            duration_ms=sabr_sequence.last_segment.duration_ms,
                            is_init_segment=False,
                        ),
                    ),
                ))
            except DownloadError as e:
                self.fd.report_warning(
                    f'Failed to resume sequence {sabr_sequence.sequence_start_number} '
                    f'for format {self.info_dict.get("format_id")}: {e}')

    @property
    def initialized(self):
        return self._format_id is not None

    def close(self):
        if not self.file:
            raise ValueError('Already closed')
        for sequence in self._sequence_files:
            sequence.close()
        self._sequence_files.clear()
        if self._init_sequence:
            self._init_sequence.close()
            self._init_sequence = None
        self.file.close()

    def _find_sequence_file(self, predicate):
        match = None
        for sequence in self._sequence_files:
            if predicate(sequence):
                if match is not None:
                    raise DownloadError('Multiple sequence files found for segment')
                match = sequence
        return match

    def find_next_sequence_file(self, next_segment: Segment):
        return self._find_sequence_file(lambda sequence: sequence.is_next_segment(next_segment))

    def find_current_sequence_file(self, segment_id: str):
        return self._find_sequence_file(lambda sequence: sequence.is_current_segment(segment_id))

    def initialize_segment(self, part: MediaSegmentInitSabrPart):
        if not self._progress:
            self._progress = ProgressCalculator(part.start_bytes)

        if not self._format_id:
            raise ValueError('not initialized')

        if part.is_init_segment:
            if not self._init_sequence:
                self._init_sequence = SequenceFile(
                    fd=self.fd,
                    format_filename=self.filename,
                    resume=False,
                    sequence=Sequence(
                        sequence_id=INIT_SEGMENT_ID,
                    ))

            self._init_sequence.initialize_segment(Segment(
                segment_id=INIT_SEGMENT_ID,
                content_length=part.content_length,
                content_length_estimated=part.content_length_estimated,
                is_init_segment=True,
            ))
            return True

        segment = Segment(
            segment_id=str(part.sequence_number),
            sequence_number=part.sequence_number,
            start_time_ms=part.start_time_ms,
            duration_ms=part.duration_ms,
            duration_estimated=part.duration_estimated,
            content_length=part.content_length,
            content_length_estimated=part.content_length_estimated,
        )

        sequence_file = self.find_current_sequence_file(segment.segment_id) or self.find_next_sequence_file(segment)

        if not sequence_file:
            sequence_file = SequenceFile(
                fd=self.fd,
                format_filename=self.filename,
                resume=False,
                sequence=Sequence(sequence_id=str(part.sequence_number)),
            )
            self._sequence_files.append(sequence_file)

        sequence_file.initialize_segment(segment)
        return True

    def write_segment_data(self, part: MediaSegmentDataSabrPart):
        if part.is_init_segment:
            sequence_file, segment_id = self._init_sequence, INIT_SEGMENT_ID
        else:
            segment_id = str(part.sequence_number)
            sequence_file = self.find_current_sequence_file(segment_id)

        if not sequence_file:
            raise DownloadError('Unable to find sequence file for segment. Was the segment initialized?')

        sequence_file.write_segment_data(part.data, segment_id)

        # TODO: Handling of disjointed segments (e.g. when downloading segments out of order / concurrently)
        self._progress.total = self.info_dict.get('filesize')
        self._state = {
            'status': 'downloading',
            'downloaded_bytes': self.downloaded_bytes,
            'total_bytes': self.info_dict.get('filesize'),
            'filename': self.filename,
            'eta': self._progress.eta.smooth,
            'speed': self._progress.speed.smooth,
            'elapsed': self._progress.elapsed,
            'progress_idx': self.progress_idx,
            'fragment_count': part.total_segments,
            'fragment_index': part.sequence_number,
        }

        self._progress.update(self._state['downloaded_bytes'])
        self.fd._hook_progress(self._state, self.info_dict)

    def end_segment(self, part: MediaSegmentEndSabrPart):
        if part.is_init_segment:
            sequence_file, segment_id = self._init_sequence, INIT_SEGMENT_ID
        else:
            segment_id = str(part.sequence_number)
            sequence_file = self.find_current_sequence_file(segment_id)

        if not sequence_file:
            raise DownloadError('Unable to find sequence file for segment. Was the segment initialized?')

        sequence_file.end_segment(segment_id)
        self._write_sabr_state()

    def _load_sabr_state(self):
        sabr_state = None
        if self._sabr_state_file.exists:
            try:
                sabr_state = self._sabr_state_file.retrieve()
            except Exception:
                self.fd.report_warning(
                    f'Corrupted state file for format {self.info_dict.get("format_id")}, restarting download')

        if sabr_state and sabr_state.format_id != self._format_id:
            self.fd.report_warning(
                f'Format ID mismatch in state file for {self.info_dict.get("format_id")}, restarting download')
            sabr_state = None

        if not sabr_state:
            sabr_state = SabrState(format_id=self._format_id)

        return sabr_state

    def _write_sabr_state(self):
        sabr_state = SabrState(format_id=self._format_id)

        if not self._init_sequence:
            sabr_state.init_segment = None
        else:
            sabr_state.init_segment = SabrStateInitSegment(
                content_length=self._init_sequence.sequence.sequence_content_length,
            )

        sabr_state.sequences = []
        for sequence_file in self._sequence_files:
            # Ignore partial sequences
            if not sequence_file.sequence.first_segment or not sequence_file.sequence.last_segment:
                continue
            sabr_state.sequences.append(SabrStateSequence(
                sequence_start_number=sequence_file.sequence.first_segment.sequence_number,
                sequence_content_length=sequence_file.sequence.sequence_content_length,
                first_segment=SabrStateSegment(
                    sequence_number=sequence_file.sequence.first_segment.sequence_number,
                    start_time_ms=sequence_file.sequence.first_segment.start_time_ms,
                    duration_ms=sequence_file.sequence.first_segment.duration_ms,
                    duration_estimated=sequence_file.sequence.first_segment.duration_estimated,
                    content_length=sequence_file.sequence.first_segment.content_length,
                ),
                last_segment=SabrStateSegment(
                    sequence_number=sequence_file.sequence.last_segment.sequence_number,
                    start_time_ms=sequence_file.sequence.last_segment.start_time_ms,
                    duration_ms=sequence_file.sequence.last_segment.duration_ms,
                    duration_estimated=sequence_file.sequence.last_segment.duration_estimated,
                    content_length=sequence_file.sequence.last_segment.content_length,
                ),
            ))

        self._sabr_state_file.update(sabr_state)

    def finish(self):
        self._state['status'] = 'finished'
        self.fd._hook_progress(self._state, self.info_dict)

        for sequence_file in self._sequence_files:
            sequence_file.close()

        if self._init_sequence:
            self._init_sequence.close()

        # Now merge all the sequences together
        self.file.initialize_writer(resume=False)

        # Note: May not always be an init segment, e.g for live streams
        if self._init_sequence:
            self._init_sequence.read_into(self.file)
            self._init_sequence.close()

        # TODO: handling of disjointed segments
        previous_seq_number = None
        for sequence_file in sorted(
                (sf for sf in self._sequence_files if sf.sequence.first_segment),
                key=lambda s: s.sequence.first_segment.sequence_number):
            if previous_seq_number and previous_seq_number + 1 != sequence_file.sequence.first_segment.sequence_number:
                self.fd.report_warning(f'Disjointed sequences found in SABR format {self.info_dict.get("format_id")}')
            previous_seq_number = sequence_file.sequence.last_segment.sequence_number
            sequence_file.read_into(self.file)
            sequence_file.close()

        # Format temp file should have all the segments, rename it to the final name
        self.file.close()
        self.fd.try_rename(self.file.filename, self.fd.undo_temp_name(self.file.filename))

        # Remove the state file
        self._sabr_state_file.remove()

        # Remove sequence files
        for sf in self._sequence_files:
            sf.close()
            sf.remove()

        if self._init_sequence:
            self._init_sequence.close()
            self._init_sequence.remove()
        self.close()

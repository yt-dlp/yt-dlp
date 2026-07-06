import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from yt_dlp.downloader.sabr._file import Sequence, SequenceFile, Segment
from yt_dlp.downloader.sabr._state import (
    SabrState,
    SabrStateFile,
    SabrStateInitSegment,
    SabrStateSegment,
    SabrStateSequence,
)
from yt_dlp.downloader.sabr._writer import INIT_SEGMENT_ID, SabrFDFormatWriter
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
    MediaSegmentInitSabrPart,
)
from yt_dlp.utils._utils import DownloadError


INIT_DATA = b'init-data'
SEGMENT_ONE_DATA = b'segment-one'
SEGMENT_TWO_DATA = b'segment-two'
SEGMENT_THREE_DATA = b'segment-three'
BROADCAST_ID_1 = 'broadcast-1'
BROADCAST_ID_2 = 'broadcast-2'
VIDEO_ID = 'video_id'
VIDEO_ID_2 = 'video_id_2'


@pytest.fixture
def format_id():
    return FormatId(itag=251, lmt=123456789, xtags='dash')


@pytest.fixture
def format_selector(format_id):
    return AudioSelector(display_name='audio', format_ids=[format_id])


@pytest.fixture
def info_dict():
    return {
        'format_id': '251',
        'filesize': len(INIT_DATA) + len(SEGMENT_ONE_DATA) + len(SEGMENT_TWO_DATA),
    }


def make_writer(fd, filename, info_dict, *, resume=False):
    return SabrFDFormatWriter(fd=fd, filename=filename, video_id=VIDEO_ID, infodict=info_dict, resume=resume)


def make_init_part(format_selector, format_id, **kwargs):
    return MediaSegmentInitSabrPart(
        format_selector=format_selector,
        format_id=format_id,
        total_segments=kwargs.pop('total_segments', 2),
        start_time_ms=kwargs.pop('start_time_ms', 0),
        duration_ms=kwargs.pop('duration_ms', 1000),
        start_bytes=kwargs.pop('start_bytes', 0),
        **kwargs,
    )


def make_data_part(format_selector, format_id, **kwargs):
    return MediaSegmentDataSabrPart(
        format_selector=format_selector,
        format_id=format_id,
        total_segments=kwargs.pop('total_segments', 2),
        **kwargs,
    )


def make_end_part(format_selector, format_id, **kwargs):
    return MediaSegmentEndSabrPart(
        format_selector=format_selector,
        format_id=format_id,
        total_segments=kwargs.pop('total_segments', 2),
        **kwargs,
    )


def write_sequence_file(fd, filename, sequence, segment, data):
    sequence_file = SequenceFile(fd=fd, format_filename=filename, sequence=sequence)
    sequence_file.initialize_segment(segment)
    sequence_file.write_segment_data(data, segment.segment_id)
    sequence_file.end_segment(segment.segment_id)
    sequence_file.close()
    return sequence_file


def make_state_segment(segment: Segment):
    return SabrStateSegment(
        sequence_number=segment.sequence_number,
        start_time_ms=segment.start_time_ms,
        duration_ms=segment.duration_ms,
        duration_estimated=segment.duration_estimated,
        content_length=segment.content_length,
    )


class TestSabrFDFormatWriter:
    def test_write_and_finish(self, fd, filename, info_dict, format_id, format_selector):
        fd._hook_progress = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            is_init_segment=True,
            content_length=len(INIT_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            is_init_segment=True,
            total_segments=2,
            data=io.BytesIO(INIT_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, is_init_segment=True, total_segments=2))

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=2,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1, total_segments=2))

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=2,
            start_time_ms=1000,
            duration_ms=1000,
            content_length=len(SEGMENT_TWO_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=2,
            total_segments=2,
            data=io.BytesIO(SEGMENT_TWO_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=2, total_segments=2))

        assert Path(writer.file.filename).exists() is False
        assert writer._sabr_state_file.exists is True
        assert Path(filename + '.sqi.part').exists() is True
        assert Path(filename + '.sq1.part').exists() is True

        writer.finish()

        assert Path(filename).read_bytes() == INIT_DATA + SEGMENT_ONE_DATA + SEGMENT_TWO_DATA
        assert Path(filename + '.part').exists() is False
        assert writer._sabr_state_file.exists is False
        assert Path(filename + '.sqi.part').exists() is False
        assert Path(filename + '.sq1.part').exists() is False
        assert Path(filename + '.sq2.part').exists() is False
        assert writer.state.sequences == []
        assert writer.state.init_sequence is None
        assert fd._hook_progress.call_args_list[-1].args[0]['status'] == 'finished'

    def test_e2e_no_init_sequence(self, fd, filename, info_dict, format_id, format_selector):
        fd._hook_progress = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)
        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=2,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1, total_segments=2))

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=2,
            start_time_ms=1000,
            duration_ms=1000,
            content_length=len(SEGMENT_TWO_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=2,
            total_segments=2,
            data=io.BytesIO(SEGMENT_TWO_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=2, total_segments=2))

        assert Path(writer.file.filename).exists() is False
        assert writer._sabr_state_file.exists is True
        # no init sequence should exist
        assert Path(filename + '.sqi.part').exists() is False
        assert writer.state.init_sequence is None
        assert Path(filename + '.sq1.part').exists() is True

        writer.finish()

        assert Path(filename).read_bytes() == SEGMENT_ONE_DATA + SEGMENT_TWO_DATA
        assert Path(filename + '.part').exists() is False
        assert writer._sabr_state_file.exists is False
        assert Path(filename + '.sq1.part').exists() is False
        assert Path(filename + '.sq2.part').exists() is False
        assert writer.state.sequences == []
        assert writer.state.init_sequence is None
        assert fd._hook_progress.call_args_list[-1].args[0]['status'] == 'finished'

    def test_fail_writing_final_file(self, fd, filename, info_dict, format_id, format_selector):
        # Should not remove state file if writing the final file fails.
        fd._hook_progress = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1))

        original_try_rename = fd.try_rename
        fd.try_rename = MagicMock(side_effect=OSError('rename failed'))

        with pytest.raises(OSError, match='rename failed'):
            writer.finish()

        assert writer._sabr_state_file.exists is True
        assert Path(filename + '.sq1.part').exists() is True
        assert Path(filename + '.part').exists() is True

        # Should be able to recover if try finishing again
        fd.try_rename = original_try_rename
        writer.finish()

        assert Path(filename).read_bytes() == SEGMENT_ONE_DATA
        assert writer._sabr_state_file.exists is False
        assert Path(filename + '.sq1.part').exists() is False
        assert Path(filename + '.part').exists() is False

    def test_e2e_multiple_disjointed_sequence_files(self, fd, filename, info_dict, format_id, format_selector):
        fd._hook_progress = MagicMock()
        fd.report_warning = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
            total_segments=3,
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=3,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1, total_segments=3))

        # Segment 3 creates another sequence file (disjoint from sequence 1)
        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=3,
            start_time_ms=2000,
            duration_ms=1000,
            content_length=len(SEGMENT_THREE_DATA),
            total_segments=3,
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=3,
            total_segments=3,
            data=SEGMENT_THREE_DATA,
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=3, total_segments=3))

        assert sorted(sf.sequence_id for sf in writer.state.sequences) == ['1', '3']
        assert Path(filename + '.sq1.part').exists() is True
        assert Path(filename + '.sq3.part').exists() is True

        writer.finish()

        assert Path(filename).read_bytes() == SEGMENT_ONE_DATA + SEGMENT_THREE_DATA
        fd.report_warning.assert_called_once()
        assert 'Missing segments detected in format 251: 2-3' in fd.report_warning.call_args.args[0]

    def test_sequence_file_not_found_write(self, fd, filename, info_dict, format_id, format_selector):
        # Should raise an error if attempting to write segment data without initializing it first
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        with pytest.raises(DownloadError, match=r'Unable to find sequence file for segment. Was the segment initialized\?'):
            writer.write_segment_data(make_data_part(
                format_selector,
                format_id,
                sequence_number=1,
                data=io.BytesIO(SEGMENT_ONE_DATA),
            ))

        writer.close()

    def test_sequence_file_not_found_end(self, fd, filename, info_dict, format_id, format_selector):
        # Should raise an error if attempting to end a segment without initializing it first
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        with pytest.raises(DownloadError, match=r'Unable to find sequence file for segment. Was the segment initialized\?'):
            writer.end_segment(make_end_part(
                format_selector,
                format_id,
                sequence_number=1,
            ))

        writer.close()

    def test_initialize_segment_without_initializing_format(self, fd, filename, info_dict, format_id, format_selector):
        # Should raise an error if attempting to initialize a segment without initializing the format first.
        writer = make_writer(fd, filename, info_dict)

        with pytest.raises(ValueError, match='not initialized'):
            writer.initialize_segment(make_init_part(
                format_selector,
                format_id,
                sequence_number=1,
            ))

        writer.close()

    def test_segment_in_multiple_sequence_files(self, fd, filename, info_dict, format_id, format_selector):
        # Should fail if a segment is found within multiple sequence files.
        # This should never happen, but if it does it should raise an error to avoid file corruption.
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        segment = Segment(
            segment_id='1',
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        )
        sequence_file_a = SequenceFile(fd=fd, format_filename=filename, sequence=Sequence(sequence_id='a'))
        sequence_file_a.initialize_segment(segment)
        sequence_file_b = SequenceFile(fd=fd, format_filename=filename, sequence=Sequence(sequence_id='b'))
        sequence_file_b.initialize_segment(segment)
        writer._sequence_files = [sequence_file_a, sequence_file_b]

        with pytest.raises(DownloadError, match='Multiple sequence files found for segment'):
            writer.write_segment_data(make_data_part(
                format_selector,
                format_id,
                sequence_number=1,
                data=io.BytesIO(SEGMENT_ONE_DATA),
            ))

        writer.close()

    def test_resume(self, fd, filename, info_dict, format_id):
        # setup resume data
        fd._hook_progress = MagicMock()
        init_segment = Segment(
            segment_id=INIT_SEGMENT_ID,
            content_length=len(INIT_DATA),
            is_init_segment=True,
        )
        media_segment = Segment(
            segment_id='1',
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        )
        write_sequence_file(fd, filename, Sequence(sequence_id=INIT_SEGMENT_ID), init_segment, INIT_DATA)
        write_sequence_file(fd, filename, Sequence(sequence_id='1'), media_segment, SEGMENT_ONE_DATA)

        SabrStateFile(filename, fd).update(SabrState(
            format_id=format_id,
            video_id=VIDEO_ID,
            init_segment=SabrStateInitSegment(content_length=len(INIT_DATA)),
            sequences=[
                SabrStateSequence(
                    sequence_start_number=1,
                    sequence_content_length=len(SEGMENT_ONE_DATA),
                    first_segments=[make_state_segment(media_segment)],
                    last_segments=[make_state_segment(media_segment)],
                ),
            ],
            broadcast_id=BROADCAST_ID_1,
        ))

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        assert writer.initialized is True
        state = writer.state
        assert state.format_id == format_id
        assert state.init_sequence is not None
        assert state.init_sequence.sequence_id == INIT_SEGMENT_ID
        assert len(state.sequences) == 1
        assert state.sequences[0].sequence_id == '1'
        assert [segment.sequence_number for segment in state.sequences[0].first_segments] == [1]
        assert [segment.sequence_number for segment in state.sequences[0].last_segments] == [1]
        assert writer.downloaded_bytes == len(INIT_DATA) + len(SEGMENT_ONE_DATA)

        writer.initialize_segment(make_init_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=2,
            start_time_ms=1000,
            duration_ms=1000,
            content_length=len(SEGMENT_TWO_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=2,
            total_segments=2,
            data=io.BytesIO(SEGMENT_TWO_DATA),
        ))
        writer.end_segment(make_end_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=2,
            total_segments=2,
        ))

        resumed_state = writer.state
        assert len(resumed_state.sequences) == 1
        assert [segment.sequence_number for segment in resumed_state.sequences[0].first_segments] == [1, 2]
        assert [segment.sequence_number for segment in resumed_state.sequences[0].last_segments] == [1, 2]
        assert resumed_state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA) + len(SEGMENT_TWO_DATA)

        persisted_state = SabrStateFile(filename, fd).retrieve()
        assert len(persisted_state.sequences) == 1
        assert [segment.sequence_number for segment in persisted_state.sequences[0].first_segments] == [1, 2]
        assert [segment.sequence_number for segment in persisted_state.sequences[0].last_segments] == [1, 2]
        assert persisted_state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA) + len(SEGMENT_TWO_DATA)

        writer.finish()

        assert Path(filename).read_bytes() == INIT_DATA + SEGMENT_ONE_DATA + SEGMENT_TWO_DATA
        assert writer._sabr_state_file.exists is False

    def test_resume_format_id_mismatch(self, fd, filename, info_dict, format_id):
        SabrStateFile(filename, fd).update(SabrState(
            format_id=FormatId(itag=140),
            broadcast_id=BROADCAST_ID_1,
            video_id=VIDEO_ID,
            init_segment=SabrStateInitSegment(content_length=len(INIT_DATA)),
        ))
        fd.report_warning = MagicMock()

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        state = writer.state
        assert state.format_id == format_id
        assert state.init_sequence is None
        assert len(state.sequences) == 0
        fd.report_warning.assert_called_once()
        assert 'Format ID mismatch in state file' in fd.report_warning.call_args.args[0]

        writer.initialize_segment(make_init_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
        ))

        reloaded_state = SabrStateFile(filename, fd).retrieve()
        assert reloaded_state.format_id == format_id
        assert reloaded_state.broadcast_id == BROADCAST_ID_1
        assert len(reloaded_state.sequences) == 1

        writer.close()

    def test_resume_broadcast_id_mismatch(self, fd, filename, info_dict, format_id):
        SabrStateFile(filename, fd).update(SabrState(
            format_id=format_id,
            broadcast_id=BROADCAST_ID_2,
            video_id=VIDEO_ID,
            init_segment=SabrStateInitSegment(content_length=len(INIT_DATA)),
        ))
        fd.report_warning = MagicMock()

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        state = writer.state
        assert state.format_id == format_id
        assert state.init_sequence is None
        assert len(state.sequences) == 0
        fd.report_warning.assert_called_once()
        assert 'Broadcast ID mismatch in state file' in fd.report_warning.call_args.args[0]

        writer.initialize_segment(make_init_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
        ))

        reloaded_state = SabrStateFile(filename, fd).retrieve()
        assert reloaded_state.format_id == format_id
        assert reloaded_state.broadcast_id == BROADCAST_ID_1
        assert len(reloaded_state.sequences) == 1

        writer.close()

    def test_resume_video_id_mismatch(self, fd, filename, info_dict, format_id):
        SabrStateFile(filename, fd).update(SabrState(
            format_id=format_id,
            broadcast_id=BROADCAST_ID_1,
            video_id=VIDEO_ID_2,
            init_segment=SabrStateInitSegment(content_length=len(INIT_DATA)),
        ))
        fd.report_warning = MagicMock()

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        state = writer.state
        assert state.format_id == format_id
        assert state.init_sequence is None
        assert len(state.sequences) == 0
        fd.report_warning.assert_called_once()
        assert 'Video ID mismatch in state file' in fd.report_warning.call_args.args[0]

        writer.initialize_segment(make_init_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
        ))

        reloaded_state = SabrStateFile(filename, fd).retrieve()
        assert reloaded_state.format_id == format_id
        assert reloaded_state.video_id == VIDEO_ID
        assert len(reloaded_state.sequences) == 1

        writer.close()

    def test_resume_corrupted_state(self, fd, filename, info_dict, format_id):
        Path(filename + '.state').write_bytes(b'invalid-state')
        fd.report_warning = MagicMock()

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        assert writer.state.format_id == format_id
        assert writer.state.init_sequence is None
        assert writer.state.sequences == []
        fd.report_warning.assert_called_once()
        assert 'Corrupted state file for format' in fd.report_warning.call_args.args[0]

        writer.initialize_segment(make_init_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(
            format_selector=AudioSelector(display_name='audio', format_ids=[format_id]),
            format_id=format_id,
            sequence_number=1,
        ))

        reloaded_state = SabrStateFile(filename, fd).retrieve()
        assert reloaded_state.format_id == format_id
        assert reloaded_state.broadcast_id == BROADCAST_ID_1
        assert len(reloaded_state.sequences) == 1
        writer.close()

    def test_progress_reporting(self, fd, filename, info_dict, format_id, format_selector):
        fd._hook_progress = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=3,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))

        progress_state, progress_info = fd._hook_progress.call_args.args
        assert progress_info == info_dict
        assert progress_state['status'] == 'downloading'
        assert progress_state['downloaded_bytes'] == len(SEGMENT_ONE_DATA)
        assert progress_state['total_bytes'] == info_dict['filesize']
        assert progress_state['filename'] == filename
        assert progress_state['fragment_count'] == 3
        assert progress_state['fragment_index'] == 1

        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1, total_segments=3))

        state = writer.state
        assert state.format_id == format_id
        assert state.init_sequence is None
        assert len(state.sequences) == 1
        assert state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA)
        assert state.sequences[0].first_segment.sequence_number == 1
        assert state.sequences[0].last_segment.sequence_number == 1

        writer.close()

    def test_initialize_format_twice_error(self, fd, filename, info_dict, format_id):
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        with pytest.raises(ValueError, match='Already initialized'):
            writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.close()

    def test_remove_existing_state_not_resuming(self, fd, filename, info_dict, format_id):
        # Should remove existing state file when not resuming
        sabr_state_file = SabrStateFile(filename, fd)
        sabr_state_file.update(SabrState(format_id=format_id, broadcast_id=BROADCAST_ID_1, video_id=VIDEO_ID))
        assert sabr_state_file.exists is True

        writer = make_writer(fd, filename, info_dict, resume=False)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        assert sabr_state_file.exists is False
        writer.close()

    def test_initialize_format_ignores_init_resume_error(self, fd, filename, info_dict, format_id):
        # Should warn and continue if fail to resume init sequence

        # init sequence without an associated file
        SabrStateFile(filename, fd).update(SabrState(
            format_id=format_id,
            broadcast_id=BROADCAST_ID_1,
            video_id=VIDEO_ID,
            init_segment=SabrStateInitSegment(content_length=len(INIT_DATA)),
        ))
        fd.report_warning = MagicMock()

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        assert writer.state.init_sequence is None
        assert writer.state.sequences == []
        fd.report_warning.assert_called_once()
        assert 'Failed to resume init segment' in fd.report_warning.call_args.args[0]
        writer.close()

    def test_initialize_format_ignores_sequence_resume_error(self, fd, filename, info_dict, format_id):
        # Should warn and continue if fail to resume a sequence

        # sequence without an associated file
        media_segment = Segment(
            segment_id='1',
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        )
        SabrStateFile(filename, fd).update(SabrState(
            format_id=format_id,
            broadcast_id=BROADCAST_ID_1,
            video_id=VIDEO_ID,
            sequences=[
                SabrStateSequence(
                    sequence_start_number=1,
                    sequence_content_length=len(SEGMENT_ONE_DATA),
                    first_segments=[make_state_segment(media_segment)],
                    last_segments=[make_state_segment(media_segment)],
                ),
            ],
        ))
        fd.report_warning = MagicMock()

        writer = make_writer(fd, filename, info_dict, resume=True)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        assert writer.state.init_sequence is None
        assert writer.state.sequences == []
        fd.report_warning.assert_called_once()
        assert 'Failed to resume sequence 1' in fd.report_warning.call_args.args[0]
        writer.close()

    def test_close_ignores_already_closed(self, fd, filename, info_dict):
        writer = make_writer(fd, filename, info_dict)
        writer.close()
        writer.close()

    def test_write_state_ignores_partial_sequences(self, fd, filename, info_dict, format_id, format_selector):
        # should not write partial sequences to the state file
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        # complete sequence
        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=10,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=10,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=10))

        # partial sequence
        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=12,
            start_time_ms=2000,
            duration_ms=1000,
            content_length=len(SEGMENT_TWO_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=12,
            data=io.BytesIO(SEGMENT_TWO_DATA[:4]),
        ))

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=14,
            start_time_ms=4000,
            duration_ms=1000,
            content_length=len(SEGMENT_THREE_DATA),
        ))

        assert sorted(sf.sequence_id for sf in writer.state.sequences) == ['10', '12', '14']
        partial_sequences = [sf for sf in writer.state.sequences if sf.sequence_id in ['12', '14']]
        assert all(sequence.first_segment is None for sequence in partial_sequences)
        assert all(sequence.last_segment is None for sequence in partial_sequences)

        writer._write_sabr_state()
        state = SabrStateFile(filename, fd).retrieve()

        # Should not have any of the partial sequences
        assert state.broadcast_id == BROADCAST_ID_1
        assert len(state.sequences) == 1
        assert state.sequences[0].sequence_start_number == 10
        assert state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA)
        writer.close()

    def test_reinitialize_incomplete_segment(self, fd, filename, info_dict, format_id, format_selector):
        # Should handle reinitializing a segment that was partially written
        # This can occur if SabrStream retries during segment read
        fd._hook_progress = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=1,
            data=io.BytesIO(SEGMENT_ONE_DATA[:4]),
        ))

        assert writer.downloaded_bytes == 4
        assert len(writer.state.sequences) == 1
        assert writer.state.sequences[0].first_segment is None
        assert writer.state.sequences[0].last_segment is None

        # reinitializing should discard the incomplete segment
        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        ))

        assert writer.downloaded_bytes == 0
        assert writer.state.sequences[0].first_segment is None
        assert writer.state.sequences[0].last_segment is None

        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1, total_segments=1))

        state = writer.state
        assert len(state.sequences) == 1
        assert state.sequences[0].sequence_id == '1'
        assert state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA)
        assert state.sequences[0].first_segment.sequence_number == 1
        assert state.sequences[0].last_segment.sequence_number == 1

        persisted_state = SabrStateFile(filename, fd).retrieve()
        assert len(persisted_state.sequences) == 1
        assert persisted_state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA)

        writer.finish()

        assert Path(filename).read_bytes() == SEGMENT_ONE_DATA

    def test_reinitialize_complete_segment(self, fd, filename, info_dict, format_id, format_selector):
        # Should fail if a completed segment is initialized again.
        fd._hook_progress = MagicMock()
        writer = make_writer(fd, filename, info_dict)
        writer.initialize_format(format_id, broadcast_id=BROADCAST_ID_1)

        writer.initialize_segment(make_init_part(
            format_selector,
            format_id,
            sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
            content_length=len(SEGMENT_ONE_DATA),
        ))
        writer.write_segment_data(make_data_part(
            format_selector,
            format_id,
            sequence_number=1,
            total_segments=1,
            data=io.BytesIO(SEGMENT_ONE_DATA),
        ))
        writer.end_segment(make_end_part(format_selector, format_id, sequence_number=1, total_segments=1))

        initial_state = writer.state
        assert len(initial_state.sequences) == 1
        assert initial_state.sequences[0].sequence_id == '1'
        assert initial_state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA)

        with pytest.raises(DownloadError, match='Cannot reinitialize completed segment 1'):
            writer.initialize_segment(make_init_part(
                format_selector,
                format_id,
                sequence_number=1,
                start_time_ms=0,
                duration_ms=1000,
                content_length=len(SEGMENT_ONE_DATA),
            ))

        assert len(writer.state.sequences) == 1
        assert writer.state.sequences[0].sequence_id == '1'
        assert writer.state.sequences[0].sequence_content_length == len(SEGMENT_ONE_DATA)

        persisted_state = SabrStateFile(filename, fd).retrieve()
        assert len(persisted_state.sequences) == 1
        assert [sequence.sequence_start_number for sequence in persisted_state.sequences] == [1]
        assert [sequence.sequence_content_length for sequence in persisted_state.sequences] == [len(SEGMENT_ONE_DATA)]

        writer.finish()

        assert Path(filename).read_bytes() == SEGMENT_ONE_DATA

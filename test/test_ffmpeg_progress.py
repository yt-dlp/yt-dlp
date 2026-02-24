#!/usr/bin/env python3

# Allow direct execution
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.postprocessor.ffmpeg import FFmpegProgressTracker


class TestProgressPattern(unittest.TestCase):
    """Test _progress_pattern regex against various ffmpeg -progress outputs"""

    def _match(self, text):
        return re.match(FFmpegProgressTracker._progress_pattern, text)

    def test_single_video_stream(self):
        output = (
            'frame=  120\n'
            'fps=30.00\n'
            'stream_0_0_q=28.0\n'
            'bitrate= 512.0kbits/s\n'
            'total_size=  131072\n'
            'out_time_us=4000000\n'
            'out_time_ms=4000000\n'
            'out_time=00:00:04.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=2.00x\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m)
        self.assertEqual(m.group('frame'), '120')
        self.assertEqual(m.group('fps'), '30.00')
        self.assertEqual(m.group('bitrate'), '512.0kbits/s')
        self.assertEqual(m.group('total_size'), '131072')
        self.assertEqual(m.group('out_time_us'), '4000000')
        self.assertEqual(m.group('speed'), '2.00x')
        self.assertEqual(m.group('progress'), 'continue')

    def test_two_streams_video_audio(self):
        output = (
            'frame=  240\n'
            'fps=24.00\n'
            'stream_0_0_q=28.0\n'
            'stream_0_1_q=-1.0\n'
            'bitrate= 1024.5kbits/s\n'
            'total_size=  262144\n'
            'out_time_us=10000000\n'
            'out_time_ms=10000000\n'
            'out_time=00:00:10.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=1.50x\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m, 'Regex must match 2-stream output')
        self.assertEqual(m.group('frame'), '240')
        self.assertEqual(m.group('bitrate'), '1024.5kbits/s')

    def test_three_streams(self):
        output = (
            'frame=  100\n'
            'fps=25.00\n'
            'stream_0_0_q=23.0\n'
            'stream_0_1_q=-1.0\n'
            'stream_0_2_q=-1.0\n'
            'bitrate= 2048.0kbits/s\n'
            'total_size=  524288\n'
            'out_time_us=4000000\n'
            'out_time_ms=4000000\n'
            'out_time=00:00:04.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=1.00x\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m, 'Regex must match 3-stream output')

    def test_audio_only_no_frame(self):
        """Audio-only encoding: no frame/fps/stream lines"""
        output = (
            'bitrate= 128.0kbits/s\n'
            'total_size=  65536\n'
            'out_time_us=4000000\n'
            'out_time_ms=4000000\n'
            'out_time=00:00:04.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=5.00x\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m, 'Regex must match audio-only output (no frame/fps/stream)')
        self.assertIsNone(m.group('frame'))
        self.assertEqual(m.group('bitrate'), '128.0kbits/s')
        self.assertEqual(m.group('speed'), '5.00x')

    def test_progress_end(self):
        output = (
            'bitrate=N/A\n'
            'total_size=  1048576\n'
            'out_time_us=60000000\n'
            'out_time_ms=60000000\n'
            'out_time=00:01:00.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=N/A\n'
            'progress=end'
        )
        m = self._match(output)
        self.assertIsNotNone(m)
        self.assertEqual(m.group('progress'), 'end')
        self.assertEqual(m.group('bitrate'), 'N/A')
        self.assertEqual(m.group('speed'), 'N/A')

    def test_na_values_at_start(self):
        """ffmpeg outputs N/A for bitrate and speed at the very beginning"""
        output = (
            'frame=    1\n'
            'fps=0.00\n'
            'stream_0_0_q=0.0\n'
            'bitrate=N/A\n'
            'total_size=       0\n'
            'out_time_us=0\n'
            'out_time_ms=0\n'
            'out_time=00:00:00.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=N/A\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m)
        self.assertEqual(m.group('bitrate'), 'N/A')
        self.assertEqual(m.group('speed'), 'N/A')
        self.assertEqual(m.group('total_size'), '0')

    def test_no_match_on_partial_output(self):
        """Partial progress block should NOT match"""
        partial = (
            'frame=  120\n'
            'fps=30.00\n'
            'stream_0_0_q=28.0\n'
            'bitrate= 512.0kbits/s\n'
        )
        m = self._match(partial)
        self.assertIsNone(m)

    def test_no_match_on_empty(self):
        self.assertIsNone(self._match(''))

    def test_large_stream_indices(self):
        """Stream indices can be large numbers"""
        output = (
            'frame=  100\n'
            'fps=25.00\n'
            'stream_0_10_q=23.0\n'
            'stream_0_11_q=-1.0\n'
            'bitrate= 1024.0kbits/s\n'
            'total_size=  262144\n'
            'out_time_us=4000000\n'
            'out_time_ms=4000000\n'
            'out_time=00:00:04.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=1.00x\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m, 'Must handle large stream indices')

    def test_negative_q_values(self):
        """Audio streams typically have q=-1.0"""
        output = (
            'frame=  100\n'
            'fps=25.00\n'
            'stream_0_0_q=-1.0\n'
            'bitrate= 128.0kbits/s\n'
            'total_size=  65536\n'
            'out_time_us=4000000\n'
            'out_time_ms=4000000\n'
            'out_time=00:00:04.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=3.00x\n'
            'progress=continue'
        )
        m = self._match(output)
        self.assertIsNotNone(m)


class TestTimeStringToSeconds(unittest.TestCase):
    """Test ffmpeg_time_string_to_seconds with all ffmpeg time formats"""

    def test_seconds_only(self):
        self.assertEqual(FFmpegProgressTracker.ffmpeg_time_string_to_seconds('42'), 42)

    def test_seconds_float(self):
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('42.5'), 42.5)

    def test_hour_seconds_two_components(self):
        """With 2 components (H:S), ffmpeg parses as hours:seconds"""
        self.assertEqual(FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1:30'), 3630)

    def test_hours_minutes_seconds(self):
        self.assertEqual(FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1:30:00'), 5400)

    def test_hms_with_float(self):
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1:02:03.456'), 3723.456)

    def test_zero(self):
        self.assertEqual(FFmpegProgressTracker.ffmpeg_time_string_to_seconds('0'), 0)

    def test_milliseconds_unit(self):
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1500ms'), 1.5)

    def test_microseconds_unit(self):
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1500000us'), 1.5)

    def test_seconds_unit(self):
        self.assertEqual(FFmpegProgressTracker.ffmpeg_time_string_to_seconds('30s'), 30)

    def test_milliseconds_zero(self):
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('0ms'), 0)

    def test_large_hms(self):
        self.assertEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('10:00:00'), 36000)

    def test_fractional_seconds(self):
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('0.001'), 0.001)

    def test_single_digit_components(self):
        self.assertEqual(FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1:2:3'), 3723)

    def test_ms_does_not_match_as_hms(self):
        """100ms should be 0.1 seconds, NOT 100 seconds"""
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('100ms'), 0.1)

    def test_us_does_not_match_as_hms(self):
        """1000000us should be 1 second, NOT 1000000 seconds"""
        self.assertAlmostEqual(
            FFmpegProgressTracker.ffmpeg_time_string_to_seconds('1000000us'), 1.0)


class TestComputeDurationToTrack(unittest.TestCase):
    """Test _compute_duration_to_track with various ffmpeg arg combinations"""

    def _make_tracker(self, args, duration=100):
        info_dict = {'duration': duration} if duration else {}
        tracker = FFmpegProgressTracker(info_dict, args, lambda s, i: None)
        return tracker

    def test_no_seek_args(self):
        tracker = self._make_tracker(['ffmpeg', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (100, 100))

    def test_ss_only(self):
        tracker = self._make_tracker(['ffmpeg', '-ss', '10', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (90, 100))

    def test_to_only(self):
        tracker = self._make_tracker(['ffmpeg', '-to', '50', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (50, 100))

    def test_ss_and_to(self):
        tracker = self._make_tracker(['ffmpeg', '-ss', '10', '-to', '50', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (40, 100))

    def test_t_duration(self):
        """ffmpeg -t specifies explicit duration, not end time"""
        tracker = self._make_tracker(['ffmpeg', '-ss', '10', '-t', '30', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (30, 100))

    def test_t_alone(self):
        tracker = self._make_tracker(['ffmpeg', '-t', '45', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (45, 100))

    def test_sseof(self):
        tracker = self._make_tracker(['ffmpeg', '-sseof', '30', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (30, 100))

    def test_equals_form(self):
        """ffmpeg accepts -ss=10 as well as -ss 10"""
        tracker = self._make_tracker(['ffmpeg', '-ss=10', '-to=50', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (40, 100))

    def test_t_equals_form(self):
        tracker = self._make_tracker(['ffmpeg', '-t=30', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (30, 100))

    def test_no_duration_in_info(self):
        tracker = self._make_tracker(['ffmpeg', '-i', 'in.mp4', 'out.mp4'], duration=None)
        self.assertEqual(tracker._compute_duration_to_track(), (0, 0))

    def test_negative_duration_returns_zero(self):
        """If -to < -ss, duration_to_track should be 0"""
        tracker = self._make_tracker(['ffmpeg', '-ss', '50', '-to', '10', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (0, 100))

    def test_hms_timestamps(self):
        tracker = self._make_tracker(
            ['ffmpeg', '-ss', '0:01:00', '-to', '0:02:00', '-i', 'in.mp4', 'out.mp4'],
            duration=300)
        self.assertEqual(tracker._compute_duration_to_track(), (60, 300))

    def test_does_not_match_similar_args(self):
        """Args like -ssa or -strict should NOT be treated as -ss"""
        tracker = self._make_tracker(
            ['ffmpeg', '-ssa', '10', '-strict', '-2', '-i', 'in.mp4', 'out.mp4'])
        # Should return full duration since no seek args
        self.assertEqual(tracker._compute_duration_to_track(), (100, 100))

    def test_t_takes_precedence_over_to(self):
        """-t explicitly sets duration regardless of -to"""
        tracker = self._make_tracker(
            ['ffmpeg', '-ss', '10', '-t', '20', '-to', '90', '-i', 'in.mp4', 'out.mp4'])
        self.assertEqual(tracker._compute_duration_to_track(), (20, 100))


class TestComputeBitrate(unittest.TestCase):
    """Test _compute_bitrate with various ffmpeg bitrate formats"""

    def test_kbits(self):
        self.assertAlmostEqual(FFmpegProgressTracker._compute_bitrate('512.0kbits/s'), 512000.0)

    def test_mbits(self):
        self.assertAlmostEqual(FFmpegProgressTracker._compute_bitrate('2.5mbits/s'), 2500000.0)

    def test_gbits(self):
        self.assertAlmostEqual(FFmpegProgressTracker._compute_bitrate('1.0gbits/s'), 1000000000.0)

    def test_no_prefix(self):
        self.assertEqual(FFmpegProgressTracker._compute_bitrate('128000bits/s'), 128000)

    def test_integer_kbits(self):
        self.assertEqual(FFmpegProgressTracker._compute_bitrate('256kbits/s'), 256000)

    def test_na_returns_zero(self):
        self.assertEqual(FFmpegProgressTracker._compute_bitrate('N/A'), 0)

    def test_empty_returns_zero(self):
        self.assertEqual(FFmpegProgressTracker._compute_bitrate(''), 0)

    def test_float_precision(self):
        result = FFmpegProgressTracker._compute_bitrate('1234.56kbits/s')
        self.assertAlmostEqual(result, 1234560.0, places=0)


class TestComputeEta(unittest.TestCase):
    """Test _compute_eta with various speed and progress scenarios"""

    def _make_match(self, speed='2.00x', out_time_us='30000000'):
        text = (
            'bitrate= 512.0kbits/s\n'
            'total_size=  131072\n'
            f'out_time_us={out_time_us}\n'
            'out_time_ms=0\n'
            'out_time=00:00:00.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            f'speed={speed}\n'
            'progress=continue'
        )
        return re.match(FFmpegProgressTracker._progress_pattern, text)

    def test_normal_eta(self):
        m = self._make_match(speed='2.00x', out_time_us='30000000')
        # duration=60, out_time=30s, speed=2x => ETA = (60-30)/2 = 15
        eta = FFmpegProgressTracker._compute_eta(m, 60)
        self.assertEqual(eta, 15)

    def test_speed_1x(self):
        m = self._make_match(speed='1.00x', out_time_us='30000000')
        eta = FFmpegProgressTracker._compute_eta(m, 60)
        self.assertEqual(eta, 30)

    def test_na_speed_returns_none(self):
        m = self._make_match(speed='N/A', out_time_us='0')
        eta = FFmpegProgressTracker._compute_eta(m, 60)
        self.assertIsNone(eta)

    def test_zero_speed_returns_none(self):
        m = self._make_match(speed='0.00x', out_time_us='0')
        eta = FFmpegProgressTracker._compute_eta(m, 60)
        self.assertIsNone(eta)

    def test_zero_duration_returns_zero(self):
        m = self._make_match(speed='2.00x', out_time_us='0')
        eta = FFmpegProgressTracker._compute_eta(m, 0)
        self.assertEqual(eta, 0)

    def test_very_fast_speed(self):
        m = self._make_match(speed='100.0x', out_time_us='0')
        eta = FFmpegProgressTracker._compute_eta(m, 60)
        self.assertEqual(eta, 0)  # 60/100 rounds down to 0


class TestComputeTotalFilesize(unittest.TestCase):
    """Test _compute_total_filesize edge cases"""

    def _make_tracker(self, filesize=None, filesize_approx=None):
        info_dict = {}
        if filesize is not None:
            info_dict['filesize'] = filesize
        if filesize_approx is not None:
            info_dict['filesize_approx'] = filesize_approx
        return FFmpegProgressTracker(info_dict, [], lambda s, i: None)

    def test_with_filesize(self):
        tracker = self._make_tracker(filesize=1000)
        self.assertEqual(tracker._compute_total_filesize(50, 100), 500)

    def test_with_filesize_approx(self):
        tracker = self._make_tracker(filesize_approx=1000)
        self.assertEqual(tracker._compute_total_filesize(50, 100), 500)

    def test_filesize_preferred_over_approx(self):
        tracker = self._make_tracker(filesize=2000, filesize_approx=1000)
        self.assertEqual(tracker._compute_total_filesize(50, 100), 1000)

    def test_zero_duration_returns_zero(self):
        tracker = self._make_tracker(filesize=1000)
        self.assertEqual(tracker._compute_total_filesize(0, 0), 0)

    def test_no_filesize_returns_zero(self):
        tracker = self._make_tracker()
        self.assertEqual(tracker._compute_total_filesize(50, 100), 0)

    def test_full_duration(self):
        tracker = self._make_tracker(filesize=1000)
        self.assertEqual(tracker._compute_total_filesize(100, 100), 1000)


class TestTrackerInit(unittest.TestCase):
    """Test FFmpegProgressTracker construction and status initialization"""

    def test_init_status_has_required_keys(self):
        tracker = FFmpegProgressTracker({}, [], lambda s, i: None)
        self.assertIn('filename', tracker._status)
        self.assertIn('status', tracker._status)
        self.assertIn('elapsed', tracker._status)
        self.assertIn('outputted', tracker._status)
        self.assertEqual(tracker._status['status'], 'ffmpeg_running')

    def test_init_with_output_filename(self):
        tracker = FFmpegProgressTracker(
            {}, [], lambda s, i: None, output_filename='/tmp/out.mp4')
        self.assertEqual(tracker._status['filename'], '/tmp/out.mp4')

    def test_init_without_output_filename(self):
        tracker = FFmpegProgressTracker({}, [], lambda s, i: None)
        self.assertEqual(tracker._status['filename'], '')

    def test_proc_is_none_before_start(self):
        tracker = FFmpegProgressTracker({}, [], lambda s, i: None)
        self.assertIsNone(tracker.ffmpeg_proc)

    def test_trigger_progress_hook_works_immediately(self):
        """trigger_progress_hook should work even before start()"""
        received = []
        tracker = FFmpegProgressTracker(
            {'id': 'test'}, [], lambda s, i: received.append(s.copy()))
        tracker.trigger_progress_hook({'custom_key': 'value'})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['custom_key'], 'value')
        self.assertEqual(received[0]['status'], 'ffmpeg_running')

    def test_env_and_stdin_stored(self):
        import subprocess
        env = {'HTTP_PROXY': 'http://proxy:8080'}
        tracker = FFmpegProgressTracker(
            {}, [], lambda s, i: None,
            env=env, stdin=subprocess.PIPE)
        self.assertEqual(tracker._env, env)
        self.assertEqual(tracker._stdin, subprocess.PIPE)


class TestTrackerStreams(unittest.TestCase):
    """Test _save_stream correctly separates stdout and stderr"""

    def _make_tracker(self):
        return FFmpegProgressTracker({}, [], lambda s, i: None)

    def test_save_stdout(self):
        tracker = self._make_tracker()
        tracker._save_stream('hello\n', to_stderr=False)
        self.assertEqual(tracker._stdout_data, 'hello\n')
        self.assertEqual(tracker._stderr_data, '')

    def test_save_stderr(self):
        tracker = self._make_tracker()
        tracker._save_stream('error\n', to_stderr=True)
        self.assertEqual(tracker._stderr_data, 'error\n')
        self.assertEqual(tracker._stdout_data, '')

    def test_accumulation(self):
        tracker = self._make_tracker()
        tracker._save_stream('line1\n', to_stderr=False)
        tracker._save_stream('line2\n', to_stderr=False)
        self.assertEqual(tracker._stdout_data, 'line1\nline2\n')

    def test_empty_lines_ignored(self):
        tracker = self._make_tracker()
        tracker._save_stream('', to_stderr=False)
        self.assertEqual(tracker._stdout_data, '')


class TestParseFFmpegOutput(unittest.TestCase):
    """Test _parse_ffmpeg_output status updates"""

    def _make_tracker(self, duration=100, filesize=1000):
        info_dict = {'duration': duration, 'filesize': filesize}
        tracker = FFmpegProgressTracker(info_dict, ['ffmpeg', '-i', 'in.mp4', 'out.mp4'], lambda s, i: None)
        tracker._duration_to_track = duration
        tracker._total_duration = duration
        tracker._total_filesize = filesize
        return tracker

    def test_full_progress_block_updates_status(self):
        tracker = self._make_tracker()
        tracker._stdout_buffer = (
            'frame=  120\n'
            'fps=30.00\n'
            'stream_0_0_q=28.0\n'
            'bitrate= 512.0kbits/s\n'
            'total_size=  131072\n'
            'out_time_us=50000000\n'
            'out_time_ms=50000000\n'
            'out_time=00:00:50.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=2.00x\n'
            'progress=continue'
        )
        tracker._parse_ffmpeg_output()
        self.assertGreater(tracker._status['outputted'], 0)
        self.assertIn('speed', tracker._status)
        self.assertIn('eta', tracker._status)
        # Buffer should be cleared after successful parse
        self.assertEqual(tracker._stdout_buffer, '')

    def test_partial_block_does_not_clear_buffer(self):
        tracker = self._make_tracker()
        tracker._stdout_buffer = 'frame=  120\nfps=30.00\n'
        tracker._parse_ffmpeg_output()
        # Buffer should not be cleared since regex didn't match
        self.assertEqual(tracker._stdout_buffer, 'frame=  120\nfps=30.00\n')

    def test_na_bitrate_gives_zero_speed(self):
        tracker = self._make_tracker()
        tracker._stdout_buffer = (
            'bitrate=N/A\n'
            'total_size=       0\n'
            'out_time_us=0\n'
            'out_time_ms=0\n'
            'out_time=00:00:00.000000\n'
            'dup_frames=0\n'
            'drop_frames=0\n'
            'speed=N/A\n'
            'progress=continue'
        )
        tracker._parse_ffmpeg_output()
        self.assertEqual(tracker._status['speed'], 0)


class TestHandleLines(unittest.TestCase):
    """Test _handle_lines drains both queues"""

    def _make_tracker(self, duration=100, filesize=1000):
        info_dict = {'duration': duration, 'filesize': filesize}
        tracker = FFmpegProgressTracker(info_dict, ['ffmpeg', '-i', 'in.mp4', 'out.mp4'], lambda s, i: None)
        tracker._duration_to_track = duration
        tracker._total_duration = duration
        tracker._total_filesize = filesize
        return tracker

    def test_drains_stdout_queue(self):
        tracker = self._make_tracker()
        tracker._stdout_queue.put('frame=  120')
        tracker._stdout_queue.put('fps=30.00')
        tracker._handle_lines()
        self.assertTrue(tracker._stdout_queue.empty())
        self.assertIn('frame=  120', tracker._stdout_buffer)

    def test_drains_stderr_queue(self):
        tracker = self._make_tracker()
        tracker._stderr_queue.put('warning: something')
        tracker._handle_lines()
        self.assertTrue(tracker._stderr_queue.empty())
        self.assertIn('warning: something', tracker._stderr_data)

    def test_multiple_lines_in_queue(self):
        tracker = self._make_tracker()
        for i in range(10):
            tracker._stderr_queue.put(f'line {i}')
        tracker._handle_lines()
        self.assertTrue(tracker._stderr_queue.empty())
        for i in range(10):
            self.assertIn(f'line {i}', tracker._stderr_data)


class TestReportProgress(unittest.TestCase):
    """Test PostProcessor.report_progress display logic"""

    def _make_pp(self, params=None):
        from test.helper import FakeYDL
        from yt_dlp.postprocessor.common import PostProcessor
        with FakeYDL(params) as ydl:
            pp = PostProcessor(ydl)
        return pp

    def test_finished_without_data_is_silent(self):
        """Metaclass finished hook sends minimal dict - should not crash or display"""
        pp = self._make_pp()
        # Simulate what PostProcessorMetaClass.run_wrapper sends
        pp.report_progress({
            'status': 'finished',
            'info_dict': {'id': 'test'},
            'postprocessor': 'Test',
        })
        # Should return early without error (no total_bytes)

    def test_finished_with_data(self):
        """Finished with progress data should not crash"""
        pp = self._make_pp()
        pp.report_progress({
            'status': 'finished',
            'info_dict': {'id': 'test'},
            'postprocessor': 'Test',
            'total_bytes': 1000000,
            'elapsed': 10.0,
        })

    def test_started_is_ignored(self):
        """Started status should be silently ignored"""
        pp = self._make_pp()
        pp.report_progress({
            'status': 'started',
            'info_dict': {'id': 'test'},
            'postprocessor': 'Test',
        })

    def test_processing_with_all_fields(self):
        """Processing status with full data should not crash"""
        pp = self._make_pp()
        pp.report_progress({
            'status': 'processing',
            'info_dict': {'id': 'test'},
            'postprocessor': 'Test',
            'processed_bytes': 500000,
            'total_bytes': 1000000,
            'speed': 100000,
            'eta': 5,
            'elapsed': 5.0,
        })

    def test_processing_minimal_fields(self):
        """Processing status with minimal data should not crash"""
        pp = self._make_pp()
        pp.report_progress({
            'status': 'processing',
            'info_dict': {'id': 'test'},
            'postprocessor': 'Test',
        })

    def test_no_downloader_returns_early(self):
        """Without a downloader, report_progress should return immediately"""
        from yt_dlp.postprocessor.common import PostProcessor
        pp = PostProcessor.__new__(PostProcessor)
        pp._progress_hooks = []
        pp._downloader = None
        pp.PP_NAME = 'Test'
        pp._prepare_multiline_status()
        pp.report_progress({'status': 'processing'})

    def test_report_progress_status_without_info_dict(self):
        """_report_progress_status should not crash without info_dict"""
        pp = self._make_pp()
        pp.report_progress({
            'status': 'processing',
            'postprocessor': 'Test',
        })


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Tests for HLS downloader and HlsManifestParser."""
import http.server
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL, http_server_port, try_rm

from yt_dlp.utils import HlsManifestParser


class TestHlsManifestParser(unittest.TestCase):
    """Unit tests for HlsManifestParser class."""

    def test_basic_playlist(self):
        """Test parsing a simple HLS playlist."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:5.005,
segment100.ts
#EXTINF:6.006,
segment101.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.target_duration, 6.0)
        self.assertEqual(parser.media_sequence, 100)
        self.assertEqual(len(parser.segments), 2)
        self.assertEqual(parser.segments[0]['media_sequence'], 100)
        self.assertEqual(parser.segments[0]['duration'], 5.005)
        self.assertEqual(parser.segments[0]['url'], 'http://example.com/segment100.ts')
        self.assertEqual(parser.segments[1]['media_sequence'], 101)
        self.assertEqual(parser.segments[1]['duration'], 6.006)
        self.assertFalse(parser.is_endlist)

    def test_endlist_detection(self):
        """Test detection of EXT-X-ENDLIST tag."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:50
#EXTINF:10.0,
segment50.ts
#EXT-X-ENDLIST
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertTrue(parser.is_endlist)
        self.assertEqual(len(parser.segments), 1)

    def test_no_endlist_for_live(self):
        """Test that live streams don't have EXT-X-ENDLIST."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:4
#EXT-X-MEDIA-SEQUENCE:1000
#EXTINF:4.0,
segment1000.ts
#EXTINF:4.0,
segment1001.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertFalse(parser.is_endlist)
        self.assertEqual(parser.media_sequence, 1000)

    def test_encrypted_segments_aes128(self):
        """Test parsing AES-128 encrypted segments."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:50
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.bin",IV=0x00000000000000000000000000000001
#EXTINF:5.0,
segment50.ts
#EXTINF:5.0,
segment51.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(len(parser.segments), 2)
        self.assertEqual(parser.segments[0]['decrypt_info']['METHOD'], 'AES-128')
        self.assertEqual(parser.segments[0]['decrypt_info']['URI'], 'https://example.com/key.bin')
        self.assertIsNotNone(parser.segments[0]['decrypt_info']['IV'])
        # IV should be bytes
        self.assertIsInstance(parser.segments[0]['decrypt_info']['IV'], bytes)

    def test_key_rotation(self):
        """Test parsing playlist with key rotation."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:50
#EXT-X-KEY:METHOD=AES-128,URI="key1.bin"
#EXTINF:5.0,
segment50.ts
#EXT-X-KEY:METHOD=AES-128,URI="key2.bin"
#EXTINF:5.0,
segment51.ts
#EXT-X-KEY:METHOD=NONE
#EXTINF:5.0,
segment52.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(len(parser.segments), 3)
        self.assertEqual(parser.segments[0]['decrypt_info']['URI'], 'http://example.com/key1.bin')
        self.assertEqual(parser.segments[1]['decrypt_info']['URI'], 'http://example.com/key2.bin')
        self.assertEqual(parser.segments[2]['decrypt_info']['METHOD'], 'NONE')

    def test_byterange_segments(self):
        """Test parsing segments with byte ranges."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-BYTERANGE:1000@0
#EXTINF:5.0,
media.ts
#EXT-X-BYTERANGE:1000@1000
#EXTINF:5.0,
media.ts
#EXT-X-BYTERANGE:1000
#EXTINF:5.0,
media.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(len(parser.segments), 3)
        self.assertEqual(parser.segments[0]['byte_range'], {'start': 0, 'end': 1000})
        self.assertEqual(parser.segments[1]['byte_range'], {'start': 1000, 'end': 2000})
        # Third segment should continue from previous end
        self.assertEqual(parser.segments[2]['byte_range'], {'start': 2000, 'end': 3000})

    def test_init_segment_map(self):
        """Test parsing EXT-X-MAP initialization segment."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXT-X-MAP:URI="init.mp4"
#EXTINF:6.0,
segment100.m4s
#EXTINF:6.0,
segment101.m4s
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(len(parser.segments), 3)  # init + 2 segments
        self.assertTrue(parser.segments[0].get('is_init'))
        self.assertEqual(parser.segments[0]['url'], 'http://example.com/init.mp4')
        self.assertEqual(parser.segments[0]['media_sequence'], 99)  # Before first segment
        self.assertFalse(parser.segments[1].get('is_init'))
        self.assertEqual(parser.segments[1]['media_sequence'], 100)

    def test_init_segment_with_byterange(self):
        """Test parsing EXT-X-MAP with byte range."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-MAP:URI="media.mp4",BYTERANGE="500@0"
#EXTINF:6.0,
segment0.m4s
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(len(parser.segments), 2)
        self.assertTrue(parser.segments[0].get('is_init'))
        self.assertEqual(parser.segments[0]['byte_range'], {'start': 0, 'end': 500})

    def test_new_segments_since(self):
        """Test filtering segments by media sequence."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:5.0,
seg100.ts
#EXTINF:5.0,
seg101.ts
#EXTINF:5.0,
seg102.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        # Get segments after sequence 100
        new_segments = parser.get_new_segments_since(100)
        self.assertEqual(len(new_segments), 2)
        self.assertEqual(new_segments[0]['media_sequence'], 101)
        self.assertEqual(new_segments[1]['media_sequence'], 102)

        # Get segments after sequence 101
        new_segments = parser.get_new_segments_since(101)
        self.assertEqual(len(new_segments), 1)
        self.assertEqual(new_segments[0]['media_sequence'], 102)

        # Get segments after sequence 102 (none)
        new_segments = parser.get_new_segments_since(102)
        self.assertEqual(len(new_segments), 0)

    def test_new_segments_excludes_init(self):
        """Test that get_new_segments_since excludes init segments."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXT-X-MAP:URI="init.mp4"
#EXTINF:6.0,
seg100.m4s
#EXTINF:6.0,
seg101.m4s
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        new_segments = parser.get_new_segments_since(99)
        # Should get both media segments but not the init segment
        self.assertEqual(len(new_segments), 2)
        for seg in new_segments:
            self.assertFalse(seg.get('is_init'))

    def test_last_media_sequence(self):
        """Test last_media_sequence property."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:500
#EXTINF:5.0,
seg500.ts
#EXTINF:5.0,
seg501.ts
#EXTINF:5.0,
seg502.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.last_media_sequence, 502)

    def test_last_media_sequence_with_init(self):
        """Test last_media_sequence excludes init segment."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXT-X-MAP:URI="init.mp4"
#EXTINF:6.0,
seg100.m4s
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.last_media_sequence, 100)

    def test_extra_segment_query(self):
        """Test that extra query params are added to segment URLs."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:5.0,
segment.ts
'''
        parser = HlsManifestParser(
            manifest, 'http://example.com/',
            extra_segment_query={'token': ['abc123']})

        self.assertIn('token=abc123', parser.segments[0]['url'])

    def test_extra_key_query(self):
        """Test that extra query params are added to key URLs."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="key.bin"
#EXTINF:5.0,
segment.ts
'''
        parser = HlsManifestParser(
            manifest, 'http://example.com/',
            extra_key_query={'auth': ['secret']})

        self.assertIn('auth=secret', parser.segments[0]['decrypt_info']['URI'])

    def test_discontinuity_tracking(self):
        """Test tracking of discontinuity markers."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:5.0,
seg0.ts
#EXT-X-DISCONTINUITY
#EXTINF:5.0,
seg1.ts
#EXT-X-DISCONTINUITY
#EXTINF:5.0,
seg2.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.segments[0]['discontinuity_count'], 0)
        self.assertEqual(parser.segments[1]['discontinuity_count'], 1)
        self.assertEqual(parser.segments[2]['discontinuity_count'], 2)

    def test_relative_urls(self):
        """Test that relative URLs are resolved correctly."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:5.0,
segments/seg0.ts
#EXTINF:5.0,
../other/seg1.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/live/playlist.m3u8')

        self.assertEqual(parser.segments[0]['url'], 'http://example.com/live/segments/seg0.ts')
        self.assertEqual(parser.segments[1]['url'], 'http://example.com/other/seg1.ts')

    def test_absolute_urls(self):
        """Test that absolute URLs are preserved."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:5.0,
https://cdn.example.com/segment.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.segments[0]['url'], 'https://cdn.example.com/segment.ts')

    def test_empty_manifest(self):
        """Test parsing empty manifest."""
        manifest = '''\
#EXTM3U
#EXT-X-VERSION:3
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(len(parser.segments), 0)
        self.assertIsNone(parser.target_duration)
        self.assertEqual(parser.media_sequence, 0)
        self.assertFalse(parser.is_endlist)

    def test_extinf_title_ignored(self):
        """Test that EXTINF title component is ignored."""
        manifest = '''\
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.5,Segment Title Here
segment.ts
'''
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.segments[0]['duration'], 10.5)


class HlsLiveTestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that simulates an HLS live stream."""

    # Class-level state for simulating live stream
    _segment_counter = 100
    _lock = threading.Lock()
    _ended = False

    @classmethod
    def reset(cls, start_sequence=100, ended=False):
        """Reset the handler state for a new test."""
        with cls._lock:
            cls._segment_counter = start_sequence
            cls._ended = ended

    @classmethod
    def advance(cls, count=1):
        """Advance the stream by adding new segments."""
        with cls._lock:
            cls._segment_counter += count

    @classmethod
    def end_stream(cls):
        """Mark the stream as ended."""
        with cls._lock:
            cls._ended = True

    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        if self.path == '/live.m3u8':
            with self._lock:
                seq = self._segment_counter
                ended = self._ended

            manifest = f'''\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:2
#EXT-X-MEDIA-SEQUENCE:{seq}
#EXTINF:2.0,
segment{seq}.ts
#EXTINF:2.0,
segment{seq + 1}.ts
'''
            if ended:
                manifest += '#EXT-X-ENDLIST\n'

            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
            self.send_header('Content-Length', str(len(manifest)))
            self.end_headers()
            self.wfile.write(manifest.encode())

        elif self.path.startswith('/segment') and self.path.endswith('.ts'):
            # Serve a small fake segment
            content = b'\x00' * 1024
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        else:
            self.send_response(404)
            self.end_headers()


class TestHlsLiveDownloader(unittest.TestCase):
    """Integration tests for HLS live stream downloading."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = http.server.HTTPServer(('127.0.0.1', 0), HlsLiveTestHandler)
        cls.port = http_server_port(cls.httpd)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        HlsLiveTestHandler.reset()

    def test_live_generator_protocol_routing(self):
        """Test that m3u8_native_generator protocol routes to HlsFD."""
        from yt_dlp.downloader import get_suitable_downloader
        from yt_dlp.downloader.hls import HlsFD

        info_dict = {
            'url': f'http://127.0.0.1:{self.port}/live.m3u8',
            'protocol': 'm3u8_native_generator',
            'is_live': True,
        }
        downloader = get_suitable_downloader(info_dict, {})
        self.assertEqual(downloader, HlsFD)

    def test_live_manifest_polling_simulation(self):
        """Test that manifest is polled and new segments are detected."""
        url = f'http://127.0.0.1:{self.port}/live.m3u8'

        # First poll
        import urllib.request
        with urllib.request.urlopen(url) as response:
            manifest1 = response.read().decode()
        parser1 = HlsManifestParser(manifest1, url)

        initial_seq = parser1.last_media_sequence

        # Advance the stream
        HlsLiveTestHandler.advance(2)

        # Second poll
        with urllib.request.urlopen(url) as response:
            manifest2 = response.read().decode()
        parser2 = HlsManifestParser(manifest2, url)

        # Should have new segments
        new_segments = parser2.get_new_segments_since(initial_seq)
        self.assertEqual(len(new_segments), 2)

    def test_live_stream_end_detection(self):
        """Test that stream end is detected via EXT-X-ENDLIST."""
        url = f'http://127.0.0.1:{self.port}/live.m3u8'

        # First poll - stream not ended
        import urllib.request
        with urllib.request.urlopen(url) as response:
            manifest1 = response.read().decode()
        parser1 = HlsManifestParser(manifest1, url)
        self.assertFalse(parser1.is_endlist)

        # End the stream
        HlsLiveTestHandler.end_stream()

        # Second poll - stream ended
        with urllib.request.urlopen(url) as response:
            manifest2 = response.read().decode()
        parser2 = HlsManifestParser(manifest2, url)
        self.assertTrue(parser2.is_endlist)

    def test_vod_hls_unchanged(self):
        """Test that VOD HLS downloads are unaffected by live changes."""
        from yt_dlp.downloader import get_suitable_downloader
        from yt_dlp.downloader.hls import HlsFD

        # VOD with m3u8_native should still use HlsFD
        info_dict = {
            'url': 'http://example.com/vod.m3u8',
            'protocol': 'm3u8_native',
            'is_live': False,
        }
        downloader = get_suitable_downloader(info_dict, {})
        self.assertEqual(downloader, HlsFD)

    def test_live_without_generator_falls_back_to_ffmpeg(self):
        """Test that live HLS without generator protocol falls back to FFmpeg."""
        from yt_dlp.downloader import get_suitable_downloader
        from yt_dlp.downloader.external import FFmpegFD

        info_dict = {
            'url': 'http://example.com/live.m3u8',
            'protocol': 'm3u8_native',
            'is_live': True,
        }
        downloader = get_suitable_downloader(info_dict, {})
        self.assertEqual(downloader, FFmpegFD)

    def test_hls_native_live_option_routes_to_hlsfd(self):
        """Test that --hls-native-live routes live HLS to HlsFD."""
        from yt_dlp.downloader import get_suitable_downloader
        from yt_dlp.downloader.hls import HlsFD

        info_dict = {
            'url': 'http://example.com/live.m3u8',
            'protocol': 'm3u8_native',
            'is_live': True,
        }
        # With hls_native_live=True, should use HlsFD
        downloader = get_suitable_downloader(info_dict, {'hls_native_live': True})
        self.assertEqual(downloader, HlsFD)

    def test_hls_fd_creates_live_generator(self):
        """Test that HlsFD creates a fragment generator for live with --hls-native-live."""
        from yt_dlp.downloader.hls import HlsFD

        ydl = FakeYDL({'hls_native_live': True})
        fd = HlsFD(ydl, {'hls_native_live': True})

        man_url = f'http://127.0.0.1:{self.port}/live.m3u8'
        info_dict = {
            'url': man_url,
            'is_live': True,
        }

        # Test that _create_live_fragment_generator returns a callable
        gen_func = fd._create_live_fragment_generator(man_url, info_dict)
        self.assertTrue(callable(gen_func))

        # Test that calling it returns a generator that yields fragments
        ctx = {'start': time.time()}
        gen = gen_func(ctx)

        # Get just the first fragment to verify it works
        first_frag = next(gen)
        self.assertIn('url', first_frag)
        self.assertIn('frag_index', first_frag)
        self.assertEqual(first_frag['frag_index'], 1)

    def test_hls_fd_can_download_with_generator_protocol(self):
        """Test that HlsFD.can_download allows live with generator protocol."""
        from yt_dlp.downloader.hls import HlsFD

        manifest = '''\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:6.0,
segment100.ts
'''
        # Live + generator protocol should be allowed
        info_dict = {
            'protocol': 'm3u8_native_generator',
            'is_live': True,
        }
        self.assertTrue(HlsFD.can_download(manifest, info_dict))

        # Live + regular protocol should be rejected
        info_dict_regular = {
            'protocol': 'm3u8_native',
            'is_live': True,
        }
        self.assertFalse(HlsFD.can_download(manifest, info_dict_regular))

        # VOD should always be allowed
        info_dict_vod = {
            'protocol': 'm3u8_native',
            'is_live': False,
        }
        self.assertTrue(HlsFD.can_download(manifest, info_dict_vod))

    def test_fragment_generator_yields_fragments(self):
        """Test that the fragment generator correctly yields fragment dicts."""
        import functools

        url = f'http://127.0.0.1:{self.port}/live.m3u8'

        # Create a simple fragment generator similar to what the extractor does
        def fragment_generator(ctx):
            import urllib.request
            with urllib.request.urlopen(url) as response:
                manifest = response.read().decode()
            parser = HlsManifestParser(manifest, url)

            for i, segment in enumerate(parser.segments):
                yield {
                    'frag_index': i + 1,
                    'url': segment['url'],
                    'decrypt_info': segment['decrypt_info'],
                    'byte_range': segment['byte_range'],
                    'media_sequence': segment['media_sequence'],
                }

        gen_callable = functools.partial(fragment_generator)
        ctx = {'start': time.time()}

        # Call the generator and collect fragments
        fragments = list(gen_callable(ctx))

        self.assertEqual(len(fragments), 2)
        self.assertEqual(fragments[0]['frag_index'], 1)
        self.assertEqual(fragments[0]['media_sequence'], 100)
        self.assertIn('segment100.ts', fragments[0]['url'])
        self.assertEqual(fragments[1]['frag_index'], 2)
        self.assertEqual(fragments[1]['media_sequence'], 101)

    def test_hls_fd_resolve_fragments_callable(self):
        """Test that HlsFD._resolve_fragments handles callable correctly."""
        from yt_dlp.downloader.hls import HlsFD

        ydl = FakeYDL()
        fd = HlsFD(ydl, {})

        # Test with callable
        def fragments_gen(ctx):
            yield {'frag_index': 1, 'url': 'http://example.com/seg1.ts'}
            yield {'frag_index': 2, 'url': 'http://example.com/seg2.ts'}

        ctx = {}
        result = fd._resolve_fragments(fragments_gen, ctx)
        # Should be a generator, collect it
        fragments = list(result)
        self.assertEqual(len(fragments), 2)

        # Test with list (non-callable)
        frag_list = [
            {'frag_index': 1, 'url': 'http://example.com/seg1.ts'},
            {'frag_index': 2, 'url': 'http://example.com/seg2.ts'},
        ]
        result = fd._resolve_fragments(frag_list, ctx)
        self.assertEqual(result, frag_list)

    def test_hls_fd_resolve_fragments_test_mode(self):
        """Test that _resolve_fragments returns only first fragment in test mode."""
        from yt_dlp.downloader.hls import HlsFD

        ydl = FakeYDL()
        fd = HlsFD(ydl, {'test': True})

        def fragments_gen(ctx):
            yield {'frag_index': 1, 'url': 'http://example.com/seg1.ts'}
            yield {'frag_index': 2, 'url': 'http://example.com/seg2.ts'}
            yield {'frag_index': 3, 'url': 'http://example.com/seg3.ts'}

        ctx = {}
        result = fd._resolve_fragments(fragments_gen, ctx)
        # In test mode, should only return first fragment
        fragments = list(result) if hasattr(result, '__iter__') else [result]
        self.assertEqual(len(fragments), 1)


class TestHlsManifestParserWithFixtures(unittest.TestCase):
    """Tests using the M3U8 test fixture files."""

    FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'testdata', 'm3u8')

    def _read_fixture(self, filename):
        with open(os.path.join(self.FIXTURES_DIR, filename), encoding='utf-8') as f:
            return f.read()

    def test_livestream_basic_fixture(self):
        """Test parsing the basic livestream fixture."""
        manifest = self._read_fixture('livestream_basic.m3u8')
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.target_duration, 6.0)
        self.assertEqual(parser.media_sequence, 1000)
        self.assertEqual(len(parser.segments), 3)
        self.assertFalse(parser.is_endlist)
        self.assertEqual(parser.last_media_sequence, 1002)

    def test_livestream_encrypted_fixture(self):
        """Test parsing the encrypted livestream fixture."""
        manifest = self._read_fixture('livestream_encrypted.m3u8')
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.media_sequence, 500)
        self.assertEqual(len(parser.segments), 3)
        # First two segments use key1
        self.assertEqual(
            parser.segments[0]['decrypt_info']['URI'],
            'https://keys.example.com/key1.bin')
        self.assertIsNotNone(parser.segments[0]['decrypt_info']['IV'])
        # Third segment uses key2 (no explicit IV)
        self.assertEqual(
            parser.segments[2]['decrypt_info']['URI'],
            'https://keys.example.com/key2.bin')

    def test_livestream_ended_fixture(self):
        """Test parsing the ended livestream fixture."""
        manifest = self._read_fixture('livestream_ended.m3u8')
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertTrue(parser.is_endlist)
        self.assertEqual(parser.media_sequence, 2000)
        self.assertEqual(len(parser.segments), 3)

    def test_livestream_with_init_fixture(self):
        """Test parsing the fMP4 livestream with init segment fixture."""
        manifest = self._read_fixture('livestream_with_init.m3u8')
        parser = HlsManifestParser(manifest, 'http://example.com/')

        self.assertEqual(parser.media_sequence, 100)
        # Should have init segment + 3 media segments
        self.assertEqual(len(parser.segments), 4)
        self.assertTrue(parser.segments[0].get('is_init'))
        self.assertEqual(
            parser.segments[0]['url'],
            'https://cdn.example.com/live/init.mp4')
        self.assertFalse(parser.segments[1].get('is_init'))


class TestHlsLiveFragmentGenerator(unittest.TestCase):
    """Tests for the _extract_m3u8_live_fragments helper."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = http.server.HTTPServer(('127.0.0.1', 0), HlsLiveTestHandler)
        cls.port = http_server_port(cls.httpd)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        HlsLiveTestHandler.reset()

    def test_fragment_generator_from_extractor(self):
        """Test fragment generator created by extractor helper."""
        # This test simulates what the extractor helper does
        # We can't easily test _extract_m3u8_live_fragments directly
        # without a full extractor, so we test the pattern it uses

        url = f'http://127.0.0.1:{self.port}/live.m3u8'

        # Simulate the generator pattern
        collected_fragments = []
        max_fragments = 4

        import urllib.request
        last_media_sequence = -1

        for _ in range(3):  # Simulate 3 polls
            with urllib.request.urlopen(url) as response:
                manifest = response.read().decode()
            parser = HlsManifestParser(manifest, url)

            new_segments = parser.get_new_segments_since(last_media_sequence)
            for seg in new_segments:
                collected_fragments.append({
                    'url': seg['url'],
                    'media_sequence': seg['media_sequence'],
                })
                if len(collected_fragments) >= max_fragments:
                    break

            last_media_sequence = parser.last_media_sequence

            if len(collected_fragments) >= max_fragments:
                break

            # Simulate stream advancing
            HlsLiveTestHandler.advance(1)

        # Should have collected at least 2 fragments from initial manifest
        self.assertGreaterEqual(len(collected_fragments), 2)
        # All fragments should have incrementing media sequences
        sequences = [f['media_sequence'] for f in collected_fragments]
        self.assertEqual(sequences, sorted(sequences))


if __name__ == '__main__':
    unittest.main()

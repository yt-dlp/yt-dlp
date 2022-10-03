import io
import re
import urllib.parse

from . import get_suitable_downloader
from .external import FFmpegFD
from .fragment import FragmentFD
from .. import webvtt
from ..dependencies import Cryptodome_AES
from ..utils import HlsMediaManifest, bug_reports_message


class HlsFD(FragmentFD):
    """
    Download segments in a m3u8 manifest. External downloaders can take over
    the fragment downloads by supporting the 'm3u8_frag_urls' protocol and
    re-defining 'supports_manifest' function
    """

    FD_NAME = 'hlsnative'

    @staticmethod
    def can_download(manifest, info_dict, allow_unplayable_formats=False):
        UNSUPPORTED_FEATURES = [
            # r'#EXT-X-BYTERANGE',  # playlists composed of byte ranges of media files [2]

            # Live streams heuristic does not always work (e.g. geo restricted to Germany
            # http://hls-geo.daserste.de/i/videoportal/Film/c_620000/622873/format,716451,716457,716450,716458,716459,.mp4.csmil/index_4_av.m3u8?null=0)
            # r'#EXT-X-MEDIA-SEQUENCE:(?!0$)',  # live streams [3]

            # This heuristic also is not correct since segments may not be appended as well.
            # Twitch vods of finished streams have EXT-X-PLAYLIST-TYPE:EVENT despite
            # no segments will definitely be appended to the end of the playlist.
            # r'#EXT-X-PLAYLIST-TYPE:EVENT',  # media segments may be appended to the end of
            #                                 # event media playlists [4]
            # r'#EXT-X-MAP:',  # media initialization [5]
            # 1. https://tools.ietf.org/html/draft-pantos-http-live-streaming-17#section-4.3.2.4
            # 2. https://tools.ietf.org/html/draft-pantos-http-live-streaming-17#section-4.3.2.2
            # 3. https://tools.ietf.org/html/draft-pantos-http-live-streaming-17#section-4.3.3.2
            # 4. https://tools.ietf.org/html/draft-pantos-http-live-streaming-17#section-4.3.3.5
            # 5. https://tools.ietf.org/html/draft-pantos-http-live-streaming-17#section-4.3.2.5
        ]
        if not allow_unplayable_formats:
            UNSUPPORTED_FEATURES += [
                r'#EXT-X-KEY:METHOD=(?!NONE|AES-128)',  # encrypted streams [1]
            ]

        def check_results():
            yield not info_dict.get('is_live')
            for feature in UNSUPPORTED_FEATURES:
                yield not re.search(feature, manifest)
        return all(check_results())

    def real_download(self, filename, info_dict):
        man_url = info_dict['url']
        self.to_screen('[%s] Downloading m3u8 manifest' % self.FD_NAME)

        urlh = self.ydl.urlopen(self._prepare_url(info_dict, man_url))
        man_url = urlh.geturl()
        s = urlh.read().decode('utf-8', 'ignore')

        can_download, message = self.can_download(s, info_dict, self.params.get('allow_unplayable_formats')), None
        if can_download:
            has_ffmpeg = FFmpegFD.available()
            no_crypto = not Cryptodome_AES and '#EXT-X-KEY:METHOD=AES-128' in s
            if no_crypto and has_ffmpeg:
                can_download, message = False, 'The stream has AES-128 encryption and pycryptodomex is not available'
            elif no_crypto:
                message = ('The stream has AES-128 encryption and neither ffmpeg nor pycryptodomex are available; '
                           'Decryption will be performed natively, but will be extremely slow')
            elif info_dict.get('extractor_key') == 'Generic' and re.search(r'(?m)#EXT-X-MEDIA-SEQUENCE:(?!0$)', s):
                install_ffmpeg = '' if has_ffmpeg else 'install ffmpeg and '
                message = ('Live HLS streams are not supported by the native downloader. If this is a livestream, '
                           f'please {install_ffmpeg}add "--downloader ffmpeg --hls-use-mpegts" to your command')
        if not can_download:
            has_drm = re.search('|'.join([
                r'#EXT-X-FAXS-CM:',  # Adobe Flash Access
                r'#EXT-X-(?:SESSION-)?KEY:.*?URI="skd://',  # Apple FairPlay
            ]), s)
            if has_drm and not self.params.get('allow_unplayable_formats'):
                self.report_error(
                    'This video is DRM protected; Try selecting another format with --format or '
                    'add --check-formats to automatically fallback to the next best format')
                return False
            message = message or 'Unsupported features have been detected'
            fd = FFmpegFD(self.ydl, self.params)
            self.report_warning(f'{message}; extraction will be delegated to {fd.get_basename()}')
            return fd.real_download(filename, info_dict)
        elif message:
            self.report_warning(message)

        is_webvtt = info_dict['ext'] == 'vtt'
        if is_webvtt:
            real_downloader = None  # Packing the fragments is not currently supported for external downloader
        else:
            real_downloader = get_suitable_downloader(
                info_dict, self.params, None, protocol='m3u8_frag_urls', to_stdout=(filename == '-'))
        if real_downloader and not real_downloader.supports_manifest(s):
            real_downloader = None
        if real_downloader:
            self.to_screen(f'[{self.FD_NAME}] Fragment downloads will be delegated to {real_downloader.get_basename()}')

        media_manifest = HlsMediaManifest(s, man_url)
        manifest_stats = media_manifest.get_stats()
        ctx = {
            'filename': filename,
            'total_frags': manifest_stats['media_frags'],
            'ad_frags': manifest_stats['ad_frags'],
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx, info_dict)

        extra_state = ctx.setdefault('extra_state', {})

        extra_query = None
        extra_param_to_segment_url = info_dict.get('extra_param_to_segment_url')
        if extra_param_to_segment_url:
            extra_query = urllib.parse.parse_qs(extra_param_to_segment_url)

        fragments = media_manifest.get_fragments(info_dict.get('format_index'), ctx['fragment_index'], extra_query)

        # We only download the first fragment during the test
        if self.params.get('test', False):
            fragments = [fragments[0] if fragments else None]

        if real_downloader:
            info_dict['fragments'] = fragments
            fd = real_downloader(self.ydl, self.params)
            # TODO: Make progress updates work without hooking twice
            # for ph in self._progress_hooks:
            #     fd.add_progress_hook(ph)
            return fd.real_download(filename, info_dict)

        if is_webvtt:
            def pack_fragment(frag_content, frag_index):
                output = io.StringIO()
                adjust = 0
                overflow = False
                mpegts_last = None
                for block in webvtt.parse_fragment(frag_content):
                    if isinstance(block, webvtt.CueBlock):
                        extra_state['webvtt_mpegts_last'] = mpegts_last
                        if overflow:
                            extra_state['webvtt_mpegts_adjust'] += 1
                            overflow = False
                        block.start += adjust
                        block.end += adjust

                        dedup_window = extra_state.setdefault('webvtt_dedup_window', [])

                        ready = []

                        i = 0
                        is_new = True
                        while i < len(dedup_window):
                            wcue = dedup_window[i]
                            wblock = webvtt.CueBlock.from_json(wcue)
                            i += 1
                            if wblock.hinges(block):
                                wcue['end'] = block.end
                                is_new = False
                                continue
                            if wblock == block:
                                is_new = False
                                continue
                            if wblock.end > block.start:
                                continue
                            ready.append(wblock)
                            i -= 1
                            del dedup_window[i]

                        if is_new:
                            dedup_window.append(block.as_json)
                        for block in ready:
                            block.write_into(output)

                        # we only emit cues once they fall out of the duplicate window
                        continue
                    elif isinstance(block, webvtt.Magic):
                        # take care of MPEG PES timestamp overflow
                        if block.mpegts is None:
                            block.mpegts = 0
                        extra_state.setdefault('webvtt_mpegts_adjust', 0)
                        block.mpegts += extra_state['webvtt_mpegts_adjust'] << 33
                        if block.mpegts < extra_state.get('webvtt_mpegts_last', 0):
                            overflow = True
                            block.mpegts += 1 << 33
                        mpegts_last = block.mpegts

                        if frag_index == 1:
                            extra_state['webvtt_mpegts'] = block.mpegts or 0
                            extra_state['webvtt_local'] = block.local or 0
                            # XXX: block.local = block.mpegts = None ?
                        else:
                            if block.mpegts is not None and block.local is not None:
                                adjust = (
                                    (block.mpegts - extra_state.get('webvtt_mpegts', 0))
                                    - (block.local - extra_state.get('webvtt_local', 0))
                                )
                            continue
                    elif isinstance(block, webvtt.HeaderBlock):
                        if frag_index != 1:
                            # XXX: this should probably be silent as well
                            # or verify that all segments contain the same data
                            self.report_warning(bug_reports_message(
                                'Discarding a %s block found in the middle of the stream; '
                                'if the subtitles display incorrectly,'
                                % (type(block).__name__)))
                            continue
                    block.write_into(output)

                return output.getvalue().encode()

            def fin_fragments():
                dedup_window = extra_state.get('webvtt_dedup_window')
                if not dedup_window:
                    return b''

                output = io.StringIO()
                for cue in dedup_window:
                    webvtt.CueBlock.from_json(cue).write_into(output)

                return output.getvalue().encode()

            self.download_and_append_fragments(
                ctx, fragments, info_dict, pack_func=pack_fragment, finish_func=fin_fragments)
        else:
            return self.download_and_append_fragments(ctx, fragments, info_dict)

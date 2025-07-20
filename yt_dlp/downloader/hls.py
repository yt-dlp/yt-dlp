import binascii
import io
import re
import urllib.parse

from . import get_suitable_downloader
from .external import FFmpegFD
from .fragment import FragmentFD
from .. import webvtt
from ..dependencies import Cryptodome
from ..utils import (
    bug_reports_message,
    parse_m3u8_attributes,
    remove_start,
    traverse_obj,
    update_url_query,
    urljoin,
)
from ..utils._utils import _request_dump_filename


class HlsFD(FragmentFD):
    """
    Download segments in a m3u8 manifest. External downloaders can take over
    the fragment downloads by supporting the 'm3u8_frag_urls' protocol and
    re-defining 'supports_manifest' function
    """

    FD_NAME = 'hlsnative'

    @staticmethod
    def _has_drm(manifest):  # TODO: https://github.com/yt-dlp/yt-dlp/pull/5039
        return bool(re.search('|'.join((
            r'#EXT-X-(?:SESSION-)?KEY:.*?URI="skd://',  # Apple FairPlay
            r'#EXT-X-(?:SESSION-)?KEY:.*?KEYFORMAT="com\.apple\.streamingkeydelivery"',  # Apple FairPlay
            r'#EXT-X-(?:SESSION-)?KEY:.*?KEYFORMAT="com\.microsoft\.playready"',  # Microsoft PlayReady
            r'#EXT-X-FAXS-CM:',  # Adobe Flash Access
        )), manifest))

    @classmethod
    def can_download(cls, manifest, info_dict, allow_unplayable_formats=False):
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
                r'#EXT-X-KEY:METHOD=(?!NONE|AES-128)',  # encrypted streams [1], but not necessarily DRM
            ]

        def check_results():
            yield not info_dict.get('is_live')
            for feature in UNSUPPORTED_FEATURES:
                yield not re.search(feature, manifest)
            if not allow_unplayable_formats:
                yield not cls._has_drm(manifest)
        return all(check_results())

    def real_download(self, filename, info_dict):
        man_url = info_dict['url']

        s = info_dict.get('hls_media_playlist_data')
        if s:
            self.to_screen(f'[{self.FD_NAME}] Using m3u8 manifest from extracted info')
        else:
            self.to_screen(f'[{self.FD_NAME}] Downloading m3u8 manifest')
            urlh = self.ydl.urlopen(self._prepare_url(info_dict, man_url))
            man_url = urlh.url
            s_bytes = urlh.read()
            if self.params.get('write_pages'):
                dump_filename = _request_dump_filename(
                    man_url, info_dict['id'], None,
                    trim_length=self.params.get('trim_file_name'))
                self.to_screen(f'[{self.FD_NAME}] Saving request to {dump_filename}')
                with open(dump_filename, 'wb') as outf:
                    outf.write(s_bytes)
            s = s_bytes.decode('utf-8', 'ignore')

        can_download, message = self.can_download(s, info_dict, self.params.get('allow_unplayable_formats')), None
        if can_download:
            has_ffmpeg = FFmpegFD.available()
            if not Cryptodome.AES and '#EXT-X-KEY:METHOD=AES-128' in s:
                # Even if pycryptodomex isn't available, force HlsFD for m3u8s that won't work with ffmpeg
                ffmpeg_can_dl = not traverse_obj(info_dict, ((
                    'extra_param_to_segment_url', 'extra_param_to_key_url',
                    'hls_media_playlist_data', ('hls_aes', ('uri', 'key', 'iv')),
                ), any))
                message = 'The stream has AES-128 encryption and {} available'.format(
                    'neither ffmpeg nor pycryptodomex are' if ffmpeg_can_dl and not has_ffmpeg else
                    'pycryptodomex is not')
                if has_ffmpeg and ffmpeg_can_dl:
                    can_download = False
                else:
                    message += '; decryption will be performed natively, but will be extremely slow'
            elif info_dict.get('extractor_key') == 'Generic' and re.search(r'(?m)#EXT-X-MEDIA-SEQUENCE:(?!0$)', s):
                install_ffmpeg = '' if has_ffmpeg else 'install ffmpeg and '
                message = ('Live HLS streams are not supported by the native downloader. If this is a livestream, '
                           f'please {install_ffmpeg}add "--downloader ffmpeg --hls-use-mpegts" to your command')
        if not can_download:
            if self._has_drm(s) and not self.params.get('allow_unplayable_formats'):
                if info_dict.get('has_drm') and self.params.get('test'):
                    self.to_screen(f'[{self.FD_NAME}] This format is DRM protected', skip_eol=True)
                else:
                    self.report_error(
                        'This format is DRM protected; Try selecting another format with --format or '
                        'add --check-formats to automatically fallback to the next best format', tb=False)
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

        def is_ad_fragment_start(s):
            return ((s.startswith('#ANVATO-SEGMENT-INFO') and 'type=ad' in s)
                    or (s.startswith('#UPLYNK-SEGMENT') and s.endswith(',ad')))

        def is_ad_fragment_end(s):
            return ((s.startswith('#ANVATO-SEGMENT-INFO') and 'type=master' in s)
                    or (s.startswith('#UPLYNK-SEGMENT') and s.endswith(',segment')))

        fragments = []

        media_frags = 0
        ad_frags = 0
        ad_frag_next = False
        for line in s.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                if is_ad_fragment_start(line):
                    ad_frag_next = True
                elif is_ad_fragment_end(line):
                    ad_frag_next = False
                continue
            if ad_frag_next:
                ad_frags += 1
                continue
            media_frags += 1

        ctx = {
            'filename': filename,
            'total_frags': media_frags,
            'ad_frags': ad_frags,
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx, info_dict)

        extra_state = ctx.setdefault('extra_state', {})

        format_index = info_dict.get('format_index')
        extra_segment_query = None
        if extra_param_to_segment_url := info_dict.get('extra_param_to_segment_url'):
            extra_segment_query = urllib.parse.parse_qs(extra_param_to_segment_url)
        extra_key_query = None
        if extra_param_to_key_url := info_dict.get('extra_param_to_key_url'):
            extra_key_query = urllib.parse.parse_qs(extra_param_to_key_url)
        i = 0
        media_sequence = 0
        decrypt_info = {'METHOD': 'NONE'}
        external_aes_key = traverse_obj(info_dict, ('hls_aes', 'key'))
        if external_aes_key:
            external_aes_key = binascii.unhexlify(remove_start(external_aes_key, '0x'))
            assert len(external_aes_key) in (16, 24, 32), 'Invalid length for HLS AES-128 key'
        external_aes_iv = traverse_obj(info_dict, ('hls_aes', 'iv'))
        if external_aes_iv:
            external_aes_iv = binascii.unhexlify(remove_start(external_aes_iv, '0x').zfill(32))
        byte_range = {}
        byte_range_offset = 0
        discontinuity_count = 0
        frag_index = 0
        ad_frag_next = False
        for line in s.splitlines():
            line = line.strip()
            if line:
                if not line.startswith('#'):
                    if format_index and discontinuity_count != format_index:
                        continue
                    if ad_frag_next:
                        continue
                    frag_index += 1
                    if frag_index <= ctx['fragment_index']:
                        continue
                    frag_url = urljoin(man_url, line)
                    if extra_segment_query:
                        frag_url = update_url_query(frag_url, extra_segment_query)

                    fragments.append({
                        'frag_index': frag_index,
                        'url': frag_url,
                        'decrypt_info': decrypt_info,
                        'byte_range': byte_range,
                        'media_sequence': media_sequence,
                    })
                    media_sequence += 1

                    # If the byte_range is truthy, reset it after appending a fragment that uses it
                    if byte_range:
                        byte_range_offset = byte_range['end']
                        byte_range = {}

                elif line.startswith('#EXT-X-MAP'):
                    if format_index and discontinuity_count != format_index:
                        continue
                    if frag_index > 0:
                        self.report_error(
                            'Initialization fragment found after media fragments, unable to download')
                        return False
                    frag_index += 1
                    map_info = parse_m3u8_attributes(line[11:])
                    frag_url = urljoin(man_url, map_info.get('URI'))
                    if extra_segment_query:
                        frag_url = update_url_query(frag_url, extra_segment_query)

                    map_byte_range = {}

                    if map_info.get('BYTERANGE'):
                        splitted_byte_range = map_info.get('BYTERANGE').split('@')
                        sub_range_start = int(splitted_byte_range[1]) if len(splitted_byte_range) == 2 else 0
                        map_byte_range = {
                            'start': sub_range_start,
                            'end': sub_range_start + int(splitted_byte_range[0]),
                        }

                    fragments.append({
                        'frag_index': frag_index,
                        'url': frag_url,
                        'decrypt_info': decrypt_info,
                        'byte_range': map_byte_range,
                        'media_sequence': media_sequence,
                    })
                    media_sequence += 1

                elif line.startswith('#EXT-X-KEY'):
                    decrypt_url = decrypt_info.get('URI')
                    decrypt_info = parse_m3u8_attributes(line[11:])
                    if decrypt_info['METHOD'] == 'AES-128':
                        if external_aes_iv:
                            decrypt_info['IV'] = external_aes_iv
                        elif 'IV' in decrypt_info:
                            decrypt_info['IV'] = binascii.unhexlify(decrypt_info['IV'][2:].zfill(32))
                        if external_aes_key:
                            decrypt_info['KEY'] = external_aes_key
                        else:
                            decrypt_info['URI'] = urljoin(man_url, decrypt_info['URI'])
                            if extra_key_query or extra_segment_query:
                                # Fall back to extra_segment_query to key for backwards compat
                                decrypt_info['URI'] = update_url_query(
                                    decrypt_info['URI'], extra_key_query or extra_segment_query)
                            if decrypt_url != decrypt_info['URI']:
                                decrypt_info['KEY'] = None

                elif line.startswith('#EXT-X-MEDIA-SEQUENCE'):
                    media_sequence = int(line[22:])
                elif line.startswith('#EXT-X-BYTERANGE'):
                    splitted_byte_range = line[17:].split('@')
                    sub_range_start = int(splitted_byte_range[1]) if len(splitted_byte_range) == 2 else byte_range_offset
                    byte_range = {
                        'start': sub_range_start,
                        'end': sub_range_start + int(splitted_byte_range[0]),
                    }
                elif is_ad_fragment_start(line):
                    ad_frag_next = True
                elif is_ad_fragment_end(line):
                    ad_frag_next = False
                elif line.startswith('#EXT-X-DISCONTINUITY'):
                    discontinuity_count += 1
                i += 1

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
                                f'Discarding a {type(block).__name__} block found in the middle of the stream; '
                                'if the subtitles display incorrectly,'))
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

            if len(fragments) == 1:
                self.download_and_append_fragments(ctx, fragments, info_dict)
            else:
                self.download_and_append_fragments(
                    ctx, fragments, info_dict, pack_func=pack_fragment, finish_func=fin_fragments)
        else:
            return self.download_and_append_fragments(ctx, fragments, info_dict)

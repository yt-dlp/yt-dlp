import json
import os
import re
import threading
import time

from .hls import HlsFD
from ..extractor.eplus import EplusIbIE
from ..networking import Request
from ..networking.exceptions import network_exceptions
from ..utils import DownloadError, ExtractorError, RetryManager, traverse_obj


class EplusFD(HlsFD):
    """
    Downloads Streaming+ HLS while refreshing signed cookies
    Note, this is not a part of public API, and will be removed without notice.
    DO NOT USE
    """

    FD_NAME = 'eplus'
    # Player refreshes cookies via getStreamStatus every 15 minutes
    _REFRESH_INTERVAL = 15 * 60

    def real_download(self, filename, info_dict):
        self.to_screen(f'[{self.FD_NAME}] Downloading Streaming+ HLS')
        # External downloaders receive the cookies only once, when they start
        self.params = {**self.params, 'external_downloader': 'native'}
        self._auth_lock = threading.Lock()
        self._last_refresh = time.monotonic()
        self._live_ended = False

        if not info_dict.get('is_live'):
            return super().real_download(filename, info_dict)

        if os.path.isfile(self.temp_name(filename)):
            self.report_error('Cannot resume a live Streaming+ download; use a different output filename')
            return False

        # Concurrent fragment downloads eagerly consume the iterable
        self.params['concurrent_fragment_downloads'] = 1
        ctx = {'filename': filename, 'live': True, 'total_frags': None}
        self._prepare_and_start_frag_download(ctx, info_dict)
        return self.download_and_append_fragments(
            ctx, self._live_fragments(info_dict), info_dict, is_fatal=lambda _: True)

    def _refresh_authentication(self, info_dict):
        with self._auth_lock:
            if time.monotonic() - self._last_refresh < self._REFRESH_INTERVAL:
                return
            retry_manager = RetryManager(self.params.get('retries'), self.report_retry)
            for retry in retry_manager:
                try:
                    # Connections left idle for 15 minutes stop responding; do not reuse them
                    urlh = self.ydl.urlopen(Request(
                        f'https://live.eplus.jp/api/stream/{info_dict["id"]}/status',
                        query={'sid': info_dict['_eplus_stream_session']},
                        headers={
                            'User-Agent': EplusIbIE._USER_AGENT,
                            'Referer': info_dict['webpage_url'],
                            'X-Requested-With': 'XMLHttpRequest',
                            'Connection': 'close',
                        }))
                    status = json.loads(urlh.read())
                except network_exceptions as e:
                    retry.error = e
                    continue
                if status.get('error'):
                    raise ExtractorError(
                        'Streaming+ viewing session is no longer valid; re-extract the video', expected=True)
                if info_dict.get('_eplus_limited_viewing') and not status.get('cvd'):
                    raise ExtractorError('The Streaming+ viewing period has expired', expected=True)
                if info_dict.get('is_live'):
                    self._live_ended = traverse_obj(status, ('stream', 'delivery_status')) in (
                        'STOPPED', 'WAIT_CONFIRM_ARCHIVED', 'CONFIRMED_ARCHIVE')
                self._last_refresh = time.monotonic()
            if retry_manager.error:
                raise DownloadError('Unable to refresh Streaming+ authentication')

    def _download_fragment(self, ctx, frag_url, info_dict, headers=None, request_data=None):
        self._refresh_authentication(info_dict)
        return super()._download_fragment(ctx, frag_url, info_dict, headers, request_data)

    def _live_fragments(self, info_dict):
        next_sequence = None
        frag_index = 0
        last_map = None
        last_progress = time.monotonic()
        while True:
            self._refresh_authentication(info_dict)
            retry_manager = RetryManager(self.params.get('retries'), self.report_retry)
            for retry in retry_manager:
                try:
                    urlh = self.ydl.urlopen(self._prepare_url(info_dict, info_dict['url']))
                    manifest = urlh.read().decode('utf-8', 'ignore')
                    man_url = urlh.url
                except network_exceptions as e:
                    retry.error = e
                    continue
            if retry_manager.error:
                raise DownloadError('Unable to download Streaming+ live HLS playlist')

            # can_download rejects is_live; reuse only the playlist feature checks
            if not self.can_download(
                    manifest, {**info_dict, 'is_live': False},
                    self.params.get('allow_unplayable_formats')):
                raise DownloadError('Unsupported Streaming+ live HLS playlist')

            media_sequence = re.search(r'(?m)^#EXT-X-MEDIA-SEQUENCE:(\d+)', manifest)
            target = re.search(r'(?m)^#EXT-X-TARGETDURATION:(\d+)', manifest)
            sequence = int(media_sequence.group(1)) if media_sequence else 0
            target_duration = int(target.group(1)) if target else None
            if not target_duration:
                raise DownloadError('Invalid Streaming+ live HLS playlist')
            if next_sequence is not None and sequence > next_sequence:
                raise DownloadError(f'Streaming+ live segments {next_sequence}-{sequence - 1} are no longer available')

            fragments = self._get_fragments(manifest, man_url, info_dict, {'fragment_index': 0, 'live': True})
            if fragments is False:
                raise DownloadError('Unable to parse Streaming+ live HLS playlist')
            init_fragment = None
            for fragment in fragments:
                if fragment.get('is_map'):
                    init_fragment = fragment
                    continue
                if next_sequence is None or sequence >= next_sequence:
                    if init_fragment:
                        map_id = (
                            init_fragment['url'], init_fragment['byte_range'],
                            init_fragment['decrypt_info'].get('URI'), init_fragment['decrypt_info'].get('IV'))
                        if map_id != last_map:
                            frag_index += 1
                            yield {**init_fragment, 'frag_index': frag_index}
                            last_map = map_id
                    frag_index += 1
                    # MAP tags do not advance MEDIA-SEQUENCE
                    yield {**fragment, 'frag_index': frag_index, 'media_sequence': sequence}
                    next_sequence = sequence + 1
                    last_progress = time.monotonic()
                    if self.params.get('test'):
                        return
                sequence += 1

            if '#EXT-X-ENDLIST' in manifest or (
                    self._live_ended and time.monotonic() - last_progress >= target_duration):
                return
            time.sleep(target_duration)

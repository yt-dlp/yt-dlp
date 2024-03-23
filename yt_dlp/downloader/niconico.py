import contextlib
import json
import math
import threading
import time

from . import get_suitable_downloader
from .common import FileDownloader
from .external import FFmpegFD
from ..downloader.fragment import FragmentFD
from ..networking import Request
from ..networking.exceptions import network_exceptions
from ..utils import (
    DownloadError,
    RetryManager,
    str_or_none,
    traverse_obj,
    try_get,
    urljoin,
)


class NiconicoDmcFD(FileDownloader):
    """ Downloading niconico douga from DMC with heartbeat """

    def real_download(self, filename, info_dict):
        from ..extractor.niconico import NiconicoIE

        self.to_screen('[%s] Downloading from DMC' % self.FD_NAME)
        ie = NiconicoIE(self.ydl)
        info_dict, heartbeat_info_dict = ie._get_heartbeat_info(info_dict)

        fd = get_suitable_downloader(info_dict, params=self.params)(self.ydl, self.params)

        success = download_complete = False
        timer = [None]
        heartbeat_lock = threading.Lock()
        heartbeat_url = heartbeat_info_dict['url']
        heartbeat_data = heartbeat_info_dict['data'].encode()
        heartbeat_interval = heartbeat_info_dict.get('interval', 30)

        request = Request(heartbeat_url, heartbeat_data)

        def heartbeat():
            try:
                self.ydl.urlopen(request).read()
            except Exception:
                self.to_screen('[%s] Heartbeat failed' % self.FD_NAME)

            with heartbeat_lock:
                if not download_complete:
                    timer[0] = threading.Timer(heartbeat_interval, heartbeat)
                    timer[0].start()

        heartbeat_info_dict['ping']()
        self.to_screen('[%s] Heartbeat with %d second interval ...' % (self.FD_NAME, heartbeat_interval))
        try:
            heartbeat()
            if type(fd).__name__ == 'HlsFD':
                info_dict.update(ie._extract_m3u8_formats(info_dict['url'], info_dict['id'])[0])
            success = fd.real_download(filename, info_dict)
        finally:
            if heartbeat_lock:
                with heartbeat_lock:
                    timer[0].cancel()
                    download_complete = True
        return success


class NiconicoLiveFD(FragmentFD):
    """ Downloads niconico live/timeshift VOD """

    _PER_FRAGMENT_DOWNLOAD_RATIO = 0.1
    _WEBSOCKET_RECONNECT_DELAY = 10

    @contextlib.contextmanager
    def _ws_context(self, info_dict):
        """ Hold a WebSocket object and release it when leaving """

        video_id = info_dict['id']
        live_latency = info_dict['downloader_options']['live_latency']
        ws_url = info_dict['downloader_options']['ws_url']

        self.ws = None

        self.m3u8_lock = threading.Event()
        self.m3u8_url = None

        def communicate_ws():
            self.ws = self.ydl.urlopen(Request(ws_url, headers=info_dict.get('http_headers')))
            if self.ydl.params.get('verbose', False):
                self.to_screen('[debug] Sending startWatching request')
            self.ws.send(json.dumps({
                'type': 'startWatching',
                'data': {
                    'stream': {
                        'quality': 'abr',
                        'protocol': 'hls',
                        'latency': live_latency,
                        'chasePlay': False
                    },
                    'room': {
                        'protocol': 'webSocket',
                        'commentable': True
                    },
                    'reconnect': True,
                }
            }))
            with self.ws:
                while True:
                    recv = self.ws.recv()
                    if not recv:
                        continue
                    data = json.loads(recv)
                    if not data or not isinstance(data, dict):
                        continue
                    if data.get('type') == 'ping':
                        # pong back
                        self.ws.send(r'{"type":"pong"}')
                        self.ws.send(r'{"type":"keepSeat"}')
                    elif data.get('type') == 'stream':
                        self.m3u8_url = data['data']['uri']
                        self.m3u8_lock.set()
                    elif data.get('type') == 'disconnect':
                        self.write_debug(data)
                        return
                    elif data.get('type') == 'error':
                        self.write_debug(data)
                        message = try_get(data, lambda x: x['body']['code'], str) or recv
                        raise DownloadError(message)
                    elif self.ydl.params.get('verbose', False):
                        if len(recv) > 100:
                            recv = recv[:100] + '...'
                        self.to_screen('[debug] Server said: %s' % recv)

        stopped = threading.Event()

        def ws_main():
            while not stopped.is_set():
                try:
                    communicate_ws()
                    break  # Disconnected
                except BaseException as e:  # Including TransportError
                    if stopped.is_set():
                        break

                    self.m3u8_lock.clear()  # m3u8 url may be changed

                    self.to_screen('[%s] %s: Connection error occured, reconnecting after %d seconds: %s' % ('niconico:live', video_id, self._WEBSOCKET_RECONNECT_DELAY, str_or_none(e)))
                    time.sleep(self._WEBSOCKET_RECONNECT_DELAY)

            self.m3u8_lock.set()  # Release possible locks

        thread = threading.Thread(target=ws_main, daemon=True)
        thread.start()

        try:
            yield self
        finally:
            stopped.set()
            if self.ws:
                self.ws.close()
            thread.join()

    def _master_m3u8_url(self):
        """ Get the refreshed manifest url after WebSocket reconnection to prevent HTTP 403 """

        self.m3u8_lock.wait()
        return self.m3u8_url

    def real_download(self, filename, info_dict):
        with self._ws_context(info_dict) as ws_context:
            # live
            if info_dict.get('is_live'):
                info_dict = info_dict.copy()
                info_dict['protocol'] = 'm3u8'
                return FFmpegFD(self.ydl, self.params or {}).download(filename, info_dict)

            # timeshift VOD
            from ..extractor.niconico import NiconicoIE
            ie = NiconicoIE(self.ydl)

            video_id = info_dict['id']

            # Get format index
            for format_index, fmt in enumerate(info_dict['formats']):
                if fmt['format_id'] == info_dict['format_id']:
                    break

            # Get video info
            total_duration = 0
            fragment_duration = 0
            for line in ie._download_webpage(info_dict['url'], video_id, note='Downloading m3u8').splitlines():
                if '#STREAM-DURATION' in line:
                    total_duration = int(float(line.split(':')[1]))
                if '#EXT-X-TARGETDURATION' in line:
                    fragment_duration = int(line.split(':')[1])
            if not all({total_duration, fragment_duration}):
                raise DownloadError('Unable to get required video info')

            ctx = {
                'filename': filename,
                'total_frags': math.ceil(total_duration / fragment_duration),
            }

            self._prepare_and_start_frag_download(ctx, info_dict)

            downloaded_duration = ctx['fragment_index'] * fragment_duration
            while True:
                if downloaded_duration > total_duration:
                    break

                retry_manager = RetryManager(self.params.get('fragment_retries'), self.report_retry)
                for retry in retry_manager:
                    try:
                        # Refresh master m3u8 (if possible) and get the url of the previously-chose format
                        master_m3u8_url = ws_context._master_m3u8_url()
                        formats = ie._extract_m3u8_formats(
                            master_m3u8_url, video_id, query={"start": downloaded_duration}, live=False, note=False, fatal=False)
                        media_m3u8_url = traverse_obj(formats, (format_index, {dict}, 'url'), get_all=False)
                        if not media_m3u8_url:
                            raise DownloadError('Unable to get playlist')

                        # Get all fragments
                        media_m3u8 = ie._download_webpage(
                            media_m3u8_url, video_id, note=False, errnote='Unable to download media m3u8')
                        fragment_urls = traverse_obj(media_m3u8.splitlines(), (
                            lambda _, v: not v.startswith('#'), {lambda url: urljoin(media_m3u8_url, url)}))

                        with self.DurationLimiter(len(fragment_urls) * fragment_duration * self._PER_FRAGMENT_DOWNLOAD_RATIO):
                            for fragment_url in fragment_urls:
                                success = self._download_fragment(ctx, fragment_url, info_dict)
                                if not success:
                                    return False
                                self._append_fragment(ctx, self._read_fragment(ctx))
                                downloaded_duration += fragment_duration

                    except (DownloadError, *network_exceptions) as err:
                        retry.error = err
                        continue

                if retry_manager.error:
                    return False

            return self._finish_frag_download(ctx, info_dict)

    class DurationLimiter():
        def __init__(self, target):
            self.target = target

        def __enter__(self):
            self.start = time.time()

        def __exit__(self, *exc):
            remaining = self.target - (time.time() - self.start)
            if remaining > 0:
                time.sleep(remaining)

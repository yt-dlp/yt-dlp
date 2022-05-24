import threading

from .common import FileDownloader
from .external import FFmpegFD


class FC2LiveFD(FileDownloader):
    """
    Downloads FC2 live without being stopped. <br>
    Note, this is not a part of public API, and will be removed without notice.
    DO NOT USE
    """

    def real_download(self, filename, info_dict):
        ws = info_dict['ws']

        heartbeat_lock = threading.Lock()
        heartbeat_state = [None, 1]

        def heartbeat():
            if heartbeat_state[1] < 0:
                return

            try:
                heartbeat_state[1] += 1
                ws.send('{"name":"heartbeat","arguments":{},"id":%d}' % heartbeat_state[1])
            except Exception:
                self.to_screen('[fc2:live] Heartbeat failed')

            with heartbeat_lock:
                heartbeat_state[0] = threading.Timer(30, heartbeat)
                heartbeat_state[0]._daemonic = True
                heartbeat_state[0].start()

        heartbeat()

        new_info_dict = info_dict.copy()
        new_info_dict.update({
            'ws': None,
            'protocol': 'live_ffmpeg',
        })
        try:
            return FFmpegFD(self.ydl, self.params or {}).download(filename, new_info_dict)
        finally:
            # stop heartbeating
            heartbeat_state[1] = -1

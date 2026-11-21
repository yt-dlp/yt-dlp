import json
import threading

from .common import FileDownloader
from .external import FFmpegFD
from ..networking import Request
from ..networking.exceptions import network_exceptions


class ZaikoFD(FileDownloader):
    def real_download(self, filename, info_dict):
        opts = info_dict['downloader_options']
        event_id, external_id, referer = opts['event_id'], opts['external_id'], opts['referer']

        stop = threading.Event()

        def ping_thread():
            while not stop.wait(30):
                try:
                    self.ydl.urlopen(Request(
                        f'https://live.zaiko.services/playerapi/event/{event_id}', headers={
                            'Content-Type': 'application/json',
                            'Referer': referer,
                        }, data=json.dumps({
                            'external_id': external_id,
                        }).encode(),
                    )).read()
                except network_exceptions as e:
                    self.to_screen(f'[{self.FD_NAME}] Ping failed: {e}')

        thread = threading.Thread(target=ping_thread, daemon=True)
        thread.start()

        try:
            info_dict['protocol'] = 'm3u8'
            return FFmpegFD(self.ydl, self.params).real_download(filename, info_dict)
        finally:
            stop.set()
            thread.join(timeout=5)

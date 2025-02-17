import hashlib
import random
import threading

from .common import FileDownloader
from . import HlsFD
from ..networking import Request


class BunnyCdnFD(FileDownloader):
    """Downloads from BunnyCDN with required pings"""

    def real_download(self, filename, info_dict):
        self.to_screen(f'[{self.FD_NAME}] Downloading from BunnyCDN')

        fd = HlsFD(self.ydl, self.params)

        success = download_complete = False
        ping_lock = threading.Lock()

        timer = None
        current_time = 0

        ping_url = info_dict['_bunnycdn_ping_data']['url']
        headers = info_dict['_bunnycdn_ping_data']['headers']
        secret = info_dict['_bunnycdn_ping_data']['secret']
        context_id = info_dict['_bunnycdn_ping_data']['context_id']
        # Site sends ping every 4 seconds, but this throttles the download. Pinging every 2 seconds seems to work.
        ping_interval = 2

        def send_ping():
            nonlocal timer, current_time
            time = current_time + round(random.random(), 6)
            # Hard coded resolution as it doesn't seem to matter
            res = 1080
            paused = 'false'
            md5_hash = hashlib.md5(f'{secret}_{context_id}_{time}_{paused}_{res}'.encode()).hexdigest()

            request = Request(
                f'{ping_url}?hash={md5_hash}&time={time}&paused={paused}&resolution={res}',
                headers=headers)

            try:
                self.ydl.urlopen(request).read()
            except Exception:
                self.to_screen(f'[{self.FD_NAME}] Ping failed')

            with ping_lock:
                if not download_complete:
                    current_time += ping_interval
                    timer = threading.Timer(ping_interval, send_ping)
                    timer.start()

        # Start ping loop
        self.to_screen(f'[{self.FD_NAME}] Starting pings with {ping_interval} second interval...')
        try:
            send_ping()
            success = fd.real_download(filename, info_dict)
        finally:
            with ping_lock:
                if timer:
                    timer.cancel()
                download_complete = True

        return success

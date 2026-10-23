import hashlib
import random
import threading

from .common import FileDownloader
from . import HlsFD
from ..networking import Request
from ..networking.exceptions import network_exceptions


class BunnyCdnFD(FileDownloader):
    """
    Downloads from BunnyCDN with required pings
    Note, this is not a part of public API, and will be removed without notice.
    DO NOT USE
    """

    def real_download(self, filename, info_dict):
        self.to_screen(f'[{self.FD_NAME}] Downloading from BunnyCDN')

        fd = HlsFD(self.ydl, self.params)

        stop_event = threading.Event()
        ping_thread = threading.Thread(target=self.ping_thread, args=(stop_event,), kwargs=info_dict['_bunnycdn_ping_data'])
        ping_thread.start()

        try:
            return fd.real_download(filename, info_dict)
        finally:
            stop_event.set()

    def ping_thread(self, stop_event, url, headers, secret, context_id):
        # Site sends ping every 4 seconds, but this throttles the download. Pinging every 2 seconds seems to work.
        ping_interval = 2
        # Hard coded resolution as it doesn't seem to matter
        res = 1080
        paused = 'false'
        current_time = 0

        while not stop_event.wait(ping_interval):
            current_time += ping_interval

            time = current_time + round(random.random(), 6)
            md5_hash = hashlib.md5(f'{secret}_{context_id}_{time}_{paused}_{res}'.encode()).hexdigest()
            ping_url = f'{url}?hash={md5_hash}&time={time}&paused={paused}&resolution={res}'

            try:
                self.ydl.urlopen(Request(ping_url, headers=headers)).read()
            except network_exceptions as e:
                self.to_screen(f'[{self.FD_NAME}] Ping failed: {e}')

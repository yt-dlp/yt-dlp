import threading

from . import get_suitable_downloader
from .common import FileDownloader
from ..utils import sanitized_Request


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

        request = sanitized_Request(heartbeat_url, heartbeat_data)

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

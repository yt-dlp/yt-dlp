# coding: utf-8
from __future__ import unicode_literals

import threading

from .common import FileDownloader
from ..downloader import _get_real_downloader
from ..extractor.niconico import NiconicoIE
from ..compat import compat_urllib_request


class NiconicoDmcFD(FileDownloader):
    """ Downloading niconico douga from DMC with heartbeat """

    FD_NAME = 'niconico_dmc'

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] Downloading from DMC' % self.FD_NAME)

        ie = NiconicoIE(self.ydl)
        info_dict, heartbeat_info_dict = ie._get_heartbeat_info(info_dict)

        fd = _get_real_downloader(info_dict, params=self.params)(self.ydl, self.params)

        success = download_complete = False
        timer = [None]

        heartbeat_lock = threading.Lock()
        heartbeat_url = heartbeat_info_dict['url']
        heartbeat_data = heartbeat_info_dict['data']
        heartbeat_interval = heartbeat_info_dict.get('interval', 30)
        self.to_screen('[%s] Heartbeat with %s second interval ...' % (self.FD_NAME, heartbeat_interval))

        def heartbeat():
            try:
                compat_urllib_request.urlopen(url=heartbeat_url, data=heartbeat_data.encode())
            except Exception:
                self.to_screen('[%s] Heartbeat failed' % self.FD_NAME)

            with heartbeat_lock:
                if not download_complete:
                    timer[0] = threading.Timer(heartbeat_interval, heartbeat)
                    timer[0].start()

        try:
            heartbeat()
            success = fd.real_download(filename, info_dict)
        finally:
            if heartbeat_lock:
                with heartbeat_lock:
                    timer[0].cancel()
                    download_complete = True

            return success

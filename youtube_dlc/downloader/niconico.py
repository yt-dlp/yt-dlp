# coding: utf-8
from __future__ import unicode_literals

import threading

from .common import FileDownloader
from .http import HttpFD
from .external import FFmpegFD
from ..extractor.niconico import NiconicoIE
from ..compat import compat_urllib_request


class NiconicoDmcFD(FileDownloader):
    """ Base class of Downloading niconico douga from DMC using heartbeat """

    FD_NAME = ''
    FD_DESCRIPTION = ''

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] %s' % (self.FD_NAME, self.FD_DESCRIPTION))

        timer = [None]
        heartbeat_lock = None
        download_complete = False

        if 'heartbeat_url' in info_dict:
            heartbeat_lock = threading.Lock()

            heartbeat_url = info_dict['heartbeat_url']
            heartbeat_data = info_dict['heartbeat_data']
            heartbeat_interval = info_dict.get('heartbeat_interval', 30)
            self.to_screen('[%s] Heartbeat with %s second interval...' % (self.FD_NAME, heartbeat_interval))

            def heartbeat():
                try:
                    compat_urllib_request.urlopen(url=heartbeat_url, data=heartbeat_data.encode())
                except Exception:
                    self.to_screen("[%s] Heartbeat failed" % self.FD_NAME)

                with heartbeat_lock:
                    if not download_complete:
                        timer[0] = threading.Timer(heartbeat_interval, heartbeat)
                        timer[0].start()

            heartbeat()

        try:
            super().real_download(filename, info_dict)
        finally:
            if heartbeat_lock:
                with heartbeat_lock:
                    timer[0].cancel()
                    download_complete = True


class NiconicoDmcHttpFD(NiconicoDmcFD, HttpFD):
    """ Downloads niconico douga from DMC by http with heartbeat """

    FD_NAME = 'niconico_dmc_http'
    FD_DESCRIPTION = 'Downloading from DMC by http'


class NiconicoDmcHlsFD(NiconicoDmcFD, FFmpegFD):
    """ Downloads niconico douga from DMC by hls with heartbeat """

    FD_NAME = 'niconico_dmc_hls'
    FD_DESCRIPTION = 'Downloading from DMC by hls'

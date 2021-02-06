# coding: utf-8
from __future__ import unicode_literals

import threading

from .common import FileDownloader
from .http import HttpFD
from .external import FFmpegFD
from ..extractor.niconico import NiconicoIE
from ..compat import compat_urllib_request


class NiconicoDmcFD(FileDownloader):
    """ Downloading niconico douga from DMC with heartbeat """

    FD_NAME = 'niconico_dmc'

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] Downloading from DMC' % self.FD_NAME)

        ie = NiconicoIE(self.ydl)
        fd = None
        ret = None

        info_dict, heartbeat_info_dict = ie._get_actually_info(info_dict)

        timer = [None]
        heartbeat_lock = None
        download_complete = False

        heartbeat_lock = threading.Lock()

        heartbeat_url = heartbeat_info_dict['url']
        heartbeat_data = heartbeat_info_dict['data']
        heartbeat_interval = heartbeat_info_dict.get('interval', 30)
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

        try:
            if info_dict['protocol'] == 'http':
                self.to_screen('[%s] Downloading from DMC by http' % self.FD_NAME)

                fd = HttpFD(self.ydl, self.params)
            elif info_dict['protocol'] == 'm3u8':  # not 'hls'!
                self.to_screen('[%s] Downloading from DMC by hls' % self.FD_NAME)

                fd = FFmpegFD(self.ydl, self.params)
            else:
                self.report_error('[%s] Unable download %s' % (self.FD_NAME, info_dict['url']))

            heartbeat()
            ret = fd.real_download(filename, info_dict)

        finally:
            if heartbeat_lock:
                with heartbeat_lock:
                    timer[0].cancel()
                    download_complete = True

            return ret

# coding: utf-8
from __future__ import unicode_literals

from .common import FileDownloader
from .augment import HeartbeatAugment
from ..downloader import get_suitable_downloader
from ..extractor.niconico import NiconicoIE


class NiconicoDmcFD(FileDownloader):
    """ Downloading niconico douga from DMC with heartbeat """

    FD_NAME = 'niconico_dmc'

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] Downloading from DMC' % self.FD_NAME)

        ie = NiconicoIE(self.ydl)
        info_dict, heartbeat_info_dict = ie._get_heartbeat_info(info_dict)
        fd = get_suitable_downloader(info_dict, params=self.params)(self.ydl, self.params)

        if type(fd).__name__ == 'HlsFD':
            info_dict.update(ie._extract_m3u8_formats(info_dict['url'], info_dict['id'])[0])

        # NOTE: The Augment is not intended to be called directly,
        # but lazy-DMC requires it so we do that here. It works.
        with HeartbeatAugment(self, info_dict, heartbeat_info_dict):
            return fd.real_download(filename, info_dict)

# coding: utf-8
from __future__ import unicode_literals

from .http import HttpFD
from .external import FFmpegFD
from ..extractor.niconico import NiconicoIE

class NiconicoDmcHttpFD(HttpFD):
    """ Downloads niconico douga from DMC by http with heartbeat """

    FD_NAME = 'niconico_dmc_http'

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] Downloading from DMC by http' % self.FD_NAME)

        super().real_download(filename, info_dict)

class NiconicoDmcHlsFD(FFmpegFD):
    """ Downloads niconico douga from DMC by hls with heartbeat """

    FD_NAME = 'niconico_dmc_hls'

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] Downloading from DMC by hls' % self.FD_NAME)

        super().real_download(filename, info_dict)

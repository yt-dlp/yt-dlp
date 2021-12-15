from __future__ import unicode_literals

import re
from time import sleep

from .dash import DashSegmentsFD
from ..extractor.youtube import YoutubeIE

from ..utils import (
    int_or_none,
    traverse_obj,
    urljoin,
    time_millis,
)


class YoutubeDlFromStartDashFD(DashSegmentsFD):
    """
    Download YouTube live from the start, to the end. For DASH formats.
    """

    FD_NAME = 'ytlivestartdash'

    def _calculate_fragment_count(self, info_dict):
        return True, None

    def _get_fragments(self, info_dict, root_info_dict, ctx):
        manifest_url = info_dict.get('manifest_url')
        if not manifest_url:
            self.report_error('URL for MPD manifest is not known; there is a problem in YoutubeIE code')

        stream_number = info_dict.get('manifest_stream_number', 0)

        download_start_time = ctx.get('start') or (time_millis() / 1000)
        live_start_time = traverse_obj(root_info_dict, ('__original_infodict', 'release_timestamp'))
        lack_early = False
        if live_start_time is not None and download_start_time - live_start_time > 432000:
            self.report_warning('Starting downloading from recent 120 hours of live, because YouTube does not have the data. Please file an issue if you think it is wrong.', only_once=True)
            lack_early = True

        ie = self.ydl.get_info_extractor(YoutubeIE.ie_key())
        return ie._manifest_fragments(manifest_url, stream_number, lack_early=lack_early)

    @staticmethod
    def _accept_live():
        return True

    @staticmethod
    def _ignore_lethal_error():
        return True

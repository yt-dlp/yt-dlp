from __future__ import unicode_literals

import re
from time import sleep

from .dash import DashSegmentsFD
from ..extractor.youtube import YoutubeIE

from ..utils import (
    urljoin,
    time_millis,
)


class YoutubeDlFromStartDashFD(DashSegmentsFD):
    """
    Download YouTube live from the start, to the end. For DASH formats.
    """

    FD_NAME = 'ytlivestartdash'

    @staticmethod
    def _manifest_fragments(ie: YoutubeIE, mpd_url, stream_number, begin_index=0, fetch_span=5000):
        known_idx = begin_index
        no_fragment_count = 0
        prev_dl = time_millis()
        while True:
            if no_fragment_count > 5:
                return
            fmts, _ = ie._extract_mpd_formats_and_subtitles(
                mpd_url, None, note=False, errnote=False, fatal=False)
            if not fmts:
                no_fragment_count += 1
                continue
            fmt_info = next(x for x in fmts if x['manifest_stream_number'] == stream_number)
            fragments = fmt_info['fragments']
            fragment_base_url = fmt_info['fragment_base_url']
            assert fragment_base_url

            last_fragment = fragments[-1]
            last_url = urljoin(fragment_base_url, last_fragment['path'])
            last_seq = int(re.search(r'/sq/(\d+)', last_url).group(1))
            for idx in range(known_idx, last_seq):
                seq = idx + 1
                yield {
                    'frag_index': seq,
                    'index': seq,
                    'url': urljoin(fragment_base_url, 'sq/%d' % seq),
                }
            if known_idx == last_seq:
                no_fragment_count += 1
            else:
                no_fragment_count = 0
            known_idx = last_seq

            now_time = time_millis()
            elapsed = now_time - prev_dl
            if 0 < elapsed and elapsed < fetch_span:
                sleep((fetch_span - elapsed) / 1e3)
            prev_dl = now_time

    def _calculate_fragment_count(self, info_dict):
        return True, None

    def _get_fragments(self, info_dict, ctx):
        manifest_url = info_dict.get('manifest_url')
        if not manifest_url:
            self.report_error('URL for MPD manifest is not known; there is a problem in YoutubeIE code')

        stream_number = info_dict.get('manifest_stream_number', 0)
        yie: YoutubeIE = self.ydl.get_info_extractor(YoutubeIE.ie_key())

        return self._manifest_fragments(yie, manifest_url, stream_number)

    @staticmethod
    def _accept_live():
        return True

    @staticmethod
    def _ignore_lethal_error():
        return True

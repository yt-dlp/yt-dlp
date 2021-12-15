from __future__ import unicode_literals

from ..downloader import get_suitable_downloader
from .fragment import FragmentFD

from ..utils import (
    int_or_none,
    time_millis,
    traverse_obj,
    urljoin,
)


class DashSegmentsFD(FragmentFD):
    """
    Download segments in a DASH manifest. External downloaders can take over
    the fragment downloads by supporting the 'dash_frag_urls' protocol
    """

    FD_NAME = 'dashsegments'

    def real_download(self, filename, info_dict):
        if info_dict.get('is_live') and not self._accept_live():
            # YoutubeDlFromStartDashFD needs to avoid this
            self.report_error('Live DASH videos are not supported')

        real_start = time_millis() / 1000
        real_downloader = get_suitable_downloader(
            info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        args = []
        for fmt in info_dict.get('requested_formats') or [info_dict]:
            is_live, fragment_count = self._calculate_fragment_count(fmt)
            real_filename = fmt.get('filepath', ) or filename
            ctx = {
                'filename': real_filename,
                'live': is_live,
                'total_frags': fragment_count,
            }

            if real_downloader:
                self._prepare_external_frag_download(ctx)
            else:
                self._prepare_and_start_frag_download(ctx, fmt)
            ctx['start'] = real_start

            fragments_to_download = self._get_fragments(fmt, info_dict, ctx)

            if real_downloader:
                self.to_screen(
                    '[%s] Fragment downloads will be delegated to %s' % (self.FD_NAME, real_downloader.get_basename()))
                info_dict['fragments'] = fragments_to_download
                fd = real_downloader(self.ydl, self.params)
                return fd.real_download(filename, info_dict)

            args.append([ctx, fragments_to_download, fmt])

        return self.download_and_append_fragments_multiple(*args, ignore_lethal_error=self._ignore_lethal_error())

    def _calculate_fragment_count(self, info_dict):
        return False, (1 if self.params.get('test', False) else len(info_dict['fragments']))

    def _get_fragments(self, info_dict, root_info_dict, ctx):
        fragment_base_url = info_dict.get('fragment_base_url')
        fragments = info_dict['fragments'][:1] if self.params.get(
            'test', False) else info_dict['fragments']

        fragments_to_download = []
        frag_index = 0
        for i, fragment in enumerate(fragments):
            frag_index += 1
            if frag_index <= ctx['fragment_index']:
                continue
            fragment_url = fragment.get('url')
            if not fragment_url:
                assert fragment_base_url
                fragment_url = urljoin(fragment_base_url, fragment['path'])

            fragments_to_download.append({
                'frag_index': frag_index,
                'index': i,
                'url': fragment_url,
            })

        return fragments_to_download

    @staticmethod
    def _accept_live():
        return False

    @staticmethod
    def _ignore_lethal_error():
        return False


class YoutubeDlFromStartDashFD(DashSegmentsFD):

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

        ie = self.ydl.get_info_extractor('Youtube')
        return ie._manifest_fragments(manifest_url, stream_number, lack_early=lack_early)

    @staticmethod
    def _accept_live():
        return True

    @staticmethod
    def _ignore_lethal_error():
        return True

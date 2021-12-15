from __future__ import unicode_literals

from ..downloader import get_suitable_downloader
from .fragment import FragmentFD

from ..utils import (
    time_millis,
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

        requested_formats = [{**info_dict, **fmt} for fmt in info_dict.get('requested_formats', [])]
        args = []
        for fmt in requested_formats or [info_dict]:
            is_live, fragment_count = self._calculate_fragment_count(fmt)
            real_filename = fmt.get('filepath') or filename
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

            fragments_to_download = self._get_fragments(fmt, ctx)

            if real_downloader:
                self.to_screen(
                    '[%s] Fragment downloads will be delegated to %s' % (self.FD_NAME, real_downloader.get_basename()))
                info_dict['fragments'] = fragments_to_download
                fd = real_downloader(self.ydl, self.params)
                return fd.real_download(filename, info_dict)

            args.append([ctx, fragments_to_download, fmt])

        return self.download_and_append_fragments_multiple(*args)

    def _calculate_fragment_count(self, info_dict):
        return False, (1 if self.params.get('test', False) else len(info_dict['fragments']))

    def _resolve_fragments(self, fragments, ctx):
        fragments = fragments(ctx) if callable(fragments) else fragments
        return [next(fragments)] if self.params.get('test') else fragments

    def _get_fragments(self, fmt, ctx):
        fragment_base_url = fmt.get('fragment_base_url')
        fragments = self._resolve_fragments(fmt['fragments'], ctx)

        frag_index = 0
        for i, fragment in enumerate(fragments):
            frag_index += 1
            if frag_index <= ctx['fragment_index']:
                continue
            fragment_url = fragment.get('url')
            if not fragment_url:
                assert fragment_base_url
                fragment_url = urljoin(fragment_base_url, fragment['path'])

            yield {
                'frag_index': frag_index,
                'index': i,
                'url': fragment_url,
            }

    @staticmethod
    def _accept_live():
        return False


class YoutubeDlFromStartDashFD(DashSegmentsFD):

    FD_NAME = 'ytlivestartdash'

    def _calculate_fragment_count(self, info_dict):
        return True, None

    @staticmethod
    def _accept_live():
        return True

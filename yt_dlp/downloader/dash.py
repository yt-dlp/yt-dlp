from __future__ import unicode_literals
import time

from ..downloader import get_suitable_downloader
from .fragment import FragmentFD

from ..utils import urljoin


class DashSegmentsFD(FragmentFD):
    """
    Download segments in a DASH manifest. External downloaders can take over
    the fragment downloads by supporting the 'dash_frag_urls' protocol
    """

    FD_NAME = 'dashsegments'

    def real_download(self, filename, info_dict):
        if info_dict.get('is_live') and set(info_dict['protocol'].split('+')) != {'http_dash_segments_generator'}:
            self.report_error('Live DASH videos are not supported')

        real_start = time.time()
        real_downloader = get_suitable_downloader(
            info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        requested_formats = [{**info_dict, **fmt} for fmt in info_dict.get('requested_formats', [])]
        args = []
        for fmt in requested_formats or [info_dict]:
            try:
                fragment_count = 1 if self.params.get('test') else len(fmt['fragments'])
            except TypeError:
                fragment_count = None
            ctx = {
                'filename': fmt.get('filepath') or filename,
                'live': 'is_from_start' if fmt.get('is_from_start') else fmt.get('is_live'),
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
                info_dict['fragments'] = list(fragments_to_download)
                fd = real_downloader(self.ydl, self.params)
                return fd.real_download(filename, info_dict)

            args.append([ctx, fragments_to_download, fmt])

        return self.download_and_append_fragments_multiple(*args)

    def _resolve_fragments(self, fragments, ctx):
        fragments = fragments(ctx) if callable(fragments) else fragments
        return [next(iter(fragments))] if self.params.get('test') else fragments

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

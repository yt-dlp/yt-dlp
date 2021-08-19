from __future__ import unicode_literals

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
        if info_dict.get('is_live'):
            self.report_error('Live DASH videos are not supported')

        fragment_base_url = info_dict.get('fragment_base_url')
        fragments = info_dict['fragments'][:1] if self.params.get(
            'test', False) else info_dict['fragments']

        real_downloader = get_suitable_downloader(
            info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        ctx = {
            'filename': filename,
            'total_frags': len(fragments),
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx, info_dict)

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

        if real_downloader:
            self.to_screen(
                '[%s] Fragment downloads will be delegated to %s' % (self.FD_NAME, real_downloader.get_basename()))
            info_copy = info_dict.copy()
            info_copy['fragments'] = fragments_to_download
            fd = real_downloader(self.ydl, self.params)
            return fd.real_download(filename, info_copy)

        return self.download_and_append_fragments(ctx, fragments_to_download, info_dict)

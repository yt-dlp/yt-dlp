from __future__ import unicode_literals

from ..downloader import _get_real_downloader
from .fragment import FragmentFD

from ..utils import urljoin


class DashSegmentsFD(FragmentFD):
    """
    Download segments in a DASH manifest. External downloaders can take over
    the fragment downloads by supporting the 'dash_frag_urls' protocol
    """

    FD_NAME = 'dashsegments'

    def real_download(self, filename, info_dict):
        fragment_base_url = info_dict.get('fragment_base_url')
        fragments = info_dict['fragments'][:1] if self.params.get(
            'test', False) else info_dict['fragments']

        real_downloader = _get_real_downloader(info_dict, 'dash_frag_urls', self.params, None)

        ctx = {
            'filename': filename,
            'total_frags': len(fragments),
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx)

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
            # TODO: Make progress updates work without hooking twice
            # for ph in self._progress_hooks:
            #     fd.add_progress_hook(ph)
            success = fd.real_download(filename, info_copy)
            if not success:
                return False
        else:
            self.download_and_append_fragments(ctx, fragments_to_download, info_dict)
        return True

from __future__ import unicode_literals

from .fragment import FragmentFD
from ..compat import compat_urllib_error
from ..utils import (
    DownloadError,
    urljoin,
)

from .external import (
    get_external_downloader,
    Aria2cFD
)

class DashSegmentsFD(FragmentFD):
    """
    Download segments in a DASH manifest
    """

    FD_NAME = 'dashsegments'

    def real_download(self, filename, info_dict):
        fragment_base_url = info_dict.get('fragment_base_url')
        fragments = info_dict['fragments'][:1] if self.params.get(
            'test', False) else info_dict['fragments']

        external_downloader = self.params.get('external_downloader')

        ctx = {
            'filename': filename,
            'total_frags': len(fragments),
        }

        self._prepare_and_start_frag_download(ctx)

        fragment_retries = self.params.get('fragment_retries', 0)
        skip_unavailable_fragments = self.params.get('skip_unavailable_fragments', True)

        fragment_urls = []
        frag_index = 0
        for i, fragment in enumerate(fragments):
            frag_index += 1
            if frag_index <= ctx['fragment_index']:
                continue
            # In DASH, the first segment contains necessary headers to
            # generate a valid MP4 file, so always abort for the first segment
            fatal = i == 0 or not skip_unavailable_fragments
            count = 0
            while count <= fragment_retries:
                try:
                    fragment_url = fragment.get('url')
                    if not fragment_url:
                        assert fragment_base_url
                        fragment_url = urljoin(fragment_base_url, fragment['path'])
                    if external_downloader == 'aria2c':
                        fragment_urls.append(fragment_url)
                    else:
                        success, frag_content = self._download_fragment(ctx, fragment_url, info_dict)
                        if not success:
                            return False
                        self._append_fragment(ctx, frag_content)
                    break
                except compat_urllib_error.HTTPError as err:
                    # YouTube may often return 404 HTTP error for a fragment causing the
                    # whole download to fail. However if the same fragment is immediately
                    # retried with the same request data this usually succeeds (1-2 attempts
                    # is usually enough) thus allowing to download the whole file successfully.
                    # To be future-proof we will retry all fragments that fail with any
                    # HTTP error.
                    count += 1
                    if count <= fragment_retries:
                        self.report_retry_fragment(err, frag_index, count, fragment_retries)
                except DownloadError:
                    # Don't retry fragment if error occurred during HTTP downloading
                    # itself since it has own retry settings
                    if not fatal:
                        self.report_skip_fragment(frag_index)
                        break
                    raise

            if count > fragment_retries:
                if not fatal:
                    self.report_skip_fragment(frag_index)
                    continue
                self.report_error('giving up after %s fragment retries' % fragment_retries)
                return False

        if external_downloader == 'aria2c':
            ctx['url_list'] = fragment_urls
            downloader = Aria2cFD(self, self.params)
            downloader.real_download(ctx['filename'], ctx)
            
        self._finish_frag_download(ctx)

        return True

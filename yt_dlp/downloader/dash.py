from __future__ import unicode_literals

try:
    import concurrent.futures
    can_threaded_download = True
except ImportError:
    can_threaded_download = False

from ..downloader import _get_real_downloader
from .fragment import FragmentFD

from ..compat import compat_urllib_error
from ..utils import (
    DownloadError,
    sanitize_open,
    urljoin,
)


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

        fragment_retries = self.params.get('fragment_retries', 0)
        skip_unavailable_fragments = self.params.get('skip_unavailable_fragments', True)

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
            def download_fragment(fragment):
                i = fragment['index']
                frag_index = fragment['frag_index']
                fragment_url = fragment['url']

                ctx['fragment_index'] = frag_index

                # In DASH, the first segment contains necessary headers to
                # generate a valid MP4 file, so always abort for the first segment
                fatal = i == 0 or not skip_unavailable_fragments
                count = 0
                while count <= fragment_retries:
                    try:
                        success, frag_content = self._download_fragment(ctx, fragment_url, info_dict)
                        if not success:
                            return False, frag_index
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
                            break
                        raise

                if count > fragment_retries:
                    if not fatal:
                        return False, frag_index
                    self.report_error('Giving up after %s fragment retries' % fragment_retries)
                    return False, frag_index

                return frag_content, frag_index

            def append_fragment(frag_content, frag_index):
                if frag_content:
                    fragment_filename = '%s-Frag%d' % (ctx['tmpfilename'], frag_index)
                    try:
                        file, frag_sanitized = sanitize_open(fragment_filename, 'rb')
                        ctx['fragment_filename_sanitized'] = frag_sanitized
                        file.close()
                        self._append_fragment(ctx, frag_content)
                        return True
                    except FileNotFoundError:
                        if skip_unavailable_fragments:
                            self.report_skip_fragment(frag_index)
                            return True
                        else:
                            self.report_error(
                                'fragment %s not found, unable to continue' % frag_index)
                            return False
                else:
                    if skip_unavailable_fragments:
                        self.report_skip_fragment(frag_index)
                        return True
                    else:
                        self.report_error(
                            'fragment %s not found, unable to continue' % frag_index)
                        return False

            max_workers = self.params.get('concurrent_fragment_downloads', 1)
            if can_threaded_download and max_workers > 1:
                self.report_warning('The download speed shown is only of one thread. This is a known issue')
                with concurrent.futures.ThreadPoolExecutor(max_workers) as pool:
                    futures = [pool.submit(download_fragment, fragment) for fragment in fragments_to_download]
                    # timeout must be 0 to return instantly
                    done, not_done = concurrent.futures.wait(futures, timeout=0)
                    try:
                        while not_done:
                            # Check every 1 second for KeyboardInterrupt
                            freshly_done, not_done = concurrent.futures.wait(not_done, timeout=1)
                            done |= freshly_done
                    except KeyboardInterrupt:
                        for future in not_done:
                            future.cancel()
                        # timeout must be none to cancel
                        concurrent.futures.wait(not_done, timeout=None)
                        raise KeyboardInterrupt
                results = [future.result() for future in futures]

                for frag_content, frag_index in results:
                    result = append_fragment(frag_content, frag_index)
                    if not result:
                        return False
            else:
                for fragment in fragments_to_download:
                    frag_content, frag_index = download_fragment(fragment)
                    result = append_fragment(frag_content, frag_index)
                    if not result:
                        return False

            self._finish_frag_download(ctx)
        return True

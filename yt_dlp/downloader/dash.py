import time
import urllib.parse

from . import get_suitable_downloader
from .fragment import FragmentFD
from ..utils import ReExtractInfo, update_url_query, urljoin


class DashSegmentsFD(FragmentFD):
    """
    Download segments in a DASH manifest. External downloaders can take over
    the fragment downloads by supporting the 'dash_frag_urls' protocol
    """

    FD_NAME = 'dashsegments'

    def real_download(self, filename, info_dict):
        if 'http_dash_segments_generator' in info_dict['protocol'].split('+'):
            real_downloader = None  # No external FD can support --live-from-start
        else:
            if info_dict.get('is_live'):
                self.report_error('Live DASH videos are not supported')
            real_downloader = get_suitable_downloader(
                info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        real_start = time.time()
        requested_formats = [{**info_dict, **fmt} for fmt in info_dict.get('requested_formats', [])]

        args = []
        for fmt in requested_formats or [info_dict]:
            if isinstance(fmt['fragments'], str):
                is_live_stream = fmt.get('is_live') or fmt.get('is_from_start')
                if not is_live_stream:
                    raise ReExtractInfo('the stream needs to be re-extracted', expected=True)
                else:
                    # live handled by extractor
                    self.to_screen(
                        f'[{self.FD_NAME}] Warning: fragments is string type for live stream')
                    raise ReExtractInfo('live manifest needs refresh', expected=True)
            
            try:
                fragment_count = 1 if self.params.get('test') else len(fmt['fragments'])
            except TypeError:
                # fragments are generator on live
                fragment_count = None
            
            if fmt.get('is_live') or fmt.get('is_from_start'):
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

            extra_query = None
            extra_param_to_segment_url = info_dict.get('extra_param_to_segment_url')
            if extra_param_to_segment_url:
                extra_query = urllib.parse.parse_qs(extra_param_to_segment_url)

            fragments_to_download = self._get_fragments(fmt, ctx, extra_query)

            if real_downloader:
                self.to_screen(
                    f'[{self.FD_NAME}] Fragment downloads will be delegated to {real_downloader.get_basename()}')
                info_dict['fragments'] = list(fragments_to_download)
                fd = real_downloader(self.ydl, self.params)
                return fd.real_download(filename, info_dict)

            args.append([ctx, fragments_to_download, fmt])

        return self.download_and_append_fragments_multiple(*args, is_fatal=lambda idx: idx == 0)

    def _resolve_fragments(self, fragments, ctx):
        fragments = fragments(ctx) if callable(fragments) else fragments
        return [next(iter(fragments))] if self.params.get('test') else fragments

    def _get_fragments(self, fmt, ctx, extra_query):
        fragment_base_url = fmt.get('fragment_base_url')
        fragments = self._resolve_fragments(fmt['fragments'], ctx)
        catching_up_shown = False 

        frag_index = 0
        for i, fragment in enumerate(fragments):
            if ctx.get('live_ended_gracefully'):
                if self.params.get('verbose'):
                    self.to_screen(f'[{self.FD_NAME}] Live stream end detected. Stopping fragment generation.')
                return

            frag_index += 1
            if frag_index <= ctx['fragment_index']:
                continue

            fragment_url = fragment.get('url')
            if not fragment_url:
                assert fragment_base_url
                fragment_url = urljoin(fragment_base_url, fragment['path'])

            if extra_query:
                fragment_url = update_url_query(fragment_url, extra_query)

            current_total = fragment.get('fragment_count')
            if not catching_up_shown and ctx.get('live') == 'is_from_start' and current_total:
                self.to_screen(
                    f'[{self.FD_NAME}] Catching up to live: fragments total >{current_total}')
                catching_up_shown = True

            yield {
                'frag_index': frag_index,
                'fragment_count': current_total,
                'index': i,
                'url': fragment_url,
            }

        if ctx.get('live') and self.params.get('verbose'):
            self.to_screen(
                f'[DEBUG][{self.FD_NAME}] Fragment generator {ctx.get("live")} exhausted after {frag_index} fragments.')


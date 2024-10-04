import base64
import binascii
import json
import time
import urllib.parse

from . import get_suitable_downloader
from .fragment import FragmentFD
from ..networking import Request
from ..networking.exceptions import RequestError
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
            # Re-extract if --load-info-json is used and 'fragments' was originally a generator
            # See https://github.com/yt-dlp/yt-dlp/issues/13906
            if isinstance(fmt['fragments'], str):
                raise ReExtractInfo('the stream needs to be re-extracted', expected=True)

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

        if 'dash_cenc' in info_dict and not info_dict['dash_cenc'].get('key'):
            self._get_clearkey_cenc(info_dict)

        return self.download_and_append_fragments_multiple(*args, is_fatal=lambda idx: idx == 0)

    def _resolve_fragments(self, fragments, ctx):
        fragments = fragments(ctx) if callable(fragments) else fragments
        return [next(iter(fragments))] if self.params.get('test') else fragments

    def _get_fragments(self, fmt, ctx, extra_query):
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
            if extra_query:
                fragment_url = update_url_query(fragment_url, extra_query)

            yield {
                'frag_index': frag_index,
                'fragment_count': fragment.get('fragment_count'),
                'index': i,
                'url': fragment_url,
            }

    def _get_clearkey_cenc(self, info_dict):
        dash_cenc = info_dict.get('dash_cenc', {})
        laurl = dash_cenc.get('laurl')
        if not laurl:
            self.report_error('No Clear Key license server URL for encrypted DASH stream')
            return
        key_ids = dash_cenc.get('key_ids')
        if not key_ids:
            self.report_error('No requested CENC KIDs for encrypted DASH stream')
            return
        payload = json.dumps({
            'kids': [
                base64.urlsafe_b64encode(bytes.fromhex(k)).decode().rstrip('=')
                for k in key_ids
            ],
            'type': 'temporary',
        }).encode()
        try:
            response = self.ydl.urlopen(Request(
                laurl, data=payload, headers={'Content-Type': 'application/json'}))
            data = json.loads(response.read())
        except (RequestError, json.JSONDecodeError) as err:
            self.report_error(f'Failed to retrieve key from Clear Key license server: {err}')
            return
        keys = data.get('keys', [])
        if len(keys) > 1:
            self.report_warning('Clear Key license server returned multiple keys but only single key CENC is supported')
        for key in keys:
            k = key.get('k')
            if k:
                try:
                    dash_cenc['key'] = base64.urlsafe_b64decode(f'{k}==').hex()
                    info_dict['dash_cenc'] = dash_cenc
                    return
                except (ValueError, binascii.Error):
                    pass
        self.report_error('Clear key license server did not return any valid CENC keys')

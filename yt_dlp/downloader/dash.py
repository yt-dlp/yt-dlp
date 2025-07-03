import base64
import binascii
import json
import time
import urllib.parse

from . import get_suitable_downloader
from .fragment import FragmentFD
from ..networking import Request
from ..networking.exceptions import RequestError
from ..utils import remove_start, traverse_obj, update_url_query, urljoin


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

            hls_aes = fmt.get('hls_aes', {})
            if hls_aes:
                decrypt_info = {'METHOD', 'AES-128'}
                key = hls_aes.get('key')
                if key:
                    key = binascii.unhexlify(remove_start(key, '0x'))
                    assert len(key) in (16, 24, 32), 'Invalid length for HLS AES-128 key'
                    decrypt_info['KEY'] = key
                iv = hls_aes.get('iv')
                if iv:
                    iv = binascii.unhexlify(remove_start(iv, '0x').zfill(32))
                    decrypt_info['IV'] = iv
                uri = hls_aes.get('uri')
                if uri:
                    if extra_query:
                        uri = update_url_query(uri, extra_query)
                    decrypt_info['URI'] = uri
                ctx['decrypt_info'] = decrypt_info

            fragments_to_download = self._get_fragments(fmt, ctx, extra_query)

            if real_downloader:
                self.to_screen(
                    f'[{self.FD_NAME}] Fragment downloads will be delegated to {real_downloader.get_basename()}')
                info_dict['fragments'] = list(fragments_to_download)
                fd = real_downloader(self.ydl, self.params)
                return fd.real_download(filename, info_dict)

            args.append([ctx, fragments_to_download, fmt])

        cenc_key = traverse_obj(info_dict, ('dash_cenc', 'key'))
        cenc_key_ids = traverse_obj(info_dict, ('dash_cenc', 'key_ids'))
        clearkey_laurl = traverse_obj(info_dict, ('dash_cenc', 'laurl'))
        if not cenc_key and cenc_key_ids and clearkey_laurl:
            self._get_clearkey_cenc(info_dict, clearkey_laurl, cenc_key_ids)

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
                'decrypt_info': ctx.get('decrypt_info', {'METHOD': 'NONE'}),
            }

    def _get_clearkey_cenc(self, info_dict, laurl, key_ids):
        dash_cenc = info_dict.get('dash_cenc', {})
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
                    dash_cenc.update({'key': base64.urlsafe_b64decode(f'{k}==').hex()})
                    info_dict['dash_cenc'] = dash_cenc
                    return
                except (ValueError, binascii.Error):
                    pass
        self.report_error('Clear key license server did not return any valid CENC keys')

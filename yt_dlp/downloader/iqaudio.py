from .fragment import FragmentFD

import gzip

class IqAudioFragmentFD(FragmentFD):
    """
    Downloads a list of audio fragments, the first fragment is always a gzipped header.
    """

    FD_NAME = 'IqAudioFragmentDownloader'

    def real_download(self, filename, info_dict):
        format = None
        for f in info_dict['formats']:
            if f['format_id'] == info_dict['format_id']:
                format = f
                break

        if format == None:
            return

        fragments = []
        totalFrags = 0
        for url in format['fragment_urls']:
            fragments.append({
                'frag_index': totalFrags,
                'url': url
            })
            totalFrags += 1

        ctx = {
            'filename': filename,
            'total_frags': totalFrags,
            'ad_frags': 0,
        }
        self._prepare_and_start_frag_download(ctx, info_dict)

        def decompress_header(fragment_content, fragment_index):
            # The first fragment is just gzipped, so decompress it here.
            if fragment_index == 0:
                return gzip.decompress(fragment_content)
            return fragment_content

        self.download_and_append_fragments(ctx, fragments, info_dict, pack_func=decompress_header)
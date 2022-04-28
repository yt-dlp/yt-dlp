from .fragment import FragmentFD
import gzip


class IqAudioFragmentFD(FragmentFD):
    """
    Downloads a list of audio fragments, the first fragment is always a gzipped header.
    """

    FD_NAME = 'IqAudioFragmentDownloader'

    def real_download(self, filename, info_dict):
        fragments = []
        total_frags = 0
        for frag in info_dict['fragments']:
            fragments.append({
                'frag_index': total_frags,
                'url': frag['url']
            })
            total_frags += 1

        ctx = {
            'filename': filename,
            'total_frags': total_frags,
            'ad_frags': 0,
        }
        self._prepare_and_start_frag_download(ctx, info_dict)

        def decompress_header(fragment_content, fragment_index):
            # The first fragment is just gzipped, so decompress it here.
            if fragment_index == 0:
                return gzip.decompress(fragment_content)
            return fragment_content

        self.download_and_append_fragments(ctx, fragments, info_dict, pack_func=decompress_header)

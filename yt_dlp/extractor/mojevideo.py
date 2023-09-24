from .common import InfoExtractor


class MojevideoIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?mojevideo\.sk/video/(?P<id>\w+)'

    _TESTS = [
        {
            'url': 'https://www.mojevideo.sk/video/3d17c/chlapci_dobetonovali_sme_mame_hotovo.html',
            'md5': '384a4628bd2bbd261c5206cf77c38c17',
            'info_dict': {
                'id': '250236',
                'ext': 'mp4',
                'title': 'Chlapci dobetónovali sme, máme hotovo! - Mojevideo',
                'description': 'Celodenná práca bola za pár sekúnd fuč. Betón stiekol k susedovi, kam aj zrútil celý plot, ktorý polámal aj tuje....'
            }
        }
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        v_id = self._search_regex(r'\bvId=(\d+)', webpage, 'video id')
        v_exp = self._search_regex(r'\bvEx=\'(\d+)', webpage, 'expiry')
        v_hash = self._search_regex(r'\bvHash=\[([^\]]+)', webpage, 'hash').split(",")[0].replace("'", "")
        v_title = self._html_extract_title(webpage, 'title')

        return {
            'id': v_id,
            'url': f'https://cache01.mojevideo.sk/securevideos69/{v_id}.mp4?md5={v_hash}&expires={v_exp}',
            'title': v_title,
            'description': self._og_search_description(webpage, default=None),

        }

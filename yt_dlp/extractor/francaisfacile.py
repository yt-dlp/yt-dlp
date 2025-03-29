from .common import InfoExtractor


class FrancaisFacileIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/francaisfacile\.rfi\.fr\/fr\/(actualit%C3%A9|podcasts\/[^\/]+)\/(?P<id>\d+)-.*'
    IE_NAME = 'francaisfacile'
    _TESTS = [
        {
            'url': 'https://francaisfacile.rfi.fr/fr/podcasts/un-mot-une-histoire/20250317-le-mot-de-david-foenkinos-peut-%C3%AAtre',
            'md5': 'db83c2cc2589b4c24571c6b6cf14f5f1',
            'info_dict': {
                'id': '20250317',
                'title': 'Le mot de David Foenkinos: «peut-être» - Un mot, une histoire',
                'url': 'https://aod-fle.akamaized.net/fle/sounds/fr/2025/03/17/4ca6cbbe-0315-11f0-a85b-005056a97652.mp3',
                'ext': 'mp3',
            },
        },
        {
            'url': 'https://francaisfacile.rfi.fr/fr/actualit%C3%A9/20250307-argentine-le-sac-d-un-alpiniste-retrouv%C3%A9-40-ans-apr%C3%A8s-sa-mort',
            'md5': 'b8c3a63652d4ae8e8092dda5700c1cd9',
            'info_dict': {
                'id': '20250307',
                'title': 'Argentine: le sac d\'un alpiniste retrouvé 40 ans après sa mort',
                'url': 'https://aod-fle.akamaized.net/fle/sounds/fr/2025/03/07/8edf4082-fb46-11ef-8a37-005056bf762b.mp3',
                'ext': 'mp3',
            },
        },
        {
            'url': 'https://francaisfacile.rfi.fr/fr/actualit%C3%A9/20250305-r%C3%A9concilier-les-jeunes-avec-la-lecture-gr%C3%A2ce-aux-r%C3%A9seaux-sociaux',
            'md5': '4f33674cb205744345cc835991100afa',
            'info_dict': {
                'id': '20250305',
                'title': 'Réconcilier les jeunes avec la lecture grâce aux réseaux sociaux',
                'url': 'https://aod-fle.akamaized.net/fle/sounds/fr/2025/03/05/6b6af52a-f9ba-11ef-a1f8-005056a97652.mp3',
                'ext': 'mp3',
            },
        },
    ]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:135.0) Gecko/20100101 Firefox/135.0'})
        title = self._html_extract_title(webpage, fatal=True)
        audio_url = self._html_search_regex(r'(?P<url>https://aod-fle\.akamaized\.net/fle/sounds/fr/.+?\.mp3)', webpage, 'audio URL', group='url')
        return {
            'id': audio_id,
            'title': title,
            'url': audio_url,
            'ext': 'mp3',
        }

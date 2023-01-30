from .common import InfoExtractor


class VocarooIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:vocaroo\.com|voca\.ro)/(?:embed/)?(?P<id>\w+)'
    _TESTS = [
        {
            'url': 'https://vocaroo.com/1de8yA3LNe77',
            'md5': 'c557841d5e50261777a6585648adf439',
            'info_dict': {
                'id': '1de8yA3LNe77',
                'ext': 'mp3',
                'title': 'Vocaroo video #1de8yA3LNe77',
            },
        },
        {
            'url': 'https://vocaroo.com/embed/12WqtjLnpj6g?autoplay=0',
            'md5': 'c78c00064a58f98f4770ec0e7f4de1ff',
            'info_dict': {
                'id': '12WqtjLnpj6g',
                'ext': 'mp3',
                'title': 'Vocaroo video #12WqtjLnpj6g',
            },
        },
        {
            'url': 'https://voca.ro/12D52rgpzkB0',
            'md5': 'c4a8339d8d592fc7d5ad6188431db1f7',
            'info_dict': {
                'id': '12D52rgpzkB0',
                'ext': 'mp3',
                'title': 'Vocaroo video #12D52rgpzkB0',
            },
        },
    ]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        return {
            'id': audio_id,
            'title': '',
            'url': f'https://media1.vocaroo.com/mp3/{audio_id}',
            'ext': 'mp3',
            'vcodec': 'none',
            'http_headers': {'Referer': 'https://vocaroo.com/'},
        }

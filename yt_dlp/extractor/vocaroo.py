from .common import InfoExtractor


class VocarooIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:vocaroo\.com|voca\.ro)/(?:embed/)?(?P<id>[a-zA-Z0-9]{11,12})'
    _TESTS = [
        {
            'url': 'https://vocaroo.com/1de8yA3LNe77',
            'md5': 'c557841d5e50261777a6585648adf439',
            'info_dict': {
                'id': '1de8yA3LNe77',
                'ext': 'mp3',
                'title': 'Vocaroo 1de8yA3LNe77',
            },
        },
        {
            'url': 'https://vocaroo.com/embed/my6dHeF93UR?autoplay=0',
            'only_matching': True,
        },
        {
            'url': 'https://voca.ro/15VY7fSWDqpU',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        return {
            'id': audio_id,
            'title': f'Vocaroo {audio_id}',
            'url': f'https://media1.vocaroo.com/mp3/{audio_id}',
            'ext': 'mp3',
            'http_headers': {'Referer': 'https://vocaroo.com/'},
        }

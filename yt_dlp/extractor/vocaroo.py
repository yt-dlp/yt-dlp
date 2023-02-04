from .common import InfoExtractor


class VocarooIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:vocaroo\.com|voca\.ro)/(?:embed/)?(?P<id>\w+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?://)?(?:www\.)?vocaroo\.com/embed/.+?)\1']
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
            'only_matching': True,
        },
        {
            'url': 'https://voca.ro/12D52rgpzkB0',
            'only_matching': True,
        },
    ]

    _WEBPAGE_TESTS = [
        {
            'url': 'https://qbnu.github.io/cool.html',
            'md5': 'f322e529275dd8a47994919eeac404a5',
            'info_dict': {
                'id': '19cgWmKO6AmC',
                'ext': 'mp3',
                'title': 'Vocaroo video #19cgWmKO6AmC',
            },
        },
    ]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        if len(audio_id) == 10 or (len(audio_id) == 12 and audio_id[0] == '1'):
            media_subdomain = 'media1'
        else:
            media_subdomain = 'media'

        return {
            'id': audio_id,
            'title': '',
            'url': f'https://{media_subdomain}.vocaroo.com/mp3/{audio_id}',
            'ext': 'mp3',
            'vcodec': 'none',
            'http_headers': {'Referer': 'https://vocaroo.com/'},
        }

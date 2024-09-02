from .common import InfoExtractor


class Canal1IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|noticias\.)?canal1\.com\.co/(?:[^?#&])+/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://canal1.com.co/noticias/napa-i-una-cadena-de-produccion-de-arroz-que-se-quedo-en-veremos-y-abandonada-en-el-departamento-del-choco/',
        'info_dict': {
            'id': '63b39f6b354977084b85ab54',
            'display_id': 'napa-i-una-cadena-de-produccion-de-arroz-que-se-quedo-en-veremos-y-abandonada-en-el-departamento-del-choco',
            'title': 'Ñapa I Una cadena de producción de arroz que se quedó en veremos y abandonada en el departamento del Chocó',
            'description': 'md5:bc49c6d64d20610ea1e7daf079a0d013',
            'thumbnail': r're:^https?://[^?#]+63b39f6b354977084b85ab54',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://noticias.canal1.com.co/noticias/tres-i-el-triste-record-que-impuso-elon-musk-el-dueno-de-tesla-y-de-twitter/',
        'info_dict': {
            'id': '63b39e93f5fd223aa32250fb',
            'display_id': 'tres-i-el-triste-record-que-impuso-elon-musk-el-dueno-de-tesla-y-de-twitter',
            'title': 'Tres I El triste récord que impuso Elon Musk, el dueño de Tesla y de Twitter',
            'description': 'md5:d9f691f131a21ce6767ca6c05d17d791',
            'thumbnail': r're:^https?://[^?#]+63b39e93f5fd223aa32250fb',
            'ext': 'mp4',
        },
    }, {
        # Geo-restricted to Colombia
        'url': 'https://canal1.com.co/programas/guerreros-canal-1/video-inedito-guerreros-despedida-kewin-zarate/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        return self.url_result(
            self._search_regex(r'"embedUrl"\s*:\s*"([^"]+)', webpage, 'embed url'),
            display_id=display_id, url_transparent=True)

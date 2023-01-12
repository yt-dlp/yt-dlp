from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    remove_end,
)


class BioBioChileTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:tv|www)\.biobiochile\.cl/(?:notas|noticias)/(?:[^/]+/)+(?P<id>[^/]+)\.shtml'

    _TESTS = [{
        'url': 'http://tv.biobiochile.cl/notas/2015/10/21/sobre-camaras-y-camarillas-parlamentarias.shtml',
        'md5': '26f51f03cf580265defefb4518faec09',
        'info_dict': {
            'id': 'sobre-camaras-y-camarillas-parlamentarias',
            'ext': 'mp4',
            'title': 'Sobre Cámaras y camarillas parlamentarias',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Fernando Atria',
        },
        'skip': 'URL expired and redirected to http://www.biobiochile.cl/portada/bbtv/index.html',
    }, {
        # different uploader layout
        'url': 'http://tv.biobiochile.cl/notas/2016/03/18/natalia-valdebenito-repasa-a-diputado-hasbun-paso-a-la-categoria-de-hablar-brutalidades.shtml',
        'md5': 'edc2e6b58974c46d5b047dea3c539ff3',
        'info_dict': {
            'id': 'natalia-valdebenito-repasa-a-diputado-hasbun-paso-a-la-categoria-de-hablar-brutalidades',
            'ext': 'mp4',
            'title': 'Natalia Valdebenito repasa a diputado Hasbún: Pasó a la categoría de hablar brutalidades',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Piangella Obrador',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'URL expired and redirected to http://www.biobiochile.cl/portada/bbtv/index.html',
    }, {
        'url': 'http://www.biobiochile.cl/noticias/bbtv/comentarios-bio-bio/2016/07/08/edecanes-del-congreso-figuras-decorativas-que-le-cuestan-muy-caro-a-los-chilenos.shtml',
        'info_dict': {
            'id': 'b4xd0LK3SK',
            'ext': 'mp4',
            # TODO: fix url_transparent information overriding
            # 'uploader': 'Juan Pablo Echenique',
            'title': 'Comentario Oscar Cáceres',
        },
        'params': {
            # empty m3u8 manifest
            'skip_download': True,
        },
    }, {
        'url': 'http://tv.biobiochile.cl/notas/2015/10/22/ninos-transexuales-de-quien-es-la-decision.shtml',
        'only_matching': True,
    }, {
        'url': 'http://tv.biobiochile.cl/notas/2015/10/21/exclusivo-hector-pinto-formador-de-chupete-revela-version-del-ex-delantero-albo.shtml',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        rudo_url = self._search_regex(
            r'<iframe[^>]+src=(?P<q1>[\'"])(?P<url>(?:https?:)?//rudo\.video/vod/[0-9a-zA-Z]+)(?P=q1)',
            webpage, 'embed URL', None, group='url')
        if not rudo_url:
            raise ExtractorError('No videos found')

        title = remove_end(self._og_search_title(webpage), ' - BioBioChile TV')

        thumbnail = self._og_search_thumbnail(webpage)
        uploader = self._html_search_regex(
            r'<a[^>]+href=["\'](?:https?://(?:busca|www)\.biobiochile\.cl)?/(?:lista/)?(?:author|autor)[^>]+>(.+?)</a>',
            webpage, 'uploader', fatal=False)

        return {
            '_type': 'url_transparent',
            'url': rudo_url,
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'uploader': uploader,
        }

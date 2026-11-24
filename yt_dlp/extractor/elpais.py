from .common import InfoExtractor
from ..utils import (
    str_or_none,
    traverse_obj,
    url_or_none,
)


class ElPaisIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^.]+\.)?elpais\.com/.*/(?P<id>[^/#?]+)\.html(?:$|[?#])'
    IE_DESC = 'El País'

    _TESTS = [{
        'url': 'http://elpais.com/elpais/2017/01/26/ciencia/1485456786_417876.html',
        'md5': 'cd8cba33f974f69ed82df788ad43eef8',
        'info_dict': {
            'id': '1485456786_417876',
            'ext': 'mp4',
            'title': 'Hallado un barco de la antigua Roma que naufragó en Baleares hace 1.800 años',
            'description': 'Un submarinista contempla el pecio de Cabrera, que contiene cientos de ánforas',
            'thumbnail': 'https://imagenes.elpais.com/resizer/v2/https%3A%2F%2Fep01.epimg.net%2Felpais%2Fimagenes%2F2017%2F01%2F26%2Fciencia%2F1485456786_417876_1485523827_noticia_fotograma.jpg?auth=b9ed873402809633a5ac8bc154dcd13e468547d34bbd82e0808f9e2813eb7542&width=1960&height=1103&smart=true',
        },
    }, {
        'url': 'https://elpais.com/gastronomia/el-comidista/2024-07-16/la-ensalada-de-pasta-mas-verde.html',
        'md5': '3db968bf1d29b8fa723fd8cfb30d5d28',
        'info_dict': {
            'id': 'la-ensalada-de-pasta-mas-verde',
            'ext': 'mp4',
            'title': 'La ensalada de pasta más verde | EL COMIDISTA',
            'description': 'La ensalada de pasta más verde | EL COMIDISTA',
            'thumbnail': 'https://imagenes.elpais.com/resizer/v2/B4O2NY6B2FCE7KWOMO2CJH7FYQ.png?auth=bea914a842eba835a6ea92169acb94b977c5fe3a4564b2b69ef27ac9e7199668&width=1960&height=1103&smart=true',
        },
    }, {
        'url': 'http://epv.elpais.com/epv/2017/02/14/programa_la_voz_de_inaki/1487062137_075943.html',
        'info_dict': {
            'id': '1487062137_075943',
            'ext': 'mp4',
            'title': 'Disyuntivas',
            'description': 'md5:0d538b71b6c2ec519fd7899811fb3f23',
            'thumbnail': 'https://imagenes.elpais.com/resizer/v2/https%3A%2F%2Fep01.epimg.net%2Felpais%2Fimagenes%2F2017%2F02%2F14%2Fvideos%2F1487058850_493037_1487059369_noticia_fotograma.jpg?auth=1e1691499249851785dadbec92da3bfacdfef6cf6404845599c0c9295271d9e4&width=1960&height=1103&smart=true',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_info = self._search_json_ld(webpage, video_id)

        return {
            'id': video_id,
            **traverse_obj(video_info, {
                'title': ('title', {str_or_none}),
                'url': ('url'),
                'thumbnail': ('thumbnails', 0, 'url', {url_or_none}),
                'description': ('description', {str_or_none}),
            }),
        }

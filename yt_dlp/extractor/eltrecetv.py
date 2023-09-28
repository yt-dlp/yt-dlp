from .common import InfoExtractor


class ElTreceTVIE(InfoExtractor):
    IE_DESC = 'El Trece TV (Argentina)'
    _VALID_URL = r'https?://(?:www\.)?eltrecetv.com.ar/(?:[\w\-]+)/capitulos/temporada-(?:\d+)/(?P<id>[\w\-]+)/?'
    _TESTS = [
        {
            'url': 'https://www.eltrecetv.com.ar/ahora-caigo/capitulos/temporada-2023/programa-del-280823/',
            'md5': 'e0a2033e020f423c0e620ec8471b54f3',
            'info_dict': {
                'id': 'AHCA25082023145927244603575',
                'ext': 'mp4',
                'title': 'AHORA CAIGO - Programa 28/08/23',
                'thumbnail': 'https://thumbs.vodgc.net/AHCA25082023145927244603575.jpg?377333',
            }
        },
        {
            'url': 'https://www.eltrecetv.com.ar/poco-correctos/capitulos/temporada-2023/programa-del-250923-invitada-dalia-gutmann/',
            'md5': 'c6066e6ea4a4b7d11a8c4cc8cb5a0c85',
            'info_dict': {
                'id': '804C6158638F598B4903394E9707B6EB129',
                'ext': 'mp4',
                'title': 'POCO CORRECTOS - Programa 25/09/23',
                'thumbnail': 'https://thumbs.vodgc.net/804C6158638F598B4903394E9707B6EB129.jpg?194429',
            }
        },
        {
            'url': 'https://www.eltrecetv.com.ar/argentina-tierra-de-amor-y-venganza/capitulos/temporada-2023/atav-2-capitulo-121-del-250923/',
            'only_matching': True,
        },
        {
            'url': 'https://www.eltrecetv.com.ar/ahora-caigo/capitulos/temporada-2023/programa-del-250923/',
            'only_matching': True,
        },
        {
            'url': 'https://www.eltrecetv.com.ar/pasaplatos/capitulos/temporada-2023/pasaplatos-el-restaurante-del-250923/',
            'only_matching': True,
        },
        {
            'url': 'https://www.eltrecetv.com.ar/el-galpon/capitulos/temporada-2023/programa-del-160923-invitado-raul-lavie/',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        slug = self._match_id(url)
        webpage = self._download_webpage(url, slug)

        json_all = self._search_json(r'Fusion.globalContent\s*=', webpage, 'content', slug)
        config = json_all.get('promo_items').get('basic').get('embed').get('config')

        title = config.get('title')
        thumbnail = config.get('thumbnail')

        video_id = self._search_regex(r'/([A-Z0-9]+).jpg', thumbnail, 'video_id')
        url = 'https://vod.vodgc.net/gid1/vod/Artear/Eltrece/75/%s_720P.mp4' % video_id

        return {
            'id': video_id,
            'title': title,
            'url': url,
            'thumbnail': thumbnail,
        }

from .common import InfoExtractor


class ElTreceTVIE(InfoExtractor):
    IE_DESC = 'El Trece TV (Argentina)'
    _VALID_URL = r'https?://(?:www\.)?eltrecetv\.com\.ar/[\w-]+/capitulos/temporada-\d+/(?P<id>[\w-]+)'
    _TESTS = [
        {
            'url': 'https://www.eltrecetv.com.ar/ahora-caigo/capitulos/temporada-2023/programa-del-061023/',
            'md5': '71a66673dc63f9a5939d97bfe4b311ba',
            'info_dict': {
                'id': 'AHCA05102023145553329621094',
                'ext': 'mp4',
                'title': 'AHORA CAIGO - Programa 06/10/23',
                'thumbnail': 'https://thumbs.vodgc.net/AHCA05102023145553329621094.JPG?649339',
            },
        },
        {
            'url': 'https://www.eltrecetv.com.ar/poco-correctos/capitulos/temporada-2023/programa-del-250923-invitada-dalia-gutmann/',
            'only_matching': True,
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
        },
    ]

    def _real_extract(self, url):
        slug = self._match_id(url)
        webpage = self._download_webpage(url, slug)
        config = self._search_json(
            r'Fusion.globalContent\s*=', webpage, 'content', slug)['promo_items']['basic']['embed']['config']
        video_url = config['m3u8']
        video_id = self._search_regex(r'/(\w+)\.m3u8', video_url, 'video id', default=slug)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4', m3u8_id='hls')
        formats.extend([{
            'url': f['url'][:-23],
            'format_id': f['format_id'].replace('hls', 'http'),
            'width': f.get('width'),
            'height': f.get('height'),
        } for f in formats if f['url'].endswith('/tracks-v1a1/index.m3u8') and f.get('height') != 1080])

        return {
            'id': video_id,
            'title': config.get('title'),
            'thumbnail': config.get('thumbnail'),
            'formats': formats,
            'subtitles': subtitles,
        }

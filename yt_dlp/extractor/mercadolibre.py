from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class MercadoLibreIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.|.*\.)?mercadolibre\.com\.ar/*.*/(?P<id>MLA-?[0-9]+)'

    _TESTS = [
        {
            'url': 'https://articulo.mercadolibre.com.ar/MLA-780443524-pool-profesional-mesa-de-ping-pong-comedor-accesorios-_JM#position=5&search_layout=stack&type=item&tracking_id=b9180504-37fc-4829-adff-4320ac49464c',
            'info_dict': {
                'id': 'MLA-780443524',
                'title': 'Pool Profesional + Mesa De Ping Pong + Comedor + Accesorios',
                'price': '651.999'
            },
            'playlist': [{
                'info_dict': {
                    'id': 'iUvfyU',
                    'ext': 'mp4',
                    'formats': 'mincount:2',
                    'duration': 49.08,
                    'title': 'Pool Profesional + Mesa De Ping Pong + Comedor + Accesorios',
                    'view_count': int
                }
            }
            ],
            'params': {
                'skip_download': True,
            }
        },
        {
            'url': 'https://www.mercadolibre.com.ar/motorola-moto-e22-64gb-azul-4gb-ram/p/MLA25665291?pdp_filters=seller_id%3A225480741#reco_item_pos=20&reco_backend=machinalis-seller-items-pdp&reco_backend_type=low_level&reco_client=vip-seller_items-above&reco_id=08cf53bc-f759-4c39-9253-ae21f5d75ae9',
            'info_dict': {
                'id': 'MLA25665291',
                'title': 'Motorola Moto E22 64GB Azul 4GB RAM',
                'price': '399.999',
            },
            'playlist': [{
                'info_dict': {
                    'id': 'gO27T5',
                    'ext': 'mp4',
                    'formats': 'mincount:4',
                    'duration': 56.21,
                    'title': 'Motorola Moto E22 64GB Azul 4GB RAM',
                    'view_count': int,
                }
            }
            ],
            'params': {
                'skip_download': True,
            }
        },
        {
            'url': 'https://www.mercadolibre.com.ar/sony-playstation-5-825gb-digital-edition-color-blanco-y-negro-2020/p/MLA16253015',
            'info_dict': {
                'id': 'MLA16253015',
                'title': 'Sony PlayStation 5 825GB Digital Edition  color blanco y negro 2020',
                'price': '1.779.999',
            },
            'playlist_mincount': 2,
            'params': {
                'skip_download': True,
            }
        },
    ]

    def _real_initialize(self):
        self._request_webpage('https://www.mercadolibre.com.ar/', None, 'Setting up session')

    def _real_extract(self, url):

        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        title = self._search_regex(r'<h1 class="ui-pdp-title">(.*?)</h1>', webpage, 'title', fatal=True)
        price = self._search_regex(r'<span class="andes-money-amount__fraction" aria-hidden="true">(.*?)</span>', webpage, 'precio', fatal=True)

        data = self._search_json(
            r'window\.__PRELOADED_STATE__\s*=', webpage, 'json data', display_id)

        shorts = traverse_obj(data, (
            'initialState', 'components', 'gallery', 'clips', 'shorts'))

        if len(shorts) == 0:
            raise ExtractorError('No videos found at the site')

        entries = []
        for short in shorts:
            video_id = short['id']
            video_url = short['video_url']

            formats = self._extract_m3u8_formats(video_url, video_id)

            entry = {
                'id': video_id,
                'title': title,
                'duration': short['video_duration'],
                'view_count': short['views'],
                'formats': formats
            }
            entries.append(entry)

        response = {
            '_type': 'playlist',
            'id': display_id,
            'title': title,
            'price': price,
            'entries': entries,
        }

        return response

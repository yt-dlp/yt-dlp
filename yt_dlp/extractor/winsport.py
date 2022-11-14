from .common import InfoExtractor
from ..utils import clean_html, get_element_html_by_class


class WinsportVideoIE(InfoExtractor):
    _VALID_URL = r'https?://www\.winsports\.co/videos/(?P<display_id>[\w-]+)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.winsports.co/videos/siempre-castellanos-gran-atajada-del-portero-cardenal-para-evitar-la-caida-de-su-arco-60536',
        'info_dict': {
            'id': '60536',
            'ext': 'mp4',
            'title': '¡Siempre Castellanos! Gran atajada del portero \'cardenal\' para evitar la caída de su arco',
            'display_id': 'siempre-castellanos-gran-atajada-del-portero-cardenal-para-evitar-la-caida-de-su-arco'
        }
    }, {
        'url': 'https://www.winsports.co/videos/observa-aqui-los-goles-del-empate-entre-tolima-y-nacional-60548',
        'info_dict': {
            'id': '60548',
            'ext': 'mp4',
            'display_id': 'observa-aqui-los-goles-del-empate-entre-tolima-y-nacional',
            'title': 'Observa aquí los goles del empate entre Tolima y Nacional',
        }
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).group('display_id', 'id')
        webpage = self._download_webpage(url, display_id)

        media_setting_json = self._search_json(
            r'<script\s*[^>]+data-drupal-selector="drupal-settings-json">', webpage, 'drupal-setting-json', display_id)

        mediastream_id = media_setting_json['settings']['mediastream_formatter'][video_id]['mediastream_id']

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(f'https://mdstrm.com/video/{mediastream_id}.m3u8', display_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': clean_html(get_element_html_by_class('title-news', webpage) or self._html_extract_title(webpage)),
        }

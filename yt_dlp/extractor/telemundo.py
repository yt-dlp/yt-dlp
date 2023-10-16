from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import try_get, unified_timestamp


class TelemundoIE(InfoExtractor):

    _VALID_URL = r'https?:\/\/(?:www\.)?telemundo\.com\/.+?video\/[^\/]+(?P<id>tmvo\d{7})'
    _TESTS = [{
        'url': 'https://www.telemundo.com/noticias/noticias-telemundo-en-la-noche/empleo/video/esta-aplicacion-gratuita-esta-ayudando-los-latinos-encontrar-trabajo-en-estados-unidos-tmvo9829325',
        'info_dict': {
            'id': 'tmvo9829325',
            'timestamp': 1621396800,
            'title': 'Esta aplicación gratuita está ayudando a los latinos a encontrar trabajo en Estados Unidos',
            'uploader': 'Telemundo',
            'uploader_id': 'NBCU_Telemundo',
            'ext': 'mp4',
            'upload_date': '20210519',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://www.telemundo.com/shows/al-rojo-vivo/empleo/video/personajes-de-times-square-piden-que-la-ciudad-de-nueva-york-los-deje-volver-trabajar-tmvo9816272',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        metadata = self._search_nextjs_data(webpage, video_id)
        redirect_url = try_get(
            metadata,
            lambda x: x['props']['initialState']['video']['associatedPlaylists'][0]['videos'][0]['videoAssets'][0]['publicUrl'])

        m3u8_url = self._request_webpage(HEADRequest(
            redirect_url + '?format=redirect&manifest=m3u&format=redirect&Tracking=true&Embedded=true&formats=MPEG4'),
            video_id, 'Processing m3u8').url
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        date = unified_timestamp(try_get(
            metadata, lambda x: x['props']['initialState']['video']['associatedPlaylists'][0]['videos'][0]['datePublished'].split(' ', 1)[1]))
        return {
            'url': url,
            'id': video_id,
            'title': self._search_regex(r'<h1[^>]+>([^<]+)', webpage, 'title', fatal=False),
            'formats': formats,
            'timestamp': date,
            'uploader': 'Telemundo',
            'uploader_id': self._search_regex(r'https?:\/\/(?:[^/]+\/){3}video\/(?P<id>[^\/]+)', m3u8_url, 'Akamai account', fatal=False)
        }

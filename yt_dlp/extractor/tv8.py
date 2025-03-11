from .common import InfoExtractor
from .skyit import TV8ItIE
from ..utils import clean_html, url_or_none, urljoin
from .common import InfoExtractor


class TV8StreamingIE(InfoExtractor):
    IE_NAME = 'TV8Streaming'
    IE_DESC = 'TV8 Live'
    _VALID_URL = r'https?://(?:www\.)?tv8\.it/streaming'
    _TESTS = [{
        'url': 'https://tv8.it/streaming',
        'info_dict': {
            'id': 'tv8',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'is_live': True,
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        video_id = 'tv8'
        streaming = self._download_json(
            'https://tv8.it/api/getStreaming', video_id, 'Downloading streaming data', fatal=False)
        livestream = self._download_json(
            'https://apid.sky.it/vdp/v1/getLivestream?id=7', video_id, 'Downloading manifest json info')

        return {
            'id': video_id,
            'is_live': True,
            'formats': self._extract_m3u8_formats(livestream['streaming_url'], video_id),
            **traverse_obj(streaming, ('info', {
                'title': ('title', 'text', {str}),
                'description': ('description', 'html', {clean_html}),
            })),
        }


class TV8PlaylistIE(InfoExtractor):
    IE_NAME = 'TV8Playlist'
    IE_DESC = 'TV8 Playlist'
    _VALID_URL = r'https?://(?:www\.)?tv8\.it/(?!video)[^/#?]+/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://tv8.it/intrattenimento/tv8-gialappas-night',
        'playlist_mincount': 32,
        'info_dict': {
            'id': 'tv8-gialappas-night',
            'title': 'Tv8 Gialappa\'s Night',
            'description': 'Tv8 Gialappa\'s Night vi aspetta tutti i mercoledì di UEFA Champions League, in diretta su Tv8. La Gialappa\'s Band si divertirà a commentare con ironia e sarcasmo quello che succede nel mondo del calcio.',
        },
    }, {
        'url': 'https://tv8.it/sport/uefa-europa-league',
        'playlist_mincount': 11,
        'info_dict': {
            'id': 'uefa-europa-league',
            'title': 'UEFA Europa League',
            'description': 'Su Tv8 torna il grande calcio europeo con la UEFA Europa League 2024-2025. La competizione è ufficialmente partita lo scorso 11 luglio con il primo turno di qualificazione e proseguirà fino al 21 maggio 2025, data in cui si disputerà la finale all\'Estadio de San Mamés di Bilbao. Per questa edizione ci saranno delle novità, la fase a gironi infatti è stata sostituita da un\'unica fase a campionato con 36 squadre. Ogni club affronterà 8 squadre diverse. Le prime otto classificate staccheranno direttamente il biglietto per gli ottavi di finale, le squadre che si piazzeranno tra la nona e la ventiquattresima posizione invece accederanno alla fase a elimazione diretta solamente tramite gli spareggi.',
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        data = self._search_nextjs_data(webpage, playlist_id)['props']['pageProps']['data']

        return self.playlist_result([{
            '_type': 'url_transparent',
            'ie_key': 'TV8It',
            'url': f"https://tv8.it{c['href']}",
            'title': traverse_obj(c, ('title', 'typography', 'text')),
            'thumbnail': traverse_obj(c, ('image', 'src')),
            'description': traverse_obj(c, ('extraData', 'videoDesc')),
            'id': str_or_none(traverse_obj(c, ('extraData', 'asset_id'))),
        } for c in data['lastContent']['cards']], video_id, traverse_obj(data, ('card', 'desktop', 'title', 'text')), re.sub(r'<.*?>', '', traverse_obj(data, ('card', 'desktop', 'description', 'html'))).strip())

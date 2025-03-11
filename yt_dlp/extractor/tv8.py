from .common import InfoExtractor
from .skyit import TV8ItIE
from ..utils import clean_html, traverse_obj, url_or_none, urljoin


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
            'description': 'md5:c876039d487d9cf40229b768872718ed',
            'thumbnail': 'https://static.sky.it/editorialimages/47b87cd71c2a4b71c4acbb8be04ae65dd71ce7ff/tv8/assets/entertainment/tv8-gialappa\'s-night/Gialappa\'sNight%20sito.jpg?auto=webp&im=Resize,width=1040,height=1040',
        },
    }, {
        'url': 'https://tv8.it/sport/uefa-europa-league',
        'playlist_mincount': 11,
        'info_dict': {
            'id': 'uefa-europa-league',
            'title': 'UEFA Europa League',
            'description': 'md5:9ab1832b7a8b1705b1f590e13a36bc6a',
            'thumbnail': 'https://static.sky.it/editorialimages/ecb73aebea8008b2d42b8f393adedf8d6b28bba9/tv8/assets/sport/europa-league/1040x467_europaleague.png?auto=webp&im=Resize,width=1040,height=1040',
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        data = self._search_nextjs_data(webpage, playlist_id)['props']['pageProps']['data']
        entries = [self.url_result(
            urljoin('https://tv8.it', card['href']), ie=TV8ItIE,
            **traverse_obj(card, {
                'description': ('extraData', 'videoDesc', {str}),
                'id': ('extraData', 'asset_id', {str}),
                'thumbnail': ('image', 'src', {url_or_none}),
                'title': ('title', 'typography', 'text', {str}),
            }))
            for card in traverse_obj(data, ('lastContent', 'cards', lambda _, v: v['href']))]

        return self.playlist_result(entries, playlist_id, **traverse_obj(data, ('card', 'desktop', {
            'description': ('description', 'html', {clean_html}),
            'thumbnail': ('image', 'src', {url_or_none}),
            'title': ('title', 'text', {str}),
        })))

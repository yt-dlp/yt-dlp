from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj


class IltalehtiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?iltalehti\.fi/[^/?#]+/a/(?P<id>[^/?#])'
    _TESTS = [
        # jwplatform embed main_media
        {
            'url': 'https://www.iltalehti.fi/ulkomaat/a/9fbd067f-94e4-46cd-8748-9d958eb4dae2',
            'md5': 'af12d42c539f1f49f0b62d231fe72dcd',
            'info_dict': {
                'id': 'gYjjaf1L',
                'ext': 'mp4',
                'title': 'Sensuroimaton Päivärinta, jakso 227: Vieraana Suomen Venäjän ex-suurlähettiläs René Nyberg ja Kenraalimajuri evp Pekka Toveri',
                'description': '',
                'upload_date': '20220928',
                'timestamp': 1664360878,
                'duration': 2089,
                'thumbnail': r're:^https?://.*\.jpg',
            },
        },
        # jwplatform embed body
        {
            'url': 'https://www.iltalehti.fi/politiikka/a/1ce49d85-1670-428b-8db8-d2479b9950a4',
            'md5': '9e50334b8f8330ce8828b567a82a3c65',
            'info_dict': {
                'id': '18R6zkLi',
                'ext': 'mp4',
                'title': 'Pekka Toverin arvio: Näin Nord Stream -kaasuputken räjäyttäminen on saatettu toteuttaa',
                'description': 'md5:3d1302c9e17e7ffd564143ff58f8de35',
                'upload_date': '20220929',
                'timestamp': 1664435867,
                'duration': 165.0,
                'thumbnail': r're:^https?://.*\.jpg',
            },
        },
    ]

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        info = self._search_json(
            r'<script>\s*window.App\s*=', webpage, 'json', article_id,
            transform_source=js_to_json)
        props = traverse_obj(info, (
            'state', 'articles', ..., 'items', (('main_media', 'properties'), ('body', ..., 'properties'))))
        video_ids = traverse_obj(props, (lambda _, v: v['provider'] == 'jwplayer', 'id'))
        return self.playlist_from_matches(
            video_ids, article_id, ie='JWPlatform', getter=lambda id: f'jwplatform:{id}',
            title=traverse_obj(info, ('state', 'articles', ..., 'items', 'canonical_title'), get_all=False))

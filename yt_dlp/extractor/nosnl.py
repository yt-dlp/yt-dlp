from .common import InfoExtractor
from ..utils import parse_duration, parse_iso8601, traverse_obj


class NOSNLArticleIE(InfoExtractor):
    _VALID_URL = r'https?://nos\.nl/(?P<type>video|(\w+/)?\w+)/?\d+-(?P<display_id>[\w-]+)'
    _TESTS = [
        {
            # only 1 video
            'url': 'https://nos.nl/nieuwsuur/artikel/2440353-verzakking-door-droogte-dreigt-tot-een-miljoen-kwetsbare-huizen',
            'info_dict': {
                'id': '2440340',
                'ext': 'mp4',
                'description': 'md5:5f83185d902ac97af3af4bed7ece3db5',
                'title': '\'We hebben een huis vol met scheuren\'',
                'duration': 95.0,
                'thumbnail': 'https://cdn.nos.nl/image/2022/08/12/887149/3840x2160a.jpg',
            },
        }, {
            # more than 1 video
            'url': 'https://nos.nl/artikel/2440409-vannacht-sliepen-weer-enkele-honderden-asielzoekers-in-ter-apel-buiten',
            'info_dict': {
                'id': '2440409',
                'title': 'Vannacht sliepen weer enkele honderden asielzoekers in Ter Apel buiten',
                'description': 'md5:72b1e1674d798460e79d78fa37e9f56d',
                'tags': ['aanmeldcentrum', 'Centraal Orgaan opvang asielzoekers', 'COA', 'asielzoekers', 'Ter Apel'],
                'modified_timestamp': 1660452773,
                'modified_date': '20220814',
                'upload_date': '20220813',
                'thumbnail': 'https://cdn.nos.nl/image/2022/07/18/880346/1024x576a.jpg',
                'timestamp': 1660401384,
                'categories': ['Regionaal nieuws', 'Binnenland'],
            },
            'playlist_count': 2,
        }, {
            # audio + video
            'url': 'https://nos.nl/artikel/2440789-wekdienst-16-8-groningse-acties-tien-jaar-na-zware-aardbeving-femke-bol-in-actie-op-ek-atletiek',
            'info_dict': {
                'id': '2440789',
                'title': 'Wekdienst 16/8: Groningse acties tien jaar na zware aardbeving • Femke Bol in actie op EK atletiek ',
                'description': 'md5:0bd277ed7a44fc15cb12a9d27d8f6641',
                'tags': ['wekdienst'],
                'modified_date': '20220816',
                'modified_timestamp': 1660625449,
                'timestamp': 1660625449,
                'upload_date': '20220816',
                'thumbnail': 'https://cdn.nos.nl/image/2022/08/16/888178/1024x576a.jpg',
                'categories': ['Binnenland', 'Buitenland'],
            },
            'playlist_count': 2,
        }, {
            # video url
            'url': 'https://nos.nl/video/2452718-xi-en-trudeau-botsen-voor-de-camera-op-g20-top-je-hebt-gelekt',
            'info_dict': {
                'id': '2452718',
                'title': 'Xi en Trudeau botsen voor de camera op G20-top: \'Je hebt gelekt\'',
                'modified_date': '20221117',
                'description': 'md5:61907dac576f75c11bf8ffffd4a3cc0f',
                'tags': ['Xi', 'Trudeau', 'G20', 'indonesié'],
                'upload_date': '20221117',
                'thumbnail': 'https://cdn.nos.nl/image/2022/11/17/916155/1024x576a.jpg',
                'modified_timestamp': 1668663388,
                'timestamp': 1668663388,
                'categories': ['Buitenland'],
            },
            'playlist_mincount': 1,
        },
    ]

    def _entries(self, nextjs_json, display_id):
        for item in nextjs_json:
            if item.get('type') == 'video':
                formats, subtitle = self._extract_m3u8_formats_and_subtitles(
                    traverse_obj(item, ('source', 'url')), display_id, ext='mp4')
                yield {
                    'id': str(item['id']),
                    'title': item.get('title'),
                    'description': item.get('description'),
                    'formats': formats,
                    'subtitles': subtitle,
                    'duration': parse_duration(item.get('duration')),
                    'thumbnails': [{
                        'url': traverse_obj(image, ('url', ...), get_all=False),
                        'width': image.get('width'),
                        'height': image.get('height'),
                    } for image in traverse_obj(item, ('imagesByRatio', ...))[0]],
                }

            elif item.get('type') == 'audio':
                yield {
                    'id': str(item['id']),
                    'title': item.get('title'),
                    'url': traverse_obj(item, ('media', 'src')),
                    'ext': 'mp3',
                }

    def _real_extract(self, url):
        site_type, display_id = self._match_valid_url(url).group('type', 'display_id')
        webpage = self._download_webpage(url, display_id)

        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['data']
        return {
            '_type': 'playlist',
            'entries': self._entries(
                [nextjs_json['video']] if site_type == 'video' else nextjs_json['items'], display_id),
            'id': str(nextjs_json['id']),
            'title': nextjs_json.get('title') or self._html_search_meta(['title', 'og:title', 'twitter:title'], webpage),
            'description': (nextjs_json.get('description')
                            or self._html_search_meta(['description', 'twitter:description', 'og:description'], webpage)),
            'tags': nextjs_json.get('keywords'),
            'modified_timestamp': parse_iso8601(nextjs_json.get('modifiedAt')),
            'thumbnail': nextjs_json.get('shareImageSrc') or self._html_search_meta(['og:image', 'twitter:image'], webpage),
            'timestamp': parse_iso8601(nextjs_json.get('publishedAt')),
            'categories': traverse_obj(nextjs_json, ('categories', ..., 'label')),
        }

from .common import InfoExtractor
from ..utils import url_or_none
from ..utils.traversal import traverse_obj


class RadioRadicaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radioradicale\.it/scheda/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.radioradicale.it/scheda/471591',
        'info_dict': {
            'id': '471591',
            'title': 'md5:e8fbb8de57011a3255db0beca69af73d',
            'description': 'md5:e8b8f4f1e06595965bfc1a312dec9b5b',
            'location': 'Napoli',
            'duration': 2852.0,
            'thumbnails': 'count:1',
            'timestamp': 1459987200,
            'upload_date': '20160407',
        },
        'playlist': [{
            'md5': 'eb0fbe43a601f1a361cbd00f3c45af4a',
            'info_dict': {
                'id': '471591-0',
                'ext': 'mp4',
                'title': 'RadioRadicale video #471591-0',
            },
        }],
    }, {
        'url': 'https://www.radioradicale.it/scheda/742783/parlamento-riunito-in-seduta-comune-11a-della-xix-legislatura',
        'info_dict': {
            'id': '742783',
            'title': 'Parlamento riunito in seduta comune (11ª della XIX legislatura)',
            'description': '-) Votazione per l\'elezione di un giudice della Corte Costituzionale (nono scrutinio)',
            'location': 'CAMERA',
            'duration': 5868.0,
            'thumbnails': 'count:1',
            'timestamp': 1730246400,
            'upload_date': '20241030',
        },
        'playlist': [{
            'md5': 'aa48de55dcc45478e4cd200f299aab7d',
            'info_dict': {
                'id': '742783-0',
                'ext': 'mp4',
                'title': 'RadioRadicale video #742783-0',
            },
        }, {
            'md5': 'be915c189c70ad2920e5810f32260ff5',
            'info_dict': {
                'id': '742783-1',
                'ext': 'mp4',
                'title': 'RadioRadicale video #742783-1',
            },
        }, {
            'md5': 'f0ee4047342baf8ed3128a8417ac5e0a',
            'info_dict': {
                'id': '742783-2',
                'ext': 'mp4',
                'title': 'RadioRadicale video #742783-2',
            },
        }],
    }]

    def _entries(self, videos_info, page_id):
        for idx, video in enumerate(traverse_obj(
                videos_info, ('playlist', lambda _, v: v['sources']))):
            video_id = f'{page_id}-{idx}'
            formats = []
            subtitles = {}

            for m3u8_url in traverse_obj(video, ('sources', ..., 'src', {url_or_none})):
                formats.extend(self._extract_m3u8_formats(m3u8_url, video_id))
            for sub in traverse_obj(video, ('subtitles', ..., {dict})):
                self._merge_subtitles({sub.get('srclang') or 'und': [{
                    'url': sub.get('src'),
                    'name': sub.get('label'),
                }]}, target=subtitles)

            yield {
                'id': video_id,
                'title': '',
                'formats': formats,
                'subtitles': subtitles,
            }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        videos_info = self._search_json(
            r'jQuery\.extend\(Drupal\.settings\s*,',
            webpage, 'videos_info', page_id)['RRscheda']

        return self.playlist_result(
            self._entries(videos_info, page_id), page_id, self._og_search_title(webpage),
            self._og_search_description(webpage), location=videos_info.get('luogo'),
            **self._search_json_ld(webpage, page_id))

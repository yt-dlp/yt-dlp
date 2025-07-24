from .common import InfoExtractor
from ..utils import url_or_none
from ..utils.traversal import traverse_obj


class RadioRadicaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radioradicale\.it/scheda/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.radioradicale.it/scheda/471591',
        'md5': 'eb0fbe43a601f1a361cbd00f3c45af4a',
        'info_dict': {
            'id': '471591',
            'ext': 'mp4',
            'title': 'md5:e8fbb8de57011a3255db0beca69af73d',
            'description': 'md5:5e15a789a2fe4d67da8d1366996e89ef',
            'location': 'Napoli',
            'duration': 2852.0,
            'timestamp': 1459987200,
            'upload_date': '20160407',
            'thumbnail': 'https://www.radioradicale.it/photo400/0/0/9/0/1/00901768.jpg',
        },
    }, {
        'url': 'https://www.radioradicale.it/scheda/742783/parlamento-riunito-in-seduta-comune-11a-della-xix-legislatura',
        'info_dict': {
            'id': '742783',
            'title': 'Parlamento riunito in seduta comune (11ª della XIX legislatura)',
            'description': '-) Votazione per l\'elezione di un giudice della Corte Costituzionale (nono scrutinio)',
            'location': 'CAMERA',
            'duration': 5868.0,
            'timestamp': 1730246400,
            'upload_date': '20241030',
        },
        'playlist': [{
            'md5': 'aa48de55dcc45478e4cd200f299aab7d',
            'info_dict': {
                'id': '742783-0',
                'ext': 'mp4',
                'title': 'Parlamento riunito in seduta comune (11ª della XIX legislatura)',
            },
        }, {
            'md5': 'be915c189c70ad2920e5810f32260ff5',
            'info_dict': {
                'id': '742783-1',
                'ext': 'mp4',
                'title': 'Parlamento riunito in seduta comune (11ª della XIX legislatura)',
            },
        }, {
            'md5': 'f0ee4047342baf8ed3128a8417ac5e0a',
            'info_dict': {
                'id': '742783-2',
                'ext': 'mp4',
                'title': 'Parlamento riunito in seduta comune (11ª della XIX legislatura)',
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
                fmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            for sub in traverse_obj(video, ('subtitles', ..., lambda _, v: url_or_none(v['src']))):
                self._merge_subtitles({sub.get('srclang') or 'und': [{
                    'url': sub['src'],
                    'name': sub.get('label'),
                }]}, target=subtitles)

            yield {
                'id': video_id,
                'title': video.get('title'),
                'formats': formats,
                'subtitles': subtitles,
            }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        videos_info = self._search_json(
            r'jQuery\.extend\(Drupal\.settings\s*,',
            webpage, 'videos_info', page_id)['RRscheda']

        entries = list(self._entries(videos_info, page_id))

        common_info = {
            'id': page_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'location': videos_info.get('luogo'),
            **self._search_json_ld(webpage, page_id),
        }

        if len(entries) == 1:
            return {
                **entries[0],
                **common_info,
            }

        return self.playlist_result(entries, multi_video=True, **common_info)

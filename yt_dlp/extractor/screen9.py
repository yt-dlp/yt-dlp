from .common import InfoExtractor
from ..utils import traverse_obj


class Screen9IE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.screen9\.(?:tv|com)|play\.su\.se)/(?:embed|media)/(?P<id>[^?#/]+)'
    _TESTS = [
        {
            'url': 'https://api.screen9.com/embed/8kTNEjvoXGM33dmWwF0uDA',
            'md5': 'd60d23f8980583b930724b01fa6ddb41',
            'info_dict': {
                'id': '8kTNEjvoXGM33dmWwF0uDA',
                'ext': 'mp4',
                'title': 'Östersjön i förändrat klimat',
                'thumbnail': r're:^https?://.+\.jpg',
            },
        },
        {
            'url': 'https://folkhogskolekanalen.screen9.tv/media/gy35PKLHe-5K29RYHga2bw/ett-starkare-samhalle-en-snabbguide-om-sveriges-folkhogskolor',
            'md5': 'c9389806e78573ea34fc48b6f94465dc',
            'info_dict': {
                'id': 'gy35PKLHe-5K29RYHga2bw',
                'ext': 'mp4',
                'title': 'Ett starkare samhälle - en snabbguide om Sveriges folkhögskolor',
                'thumbnail': r're:^https?://.+\.jpg',
            },
        },
        {
            'url': 'https://play.su.se/media/H1YA0EYNCxiesrSU1kaRBQ/baltic-breakfast',
            'md5': '2b817647c3058002526269deff4c0683',
            'info_dict': {
                'id': 'H1YA0EYNCxiesrSU1kaRBQ',
                'ext': 'mp4',
                'title': 'Baltic Breakfast',
                'thumbnail': r're:^https?://.+\.jpg',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://api.screen9.com/embed/{video_id}', video_id)
        config = self._search_json(r'var\s+config\s*=', webpage, 'config', video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(config, ('src', lambda _, v: v['type'] == 'application/x-mpegURL', 'src'), get_all=False),
            video_id, ext='mp4')
        formats.append({
            'url': traverse_obj(config, ('src', lambda _, v: v['type'] == 'video/mp4', 'src'), get_all=False),
            'format': 'mp4',
        })

        return {
            'id': video_id,
            'title': traverse_obj(
                config,
                ('plugins', (('title', 'title'), ('googleAnalytics', 'title'), ('share', 'mediaTitle'))),
                get_all=False),
            'description': traverse_obj(config, ('plugins', 'title', 'description')),
            'thumbnail': traverse_obj(config, ('poster')),
            'formats': formats,
            'subtitles': subtitles,
        }

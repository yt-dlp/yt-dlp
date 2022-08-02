from .common import InfoExtractor
from ..utils import parse_duration


class PornboxExtractorIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornbox\.com/application/watch-page/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://pornbox.com/application/watch-page/73480',
        'md5': '4a4b8db9dfb46a6671e41d5a36dffacf',
        'info_dict': {
            'id': '73480',
            'ext': 'mp4',
            'title': 'Cute Teen Lesya Milk VS Big Monster Cock by Leo Casanova - Big Ass - Intense Hard Anal Fuck',
            'description': 'Cute Teen Lesya Milk VS Big Monster Cock by Leo Casanova - Big Ass - Intense Hard Anal Fuck',
            'uploader': 'VK Studio',
            'upload_date': '20220617',
            'age_limit': 18,
            'duration': 2753,
            'cast': ['Lesya Milk', 'Leo Casanova'],
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$'
        }
    },
        {
            'url': 'https://pornbox.com/application/watch-page/216045',
            'md5': '56cb78bb1d8e0d2dad8b75c278c20098',
            'info_dict': {
                'id': '216045',
                'ext': 'mp4',
                'title': 'DP Bella Grey - Hard Anal Fuck - Interview With Translation VK054',
                'description': 'DP Bella Grey - Hard Anal Fuck - Interview With Translation',
                'uploader': 'VK Studio',
                'upload_date': '20210412',
                'age_limit': 18,
                'duration': 2710,
                'cast': ['Bella Grey', 'Oliver Trunk'],
                'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$'
            }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_json = self._download_json(f'https://pornbox.com/contents/{video_id}', video_id)
        medias = data_json.get('medias')
        media_id = list(filter(lambda x: x.get('title') == "Full video", medias))[0].get('media_id')

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0",
            "Accept": "*/*",
            "Accept-Language": "en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Requested-With": "XMLHttpRequest",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        stream_data = self._download_json(f'https://pornbox.com/media/{media_id}/stream', video_id, headers=headers)
        qualities = stream_data.get('qualities')
        qualities.sort(key=lambda x: x.get('bitrate'))
        formats = []
        for q in qualities:
            formats.append({
                'url': q.get('src'),
                'vbr': int(int(q.get('bitrate')) / 1000),
                'format_id': q.get('quality')
            })

        if data_json.get('studios') is not None:
            date = data_json.get('studios')[0].get('release_date')
        else:
            date = data_json.get('publish_date')
        date = date[:10].replace('-', '')
        cast = []
        for m in data_json.get('models'):
            cast.append(m.get('model_name'))
        for m in data_json.get('male_models'):
            cast.append(m.get('model_name'))

        scene_subtitles = data_json.get('subtitles') or []
        subtitles = {}
        for country_code in scene_subtitles:
            subtitles[country_code] = [{
                'url': f'https://pornbox.com/contents/{video_id}/subtitles/{country_code}',
                'ext': 'srt'
            }]

        return {
            'id': video_id,
            'title': data_json.get('scene_name').strip(),
            'formats': formats,
            'description': data_json.get('small_description').strip(),
            'uploader': data_json.get('studio'),
            'upload_date': date,
            'age_limit': 18,
            'duration': parse_duration(data_json.get('runtime')),
            'cast': cast,
            'thumbnail': data_json.get('player_poster'),
            'subtitles': subtitles
        }

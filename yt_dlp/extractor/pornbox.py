from .common import InfoExtractor
from ..utils import parse_duration


class PornboxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornbox\.com/application/watch-page/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://pornbox.com/application/watch-page/429019',
        'md5': '7c2f09cc7be6d9084a9faa7186d395d7',
        'info_dict': {
            'id': '429019',
            'ext': 'mp4',
            'title': 'md5:9c5decc32bc4d96c255e328282a9730a',
            'description': 'md5:c47331c98221bc55c2d02a142a13f562',
            'uploader': 'Giorgio Grandi',
            'upload_date': '20230609',
            'age_limit': 18,
            'availability': 'needs_auth',
            'duration': 1961,
            'cast': ['Tina Kay', 'Monika Wild', 'Neeo', 'Mr. Anderson', 'Thomas Lee', 'Angelo Godshack', 'Dylan Brown'],
            'tags': 'count:40',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$'
        }
    }, {
        'url': 'https://pornbox.com/application/watch-page/426095',
        'md5': '0cc35f4d4300bc8e0496aef2a9ec20b9',
        'info_dict': {
            'id': '426095',
            'ext': 'mp4',
            'title': 'md5:96b05922d74be2be939cf247294f26bd',
            'uploader': 'Giorgio Grandi',
            'upload_date': '20230606',
            'age_limit': 18,
            'availability': 'needs_auth',
            'duration': 1767,
            'cast': ['Tina Kay', 'Neeo', 'Mr. Anderson', 'Thomas Lee', 'Brian Ragnastone', 'Rycky Optimal'],
            'tags': 'count:37',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$'
        }
    }, {
        'url': 'https://pornbox.com/application/watch-page/216045',
        'md5': '56cb78bb1d8e0d2dad8b75c278c20098',
        'info_dict': {
            'id': '216045',
            'ext': 'mp4',
            'title': 'md5:3e48528e73a9a2b12f7a2772ed0b26a2',
            'description': 'md5:3e631dcaac029f15ed434e402d1b06c7',
            'uploader': 'VK Studio',
            'upload_date': '20210412',
            'age_limit': 18,
            'availability': 'premium_only',
            'duration': 2710,
            'cast': ['Bella Grey', 'Oliver Trunk'],
            'tags': 'count:29',
            'thumbnail': r're:^https?://cdn-image\.gtflixtv\.com.*\.jpg.*$'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        public_data = self._download_json(f'https://pornbox.com/contents/{video_id}', video_id)

        if public_data.get('studios') is not None:
            date = public_data.get('studios')[0].get('release_date') or public_data.get('publish_date')
        else:
            date = public_data.get('publish_date')
        date = date[:10].replace('-', '')
        cast = []
        for m in public_data.get('models') or []:
            cast.append(m.get('model_name'))
        for m in public_data.get('male_models') or []:
            cast.append(m.get('model_name'))
        tags = []
        for t in public_data.get('niches') or []:
            tags.append(t.get('niche'))

        subtitles = {}
        for country_code in public_data.get('subtitles') or []:
            subtitles[country_code] = [{
                'url': f'https://pornbox.com/contents/{video_id}/subtitles/{country_code}',
                'ext': 'srt'
            }]

        metadata = {
            'id': video_id,
            'title': public_data.get('scene_name').strip(),
            'uploader': public_data.get('studio'),
            'upload_date': date,
            'age_limit': 18,
            'duration': parse_duration(public_data.get('runtime')),
            'cast': cast,
            'tags': tags,
            'thumbnail': public_data.get('player_poster'),
            'subtitles': subtitles
        }

        if description := public_data.get('small_description'):
            metadata['description'] = description.strip()

        if public_data.get('price').get('is_available_for_free'):
            metadata['availability'] = 'needs_auth'
        else:
            metadata['availability'] = 'premium_only'

        if (not public_data.get('is_purchased')) or (not public_data.get('price').get('is_available_for_free')):
            self.raise_login_required('You are either not logged in or do not have access to this scene',
                                      metadata_available=True, method='cookies')
            return metadata

        medias = public_data.get('medias')
        full_video = next(filter(lambda x: x.get('title') == 'Full video', medias), None)
        if full_video is None:
            self.raise_no_formats(msg='Could not find stream id', video_id=video_id)
        media_id = full_video.get('media_id')

        headers = {
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
        stream_data = self._download_json(f'https://pornbox.com/media/{media_id}/stream', video_id=video_id,
                                          headers=headers, note='Getting manifest urls')
        qualities = stream_data.get('qualities')
        qualities.sort(key=lambda x: x.get('bitrate'))
        formats = []
        for q in qualities:
            formats.append({
                'url': q.get('src'),
                'vbr': int(q.get('bitrate')) // 1000,
                'format_id': q.get('quality')
            })

        metadata['formats'] = formats

        return metadata

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    mimetype2ext,
)


class TweakersIE(InfoExtractor):
    _VALID_URL = r'https?://tweakers\.net/video/(?P<id>\d+)'
    _TEST = {
        'url': 'https://tweakers.net/video/9926/new-nintendo-3ds-xl-op-alle-fronten-beter.html',
        'md5': 'fe73e417c093a788e0160c4025f88b15',
        'info_dict': {
            'id': '9926',
            'ext': 'mp4',
            'title': 'New Nintendo 3DS XL - Op alle fronten beter',
            'description': 'md5:3789b21fed9c0219e9bcaacd43fab280',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'duration': 386,
            'uploader_id': 's7JeEm',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            f'https://tweakers.net/video/s1playlist/{video_id}/1920/1080/playlist.json',
            video_id)['items'][0]

        title = video_data['title']

        formats = []
        for location in video_data.get('locations', {}).get('progressive', []):
            format_id = location.get('label')
            width = int_or_none(location.get('width'))
            height = int_or_none(location.get('height'))
            for source in location.get('sources', []):
                source_url = source.get('src')
                if not source_url:
                    continue
                ext = mimetype2ext(source.get('type')) or determine_ext(source_url)
                formats.append({
                    'format_id': format_id,
                    'url': source_url,
                    'width': width,
                    'height': height,
                    'ext': ext,
                })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('poster'),
            'duration': int_or_none(video_data.get('duration')),
            'uploader_id': video_data.get('account'),
            'formats': formats,
        }

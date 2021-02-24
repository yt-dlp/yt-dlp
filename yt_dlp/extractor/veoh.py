from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    qualities,
)


class VeohIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?veoh\.com/(?:watch|embed|iphone/#_Watch)/(?P<id>(?:v|e|yapi-)[\da-zA-Z]+)'

    _TESTS = [{
        'url': 'http://www.veoh.com/watch/v56314296nk7Zdmz3',
        'md5': '9e7ecc0fd8bbee7a69fe38953aeebd30',
        'info_dict': {
            'id': 'v56314296nk7Zdmz3',
            'ext': 'mp4',
            'title': 'Straight Backs Are Stronger',
            'uploader': 'LUMOback',
            'description': 'At LUMOback, we believe straight backs are stronger.  The LUMOback Posture & Movement Sensor:  It gently vibrates when you slouch, inspiring improved posture and mobility.  Use the app to track your data and improve your posture over time. ',
        },
    }, {
        'url': 'http://www.veoh.com/embed/v56314296nk7Zdmz3',
        'only_matching': True,
    }, {
        'url': 'http://www.veoh.com/watch/v27701988pbTc4wzN?h1=Chile+workers+cover+up+to+avoid+skin+damage',
        'md5': '4a6ff84b87d536a6a71e6aa6c0ad07fa',
        'info_dict': {
            'id': '27701988',
            'ext': 'mp4',
            'title': 'Chile workers cover up to avoid skin damage',
            'description': 'md5:2bd151625a60a32822873efc246ba20d',
            'uploader': 'afp-news',
            'duration': 123,
        },
        'skip': 'This video has been deleted.',
    }, {
        'url': 'http://www.veoh.com/watch/v69525809F6Nc4frX',
        'md5': '4fde7b9e33577bab2f2f8f260e30e979',
        'note': 'Embedded ooyala video',
        'info_dict': {
            'id': '69525809',
            'ext': 'mp4',
            'title': 'Doctors Alter Plan For Preteen\'s Weight Loss Surgery',
            'description': 'md5:f5a11c51f8fb51d2315bca0937526891',
            'uploader': 'newsy-videos',
        },
        'skip': 'This video has been deleted.',
    }, {
        'url': 'http://www.veoh.com/watch/e152215AJxZktGS',
        'only_matching': True,
    }]

    def _extract_video(self, source):
        return {
            'id': source.get('videoId'),
            'title': source.get('title'),
            'description': source.get('description'),
            'thumbnail': source.get('highResImage') or source.get('medResImage'),
            'uploader': source.get('username'),
            'duration': int_or_none(source.get('length')),
            'view_count': int_or_none(source.get('views')),
            'age_limit': 18 if source.get('isMature') == 'true' or source.get('isSexy') == 'true' else 0,
            'formats': self._extract_formats(source),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video = self._download_json(
            'https://www.veoh.com/watch/getVideo/' + video_id,
            video_id)['video']
        title = video['title']

        thumbnail_url = None
        q = qualities(['HQ', 'Regular'])
        formats = []
        for f_id, f_url in video.get('src', {}).items():
            if not f_url:
                continue
            if f_id == 'poster':
                thumbnail_url = f_url
            else:
                formats.append({
                    'format_id': f_id,
                    'quality': q(f_id),
                    'url': f_url,
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'thumbnail': thumbnail_url,
            'uploader': video.get('author', {}).get('nickname'),
            'duration': int_or_none(video.get('lengthBySec')) or parse_duration(video.get('length')),
            'view_count': int_or_none(video.get('views')),
            'formats': formats,
            'average_rating': int_or_none(video.get('rating')),
            'comment_count': int_or_none(video.get('numOfComments')),
        }

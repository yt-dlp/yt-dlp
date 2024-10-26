import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    parse_duration,
    qualities,
    remove_start,
    strip_or_none,
)


class VeohIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?veoh\.com/(?:watch|videos|embed|iphone/#_Watch)/(?P<id>(?:v|e|yapi-)[\da-zA-Z]+)'

    _TESTS = [{
        'url': 'http://www.veoh.com/watch/v56314296nk7Zdmz3',
        'md5': '620e68e6a3cff80086df3348426c9ca3',
        'info_dict': {
            'id': 'v56314296nk7Zdmz3',
            'ext': 'mp4',
            'title': 'Straight Backs Are Stronger',
            'description': 'md5:203f976279939a6dc664d4001e13f5f4',
            'thumbnail': 're:https://fcache\\.veoh\\.com/file/f/th56314296\\.jpg(\\?.*)?',
            'uploader': 'LUMOback',
            'duration': 46,
            'view_count': int,
            'average_rating': int,
            'comment_count': int,
            'age_limit': 0,
            'categories': ['technology_and_gaming'],
            'tags': ['posture', 'posture', 'sensor', 'back', 'pain', 'wearable', 'tech', 'lumo'],
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
    }, {
        'url': 'https://www.veoh.com/videos/v16374379WA437rMH',
        'md5': 'cceb73f3909063d64f4b93d4defca1b3',
        'info_dict': {
            'id': 'v16374379WA437rMH',
            'ext': 'mp4',
            'title': 'Phantasmagoria 2, pt. 1-3',
            'description': 'Phantasmagoria: a Puzzle of Flesh',
            'thumbnail': 're:https://fcache\\.veoh\\.com/file/f/th16374379\\.jpg(\\?.*)?',
            'uploader': 'davidspackage',
            'duration': 968,
            'view_count': int,
            'average_rating': int,
            'comment_count': int,
            'age_limit': 18,
            'categories': ['technology_and_gaming', 'gaming'],
            'tags': ['puzzle', 'of', 'flesh'],
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(
            'https://www.veoh.com/watch/getVideo/' + video_id,
            video_id)
        video = metadata['video']
        title = video['title']

        thumbnail_url = None
        q = qualities(['Regular', 'HQ'])
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

        categories = metadata.get('categoryPath')
        if not categories:
            category = remove_start(strip_or_none(video.get('category')), 'category_')
            categories = [category] if category else None
        tags = video.get('tags')

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
            'age_limit': 18 if video.get('contentRatingId') == 2 else 0,
            'categories': categories,
            'tags': tags.split(', ') if tags else None,
        }


class VeohUserIE(VeohIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?veoh\.com/users/(?P<id>[\w-]+)'
    IE_NAME = 'veoh:user'

    _TESTS = [
        {
            'url': 'https://www.veoh.com/users/valentinazoe',
            'info_dict': {
                'id': 'valentinazoe',
                'title': 'valentinazoe (Uploads)',
            },
            'playlist_mincount': 75,
        },
        {
            'url': 'https://www.veoh.com/users/PiensaLibre',
            'info_dict': {
                'id': 'PiensaLibre',
                'title': 'PiensaLibre (Uploads)',
            },
            'playlist_mincount': 2,
        }]

    _PAGE_SIZE = 16

    def _fetch_page(self, uploader, page):
        response = self._download_json(
            'https://www.veoh.com/users/published/videos', uploader,
            note=f'Downloading videos page {page + 1}',
            headers={
                'x-csrf-token': self._TOKEN,
                'content-type': 'application/json;charset=UTF-8',
            },
            data=json.dumps({
                'username': uploader,
                'maxResults': self._PAGE_SIZE,
                'page': page + 1,
                'requestName': 'userPage',
            }).encode())
        if not response.get('success'):
            raise ExtractorError(response['message'])

        for video in response['videos']:
            yield self.url_result(f'https://www.veoh.com/watch/{video["permalinkId"]}', VeohIE,
                                  video['permalinkId'], video.get('title'))

    def _real_initialize(self):
        webpage = self._download_webpage(
            'https://www.veoh.com', None, note='Downloading authorization token')
        self._TOKEN = self._search_regex(
            r'csrfToken:\s*(["\'])(?P<token>[0-9a-zA-Z]{40})\1', webpage,
            'request token', group='token')

    def _real_extract(self, url):
        uploader = self._match_id(url)
        return self.playlist_result(OnDemandPagedList(
            functools.partial(self._fetch_page, uploader),
            self._PAGE_SIZE), uploader, f'{uploader} (Uploads)')

import itertools
import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    qualities,
    try_get,
    str_or_none,
    ExtractorError,
    url_or_none
)


class VeohIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?veoh\.com/(?:watch|videos|embed|iphone/#_Watch)/(?P<id>(?:v|e|yapi-)[\da-zA-Z]+)'

    IE_NAME = 'veoh'
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
        }
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
        self._sort_formats(formats)

        categories = metadata.get('categoryPath')
        if not categories:
            category = try_get(video, lambda x: x['category'].strip().removeprefix('category_'))
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


class VeohUserIE(VeohIE):
    _VALID_URL = r'https?://(?:www\.)?veoh\.com/users/(?P<user>([\da-zA-Z_\-]+))'
    IE_NAME = 'veoh:user'

    _TESTS = [
        {
            'url': 'https://www.veoh.com/users/valentinazoe',
            'info_dict': {
                'id': 'valentinazoe',
                'title': 'valentinazoe (Uploads)'
            },
            'playlist_mincount': 75
        },
        {
            'url': 'https://www.veoh.com/users/PiensaLibre',
            'info_dict': {
                'id': 'PiensaLibre',
                'title': 'PiensaLibre (Uploads)'
            },
            'playlist_mincount': 2
        }]

    _USERSINFO_ENDPOINT = 'https://www.veoh.com/users/published/videos'
    _VIDEO_BASEURL = 'https://www.veoh.com/watch/'

    def _get_authtoken(self, page, uploader=None):
        webpage = self._download_webpage(page, uploader)
        return self._search_regex(
            r'csrfToken: "(?P<token>[0-9a-zA-Z]{40})"', webpage,
            'request token', group='token')

    def _get_videos(self, uploader, authtoken=None):
        if authtoken is None:
            authtoken = self._get_authtoken(f'https://www.veoh.com/users/{uploader}', uploader)
        totalVids = 0
        for i in itertools.count():
            payload = json.dumps({'username': uploader, 'maxResults': 16, 'page': i + 1, 'requestName': 'userPage'}).encode('utf-8')
            headers = {
                'x-csrf-token': authtoken,
                'content-type': 'application/json;charset=UTF-8'
            }
            for retry in self.RetryManager():
                try:
                    response = self._download_json(
                        self._USERSINFO_ENDPOINT, uploader, data=payload, headers=headers,
                        note=f'Downloading videos page {i + 1}')
                    if not response['success']:
                        raise ExtractorError('unsuccessful veoh user videos request')
                    break
                except ExtractorError as e:
                    raise e

            def resolve_entry(*candidates):
                for cand in candidates:
                    if not isinstance(cand, dict):
                        continue
                    permalink_url = url_or_none(self._VIDEO_BASEURL + cand['permalinkId'])
                    if permalink_url:
                        return self.url_result(
                            permalink_url,
                            VeohIE.ie_key() if VeohIE.suitable(permalink_url) else None,
                            str_or_none(cand['permalinkId']), cand['title'])

            for e in response['videos'] or []:
                yield resolve_entry(e)

            totalVids += len(response['videos'])
            if (totalVids == response['totalRecords']) or (len(response['videos']) == 0):
                break

    def _extract_videos(self, uploader, playlist_title, playlist_id):
        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': playlist_title,
            'entries': self._get_videos(uploader)
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        uploader = mobj.group('user')

        return self._extract_videos(
            uploader,
            f'{str_or_none(uploader)} (Uploads)',
            str_or_none(uploader))

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    smuggle_url,
    str_or_none,
    traverse_obj,
    urlencode_postdata
)


class CybraryBaseIE(InfoExtractor):
    _API_KEY = 'AIzaSyCX9ru6j70PX2My1Eq6Q1zoMAhuTdXlzSw'
    _ENDPOINTS = {
        'course': 'https://app.cybrary.it/courses/api/catalog/browse/course/{}',
        'course_enrollment': 'https://app.cybrary.it/courses/api/catalog/{}/enrollment',
        'enrollment': 'https://app.cybrary.it/courses/api/enrollment/{}',
        'launch': 'https://app.cybrary.it/courses/api/catalog/{}/launch',
        'vimeo_oembed': 'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{}',
    }
    _NETRC_MACHINE = 'cybrary'
    _TOKEN = None

    def _perform_login(self, username, password):
        CybraryBaseIE._TOKEN = self._download_json(
            f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self._API_KEY}',
            None, data=urlencode_postdata({'email': username, 'password': password, 'returnSecureToken': True}),
            note='Logging in')['idToken']

    def _real_initialize(self):
        if not self._TOKEN:
            self.raise_login_required(method='password')

    def _call_api(self, endpoint, item_id):
        return self._download_json(
            self._ENDPOINTS[endpoint].format(item_id), item_id,
            note=f'Downloading {endpoint} JSON metadata',
            headers={'Authorization': f'Bearer {self._TOKEN}'})

    def _get_vimeo_id(self, activity_id):
        launch_api = self._call_api('launch', activity_id)

        if launch_api.get('url'):
            return self._search_regex(r'https?://player\.vimeo\.com/video/(?P<vimeo_id>[0-9]+)', launch_api['url'], 'vimeo_id')
        return traverse_obj(launch_api, ('vendor_data', 'content', ..., 'videoId'), get_all=False)


class CybraryIE(CybraryBaseIE):
    _VALID_URL = r'https?://app.cybrary.it/immersive/(?P<enrollment>[0-9]+)/activity/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://app.cybrary.it/immersive/12487950/activity/63102',
        'md5': '9ae12d37e555cb2ed554223a71a701d0',
        'info_dict': {
            'id': '646609770',
            'ext': 'mp4',
            'title': 'Getting Started',
            'thumbnail': 'https://i.vimeocdn.com/video/1301817996-76a268f0c56cff18a5cecbbdc44131eb9dda0c80eb0b3a036_1280',
            'series_id': '63111',
            'uploader_url': 'https://vimeo.com/user30867300',
            'duration': 88,
            'uploader_id': 'user30867300',
            'series': 'Cybrary Orientation',
            'uploader': 'Cybrary',
            'chapter': 'Cybrary Orientation Series',
            'chapter_id': '63110'
        },
        'expected_warnings': ['No authenticators for vimeo']
    }, {
        'url': 'https://app.cybrary.it/immersive/12747143/activity/52686',
        'md5': '62f26547dccc59c44363e2a13d4ad08d',
        'info_dict': {
            'id': '445638073',
            'ext': 'mp4',
            'title': 'Azure Virtual Network IP Addressing',
            'thumbnail': 'https://i.vimeocdn.com/video/936667051-1647ace66c627d4a2382185e0dae8deb830309bfddd53f8b2367b2f91e92ed0e-d_1280',
            'series_id': '52733',
            'uploader_url': 'https://vimeo.com/user30867300',
            'duration': 426,
            'uploader_id': 'user30867300',
            'series': 'AZ-500: Microsoft Azure Security Technologies',
            'uploader': 'Cybrary',
            'chapter': 'Implement Network Security',
            'chapter_id': '52693'
        },
        'expected_warnings': ['No authenticators for vimeo']
    }]

    def _real_extract(self, url):
        activity_id, enrollment_id = self._match_valid_url(url).group('id', 'enrollment')
        course = self._call_api('enrollment', enrollment_id)['content']
        activity = traverse_obj(course, ('learning_modules', ..., 'activities', lambda _, v: int(activity_id) == v['id']), get_all=False)

        if activity.get('type') not in ['Video Activity', 'Lesson Activity']:
            raise ExtractorError('The activity is not a video', expected=True)

        module = next((m for m in course.get('learning_modules') or []
                      if int(activity_id) in traverse_obj(m, ('activities', ..., 'id') or [])), None)

        vimeo_id = self._get_vimeo_id(activity_id)

        return {
            '_type': 'url_transparent',
            'series': traverse_obj(course, ('content_description', 'title')),
            'series_id': str_or_none(traverse_obj(course, ('content_description', 'id'))),
            'id': vimeo_id,
            'chapter': module.get('title'),
            'chapter_id': str_or_none(module.get('id')),
            'title': activity.get('title'),
            'url': smuggle_url(f'https://player.vimeo.com/video/{vimeo_id}', {'http_headers': {'Referer': 'https://api.cybrary.it'}})
        }


class CybraryCourseIE(CybraryBaseIE):
    _VALID_URL = r'https://app.cybrary.it/browse/course/(?P<id>[\w-]+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://app.cybrary.it/browse/course/az-500-microsoft-azure-security-technologies',
        'info_dict': {
            'id': 898,
            'title': 'AZ-500: Microsoft Azure Security Technologies',
            'description': 'md5:69549d379c0fc1dec92926d4e8b6fbd4'
        },
        'playlist_count': 59
    }, {
        'url': 'https://app.cybrary.it/browse/course/cybrary-orientation',
        'info_dict': {
            'id': 1245,
            'title': 'Cybrary Orientation',
            'description': 'md5:9e69ff66b32fe78744e0ad4babe2e88e'
        },
        'playlist_count': 4
    }]

    def _real_extract(self, url):
        course_id = self._match_id(url)
        course = self._call_api('course', course_id)
        enrollment_info = self._call_api('course_enrollment', course['id'])

        entries = [self.url_result(
            f'https://app.cybrary.it/immersive/{enrollment_info["id"]}/activity/{activity["id"]}')
            for activity in traverse_obj(course, ('content_item', 'learning_modules', ..., 'activities', ...))]

        return self.playlist_result(
            entries,
            traverse_obj(course, ('content_item', 'id'), expected_type=str_or_none),
            course.get('title'), course.get('short_description'))

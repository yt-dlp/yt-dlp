import json

from .common import InfoExtractor


class GameDevTVDashboardIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gamedev\.tv/dashboard/courses/(?P<id>\d+)'
    _NETRC_MACHINE = 'gamedevtv'
    _API_HEADERS = {}
    _TESTS = [{
        'url': 'https://www.gamedev.tv/dashboard/courses/25',
        'md5': 'ece542a1071018d5a09e0dc91a843763',
        'info_dict': {
            'playlist': 'Complete Blender Creator 3: Learn 3D Modelling for Beginners',
            'playlist_id': 25,
            'chapter_id': '01',
            'chapter': 'Introduction & Setup',
            'id': '01',
            'ext': 'mp4',
            'title': 'Section Intro - Introduction To Blender',
        },
    }]

    def _perform_login(self, username, password):
        response = self._download_json(
            'https://api.gamedev.tv/api/students/login', None, 'Logging in',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'email': username,
                'password': password,
                'cart_items': [],
            }).encode())
        self._API_HEADERS['Authorization'] = f'{response["token_type"]} {response["access_token"]}'

    def _entries(self, data, course_id):
        course_list = []
        for section in data['data']['sections']:
            for lecture in section['lectures']:
                video_id = str(lecture['order']).zfill(2)
                title = lecture['title']
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                    lecture['video']['playListUrl'], course_id, 'mp4', m3u8_id='hls')
                playlist_title = data['data']['title']
                playlist_id = data['data']['id']
                chapter_id = str(section['order']).zfill(2)
                chapter = section['title']
                course_list.append({
                    'id': video_id,
                    'title': title,
                    'formats': formats,
                    'subtitles': subtitles,
                    'playlist': playlist_title,
                    'playlist_id': playlist_id,
                    'chapter_id': chapter_id,
                    'chapter': chapter,
                })
        yield from course_list

    def _real_extract(self, url):
        course_id = self._match_id(url)
        data = self._download_json(
            f'https://api.gamedev.tv/api/courses/my/{course_id}', course_id,
            headers=self._API_HEADERS)

        return self.playlist_result(self._entries(data, course_id), course_id)

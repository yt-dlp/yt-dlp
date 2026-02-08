import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class GameDevTVDashboardIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gamedev\.tv/dashboard/courses/(?P<course_id>\d+)(?:/(?P<lecture_id>\d+))?'
    _NETRC_MACHINE = 'gamedevtv'
    _TESTS = [{
        'url': 'https://www.gamedev.tv/dashboard/courses/25',
        'info_dict': {
            'id': '25',
            'title': 'Complete Blender Creator 3: Learn 3D Modelling for Beginners',
            'tags': ['blender', 'course', 'all', 'box modelling', 'sculpting'],
            'categories': ['Blender', '3D Art'],
            'thumbnail': 'https://gamedev-files.b-cdn.net/courses/qisc9pmu1jdc.jpg',
            'upload_date': '20220516',
            'timestamp': 1652694420,
            'modified_date': '20241027',
            'modified_timestamp': 1730049658,
        },
        'playlist_count': 100,
    }, {
        'url': 'https://www.gamedev.tv/dashboard/courses/63/2279',
        'info_dict': {
            'id': 'df04f4d8-68a4-4756-a71b-9ca9446c3a01',
            'ext': 'mp4',
            'modified_timestamp': 1701695752,
            'upload_date': '20230504',
            'episode': 'MagicaVoxel Community Course Introduction',
            'series_id': '63',
            'title': 'MagicaVoxel Community Course Introduction',
            'timestamp': 1683195397,
            'modified_date': '20231204',
            'categories': ['3D Art', 'MagicaVoxel'],
            'season': 'MagicaVoxel Community Course',
            'tags': ['MagicaVoxel', 'all', 'course'],
            'series': 'MagicaVoxel 3D Art Mini Course',
            'duration': 1405,
            'episode_number': 1,
            'season_number': 1,
            'season_id': '219',
            'description': 'md5:a378738c5bbec1c785d76c067652d650',
            'display_id': '63-219-2279',
            'alt_title': '1_CC_MVX MagicaVoxel Community Course Introduction.mp4',
            'thumbnail': 'https://vz-23691c65-6fa.b-cdn.net/df04f4d8-68a4-4756-a71b-9ca9446c3a01/thumbnail.jpg',
        },
    }]
    _API_HEADERS = {}

    def _perform_login(self, username, password):
        try:
            response = self._download_json(
                'https://api.gamedev.tv/api/students/login', None, 'Logging in',
                headers={'Content-Type': 'application/json'},
                data=json.dumps({
                    'email': username,
                    'password': password,
                    'cart_items': [],
                }).encode())
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                raise ExtractorError('Invalid username/password', expected=True)
            raise

        self._API_HEADERS['Authorization'] = f'{response["token_type"]} {response["access_token"]}'

    def _real_initialize(self):
        if not self._API_HEADERS.get('Authorization'):
            self.raise_login_required(
                'This content is only available with purchase', method='password')

    def _entries(self, data, course_id, course_info, selected_lecture):
        for section in traverse_obj(data, ('sections', ..., {dict})):
            section_info = traverse_obj(section, {
                'season_id': ('id', {str_or_none}),
                'season': ('title', {str}),
                'season_number': ('order', {int_or_none}),
            })
            for lecture in traverse_obj(section, ('lectures', lambda _, v: url_or_none(v['video']['playListUrl']))):
                if selected_lecture and str(lecture.get('id')) != selected_lecture:
                    continue
                display_id = join_nonempty(course_id, section_info.get('season_id'), lecture.get('id'))
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                    lecture['video']['playListUrl'], display_id, 'mp4', m3u8_id='hls')
                yield {
                    **course_info,
                    **section_info,
                    'id': display_id,  # fallback
                    'display_id': display_id,
                    'formats': formats,
                    'subtitles': subtitles,
                    'series': course_info.get('title'),
                    'series_id': course_id,
                    **traverse_obj(lecture, {
                        'id': ('video', 'guid', {str}),
                        'title': ('title', {str}),
                        'alt_title': ('video', 'title', {str}),
                        'description': ('description', {clean_html}),
                        'episode': ('title', {str}),
                        'episode_number': ('order', {int_or_none}),
                        'duration': ('video', 'duration_in_sec', {int_or_none}),
                        'timestamp': ('video', 'created_at', {parse_iso8601}),
                        'modified_timestamp': ('video', 'updated_at', {parse_iso8601}),
                        'thumbnail': ('video', 'thumbnailUrl', {url_or_none}),
                    }),
                }

    def _real_extract(self, url):
        course_id, lecture_id = self._match_valid_url(url).group('course_id', 'lecture_id')
        data = self._download_json(
            f'https://api.gamedev.tv/api/courses/my/{course_id}', course_id,
            headers=self._API_HEADERS)['data']

        course_info = traverse_obj(data, {
            'title': ('title', {str}),
            'tags': ('tags', ..., 'name', {str}),
            'categories': ('categories', ..., 'title', {str}),
            'timestamp': ('created_at', {parse_iso8601}),
            'modified_timestamp': ('updated_at', {parse_iso8601}),
            'thumbnail': ('image', {url_or_none}),
        })

        entries = self._entries(data, course_id, course_info, lecture_id)
        if lecture_id:
            lecture = next(entries, None)
            if not lecture:
                raise ExtractorError('Lecture not found')
            return lecture
        return self.playlist_result(entries, course_id, **course_info)

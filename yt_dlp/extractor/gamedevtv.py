import json
from collections.abc import Generator, Iterable

from .common import InfoExtractor


class GameDevTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gamedev\.tv/dashboard/courses/(?P<id>\d+)'
    _NETRC_MACHINE = 'gamedevtv'
    _API_HEADERS = {}
    _TEST = {
        'url': 'https://www.gamedev.tv/courses/complete-blender-creator',
        'md5': '94202bb82884a4e6b2e3dab06f70110c',
        'info_dict': {
            'id': '565801ef-ee86-4c80-8cda-a50e970c6388-1',
            'ext': 'mp4',
            'title': 'promo vid.mp4',
            'thumbnail': r're:https?://.*\.jpg',
            'timestamp': 1713171606,
            'upload_date': '20240415',
            'age_limit': 0,
            '_old_archive_ids': ['generic 565801ef-ee86-4c80-8cda-a50e970c6388'],
            'duration': 94.0,
            'description': 'Learn How To Use Blender to Create Beautiful 3D models for Video Games, 3D Printing & More',
        },
    }

    def _perform_login(self, username: str, password: str) -> None:
        """
        Logs in a user to the GameDev.tv API using their credentials.
        This function sends a login request and updates the API headers with the received authorization token.

        Args:
            username (str): The email address of the user.
            password (str): The password of the user.

        Returns:
            None

        Raises:
            ValueError: If the login fails or the response does not contain the expected data.

        Examples:
            >>> _perform_login("user@example.com", "securepassword")
        """
        response = self._download_json(
            'https://api.gamedev.tv/api/students/login',
            None,
            'Logging in',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(
                {
                    'email': username,
                    'password': password,
                    'cart_items': [],
                },
            ).encode(),
        )
        self._API_HEADERS['Authorization'] = (
            f'{response['token_type']} {response['access_token']}'
        )

    def _get_lecture_info(self, data: dict, course_id: str) -> Generator:
        """
        Extracts lecture information from the provided course data.
        This function yields structured information about each lecture, including its title, formats, and subtitles.

        Args:
            data (dict): The course data containing sections and lectures.
            course_id (str): The unique identifier for the course.

        Returns:
            Generator: A generator that yields dictionaries containing lecture information.
        """
        course_list = []
        for section in data['data']['sections']:
            for lecture in section['lectures']:
                video_order = str(lecture['order']).zfill(2)
                title = (
                    (
                        data['data']['title']
                        + '-'
                        + 'Chapter_'
                        + str(section['order'])
                        + '-'
                        + section['title']
                        + '-'
                        + video_order
                        + '_'
                        + lecture['title']
                    )
                    .replace(' ', '_')
                    .replace(':', '')
                )
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                    lecture['video']['playListUrl'], course_id, 'mp4', m3u8_id='hls',
                )
                course_list.append(
                    {
                        'id': course_id,
                        'title': title,
                        'formats': formats,
                        'subtitles': subtitles,
                    },
                )
        yield from course_list

    def _real_extract(self, url: str) -> Iterable:
        """
        Extracts course information from the GameDev.tv API based on the provided URL.
        This function retrieves the course data and yields a structured playlist of lectures.

        Args:
            url (str): The URL of the course to extract information from.

        Returns:
            Iterable: An iterable containing the structured playlist result of the course lectures.

        Raises:
            ValueError: If the course ID cannot be matched from the URL or if the data retrieval fails.
        """
        course_id = self._match_id(url)

        data = self._download_json(
            f'https://api.gamedev.tv/api/courses/my/{course_id}',
            course_id,
            headers=self._API_HEADERS,
        )

        course_list = self._get_lecture_info(data, course_id)

        return self.playlist_result(course_list)

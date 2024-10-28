import json
from collections.abc import Generator, Iterable

from .common import InfoExtractor


class GameDevTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gamedev\.tv/dashboard/courses/(?P<id>\d+)'
    _NETRC_MACHINE = 'gamedevtv'
    _API_HEADERS = {}
    _TEST = {
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
            f"{response['token_type']} {response['access_token']}"
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
                video_id = str(lecture['order']).zfill(2)
                title = lecture['title']
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                    lecture['video']['playListUrl'], course_id, 'mp4', m3u8_id='hls',
                )
                playlist_title = data['data']['title']
                playlist_id = data['data']['id']
                chapter_id = str(section['order']).zfill(2)
                chapter = section['title']
                course_list.append(
                    {
                        'id': video_id,
                        'title': title,
                        'formats': formats,
                        'subtitles': subtitles,
                        'playlist': playlist_title,
                        'playlist_id': playlist_id,
                        'chapter_id': chapter_id,
                        'chapter': chapter,

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

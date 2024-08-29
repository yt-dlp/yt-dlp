import json

from .common import InfoExtractor


class VRPornIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vrporn\.com/(?P<display_id>.+)/'
    _LOGIN_URL = 'https://vrporn.com/api/playa/v2/auth/sign-in-password'
    _SINGLE_VIDEO_URL = 'https://vrporn.com/api/playa/v2/video/'
    _NETRC_MACHINE = 'vrporn'
    _USERTOKEN = None
    _TESTS = [
        {
            'url': 'https://vrporn.com/milkmans-diaries/',
            'md5': 'd50ab6c2b4adbe4fcd3f46e40984c7c8',
            'info_dict': {
                'id': '865690',
                'ext': 'mp4',
                'duration': 60,
                'age_limit': 18,
                'title': "Milkman's Diaries",
                'display_id': 'milkmans-diaries',
            },
        },
        {
            'url': 'https://vrporn.com/what-a-fellin/',
            'md5': 'eebd569dfea62c398947dbdc422ae0f0',
            'info_dict': {
                'id': '852931',
                'ext': 'mp4',
                'duration': 60,
                'age_limit': 18,
                'title': 'What A Feelin',
                'display_id': 'what-a-fellin',
            },
        },
    ]

    def _perform_login(self, username, password):
        user_data = self._download_json(
            self._LOGIN_URL,
            None,
            note='Logging in',
            data=json.dumps(
                {
                    'login': username,
                    'password': password,
                },
            ).encode(),
            headers={
                'Content-Type': 'application/json',
            },
        )
        self._USERTOKEN = user_data['data']['access_token']

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('display_id')

        webpage, _ = self._download_webpage_handle(url, display_id)

        video_id = self._search_regex(
            r"shortlink.+href=[\'\"]https://vrporn\.com/\?p=([0-9]+)[\'\"]",
            webpage,
            'id',
        )

        headers = {
            'Content-Type': 'application/json',
        }
        if self._USERTOKEN:
            headers.update(
                {
                    'Authorization': f'Bearer {self._USERTOKEN}',
                },
            )

        video_data = self._download_json(
            self._SINGLE_VIDEO_URL + video_id,
            None,
            query={'asd': 'asd'},
            note='fetching formats',
            headers=headers,
        )

        title = video_data['data']['title']

        formats = []

        duration = ''

        for detail in video_data['data']['details']:
            video_type = detail['type']
            duration = detail['duration_seconds']

            for link in detail['links']:
                if link['is_download']:
                    formats.append(
                        {
                            'url': link['url'],
                            'format_id': f'{video_type}-{link["quality_name"]}-{link["stereo"]}-{link["projection"]}',
                            'quality': link['quality_name'],
                            'resolution': link['quality_name'],
                        },
                    )

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'duration': duration,
            'formats': formats,
            'age_limit': 18,
        }

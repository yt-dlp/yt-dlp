import re
from .common import InfoExtractor
from ..utils import (
    urlencode_postdata,
    extract_attributes
)


class MurrtubeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        (?:
                            murrtube:|
                            https?://murrtube\.net/v/|
                            https?://murrtube\.net/videos/(?P<slug>[a-z0-9\-]+?)\-
                        )
                        (?P<id>[A-Z0-9]{4}|[a-f0-9]{8}\-[a-f0-9]{4}\-[a-f0-9]{4}\-[a-f0-9]{4}\-[a-f0-9]{12})
                    '''

    _TESTS = [
        {
            "url": "https://murrtube.net/videos/inferno-x-skyler-148b6f2a-fdcc-4902-affe-9c0f41aaaca0",
            "md5": "70380878a77e8565d4aea7f68b8bbb35",
            "info_dict": {
                "id": "ca885d8456b95de529b6723b158032e11115d",
                "ext": "mp4",
                "title": "Inferno X Skyler",
                "description": "Humping a very good slutty sheppy (roomate)",
                "uploader": "Inferno Wolf",
                "age_limit": 18,
                "thumbnail": "https://storage.murrtube.net/murrtube-production/ekbs3zcfvuynnqfx72nn2tkokvsd"
            },
        },
        {
            "url": "https://murrtube.net/v/0J2Q",
            "md5": "31262f6ac56f0ca75e5a54a0f3fefcb6",
            "info_dict": {
                "id": "8442998c52134968d9caa36e473e1a6bac6ca",
                "ext": "mp4",
                "uploader": "Hayel",
                "title": "Who's in charge now?",
                "description": """Fenny sneaked into my bed room and played naughty with one of my plushies. I caught him in the act and wanted to punish him. He thought he was in charge and wanted to use me instead but he wasn't prepared on my butt milking him within just a minute. Fenny: @fenny_ad (both here and on Twitter) Hayel on Twitter: https://twitter.com/plushmods""",
                "age_limit": 18,
                "thumbnail": "https://storage.murrtube.net/murrtube-production/fb1ojjwiucufp34ya6hxu5vfqi5s"
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_valid_url(url)
        # TODO: This part could be smarter (Set and store age cookie?)
        video_page = self._download_webpage(
            'https://murrtube.net', None, note='Getting session token')
        data = self._hidden_inputs(video_page)
        self._download_webpage(
            'https://murrtube.net/accept_age_check', None, 'Set age cookie', data=urlencode_postdata(data))
        video_page = self._download_webpage(url, None)
        video_attrs = extract_attributes(self._search_regex(r'(<video[^>]+>)', video_page, 'video'))
        playlist = video_attrs['data-url'].split('?')[0]
        matches = re.compile(r'https://storage.murrtube.net/murrtube-production/.+/(?P<id>.+)/index.m3u8').match(playlist).groupdict()
        video_id = matches['id']
        formats = self._extract_m3u8_formats(playlist, video_id, 'mp4', entry_protocol='m3u8_native', fatal=False)
        title = self._html_search_meta(
            'og:title', video_page, display_name='title', fatal=True)[:-11]
        description = self._html_search_meta(
            'og:description', video_page, display_name='description', fatal=True)
        thumbnail = self._html_search_meta(
            'og:image', video_page, display_name='thumbnail', fatal=True).split("?")[0]
        uploader = self._html_search_regex(
            r'<span class="pl-1 is-size-6 has-text-lighter">(.+?)</span>', video_page, 'uploader', default=None)
        return {
            'id': video_id,
            'title': title,
            'age_limit': 18,
            'formats': formats,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
        }

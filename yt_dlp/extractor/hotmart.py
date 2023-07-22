import json
import urllib.request

from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    traverse_obj,
    int_or_none,
    url_or_none,
)


class TeachableAPI:
    @staticmethod
    def get_hotmart_url():
        req = urllib.request.Request(
            'https://gns3.teachable.com/api/v2/hotmart/private_video?attachment_id=13633604',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            hotmart_url = (
                'https://player.hotmart.com/embed/'
                f'{data["video_id"]}?'
                f'signature={data["signature"]}&'
                'token='
                f'{data["teachable_application_key"]}'
            )
            return hotmart_url


class HotmartIE(InfoExtractor):
    _VALID_URL = r'https?://player\.hotmart\.com/embed/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [
        {
            'url': TeachableAPI.get_hotmart_url(),
            'md5': 'f9b6107c07300e4f77e23dde37f391a4',
            'info_dict': {
                'id': 'Nq7vkXmXRA',
                'video_id': 'Nq7vkXmXRA',
                'ext': 'mp4',
                'title': 'Hotmart video #Nq7vkXmXRA',
                'thumbnail': (
                    r're:https?://.*\.(?:jpg|jpeg|png|gif)\?token=exp=\d+~acl=.*~hmac=[a-f0-9]+$'
                ),
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_data_string = get_element_by_id('__NEXT_DATA__', webpage)
        video_data = self._parse_json(video_data_string, video_id, fatal=False)

        title = self._html_search_meta(
            ['og:title', 'title', 'twitter:title'],
            webpage, 'title', default='Hotmart video #' + video_id
        )

        url = traverse_obj(
            video_data,
            (
                'props',
                'pageProps',
                'applicationData',
                'mediaAssets',
                0,
                'urlEncrypted',
            ),
            expected_type=url_or_none,
        )
        thumbnail_url = traverse_obj(
            video_data,
            ('props', 'pageProps', 'applicationData', 'thumbnailUrl'),
            expected_type=url_or_none,
        )

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            url, video_id, 'mp4', fatal=False
        )

        description = self._og_search_description(webpage, default=None)
        chapter = None
        chapter_number = None

        return {
            'id': video_id,
            'video_id': video_id,
            'thumbnail': thumbnail_url,
            'formats': formats,
            'subtitles': subtitles,
            'title': title,
            'description': description,
            'chapter': chapter,
            'chapter_number': int_or_none(chapter_number),
        }

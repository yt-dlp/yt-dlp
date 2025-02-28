import json

from .common import InfoExtractor
from ..networking.common import Request


class CanalsurmasExtractorIE(InfoExtractor):
    _VALID_URL = r'https://www.canalsurmas.es/videos/(?P<id>[0-9]*)-.*'

    _TESTS = [
        {
            'url': 'https://www.canalsurmas.es/videos/44006-el-gran-queo-1-lora-del-rio-sevilla-20072014',
            'md5': '861f86fdc1221175e15523047d0087ef',
            'info_dict': {
                'id': '44006',
                'ext': 'mp4',
                'title': 'Lora del Río (Sevilla)  ',
                'description': 'md5:3d9ee40a9b1b26ed8259e6b71ed27b8b',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        access_token = self._download_json(
            Request(
                url='https://api-rtva.interactvty.com/jwt/token/',
                method='POST',
                headers={
                    'Content-Type': 'application/json',
                },
                data=json.dumps(
                    {
                        'username': 'canalsur_demo',
                        'password': 'dsUBXUcI',
                    },
                ).encode(),
            ),
            video_id,
        )['access']

        # An access token must be sent along with this request, otherwise, the server will return an unauthorized response. The access token can be obtained via the following global variable: window.__NUXT__.state.auth.accessToken (in the context of the video webpage).
        '''
        The 'optional_fields' query parameter of this request can have 1 or more values delimited by a ',' (comma) character. The known valid values for this query parameter are:
        - image
        - badges
        - type
        - duration
        - clasification
        - is_premium
        - inapppurchase
        - background
        - description
        - short_description
        - genre
        - emision_date
        - quality
        - has_subtitle
        - technical_details
        - trailer
        - title_image
        - is_ads
        - has_dvr
        - next_chapter
        - reference
          - A string value (e.g. "0000051497") that is needed when sending a request to get the main M3U8 file of the video.
        - season_category
        - main_category
          - A nested object that contains the following fields:
            - id
            - name
            - image
            - badges
            - type
            - duration
            - clasification
            - is_premium
            - inapppurchase
            - background
            - description
            - short_description
            - genre
            - emision_date
            - quality
            - has_subtitle
            - technical_details
            - trailer
            - title_image
            - reference
            - start_second_chapter
            - finish_second_chapter
            - alternative_image
            - image_mobile
            - image_medium
            - image_tiny
            - background_medium
            - background_tiny
            - alternative_image_medium
            - alternative_image_tiny
            - image_mobile_medium
            - image_mobile_tiny
        - start_second_chapter
        - finish_second_chapter
        - created_at
        - image_medium
        - alternative_image
        - alternative_image_medium
        - image_mobile
        - expiration_date
        - publish_date
        - is_freemium
        - tags
        '''
        video_info = self._download_json(
            url_or_request=f'https://api-rtva.interactvty.com/api/2.0/contents/content/{video_id}/?optional_fields=reference,description,main_category',
            video_id=video_id,
            headers={
                'Authorization': f'jwtok {access_token}',
            },
        )

        video_reference_num: str = video_info['reference']

        video_main_category_name_as_lower_case_underscore_delimited_string = video_info['main_category']['name'].lower().replace(' ', '_')

        # Another request can be made like so to get the main M3U8 file for a video with a specific reference number.
        # The returned M3U8 file points to other M3U8 files for different qualities (i.e. 480p, 1080p) and resolutions.
        # Example URL: https://cdn.rtva.interactvty.com/archivo_ott/el_gran_queo/0000051497/0000051497_3R.m3u8
        video_master_playlist_m3u8_url = f'https://cdn.rtva.interactvty.com/archivo_ott/{video_main_category_name_as_lower_case_underscore_delimited_string}/{video_reference_num}/{video_reference_num}_3R.m3u8'

        # Example URL of a M3U8 file for a specific quality (i.e. 480p): https://cdn.rtva.interactvty.com/archivo_ott/el_gran_queo/0000051496/0000051496_480p/0000051496_480p.m3u8
        formats = self._extract_m3u8_formats(
            video_master_playlist_m3u8_url,
            video_id,
        )

        return {
            'id': video_id,
            'title': video_info['name'],
            'description': video_info['description'],
            'formats': formats,
        }

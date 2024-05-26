from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    traverse_obj,
    int_or_none,
    url_or_none,
)


class HotmartIE(InfoExtractor):
    _VALID_URL = r'https?://player\.hotmart\.com/embed/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [
        {
            'url': (
                'https://player.hotmart.com/embed/pRQKDWkKLB?signature=S0Pr1OaDwGvKwQ8i6Y9whykEo4uuok2P4AShiYcyarvFkQDT_rBlR5L1qdIbIferFBHfTVJlXcbgUAwMMPiV6sWaA0XIU4OO282MO092DX_Z8KqS1h0Y-452TMjAt3dW2ZYMKWtfA2A2sxM7JmpYZZdMKTrT7nwoPsfbythXfph3dCLzxNQ0gS-rHfD7SYWuKJGN1JmK6iAygJf1thpskoeOJyK04SpDwMoqIOYfsrUktvsJFlV3oWM1tVoeDIQPWSZGXE6WRWDPNmTz6h7IHvc-QKGzoRy3_CvzSEioq2SaDNDdloECrKH37V1eCNvdaIr0dQeHqH_vI0NMBsfCow==&token=aa2d356b-e2f0-45e8-9725-e0efc7b5d29c&autoplay=autoplay'
            ),
            'md5': '95d7a252bb97954663fcf6c6db4b4555',
            'info_dict': {
                'id': 'pRQKDWkKLB',
                'video_id': 'pRQKDWkKLB',
                'ext': 'mp4',
                'title': 'Hotmart video #pRQKDWkKLB',
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

from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    traverse_obj,
)


class HotmartIE(InfoExtractor):
    _VALID_URL = r"https?://player\.hotmart\.com/embed/(?P<id>[a-zA-Z0-9]+)"
    _TESTS = [
        {
            "url": (
                "https://player.hotmart.com/embed/DLNy9QQ4qr?signature=cSnA"
                "r99eUZ0cne-ZMMJdjwwzV5hD4pLXVPO3urVQUF0XoWaG3MqF6jhfPFf7il"
                "Eh6YdtJeirComlat6kF_ZFQMFf1iW-lmqXfsWdANDVYfh8-lqjKY02_Xxg"
                "a0nwV3WwrYRkuQ7pnJZiueGkbSHvfixgNGzp12kNDqK1ynPojnVfIaijK2"
                "NQV9A0oeG7icUW2K-C9KD0phuuhQmt5qS8u7FxRC7buQm5MoSKYGMi_ot2"
                "FUSe2Mgx_S1TOYYNgi0FiTyUyixn884HouIIz8e_N4ceE8PF7x8mVK_IWH"
                "gIGic2NhBo9aAo7m8TmP4FA5SNaQnEIPqY1G7SHmDoBvcXyA==&token=a"
                "a2d356b-e2f0-45e8-9725-e0efc7b5d29c&autoplay=autoplay"
            ),
            "md5": "620b25017119475adbd6f7932294129d",
            "info_dict": {
                "id": "DLNy9QQ4qr",
                "video_id": "DLNy9QQ4qr",
                "ext": "mp4",
                "title": "Hotmart video #DLNy9QQ4qr",
                "thumbnail": (
                    r"re:https?://.*\.(?:jpg|jpeg|png|gif)\?token=exp=\d+~acl"
                    r"=.*~hmac=[a-f0-9]+$"
                ),
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_data_string = get_element_by_id("__NEXT_DATA__", webpage)
        video_data = self._parse_json(video_data_string, video_id)

        # Extract the title from the video_data object
        title = traverse_obj(
            video_data, ("props", "pageProps", "applicationData", "mediaTitle")
        )

        url = traverse_obj(
            video_data,
            (
                "props",
                "pageProps",
                "applicationData",
                "mediaAssets",
                0,
                "urlEncrypted",
            ),
        )
        thumbnail_url = traverse_obj(
            video_data,
            ("props", "pageProps", "applicationData", "thumbnailUrl"),
        )

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            url, video_id, "mp4"
        )

        description = self._og_search_description(webpage, default=None)
        chapter = None
        chapter_number = None

        return {
            "id": video_id,
            "video_id": video_id,
            "thumbnail": thumbnail_url,
            "formats": formats,
            "subtitles": subtitles,
            "title": title,
            "description": description,
            "chapter": chapter,
            "chapter_number": chapter_number,
        }

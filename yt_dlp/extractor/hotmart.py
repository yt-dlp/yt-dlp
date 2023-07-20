from .common import InfoExtractor
from ..utils import get_element_by_id, traverse_obj


class HotmartIE(InfoExtractor):
    _VALID_URL = r"https?://player\.hotmart\.com/embed/(?P<id>[a-zA-Z0-9]+)"
    _TESTS = [
        {
            "url": "https://player.hotmart.com/embed/Nq7rJ2mARA?signature=SjylayL7eOhQwSYJNxKWY1g2gqJ5WMz4l1VSuOGVv6qAJnDXFsK6fSXziJ_u12YHSfrT0SfHTYxqgGqZ4UBLLmo7ScIzDQR9JUs_sJbLVtp0g6ferIbEIJxjyXk2MO1suyhYtdIz8N5CaZ9mJ-kE2wBK3SlR1eYQVZ9EEmf4Y254wsB71JGJW8_blsKV31VWKWKaFqQ5XmaHuS9d5N5cVG2ZDetxgqEea2ULLUwD6U2i2jBpnOobbEiXga5KRO6r1zA0xOOzx_K3BxbrS1UpmTfKpk1Z3Pt35aoKtvG9wjhJpR-4n-0KKKr6fUq8vn-t6W9bqSnULAJb-biBsNhx2w==&token=aa2d356b-e2f0-45e8-9725-e0efc7b5d29c&autoplay=autoplay",
            "md5": "TODO: md5 sum of the first 10241 bytes of the video file (use --test)",
            "info_dict": {
                "id": "42",
                "ext": "mp4",
                "title": "Video title goes here",
                "thumbnail": r"re:^https?://.*\.jpg$",
                # TODO more properties, either as:
                # * A value
                # * MD5 checksum; start the string with md5:
                # * A regular expression; start the string with re:
                # * Any Python type (for example int or float)
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_data_string = get_element_by_id("__NEXT_DATA__", webpage)
        video_data = self._parse_json(video_data_string, video_id)

        # Encrypted url is 'urlEncrypted' instead of 'url'
        # See https://github.com/yt-dlp/yt-dlp/issues/3564 for initial discussion of design
        url = traverse_obj(
            video_data,
            ("props", "pageProps", "applicationData", "mediaAssets", 0, "url"),
        )
        thumbnail_url = traverse_obj(
            video_data, ("props", "pageProps", "applicationData", "urlThumbnail")
        )

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            url, video_id, "mp4"
        )

        title = self._og_search_title(webpage, default=None)
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

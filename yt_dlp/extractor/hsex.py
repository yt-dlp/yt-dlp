from .common import InfoExtractor


class HSexIE(InfoExtractor):
    IE_NAME = 'hsex'
    _VALID_URL = r'https?://hsex\.men/(?P<id>video-[0-9]+)\.htm'
    _TESTS = [{
        'url': 'https://hsex.men/video-1016887.htm',
        'info_dict': {
            'id': 'video-1016887',
            'title': '这才是真正的暴力打桩狂操！高潮迭起彻底释放【简界免费看完整版】.',
            'description': '这才是真正的暴力打桩狂操！高潮迭起彻底释放【简界免费看完整版】.',
            'uploader_id': 'jdjjfrnn',
            'duration_string': '00:12:14',
            'ext': 'mp4',
            'age_limit': 18,
        },
    }, {
        'url': 'https://hsex.men/video-594002.htm',
        'info_dict': {
            'id': 'video-594002',
            'title': '《探总奉上》热爱黑丝丝袜，撕开了干',
            'description': '《探总奉上》热爱黑丝丝袜，撕开了干',
            'uploader_id': '91探花探总',
            'duration_string': '00:25:07',
            'ext': 'mp4',
            'age_limit': 18,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, impersonate=True)
        title = self._html_search_meta(['og:title', 'name'], webpage)
        description = self._html_search_meta(['og:description', 'description'], webpage)
        uploader_id = self._html_search_meta(['og:video:actor'], webpage)
        duration_string = self._html_search_meta(['video:duration', 'duration'], webpage)
        video_url = self._search_regex(r'"video-source" src="(.+?)"', webpage, 'video_url', fatal=True)
        formats, _ = self._extract_m3u8_formats_and_subtitles(video_url, video_id, ext='mp4')
        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader_id': uploader_id,
            'duration_string': duration_string,
            'formats': formats,
            'age_limit': 18,
        }

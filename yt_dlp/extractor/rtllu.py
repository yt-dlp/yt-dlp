from .common import InfoExtractor


class RTLLuBaseIE(InfoExtractor):
    _MEDIA_REGEX = {
        'video': r'<rtl-player\s*poster\s*=\s*\"(?P<thumbnail_url>[\"\w\.://-]+)\"\s*title\s*=\s*(?P<title>[\"\w\.-]+)\s*hls\s*=\s*\"(?P<media_url>[\w\.\:/-]+)\"',
        'audio': r'<rtl-audioplayer\s*src\s*=\s*\"(?P<media_url>[\w\.\:/-]+)\"',
    }

    def get_media(self, media_type, webpage, video_id):
        media_url = self._search_regex(
            self._MEDIA_REGEX[media_type], webpage, 'media_url', group=('media_url'))

        return media_url


class RTLLuTeleVODIE(RTLLuBaseIE):
    IE_NAME = 'rtl.lu:tele-vod'
    _VALID_URL = r'https?://(?:www.)?rtl\.lu/(tele/(?P<slug>[\w-]+)/v/|video/)(?P<id>\d+)(\.html)?'
    _TESTS = [{
        'url': 'https://www.rtl.lu/tele/de-journal-vun-der-tele/v/3266757.html',
        'info_dict': {
            'id': '3266757',
            'title': 'Informatiounsversammlung Héichwaasser',
            'ext': 'mp4',
            'thumbnail': 'https://replay-assets.rtl.lu/2021/11/16/d3647fc4-470d-11ec-adc2-3a00abd6e90f_00008.jpg',
            'description': 'md5:b1db974408cc858c9fd241812e4a2a14',
        }
    }, {
        'url': 'https://www.rtl.lu/video/3295215',
        'info_dict': {
            'id': '3295215',
            'title': 'Kulturassisen iwwer d\'Bestandsopnam vum Lëtzebuerger Konscht',
            'ext': 'mp4',
            'thumbnail': 'https://replay-assets.rtl.lu/2022/06/28/0000_3295215_0000.jpg',
            'description': 'md5:85bcd4e0490aa6ec969d9bf16927437b',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        hls_url = self.get_media('video', webpage, video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls_url, video_id)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._og_search_thumbnail(webpage),
        }

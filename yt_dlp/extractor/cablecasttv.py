from .common import InfoExtractor


class CableCastTVIE(InfoExtractor):
    _VALID_URL = r'https://wctv\.wilmette\.com/CablecastPublicSite/show/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://wctv.wilmette.com/CablecastPublicSite/show/532',
        'md5': '17e7ed129582babf6d1ae5c3b9d70d18',
        'info_dict': {
            'id': '532',
            'ext': 'mp4',
            'title': 'Village Board Meeting 4/24/24',
        },
    }, {
        'url': 'https://wctv.wilmette.com/CablecastPublicSite/show/53/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        url_video_page = self._html_search_regex(r'<iframe[^>]*class=\"trms-player\"[^>]*src=\"([^\"]+)\"', webpage, 'url_video_webpage')
        webpage_video = self._download_webpage(url_video_page, video_id)
        video_url = self._html_search_regex(r'"([^\"]*\.m3u8)"', webpage_video, 'video URL')

        formats = []
        formats.extend(self._extract_m3u8_formats(video_url, video_id, ext='mp4', m3u8_id='hls'))

        title = self._og_search_title(webpage) or self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }

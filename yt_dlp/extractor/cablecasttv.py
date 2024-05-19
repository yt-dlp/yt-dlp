from .common import InfoExtractor

import re


class CableCastTVIE(InfoExtractor):
    _VALID_URL = r'https://wctv\.wilmette\.com/CablecastPublicSite/show/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://wctv.wilmette.com/CablecastPublicSite/show/532',
        'md5': 'fc12bce4a9c1335f153500c8fea6e1a8',
        'info_dict': {
            'id': '532',
            'ext': 'mp4',
            'title': 'Village Board Meeting 4/24/24',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        with open('output.txt', 'w', encoding='utf-8') as file:
            file.write(webpage)


        url_video_webpage = self._html_search_regex(r'<iframe[^>]*class=\"trms-player\"[^>]*src=\"([^\"]+)\"', webpage, 'url_video_webpage')
        webpage_video = self._download_webpage(url_video_webpage, video_id)

        video_url = self._html_search_regex(r'"([^\"]*\.m3u8)"', webpage_video, 'video URL')
        print(video_url)

        formats = []
        formats.extend(self._extract_m3u8_formats(video_url, video_id, ext='mp4', m3u8_id='hls'))
        print(formats)
        #format_url = re.sub(r'\\', '', format_url)

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')

#        base_url = re.search(r'^(https?://[a-zA-Z0-9_-]+\.to)', url).group(1)
#        http_headers = {'Referer': base_url}

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
#            'http_headers': http_headers
        }
 

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
    }, {
        'url': 'https://fyptt.to/10382/beautiful-livestream-tits-and-nipples-slip-from-girls-who-loves-talking-with-their-viewers/',
        'only_matching': True,
    }, {
        'url': 'https://fyptt.to/120/small-tits-fit-blonde-dancing-naked-at-the-front-door-on-tiktok',
        'only_matching': True,
    }, {
        'url': 'https://fkbae.to/18',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []
        format_url = self._html_search_regex(r'"embedURL":"([^"]+)"', webpage, 'video URL')
        format_url = re.sub(r'\\', '', format_url)

        webpage_video = self._download_webpage(format_url, video_id)

        match = re.search(r'(https:\/\/[^"]+\.mp4)', webpage_video)
        format_url = match.group(1)
        formats.append({
            'url': format_url,
            'format_id': 'default',
        })

        title = self._html_search_regex(r'<span class="fl-heading-text">(.+?)</span>', webpage, 'title')

#        base_url = re.search(r'^(https?://[a-zA-Z0-9_-]+\.to)', url).group(1)
#        http_headers = {'Referer': base_url}

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
#            'http_headers': http_headers
        }
 

from .common import InfoExtractor


class MiaoPaiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?miaopai\.com/show/(?P<id>[-A-Za-z0-9~_]+)'
    _TEST = {
        'url': 'http://www.miaopai.com/show/n~0hO7sfV1nBEw4Y29-Hqg__.htm',
        'md5': '095ed3f1cd96b821add957bdc29f845b',
        'info_dict': {
            'id': 'n~0hO7sfV1nBEw4Y29-Hqg__',
            'ext': 'mp4',
            'title': '西游记音乐会的秒拍视频',
            'thumbnail': 're:^https?://.*/n~0hO7sfV1nBEw4Y29-Hqg___m.jpg',
        }
    }

    _USER_AGENT_IPAD = 'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            url, video_id, headers={'User-Agent': self._USER_AGENT_IPAD})

        title = self._html_extract_title(webpage)
        thumbnail = self._html_search_regex(
            r'<div[^>]+class=(?P<q1>[\'"]).*\bvideo_img\b.*(?P=q1)[^>]+data-url=(?P<q2>[\'"])(?P<url>[^\'"]+)(?P=q2)',
            webpage, 'thumbnail', fatal=False, group='url')
        videos = self._parse_html5_media_entries(url, webpage, video_id)
        info = videos[0]

        info.update({
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
        })
        return info

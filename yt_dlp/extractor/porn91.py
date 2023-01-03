import urllib.parse

from .common import InfoExtractor
from ..utils import (
    parse_duration,
    int_or_none,
    remove_end,
    ExtractorError,
)

class Porn91IE(InfoExtractor):
    IE_NAME = '91porn'
    _VALID_URL = r'(?:https?://)(?:www\.|)91porn\.com/.+?\?viewkey=(?P<id>[\w\d]+)'

    _TESTS = [{
        'url': 'http://91porn.com/view_video.php?viewkey=7e42283b4f5ab36da134',
        'md5': 'd869db281402e0ef4ddef3c38b866f86',
        'info_dict': {
            'id': '7e42283b4f5ab36da134',
            'title': '18岁大一漂亮学妹，水嫩性感，再爽一次！',
            'ext': 'mp4',
            'duration': 431,
            'comment_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://91porn.com/view_video.php?viewkey=23a2ab9f50a9bcdc410a',
        'md5': '4bf9f0f108368a3af6ae7be4973e38d6',
        'info_dict': {
            'id': '23a2ab9f50a9bcdc410a',
            'title': '“老师下面都湿了，快给我”',
            'ext': 'mp4',
            'duration': 617,
            'comment_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://91porn.com/view_video.php?viewkey=726186267387ffe1e5e6',
        'md5': 'b0067d158495566fe3d20bafd89e36d1',
        'info_dict': {
            'id': '726186267387ffe1e5e6',
            'title': '见过卖老婆的，那你见过卖亲闺女的吗？',
            'ext': 'mp4',
            'duration': 244,
            'comment_count': int,
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._set_cookie('91porn.com', 'language', 'cn_CN')

        webpage = self._download_webpage(
            'http://91porn.com/view_video.php?viewkey=%s' % video_id, video_id)

        if '作为游客，你每天只可观看10个视频' in webpage:
            raise ExtractorError('91 Porn says: Daily limit 10 videos exceeded', expected=True)

        title = self._html_extract_title(webpage)
        title = remove_end(title.replace('\n', ''), 'Chinese homemade video').strip()

        video_link_url = self._search_regex(
            r'document\.write\(\s*strencode2\s*\(\s*((?:"[^"]+\")|(?:\'[^\']+\'))\s*\)\s*\)',
            webpage, 'video link')
        video_link_url = self._search_regex(
            r"src=\'([^\']+)\'", urllib.parse.unquote(video_link_url), 'unquoted video link')

        duration = parse_duration(self._search_regex(
            r'时长:\s*<span[^>]*>\s*(\d+:\d+)\s*</span>', webpage, 'duration', fatal=False))

        comment_count = int_or_none(self._search_regex(
            r'留言:\s*<span[^>]*>\s*(\d+)\s*</span>', webpage, 'comment count', fatal=False))

        return {
            'id': video_id,
            'url': video_link_url,
            'ext': 'mp4',
            'title': title,
            'duration': duration,
            'comment_count': comment_count,
            'age_limit': 18
        }

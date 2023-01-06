import urllib.parse
import calendar
from .common import InfoExtractor
from ..utils import (
    determine_ext,
    parse_duration,
    int_or_none,
    date_from_str,
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
            'description': '想看我拍新的系列都请帮我加精跟5星好评哦！希望大家鼎力支持，谢过了。我再重申，这次是朋友介绍安排的漂亮学生，费用不低，不过胜在年轻听话，水嫩性感，很超值的女生（6分05有91验证）。PS:本人强壮耐久，事业型男，愿意结交江浙沪的漂亮学妹，加Q：2889560495，语音验证性别，欢迎女生约我，或者靠谱男来一起泡美眉。',
            'ext': 'mp4',
            'duration': 431,
            'release_date': '20150520',
            'comment_count': int,
            'view_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://91porn.com/view_video.php?viewkey=23a2ab9f50a9bcdc410a',
        'md5': '4bf9f0f108368a3af6ae7be4973e38d6',
        'info_dict': {
            'id': '23a2ab9f50a9bcdc410a',
            'title': '“老师下面都湿了，快给我”',
            'description': '疫情开放  炮友出圈',
            'ext': 'm3u8',
            'duration': 617,
            'release_date': '20221231',
            'comment_count': int,
            'view_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://91porn.com/view_video.php?viewkey=726186267387ffe1e5e6',
        'md5': 'b0067d158495566fe3d20bafd89e36d1',
        'info_dict': {
            'id': '726186267387ffe1e5e6',
            'title': '见过卖老婆的，那你见过卖亲闺女的吗？',
            'description': '疫情当下，如何约炮？',
            'ext': 'm3u8',
            'duration': 244,
            'release_date': '20221231',
            'comment_count': int,
            'view_count': int,
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

        release_date = self._search_regex(
            r'<span\s+class=["\']title-yakov["\']>(\d{4}-\d{2}-\d{2})</span>', webpage, 'timestamp', fatal=False)
        release_date = release_date.replace('-', '') if release_date else None

        description = self._search_regex(
            r'<span\s+class=["\']more title["\']>([^<]*)<br', webpage, 'description', fatal=False).strip()

        duration = parse_duration(self._search_regex(
            r'时长:\s*<span[^>]*>\s*(\d+:\d+)\s*</span>', webpage, 'duration', fatal=False))

        comment_count = int_or_none(self._search_regex(
            r'留言:\s*<span[^>]*>\s*(\d+)\s*</span>', webpage, 'comment count', fatal=False))

        view_count = int_or_none(self._search_regex(
            r'热度:\s*<span[^>]*>\s*(\d+)\s*</span>', webpage, 'comment count', fatal=False))

        return {
            'id': video_id,
            'url': video_link_url,
            'ext': determine_ext(video_link_url),
            'title': title,
            'release_date': release_date,
            'description': description,
            'duration': duration,
            'comment_count': comment_count,
            'view_count': view_count,
            'age_limit': 18,
        }

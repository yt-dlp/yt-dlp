import urllib.parse
from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_duration,
    remove_end,
    unified_strdate,
    ExtractorError,
)


class Porn91IE(InfoExtractor):
    IE_NAME = '91porn'
    _VALID_URL = r'(?:https?://)(?:www\.|)91porn\.com/.*([\?&])viewkey=(?P<id>[\w\d]+)'

    _TESTS = [{
        'url': 'http://91porn.com/view_video.php?viewkey=7e42283b4f5ab36da134',
        'md5': 'd869db281402e0ef4ddef3c38b866f86',
        'info_dict': {
            'id': '7e42283b4f5ab36da134',
            'title': '18岁大一漂亮学妹，水嫩性感，再爽一次！',
            'description': 'md5:1ff241f579b07ae936a54e810ad2e891',
            'ext': 'mp4',
            'duration': 431,
            'upload_date': '20150520',
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
            'description': 'md5:5561851475c2d3f39aafd208ec705d3a',
            'ext': 'm3u8',
            'duration': 244,
            'upload_date': '20221231',
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

        if '视频不存在,可能已经被删除或者被举报为不良内容!' in webpage:
            raise ExtractorError('91 Porn says: Video does not exist', expected=True)

        if '作为游客，你每天只可观看15个视频' in webpage:
            raise ExtractorError('91 Porn says: Daily limit 15 videos exceeded', expected=True)

        title = self._html_extract_title(webpage)
        title = remove_end(title.replace('\n', ''), 'Chinese homemade video').strip()

        video_link_url = self._search_regex(
            r'document\.write\(\s*strencode2\s*\(\s*((?:"[^"]+")|(?:\'[^\']+\'))\s*\)\s*\)', webpage, 'video link')
        video_link_url = self._search_regex(
            r'src=["\']([^"\']+)["\']', urllib.parse.unquote(video_link_url), 'unquoted video link')

        upload_date = self._search_regex(
            r'<span\s+class=["\']title-yakov["\']>(\d{4}-\d{2}-\d{2})</span>', webpage, 'upload_date', fatal=False)
        upload_date = unified_strdate(upload_date)

        description = self._html_search_regex(
            r'<span\s+class=["\']more title["\']>\s*(.*(?!</span>))\s*</span>', webpage, 'description', fatal=False)

        duration = parse_duration(self._search_regex(
            r'时长:\s*<span[^>]*>\s*(\d+:\d+:\d+)\s*</span>', webpage, 'duration', fatal=False))

        comment_count = int_or_none(self._search_regex(
            r'留言:\s*<span[^>]*>\s*(\d+)\s*</span>', webpage, 'comment count', fatal=False))

        view_count = int_or_none(self._search_regex(
            r'热度:\s*<span[^>]*>\s*(\d+)\s*</span>', webpage, 'view count', fatal=False))

        formats, subtitles = self._get_formats_and_subtitle(video_link_url, video_id)

        return {
            'id': video_id,
            'url': video_link_url,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'upload_date': upload_date,
            'description': description,
            'duration': duration,
            'comment_count': comment_count,
            'view_count': view_count,
            'age_limit': 18,
        }

    def _get_formats_and_subtitle(self, video_link_url, video_id):
        formats, subtitles = [], {}
        ext = determine_ext(video_link_url)
        if ext == 'm3u8':
            fmts, subs = self._extract_m3u8_formats_and_subtitles(video_link_url, video_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        else:
            formats.append({'url': video_link_url, 'ext': ext})
        return formats, subtitles

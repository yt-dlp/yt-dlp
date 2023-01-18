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
    _VALID_URL = r'(?:https?://)(?:www\.|)91porn\.com/.*([\?&]{1})viewkey=(?P<id>[\w\d]+)'

    _TESTS = [{
       'url': 'http://91porn.com/view_video.php?viewkey=7e42283b4f5ab36da134',
       'md5': 'd869db281402e0ef4ddef3c38b866f86',
       'info_dict': {
            'id': '7e42283b4f5ab36da134',
            'title': '18岁大一漂亮学妹，水嫩性感，再爽一次！',
            'description': '想看我拍新的系列都请帮我加精跟5星好评哦！希望大家鼎力支持，谢过了。我再重申，这次是朋友介绍安排的漂亮学生，费用不低，不过胜在年轻听话，水嫩性感，很超值的女生（6分05有91验证）。PS:本人强壮耐久，事业型男，愿意结交江浙沪的漂亮学妹，加Q：2889560495，语音验证性别，欢迎女生约我，或者靠谱男来一起泡美眉。',
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
            'description': '疫情当下，如何约炮？\n--19kn.cc--\n拥有全国线下学生、少妇、反差婊、兼职良家。\n并且免费！！！\n只需要一个电话，一个定位，就能送炮上门。可提前查看照片\n（妹子自带48小时核酸报告）\n约炮，我们是认真的！\n并且拥有三大优势！\n\n1、各种求包养母狗，学生妹资源。为你解决各种需要。--19kn.cc--\n\n2、所有女性会员经过实名视频验证，平台严选，杜绝各种骗红包，口嗨者。--19kn.cc--\n\n3、5年大平台，91许多约炮案例，包括知名博主女伴，均是我们撮合成功的，保障会员隐私，并且约炮3次可自行联系平台进行信息发布。--19kn.cc--\n\n平台5周年庆活动，特回馈91狼友\n\n1、所有女性会员，如果参假，举报客服，核实成功奖励10000人民币。\n\n2、约炮成功并且反馈客服，赠送91vip自拍达人号\n\n3、情侣入驻，可享受专属奖励（奖金5000元）\n\n年关将近，平台大放血，只为各位狼友能找到固定性伴侣，度过美好新年！\n\n约炮渠道请登录--19kn.cc--\n\nPS:招网络客服，对接客户，安排妹子（要求耐心，熟悉客服流程优先，有电脑优先）工作时间:12小时制，\n\n招男模，女模（要求形象气质佳，需提供体检报告）\n有意可以联系官方招聘邮箱[email\xa0protected]',
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

        return {
            'id': video_id,
            'url': video_link_url,
            'ext': determine_ext(video_link_url),
            'title': title,
            'upload_date': upload_date,
            'description': description,
            'duration': duration,
            'comment_count': comment_count,
            'view_count': view_count,
            'age_limit': 18,
        }

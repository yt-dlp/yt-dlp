# coding: utf-8

from ..utils import (
    int_or_none,
    traverse_obj,
    url_or_none,
)
from .common import (
    InfoExtractor,
    compat_urllib_parse_unquote,
)


class DouyinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?douyin\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.douyin.com/video/6961737553342991651',
        'md5': '10523312c8b8100f353620ac9dc8f067',
        'info_dict': {
            'id': '6961737553342991651',
            'ext': 'mp4',
            'title': '#杨超越  小小水手带你去远航❤️',
            'uploader': '杨超越',
            'upload_date': '20210513',
            'timestamp': 1620905839,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6982497745948921092',
        'md5': 'd78408c984b9b5102904cf6b6bc2d712',
        'info_dict': {
            'id': '6982497745948921092',
            'ext': 'mp4',
            'title': '这个夏日和小羊@杨超越 一起遇见白色幻想',
            'uploader': '杨超越工作室',
            'upload_date': '20210708',
            'timestamp': 1625739481,
            'uploader_id': '408654318141572',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6953975910773099811',
        'md5': '72e882e24f75064c218b76c8b713c185',
        'info_dict': {
            'id': '6953975910773099811',
            'ext': 'mp4',
            'title': '#一起看海  出现在你的夏日里',
            'uploader': '杨超越',
            'upload_date': '20210422',
            'timestamp': 1619098692,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6950251282489675042',
        'md5': 'b4db86aec367ef810ddd38b1737d2fed',
        'info_dict': {
            'id': '6950251282489675042',
            'ext': 'mp4',
            'title': '哈哈哈，成功了哈哈哈哈哈哈',
            'uploader': '杨超越',
            'upload_date': '20210412',
            'timestamp': 1618231483,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6963263655114722595',
        'md5': '1abe1c477d05ee62efb40bf2329957cf',
        'info_dict': {
            'id': '6963263655114722595',
            'ext': 'mp4',
            'title': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
            'uploader': '杨超越',
            'upload_date': '20210517',
            'timestamp': 1621261163,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        render_data = self._parse_json(
            self._search_regex(
                r'<script [^>]*\bid=[\'"]RENDER_DATA[\'"][^>]*>(%7B.+%7D)</script>',
                webpage, 'render data'),
            video_id, transform_source=compat_urllib_parse_unquote)
        details = traverse_obj(render_data, (..., 'aweme', 'detail'), get_all=False)

        thumbnails = [{'url': self._proto_relative_url(url)} for url in traverse_obj(
            details, ('video', ('cover', 'dynamicCover', 'originCover')), expected_type=url_or_none, default=[])]

        common = {
            'width': traverse_obj(details, ('video', 'width'), expected_type=int),
            'height': traverse_obj(details, ('video', 'height'), expected_type=int),
            'ext': 'mp4',
        }
        formats = [{**common, 'url': self._proto_relative_url(url)} for url in traverse_obj(
            details, ('video', 'playAddr', ..., 'src'), expected_type=url_or_none, default=[]) if url]
        self._remove_duplicate_formats(formats)

        download_url = traverse_obj(details, ('download', 'url'), expected_type=url_or_none)
        if download_url:
            formats.append({
                **common,
                'format_id': 'download',
                'url': self._proto_relative_url(download_url),
                'quality': 1,
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': details.get('desc') or self._html_search_meta('title', webpage),
            'formats': formats,
            'thumbnails': thumbnails,
            'uploader': traverse_obj(details, ('authorInfo', 'nickname'), expected_type=str),
            'uploader_id': traverse_obj(details, ('authorInfo', 'uid'), expected_type=str),
            'uploader_url': 'https://www.douyin.com/user/%s' % traverse_obj(
                details, ('authorInfo', 'secUid'), expected_type=str),
            'timestamp': int_or_none(details.get('createTime')),
            'duration': traverse_obj(details, ('video', 'duration'), expected_type=int),
            'view_count': traverse_obj(details, ('stats', 'playCount'), expected_type=int),
            'like_count': traverse_obj(details, ('stats', 'diggCount'), expected_type=int),
            'repost_count': traverse_obj(details, ('stats', 'shareCount'), expected_type=int),
            'comment_count': traverse_obj(details, ('stats', 'commentCount'), expected_type=int),
        }

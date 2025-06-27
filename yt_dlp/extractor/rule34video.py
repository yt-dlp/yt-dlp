import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_element_html_by_class,
    get_elements_by_class,
    int_or_none,
    merge_dicts,
    parse_count,
    parse_duration,
    unescapeHTML,
)
from ..utils.traversal import traverse_obj


class Rule34VideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/videos?/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://rule34video.com/video/3065157/shot-it-mmd-hmv/',
            'md5': 'ffccac2c23799dabbd192621ae4d04f3',
            'info_dict': {
                'id': '3065157',
                'ext': 'mp4',
                'title': 'Shot It-(mmd hmv)',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065157/preview.jpg',
                'duration': 347.0,
                'age_limit': 18,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'timestamp': 1639872000,
                'description': 'https://discord.gg/aBqPrHSHvv',
                'upload_date': '20211219',
                'uploader': 'Sweet HMV',
                'uploader_url': 'https://rule34video.com/members/22119/',
                'categories': ['3D', 'MMD', 'iwara'],
                'tags': 'mincount:10',
            },
        },
        {
            'url': 'https://rule34video.com/videos/3065296/lara-in-trouble-ep-7-wildeerstudio/',
            'md5': '6bb5169f9f6b38cd70882bf2e64f6b86',
            'info_dict': {
                'id': '3065296',
                'ext': 'mp4',
                'title': 'Lara in Trouble Ep. 7 [WildeerStudio]',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065296/preview.jpg',
                'duration': 938.0,
                'age_limit': 18,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'timestamp': 1640131200,
                'description': '',
                'creators': ['WildeerStudio'],
                'upload_date': '20211222',
                'uploader': 'CerZule',
                'uploader_url': 'https://rule34video.com/members/36281/',
                'categories': ['3D', 'Tomb Raider'],
                'tags': 'mincount:40',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []

        for mobj in re.finditer(r'<a[^>]+href="(?P<video_url>[^"]+download=true[^"]+)".*>(?P<ext>[^\s]+) (?P<quality>[^<]+)p</a>', webpage):
            url, ext, quality = mobj.groups()
            formats.append({
                'url': url,
                'ext': ext.lower(),
                'quality': quality,
            })

        categories, creators, uploader, uploader_url = [None] * 4
        for col in get_elements_by_class('col', webpage):
            label = clean_html(get_element_by_class('label', col))
            if label == 'Categories':
                categories = list(map(clean_html, get_elements_by_class('item', col)))
            elif label == 'Artist':
                creators = list(map(clean_html, get_elements_by_class('item', col)))
            elif label == 'Uploaded by':
                uploader_link = get_element_html_by_class('btn_link', col)
                uploader = clean_html(uploader_link)
                uploader_url = extract_attributes(uploader_link or '').get('href')

        view_count, duration = [None] * 2
        for item_info in get_elements_by_class('item_info', webpage):
            item_info_text = clean_html(item_info)
            if get_element_by_class('custom-eye', item_info) is not None:
                precise_view_count = re.search(r'\(([\d,]+)\)', item_info_text)
                view_count = parse_count(precise_view_count.group(1) if precise_view_count is not None else item_info_text)
            elif get_element_by_class('custom-time', item_info) is not None:
                duration = parse_duration(clean_html(item_info))

        like_count = None
        if like_count_text := re.search(r'\(([\d,]+)\)', get_element_by_class('voters count', webpage)):
            like_count = parse_count(like_count_text.group(1))

        json_ld = traverse_obj(self._search_json_ld(webpage, video_id, default={}), ({
            'title': 'title',
            'view_count': 'view_count',
            'like_count': 'like_count',
            'duration': 'duration',
            'timestamp': 'timestamp',
            'description': 'description',
            'thumbnail': ('thumbnails', 0, 'url'),
        }))

        return merge_dicts({
            'id': video_id,
            'formats': formats,
            'title': self._html_extract_title(webpage),
            'thumbnail': self._html_search_regex(
                r'preview_url:\s+\'([^\']+)\'', webpage, 'thumbnail', default=None),
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': int_or_none(self._search_regex(
                r'[^(]+\((\d+)\)', get_element_by_attribute('href', '#tab_comments', webpage), 'comment count', fatal=False)),
            'age_limit': 18,
            'creators': creators,
            'uploader': uploader,
            'uploader_url': uploader_url,
            'categories': categories,
            'tags': list(map(unescapeHTML, re.findall(
                r'<a class="tag_item"[^>]+\bhref="https://rule34video\.com/tags/\d+/"[^>]*>(?P<tag>[^>]*)</a>', webpage))),
        }, json_ld)

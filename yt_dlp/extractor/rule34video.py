import re

from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_element_by_id,
    get_element_html_by_class,
    get_elements_by_class,
    int_or_none,
    join_nonempty,
    parse_duration,
    remove_end,
    str_to_int,
    unescapeHTML,
)
from .common import InfoExtractor


class Rule34VideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/videos/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://rule34video.com/videos/3065157/shot-it-mmd-hmv/',
            'md5': 'ffccac2c23799dabbd192621ae4d04f3',
            'info_dict': {
                'id': '3065157',
                'ext': 'mp4',
                'title': 'Shot It-(mmd hmv)',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065157/preview.jpg',
                'duration': 347.0,
                'age_limit': 18,
                'like_count': int,
                'comment_count': int,
                'description': 'https://discord.gg/aBqPrHSHvv',
                'creator': None,
                'uploader': 'Sweet HMV',
                'uploader_url': 'https://rule34video.com/members/22119/',
                'categories': ['3D', 'MMD', 'iwara'],
                'tags': 'mincount:10'
            }
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
                'like_count': int,
                'comment_count': int,
                'description': None,
                'creator': 'WildeerStudio',
                'uploader': 'CerZule',
                'uploader_url': 'https://rule34video.com/members/36281/',
                'categories': ['3D', 'Tomb Raider'],
                'tags': 'mincount:40'
            }
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

        title = self._html_extract_title(webpage)
        thumbnail = self._html_search_regex(r'preview_url:\s+\'([^\']+)\'', webpage, 'thumbnail', default=None)
        duration = self._html_search_regex(r'"icon-clock"></i>\s+<span>((?:\d+:?)+)', webpage, 'duration', default=None)
        like_count = str_to_int(remove_end(get_element_by_class('voters count', webpage), ' likes'))
        comment_count = int_or_none(self._search_regex(r'[^(]+\((\d+)\)', get_element_by_attribute(
            'href', '#tab_comments', webpage), 'comment count', fatal=False))

        description = None
        video_info_element = get_element_by_id('tab_video_info', webpage)
        info_labels = get_elements_by_class('label', video_info_element)
        for label in info_labels:
            label_clean = label.strip(' \n\t')
            if label_clean.startswith('Description:'):
                description = clean_html(label_clean[len('Description:'):])
                break

        categories = None
        creator = None
        uploader, uploader_url = None, None
        for col in get_elements_by_class('col', webpage):
            label = clean_html(get_element_by_class('label', col))
            if label == 'Categories:':
                categories = list(map(clean_html, get_elements_by_class('item', col)))
            elif label == 'Artist:':
                creator = join_nonempty(*map(clean_html, get_elements_by_class('item', col)), delim=', ')
            elif label == 'Uploaded By:':
                uploader = clean_html(get_element_by_class('name', col))
                uploader_url = extract_attributes(get_element_html_by_class('name', col) or '').get('href')

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
            'duration': parse_duration(duration),
            'age_limit': 18,
            'like_count': like_count,
            'comment_count': comment_count,
            'description': description,
            'creator': creator,
            'uploader': uploader,
            'uploader_url': uploader_url,
            'categories': categories,
            'tags': list(map(unescapeHTML, re.findall(
                r'<a class="tag_item"[^>]+\bhref="https://rule34video\.com/tags/\d+/"[^>]*>(?P<tag>[^>]*)</a>', webpage))),
        }

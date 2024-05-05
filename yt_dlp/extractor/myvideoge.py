import re

from .common import InfoExtractor
from ..utils import (
    MONTH_NAMES,
    clean_html,
    get_element_by_class,
    get_element_by_id,
    int_or_none,
    js_to_json,
    qualities,
    unified_strdate,
)


class MyVideoGeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myvideo\.ge/v/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.myvideo.ge/v/3941048',
        'md5': '8c192a7d2b15454ba4f29dc9c9a52ea9',
        'info_dict': {
            'id': '3941048',
            'ext': 'mp4',
            'title': 'The best prikol',
            'upload_date': '20200611',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'chixa33',
            'description': 'md5:5b067801318e33c2e6eea4ab90b1fdd3',
        },
    }
    _MONTH_NAMES_KA = ['იანვარი', 'თებერვალი', 'მარტი', 'აპრილი', 'მაისი', 'ივნისი', 'ივლისი', 'აგვისტო', 'სექტემბერი', 'ოქტომბერი', 'ნოემბერი', 'დეკემბერი']

    _quality = staticmethod(qualities(('SD', 'HD')))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = (
            self._og_search_title(webpage, default=None)
            or clean_html(get_element_by_class('my_video_title', webpage))
            or self._html_search_regex(r'<title\b[^>]*>([^<]+)</title\b', webpage, 'title'))

        jwplayer_sources = self._parse_json(
            self._search_regex(
                r'''(?s)jwplayer\s*\(\s*['"]mvplayer['"]\s*\)\s*\.\s*setup\s*\(.*?\bsources\s*:\s*(\[.*?])\s*[,});]''', webpage, 'jwplayer sources', fatal=False)
            or '',
            video_id, transform_source=js_to_json, fatal=False)

        formats = self._parse_jwplayer_formats(jwplayer_sources or [], video_id)
        for f in formats or []:
            f['quality'] = self._quality(f['format_id'])

        description = (
            self._og_search_description(webpage)
            or get_element_by_id('long_desc_holder', webpage)
            or self._html_search_meta('description', webpage))

        uploader = self._search_regex(r'<a[^>]+class="mv_user_name"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False)

        upload_date = get_element_by_class('mv_vid_upl_date', webpage)
        # as ka locale may not be present roll a local date conversion
        upload_date = (unified_strdate(
            # translate any ka month to an en one
            re.sub('|'.join(self._MONTH_NAMES_KA),
                   lambda m: MONTH_NAMES['en'][self._MONTH_NAMES_KA.index(m.group(0))],
                   upload_date, flags=re.I))
            if upload_date else None)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'formats': formats,
            'thumbnail': self._og_search_thumbnail(webpage),
            'upload_date': upload_date,
            'view_count': int_or_none(get_element_by_class('mv_vid_views', webpage)),
            'like_count': int_or_none(get_element_by_id('likes_count', webpage)),
            'dislike_count': int_or_none(get_element_by_id('dislikes_count', webpage)),
        }

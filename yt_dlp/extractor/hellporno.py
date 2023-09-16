from .common import InfoExtractor
from ..utils import (
    int_or_none,
    merge_dicts,
    remove_end,
    unified_timestamp,
)


class HellPornoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hellporno\.(?:com/videos|net/v)/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'http://hellporno.com/videos/dixie-is-posing-with-naked-ass-very-erotic/',
        'md5': 'f0a46ebc0bed0c72ae8fe4629f7de5f3',
        'info_dict': {
            'id': '149116',
            'display_id': 'dixie-is-posing-with-naked-ass-very-erotic',
            'ext': 'mp4',
            'title': 'Dixie is posing with naked ass very erotic',
            'description': 'md5:9a72922749354edb1c4b6e540ad3d215',
            'categories': list,
            'thumbnail': r're:https?://.*\.jpg$',
            'duration': 240,
            'timestamp': 1398762720,
            'upload_date': '20140429',
            'view_count': int,
            'age_limit': 18,
        },
    }, {
        'url': 'http://hellporno.net/v/186271/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        title = remove_end(self._html_extract_title(webpage), ' - Hell Porno')

        info = self._parse_html5_media_entries(url, webpage, display_id)[0]

        video_id = self._search_regex(
            (r'chs_object\s*=\s*["\'](\d+)',
             r'params\[["\']video_id["\']\]\s*=\s*(\d+)'), webpage, 'video id',
            default=display_id)
        description = self._search_regex(
            r'class=["\']desc_video_view_v2[^>]+>([^<]+)', webpage,
            'description', fatal=False)
        categories = [
            c.strip()
            for c in self._html_search_meta(
                'keywords', webpage, 'categories', default='').split(',')
            if c.strip()]
        duration = int_or_none(self._og_search_property(
            'video:duration', webpage, fatal=False))
        timestamp = unified_timestamp(self._og_search_property(
            'video:release_date', webpage, fatal=False))
        view_count = int_or_none(self._search_regex(
            r'>Views\s+(\d+)', webpage, 'view count', fatal=False))

        return merge_dicts(info, {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'categories': categories,
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'age_limit': 18,
        })

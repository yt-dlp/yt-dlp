from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    clean_html,
    ExtractorError,
    traverse_obj,
    int_or_none,
)


class StarTVIE(InfoExtractor):
    _VALID_URL = r"""(?x)
        https?://(?:www\.)?startv\.com\.tr/
        (?:
            (?:dizi|program)/(?:[^/?#&]+)/(?:bolumler|fragmanlar|ekstralar)|
            video/arsiv/(?:dizi|program)/(?:[^/?#&]+)
        )/
        (?P<id>[^/?#&]+)
    """
    IE_NAME = 'startv'
    _TESTS = [
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/bolumler/3-bolum',
            'md5': '72381a32bcc2e2eb5841e8c8bf68f127',
            'info_dict': {
                'id': '904972',
                'display_id': '3-bolum',
                'ext': 'mp4',
                'title': '3. Bölüm',
                'description': 'md5:3a8049f05a75c2e8747116a673275de4',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*?)?$',
                'timestamp': 1569281400,
                'upload_date': '20190923'
            },
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/dizi/avlu/44-bolum',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/fragmanlar/5-bolum-fragmani',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/ekstralar/5-bolumun-nefes-kesen-final-sahnesi',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-haftasonu/bolumler/1-bolum',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-haftasonu/fragmanlar/2-fragman',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/program/buyukrisk/14-bolumde-hangi-unlu-ne-sordu-',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/program/buyukrisk/buyuk-risk-334-bolum',
            'only_matching': True
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/program/dada/dada-58-bolum',
            'only_matching': True
        }
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        info_url = self._search_regex(
            r'(["\'])videoUrl\1\s*:\s*\1(?P<url>(?:(?!\1).)+)\1\s*',
            webpage, 'video info url', group='url')

        info = traverse_obj(self._download_json(info_url, display_id), 'data', expected_type=dict)
        if not info:
            raise ExtractorError('Failed to extract API data')

        video_id = compat_str(info.get('id'))
        title = info.get('title') or self._og_search_title(webpage)
        description = clean_html(info.get('description')) or self._og_search_description(webpage, default=None)
        thumbnail = self._proto_relative_url(
            self._og_search_thumbnail(webpage), scheme='http:')

        formats = self._extract_m3u8_formats(
            traverse_obj(info, ('flavors', 'hls')), video_id, entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': int_or_none(info.get('release_date')),
            'formats': formats
        }

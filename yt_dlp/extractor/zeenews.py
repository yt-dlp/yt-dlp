from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class ZeeNewsIE(InfoExtractor):
    _WORKING = False
    _ENABLED = None  # XXX: pass through to GenericIE
    _VALID_URL = r'https?://zeenews\.india\.com/[^#?]+/video/(?P<display_id>[^#/?]+)/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://zeenews.india.com/hindi/india/delhi-ncr-haryana/delhi-ncr/video/greater-noida-video-viral-on-social-media-attackers-beat-businessman-and-his-son-oppose-market-closed-atdnh/1402138',
            'info_dict': {
                'id': '1402138',
                'ext': 'mp4',
                'title': 'Greater Noida Video: हमलावरों ने दिनदहाड़े दुकान में घुसकर की मारपीट, देखें वीडियो',
                'display_id': 'greater-noida-video-viral-on-social-media-attackers-beat-businessman-and-his-son-oppose-market-closed-atdnh',
                'upload_date': '20221019',
                'thumbnail': r're:^https?://.*\.jpg*',
                'timestamp': 1666174501,
                'view_count': int,
                'duration': 97,
                'description': 'ग्रेटर नोएडा जारचा थाना क्षेत्र के प्याबली में दिनदहाड़े दुकान में घुसकर अज्ञात हमलावरों ने हमला कर',
            }
        },
        {
            'url': 'https://zeenews.india.com/hindi/india/video/videsh-superfast-queen-elizabeth-iis-funeral-today/1357710',
            'info_dict': {
                'id': '1357710',
                'ext': 'mp4',
                'title': 'Videsh Superfast: महारानी के अंतिम संस्कार की तैयारी शुरू',
                'display_id': 'videsh-superfast-queen-elizabeth-iis-funeral-today',
                'upload_date': '20220919',
                'thumbnail': r're:^https?://.*\.jpg*',
                'timestamp': 1663556881,
                'view_count': int,
                'duration': 133,
                'description': 'सेगमेंट विदेश सुपराफास्ट में देखिए देश और दुनिया की सभी बड़ी खबरें, वो भी हर खबर फटाफट अंदाज में.',
            }
        }
    ]

    def _real_extract(self, url):
        content_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, content_id)
        json_ld_list = list(self._yield_json_ld(webpage, display_id))

        embed_url = traverse_obj(
            json_ld_list, (lambda _, v: v['@type'] == 'VideoObject', 'embedUrl'), get_all=False)
        if not embed_url:
            raise ExtractorError('No video found', expected=True)

        formats = self._extract_m3u8_formats(embed_url, content_id, 'mp4')

        return {
            **self._json_ld(json_ld_list, display_id),
            'id': content_id,
            'display_id': display_id,
            'formats': formats,
        }

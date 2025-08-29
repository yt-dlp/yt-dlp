from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    url_or_none,
)


class APAIE(InfoExtractor):
    _VALID_URL = r'(?P<base_url>https?://[^/]+\.apa\.at)/embed/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//[^/]+\.apa\.at/embed/[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}.*?)\1']
    _TESTS = [{
        'url': 'http://uvp.apa.at/embed/293f6d17-692a-44e3-9fd5-7b178f3a1029',
        'info_dict': {
            'id': '293f6d17-692a-44e3-9fd5-7b178f3a1029',
            'ext': 'mp4',
            'title': '293f6d17-692a-44e3-9fd5-7b178f3a1029',
            'thumbnail': r're:https?://kf-vn\.sf\.apa\.at/vn/.+\.jpg',
        },
    }, {
        'url': 'https://uvp-apapublisher.sf.apa.at/embed/2f94e9e6-d945-4db2-9548-f9a41ebf7b78',
        'only_matching': True,
    }, {
        'url': 'http://uvp-rma.sf.apa.at/embed/70404cca-2f47-4855-bbb8-20b1fae58f76',
        'only_matching': True,
    }, {
        'url': 'http://uvp-kleinezeitung.sf.apa.at/embed/f1c44979-dba2-4ebf-b021-e4cf2cac3c81',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.vol.at/blue-man-group/5593454',
        'info_dict': {
            'id': '293f6d17-692a-44e3-9fd5-7b178f3a1029',
            'ext': 'mp4',
            'title': '293f6d17-692a-44e3-9fd5-7b178f3a1029',
            'thumbnail': r're:https?://kf-vn\.sf\.apa\.at/vn/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id, base_url = mobj.group('id', 'base_url')

        webpage = self._download_webpage(
            f'{base_url}/player/{video_id}', video_id)

        jwplatform_id = self._search_regex(
            r'media[iI]d\s*:\s*["\'](?P<id>[a-zA-Z0-9]{8})', webpage,
            'jwplatform id', default=None)

        if jwplatform_id:
            return self.url_result(
                'jwplatform:' + jwplatform_id, ie='JWPlatform',
                video_id=video_id)

        def extract(field, name=None):
            return self._search_regex(
                rf'\b{field}["\']\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, name or field, default=None, group='value')

        title = extract('title') or video_id
        description = extract('description')
        thumbnail = extract('poster', 'thumbnail')

        formats = []
        for format_id in ('hls', 'progressive'):
            source_url = url_or_none(extract(format_id))
            if not source_url:
                continue
            ext = determine_ext(source_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    source_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                height = int_or_none(self._search_regex(
                    r'(\d+)\.mp4', source_url, 'height', default=None))
                formats.append({
                    'url': source_url,
                    'format_id': format_id,
                    'height': height,
                })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }

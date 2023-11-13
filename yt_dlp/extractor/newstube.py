import base64
import hashlib

from .common import InfoExtractor
from ..aes import aes_cbc_decrypt_bytes, unpad_pkcs7
from ..utils import (
    int_or_none,
    parse_codecs,
    parse_duration,
)


class NewstubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?newstube\.ru/media/(?P<id>.+)'
    _TEST = {
        'url': 'http://www.newstube.ru/media/telekanal-cnn-peremestil-gorod-slavyansk-v-krym',
        'md5': '9d10320ad473444352f72f746ccb8b8c',
        'info_dict': {
            'id': '728e0ef2-e187-4012-bac0-5a081fdcb1f6',
            'ext': 'mp4',
            'title': 'Телеканал CNN переместил город Славянск в Крым',
            'description': 'md5:419a8c9f03442bc0b0a794d689360335',
            'duration': 31.05,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        page = self._download_webpage(url, video_id)
        title = self._html_search_meta(['og:title', 'twitter:title'], page, fatal=True)

        video_guid = self._html_search_regex(
            r'<meta\s+property="og:video(?::(?:(?:secure_)?url|iframe))?"\s+content="https?://(?:www\.)?newstube\.ru/embed/(?P<guid>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})',
            page, 'video GUID')

        enc_data = base64.b64decode(self._download_webpage(
            'https://www.newstube.ru/embed/api/player/getsources2',
            video_guid, query={
                'guid': video_guid,
                'ff': 3,
            }))
        key = hashlib.pbkdf2_hmac(
            'sha1', video_guid.replace('-', '').encode(), enc_data[:16], 1)[:16]
        dec_data = unpad_pkcs7(aes_cbc_decrypt_bytes(enc_data[32:], key, enc_data[16:32]))
        sources = self._parse_json(dec_data, video_guid)

        formats = []
        for source in sources:
            source_url = source.get('Src')
            if not source_url:
                continue
            height = int_or_none(source.get('Height'))
            f = {
                'format_id': 'http' + ('-%dp' % height if height else ''),
                'url': source_url,
                'width': int_or_none(source.get('Width')),
                'height': height,
            }
            source_type = source.get('Type')
            if source_type:
                f.update(parse_codecs(self._search_regex(
                    r'codecs="([^"]+)"', source_type, 'codecs', fatal=False)))
            formats.append(f)

        self._check_formats(formats, video_guid)

        return {
            'id': video_guid,
            'title': title,
            'description': self._html_search_meta(['description', 'og:description'], page),
            'thumbnail': self._html_search_meta(['og:image:secure_url', 'og:image', 'twitter:image'], page),
            'duration': parse_duration(self._html_search_meta('duration', page)),
            'formats': formats,
        }

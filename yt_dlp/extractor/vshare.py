from .common import InfoExtractor
from ..utils import ExtractorError, decode_packed_codes


class VShareIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vshare\.io/[dv]/(?P<id>[^/?#&]+)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=["\'](?P<url>(?:https?:)?//(?:www\.)?vshare\.io/v/[^/?#&]+)']
    _TESTS = [{
        'url': 'https://vshare.io/d/0f64ce6',
        'md5': '17b39f55b5497ae8b59f5fbce8e35886',
        'info_dict': {
            'id': '0f64ce6',
            'title': 'vl14062007715967',
            'ext': 'mp4',
        }
    }, {
        'url': 'https://vshare.io/v/0f64ce6/width-650/height-430/1',
        'only_matching': True,
    }]

    def _extract_packed(self, webpage):
        packed = self._search_regex(
            r'(eval\(function.+)', webpage, 'packed code')
        unpacked = decode_packed_codes(packed)
        digits = self._search_regex(r'\[([\d,]+)\]', unpacked, 'digits')
        digits = [int(digit) for digit in digits.split(',')]
        key_digit = self._search_regex(
            r'fromCharCode\(.+?(\d+)\)}', unpacked, 'key digit')
        chars = [chr(d - int(key_digit)) for d in digits]
        return ''.join(chars)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://vshare.io/v/%s/width-650/height-430/1' % video_id,
            video_id, headers={'Referer': url})

        title = self._html_extract_title(webpage)
        title = title.split(' - ')[0]

        error = self._html_search_regex(
            r'(?s)<div[^>]+\bclass=["\']xxx-error[^>]+>(.+?)</div', webpage,
            'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)

        info = self._parse_html5_media_entries(
            url, '<video>%s</video>' % self._extract_packed(webpage),
            video_id)[0]

        info.update({
            'id': video_id,
            'title': title,
        })

        return info

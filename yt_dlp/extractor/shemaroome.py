import base64

from .common import InfoExtractor
from ..aes import aes_cbc_decrypt_bytes, unpad_pkcs7
from ..utils import (
    ExtractorError,
    unified_strdate,
)


class ShemarooMeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?shemaroome\.com/(?:movies|shows)/(?P<id>[^?#]+)'
    _TESTS = [{
        'url': 'https://www.shemaroome.com/movies/dil-hai-tumhaara',
        'info_dict': {
            'id': 'dil-hai-tumhaara',
            'ext': 'mp4',
            'title': 'Dil Hai Tumhaara',
            'release_date': '20020906',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:2782c4127807103cf5a6ae2ca33645ce',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.shemaroome.com/shows/jurm-aur-jazbaat/laalach',
        'info_dict': {
            'id': 'jurm-aur-jazbaat_laalach',
            'ext': 'mp4',
            'title': 'Laalach',
            'description': 'md5:92b79c2dcb539b0ab53f9fa5a048f53c',
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_date': '20210507',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Premium videos cannot be downloaded yet.',
    }, {
        'url': 'https://www.shemaroome.com/shows/jai-jai-jai-bajrang-bali/jai-jai-jai-bajrang-bali-episode-99',
        'info_dict': {
            'id': 'jai-jai-jai-bajrang-bali_jai-jai-jai-bajrang-bali-episode-99',
            'ext': 'mp4',
            'title': 'Jai Jai Jai Bajrang Bali Episode 99',
            'description': 'md5:850d127a18ee3f9529d7fbde2f49910d',
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_date': '20110101',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).replace('/', '_')
        webpage = self._download_webpage(url, video_id)
        title = self._search_regex(r'id=\"ma_title\" value=\"([^\"]+)', webpage, 'title')
        thumbnail = self._og_search_thumbnail(webpage)
        content_def = self._search_regex(r'id=\"content_definition\" value=\"([^\"]+)', webpage, 'content_def')
        catalog_id = self._search_regex(r'id=\"catalog_id\" value=\"([^\"]+)', webpage, 'catalog_id')
        item_category = self._search_regex(r'id=\"item_category\" value=\"([^\"]+)', webpage, 'item_category')
        content_id = self._search_regex(r'id=\"content_id\" value=\"([^\"]+)', webpage, 'content_id')

        data = f'catalog_id={catalog_id}&content_id={content_id}&category={item_category}&content_def={content_def}'
        data_json = self._download_json('https://www.shemaroome.com/users/user_all_lists', video_id, data=data.encode())
        if not data_json.get('status'):
            raise ExtractorError('Premium videos cannot be downloaded yet.', expected=True)
        url_data = base64.b64decode(data_json['new_play_url'])
        key = base64.b64decode(data_json['key'])
        iv = bytes(16)
        m3u8_url = unpad_pkcs7(aes_cbc_decrypt_bytes(url_data, key, iv)).decode('ascii')
        headers = {'stream_key': data_json['stream_key']}
        formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, fatal=False, headers=headers)
        for fmt in formats:
            fmt['http_headers'] = headers

        release_date = self._html_search_regex(
            (r'itemprop="uploadDate">\s*([\d-]+)', r'id="release_date" value="([\d-]+)'),
            webpage, 'release date', fatal=False)

        subtitles = {}
        sub_url = data_json.get('subtitle')
        if sub_url:
            subtitles.setdefault('EN', []).append({
                'url': self._proto_relative_url(sub_url),
            })
        subtitles = self._merge_subtitles(subtitles, m3u8_subs)
        description = self._html_search_regex(r'(?s)>Synopsis(</.+?)</', webpage, 'description', fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
            'release_date': unified_strdate(release_date),
            'description': description,
            'subtitles': subtitles,
        }

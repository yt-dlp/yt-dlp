# coding: utf-8
from __future__ import unicode_literals

import random
import re
import string

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    mimetype2ext,
    parse_codecs,
    update_url_query,
    xpath_element,
    xpath_text,
)
from ..compat import (
    compat_b64decode,
    compat_ord,
    compat_struct_pack,
)


class VideaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        videa(?:kid)?\.hu/
                        (?:
                            videok/(?:[^/]+/)*[^?#&]+-|
                            (?:videojs_)?player\?.*?\bv=|
                            player/v/
                        )
                        (?P<id>[^?#&]+)
                    '''
    _TESTS = [{
        'url': 'http://videa.hu/videok/allatok/az-orult-kigyasz-285-kigyot-kigyo-8YfIAjxwWGwT8HVQ',
        'md5': '97a7af41faeaffd9f1fc864a7c7e7603',
        'info_dict': {
            'id': '8YfIAjxwWGwT8HVQ',
            'ext': 'mp4',
            'title': 'Az őrült kígyász 285 kígyót enged szabadon',
            'thumbnail': r're:^https?://.*',
            'duration': 21,
        },
    }, {
        'url': 'http://videa.hu/videok/origo/jarmuvek/supercars-elozes-jAHDWfWSJH5XuFhH',
        'only_matching': True,
    }, {
        'url': 'http://videa.hu/player?v=8YfIAjxwWGwT8HVQ',
        'only_matching': True,
    }, {
        'url': 'http://videa.hu/player/v/8YfIAjxwWGwT8HVQ?autoplay=1',
        'only_matching': True,
    }, {
        'url': 'https://videakid.hu/videok/origo/jarmuvek/supercars-elozes-jAHDWfWSJH5XuFhH',
        'only_matching': True,
    }, {
        'url': 'https://videakid.hu/player?v=8YfIAjxwWGwT8HVQ',
        'only_matching': True,
    }, {
        'url': 'https://videakid.hu/player/v/8YfIAjxwWGwT8HVQ?autoplay=1',
        'only_matching': True,
    }]
    _STATIC_SECRET = 'xHb0ZvME5q8CBcoQi6AngerDu3FGO9fkUlwPmLVY_RTzj2hJIS4NasXWKy1td7p'

    @staticmethod
    def _extract_urls(webpage):
        return [url for _, url in re.findall(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//videa\.hu/player\?.*?\bv=.+?)\1',
            webpage)]

    @staticmethod
    def rc4(cipher_text, key):
        res = b''

        key_len = len(key)
        S = list(range(256))

        j = 0
        for i in range(256):
            j = (j + S[i] + ord(key[i % key_len])) % 256
            S[i], S[j] = S[j], S[i]

        i = 0
        j = 0
        for m in range(len(cipher_text)):
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            k = S[(S[i] + S[j]) % 256]
            res += compat_struct_pack('B', k ^ compat_ord(cipher_text[m]))

        return res.decode()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        query = {'v': video_id}
        player_page = self._download_webpage(
            'https://videa.hu/player', video_id, query=query)

        nonce = self._search_regex(
            r'_xt\s*=\s*"([^"]+)"', player_page, 'nonce')
        l = nonce[:32]
        s = nonce[32:]
        result = ''
        for i in range(0, 32):
            result += s[i - (self._STATIC_SECRET.index(l[i]) - 31)]

        random_seed = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        query['_s'] = random_seed
        query['_t'] = result[:16]

        b64_info, handle = self._download_webpage_handle(
            'http://videa.hu/videaplayer_get_xml.php', video_id, query=query)
        if b64_info.startswith('<?xml'):
            info = self._parse_xml(b64_info, video_id)
        else:
            key = result[16:] + random_seed + handle.headers['x-videa-xs']
            info = self._parse_xml(self.rc4(
                compat_b64decode(b64_info), key), video_id)

        video = xpath_element(info, './video', 'video')
        if not video:
            raise ExtractorError(xpath_element(
                info, './error', fatal=True), expected=True)
        sources = xpath_element(
            info, './video_sources', 'sources', fatal=True)
        hash_values = xpath_element(
            info, './hash_values', 'hash values', fatal=True)

        title = xpath_text(video, './title', fatal=True)

        formats = []
        for source in sources.findall('./video_source'):
            source_url = source.text
            source_name = source.get('name')
            source_exp = source.get('exp')
            if not (source_url and source_name and source_exp):
                continue
            hash_value = xpath_text(hash_values, 'hash_value_' + source_name)
            if not hash_value:
                continue
            source_url = update_url_query(source_url, {
                'md5': hash_value,
                'expires': source_exp,
            })
            f = parse_codecs(source.get('codecs'))
            f.update({
                'url': self._proto_relative_url(source_url),
                'ext': mimetype2ext(source.get('mimetype')) or 'mp4',
                'format_id': source.get('name'),
                'width': int_or_none(source.get('width')),
                'height': int_or_none(source.get('height')),
            })
            formats.append(f)
        self._sort_formats(formats)

        thumbnail = self._proto_relative_url(xpath_text(video, './poster_src'))

        age_limit = None
        is_adult = xpath_text(video, './is_adult_content', default=None)
        if is_adult:
            age_limit = 18 if is_adult == '1' else 0

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': int_or_none(xpath_text(video, './duration')),
            'age_limit': age_limit,
            'formats': formats,
        }

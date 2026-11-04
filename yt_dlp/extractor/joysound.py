import base64
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    encode_data_uri,
    multipart_encode,
    urlencode_postdata,
)
from ..utils.traversal import require, traverse_obj


class JoySoundCafeIE(InfoExtractor):
    IE_NAME = 'joysound:cafe'
    IE_DESC = 'ジョイサウンドカフェ'

    _BASE_URL = 'https://www.sound-cafe.jp/player'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['JP']
    _VALID_URL = r'https?://www\.sound-cafe\.jp/songdetail/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.sound-cafe.jp/songdetail/424782',
        'info_dict': {
            'id': '424782',
            'ext': 'ogg',
            'title': 'Sincerely',
            'artists': ['TRUE'],
            'composers': 'count:1',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.sound-cafe.jp/songdetail/612007',
        'info_dict': {
            'id': '612007',
            'ext': 'ogg',
            'title': 'Celestial',
            'artists': ['Ed Sheeran'],
            'composers': 'count:3',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.sound-cafe.jp/songdetail/177905',
        'info_dict': {
            'id': '177905',
            'ext': 'ogg',
            'title': '深愛',
            'artists': ['水樹奈々'],
            'composers': 'count:1',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id)
        hidden_inputs = self._hidden_inputs(webpage)
        song_number = traverse_obj(hidden_inputs, ('selSongNo', {str}))
        x_csrf_token = self._html_search_meta('_csrf', webpage, fatal=True)

        telop_info = self._download_json(
            f'{self._BASE_URL}/telopTitleInfo', audio_id, headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Csrf-Token': x_csrf_token,
                'X-Requested-With': 'XMLHttpRequest',
            }, data=urlencode_postdata({'songNumber': song_number}))

        formats = []
        for guide in re.finditer(
            r'<input\b[^>]+\btype=(["\'])radio\1[^>]+\bid=(["\'])(?P<id>\w+)\2[^>]+value=(["\'])(?P<value>\d+)\4', webpage,
        ):
            format_id = guide.group('id')
            data, content_type = multipart_encode({
                'serviceType': guide.group('value'),
                'songNumber': song_number,
            })
            fme = self._download_json(
                f'{self._BASE_URL}/getFME', audio_id, headers={
                    'Accept': 'application/json',
                    'Content-Type': content_type,
                    'X-Csrf-Token': x_csrf_token,
                }, data=data)

            ogg = traverse_obj(fme, ('ogg', {str}, {require('Ogg Vorbis binary')}))
            ogg_bytes = base64.b64decode(ogg[30:] + ogg[:30])

            formats.append({
                'acodec': 'vorbis',
                'ext': 'ogg',
                'filesize': len(ogg_bytes),
                'format_id': format_id,
                'source_preference': -10 if format_id == 'vocal' else None,
                'url': encode_data_uri(ogg_bytes, 'audio/ogg'),
                'vcodec': 'none',
            })

        return {
            'id': song_number,
            'composers': traverse_obj(telop_info, (
                'composer', {clean_html}, {re.compile(r'[，&]').split},
                ..., {str.strip}, filter, all, filter)),
            'display_id': audio_id,
            'formats': formats,
            '_format_sort_fields': ('source_preference', ),
            **traverse_obj(hidden_inputs, {
                'title': ('songName', {clean_html}, filter),
                'artists': ('artistName', {clean_html}, filter, all, filter),
            }),
        }

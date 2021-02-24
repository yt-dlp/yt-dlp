# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    compat_str,
    int_or_none,
    parse_iso8601,
)


class LnkGoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lnk(?:go)?\.(?:alfa\.)?lt/(?:visi-video/[^/]+|video)/(?P<id>[A-Za-z0-9-]+)(?:/(?P<episode_id>\d+))?'
    _TESTS = [{
        'url': 'http://www.lnkgo.lt/visi-video/aktualai-pratesimas/ziurek-putka-trys-klausimai',
        'info_dict': {
            'id': '10809',
            'ext': 'mp4',
            'title': "Put'ka: Trys Klausimai",
            'upload_date': '20161216',
            'description': 'Seniai matytas Put’ka užduoda tris klausimėlius. Pabandykime surasti atsakymus.',
            'age_limit': 18,
            'duration': 117,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1481904000,
        },
        'params': {
            'skip_download': True,  # HLS download
        },
    }, {
        'url': 'http://lnkgo.alfa.lt/visi-video/aktualai-pratesimas/ziurek-nerdas-taiso-kompiuteri-2',
        'info_dict': {
            'id': '10467',
            'ext': 'mp4',
            'title': 'Nėrdas: Kompiuterio Valymas',
            'upload_date': '20150113',
            'description': 'md5:7352d113a242a808676ff17e69db6a69',
            'age_limit': 18,
            'duration': 346,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1421164800,
        },
        'params': {
            'skip_download': True,  # HLS download
        },
    }, {
        'url': 'https://lnk.lt/video/neigalieji-tv-bokste/37413',
        'only_matching': True,
    }]
    _AGE_LIMITS = {
        'N-7': 7,
        'N-14': 14,
        'S': 18,
    }
    _M3U8_TEMPL = 'https://vod.lnk.lt/lnk_vod/lnk/lnk/%s:%s/playlist.m3u8%s'

    def _real_extract(self, url):
        display_id, video_id = re.match(self._VALID_URL, url).groups()

        video_info = self._download_json(
            'https://lnk.lt/api/main/video-page/%s/%s/false' % (display_id, video_id or '0'),
            display_id)['videoConfig']['videoInfo']

        video_id = compat_str(video_info['id'])
        title = video_info['title']
        prefix = 'smil' if video_info.get('isQualityChangeAvailable') else 'mp4'
        formats = self._extract_m3u8_formats(
            self._M3U8_TEMPL % (prefix, video_info['videoUrl'], video_info.get('secureTokenParams') or ''),
            video_id, 'mp4', 'm3u8_native')
        self._sort_formats(formats)

        poster_image = video_info.get('posterImage')

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'thumbnail': 'https://lnk.lt/all-images/' + poster_image if poster_image else None,
            'duration': int_or_none(video_info.get('duration')),
            'description': clean_html(video_info.get('htmlDescription')),
            'age_limit': self._AGE_LIMITS.get(video_info.get('pgRating'), 0),
            'timestamp': parse_iso8601(video_info.get('airDate')),
            'view_count': int_or_none(video_info.get('viewsCount')),
        }

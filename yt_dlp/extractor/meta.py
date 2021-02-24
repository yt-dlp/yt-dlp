# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .pladform import PladformIE
from ..utils import (
    unescapeHTML,
    int_or_none,
    ExtractorError,
)


class METAIE(InfoExtractor):
    _VALID_URL = r'https?://video\.meta\.ua/(?:iframe/)?(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://video.meta.ua/5502115.video',
        'md5': '71b6f3ee274bef16f1ab410f7f56b476',
        'info_dict': {
            'id': '5502115',
            'ext': 'mp4',
            'title': 'Sony Xperia Z camera test [HQ]',
            'description': 'Xperia Z shoots video in FullHD HDR.',
            'uploader_id': 'nomobile',
            'uploader': 'CHЁZA.TV',
            'upload_date': '20130211',
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'http://video.meta.ua/iframe/5502115',
        'only_matching': True,
    }, {
        # pladform embed
        'url': 'http://video.meta.ua/7121015.video',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        st_html5 = self._search_regex(
            r"st_html5\s*=\s*'#([^']+)'", webpage, 'uppod html5 st', default=None)

        if st_html5:
            # uppod st decryption algorithm is reverse engineered from function un(s) at uppod.js
            json_str = ''
            for i in range(0, len(st_html5), 3):
                json_str += '&#x0%s;' % st_html5[i:i + 3]
            uppod_data = self._parse_json(unescapeHTML(json_str), video_id)
            error = uppod_data.get('customnotfound')
            if error:
                raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)

            video_url = uppod_data['file']
            info = {
                'id': video_id,
                'url': video_url,
                'title': uppod_data.get('comment') or self._og_search_title(webpage),
                'description': self._og_search_description(webpage, default=None),
                'thumbnail': uppod_data.get('poster') or self._og_search_thumbnail(webpage),
                'duration': int_or_none(self._og_search_property(
                    'video:duration', webpage, default=None)),
            }
            if 'youtube.com/' in video_url:
                info.update({
                    '_type': 'url_transparent',
                    'ie_key': 'Youtube',
                })
            return info

        pladform_url = PladformIE._extract_url(webpage)
        if pladform_url:
            return self.url_result(pladform_url)

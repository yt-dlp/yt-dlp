# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor


class DBTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dagbladet\.no/video/(?:(?:embed|(?P<display_id>[^/]+))/)?(?P<id>[0-9A-Za-z_-]{11}|[a-zA-Z0-9]{8})'
    _TESTS = [{
        'url': 'https://www.dagbladet.no/video/PynxJnNWChE/',
        'md5': 'b8f850ba1860adbda668d367f9b77699',
        'info_dict': {
            'id': 'PynxJnNWChE',
            'ext': 'mp4',
            'title': 'Skulle teste ut fornøyelsespark, men kollegaen var bare opptatt av bikinikroppen',
            'description': 'md5:49cc8370e7d66e8a2ef15c3b4631fd3f',
            'thumbnail': r're:https?://.*\.jpg',
            'upload_date': '20160916',
            'duration': 69,
            'uploader_id': 'UCk5pvsyZJoYJBd7_oFPTlRQ',
            'uploader': 'Dagbladet',
        },
        'add_ie': ['Youtube']
    }, {
        'url': 'https://www.dagbladet.no/video/embed/xlGmyIeN9Jo/?autoplay=false',
        'only_matching': True,
    }, {
        'url': 'https://www.dagbladet.no/video/truer-iran-bor-passe-dere/PalfB2Cw',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [url for _, url in re.findall(
            r'<iframe[^>]+src=(["\'])((?:https?:)?//(?:www\.)?dagbladet\.no/video/embed/(?:[0-9A-Za-z_-]{11}|[a-zA-Z0-9]{8}).*?)\1',
            webpage)]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()
        info = {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
        }
        if len(video_id) == 11:
            info.update({
                'url': video_id,
                'ie_key': 'Youtube',
            })
        else:
            info.update({
                'url': 'jwplatform:' + video_id,
                'ie_key': 'JWPlatform',
            })
        return info

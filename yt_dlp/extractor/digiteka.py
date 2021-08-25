# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import int_or_none


class DigitekaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?(?:digiteka\.net|ultimedia\.com)/
        (?:
            deliver/
            (?P<embed_type>
                generic|
                musique
            )
            (?:/[^/]+)*/
            (?:
                src|
                article
            )|
            default/index/video
            (?P<site_type>
                generic|
                music
            )
            /id
        )/(?P<id>[\d+a-z]+)'''
    _TESTS = [{
        # news
        'url': 'https://www.ultimedia.com/default/index/videogeneric/id/s8uk0r',
        'md5': '276a0e49de58c7e85d32b057837952a2',
        'info_dict': {
            'id': 's8uk0r',
            'ext': 'mp4',
            'title': 'Loi sur la fin de vie: le texte prévoit un renforcement des directives anticipées',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 74,
            'upload_date': '20150317',
            'timestamp': 1426604939,
            'uploader_id': '3fszv',
        },
    }, {
        # music
        'url': 'https://www.ultimedia.com/default/index/videomusic/id/xvpfp8',
        'md5': '2ea3513813cf230605c7e2ffe7eca61c',
        'info_dict': {
            'id': 'xvpfp8',
            'ext': 'mp4',
            'title': 'Two - C\'est La Vie (clip)',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 233,
            'upload_date': '20150224',
            'timestamp': 1424760500,
            'uploader_id': '3rfzk',
        },
    }, {
        'url': 'https://www.digiteka.net/deliver/generic/iframe/mdtk/01637594/src/lqm3kl/zone/1/showtitle/1/autoplay/yes',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<(?:iframe|script)[^>]+src=["\'](?P<url>(?:https?:)?//(?:www\.)?ultimedia\.com/deliver/(?:generic|musique)(?:/[^/]+)*/(?:src|article)/[\d+a-z]+)',
            webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        video_type = mobj.group('embed_type') or mobj.group('site_type')
        if video_type == 'music':
            video_type = 'musique'

        deliver_info = self._download_json(
            'http://www.ultimedia.com/deliver/video?video=%s&topic=%s' % (video_id, video_type),
            video_id)

        yt_id = deliver_info.get('yt_id')
        if yt_id:
            return self.url_result(yt_id, 'Youtube')

        jwconf = deliver_info['jwconf']

        formats = []
        for source in jwconf['playlist'][0]['sources']:
            formats.append({
                'url': source['file'],
                'format_id': source.get('label'),
            })

        self._sort_formats(formats)

        title = deliver_info['title']
        thumbnail = jwconf.get('image')
        duration = int_or_none(deliver_info.get('duration'))
        timestamp = int_or_none(deliver_info.get('release_time'))
        uploader_id = deliver_info.get('owner_id')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'formats': formats,
        }

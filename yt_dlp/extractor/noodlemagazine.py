# coding: utf-8
from __future__ import unicode_literals

from ..utils import traverse_obj
from .common import InfoExtractor


class NoodleMagazineIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|adult\.)?noodlemagazine\.com/watch/(?P<id>[0-9-_]+)'
    _TEST = {
        'url': 'https://adult.noodlemagazine.com/watch/-67421364_456239604',
        'md5': '9e02aa763612929d0b4b850591a9248b',
        'info_dict': {
            'id': '-67421364_456239604',
            'title': 'Aria alexander manojob',
            'thumbnail': r're:^https://.*\.jpg\?(?=.*size=\d+x\d+)(?=.*quality=\d+)(?=.*sign=[0-9a-zA-Z]+)',
            'ext': 'mp4',
            'formats': [
                {
                    'url': r're:^https://.*\.pvvstream.pro/.*extra=',
                    'quality': '240',
                    'ext': 'mp4',
                },
                {
                    'url': r're:^https://.*\.pvvstream.pro/.*extra=',
                    'quality': '360',
                    'ext': 'mp4',
                },
                {
                    'url': r're:^https://.*\.pvvstream.pro/.*extra=',
                    'quality': '480',
                    'ext': 'mp4',
                },
                {
                    'url': r're:^https://.*\.pvvstream.pro/.*extra=',
                    'quality': '720',
                    'ext': 'mp4',
                },
            ]
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage)

        # fetch json
        m = self._html_search_regex(r'/' + video_id + r'\?(?:.*&)?m=([^&"\'\s,]+)', webpage, 'm')
        playlist = 'https://adult.noodlemagazine.com/playlist/%s?m=%s' % (video_id, m)
        info = self._download_json(playlist, video_id)
        thumbnail = info.get('image')

        formats = []

        for mobj in info.get('sources'):
            formats.append({
                'url': traverse_obj(mobj, 'file'),
                'quality': traverse_obj(mobj, 'label'),
                'ext': traverse_obj(mobj, 'type'),
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
        }

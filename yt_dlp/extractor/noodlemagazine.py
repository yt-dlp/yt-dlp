# coding: utf-8
from __future__ import unicode_literals

from ..utils import (
    traverse_obj,
    str_to_int,
    str_or_none
)
from .common import InfoExtractor


class NoodleMagazineIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|adult\.)?noodlemagazine\.com/watch/(?P<id>[0-9-_]+)'
    _TEST = {
        'url': 'https://adult.noodlemagazine.com/watch/-67421364_456239604',
        'md5': '9e02aa763612929d0b4b850591a9248b',
        'info_dict': {
            'id': '-67421364_456239604',
            'title': 'Aria alexander manojob',
            'thumbnail': r're:^https://.*\.jpg',
            'ext': 'mp4',
            'duration': 903,
            'view_count': int,
            'like_count': int,
            'description': 'Aria alexander manojob',
            'tags': ['aria', 'alexander', 'manojob'],
            'upload_update': '20190218',
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
        duration = str_to_int(self._html_search_meta('video:duration', webpage, 'duration', default=None))
        description = self._og_search_property('description', webpage, default='').replace(' watch online hight quality video', '')
        tags = self._html_search_meta('video:tag', webpage, default='').split(', ')
        view_count = str_to_int(self._html_search_meta('ya:ovs:views_total', webpage, default=None))
        like_count = str_to_int(self._html_search_meta('ya:ovs:likes', webpage, default=None))
        upload_update = str_or_none(self._html_search_meta('ya:ovs:upload_date', webpage, default='').replace('-', ''))

        # fetch json
        m = self._html_search_regex(r'/' + video_id + r'\?(?:.*&)?m=([^&"\'\s,]+)', webpage, 'm')
        playlist = 'https://adult.noodlemagazine.com/playlist/%s?m=%s' % (video_id, m)
        info = self._download_json(playlist, video_id)
        thumbnail = self._og_search_property('image', webpage, default=None) or info.get('image')

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
            'duration': duration,
            'description': description,
            'tags': tags,
            'view_count': view_count,
            'like_count': like_count,
            'upload_update': upload_update
        }

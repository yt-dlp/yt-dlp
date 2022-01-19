# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from .nexx import NexxIE
from ..utils import (
    int_or_none,
    str_or_none,
)


class FunkIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|origin\.)?funk\.net/(?:channel|playlist)/[^/]+/(?P<display_id>[0-9a-z-]+)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.funk.net/channel/ba-793/die-lustigsten-instrumente-aus-dem-internet-teil-2-1155821',
        'md5': '8dd9d9ab59b4aa4173b3197f2ea48e81',
        'info_dict': {
            'id': '1155821',
            'ext': 'mp4',
            'title': 'Die LUSTIGSTEN INSTRUMENTE aus dem Internet - Teil 2',
            'description': 'md5:a691d0413ef4835588c5b03ded670c1f',
            'timestamp': 1514507395,
            'upload_date': '20171229',
        },

    }, {
        'url': 'https://www.funk.net/playlist/neuesteVideos/kameras-auf-dem-fusion-festival-1618699',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id, nexx_id = self._match_valid_url(url).groups()
        video = self._download_json(
            'https://www.funk.net/api/v4.0/videos/' + nexx_id, nexx_id)
        return {
            '_type': 'url_transparent',
            'url': 'nexx:741:' + nexx_id,
            'ie_key': NexxIE.ie_key(),
            'id': nexx_id,
            'title': video.get('title'),
            'description': video.get('description'),
            'duration': int_or_none(video.get('duration')),
            'channel_id': str_or_none(video.get('channelId')),
            'display_id': display_id,
            'tags': video.get('tags'),
            'thumbnail': video.get('imageUrlLandscape'),
        }

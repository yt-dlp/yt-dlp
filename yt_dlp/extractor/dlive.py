import json

from .common import InfoExtractor
from ..utils import int_or_none


class DLiveVODIE(InfoExtractor):
    IE_NAME = 'dlive:vod'
    _VALID_URL = r'https?://(?:www\.)?dlive\.tv/p/(?P<uploader_id>.+?)\+(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://dlive.tv/p/pdp+3mTzOl4WR',
        'info_dict': {
            'id': '3mTzOl4WR',
            'ext': 'mp4',
            'title': 'Minecraft with james charles epic',
            'upload_date': '20190701',
            'timestamp': 1562011015,
            'uploader_id': 'pdp',
        }
    }, {
        'url': 'https://dlive.tv/p/pdpreplay+D-RD-xSZg',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        uploader_id, vod_id = self._match_valid_url(url).groups()
        broadcast = self._download_json(
            'https://graphigo.prd.dlive.tv/', vod_id,
            data=json.dumps({'query': '''query {
  pastBroadcast(permlink:"%s+%s") {
    content
    createdAt
    length
    playbackUrl
    title
    thumbnailUrl
    viewCount
  }
}''' % (uploader_id, vod_id)}).encode())['data']['pastBroadcast']
        title = broadcast['title']
        formats = self._extract_m3u8_formats(
            broadcast['playbackUrl'], vod_id, 'mp4', 'm3u8_native')
        return {
            'id': vod_id,
            'title': title,
            'uploader_id': uploader_id,
            'formats': formats,
            'description': broadcast.get('content'),
            'thumbnail': broadcast.get('thumbnailUrl'),
            'timestamp': int_or_none(broadcast.get('createdAt'), 1000),
            'view_count': int_or_none(broadcast.get('viewCount')),
        }


class DLiveStreamIE(InfoExtractor):
    IE_NAME = 'dlive:stream'
    _VALID_URL = r'https?://(?:www\.)?dlive\.tv/(?!p/)(?P<id>[\w.-]+)'

    def _real_extract(self, url):
        display_name = self._match_id(url)
        user = self._download_json(
            'https://graphigo.prd.dlive.tv/', display_name,
            data=json.dumps({'query': '''query {
  userByDisplayName(displayname:"%s") {
    livestream {
      content
      createdAt
      title
      thumbnailUrl
      watchingCount
    }
    username
  }
}''' % display_name}).encode())['data']['userByDisplayName']
        livestream = user['livestream']
        title = livestream['title']
        username = user['username']
        formats = self._extract_m3u8_formats(
            'https://live.prd.dlive.tv/hls/live/%s.m3u8' % username,
            display_name, 'mp4')
        return {
            'id': display_name,
            'title': title,
            'uploader': display_name,
            'uploader_id': username,
            'formats': formats,
            'description': livestream.get('content'),
            'thumbnail': livestream.get('thumbnailUrl'),
            'is_live': True,
            'timestamp': int_or_none(livestream.get('createdAt'), 1000),
            'view_count': int_or_none(livestream.get('watchingCount')),
        }

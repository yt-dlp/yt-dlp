import json

from .common import InfoExtractor
from ..utils import int_or_none


class DLiveVODIE(InfoExtractor):
    IE_NAME = 'dlive:vod'
    _VALID_URL = r'https?://(?:www\.)?dlive\.tv/p/(?P<uploader_id>.+?)\+(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://dlive.tv/p/planesfan+wDeWRZ8HR',
        'info_dict': {
            'id': 'wDeWRZ8HR',
            'ext': 'mp4',
            'title': 'Money\'s in, guys!',
            'upload_date': '20250712',
            'timestamp': 1752354913,
            'uploader_id': 'planesfan',
            'description': '',
            'thumbnail': 'https://images.prd.dlivecdn.com/thumbnail/34c9c404-5f67-11f0-a812-52ea47803baf',
            'view_count': int,
        },
    }, {
        'url': 'https://dlive.tv/p/planesfan+wDeWRZ8HR',
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
}''' % (uploader_id, vod_id)}).encode(), headers={'content-type': 'application/json'})['data']['pastBroadcast']  # noqa: UP031
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
}''' % display_name}).encode(), headers={'content-type': 'application/json'})['data']['userByDisplayName']  # noqa: UP031
        livestream = user['livestream']
        title = livestream['title']
        username = user['username']
        formats = self._extract_m3u8_formats(
            f'https://live.prd.dlive.tv/hls/live/{username}.m3u8',
            display_name, 'mp4')

        for unsigned_format in formats:
            signed_url = self._download_webpage(
                'https://live.prd.dlive.tv/hls/sign/url', display_name,
                data=json.dumps({'playlisturi': unsigned_format['url']}).encode())
            unsigned_format['url'] = signed_url

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

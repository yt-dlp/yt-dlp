from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import parse_iso8601
from ..utils.traversal import require, traverse_obj


class NetAppBaseIE(InfoExtractor):
    _BC_URL = 'https://players.brightcove.net/6255154784001/default_default/index.html?videoId={}'

    @staticmethod
    def _parse_metadata(item):
        return traverse_obj(item, {
            'title': ('name', {str}),
            'description': ('description', {str}),
            'timestamp': ('createdAt', {parse_iso8601}),
        })


class NetAppVideoIE(NetAppBaseIE):
    _VALID_URL = r'https?://media\.netapp\.com/video-detail/(?P<id>[0-9a-f-]+)'

    _TESTS = [{
        'url': 'https://media.netapp.com/video-detail/da25fc01-82ad-5284-95bc-26920200a222/seamless-storage-for-modern-kubernetes-deployments',
        'info_dict': {
            'id': '1843620950167202073',
            'ext': 'mp4',
            'title': 'Seamless storage for modern Kubernetes deployments',
            'description': 'md5:1ee39e315243fe71fb90af2796037248',
            'uploader_id': '6255154784001',
            'duration': 2159.41,
            'thumbnail': r're:https://house-fastly-signed-us-east-1-prod\.brightcovecdn\.com/image/.*\.jpg',
            'tags': 'count:15',
            'timestamp': 1758213949,
            'upload_date': '20250918',
        },
    }, {
        'url': 'https://media.netapp.com/video-detail/45593e5d-cf1c-5996-978c-c9081906e69f/unleash-ai-innovation-with-your-data-with-the-netapp-platform',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_uuid = self._match_id(url)
        metadata = self._download_json(
            f'https://api.media.netapp.com/client/detail/{video_uuid}', video_uuid)

        brightcove_video_id = traverse_obj(metadata, (
            'sections', lambda _, v: v['type'] == 'Player', 'video', {str}, any, {require('brightcove video id')}))

        video_item = traverse_obj(metadata, ('sections', lambda _, v: v['type'] == 'VideoDetail', any))

        return self.url_result(
            self._BC_URL.format(brightcove_video_id), BrightcoveNewIE, brightcove_video_id,
            url_transparent=True, **self._parse_metadata(video_item))


class NetAppCollectionIE(NetAppBaseIE):
    _VALID_URL = r'https?://media\.netapp\.com/collection/(?P<id>[0-9a-f-]+)'
    _TESTS = [{
        'url': 'https://media.netapp.com/collection/9820e190-f2a6-47ac-9c0a-98e5e64234a4',
        'info_dict': {
            'title': 'Featured sessions',
            'id': '9820e190-f2a6-47ac-9c0a-98e5e64234a4',
        },
        'playlist_count': 4,
    }]

    def _entries(self, metadata):
        for item in traverse_obj(metadata, ('items', lambda _, v: v['brightcoveVideoId'])):
            brightcove_video_id = item['brightcoveVideoId']
            yield self.url_result(
                self._BC_URL.format(brightcove_video_id), BrightcoveNewIE, brightcove_video_id,
                url_transparent=True, **self._parse_metadata(item))

    def _real_extract(self, url):
        collection_uuid = self._match_id(url)
        metadata = self._download_json(
            f'https://api.media.netapp.com/client/collection/{collection_uuid}', collection_uuid)

        return self.playlist_result(self._entries(metadata), collection_uuid, playlist_title=metadata.get('name'))

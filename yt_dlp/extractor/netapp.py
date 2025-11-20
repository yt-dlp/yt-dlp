from .common import InfoExtractor
from ..utils import ExtractorError


class NetAppBaseIE(InfoExtractor):
    _ACCOUNT_ID = '6255154784001'
    _VIDEO_METADATA_URL = 'https://api.media.netapp.com/client/detail/%s'
    _COLLECTION_METADATA_URL = 'https://api.media.netapp.com/client/collection/%s'
    _BC_URL = f'https://players.brightcove.net/{_ACCOUNT_ID}/default_default/index.html?videoId=%s'


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
            'thumbnail': 'https://house-fastly-signed-us-east-1-prod.brightcovecdn.com/image/v1/static/6255154784001/70c1fa03-0e35-4527-bc1f-f1805546bf9a/6c7c327c-408e-4a98-9779-4a0b24708c86/1920x1080/match/image.jpg?fastly_token=NjkxZjNiOGZfYWUwZjc4YWMxZTdhM2I4NzY3MWUxYTVjMmY0OTg4NTQ5ZDkyNDg1YmZmZTg5NjRlNzRkYzIzY2FjZTY5NjlhZl9odHRwczovL2hvdXNlLWZhc3RseS1zaWduZWQtdXMtZWFzdC0xLXByb2QuYnJpZ2h0Y292ZWNkbi5jb20vaW1hZ2UvdjEvc3RhdGljLzYyNTUxNTQ3ODQwMDEvNzBjMWZhMDMtMGUzNS00NTI3LWJjMWYtZjE4MDU1NDZiZjlhLzZjN2MzMjdjLTQwOGUtNGE5OC05Nzc5LTRhMGIyNDcwOGM4Ni8xOTIweDEwODAvbWF0Y2gvaW1hZ2UuanBn',
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
        metadata = self._download_json(self._VIDEO_METADATA_URL % video_uuid, video_uuid)

        video_id = None
        title = None
        for section in metadata.get('sections', {}):
            if section.get('type') == 'Player':
                video_id = section.get('video')
            if section.get('type') == 'VideoDetail':
                title = section.get('name')
                description = section.get('description')

        if not video_id:
            raise ExtractorError('Video ID not found in metadata')
        if not title:
            raise ExtractorError('Title not found in metadata')

        return {
            '_type': 'url_transparent',
            'url': self._BC_URL % video_id,
            'ie_key': 'BrightcoveNew',
            'title': title,
            'description': description,
        }


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
        for item in metadata.get('items', {}):
            video_id = item.get('brightcoveVideoId')
            yield {
                '_type': 'url_transparent',
                'url': self._BC_URL % video_id,
                'ie_key': 'BrightcoveNew',
                'title': item.get('name'),
            }

    def _real_extract(self, url):
        collection_uuid = self._match_id(url)
        metadata = self._download_json(self._COLLECTION_METADATA_URL % collection_uuid, collection_uuid)

        return self.playlist_result(self._entries(metadata), playlist_id=metadata.get('id'), playlist_title=metadata.get('name'))

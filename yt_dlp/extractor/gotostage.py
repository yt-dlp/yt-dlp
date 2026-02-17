import json

from .common import InfoExtractor
from ..utils import traverse_obj, url_or_none


class GoToStageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gotostage\.com/channel/[a-z0-9]+/recording/(?P<id>[a-z0-9]+)/watch'
    _TESTS = [{
        'url': 'https://www.gotostage.com/channel/8901680603948959494/recording/60bb55548d434f21b9ce4f0e225c4895/watch',
        'md5': 'ca72ce990cdcd7a2bd152f7217e319a2',
        'info_dict': {
            'id': '60bb55548d434f21b9ce4f0e225c4895',
            'ext': 'mp4',
            'title': 'What is GoToStage?',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 93.924711,
        },
    }, {
        'url': 'https://www.gotostage.com/channel/bacc3d3535b34bafacc3f4ef8d4df78a/recording/831e74cd3e0042be96defba627b6f676/watch?source=HOMEPAGE',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(
            f'https://api.gotostage.com/contents?ids={video_id}',
            video_id,
            note='Downloading video metadata',
            errnote='Unable to download video metadata')[0]

        registration_data = {
            'product': metadata['product'],
            'resourceType': metadata['contentType'],
            'productReferenceKey': metadata['productRefKey'],
            'firstName': 'foo',
            'lastName': 'bar',
            'email': 'foobar@example.com',
        }

        registration_response = self._download_json(
            'https://api-registrations.logmeininc.com/registrations',
            video_id,
            data=json.dumps(registration_data).encode(),
            expected_status=409,
            headers={'Content-Type': 'application/json'},
            note='Register user',
            errnote='Unable to register user')

        content_response = self._download_json(
            f'https://api.gotostage.com/contents/{video_id}/asset',
            video_id,
            headers={'x-registrantkey': registration_response['registrationKey']},
            note='Get download url',
            errnote='Unable to get download url')

        return {
            'id': video_id,
            'title': traverse_obj(metadata, ('title', {str})),
            'url': traverse_obj(content_response, ('cdnLocation', {str})),
            'ext': 'mp4',
            'thumbnail': url_or_none(traverse_obj(metadata, ('thumbnail', 'location'))),
            'duration': traverse_obj(metadata, ('duration', {float})),
            'categories': [traverse_obj(metadata, ('category', {str}))],
            'is_live': False,
        }

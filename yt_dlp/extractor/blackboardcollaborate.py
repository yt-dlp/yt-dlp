import base64
import json

from .common import InfoExtractor
from ..utils import (
    mimetype2ext,
    parse_iso8601,
)
from ..utils.traversal import traverse_obj

'''APIs references - Blackboard Learn: https://developer.blackboard.com/portal/displayApi
                   - Blackboard Collaborate: https://github.com/blackboard/BBDN-Collab-Postman-REST'''


class BlackboardCollaborateIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (?P<region>[a-z]+)(?:-lti)?\.bbcollab\.com/
                        (?:
                            collab/ui/session/playback/load|
                            recording
                        )/
                        (?P<id>[^/\?]+)
                        \??(authToken=(?P<token>[\w\.\-]+))?'''
    _TESTS = [
        {
            'url': 'https://us-lti.bbcollab.com/collab/ui/session/playback/load/0a633b6a88824deb8c918f470b22b256',
            'md5': 'bb7a055682ee4f25fdb5838cdf014541',
            'info_dict': {
                'id': '0a633b6a88824deb8c918f470b22b256',
                'title': 'HESI A2 Information Session - Thursday, May 6, 2021 - recording_1',
                'ext': 'mp4',
                'duration': 1896000,
                'timestamp': 1620331399,
                'upload_date': '20210506',
            },
        },
        {
            'url': 'https://us.bbcollab.com/collab/ui/session/playback/load/76761522adfe4345a0dee6794bbcabda',
            'only_matching': True,
        },
        {
            'url': 'https://ca.bbcollab.com/collab/ui/session/playback/load/b6399dcb44df4f21b29ebe581e22479d',
            'only_matching': True,
        },
        {
            'url': 'https://eu.bbcollab.com/recording/51ed7b50810c4444a106e48cefb3e6b5',
            'only_matching': True,
        },
        {
            'url': 'https://au.bbcollab.com/collab/ui/session/playback/load/2bccf7165d7c419ab87afc1ec3f3bb15',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        # Prepare for requests
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        token = mobj.group('token')

        headers = {'Authorization': f'Bearer {token}'}
        base_url = f'https://{region}.bbcollab.com/collab/api/csa/recordings/{video_id}'

        # Try request the way the player handles it when behind a login
        if video_info := self._download_json(f'{base_url}/data/secure', video_id, 'Trying auth token',
                                             headers=headers, fatal=False):
            video_extra = self._download_json(f'{base_url}', video_id, 'Retrieving extra attributes',
                                              headers=headers, fatal=False)

        # Blackboard will allow redownloading from the same IP without authentication for a while, so if previous method fails, try this
        else:
            video_info = self._download_json(f'{base_url}/data', video_id, 'Trying fallback')
            video_extra = 0

        # Get metadata
        duration = video_info.get('duration') / 1000
        title = video_info.get('name')
        upload_date = video_info.get('created')

        # Get streams
        stream_formats = []
        streams = video_info.get('extStreams')  # Can also use video_info.get('streams') but I don't know its structure

        for current_stream in streams:
            stream_formats.append({
                'url': current_stream['streamUrl'],
                'container': mimetype2ext(current_stream.get('contentType')),
                'filesize': video_extra.get('storageSize', None),
                'aspect_ratio': video_info.get('aspectRatio', ''),
            })

        # Get subtitles
        subtitles = {}
        subs = video_info.get('subtitles')
        for current_subs in subs:
            lang_code = current_subs.get('lang')
            subtitles.setdefault(lang_code, []).append({
                'name': current_subs.get('label'),
                'url': current_subs['url'],
            })

        # Get chat
        chats = video_info.get('chats')
        for current_chat in chats:
            subtitles.setdefault('live_chat', []).append({'url': current_chat['url']})

        return {
            'duration': duration,
            'formats': stream_formats,
            'id': video_id,
            'timestamp': parse_iso8601(upload_date),
            'subtitles': subtitles,
            'title': title,
        }

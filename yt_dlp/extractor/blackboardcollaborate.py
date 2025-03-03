import base64
import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    parse_qs,
    str_or_none,
    url_or_none,
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
                'duration': 1896,
                'timestamp': 1620333295,
                'upload_date': '20210506',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://eu.bbcollab.com/collab/ui/session/playback/load/4bde2dee104f40289a10f8e554270600',
            'md5': '108db6a8f83dcb0c2a07793649581865',
            'info_dict': {
                'id': '4bde2dee104f40289a10f8e554270600',
                'title': 'Meeting - Azerbaycanca erize formasi',
                'ext': 'mp4',
                'duration': 880,
                'timestamp': 1671176868,
                'upload_date': '20221216',
            },
        },
        {
            'url': 'https://eu.bbcollab.com/recording/f83be390ecff46c0bf7dccb9dddcf5f6',
            'md5': 'e3b0b88ddf7847eae4b4c0e2d40b83a5',
            'info_dict': {
                'id': 'f83be390ecff46c0bf7dccb9dddcf5f6',
                'title': 'Keynote lecture by Laura Carvalho - recording_1',
                'ext': 'mp4',
                'duration': 5506,
                'timestamp': 1662721705,
                'upload_date': '20220909',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://eu.bbcollab.com/recording/c3e1e7c9e83d4cd9981c93c74888d496',
            'md5': 'fdb2d8c43d66fbc0b0b74ef5e604eb1f',
            'info_dict': {
                'id': 'c3e1e7c9e83d4cd9981c93c74888d496',
                'title': 'International Ally User Group - recording_18',
                'ext': 'mp4',
                'duration': 3479,
                'timestamp': 1721919621,
                'upload_date': '20240725',
                'subtitles': {
                    'en': 'mincount:1',
                    'live_chat': 'mincount:1',
                },
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

    def _call_api(self, region, video_id, api_call='', token=None, note='Downloading JSON metadata', fatal=False):
        return self._download_json(f'https://{region}.bbcollab.com/collab/api/csa/recordings/{video_id}/{api_call}',
                                   video_id, note=note,
                                   headers={'Authorization': f'Bearer {token}'} if token else '', fatal=fatal)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        token = mobj.group('token') or parse_qs(url).get('authToken')

        if video_info := self._call_api(region, video_id, 'data/secure', token, 'Trying auth token'):
            video_extra = self._call_api(region, video_id, token=token, note='Retrieving extra attributes')
        else:
            video_info = self._call_api(region, video_id, 'data', note='Trying fallback', fatal=True)
            video_extra = {}

        duration = int_or_none(video_info.get('duration'), 1000)
        title = video_info.get('name')
        upload_date = video_info.get('created')

        formats = traverse_obj(video_info, ('extStreams', ..., {
            'url': ('streamUrl', {url_or_none}),
            'container': ('contentType', {mimetype2ext}),
            'aspect_ratio': ('aspectRatio'),
        }))

        for cur_format in formats:
            cur_format['filesize'] = int_or_none(video_extra.get('storageSize'))

        subtitles = {}
        for current_subs in video_info.get('subtitles'):
            lang_code = current_subs.get('lang')
            subtitles.setdefault(lang_code, []).append({
                'name': str_or_none(current_subs.get('label')),
                'url': url_or_none(current_subs['url']),
            })

        for current_chat in video_info.get('chats'):
            subtitles.setdefault('live_chat', []).append({'url': url_or_none(current_chat['url'])})

        return {
            'duration': duration,
            'formats': formats,
            'id': video_id,
            'timestamp': parse_iso8601(upload_date),
            'subtitles': subtitles,
            'title': title,
        }


class BlackboardCollaborateLaunchIE(InfoExtractor):
    _VALID_URL = r'https?://[a-z]+\.bbcollab\.com/launch/(?P<token>[\w\.\-]+)'

    _TESTS = [
        {
            'url': 'https://au.bbcollab.com/launch/eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJiYkNvbGxhYkFwaSIsInN1YiI6ImJiQ29sbGFiQXBpIiwiZXhwIjoxNzQwNDE2NDgzLCJpYXQiOjE3NDA0MTYxODMsInJlc291cmNlQWNjZXNzVGlja2V0Ijp7InJlc291cmNlSWQiOiI3MzI4YzRjZTNmM2U0ZTcwYmY3MTY3N2RkZTgzMzk2NSIsImNvbnN1bWVySWQiOiJhM2Q3NGM0Y2QyZGU0MGJmODFkMjFlODNlMmEzNzM5MCIsInR5cGUiOiJSRUNPUkRJTkciLCJyZXN0cmljdGlvbiI6eyJ0eXBlIjoiVElNRSIsImV4cGlyYXRpb25Ib3VycyI6MCwiZXhwaXJhdGlvbk1pbnV0ZXMiOjUsIm1heFJlcXVlc3RzIjotMX0sImRpc3Bvc2l0aW9uIjoiTEFVTkNIIiwibGF1bmNoVHlwZSI6bnVsbCwibGF1bmNoQ29tcG9uZW50IjpudWxsLCJsYXVuY2hQYXJhbUtleSI6bnVsbH19.xuELw4EafEwUMoYcCHidGn4Tw9O1QCbYHzYGJUl0kKk',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        token = self._match_valid_url(url)['token']
        video_id = traverse_obj(json.loads(base64.b64decode(token.split('.')[1] + '===')), ('resourceAccessTicket', 'resourceId'))

        redirect_url = self._request_webpage(url, video_id=video_id).url
        return self.url_result(redirect_url,
                               ie=BlackboardCollaborateIE.ie_key(), video_id=video_id)

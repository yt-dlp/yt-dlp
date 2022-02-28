# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    smuggle_url,
    unsmuggle_url,
    int_or_none,
    traverse_obj
)

from random import random
import json


class PanoptoBaseIE(InfoExtractor):
    BASE_URL_RE = r'(?P<base_url>https?://[\w.]+\.panopto.(?:com|eu)/Panopto)'

    def _call_api(self, base_url, path, video_id, query, fatal=True):
        response = self._download_json(base_url + path, video_id, query=query, fatal=fatal)
        if not response:
            return
        error_code = response.get('ErrorCode')
        if error_code == 2:
            self.raise_login_required(method='cookies')
        elif error_code is not None:
            msg = f'Panopto said: {response.get("ErrorMessage")}'
            if fatal:
                raise ExtractorError(msg, video_id)
            else:
                self.report_warning(msg, video_id=video_id)
        return response


class PanoptoIE(PanoptoBaseIE):
    _VALID_URL = PanoptoBaseIE.BASE_URL_RE + r'/Pages/Viewer\.aspx\?id=(?P<id>[a-f0-9-]+)'
    _TESTS = [
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=26b3ae9e-4a48-4dcc-96ba-0befba08a0fb',
            'info_dict': {
                'id': '26b3ae9e-4a48-4dcc-96ba-0befba08a0fb',
                'title': 'Panopto for Business - Use Cases',
                'timestamp': 1459184200,
                'thumbnail': r're:https://demo\.hosted\.panopto\.com/Panopto/Services/FrameGrabber\.svc/FrameRedirect\?objectId=26b3ae9e-4a48-4dcc-96ba-0befba08a0fb&mode=Delivery&random=[\d.]+',
                'upload_date': '20160328',
            },
            'playlist': [
                {
                    'info_dict': {
                        'id': '0d28b224-bd94-40d4-a7a0-502f15715fd5',
                        'ext': 'mp4',
                        'title': 'DV',
                        'chapters': 'count:0'
                    },
                },
            ],
        },
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=ed01b077-c9e5-4c7b-b8ff-15fa306d7a59',
            'info_dict': {
                'id': 'ed01b077-c9e5-4c7b-b8ff-15fa306d7a59',
                'title': 'Overcoming Top 4 Challenges of Enterprise Video',
                'uploader': 'Panopto Support',
                'timestamp': 1449409251,
                'thumbnail': r're:https://demo\.hosted\.panopto\.com/Panopto/Services/FrameGrabber\.svc/FrameRedirect\?objectId=ed01b077-c9e5-4c7b-b8ff-15fa306d7a59&mode=Delivery&random=[\d.]+',
                'upload_date': '20151206',
            },
            'playlist': [
                {
                    'info_dict': {
                        'id': '15ad06ef-3f7d-4074-aa4a-87c41dd18f9c',
                        'ext': 'mp4',
                        'title': 'OBJECT',
                        'chapters': 'count:21'
                    },
                },
                {
                    'info_dict': {
                        'id': '7668d6b2-dc81-421d-9853-20653689e2e8',
                        'ext': 'mp4',
                        'title': 'DV',
                        'chapters': 'count:21'
                    },
                },
            ],
            'playlist_count': 2,
        },
        {
            'url': 'https://ucc.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=0e8484a4-4ceb-4d98-a63f-ac0200b455cb',
            'only_matching': True
        }
    ]

    @staticmethod
    def _extract_chapters(delivery):
        chapters = []
        for timestamp in delivery.get('Timestamps', []):
            start, duration = int_or_none(timestamp.get('Time')), int_or_none(timestamp.get('Duration'))
            if start is None or duration is None:
                continue
            chapters.append({
                'start_time': start,
                'end_time': start + duration,
                'title': timestamp.get('Caption')
            })
        return chapters

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        base_url, video_id = mobj.group('base_url', 'id')
        delivery_info = self._call_api(
            base_url, '/Pages/Viewer/DeliveryInfo.aspx', video_id,
            query={
                'deliveryId': video_id,
                'invocationId': '',
                'isLiveNotes': 'false',
                'refreshAuthCookie': 'true',
                'isActiveBroadcast': 'false',
                'isEditing': 'false',
                'isKollectiveAgentInstalled': 'false',
                'isEmbed': 'false',
                'responseType': 'json',
            }
        )

        delivery = delivery_info['Delivery']

        streams = []
        chapters = self._extract_chapters(delivery)
        for stream in delivery.get('Streams'):
            if not isinstance(stream, dict):
                continue
            formats = []
            http_stream_url = stream.get('StreamHttpUrl')
            if http_stream_url:
                formats.append({'url': http_stream_url})

            m3u8_formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream.get('StreamUrl'), video_id, 'mp4')
            formats.extend(m3u8_formats)

            streams.append({
                'id': stream['PublicID'],
                'title': stream.get('Tag'),
                'formats': formats,
                'subtitles': subtitles,
                'chapters': chapters
            })

        session_start_time = int_or_none(delivery.get('SessionStartTime'))

        # TODO: should we return as single video if only one stream?
        # What do we do with the changing id to match the stream?
        info = {
            '_type': 'multi_video',
            'id': video_id,
            'title': delivery.get('SessionName'),
            'thumbnail': base_url + f'/Services/FrameGrabber.svc/FrameRedirect?objectId={video_id}&mode=Delivery&random={random()}',
            'entries': streams,
            'uploader': ', '.join(filter(None, traverse_obj(delivery, ('Contributors', ..., 'DisplayName'), default=[]))) or None,
            'timestamp': session_start_time - 11640000000 if session_start_time else None,
            'duration': delivery.get('duration'),
        }

        return info


class PanoptoFolderIE(PanoptoBaseIE):
    """Recursively extracts a folder of Panopto videos, digging as far as possible into subfolders."""

    _VALID_URL = r'^https?://(?P<org>[a-z0-9]+)\.hosted\.panopto.com/Panopto/Pages/Sessions/List\.aspx(?:\?.*)?#(?:.*&)?folderID=(?:"|%22)(?P<id>[a-f0-9-]+)'
    _TESTS = [
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID=%224540f269-8bb1-4352-b5dc-64e5919d1c40%22',
            'info_dict': {
                'id': '4540f269-8bb1-4352-b5dc-64e5919d1c40',
                'title': 'Demo',
            },
            'playlist_count': 4,
        }
    ]

    def _real_extract(self, url):
        """Recursively extracts the video and stream information for the given Panopto hosted URL."""
        url, smuggled = unsmuggle_url(url)
        if smuggled is None:
            smuggled = {}
        folder_id = self._match_id(url)
        org = self._match_organization(url)

        folder_data = self._download_json(
            'https://{0}.hosted.panopto.com/Panopto/Services/Data.svc/GetSessions'.format(org),
            folder_id,
            'Downloading folder listing',
            'Failed to download folder listing',
            data=json.dumps({
                'queryParameters': {
                    'query': None,
                    'sortColumn': 1,
                    'sortAscending': False,
                    'maxResults': 10000,
                    'page': 0,
                    'startDate': None,
                    'endDate': None,
                    'folderID': folder_id,
                    'bookmarked': False,
                    'getFolderData': True,
                    'isSharedWithMe': False,
                },
            }, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'})['d']

        entries = []
        if 'Results' in folder_data and folder_data['Results'] is not None:
            for video in folder_data['Results']:
                new_video = {
                    'id': video['DeliveryID'],
                    'title': video['SessionName'],
                    'url': video['ViewerUrl'],
                    '_type': 'url_transparent',
                    'ie_key': 'Panopto',
                }
                if 'prev_folders' in smuggled:
                    new_video['title'] = smuggled['prev_folders'] + ' -- ' + new_video['title']
                entries.append(new_video)

        if 'Subfolders' in folder_data and folder_data['Subfolders'] is not None:
            for subfolder in folder_data['Subfolders']:
                new_folder = {
                    'id': subfolder['ID'],
                    'title': subfolder['Name'],
                    '_type': 'url_transparent',
                    'ie_key': 'PanoptoFolder',
                }
                if 'prev_folders' in smuggled:
                    new_folder['title'] = smuggled['prev_folders'] + ' -- ' + new_folder['title']
                new_folder['url'] = smuggle_url('https://{0}.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID="{1}"'
                                                .format(org, subfolder['ID']), {'prev_folders': new_folder['title']})
                entries.append(new_folder)

        if not entries:
            raise ExtractorError('Folder is empty or authentication failed')

        return {
            'id': folder_id,
            'title': folder_data['Results'][0]['FolderName'] if len(folder_data['Results']) else folder_data['Subfolders'][0]['ParentFolderName'],
            '_type': 'playlist',
            'entries': entries,
        }

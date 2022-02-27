# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..compat import compat_str

from ..utils import (
    ExtractorError,
    smuggle_url,
    unsmuggle_url,
)

import re
from random import random
import json


class PanoptoBaseIE(InfoExtractor):
    """The base class with common methods for Panopto extractors."""

    @classmethod
    def _match_organization(cls, url):
        """Match and return the organization part of a Panopto hosted URL."""
        if '_VALID_URL_RE' not in cls.__dict__:
            cls._VALID_URL_RE = re.compile(cls._VALID_URL)
        m = cls._VALID_URL_RE.match(url)
        assert m
        return compat_str(m.group('org'))


class PanoptoIE(PanoptoBaseIE):
    """Extracts a single Panopto video including all available streams."""

    _VALID_URL = r'^https?://(?P<org>[a-z0-9]+)\.hosted\.panopto.com/Panopto/Pages/Viewer\.aspx\?id=(?P<id>[a-f0-9-]+)'
    _TESTS = [
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=26b3ae9e-4a48-4dcc-96ba-0befba08a0fb',
            'md5': 'e8e6ef6b0572dd5985f5f8c3e096f717',
            'info_dict': {
                'id': '26b3ae9e-4a48-4dcc-96ba-0befba08a0fb',
                'ext': 'mp4',
                'title': 'Panopto for Business - Use Cases',
                'uploader': 'Ari Bixhorn',
                'upload_date': '20160328',
                'timestamp': 1459184200.3759995,
            },
        },
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=ed01b077-c9e5-4c7b-b8ff-15fa306d7a59',
            'info_dict': {
                'id': 'ed01b077-c9e5-4c7b-b8ff-15fa306d7a59',
                'title': 'Overcoming Top 4 Challenges of Enterprise Video',
                'uploader': 'Panopto Support',
                'timestamp': 1449409251.8579998,
            },
            'playlist': [
                {
                    'md5': 'e22b5a284789ba2681e4fe215352d816',
                    'info_dict': {
                        'id': '15ad06ef-3f7d-4074-aa4a-87c41dd18f9c',
                        'ext': 'mp4',
                        'title': 'OBJECT',
                    },
                },
                {
                    'md5': 'a483b8116abbb04a7112a9a3ccc835ce',
                    'info_dict': {
                        'id': '7668d6b2-dc81-421d-9853-20653689e2e8',
                        'ext': 'mp4',
                        'title': 'DV',
                    },
                },
            ],
            'playlist_count': 2,
        },
    ]

    @staticmethod
    def _get_contribs_str(contribs):
        """Returns a comma-delimited string of contributors."""
        s = ''
        for c in contribs:
            display_name = c.get('DisplayName')
            if display_name is not None:
                s += '{0}, '.format(display_name)
        return s[:-2] if len(contribs) else ''

    def _real_extract(self, url):
        """Extracts the video and stream information for the given Panopto hosted URL."""
        video_id = self._match_id(url)
        org = self._match_organization(url)

        delivery_info = self._download_json(
            'https://{0}.hosted.panopto.com/Panopto/Pages/Viewer/DeliveryInfo.aspx'.format(org),
            video_id,
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

        if 'ErrorCode' in delivery_info:
            self._downloader.report_warning("If the video you are trying to download requires you to sign-in, you will "
                                            "need to provide a cookies file that allows the downloader to authenticate "
                                            "with Panopto. If the error below is about unauthorized access, this is "
                                            "most likely the issue.")
            raise ExtractorError(
                'API error: ({0}) {1}'.format(delivery_info.get('ErrorCode', '?'), delivery_info.get('ErrorMessage', '?'))
            )

        streams = []
        for this_stream in delivery_info['Delivery']['Streams']:
            new_stream = {
                'id': this_stream['PublicID'],
                'title': this_stream['Tag'],
                'formats': [],
            }
            if 'StreamHttpUrl' in this_stream:
                new_stream['formats'].append({
                    'url': this_stream['StreamHttpUrl'],
                })
            if 'StreamUrl' in this_stream:
                m3u8_formats = self._extract_m3u8_formats(this_stream['StreamUrl'], video_id, 'mp4')
                self._sort_formats(m3u8_formats)
                new_stream['formats'].extend(m3u8_formats)
            if len(new_stream['formats']):
                streams.append(new_stream)

        if not streams:
            raise ExtractorError('No streams found.')

        result = {
            'id': video_id,
            'title': delivery_info['Delivery']['SessionName'],
            'thumbnail': 'https://{0}.hosted.panopto.com/Panopto/Services/FrameGrabber.svc/FrameRedirect?objectId={1}&mode=Delivery&random={2}'.format(
                         org, video_id, random()),
        }

        if len(streams) == 1:
            result['formats'] = streams[0]['formats']
        else:
            result['_type'] = 'multi_video'
            result['entries'] = streams

        # We already know Delivery exists since we need it for stream extraction
        contributors = delivery_info['Delivery'].get('Contributors')
        if contributors is not None:
            result['uploader'] = self._get_contribs_str(contributors)

        session_start_time = delivery_info['Delivery'].get('SessionStartTime')
        if session_start_time is not None:
            result['timestamp'] = session_start_time - 11640000000

        duration = delivery_info['Delivery'].get('Duration')
        if duration is not None:
            result['duration'] = duration

        thumbnails = []
        if 'Timestamps' in delivery_info['Delivery']:
            for timestamp in delivery_info['Delivery']['Timestamps']:
                object_id = timestamp.get('ObjectIdentifier')
                object_sequence_num = timestamp.get('ObjectSequenceNumber')
                if object_id is not None and object_sequence_num is not None:
                    thumbnails.append({
                        'url': 'https://{0}.hosted.panopto.com/Panopto/Pages/Viewer/Image.aspx?id={1}&number={2}&x=undefined'.format(
                               org, object_id, object_sequence_num)
                    })

                # This provides actual thumbnails instead of the above which allows for downloading of real slides
                # object_public_id = timestamp.get('ObjectPublicIdentifier')
                # session_id = timestamp.get('SessionID')
                # absolute_time = timestamp.get('AbsoluteTime')
                # if object_public_id is not None and session_id is not None and object_sequence_num is not None and absolute_time is not None:
                #     thumbnails.append({
                #         'url': 'https://{0}.hosted.panopto.com/Panopto/Pages/Viewer/Thumb.aspx?eventTargetPID={1}&sessionPID={2}&number={3}&isPrimary=false&absoluteTime={4}'.format(
                #             org, object_public_id, session_id, object_sequence_num, absolute_time),
                #     })

        if len(thumbnails):
            if result.get('entries') is not None:
                result['entries'][1]['thumbnails'] = thumbnails
            else:
                result['thumbnails'] = thumbnails

        return result


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

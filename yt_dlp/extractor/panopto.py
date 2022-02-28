# coding: utf-8
from __future__ import unicode_literals

import functools

from .common import InfoExtractor
from .youtube import get_first
from ..compat import compat_urllib_parse_urlparse, compat_parse_qs, compat_urlparse

from ..utils import (
    ExtractorError,
    smuggle_url,
    unsmuggle_url,
    int_or_none,
    traverse_obj, parse_qs, OnDemandPagedList, InAdvancePagedList, js_to_json
)

from random import random
import json


class PanoptoBaseIE(InfoExtractor):
    BASE_URL_RE = r'(?P<base_url>https?://[\w.]+\.panopto.(?:com|eu)/Panopto)'

    def _call_api(self, base_url, path, video_id, query=None, data=None, fatal=True):
        response = self._download_json(base_url + path, video_id, query=query, data=json.dumps(data).encode('utf8'), fatal=fatal, headers={'content-type': 'application/json'})
        if not response:
            return
        error_code = response.get('ErrorCode')
        if error_code == 2:
            self.raise_login_required(method='cookies')
        elif error_code is not None:
            msg = f'Panopto said: {response.get("ErrorMessage")}'
            if fatal:
                raise ExtractorError(msg, video_id=video_id)
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


class PanoptoListIE(PanoptoBaseIE):
    _VALID_URL = PanoptoBaseIE.BASE_URL_RE + r'/Pages/Sessions/List\.aspx'
    _PAGE_SIZE = 250
    _TESTS = [
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID=%22e4c6a2fc-1214-4ca0-8fb7-aef2e29ff63a%22',
            'info_dict': {
                'id': 'e4c6a2fc-1214-4ca0-8fb7-aef2e29ff63a',
                'title': 'Showcase Videos'
            },
            'playlist_mincount': 140

        },
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#view=2&maxResults=250',
            'info_dict': {
                'id': 'list',
            },
            'playlist_mincount': 300
        }

    ]

    def _fetch_page(self, base_url, query_params, display_id, page):

        params = {
            'sortColumn': 1,
            **query_params,
            'page': page,
            'maxResults': self._PAGE_SIZE,
        }

        response = self._call_api(
            base_url, '/Services/Data.svc/GetSessions', display_id + f' page {page+1}',
            data={'queryParameters': params}, fatal=False)
        if not response:
            return  # TODO this should be fatal but being fatal makes us infinitely hit the site
        for result in traverse_obj(response, (..., 'Results'), get_all=False, default=[]):
            video_id = result.get('DeliveryID')
            yield {
                '_type': 'url',
                'ie_key': PanoptoIE.ie_key(),
                'id': video_id,
                'title': result.get('SessionName'),
                'url': base_url + f'/Pages/Viewer.aspx?id={video_id}',
                'duration': result.get('Duration'),
            }

        for folder in traverse_obj(response, (..., 'Subfolders'), get_all=False, default=[]):
            folder_id = folder.get('ID')
            yield self.url_result(
                base_url + f'/Pages/Sessions/List.aspx#folderID={folder_id}',
                ie_key=PanoptoIE.ie_key(), video_id=folder_id, title=folder.get('Name'))

    def _extract_folder_metadata(self, base_url, folder_id):
        response = self._call_api(
            base_url, '/Services/Data.svc/GetFolderInfo', folder_id,
            data={'folderID': folder_id}, fatal=False)
        return {
            'playlist_title': get_first(response, 'Name')
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        base_url = mobj.group('base_url')

        query_params = {k: json.loads(v[0]) for k, v in compat_urlparse.parse_qs(compat_urllib_parse_urlparse(url).fragment).items()}

        folder_id, display_id = query_params.get('folderID'), 'list'

        if query_params.get('isSubscriptionsPage'):
            display_id = 'subscriptions'
            if not query_params.get('subscribableTypes'):
                query_params['subscribableTypes'] = [0, 1, 2]
        elif query_params.get('isSharedWithMe'):
            display_id = 'sharedwithme'
        elif folder_id:
            display_id = folder_id

        query = query_params.get('query')
        if query:
            display_id += f': query {query}'

        info = {
            '_type': 'playlist',
            'id': display_id,
            'title': display_id,
        }
        if folder_id:
            info.update(self._extract_folder_metadata(base_url, folder_id))

        info['entries'] = OnDemandPagedList(
            functools.partial(self._fetch_page, base_url, query_params, display_id), self._PAGE_SIZE)

        return info
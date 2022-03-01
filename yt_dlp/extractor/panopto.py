# coding: utf-8
from __future__ import unicode_literals

import functools

from .common import InfoExtractor
from .youtube import get_first  # TODO
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_urlparse
)

from ..utils import (
    ExtractorError,
    int_or_none,
    OnDemandPagedList,
    traverse_obj,
    bug_reports_message,
    parse_qs
)

from random import random
import json


class PanoptoBaseIE(InfoExtractor):
    BASE_URL_RE = r'(?P<base_url>https?://[\w.]+\.panopto.(?:com|eu)/Panopto)'

    def _call_api(self, base_url, path, video_id, query=None, data=None, fatal=True):
        response = self._download_json(
            base_url + path, video_id, query=query, data=json.dumps(data).encode('utf8') if data else None,
            fatal=fatal, headers={'accept': 'application/json', 'content-type': 'application/json'})
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

    @staticmethod
    def _parse_fragment(url):
        return {k: json.loads(v[0]) for k, v in compat_urlparse.parse_qs(compat_urllib_parse_urlparse(url).fragment).items()}


class PanoptoIE(PanoptoBaseIE):
    _VALID_URL = PanoptoBaseIE.BASE_URL_RE + r'/Pages/(Viewer|Embed)\.aspx.*(?:\?|&)id=(?P<id>[a-f0-9-]+)'
    _TESTS = [
        {
            'url': 'https://demo.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=26b3ae9e-4a48-4dcc-96ba-0befba08a0fb',
            'info_dict': {
                'id': '26b3ae9e-4a48-4dcc-96ba-0befba08a0fb',
                'title': 'Panopto for Business - Use Cases',
                'timestamp': 1459184200,
                'thumbnail': r're:https://demo\.hosted\.panopto\.com/Panopto/Services/FrameGrabber\.svc/FrameRedirect\?objectId=26b3ae9e-4a48-4dcc-96ba-0befba08a0fb&mode=Delivery&random=[\d.]+',
                'upload_date': '20160328',
                'ext': 'mp4',
                'cast': [],
                'duration': 88.17099999999999,
                'average_rating': 0,
                'uploader_id': '2db6b718-47a0-4b0b-9e17-ab0b00f42b1e',
                'channel_id': 'e4c6a2fc-1214-4ca0-8fb7-aef2e29ff63a',
                'channel': 'Showcase Videos'
            },
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
                'ext': 'mp4',
                'chapters': 'count:21',
                'cast': ['Panopto Support'],
                'uploader_id': 'a96d1a31-b4de-489b-9eee-b4a5b414372c',
                'average_rating': 0,
                'description': 'md5:4391837802b3fc856dadf630c4b375d1',
                'duration': 1088.2659999999998,
                'channel_id': '9f3c1921-43bb-4bda-8b3a-b8d2f05a8546',
                'channel': 'Webcasts',
            },
        },
        {
            # Extra params in URL
            'url': 'https://howtovideos.hosted.panopto.com/Panopto/Pages/Viewer.aspx?randomparam=thisisnotreal&id=5fa74e93-3d87-4694-b60e-aaa4012214ed&advance=true',
            'info_dict': {
                'id': '5fa74e93-3d87-4694-b60e-aaa4012214ed',
                'ext': 'mp4',
                'duration': 129.513,
                'cast': ['Kathryn Kelly'],
                'uploader_id': '316a0a58-7fa2-4cd9-be1c-64270d284a56',
                'timestamp': 1569845768,
                'tags': ['Viewer', 'Enterprise'],
                'upload_date': '20190930',
                'thumbnail': r're:https://howtovideos\.hosted\.panopto\.com/Panopto/Services/FrameGrabber.svc/FrameRedirect\?objectId=5fa74e93-3d87-4694-b60e-aaa4012214ed&mode=Delivery&random=[\d.]+',
                'description': 'md5:2d844aaa1b1a14ad0e2601a0993b431f',
                'title': 'Getting Started: View a Video',
                'average_rating': 0,
                'uploader': 'Kathryn Kelly',
                'channel_id': 'fb93bc3c-6750-4b80-a05b-a921013735d3',
                'channel': 'Getting Started',
            }
        },
        {
            'url': 'https://ucc.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=0e8484a4-4ceb-4d98-a63f-ac0200b455cb',
            'only_matching': True
        },
        {
            'url': 'https://brown.hosted.panopto.com/Panopto/Pages/Embed.aspx?id=0b3ff73b-36a0-46c5-8455-aadf010a3638',
            'only_matching': True
        },
    ]

    @classmethod
    def suitable(cls, url):
        return False if PanoptoPlaylistIE.suitable(url) else super().suitable(url)

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

    def _extract_stream(self, video_id, stream, base_info):
        formats = []
        subtitles = {}
        http_stream_url = stream.get('StreamHttpUrl')
        if http_stream_url:
            formats.append({'url': http_stream_url})

        media_type = stream.get('ViewerMediaFileTypeName')
        if media_type in ('hls', ):
            m3u8_formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream.get('StreamUrl'), video_id, 'mp4')
            formats.extend(m3u8_formats)
        else:
            formats.append({
                'url': stream.get('StreamUrl')
            })
        self._sort_formats(formats)
        tag, title = stream.get('Tag'), base_info.get('title')

        return {
            **base_info,
            'id': stream['PublicID'],
            'title': '{} - {}'.format(title, tag) if tag else title,
            'formats': formats,
            'subtitles': subtitles,
        }

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
        session_start_time = int_or_none(delivery.get('SessionStartTime'))
        base_info = {
            'id': video_id,
            'title': delivery.get('SessionName'),
            'cast': list(filter(None, traverse_obj(delivery, ('Contributors', ..., 'DisplayName'), default=[]))),
            'timestamp': session_start_time - 11640000000 if session_start_time else None,
            'duration': delivery.get('Duration'),
            'thumbnail': base_url + f'/Services/FrameGrabber.svc/FrameRedirect?objectId={video_id}&mode=Delivery&random={random()}',
            'average_rating': delivery.get('AverageRating'),
            'chapters': self._extract_chapters(delivery) or None,
            'uploader': delivery.get('OwnerDisplayName') or None,
            'uploader_id': delivery.get('OwnerId'),
            'description': delivery.get('SessionAbstract') or None,
            'tags': traverse_obj(delivery, ('Tags', ..., 'Content')),
            'channel_id': delivery.get('SessionGroupPublicID'),
            'channel': traverse_obj(delivery, 'SessionGroupLongName', 'SessionGroupShortName', get_all=False)
        }

        # Podcast stream is usually the combined streams. We will prefer that by default.
        for stream in delivery.get('PodcastStreams', []):
            streams.append(self._extract_stream(video_id, stream, base_info))

        if not streams or self._configuration_arg('get_multistreams'):
            for stream in delivery.get('Streams', []):
                streams.append(self._extract_stream(video_id, stream, base_info))

        if not streams:
            self.raise_no_formats('Did not find any streams')

        if len(streams) == 1:
            return {
                **streams[0],
                **base_info,
            }
        else:
            return {
                **base_info,
                '_type': 'multi_video',
                'entries': streams,
            }


class PanoptoPlaylistIE(PanoptoBaseIE):
    _VALID_URL = PanoptoBaseIE.BASE_URL_RE + r'/Pages/(Viewer|Embed)\.aspx.*(?:\?|&)pid=(?P<id>[a-f0-9-]+)'
    _TESTS = [
        {
            'url': 'https://howtovideos.hosted.panopto.com/Panopto/Pages/Viewer.aspx?pid=f3b39fcf-882f-4849-93d6-a9f401236d36&id=5fa74e93-3d87-4694-b60e-aaa4012214ed&advance=true',
            'info_dict': {
                'title': 'Featured Video Tutorials',
                'id': 'f3b39fcf-882f-4849-93d6-a9f401236d36',
                'description': '',
            },
            'playlist_mincount': 36
        }
    ]

    def _entries(self, base_url, playlist_id, session_list_id):
        session_list_info = self._call_api(
            base_url, f'/Api/SessionLists/{session_list_id}?collections[0].maxCount=500&collections[0].name=ViewableItemsOnly', playlist_id)
        items = session_list_info['Items']
        if len(items) == 500:
            self.report_warning(
                'There are 500 items in this playlist. There may be more but we are unable to get them' + bug_reports_message(), only_once=True)

        for item in items:
            if item.get('TypeName') != 'Session':
                self.report_warning('Got an item in the playlist that is not a Session' + bug_reports_message(), only_once=True)
                continue
            yield {
                '_type': 'url',
                'id': item.get('Id'),
                'url': item.get('ViewerUri'),
                'title': item.get('Name')
            }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        base_url, playlist_id = mobj.group('base_url', 'id')

        video_id = get_first(parse_qs(url), 'id')
        if video_id:
            if self.get_param('noplaylist'):
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)
                return self.url_result(base_url + f'/Pages/Viewer.aspx?id={video_id}', ie_key=PanoptoIE.ie_key(), video_id=video_id)
            else:
                self.to_screen(f'Downloading playlist {playlist_id}; add --no-playlist to just download video {video_id}')

        playlist_info = self._call_api(base_url, f'/Api/Playlists/{playlist_id}', playlist_id)

        session_list_id = playlist_info['SessionListId']
        return self.playlist_result(
            self._entries(base_url, playlist_id, session_list_id), playlist_id, playlist_info.get('Name'), playlist_info.get('Description'))


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
                'title': 'list'
            },
            'playlist_mincount': 300
        },
        {
            # Folder that contains 8 folders and a playlist
            'url': 'https://howtovideos.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx?noredirect=true#folderID=%224b9de7ae-0080-4158-8496-a9ba01692c2e%22',
            'info_dict': {
                'id': '4b9de7ae-0080-4158-8496-a9ba01692c2e',
                'title': 'Video Tutorials'
            },
            'playlist_mincount': 9
        }

    ]

    def _fetch_page(self, base_url, query_params, display_id, page):

        params = {
            'sortColumn': 1,
            'getFolderData': True,
            'includePlaylists': True,
            **query_params,
            'page': page,
            'maxResults': self._PAGE_SIZE,
        }

        response = self._call_api(
            base_url, '/Services/Data.svc/GetSessions', display_id + f' page {page+1}',
            data={'queryParameters': params}, fatal=False)
        if not response:
            return  # TODO this should be fatal but being fatal makes us infinitely hit the site
        for result in get_first(response, 'Results', default=[]):
            # This could be a video, playlist (or maybe something else)
            item_id = result.get('DeliveryID')
            yield {
                '_type': 'url',
                'id': item_id,
                'title': result.get('SessionName'),
                'url': traverse_obj(result, 'ViewerUrl', 'EmbedUrl', get_all=False) or (base_url + f'/Pages/Viewer.aspx?id={item_id}'),
                'duration': result.get('Duration'),
            }

        for folder in get_first(response, 'Subfolders', default=[]):
            folder_id = folder.get('ID')
            yield self.url_result(
                base_url + f'/Pages/Sessions/List.aspx#folderID="{folder_id}"',
                ie_key=PanoptoListIE.ie_key(), video_id=folder_id, title=folder.get('Name'))

    def _extract_folder_metadata(self, base_url, folder_id):
        response = self._call_api(
            base_url, '/Services/Data.svc/GetFolderInfo', folder_id,
            data={'folderID': folder_id}, fatal=False)
        return {
            'title': get_first(response, 'Name')
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        base_url = mobj.group('base_url')

        query_params = self._parse_fragment(url)

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
            display_id += f': query "{query}"'

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

import re
import calendar
import json
import functools
from datetime import datetime
from random import random

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_urlparse
)

from ..utils import (
    bug_reports_message,
    ExtractorError,
    get_first,
    int_or_none,
    OnDemandPagedList,
    parse_qs,
    traverse_obj,
)


class PanoptoBaseIE(InfoExtractor):
    BASE_URL_RE = r'(?P<base_url>https?://[\w.]+\.panopto.(?:com|eu)/Panopto)'

    def _call_api(self, base_url, path, video_id, data=None, fatal=True, **kwargs):
        response = self._download_json(
            base_url + path, video_id, data=json.dumps(data).encode('utf8') if data else None,
            fatal=fatal, headers={'accept': 'application/json', 'content-type': 'application/json'}, **kwargs)
        if not response:
            return
        error_code = response.get('ErrorCode')
        if error_code == 2:
            self.raise_login_required(method='cookies')
        elif error_code is not None:
            msg = f'Panopto said: {response.get("ErrorMessage")}'
            if fatal:
                raise ExtractorError(msg, video_id=video_id, expected=True)
            else:
                self.report_warning(msg, video_id=video_id)
        return response

    @staticmethod
    def _parse_fragment(url):
        return {k: json.loads(v[0]) for k, v in compat_urlparse.parse_qs(compat_urllib_parse_urlparse(url).fragment).items()}

    @staticmethod
    def _extract_urls(webpage):
        return [m.group('url') for m in re.finditer(
            r'<iframe[^>]+src=["\'](?P<url>%s/Pages/(Viewer|Embed|Sessions/List)\.aspx[^"\']+)' % PanoptoIE.BASE_URL_RE,
            webpage)]


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
                'average_rating': int,
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
                'average_rating': int,
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
                'average_rating': int,
                'uploader': 'Kathryn Kelly',
                'channel_id': 'fb93bc3c-6750-4b80-a05b-a921013735d3',
                'channel': 'Getting Started',
            }
        },
        {
            # Does not allow normal Viewer.aspx. AUDIO livestream has no url, so should be skipped and only give one stream.
            'url': 'https://unisa.au.panopto.com/Panopto/Pages/Embed.aspx?id=9d9a0fa3-e99a-4ebd-a281-aac2017f4da4',
            'info_dict': {
                'id': '9d9a0fa3-e99a-4ebd-a281-aac2017f4da4',
                'ext': 'mp4',
                'cast': ['LTS CLI Script'],
                'duration': 2178.45,
                'description': 'md5:ee5cf653919f55b72bce2dbcf829c9fa',
                'channel_id': 'b23e673f-c287-4cb1-8344-aae9005a69f8',
                'average_rating': int,
                'uploader_id': '38377323-6a23-41e2-9ff6-a8e8004bf6f7',
                'uploader': 'LTS CLI Script',
                'timestamp': 1572458134,
                'title': 'WW2 Vets Interview 3 Ronald Stanley George',
                'thumbnail': r're:https://unisa\.au\.panopto\.com/Panopto/Services/FrameGrabber.svc/FrameRedirect\?objectId=9d9a0fa3-e99a-4ebd-a281-aac2017f4da4&mode=Delivery&random=[\d.]+',
                'channel': 'World War II Veteran Interviews',
                'upload_date': '20191030',
            },
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

    def _mark_watched(self, base_url, video_id, delivery_info):
        duration = traverse_obj(delivery_info, ('Delivery', 'Duration'), expected_type=float)
        invocation_id = delivery_info.get('InvocationId')
        stream_id = traverse_obj(delivery_info, ('Delivery', 'Streams', ..., 'PublicID'), get_all=False, expected_type=str)
        if invocation_id and stream_id and duration:
            timestamp_str = f'/Date({calendar.timegm(datetime.utcnow().timetuple())}000)/'
            data = {
                'streamRequests': [
                    {
                        'ClientTimeStamp': timestamp_str,
                        'ID': 0,
                        'InvocationID': invocation_id,
                        'PlaybackSpeed': 1,
                        'SecondsListened': duration - 1,
                        'SecondsRejected': 0,
                        'StartPosition': 0,
                        'StartReason': 2,
                        'StopReason': None,
                        'StreamID': stream_id,
                        'TimeStamp': timestamp_str,
                        'UpdatesRejected': 0
                    },
                ]}

            self._download_webpage(
                base_url + '/Services/Analytics.svc/AddStreamRequests', video_id,
                fatal=False, data=json.dumps(data).encode('utf8'), headers={'content-type': 'application/json'},
                note='Marking watched', errnote='Unable to mark watched')

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

    def _extract_streams_formats_and_subtitles(self, video_id, streams, **fmt_kwargs):
        formats = []
        subtitles = {}
        for stream in streams or []:
            stream_formats = []
            http_stream_url = stream.get('StreamHttpUrl')
            stream_url = stream.get('StreamUrl')

            if http_stream_url:
                stream_formats.append({'url': http_stream_url})

            if stream_url:
                media_type = stream.get('ViewerMediaFileTypeName')
                if media_type in ('hls', ):
                    m3u8_formats, stream_subtitles = self._extract_m3u8_formats_and_subtitles(stream_url, video_id)
                    stream_formats.extend(m3u8_formats)
                    subtitles = self._merge_subtitles(subtitles, stream_subtitles)
                else:
                    stream_formats.append({
                        'url': stream_url
                    })
            for fmt in stream_formats:
                fmt.update({
                    'format_note': stream.get('Tag'),
                    **fmt_kwargs
                })
            formats.extend(stream_formats)

        return formats, subtitles

    def _real_extract(self, url):
        base_url, video_id = self._match_valid_url(url).group('base_url', 'id')
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
        session_start_time = int_or_none(delivery.get('SessionStartTime'))

        # Podcast stream is usually the combined streams. We will prefer that by default.
        podcast_formats, podcast_subtitles = self._extract_streams_formats_and_subtitles(
            video_id, delivery.get('PodcastStreams'), format_note='PODCAST')

        streams_formats, streams_subtitles = self._extract_streams_formats_and_subtitles(
            video_id, delivery.get('Streams'), preference=-10)

        formats = podcast_formats + streams_formats
        subtitles = self._merge_subtitles(podcast_subtitles, streams_subtitles)
        self._sort_formats(formats)

        self.mark_watched(base_url, video_id, delivery_info)

        return {
            'id': video_id,
            'title': delivery.get('SessionName'),
            'cast': traverse_obj(delivery, ('Contributors', ..., 'DisplayName'), default=[], expected_type=lambda x: x or None),
            'timestamp': session_start_time - 11640000000 if session_start_time else None,
            'duration': delivery.get('Duration'),
            'thumbnail': base_url + f'/Services/FrameGrabber.svc/FrameRedirect?objectId={video_id}&mode=Delivery&random={random()}',
            'average_rating': delivery.get('AverageRating'),
            'chapters': self._extract_chapters(delivery) or None,
            'uploader': delivery.get('OwnerDisplayName') or None,
            'uploader_id': delivery.get('OwnerId'),
            'description': delivery.get('SessionAbstract'),
            'tags': traverse_obj(delivery, ('Tags', ..., 'Content')),
            'channel_id': delivery.get('SessionGroupPublicID'),
            'channel': traverse_obj(delivery, 'SessionGroupLongName', 'SessionGroupShortName', get_all=False),
            'formats': formats,
            'subtitles': subtitles
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
        },
        {
            'url': 'https://utsa.hosted.panopto.com/Panopto/Pages/Viewer.aspx?pid=e2900555-3ad4-4bdb-854d-ad2401686190',
            'info_dict': {
                'title': 'Library Website Introduction Playlist',
                'id': 'e2900555-3ad4-4bdb-854d-ad2401686190',
                'description': 'md5:f958bca50a1cbda15fdc1e20d32b3ecb',
            },
            'playlist_mincount': 4
        },

    ]

    def _entries(self, base_url, playlist_id, session_list_id):
        session_list_info = self._call_api(
            base_url, f'/Api/SessionLists/{session_list_id}?collections[0].maxCount=500&collections[0].name=items', playlist_id)

        items = session_list_info['Items']
        for item in items:
            if item.get('TypeName') != 'Session':
                self.report_warning('Got an item in the playlist that is not a Session' + bug_reports_message(), only_once=True)
                continue
            yield {
                '_type': 'url',
                'id': item.get('Id'),
                'url': item.get('ViewerUri'),
                'title': item.get('Name'),
                'description': item.get('Description'),
                'duration': item.get('Duration'),
                'channel': traverse_obj(item, ('Parent', 'Name')),
                'channel_id': traverse_obj(item, ('Parent', 'Id'))
            }

    def _real_extract(self, url):
        base_url, playlist_id = self._match_valid_url(url).group('base_url', 'id')

        video_id = get_first(parse_qs(url), 'id')
        if video_id:
            if self.get_param('noplaylist'):
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)
                return self.url_result(base_url + f'/Pages/Viewer.aspx?id={video_id}', ie_key=PanoptoIE.ie_key(), video_id=video_id)
            else:
                self.to_screen(f'Downloading playlist {playlist_id}; add --no-playlist to just download video {video_id}')

        playlist_info = self._call_api(base_url, f'/Api/Playlists/{playlist_id}', playlist_id)
        return self.playlist_result(
            self._entries(base_url, playlist_id, playlist_info['SessionListId']),
            playlist_id=playlist_id, playlist_title=playlist_info.get('Name'),
            playlist_description=playlist_info.get('Description'))


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
                'id': 'panopto_list',
                'title': 'panopto_list'
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
            base_url, '/Services/Data.svc/GetSessions', f'{display_id} page {page+1}',
            data={'queryParameters': params}, fatal=False)

        for result in get_first(response, 'Results', default=[]):
            # This could be a video, playlist (or maybe something else)
            item_id = result.get('DeliveryID')
            yield {
                '_type': 'url',
                'id': item_id,
                'title': result.get('SessionName'),
                'url': traverse_obj(result, 'ViewerUrl', 'EmbedUrl', get_all=False) or (base_url + f'/Pages/Viewer.aspx?id={item_id}'),
                'duration': result.get('Duration'),
                'channel': result.get('FolderName'),
                'channel_id': result.get('FolderID'),
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
            'title': get_first(response, 'Name', default=[])
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        base_url = mobj.group('base_url')

        query_params = self._parse_fragment(url)
        folder_id, display_id = query_params.get('folderID'), 'panopto_list'

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

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    filter_dict,
    get_element_by_class,
    get_element_html_by_id,
    int_or_none,
    mimetype2ext,
    parse_duration,
    str_or_none,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj, value


class GoogleDriveIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                            (?:
                                (?:docs|drive|drive\.usercontent)\.google\.com/
                                (?:
                                    (?:uc|open|download)\?.*?id=|
                                    file/d/
                                )|
                                video\.google\.com/get_player\?.*?docid=
                            )
                            (?P<id>[a-zA-Z0-9_-]{28,})
                    '''
    _TESTS = [{
        'url': 'https://drive.google.com/file/d/0ByeS4oOUV-49Zzh4R1J6R09zazQ/edit?pli=1',
        'md5': '5c602afbbf2c1db91831f5d82f678554',
        'info_dict': {
            'id': '0ByeS4oOUV-49Zzh4R1J6R09zazQ',
            'ext': 'mp4',
            'title': 'Big Buck Bunny.mp4',
            'duration': 45.069,
            'thumbnail': r're:https://lh3\.googleusercontent\.com/drive-storage/',
        },
    }, {
        # has itag 50 which is not in YoutubeIE._formats (royalty Free music from 1922)
        'url': 'https://drive.google.com/uc?id=1IP0o8dHcQrIHGgVyp0Ofvx2cGfLzyO1x',
        'md5': '322db8d63dd19788c04050a4bba67073',
        'info_dict': {
            'id': '1IP0o8dHcQrIHGgVyp0Ofvx2cGfLzyO1x',
            'ext': 'mp3',
            'title': 'My Buddy - Henry Burr - Gus Kahn - Walter Donaldson.mp3',
            'duration': 184.68,
        },
    }, {
        # Has subtitle track
        'url': 'https://drive.google.com/file/d/1RAGWRgzn85TXCaCk4gxnwF6TGUaZatzE/view',
        'md5': '05488c528da6ef737ec8c962bfa9724e',
        'info_dict': {
            'id': '1RAGWRgzn85TXCaCk4gxnwF6TGUaZatzE',
            'ext': 'mp4',
            'title': 'test.mp4',
            'duration': 9.999,
            'thumbnail': r're:https://lh3\.googleusercontent\.com/drive-storage/',
        },
    }, {
        # Has subtitle track with kind 'asr'
        'url': 'https://drive.google.com/file/d/1Prvv9-mtDDfN_gkJgtt1OFvIULK8c3Ev/view',
        'md5': 'ccae12d07f18b5988900b2c8b92801fc',
        'info_dict': {
            'id': '1Prvv9-mtDDfN_gkJgtt1OFvIULK8c3Ev',
            'ext': 'mp4',
            'title': 'LEE NA GYUNG-3410-VOICE_MESSAGE.mp4',
            'duration': 8.766,
            'thumbnail': r're:https://lh3\.googleusercontent\.com/drive-storage/',
        },
    }, {
        # video can't be watched anonymously due to view count limit reached,
        # but can be downloaded (see https://github.com/ytdl-org/youtube-dl/issues/14046)
        'url': 'https://drive.google.com/file/d/0B-vUyvmDLdWDcEt4WjBqcmI2XzQ/view',
        'only_matching': True,
    }, {
        # video id is longer than 28 characters
        'url': 'https://drive.google.com/file/d/1ENcQ_jeCuj7y19s66_Ou9dRP4GKGsodiDQ/edit',
        'only_matching': True,
    }, {
        'url': 'https://drive.google.com/open?id=0B2fjwgkl1A_CX083Tkowdmt6d28',
        'only_matching': True,
    }, {
        'url': 'https://drive.google.com/uc?id=0B2fjwgkl1A_CX083Tkowdmt6d28',
        'only_matching': True,
    }, {
        'url': 'https://drive.usercontent.google.com/download?id=0ByeS4oOUV-49Zzh4R1J6R09zazQ',
        'only_matching': True,
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        mobj = re.search(
            r'<iframe[^>]+src="https?://(?:video\.google\.com/get_player\?.*?docid=|(?:docs|drive)\.google\.com/file/d/)(?P<id>[a-zA-Z0-9_-]{28,})',
            webpage)
        if mobj:
            yield 'https://drive.google.com/file/d/{}'.format(mobj.group('id'))

    @staticmethod
    def _construct_subtitle_url(base_url, video_id, language, fmt, kind):
        return update_url_query(
            base_url, filter_dict({
                'hl': 'en-US',
                'v': video_id,
                'type': 'track',
                'lang': language,
                'fmt': fmt,
                'kind': kind,
            }))

    def _get_subtitles(self, video_id, video_info):
        subtitles = {}
        timed_text_base_url = traverse_obj(video_info, ('timedTextDetails', 'timedTextBaseUrl', {url_or_none}))
        if not timed_text_base_url:
            return subtitles
        subtitle_data = self._download_xml(
            timed_text_base_url, video_id, 'Downloading subtitles XML', fatal=False, query={
                'hl': 'en-US',
                'type': 'list',
                'tlangs': 1,
                'v': video_id,
                'vssids': 1,
            })
        subtitle_formats = traverse_obj(subtitle_data, (lambda _, v: v.tag == 'format', {lambda x: x.get('fmt_code')}, {str}))
        for track in traverse_obj(subtitle_data, (lambda _, v: v.tag == 'track' and v.get('lang_code'))):
            language = track.get('lang_code')
            subtitles.setdefault(language, []).extend([{
                'url': self._construct_subtitle_url(
                    timed_text_base_url, video_id, language, sub_fmt, track.get('kind')),
                'name': track.get('lang_original'),
                'ext': sub_fmt,
            } for sub_fmt in subtitle_formats])
        return subtitles

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(
            f'https://content-workspacevideo-pa.googleapis.com/v1/drive/media/{video_id}/playback',
            video_id, 'Downloading video webpage', query={'key': 'AIzaSyDVQw45DwoYh632gvsP5vPDqEKvb-Ywnb8'},
            headers={'Referer': 'https://drive.google.com/'})

        formats = []
        for fmt in traverse_obj(video_info, (
                'mediaStreamingData', 'formatStreamingData', ('adaptiveTranscodes', 'progressiveTranscodes'),
                lambda _, v: url_or_none(v['url']))):
            formats.append({
                **traverse_obj(fmt, {
                    'url': 'url',
                    'format_id': ('itag', {int}, {str_or_none}),
                }),
                **traverse_obj(fmt, ('transcodeMetadata', {
                    'ext': ('mimeType', {mimetype2ext}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'fps': ('videoFps', {int_or_none}),
                    'filesize': ('contentLength', {int_or_none}),
                    'vcodec': ((('videoCodecString', {str}), {value('none')}), any),
                    'acodec': ((('audioCodecString', {str}), {value('none')}), any),
                })),
                'downloader_options': {
                    'http_chunk_size': 10 << 20,
                },
            })

        title = traverse_obj(video_info, ('mediaMetadata', 'title', {str}))

        source_url = update_url_query(
            'https://drive.usercontent.google.com/download', {
                'id': video_id,
                'export': 'download',
                'confirm': 't',
            })

        def request_source_file(source_url, kind, data=None):
            return self._request_webpage(
                source_url, video_id, note=f'Requesting {kind} file',
                errnote=f'Unable to request {kind} file', fatal=False, data=data)
        urlh = request_source_file(source_url, 'source')
        if urlh:
            def add_source_format(urlh):
                nonlocal title
                if not title:
                    title = self._search_regex(
                        r'\bfilename="([^"]+)"', urlh.headers.get('Content-Disposition'),
                        'title', default=None)
                formats.append({
                    # Use redirect URLs as download URLs in order to calculate
                    # correct cookies in _calc_cookies.
                    # Using original URLs may result in redirect loop due to
                    # google.com's cookies mistakenly used for googleusercontent.com
                    # redirect URLs (see #23919).
                    'url': urlh.url,
                    'ext': determine_ext(title, 'mp4').lower(),
                    'format_id': 'source',
                    'quality': 1,
                })
            if urlh.headers.get('Content-Disposition'):
                add_source_format(urlh)
            else:
                confirmation_webpage = self._webpage_read_content(
                    urlh, url, video_id, note='Downloading confirmation page',
                    errnote='Unable to confirm download', fatal=False)
                if confirmation_webpage:
                    confirmed_source_url = extract_attributes(
                        get_element_html_by_id('download-form', confirmation_webpage) or '').get('action')
                    if confirmed_source_url:
                        urlh = request_source_file(confirmed_source_url, 'confirmed source', data=b'')
                        if urlh and urlh.headers.get('Content-Disposition'):
                            add_source_format(urlh)
                    else:
                        self.report_warning(
                            get_element_by_class('uc-error-subcaption', confirmation_webpage)
                            or get_element_by_class('uc-error-caption', confirmation_webpage)
                            or 'unable to extract confirmation code')

        return {
            'id': video_id,
            'title': title,
            **traverse_obj(video_info, {
                'duration': ('mediaMetadata', 'duration', {parse_duration}),
                'thumbnails': ('thumbnails', lambda _, v: url_or_none(v['url']), {
                    'url': 'url',
                    'ext': ('mimeType', {mimetype2ext}),
                    'width': ('width', {int}),
                    'height': ('height', {int}),
                }),
            }),
            'formats': formats,
            'subtitles': self.extract_subtitles(video_id, video_info),
        }


class GoogleDriveFolderIE(InfoExtractor):
    IE_NAME = 'GoogleDrive:Folder'
    _VALID_URL = r'https?://(?:docs|drive)\.google\.com/drive/folders/(?P<id>[\w-]{28,})'
    _TESTS = [{
        'url': 'https://drive.google.com/drive/folders/1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI',
        'info_dict': {
            'id': '1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI',
            'title': 'Forrest',
        },
        'playlist_count': 3,
    }]
    _BOUNDARY = '=====vc17a3rwnndj====='
    _REQUEST = "/drive/v2beta/files?openDrive=true&reason=102&syncType=0&errorRecovery=false&q=trashed%20%3D%20false%20and%20'{folder_id}'%20in%20parents&fields=kind%2CnextPageToken%2Citems(kind%2CmodifiedDate%2CmodifiedByMeDate%2ClastViewedByMeDate%2CfileSize%2Cowners(kind%2CpermissionId%2Cid)%2ClastModifyingUser(kind%2CpermissionId%2Cid)%2ChasThumbnail%2CthumbnailVersion%2Ctitle%2Cid%2CresourceKey%2Cshared%2CsharedWithMeDate%2CuserPermission(role)%2CexplicitlyTrashed%2CmimeType%2CquotaBytesUsed%2Ccopyable%2CfileExtension%2CsharingUser(kind%2CpermissionId%2Cid)%2Cspaces%2Cversion%2CteamDriveId%2ChasAugmentedPermissions%2CcreatedDate%2CtrashingUser(kind%2CpermissionId%2Cid)%2CtrashedDate%2Cparents(id)%2CshortcutDetails(targetId%2CtargetMimeType%2CtargetLookupStatus)%2Ccapabilities(canCopy%2CcanDownload%2CcanEdit%2CcanAddChildren%2CcanDelete%2CcanRemoveChildren%2CcanShare%2CcanTrash%2CcanRename%2CcanReadTeamDrive%2CcanMoveTeamDriveItem)%2Clabels(starred%2Ctrashed%2Crestricted%2Cviewed))%2CincompleteSearch&appDataFilter=NO_APP_DATA&spaces=drive&pageToken={page_token}&maxResults=50&supportsTeamDrives=true&includeItemsFromAllDrives=true&corpora=default&orderBy=folder%2Ctitle_natural%20asc&retryCount=0&key={key} HTTP/1.1"
    _DATA = f'''--{_BOUNDARY}
content-type: application/http
content-transfer-encoding: binary

GET %s

--{_BOUNDARY}
'''

    def _call_api(self, folder_id, key, data, **kwargs):
        response = self._download_webpage(
            'https://clients6.google.com/batch/drive/v2beta',
            folder_id, data=data.encode(),
            headers={
                'Content-Type': 'text/plain;charset=UTF-8;',
                'Origin': 'https://drive.google.com',
            }, query={
                '$ct': f'multipart/mixed; boundary="{self._BOUNDARY}"',
                'key': key,
            }, **kwargs)
        return self._search_json('', response, 'api response', folder_id, **kwargs) or {}

    def _get_folder_items(self, folder_id, key):
        page_token = ''
        while page_token is not None:
            request = self._REQUEST.format(folder_id=folder_id, page_token=page_token, key=key)
            page = self._call_api(folder_id, key, self._DATA % request)
            yield from page['items']
            page_token = page.get('nextPageToken')

    def _real_extract(self, url):
        folder_id = self._match_id(url)

        webpage = self._download_webpage(url, folder_id)
        key = self._search_regex(r'"(\w{39})"', webpage, 'key')

        folder_info = self._call_api(folder_id, key, self._DATA % f'/drive/v2beta/files/{folder_id} HTTP/1.1', fatal=False)

        return self.playlist_from_matches(
            self._get_folder_items(folder_id, key), folder_id, folder_info.get('title'),
            ie=GoogleDriveIE, getter=lambda item: f'https://drive.google.com/file/d/{item["id"]}')

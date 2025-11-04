import re
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    extract_attributes,
    filter_dict,
    get_element_by_class,
    get_element_html_by_id,
    int_or_none,
    js_to_json,
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
        # shortcut url
        'url': 'https://drive.google.com/file/d/1_n3-8ZwEUV4OniMsLAJ_C1JEjuT2u5Pk/view?usp=drivesdk',
        'md5': '43d34f7be1acc0262f337a039d1ad12d',
        'info_dict': {
            'id': '1J1RCw2jcgUngrZRdpza-IHXYkardZ-4l',
            'ext': 'webm',
            'title': 'Forrest walk with Best Mind Refresh Music Mithran [tEvJKrE4cS0].webm',
            'duration': 512,
            'thumbnail': 'https://drive.google.com/thumbnail?id=1J1RCw2jcgUngrZRdpza-IHXYkardZ-4l',
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
        try:
            _, webpage_urlh = self._download_webpage_handle(url, video_id)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                if e.cause.status in (401, 403):
                    self.raise_login_required('Access Denied')
                raise
        if webpage_urlh.url != url:
            url = webpage_urlh.url
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
    _VALID_URL = r'https?://(?:docs|drive)\.google\.com/drive/(?:folders/(?P<id>[\w-]{19,})|my-drive)'
    _TESTS = [{
        'url': 'https://drive.google.com/drive/folders/1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI',
        'info_dict': {
            'id': '1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI',
            'title': 'Forrest',
        },
        'playlist_count': 3,
    }, {
        'note': 'Contains various formats and a subfolder, folder name was formerly mismatched.'
                'also contains loop shortcut, shortcut to non-downloadable files, etc.',
        'url': 'https://docs.google.com/drive/folders/1jjrhqi94d8TSHSVMSdBjD49MOiHYpHfF',
        'info_dict': {
            'id': '1jjrhqi94d8TSHSVMSdBjD49MOiHYpHfF',
            'title': '], sideChannel: {}});',
        },
        'playlist_count': 8,
    }]

    def _extract_json_meta(self, webpage, video_id, dsval=None, hashval=None, name=None, **kwargs):
        """
        Uses regex to search for json metadata with 'ds' value(0-5) or 'hash' value(1-6)
        from the webpage.
            logged out  folder info:ds0hash1;          items (old):ds4hash6
            logged in   folder info:ds0hash1;          items (old):ds5hash6
            my-drive    folder info:ds0hash1/ds0hash4; items (old):ds5hash6
        For example, if the webpage contains the line below, the empty data array
        can be got by passing dsval=3 or hashval=2 to this method.
            AF_initDataCallback({key: 'ds:3', hash: '2', data:[], sideChannel: {}});
        """
        _ARRAY_RE = r'\[(?s:.+)\]'
        _META_END_RE = r', sideChannel: \{\}\}\);'  # greedy match to deal with the 2nd test case
        if dsval is not None:
            if not name:
                name = f'webpage JSON metadata ds:{dsval}'
            return self._search_json(
                rf'''key\s*?:\s*?(['"])ds:\s*?{dsval}\1,[^\[]*?data:''', webpage, name, video_id,
                end_pattern=_META_END_RE, contains_pattern=_ARRAY_RE, **kwargs)
        elif hashval is not None:
            if not name:
                name = f'webpage JSON metadata hash:{hashval}'
            return self._search_json(
                rf'''hash\s*?:\s*?(['"]){hashval}\1,[^\[]*?data:''', webpage, name, video_id,
                end_pattern=_META_END_RE, contains_pattern=_ARRAY_RE, **kwargs)

    def _real_extract(self, url):
        def item_url_getter(item, video_id):
            if not isinstance(item, list):
                return None
            available_IEs = (GoogleDriveFolderIE, GoogleDriveIE)  # subfolder or item
            if 'application/vnd.google-apps.shortcut' in item:  # extract real link
                entry_url = traverse_obj(
                    item,
                    (..., ..., lambda _, v: any(ie.suitable(v) for ie in available_IEs), any))
            else:
                entry_url = traverse_obj(
                    item,
                    (lambda _, v: any(ie.suitable(v) for ie in available_IEs), any))
            if not entry_url:
                return None
            return self.url_result(entry_url, video_id=video_id, video_title=traverse_obj(item, 2))

        folder_id = self._match_id(url) or 'my-drive'
        headers = self.geo_verification_headers()

        try:
            webpage, urlh = self._download_webpage_handle(url, folder_id, headers=headers)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                if e.cause.status == 404:
                    self.raise_no_formats(e.cause.msg, expected=True)
                elif e.cause.status == 403:
                    # logged in with an account without access
                    self.raise_login_required('Access Denied')
            raise
        if urllib.parse.urlparse(urlh.url).netloc == 'accounts.google.com':
            # not logged in when visiting a private folder
            self.raise_login_required('Access Denied')

        title = self._extract_json_meta(webpage, folder_id, dsval=0, name='folder info')[1][2]
        items = (
            self._extract_json_meta(webpage, folder_id, hashval=6, name='folder items', default=[None])[-1]
            or self._parse_json(self._search_json(
                r'''window\['_DRIVE_ivd'\]\s*=''', webpage, 'folder items', folder_id,
                contains_pattern="'[^']+'", transform_source=js_to_json), folder_id)[0])

        if not items:  # empty folder, False or None
            return self.playlist_result([], folder_id, title)

        return self.playlist_result(
            (entry for item in items if (entry := item_url_getter(item, folder_id))),
            folder_id, title)

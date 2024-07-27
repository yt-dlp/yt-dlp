import re
import urllib.parse

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    bug_reports_message,
    determine_ext,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    int_or_none,
    lowercase_escape,
    traverse_obj,
    try_get,
    update_url_query,
)


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
            'duration': 45,
            'thumbnail': 'https://drive.google.com/thumbnail?id=0ByeS4oOUV-49Zzh4R1J6R09zazQ',
        },
    }, {
        # has itag 50 which is not in YoutubeIE._formats (royalty Free music from 1922)
        'url': 'https://drive.google.com/uc?id=1IP0o8dHcQrIHGgVyp0Ofvx2cGfLzyO1x',
        'md5': '322db8d63dd19788c04050a4bba67073',
        'info_dict': {
            'id': '1IP0o8dHcQrIHGgVyp0Ofvx2cGfLzyO1x',
            'ext': 'mp3',
            'title': 'My Buddy - Henry Burr - Gus Kahn - Walter Donaldson.mp3',
            'duration': 184,
            'thumbnail': 'https://drive.google.com/thumbnail?id=1IP0o8dHcQrIHGgVyp0Ofvx2cGfLzyO1x',
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
    _FORMATS_EXT = {
        **{k: v['ext'] for k, v in YoutubeIE._formats.items() if v.get('ext')},
        '50': 'm4a',
    }
    _BASE_URL_CAPTIONS = 'https://drive.google.com/timedtext'
    _CAPTIONS_ENTRY_TAG = {
        'subtitles': 'track',
        'automatic_captions': 'target',
    }
    _caption_formats_ext = []
    _captions_xml = None

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        mobj = re.search(
            r'<iframe[^>]+src="https?://(?:video\.google\.com/get_player\?.*?docid=|(?:docs|drive)\.google\.com/file/d/)(?P<id>[a-zA-Z0-9_-]{28,})',
            webpage)
        if mobj:
            yield 'https://drive.google.com/file/d/{}'.format(mobj.group('id'))

    def _download_subtitles_xml(self, video_id, subtitles_id, hl):
        if self._captions_xml:
            return
        self._captions_xml = self._download_xml(
            self._BASE_URL_CAPTIONS, video_id, query={
                'id': video_id,
                'vid': subtitles_id,
                'hl': hl,
                'v': video_id,
                'type': 'list',
                'tlangs': '1',
                'fmts': '1',
                'vssids': '1',
            }, note='Downloading subtitles XML',
            errnote='Unable to download subtitles XML', fatal=False)
        if self._captions_xml:
            for f in self._captions_xml.findall('format'):
                if f.attrib.get('fmt_code') and not f.attrib.get('default'):
                    self._caption_formats_ext.append(f.attrib['fmt_code'])

    def _get_captions_by_type(self, video_id, subtitles_id, caption_type,
                              origin_lang_code=None):
        if not subtitles_id or not caption_type:
            return
        captions = {}
        for caption_entry in self._captions_xml.findall(
                self._CAPTIONS_ENTRY_TAG[caption_type]):
            caption_lang_code = caption_entry.attrib.get('lang_code')
            if not caption_lang_code:
                continue
            caption_format_data = []
            for caption_format in self._caption_formats_ext:
                query = {
                    'vid': subtitles_id,
                    'v': video_id,
                    'fmt': caption_format,
                    'lang': (caption_lang_code if origin_lang_code is None
                             else origin_lang_code),
                    'type': 'track',
                    'name': '',
                    'kind': '',
                }
                if origin_lang_code is not None:
                    query.update({'tlang': caption_lang_code})
                caption_format_data.append({
                    'url': update_url_query(self._BASE_URL_CAPTIONS, query),
                    'ext': caption_format,
                })
            captions[caption_lang_code] = caption_format_data
        return captions

    def _get_subtitles(self, video_id, subtitles_id, hl):
        if not subtitles_id or not hl:
            return
        self._download_subtitles_xml(video_id, subtitles_id, hl)
        if not self._captions_xml:
            return
        return self._get_captions_by_type(video_id, subtitles_id, 'subtitles')

    def _get_automatic_captions(self, video_id, subtitles_id, hl):
        if not subtitles_id or not hl:
            return
        self._download_subtitles_xml(video_id, subtitles_id, hl)
        if not self._captions_xml:
            return
        track = self._captions_xml.find('track')
        if track is None:
            return
        origin_lang_code = track.attrib.get('lang_code')
        if not origin_lang_code:
            return
        return self._get_captions_by_type(
            video_id, subtitles_id, 'automatic_captions', origin_lang_code)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        _, webpage_urlh = self._download_webpage_handle(url, video_id)
        if webpage_urlh.url != url:
            return self.url_result(webpage_urlh.url)

        video_info = urllib.parse.parse_qs(self._download_webpage(
            'https://drive.google.com/get_video_info',
            video_id, 'Downloading video webpage', query={'docid': video_id}))

        def get_value(key):
            return try_get(video_info, lambda x: x[key][0])

        reason = get_value('reason')
        title = get_value('title')

        formats = []
        fmt_stream_map = (get_value('fmt_stream_map') or '').split(',')
        fmt_list = (get_value('fmt_list') or '').split(',')
        if fmt_stream_map and fmt_list:
            resolutions = {}
            for fmt in fmt_list:
                mobj = re.search(
                    r'^(?P<format_id>\d+)/(?P<width>\d+)[xX](?P<height>\d+)', fmt)
                if mobj:
                    resolutions[mobj.group('format_id')] = (
                        int(mobj.group('width')), int(mobj.group('height')))

            for fmt_stream in fmt_stream_map:
                fmt_stream_split = fmt_stream.split('|')
                if len(fmt_stream_split) < 2:
                    continue
                format_id, format_url = fmt_stream_split[:2]
                ext = self._FORMATS_EXT.get(format_id)
                if not ext:
                    self.report_warning(f'Unknown format {format_id}{bug_reports_message()}')
                f = {
                    'url': lowercase_escape(format_url),
                    'format_id': format_id,
                    'ext': ext,
                }
                resolution = resolutions.get(format_id)
                if resolution:
                    f.update({
                        'width': resolution[0],
                        'height': resolution[1],
                    })
                formats.append(f)

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

        if not formats and reason:
            if title:
                self.raise_no_formats(reason, expected=True)
            else:
                raise ExtractorError(reason, expected=True)

        hl = get_value('hl')
        subtitles_id = None
        ttsurl = get_value('ttsurl')
        if ttsurl:
            # the video Id for subtitles will be the last value in the ttsurl
            # query string
            subtitles_id = ttsurl.encode().decode(
                'unicode_escape').split('=')[-1]

        self.cookiejar.clear(domain='.google.com', path='/', name='NID')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': 'https://drive.google.com/thumbnail?id=' + video_id,
            'duration': int_or_none(get_value('length_seconds')),
            'formats': formats,
            'subtitles': self.extract_subtitles(video_id, subtitles_id, hl),
            'automatic_captions': self.extract_automatic_captions(
                video_id, subtitles_id, hl),
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
    }, {
        # Contains various formats and a subfolder
        'url': 'https://drive.google.com/drive/folders/1CkqRsNlzZ0o3IL083j17s6sH5Q83DcGo',
        'info_dict': {
            'id': '1CkqRsNlzZ0o3IL083j17s6sH5Q83DcGo',
            'title': r'], sideChannel: {}});',
        },
        'playlist_count': 6,
    }]
    _JSON_DS_RE = r'key\s*?:\s*?([\'"])ds:\s*?%d\1,[^}]*data:'
    _JSON_HASH_RE = r'hash\s*?:\s*?([\'"])%d\1,[^}]*data:'
    _ARRAY_RE = r'\[(?s:.+)\]'

    def _extract_json_ds(self, dsval, webpage, video_id, **kwargs):
        """
        Searches for json with the 'ds' value(0~5) from the webpage with regex.
        Folder info: ds=0; Folder items: ds=4.
        For example, if the webpage contains the line below, the empty data array
        can be got by passing dsval=3 to this function.
            AF_initDataCallback({key: 'ds:3', hash: '2', data:[], sideChannel: {}});
        """
        return self._search_json(self._JSON_DS_RE % dsval, webpage,
                                 f'webpage JSON ds:{dsval}', video_id,
                                 contains_pattern=self._ARRAY_RE, **kwargs)

    def _extract_json_hash(self, hashval, webpage, video_id, **kwargs):
        """
        Searches for json with the 'hash' value(1~6) from the webpage with regex.
        Folder info: hash=1; Folder items: hash=6.
        For example, if the webpage contains the line below, the empty data array
        can be got by passing hashval=2 to this function.
            AF_initDataCallback({key: 'ds:3', hash: '2', data:[], sideChannel: {}});
        """
        return self._search_json(self._JSON_HASH_RE % hashval, webpage,
                                 f'webpage JSON hash:{hashval}', video_id,
                                 contains_pattern=self._ARRAY_RE, **kwargs)

    def _real_extract(self, url):
        def item_url_getter(item, video_id):
            available_IEs = [GoogleDriveFolderIE, GoogleDriveIE]
            if 'application/vnd.google-apps.shortcut' in item:
                entry_url = traverse_obj(
                    item, (..., ..., lambda _, v: any(ie.suitable(v) for ie in available_IEs),
                           {str}, any))
            else:
                entry_url = traverse_obj(
                    item, (lambda _, v: any(ie.suitable(v) for ie in available_IEs),
                           {str}, any))
            if not entry_url:
                return None
            return self.url_result(entry_url, video_id=video_id, video_title=item[2])

        folder_id = self._match_id(url)
        headers = self.geo_verification_headers()

        webpage = self._download_webpage(url, folder_id, headers=headers)
        json_folder_info = (
            self._extract_json_ds(0, webpage, folder_id, default=None)
            or self._extract_json_hash(1, webpage, folder_id)
        )
        json_items = (
            self._extract_json_ds(4, webpage, folder_id, default=None)
            or self._extract_json_hash(6, webpage, folder_id)
        )

        title = json_folder_info[1][2]
        items = json_items[-1]
        if not isinstance(items, list):
            return self.playlist_result([], folder_id, title)

        return self.playlist_result(
            (entry for item in items if (entry := item_url_getter(item, folder_id))),
            folder_id, title)

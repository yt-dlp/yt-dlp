# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    url_or_none,
    parse_filesize,
    urlencode_postdata
)


class ZoomIE(InfoExtractor):
    IE_NAME = 'zoom'
    _VALID_URL = r'https://(?:.*).?zoom.us/rec(?:ording)?/play/(?P<id>[A-Za-z0-9\-_]+)'

    _TEST = {
        'url': 'https://zoom.us/recording/play/SILVuCL4bFtRwWTtOCFQQxAsBQsJljFtm9e4Z_bvo-A8B-nzUSYZRNuPl3qW5IGK',
        'info_dict': {
            'md5': '031a5b379f1547a8b29c5c4c837dccf2',
            'title': "GAZ Transformational Tuesdays W/ Landon & Stapes",
            'id': "SILVuCL4bFtRwWTtOCFQQxAsBQsJljFtm9e4Z_bvo-A8B-nzUSYZRNuPl3qW5IGK",
            'ext': "mp4"
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        password_protected = self._search_regex(r'<form[^>]+?id="(password_form)"', webpage, 'password field', fatal=False, default=None)
        if password_protected is not None:
            self._verify_video_password(url, display_id, webpage)
            webpage = self._download_webpage(url, display_id)

        video_url = self._search_regex(r"viewMp4Url: \'(.*)\'", webpage, 'video url')
        title = self._html_search_regex([r"topic: \"(.*)\",", r"<title>(.*) - Zoom</title>"], webpage, 'title')
        viewResolvtionsWidth = self._search_regex(r"viewResolvtionsWidth: (\d*)", webpage, 'res width', fatal=False)
        viewResolvtionsHeight = self._search_regex(r"viewResolvtionsHeight: (\d*)", webpage, 'res height', fatal=False)
        fileSize = parse_filesize(self._search_regex(r"fileSize: \'(.+)\'", webpage, 'fileSize', fatal=False))

        urlprefix = url.split("zoom.us")[0] + "zoom.us/"

        formats = []
        formats.append({
            'url': url_or_none(video_url),
            'width': int_or_none(viewResolvtionsWidth),
            'height': int_or_none(viewResolvtionsHeight),
            'http_headers': {'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                             'Referer': urlprefix},
            'ext': "mp4",
            'filesize_approx': int_or_none(fileSize)
        })
        self._sort_formats(formats)

        return {
            'id': display_id,
            'title': title,
            'formats': formats
        }

    def _verify_video_password(self, url, video_id, webpage):
        password = self._downloader.params.get('videopassword')
        if password is None:
            raise ExtractorError('This video is protected by a password, use the --video-password option', expected=True)
        meetId = self._search_regex(r'<input[^>]+?id="meetId" value="([^\"]+)"', webpage, 'meetId')
        data = urlencode_postdata({
            'id': meetId,
            'passwd': password,
            'action': "viewdetailedpage",
            'recaptcha': ""
        })
        validation_url = url.split("zoom.us")[0] + "zoom.us/rec/validate_meet_passwd"
        validation_response = self._download_json(
            validation_url, video_id,
            note='Validating Password...',
            errnote='Wrong password?',
            data=data)

        if validation_response['errorCode'] != 0:
            raise ExtractorError('Login failed, %s said: %r' % (self.IE_NAME, validation_response['errorMessage']))

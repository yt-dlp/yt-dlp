# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    NO_DEFAULT,
    sanitized_Request,
    urlencode_postdata,
)


class VodlockerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vodlocker\.(?:com|city)/(?:embed-)?(?P<id>[0-9a-zA-Z]+)(?:\..*?)?'

    _TESTS = [{
        'url': 'http://vodlocker.com/e8wvyzz4sl42',
        'md5': 'ce0c2d18fa0735f1bd91b69b0e54aacf',
        'info_dict': {
            'id': 'e8wvyzz4sl42',
            'ext': 'mp4',
            'title': 'Germany vs Brazil',
            'thumbnail': r're:http://.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if any(p in webpage for p in (
                '>THIS FILE WAS DELETED<',
                '>File Not Found<',
                'The file you were looking for could not be found, sorry for any inconvenience.<',
                '>The file was removed')):
            raise ExtractorError('Video %s does not exist' % video_id, expected=True)

        fields = self._hidden_inputs(webpage)

        if fields['op'] == 'download1':
            self._sleep(3, video_id)  # they do detect when requests happen too fast!
            post = urlencode_postdata(fields)
            req = sanitized_Request(url, post)
            req.add_header('Content-type', 'application/x-www-form-urlencoded')
            webpage = self._download_webpage(
                req, video_id, 'Downloading video page')

        def extract_file_url(html, default=NO_DEFAULT):
            return self._search_regex(
                r'file:\s*"(http[^\"]+)",', html, 'file url', default=default)

        video_url = extract_file_url(webpage, default=None)

        if not video_url:
            embed_url = self._search_regex(
                r'<iframe[^>]+src=(["\'])(?P<url>(?:https?://)?vodlocker\.(?:com|city)/embed-.+?)\1',
                webpage, 'embed url', group='url')
            embed_webpage = self._download_webpage(
                embed_url, video_id, 'Downloading embed webpage')
            video_url = extract_file_url(embed_webpage)
            thumbnail_webpage = embed_webpage
        else:
            thumbnail_webpage = webpage

        title = self._search_regex(
            r'id="file_title".*?>\s*(.*?)\s*<(?:br|span)', webpage, 'title')
        thumbnail = self._search_regex(
            r'image:\s*"(http[^\"]+)",', thumbnail_webpage, 'thumbnail', fatal=False)

        formats = [{
            'format_id': 'sd',
            'url': video_url,
        }]

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }

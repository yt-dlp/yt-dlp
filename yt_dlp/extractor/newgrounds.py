from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    parse_duration,
    parse_filesize,
    parse_count,
    unified_timestamp,
    unified_strdate,
    RegexNotFoundError,
    ExtractorError,
)


class NewgroundsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?newgrounds\.com/(?:audio/listen|portal/view)/(?P<id>[0-9]+)(?:/format/flash)?'
    _TESTS = [{
        'url': 'https://www.newgrounds.com/audio/listen/549479',
        'md5': 'fe6033d297591288fa1c1f780386f07a',
        'info_dict': {
            'id': '549479',
            'ext': 'mp3',
            'title': 'B7 - BusMode',
            'uploader': 'Burn7',
            'timestamp': 1378878540,
            'upload_date': '20130911',
            'duration': 143,
        },
    }, {
        'url': 'https://www.newgrounds.com/portal/view/297383',
        'info_dict': {
            'id': '297383',
            'ext': 'mp4',
            'title': 'Metal Gear Awesome',
            'uploader': 'Egoraptor',
            'timestamp': 1140663240,
            'upload_date': '20060223',
        },
    }, {
        # source format unavailable, additional mp4 formats
        'url': 'http://www.newgrounds.com/portal/view/689400',
        'info_dict': {
            'id': '689400',
            'ext': 'mp4',
            'title': 'ZTV News Episode 8',
            'uploader': 'BennettTheSage',
            'timestamp': 1487965140,
            'upload_date': '20170224',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)

        webpage = self._download_webpage(url, media_id)

        title = self._html_search_regex(
            r'<title>(.+?)</title>', webpage, 'title')

        try:
            media_url = self._parse_json(self._search_regex(
                r'"url"\s*:\s*("[^"]+"),', webpage, ''), media_id)
        except RegexNotFoundError or ExtractorError:
            media_url = None
        formats = []

        if media_url:
            formats = [{
                'url': media_url,
                'format_id': 'source',
                'quality': 1,
            }]
        else:
            json_data = self._download_json('https://www.newgrounds.com/portal/video/' + media_id, media_id, headers={
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Encoding': 'gzip, deflate, br',
                'X-Requested-With': 'XMLHttpRequest',
                'Connection': 'keep-alive',
            })

            for resolution in ('360p', '720p', '1080p'):
                if resolution in json_data['sources']:
                    formats.append({
                        'url': json_data['sources'][resolution][0]['src'],
                        'format_id': resolution,
                        'height': int(resolution[:-1]),
                    })

        self._sort_formats(formats)

        uploader = self._html_search_regex(
            (r'(?s)<h4[^>]*>(.+?)</h4>.*?<em>\s*Author\s*</em>',
             r'(?:Author|Writer)\s*<a[^>]+>([^<]+)'), webpage, 'uploader',
            fatal=False)

        timestamp = self._html_search_regex(
            (r'<dt>\s*Uploaded\s*</dt>\s*<dd>([^<]+</dd>\s*<dd>[^<]+)',
             r'<dt>\s*Uploaded\s*</dt>\s*<dd>([^<]+)'), webpage, 'timestamp',
            default=None)

        upload_date = unified_strdate(timestamp)

        timestamp = unified_timestamp(timestamp)

        thumbnail = self._og_search_thumbnail(webpage)

        duration = parse_duration(self._search_regex(
            r'(?s)<dd>\s*Song\s*</dd>\s*<dd>.+?</dd>\s*<dd>([^<]+)', webpage,
            'duration', default=None))

        description = self._og_search_description(webpage)

        view_count = parse_count(self._html_search_regex(r'(?s)<dt>\s*Views\s*</dt>\s*<dd>([\d\.,]+)</dd>', webpage,
                                                         'view_count', fatal=False, default=None))

        filesize_approx = parse_filesize(self._html_search_regex(
            r'(?s)<dd>\s*Song\s*</dd>\s*<dd>(.+?)</dd>', webpage, 'filesize',
            default=None))
        if len(formats) == 1:
            formats[0]['filesize_approx'] = filesize_approx

        if '<dd>Song' in webpage:
            formats[0]['vcodec'] = 'none'
        return {
            'id': media_id,
            'title': title,
            'uploader': uploader,
            'timestamp': timestamp,
            'duration': duration,
            'formats': formats,
            'description': description,
            'thumbnail': thumbnail,
            'view_count': view_count,
            'upload_date': upload_date,
        }


class NewgroundsPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?newgrounds\.com/(?:collection|[^/]+/search/[^/]+)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.newgrounds.com/collection/cats',
        'info_dict': {
            'id': 'cats',
            'title': 'Cats',
        },
        'playlist_mincount': 45,
    }, {
        'url': 'http://www.newgrounds.com/audio/search/title/cats',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        title = self._search_regex(
            r'<title>([^>]+)</title>', webpage, 'title', default=None)

        # cut left menu
        webpage = self._search_regex(
            r'(?s)<div[^>]+\bclass=["\']column wide(.+)',
            webpage, 'wide column', default=webpage)

        entries = []
        for a, path, media_id in re.findall(
                r'(<a[^>]+href="https?://[^/]+/(audio/listen|portal/view)/([0-9]+)"[^>]+>)',
                webpage):
            a_class = extract_attributes(a).get('class')
            if a_class not in ('item-portalsubmission', 'item-audiosubmission'):
                continue
            entries.append(
                self.url_result(
                    'https://www.newgrounds.com/' + path + '/' + media_id,
                    ie=NewgroundsIE.ie_key(), video_id=media_id))

        return self.playlist_result(entries, playlist_id, title)

# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_str,
    compat_urlparse,
)
from ..utils import (
    extract_attributes,
    ExtractorError,
    get_elements_by_class,
    urlencode_postdata,
)


class EinthusanIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>einthusan\.(?:tv|com|ca))/movie/watch/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://einthusan.tv/movie/watch/9097/',
        'md5': 'ff0f7f2065031b8a2cf13a933731c035',
        'info_dict': {
            'id': '9097',
            'ext': 'mp4',
            'title': 'Ae Dil Hai Mushkil',
            'description': 'md5:33ef934c82a671a94652a9b4e54d931b',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'url': 'https://einthusan.tv/movie/watch/51MZ/?lang=hindi',
        'only_matching': True,
    }, {
        'url': 'https://einthusan.com/movie/watch/9097/',
        'only_matching': True,
    }, {
        'url': 'https://einthusan.ca/movie/watch/4E9n/?lang=hindi',
        'only_matching': True,
    }]

    # reversed from jsoncrypto.prototype.decrypt() in einthusan-PGMovieWatcher.js
    def _decrypt(self, encrypted_data, video_id):
        return self._parse_json(compat_b64decode((
            encrypted_data[:10] + encrypted_data[-1] + encrypted_data[12:-1]
        )).decode('utf-8'), video_id)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        host = mobj.group('host')
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h3>([^<]+)</h3>', webpage, 'title')

        player_params = extract_attributes(self._search_regex(
            r'(<section[^>]+id="UIVideoPlayer"[^>]+>)', webpage, 'player parameters'))

        page_id = self._html_search_regex(
            '<html[^>]+data-pageid="([^"]+)"', webpage, 'page ID')
        video_data = self._download_json(
            'https://%s/ajax/movie/watch/%s/' % (host, video_id), video_id,
            data=urlencode_postdata({
                'xEvent': 'UIVideoPlayer.PingOutcome',
                'xJson': json.dumps({
                    'EJOutcomes': player_params['data-ejpingables'],
                    'NativeHLS': False
                }),
                'arcVersion': 3,
                'appVersion': 59,
                'gorilla.csrf.Token': page_id,
            }))['Data']

        if isinstance(video_data, compat_str) and video_data.startswith('/ratelimited/'):
            raise ExtractorError(
                'Download rate reached. Please try again later.', expected=True)

        ej_links = self._decrypt(video_data['EJLinks'], video_id)

        formats = []

        m3u8_url = ej_links.get('HLSLink')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', entry_protocol='m3u8_native'))

        mp4_url = ej_links.get('MP4Link')
        if mp4_url:
            formats.append({
                'url': mp4_url,
            })

        self._sort_formats(formats)

        description = get_elements_by_class('synopsis', webpage)[0]
        thumbnail = self._html_search_regex(
            r'''<img[^>]+src=(["'])(?P<url>(?!\1).+?/moviecovers/(?!\1).+?)\1''',
            webpage, 'thumbnail url', fatal=False, group='url')
        if thumbnail is not None:
            thumbnail = compat_urlparse.urljoin(url, thumbnail)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
        }

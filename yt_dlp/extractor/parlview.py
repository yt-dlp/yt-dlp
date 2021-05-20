# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime

from .common import InfoExtractor
from ..utils import (
    HEADRequest,
    unified_timestamp,
    try_get,
)


class ParlviewIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.)?parlview\.aph\.gov\.au/(?:[^/]+)?(videoID=)+(?P<id>\d{6})'
    _TESTS = [{
        'url': 'https://parlview.aph.gov.au/mediaPlayer.php?videoID=542661',
        'info_dict': {
            'id': '542661',
            'ext': 'mp4',
            'title': "Australia's Family Law System [Part 2]",
            'description': 'md5:7099883b391619dbae435891ca871a62',
            'timestamp': 1621430700,
            'upload_date': '20210519',
            'uploader': 'Joint Committee',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://parlview.aph.gov.au/mediaPlayer.php?videoID=539936',
        'only_matching': True,
    }]
    _API_URL = 'https://parlview.aph.gov.au/api_v3/1/playback/getUniversalPlayerConfig?videoID=%s&format=json'
    _MEDIA_INFO_URL = 'https://parlview.aph.gov.au/ajaxPlayer.php?videoID=%s&tabNum=4&action=loadTab'

    def _real_extract(self, url):
        vod_id = self._match_id(url)
        _html = self._download_webpage(url, vod_id)
        _api_call = self._download_json(
            self._API_URL % vod_id, vod_id)
        _media = _api_call.get('media')
        if(len(_media.get('renditions')) == 0):
            self.raise_no_formats('No streams were detected')

        _stream = _media.get('renditions')[0]
        if(_stream.get('streamType') != 'VOD'):
            self.raise_no_formats('Unknown type of stream was detected: "%s"' % str(_stream.get('streamType')))

        m3u8_url = self._request_webpage(HEADRequest(
            _stream.get('url')), vod_id, 'Processing m3u8').geturl()
        formats = self._extract_m3u8_formats(m3u8_url, vod_id, 'mp4')
        self._sort_formats(formats)

        _timestamp = unified_timestamp(str(datetime.strptime(
            try_get(_media.get('timeMap'), lambda x: x['source']['timecode_offsets'][0], str),
            '0.0/%Y-%m-%d_%H:%M:00:00')))

        media_webpage_call = self._download_webpage(
            self._MEDIA_INFO_URL % vod_id, vod_id)

        return {
            'id': vod_id,
            'url': url,
            'title': self._search_regex(
                r'<h2>([^<]+)<',
                _html, 'title', fatal=False),
            'formats': formats,
            'timestamp': _timestamp,
            'description': self._search_regex(
                r'<div[^>]+class="descripti?on"[^>]*>[^>]+<strong>[^>]+>[^>]+>([^<]+)',
                _html, 'description').strip(),
            'uploader': self._search_regex(
                r'<td>[^>]+>Channel:[^>]+>([^<]+)', media_webpage_call, 'channel').strip(),
            'thumbnail': _media.get('staticImage')
        }

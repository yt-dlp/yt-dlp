from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    try_get,
    unified_timestamp,
)


class ParlviewIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.)?parlview\.aph\.gov\.au/(?:[^/]+)?\bvideoID=(?P<id>\d{6})'
    _TESTS = [{
        'url': 'https://parlview.aph.gov.au/mediaPlayer.php?videoID=542661',
        'info_dict': {
            'id': '542661',
            'ext': 'mp4',
            'title': "Australia's Family Law System [Part 2]",
            'duration': 5799,
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
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        media = self._download_json(self._API_URL % video_id, video_id).get('media')
        timestamp = try_get(media, lambda x: x['timeMap']['source']['timecode_offsets'][0], compat_str) or '/'

        stream = try_get(media, lambda x: x['renditions'][0], dict)
        if not stream:
            self.raise_no_formats('No streams were detected')
        elif stream.get('streamType') != 'VOD':
            self.raise_no_formats('Unknown type of stream was detected: "%s"' % str(stream.get('streamType')))
        formats = self._extract_m3u8_formats(stream['url'], video_id, 'mp4', 'm3u8_native')

        media_info = self._download_webpage(
            self._MEDIA_INFO_URL % video_id, video_id, note='Downloading media info', fatal=False)

        return {
            'id': video_id,
            'url': url,
            'title': self._html_search_regex(r'<h2>([^<]+)<', webpage, 'title', fatal=False),
            'formats': formats,
            'duration': int_or_none(media.get('duration')),
            'timestamp': unified_timestamp(timestamp.split('/', 1)[1].replace('_', ' ')),
            'description': self._html_search_regex(
                r'<div[^>]+class="descripti?on"[^>]*>[^>]+<strong>[^>]+>[^>]+>([^<]+)',
                webpage, 'description', fatal=False),
            'uploader': self._html_search_regex(
                r'<td>[^>]+>Channel:[^>]+>([^<]+)', media_info, 'channel', fatal=False),
            'thumbnail': media.get('staticImage'),
        }

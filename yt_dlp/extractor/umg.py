# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_filesize,
    parse_iso8601,
)


class UMGDeIE(InfoExtractor):
    IE_NAME = 'umg:de'
    IE_DESC = 'Universal Music Deutschland'
    _VALID_URL = r'https?://(?:www\.)?universal-music\.de/[^/]+/videos/[^/?#]+-(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.universal-music.de/sido/videos/jedes-wort-ist-gold-wert-457803',
        'md5': 'ebd90f48c80dcc82f77251eb1902634f',
        'info_dict': {
            'id': '457803',
            'ext': 'mp4',
            'title': 'Jedes Wort ist Gold wert',
            'timestamp': 1513591800,
            'upload_date': '20171218',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            'https://graphql.universal-music.de/',
            video_id, query={
                'query': '''{
  universalMusic(channel:16) {
    video(id:%s) {
      headline
      formats {
        formatId
        url
        type
        width
        height
        mimeType
        fileSize
      }
      duration
      createdDate
    }
  }
}''' % video_id})['data']['universalMusic']['video']

        title = video_data['headline']
        hls_url_template = 'http://mediadelivery.universal-music-services.de/vod/mp4:autofill/storage/' + '/'.join(list(video_id)) + '/content/%s/file/playlist.m3u8'

        thumbnails = []
        formats = []

        def add_m3u8_format(format_id):
            formats.extend(self._extract_m3u8_formats(
                hls_url_template % format_id, video_id, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False))

        for f in video_data.get('formats', []):
            f_url = f.get('url')
            mime_type = f.get('mimeType')
            if not f_url or mime_type == 'application/mxf':
                continue
            fmt = {
                'url': f_url,
                'width': int_or_none(f.get('width')),
                'height': int_or_none(f.get('height')),
                'filesize': parse_filesize(f.get('fileSize')),
            }
            f_type = f.get('type')
            if f_type == 'Image':
                thumbnails.append(fmt)
            elif f_type == 'Video':
                format_id = f.get('formatId')
                if format_id:
                    fmt['format_id'] = format_id
                    if mime_type == 'video/mp4':
                        add_m3u8_format(format_id)
                urlh = self._request_webpage(f_url, video_id, fatal=False)
                if urlh:
                    first_byte = urlh.read(1)
                    if first_byte not in (b'F', b'\x00'):
                        continue
                    formats.append(fmt)
        if not formats:
            for format_id in (867, 836, 940):
                add_m3u8_format(format_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'duration': int_or_none(video_data.get('duration')),
            'timestamp': parse_iso8601(video_data.get('createdDate'), ' '),
            'thumbnails': thumbnails,
            'formats': formats,
        }

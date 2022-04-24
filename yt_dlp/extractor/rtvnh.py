from .common import InfoExtractor
from ..utils import ExtractorError


class RTVNHIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtvnh\.nl/video/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.rtvnh.nl/video/131946',
        'md5': 'cdbec9f44550763c8afc96050fa747dc',
        'info_dict': {
            'id': '131946',
            'ext': 'mp4',
            'title': 'Grote zoektocht in zee bij Zandvoort naar vermiste vrouw',
            'thumbnail': r're:^https?:.*\.jpg$'
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        meta = self._parse_json(self._download_webpage(
            'http://www.rtvnh.nl/video/json?m=' + video_id, video_id), video_id)

        status = meta.get('status')
        if status != 200:
            raise ExtractorError(
                '%s returned error code %d' % (self.IE_NAME, status), expected=True)

        formats = []
        rtmp_formats = self._extract_smil_formats(
            'http://www.rtvnh.nl/video/smil?m=' + video_id, video_id)
        formats.extend(rtmp_formats)

        for rtmp_format in rtmp_formats:
            rtmp_url = '%s/%s' % (rtmp_format['url'], rtmp_format['play_path'])
            rtsp_format = rtmp_format.copy()
            del rtsp_format['play_path']
            del rtsp_format['ext']
            rtsp_format.update({
                'format_id': rtmp_format['format_id'].replace('rtmp', 'rtsp'),
                'url': rtmp_url.replace('rtmp://', 'rtsp://'),
                'protocol': 'rtsp',
            })
            formats.append(rtsp_format)
            http_base_url = rtmp_url.replace('rtmp://', 'http://')
            formats.extend(self._extract_m3u8_formats(
                http_base_url + '/playlist.m3u8', video_id, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False))
            formats.extend(self._extract_f4m_formats(
                http_base_url + '/manifest.f4m',
                video_id, f4m_id='hds', fatal=False))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': meta['title'].strip(),
            'thumbnail': meta.get('image'),
            'formats': formats
        }

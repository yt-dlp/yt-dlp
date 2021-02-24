from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    remove_start,
    int_or_none,
)


class BlinkxIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:www\.)blinkx\.com/#?ce/|blinkx:)(?P<id>[^?]+)'
    IE_NAME = 'blinkx'

    _TEST = {
        'url': 'http://www.blinkx.com/ce/Da0Gw3xc5ucpNduzLuDDlv4WC9PuI4fDi1-t6Y3LyfdY2SZS5Urbvn-UPJvrvbo8LTKTc67Wu2rPKSQDJyZeeORCR8bYkhs8lI7eqddznH2ofh5WEEdjYXnoRtj7ByQwt7atMErmXIeYKPsSDuMAAqJDlQZ-3Ff4HJVeH_s3Gh8oQ',
        'md5': '337cf7a344663ec79bf93a526a2e06c7',
        'info_dict': {
            'id': 'Da0Gw3xc',
            'ext': 'mp4',
            'title': 'No Daily Show for John Oliver; HBO Show Renewed - IGN News',
            'uploader': 'IGN News',
            'upload_date': '20150217',
            'timestamp': 1424215740,
            'description': 'HBO has renewed Last Week Tonight With John Oliver for two more seasons.',
            'duration': 47.743333,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        display_id = video_id[:8]

        api_url = ('https://apib4.blinkx.com/api.php?action=play_video&'
                   + 'video=%s' % video_id)
        data_json = self._download_webpage(api_url, display_id)
        data = json.loads(data_json)['api']['results'][0]
        duration = None
        thumbnails = []
        formats = []
        for m in data['media']:
            if m['type'] == 'jpg':
                thumbnails.append({
                    'url': m['link'],
                    'width': int(m['w']),
                    'height': int(m['h']),
                })
            elif m['type'] == 'original':
                duration = float(m['d'])
            elif m['type'] == 'youtube':
                yt_id = m['link']
                self.to_screen('Youtube video detected: %s' % yt_id)
                return self.url_result(yt_id, 'Youtube', video_id=yt_id)
            elif m['type'] in ('flv', 'mp4'):
                vcodec = remove_start(m['vcodec'], 'ff')
                acodec = remove_start(m['acodec'], 'ff')
                vbr = int_or_none(m.get('vbr') or m.get('vbitrate'), 1000)
                abr = int_or_none(m.get('abr') or m.get('abitrate'), 1000)
                tbr = vbr + abr if vbr and abr else None
                format_id = '%s-%sk-%s' % (vcodec, tbr, m['w'])
                formats.append({
                    'format_id': format_id,
                    'url': m['link'],
                    'vcodec': vcodec,
                    'acodec': acodec,
                    'abr': abr,
                    'vbr': vbr,
                    'tbr': tbr,
                    'width': int_or_none(m.get('w')),
                    'height': int_or_none(m.get('h')),
                })

        self._sort_formats(formats)

        return {
            'id': display_id,
            'fullid': video_id,
            'title': data['title'],
            'formats': formats,
            'uploader': data['channel_name'],
            'timestamp': data['pubdate_epoch'],
            'description': data.get('description'),
            'thumbnails': thumbnails,
            'duration': duration,
        }

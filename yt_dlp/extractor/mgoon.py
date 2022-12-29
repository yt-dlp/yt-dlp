from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    qualities,
    unified_strdate,
)


class MgoonIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?
    (?:(:?m\.)?mgoon\.com/(?:ch/(?:.+)/v|play/view)|
        video\.mgoon\.com)/(?P<id>[0-9]+)'''
    _API_URL = 'http://mpos.mgoon.com/player/video?id={0:}'
    _TESTS = [
        {
            'url': 'http://m.mgoon.com/ch/hi6618/v/5582148',
            'md5': 'dd46bb66ab35cf6d51cc812fd82da79d',
            'info_dict': {
                'id': '5582148',
                'uploader_id': 'hi6618',
                'duration': 240.419,
                'upload_date': '20131220',
                'ext': 'mp4',
                'title': 'md5:543aa4c27a4931d371c3f433e8cebebc',
                'thumbnail': r're:^https?://.*\.jpg$',
            }
        },
        {
            'url': 'http://www.mgoon.com/play/view/5582148',
            'only_matching': True,
        },
        {
            'url': 'http://video.mgoon.com/5582148',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        data = self._download_json(self._API_URL.format(video_id), video_id)

        if data.get('errorInfo', {}).get('code') != 'NONE':
            raise ExtractorError('%s encountered an error: %s' % (
                self.IE_NAME, data['errorInfo']['message']), expected=True)

        v_info = data['videoInfo']
        title = v_info.get('v_title')
        thumbnail = v_info.get('v_thumbnail')
        duration = v_info.get('v_duration')
        upload_date = unified_strdate(v_info.get('v_reg_date'))
        uploader_id = data.get('userInfo', {}).get('u_alias')
        if duration:
            duration /= 1000.0

        age_limit = None
        if data.get('accessInfo', {}).get('code') == 'VIDEO_STATUS_ADULT':
            age_limit = 18

        formats = []
        get_quality = qualities(['360p', '480p', '720p', '1080p'])
        for fmt in data['videoFiles']:
            formats.append({
                'format_id': fmt['label'],
                'quality': get_quality(fmt['label']),
                'url': fmt['url'],
                'ext': fmt['format'],

            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
            'uploader_id': uploader_id,
            'age_limit': age_limit,
        }

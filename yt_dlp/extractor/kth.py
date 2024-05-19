from .common import InfoExtractor
from ..utils import smuggle_url


class KTHIE(InfoExtractor):
    _VALID_URL = r'https?://play\.kth\.se/(?:[^/]+/)+(?P<id>[a-z0-9_]+)'
    _TEST = {
        'url': 'https://play.kth.se/media/Lunch+breakA+De+nya+aff%C3%A4rerna+inom+Fordonsdalen/0_uoop6oz9',
        'md5': 'd83ada6d00ca98b73243a88efe19e8a6',
        'info_dict': {
            'id': '0_uoop6oz9',
            'ext': 'mp4',
            'title': 'md5:bd1d6931facb6828762a33e6ce865f37',
            'thumbnail': 're:https?://.+/thumbnail/.+',
            'duration': 3516,
            'timestamp': 1647345358,
            'upload_date': '20220315',
            'uploader_id': 'md5:0ec23e33a89e795a4512930c8102509f',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        result = self.url_result(
            smuggle_url('kaltura:308:%s' % video_id, {
                'service_url': 'https://api.kaltura.nordu.net'}),
            'Kaltura')
        return result

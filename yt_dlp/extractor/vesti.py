import re

from .common import InfoExtractor
from ..utils import ExtractorError
from .rutv import RUTVIE


class VestiIE(InfoExtractor):
    IE_DESC = 'Вести.Ru'
    _VALID_URL = r'https?://(?:.+?\.)?vesti\.ru/(?P<id>.+)'

    _TESTS = [
        {
            'url': 'http://www.vesti.ru/videos?vid=575582&cid=1',
            'info_dict': {
                'id': '765035',
                'ext': 'mp4',
                'title': 'Вести.net: биткоины в России не являются законными',
                'description': 'md5:d4bb3859dc1177b28a94c5014c35a36b',
                'duration': 302,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.vesti.ru/doc.html?id=1349233',
            'info_dict': {
                'id': '773865',
                'ext': 'mp4',
                'title': 'Участники митинга штурмуют Донецкую областную администрацию',
                'description': 'md5:1a160e98b3195379b4c849f2f4958009',
                'duration': 210,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.vesti.ru/only_video.html?vid=576180',
            'info_dict': {
                'id': '766048',
                'ext': 'mp4',
                'title': 'США заморозило, Британию затопило',
                'description': 'md5:f0ed0695ec05aed27c56a70a58dc4cc1',
                'duration': 87,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://hitech.vesti.ru/news/view/id/4000',
            'info_dict': {
                'id': '766888',
                'ext': 'mp4',
                'title': 'Вести.net: интернет-гиганты начали перетягивание программных "одеял"',
                'description': 'md5:65ddd47f9830c4f42ed6475f8730c995',
                'duration': 279,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://sochi2014.vesti.ru/video/index/video_id/766403',
            'info_dict': {
                'id': '766403',
                'ext': 'mp4',
                'title': 'XXII зимние Олимпийские игры. Российские хоккеисты стартовали на Олимпиаде с победы',
                'description': 'md5:55805dfd35763a890ff50fa9e35e31b3',
                'duration': 271,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'skip': 'Blocked outside Russia',
        },
        {
            'url': 'http://sochi2014.vesti.ru/live/play/live_id/301',
            'info_dict': {
                'id': '51499',
                'ext': 'flv',
                'title': 'Сочи-2014. Биатлон. Индивидуальная гонка. Мужчины ',
                'description': 'md5:9e0ed5c9d2fa1efbfdfed90c9a6d179c',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Translation has finished'
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        page = self._download_webpage(url, video_id, 'Downloading page')

        mobj = re.search(
            r'<meta[^>]+?property="og:video"[^>]+?content="http://www\.vesti\.ru/i/flvplayer_videoHost\.swf\?vid=(?P<id>\d+)',
            page)
        if mobj:
            video_id = mobj.group('id')
            page = self._download_webpage('http://www.vesti.ru/only_video.html?vid=%s' % video_id, video_id,
                                          'Downloading video page')

        rutv_url = RUTVIE._extract_url(page)
        if rutv_url:
            return self.url_result(rutv_url, 'RUTV')

        raise ExtractorError('No video found', expected=True)

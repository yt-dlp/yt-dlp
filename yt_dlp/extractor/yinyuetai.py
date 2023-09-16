from .common import InfoExtractor
from ..utils import ExtractorError


class YinYueTaiIE(InfoExtractor):
    IE_NAME = 'yinyuetai:video'
    IE_DESC = '音悦Tai'
    _VALID_URL = r'https?://v\.yinyuetai\.com/video(?:/h5)?/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://v.yinyuetai.com/video/2322376',
        'md5': '6e3abe28d38e3a54b591f9f040595ce0',
        'info_dict': {
            'id': '2322376',
            'ext': 'mp4',
            'title': '少女时代_PARTY_Music Video Teaser',
            'creator': '少女时代',
            'duration': 25,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'http://v.yinyuetai.com/video/h5/2322376',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = self._download_json(
            'http://ext.yinyuetai.com/main/get-h-mv-info?json=true&videoId=%s' % video_id, video_id,
            'Downloading mv info')['videoInfo']['coreVideoInfo']

        if info['error']:
            raise ExtractorError(info['errorMsg'], expected=True)

        formats = [{
            'url': format_info['videoUrl'],
            'format_id': format_info['qualityLevel'],
            'format': format_info.get('qualityLevelName'),
            'filesize': format_info.get('fileSize'),
            # though URLs ends with .flv, the downloaded files are in fact mp4
            'ext': 'mp4',
            'tbr': format_info.get('bitrate'),
        } for format_info in info['videoUrlModels']]

        return {
            'id': video_id,
            'title': info['videoName'],
            'thumbnail': info.get('bigHeadImage'),
            'creator': info.get('artistNames'),
            'duration': info.get('duration'),
            'formats': formats,
        }

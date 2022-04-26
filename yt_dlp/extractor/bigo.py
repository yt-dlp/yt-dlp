from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata


class BigoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bigo\.tv/(?:[a-z]{2,}/)?(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.bigo.tv/ja/221338632',
        'info_dict': {
            'id': '6576287577575737440',
            'title': '土よ〜💁‍♂️ 休憩室/REST room',
            'thumbnail': r're:https?://.+',
            'uploader': '✨Shin💫',
            'uploader_id': '221338632',
            'is_live': True,
        },
        'skip': 'livestream',
    }, {
        'url': 'https://www.bigo.tv/th/Tarlerm1304',
        'only_matching': True,
    }, {
        'url': 'https://bigo.tv/115976881',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)

        info_raw = self._download_json(
            'https://bigo.tv/studio/getInternalStudioInfo',
            user_id, data=urlencode_postdata({'siteId': user_id}))

        if not isinstance(info_raw, dict):
            raise ExtractorError('Received invalid JSON data')
        if info_raw.get('code'):
            raise ExtractorError(
                'Bigo says: %s (code %s)' % (info_raw.get('msg'), info_raw.get('code')), expected=True)
        info = info_raw.get('data') or {}

        if not info.get('alive'):
            raise ExtractorError('This user is offline.', expected=True)

        return {
            'id': info.get('roomId') or user_id,
            'title': info.get('roomTopic') or info.get('nick_name') or user_id,
            'formats': [{
                'url': info.get('hls_src'),
                'ext': 'mp4',
                'protocol': 'm3u8',
            }],
            'thumbnail': info.get('snapshot'),
            'uploader': info.get('nick_name'),
            'uploader_id': user_id,
            'is_live': True,
        }

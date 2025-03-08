from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    smuggle_url,
    unified_timestamp,
    unsmuggle_url,
)
from ..utils.traversal import traverse_obj


class BahamutIE(InfoExtractor):
    IE_DESC = '巴哈姆特動畫瘋 ani.gamer.com.tw'
    _VALID_URL = r'https?://ani\.gamer\.com\.tw/animeVideo\.php\?sn=(?P<id>\d+)'
    _DEVICE_ID = None

    _TESTS = [{
        'url': 'https://ani.gamer.com.tw/animeVideo.php?sn=40137',
        'info_dict': {
            'id': '40137',
            'ext': 'mp4',
            'title': '膽大黨 [1]',
            'upload_date': '20241004',
            'duration': 0.38333333333333336,
            'age_limit': 12,
            'tags': ['動作', '冒險', '奇幻', '超能力', '科幻', '喜劇', '戀愛', '青春', '血腥暴力', '靈異神怪'],
            'thumbnail': 'https://p2.bahamut.com.tw/B/2KU/19/7d54e1421935f94781555420131rolv5.JPG',
            'creators': ['山代風我'],
            'timestamp': 1728000000,
            'description': 'md5:c16931fb4d24d91b858715a2560362b5',
        },
        'params': {'noplaylist': True},
        'skip': 'geo-restricted',
    }]

    # see anime_player.js
    RATING_TO_AGE_LIMIT = {
        1: 0,
        2: 6,
        3: 12,
        4: 15,
        5: 18,
        6: 18,  # age-gated, needs login
    }

    def _download_device_id(self, video_id):
        return self._download_json(
            'https://ani.gamer.com.tw/ajax/getdeviceid.php', video_id,
            note='Downloading device ID', errnote='Failed to download device ID',
            impersonate=True, headers=self.geo_verification_headers())['deviceid']

    def _real_extract(self, url):
        url, unsmuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        if not self._DEVICE_ID:
            self._DEVICE_ID = (
                self._configuration_arg('device_id', [None], casesense=True)[0]
                or self._download_device_id(video_id))

        # TODO: extract metadata from webpage
        metadata = {}
        if api_result := self._download_json(
                'https://api.gamer.com.tw/anime/v1/video.php', video_id,
                note='Downloading video info', errnote='Failed to download video info',
                impersonate=True, query={'videoSn': video_id}).get('data'):

            metadata.update(traverse_obj(api_result, ('anime', {
                'description': 'content',
                'thumbnail': 'cover',
                'tags': 'tags',
                'creators': ('director', {lambda x: [x]}),
                'title': 'title',
            })))
            playlist_id = traverse_obj(api_result, ('video', 'animeSn')) or ''
            if self._yes_playlist(playlist_id, video_id) and unsmuggled_data.get('extract_playlist') is not False:
                return self.playlist_result(
                    (self.url_result(
                        smuggle_url(f'https://ani.gamer.com.tw/animeVideo.php?sn={ep["videoSn"]}', {
                            'extract_playlist': False,
                        }), ie=BahamutIE,
                        video_id=ep['videoSn'], thumbnail=ep.get('cover')) for ep in traverse_obj(
                            api_result,
                            # The first ellipsis extracts episodes of all languages
                            ('anime', 'episodes', ..., ...))),
                    playlist_id=playlist_id, **metadata)

            # video-specific metadata, extract after returning the playlist result
            metadata.update(traverse_obj(api_result, ('video', {
                'thumbnail': 'cover',
                'title': 'title',
                'timestamp': ('upTime', {unified_timestamp}),
                'duration': ('duration', {float_or_none(scale=60)}),
                'age_limit': ('rating', {lambda x: self.RATING_TO_AGE_LIMIT.get(x)}),
            })))

        m3u8_info, urlh = self._download_json_handle(
            'https://ani.gamer.com.tw/ajax/m3u8.php', video_id,
            note='Downloading m3u8 URL', errnote='Failed to download m3u8 URL', query={
                'sn': video_id,
                'device': self._DEVICE_ID,
            }, impersonate=True, headers=self.geo_verification_headers(), expected_status=400)

        formats_fatal = True
        if urlh.status == 400:
            # TODO: handle more error codes, search for /case \d+{4}:/g in anime_player.js
            error_code = traverse_obj(m3u8_info, ('error', 'code'))
            if error_code == 1011:
                formats_fatal = False
                self.raise_geo_restricted(metadata_available=True)
            elif error_code == 1007:
                if self._configuration_arg('device_id', casesense=True):
                    # the passed device id may be wrong or expired
                    self._DEVICE_ID = self._download_device_id(video_id)
                    return self.url_result(url, ie=BahamutIE, video_id=video_id)
                raise ExtractorError('Invalid device id!')
            elif error_code == 1017:
                formats_fatal = False
                self.raise_login_required(metadata_available=True)
            else:
                raise ExtractorError(
                    traverse_obj(m3u8_info, ('error', 'message')) or 'Failed to download m3u8 URL')

        return {
            **metadata,
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                m3u8_info.get('src'), video_id, ext='mp4', fatal=formats_fatal, headers={
                    'Origin': 'https://ani.gamer.com.tw',
                    **self.geo_verification_headers(),
                }),
            'http_headers': {'Origin': 'https://ani.gamer.com.tw'},
        }

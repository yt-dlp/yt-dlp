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
    _VALID_URL = r'https?://ani\.gamer\.com\.tw/animeVideo\.php\?sn=(?P<id>\d+)'

    # see anime_player.js
    RATING_TO_AGE_LIMIT = {
        1: 0,
        2: 6,
        3: 12,
        4: 15,
        5: 18,
        6: 18,  # age-gated, needs login
    }

    def _real_extract(self, url):
        url, unsmuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        device_id = (
            self._configuration_arg('device_id', [None], casesense=True)[0]
            or unsmuggled_data.get('device_id')
            or self._download_json(
                'https://ani.gamer.com.tw/ajax/getdeviceid.php', video_id,
                'Downloading device ID', 'Failed to download device ID',
                impersonate=True, headers=self.geo_verification_headers())['deviceid'])

        # TODO: extract metadata from webpage
        metadata = {}
        if api_result := self._download_json(
                'https://api.gamer.com.tw/anime/v1/video.php', video_id,
                'Downloading video info', 'Failed to download video info',
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
                        # it may be better to use self.cache for storing device_id
                        smuggle_url(f'https://ani.gamer.com.tw/animeVideo.php?sn={ep["videoSn"]}', {
                            'extract_playlist': False,
                            'device_id': device_id,
                        }), ie=BahamutIE,
                        video_id=ep['videoSn'], thumbnail=ep.get('cover')) for ep in traverse_obj(
                            api_result,
                            # This (the first ellipsis) extracts episodes of all languages,
                            # maybe just extract episodes of the current language?
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
                'device': device_id,
            }, impersonate=True, headers=self.geo_verification_headers(), expected_status=400)

        formats_fatal = True
        if urlh.status == 400:
            # TODO: handle more error codes, search for /case \d+{4}:/g in anime_player.js
            error_code = traverse_obj(m3u8_info, ('error', 'code'))
            if error_code == 1011:
                self.raise_geo_restricted(metadata_available=True)
                formats_fatal = False
            elif error_code == 1007:
                if unsmuggled_data.pop('device_id', None) is not None:
                    return self.url_result(
                        smuggle_url(f'https://ani.gamer.com.tw/animeVideo.php?sn={video_id}',
                                    unsmuggled_data), ie=BahamutIE, video_id=video_id)
                raise ExtractorError('Invalid device id!')
            elif error_code == 1017:
                self.raise_login_required(metadata_available=True)
                formats_fatal = False
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

import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    smuggle_url,
    traverse_obj,
    try_call,
    unsmuggle_url,
    urljoin,
)


class LiTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?litv\.tv/(?:[^/?#]+/watch/|vod/[^/?#]+/content\.do\?content_id=)(?P<id>[\w-]+)'
    _URL_TEMPLATE = 'https://www.litv.tv/%s/watch/%s'
    _GEO_COUNTRIES = ['TW']
    _TESTS = [{
        'url': 'https://www.litv.tv/drama/watch/VOD00041610',
        'info_dict': {
            'id': 'VOD00041606',
            'title': '花千骨',
        },
        'playlist_count': 51,  # 50 episodes + 1 trailer
    }, {
        'url': 'https://www.litv.tv/drama/watch/VOD00041610',
        'md5': 'b90ff1e9f1d8f5cfcd0a44c3e2b34c7a',
        'info_dict': {
            'id': 'VOD00041610',
            'ext': 'mp4',
            'title': '花千骨第1集',
            'thumbnail': r're:https?://.*\.jpg$',
            'description': '《花千骨》陸劇線上看。十六年前，平靜的村莊內，一名女嬰隨異相出生，途徑此地的蜀山掌門清虛道長算出此女命運非同一般，她體內散發的異香易招惹妖魔。一念慈悲下，他在村莊周邊設下結界阻擋妖魔入侵，讓其年滿十六後去蜀山，並賜名花千骨。',
            'categories': ['奇幻', '愛情', '仙俠', '古裝'],
            'episode': 'Episode 1',
            'episode_number': 1,
        },
        'params': {
            'noplaylist': True,
        },
    }, {
        'url': 'https://www.litv.tv/drama/watch/VOD00044841',
        'md5': '88322ea132f848d6e3e18b32a832b918',
        'info_dict': {
            'id': 'VOD00044841',
            'ext': 'mp4',
            'title': '芈月傳第1集　霸星芈月降世楚國',
            'description': '楚威王二年，太史令唐昧夜觀星象，發現霸星即將現世。王后得知霸星的預言後，想盡辦法不讓孩子順利出生，幸得莒姬相護化解危機。沒想到眾人期待下出生的霸星卻是位公主，楚威王對此失望至極。楚王后命人將女嬰丟棄河中，居然奇蹟似的被少司命像攔下，楚威王認為此女非同凡響，為她取名芈月。',
        },
        'skip': 'No longer exists',
    }]

    def _extract_playlist(self, playlist_data, content_type):
        all_episodes = [
            self.url_result(smuggle_url(
                self._URL_TEMPLATE % (content_type, episode['content_id']),
                {'force_noplaylist': True}))  # To prevent infinite recursion
            for episode in traverse_obj(playlist_data, ('seasons', ..., 'episodes', lambda _, v: v['content_id']))]

        return self.playlist_result(all_episodes, playlist_data['content_id'], playlist_data.get('title'))

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        vod_data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']

        program_info = traverse_obj(vod_data, ('programInformation', {dict})) or {}
        playlist_data = traverse_obj(vod_data, ('seriesTree'))
        if playlist_data and self._yes_playlist(program_info.get('series_id'), video_id, smuggled_data):
            return self._extract_playlist(playlist_data, program_info.get('content_type'))

        asset_id = traverse_obj(program_info, ('assets', 0, 'asset_id', {str}))
        if asset_id:  # This is a VOD
            media_type = 'vod'
        else:  # This is a live stream
            asset_id = program_info['content_id']
            media_type = program_info['content_type']
        puid = try_call(lambda: self._get_cookies('https://www.litv.tv/')['PUID'].value)
        if puid:
            endpoint = 'get-urls'
        else:
            puid = str(uuid.uuid4())
            endpoint = 'get-urls-no-auth'
        video_data = self._download_json(
            f'https://www.litv.tv/api/{endpoint}', video_id,
            data=json.dumps({'AssetId': asset_id, 'MediaType': media_type, 'puid': puid}).encode(),
            headers={'Content-Type': 'application/json'})

        if error := traverse_obj(video_data, ('error', {dict})):
            error_msg = traverse_obj(error, ('message', {str}))
            if error_msg and 'OutsideRegionError' in error_msg:
                self.raise_geo_restricted('This video is available in Taiwan only')
            elif error_msg:
                raise ExtractorError(f'{self.IE_NAME} said: {error_msg}', expected=True)
            raise ExtractorError(f'Unexpected error from {self.IE_NAME}')

        formats = self._extract_m3u8_formats(
            video_data['result']['AssetURLs'][0], video_id, ext='mp4', m3u8_id='hls')
        for a_format in formats:
            # LiTV HLS segments doesn't like compressions
            a_format.setdefault('http_headers', {})['Accept-Encoding'] = 'identity'

        return {
            'id': video_id,
            'formats': formats,
            'title': join_nonempty('title', 'secondary_mark', delim='', from_dict=program_info),
            **traverse_obj(program_info, {
                'description': ('description', {str}),
                'thumbnail': ('picture', {urljoin('https://p-cdnstatic.svc.litv.tv/')}),
                'categories': ('genres', ..., 'name', {str}),
                'episode_number': ('episode', {int_or_none}),
            }),
        }

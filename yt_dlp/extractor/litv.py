import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    smuggle_url,
    unsmuggle_url,
    traverse_obj,
)


class LiTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?litv\.tv/(?:vod|promo)/[^/]+/(?:content\.do)?\?.*?\b(?:content_)?id=(?P<id>[^&]+)'

    _URL_TEMPLATE = 'https://www.litv.tv/vod/%s/content.do?content_id=%s'

    _TESTS = [{
        'url': 'https://www.litv.tv/vod/drama/content.do?brc_id=root&id=VOD00041610&isUHEnabled=true&autoPlay=1',
        'info_dict': {
            'id': 'VOD00041606',
            'title': '花千骨',
        },
        'playlist_count': 51,  # 50 episodes + 1 trailer
    }, {
        'url': 'https://www.litv.tv/vod/drama/content.do?brc_id=root&id=VOD00041610&isUHEnabled=true&autoPlay=1',
        'md5': 'b90ff1e9f1d8f5cfcd0a44c3e2b34c7a',
        'info_dict': {
            'id': 'VOD00041610',
            'ext': 'mp4',
            'title': '花千骨第1集',
            'thumbnail': r're:https?://.*\.jpg$',
            'description': '《花千骨》陸劇線上看。十六年前，平靜的村莊內，一名女嬰隨異相出生，途徑此地的蜀山掌門清虛道長算出此女命運非同一般，她體內散發的異香易招惹妖魔。一念慈悲下，他在村莊周邊設下結界阻擋妖魔入侵，讓其年滿十六後去蜀山，並賜名花千骨。',
            'categories': ['奇幻', '愛情', '中國', '仙俠'],
            'episode': 'Episode 1',
            'episode_number': 1,
        },
        'params': {
            'noplaylist': True,
        },
        'skip': 'Georestricted to Taiwan',
    }]

    def _extract_playlist(self, playlist_data, content_type):
        all_episodes = [
            self.url_result(smuggle_url(
                self._URL_TEMPLATE % (content_type, episode['contentId']),
                {'force_noplaylist': True}))  # To prevent infinite recursion
            for episode in traverse_obj(playlist_data, ('seasons', ..., 'episode', lambda _, v: v['contentId']))]

        return self.playlist_result(all_episodes, playlist_data['contentId'], playlist_data['title'])

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        if '<meta http-equiv="refresh" content="1;url=https://www.litv.tv/"' in webpage:
            raise ExtractorError('No such content', expected=True)

        program_info = self._parse_json(self._search_regex(
            r'var\s+programInfo\s*=\s*([^;]+)', webpage, 'VOD data', default='{}'),
            video_id)

        # In browsers `getProgramInfo` request is always issued. Usually this
        # endpoint gives the same result as the data embedded in the webpage.
        # If, for some reason, there are no embedded data, we do an extra request.
        if 'assetId' not in program_info:
            program_info = self._download_json(
                'https://www.litv.tv/vod/ajax/getProgramInfo', video_id,
                query={'contentId': video_id},
                headers={'Accept': 'application/json'})

        series_id = program_info['seriesId']
        if self._yes_playlist(series_id, video_id, smuggled_data):
            playlist_data = self._download_json(
                'https://www.litv.tv/vod/ajax/getSeriesTree',
                video_id,
                query={'seriesId': series_id},
                headers={'Accept': 'application/json'})
            return self._extract_playlist(playlist_data, program_info['contentType'])

        video_data = self._parse_json(self._search_regex(
            r'uiHlsUrl\s*=\s*testBackendData\(([^;]+)\);',
            webpage, 'video data', default='{}'), video_id)
        if not video_data:
            payload = {
                'assetId': program_info['assetId'],
                'watchDevices': program_info['watchDevices'],
                'contentType': program_info['contentType'],
            }
            video_data = self._download_json(
                'https://www.litv.tv/vod/ajax/getMainUrlNoAuth', video_id,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'})

        if not video_data.get('fullpath'):
            error_msg = video_data.get('errorMessage')
            if error_msg == 'vod.error.outsideregionerror':
                self.raise_geo_restricted('This video is available in Taiwan only')
            if error_msg:
                raise ExtractorError('%s said: %s' % (self.IE_NAME, error_msg), expected=True)
            raise ExtractorError('Unexpected result from %s' % self.IE_NAME)

        formats = self._extract_m3u8_formats(
            video_data['fullpath'], video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')
        for a_format in formats:
            # LiTV HLS segments doesn't like compressions
            a_format.setdefault('http_headers', {})['Accept-Encoding'] = 'identity'

        title = program_info['title'] + program_info.get('secondaryMark', '')
        description = program_info.get('description')
        thumbnail = program_info.get('imageFile')
        categories = [item['name'] for item in program_info.get('category', [])]
        episode = int_or_none(program_info.get('episode'))

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'categories': categories,
            'episode_number': episode,
        }

# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    smuggle_url,
    unsmuggle_url,
)


class LiTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?litv\.tv/(?:vod|promo)/[^/]+/(?:content\.do)?\?.*?\b(?:content_)?id=(?P<id>[^&]+)'

    _URL_TEMPLATE = 'https://www.litv.tv/vod/%s/content.do?id=%s'

    _TESTS = [{
        'url': 'https://www.litv.tv/vod/drama/content.do?brc_id=root&id=VOD00041610&isUHEnabled=true&autoPlay=1',
        'info_dict': {
            'id': 'VOD00041606',
            'title': '花千骨',
        },
        'playlist_count': 50,
    }, {
        'url': 'https://www.litv.tv/vod/drama/content.do?brc_id=root&id=VOD00041610&isUHEnabled=true&autoPlay=1',
        'md5': '969e343d9244778cb29acec608e53640',
        'info_dict': {
            'id': 'VOD00041610',
            'ext': 'mp4',
            'title': '花千骨第1集',
            'thumbnail': r're:https?://.*\.jpg$',
            'description': 'md5:c7017aa144c87467c4fb2909c4b05d6f',
            'episode_number': 1,
        },
        'params': {
            'noplaylist': True,
        },
        'skip': 'Georestricted to Taiwan',
    }, {
        'url': 'https://www.litv.tv/promo/miyuezhuan/?content_id=VOD00044841&',
        'md5': '88322ea132f848d6e3e18b32a832b918',
        'info_dict': {
            'id': 'VOD00044841',
            'ext': 'mp4',
            'title': '芈月傳第1集　霸星芈月降世楚國',
            'description': '楚威王二年，太史令唐昧夜觀星象，發現霸星即將現世。王后得知霸星的預言後，想盡辦法不讓孩子順利出生，幸得莒姬相護化解危機。沒想到眾人期待下出生的霸星卻是位公主，楚威王對此失望至極。楚王后命人將女嬰丟棄河中，居然奇蹟似的被少司命像攔下，楚威王認為此女非同凡響，為她取名芈月。',
        },
        'skip': 'Georestricted to Taiwan',
    }]

    def _extract_playlist(self, season_list, video_id, program_info, prompt=True):
        episode_title = program_info['title']
        content_id = season_list['contentId']

        if prompt:
            self.to_screen('Downloading playlist %s - add --no-playlist to just download video %s' % (content_id, video_id))

        all_episodes = [
            self.url_result(smuggle_url(
                self._URL_TEMPLATE % (program_info['contentType'], episode['contentId']),
                {'force_noplaylist': True}))  # To prevent infinite recursion
            for episode in season_list['episode']]

        return self.playlist_result(all_episodes, content_id, episode_title)

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})

        video_id = self._match_id(url)

        noplaylist = self._downloader.params.get('noplaylist')
        noplaylist_prompt = True
        if 'force_noplaylist' in data:
            noplaylist = data['force_noplaylist']
            noplaylist_prompt = False

        webpage = self._download_webpage(url, video_id)

        program_info = self._parse_json(self._search_regex(
            r'var\s+programInfo\s*=\s*([^;]+)', webpage, 'VOD data', default='{}'),
            video_id)

        season_list = list(program_info.get('seasonList', {}).values())
        if season_list:
            if not noplaylist:
                return self._extract_playlist(
                    season_list[0], video_id, program_info,
                    prompt=noplaylist_prompt)

            if noplaylist_prompt:
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)

        # In browsers `getMainUrl` request is always issued. Usually this
        # endpoint gives the same result as the data embedded in the webpage.
        # If georestricted, there are no embedded data, so an extra request is
        # necessary to get the error code
        if 'assetId' not in program_info:
            program_info = self._download_json(
                'https://www.litv.tv/vod/ajax/getProgramInfo', video_id,
                query={'contentId': video_id},
                headers={'Accept': 'application/json'})
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
                'https://www.litv.tv/vod/getMainUrl', video_id,
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
            a_format.setdefault('http_headers', {})['Youtubedl-no-compression'] = True

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

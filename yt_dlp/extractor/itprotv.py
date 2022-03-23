# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    sanitized_Request,
    urlencode_postdata,
    qualities
)


class ITProTVIE(InfoExtractor):
    _LOGIN_URL = 'https://app.itpro.tv/login/'
    _NETRC_MACHINE = 'itprotv'

    _VALID_URL = r'https://app.itpro.tv/course/accelerated-cissp-2021/(?P<id>[0-9a-z-]+)'
    _TEST = {
        'url': 'https://app.itpro.tv/course/accelerated-cissp-2021/securityrisk-keycissp',
        'md5': '0d8f96562ff3b180ba1dabda7093d822',
        'info_dict': {
            'id': 'securityrisk-keycissp',
            'ext': 'mp4',
            'title': 'Security and Risk Management Key Points',
            'thumbnail': r're:^https?://.*\.png$',
            'description': 'In this episode, we will be reviewing the Domain 1, Security and Risk Management key points that you need to focus on for the CISSP exam. After watching this episode you will be able to understand and identify the key points and items from Domain 1 that need to be mastered as part of your preparation to take and pass the CISSP exam.',
            'duration': 1100
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }

    def _real_initialize(self):
        # self._login()
        pass

    def _login(self):
        username, password = self._get_login_info()
        if username is None or password is None:
            return False

        login_form = {
            'emailInput': username,
            'passwordInput': password
        }

        login_data = urlencode_postdata(login_form)
        request = sanitized_Request(self._LOGIN_URL, login_data)

        login_results = self._download_webpage(request, None, note='Logging in', errnote='Unable to log in')

        return True

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        jwt = self._search_regex(r'{"passedToken":"([A-Za-z0-9-_]*\.[A-Za-z0-9-_]*\.[A-Za-z0-9-_]+)",', webpage, 'jwt')

        if jwt:
            headers = {'Authorization': 'Bearer ' + jwt}
            api = self._download_json(f'https://api.itpro.tv/api/urza/v3/consumer-web/brand/00002560-0000-3fa9-0000-1d61000035f3/episode?url=' + video_id, video_id, headers=headers)

        # TODO more code goes here, for example ...
        episode = api['episode']

        title = episode['title']
        description = episode['description']
        video_url = episode['jwVideo1080Embed']
        thumbnail = episode['thumbnail']

        QUALITIES = qualities(['low', 'medium', 'high', 'veryhigh'])

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': [
                {'url': episode['jwVideo320Embed'], 'height': 320, 'quality': QUALITIES('low')},
                {'url': episode['jwVideo480Embed'], 'height': 480, 'quality': QUALITIES('medium')},
                {'url': episode['jwVideo720Embed'], 'height': 720, 'quality': QUALITIES('high')},
                {'url': episode['jwVideo1080Embed'], 'height': 1080, 'quality': QUALITIES('verhigh')}
            ],
            'duration': episode['length'],
            'automatic_captions': {
                'en':
                    [{'url': episode['enCaptionLink']}]

                }
            # 'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO more properties (see youtube_dl/extractor/common.py)
        }
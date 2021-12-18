# coding: utf-8
import requests

from yt_dlp.utils import ExtractorError
from .common import InfoExtractor
from .vimeo import VHXEmbedIE


class DropoutIE(InfoExtractor):
    _LOGIN_URL = 'https://www.dropout.tv/login'
    _NETRC_MACHINE = 'dropout'
    _CONTAINS_IF_SUCCESSFUL = 'user_has_subscription: "true"'

    _VALID_URL = r'https?://(?:www\.)?dropout\.tv/videos/(?P<id>.+)'
    _TESTS = [{
        'url': 'https://www.dropout.tv/videos/misfits-magic-holiday-special',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': 'misfits-magic-holiday-special',
            'ext': 'mp4',
            'title': 'Misfits & Magic Holiday Special',
            'thumbnail': r're:^https?://.*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }]

    def _get_authenticity_token(self, session: requests.Session):
        signin_page = session.get(self._LOGIN_URL).text
        authenticity_token = self._html_search_regex(r'name="authenticity_token" value="(.+?)"', signin_page, 'authenticity_token')
        return authenticity_token

    def _login(self, session: requests.Session):
        username, password = self._get_login_info()
        if not (username and password):
            self.raise_login_required()

        payload = {
            'email': username,
            'password': password,
            'authenticity_token': self._get_authenticity_token(session),
            'utf8': True
        }
        return session.post(self._LOGIN_URL, data=payload)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Log in and get embed_url of video
        with requests.Session() as session:
            response = self._login(session)
            if not self._CONTAINS_IF_SUCCESSFUL in response.text:
                self.raise_login_required('Incorrect username/password, or account is not subscribed')
            webpage = session.get(url).text
        embed_url = self._html_search_regex(r'embed_url: "(.+?)"', webpage, 'url')
        # More metadata
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')

        return self.url_result(
            url=embed_url, 
            ie=VHXEmbedIE.ie_key(), 
            video_id=video_id, 
            video_title=title
        )
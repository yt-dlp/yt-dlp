# coding: utf-8
import requests
from .common import InfoExtractor
from .vimeo import VHXEmbedIE


class DropoutIE(InfoExtractor):
    _LOGIN_URL = 'https://www.dropout.tv/login'
    _NETRC_MACHINE = 'dropout'

    _VALID_URL = r'https?://(?:www\.)?dropout\.tv/videos/(?P<id>.+)'
    _TESTS = [{
        'url': 'https://www.dropout.tv/videos/misfits-magic-holiday-special',
        'md5': 'c30fa18999c5880d156339f13c953a26',
        'info_dict': {
            'id': '1915774',
            'display_id': 'misfits-magic-holiday-special',
            'ext': 'mp4',
            'title': 'Misfits & Magic Holiday Special',
            'description': 'The magical misfits spend Christmas break at Gowpenny, with an unwelcome visitor.',
            'release_date': '20211215',
            'thumbnail': 'https://vhx.imgix.net/chuncensoredstaging/assets/d91ea8a6-b250-42ed-907e-b30fb1c65176-8e24b8e5.jpg',
            'duration': 11698,
            'uploader_id': 'user80538407',
            'uploader_url': 'https://vimeo.com/user80538407',
            'uploader': 'OTT Videos'
        },
        'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest']
    }]

    def _get_authenticity_token(self, session: requests.Session):
        signin_page = session.get(self._LOGIN_URL).text
        authenticity_token = self._html_search_regex(r'name="authenticity_token" value="(.+?)"', 
            signin_page, 'authenticity_token')
        return authenticity_token

    def _login(self, session: requests.Session):
        # Using a Session instead of the normal _download_webpage() because we 
        # need to have cookies in order to download videos, and _download_webpage 
        # has no provisions for cookies (as far as I can tell)

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
        display_id = self._match_id(url)

        # Log in and get embed_url of video
        with requests.Session() as session:
            response = self._login(session)
            # Make sure login was successful
            if not self._html_search_regex(r'user_has_subscription: ["\'](.+?)["\']', 
                response.text, 'success').lower() == 'true':
                self.raise_login_required('Incorrect username/password, or account is not subscribed')
            webpage = session.get(url).text
        embed_url = self._html_search_regex(r'embed_url: ["\'](.+?)["\']', webpage, 'url')

        # More metadata
        id = self._html_search_regex(r'embed.vhx.tv/videos/(.+?)\?', embed_url, 'id')
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        if title: title = title.split(' - ')[0]
        description = self._html_search_regex(
            r'<meta name=["\']description["\'] content=["\'](.+?)["\']', 
            webpage, 'description')
        thumbnail = self._html_search_regex(r'<meta property="og:image" content="(.+?)\?', 
            webpage, 'thumbnail')
        release_date = self._html_search_regex(
            r'data-meta-field-name=["\']release_dates["\'] data-meta-field-value=["\'](.+?)["\']', 
            webpage, 'release_date')
        if release_date: release_date = release_date.replace('-','')

        return {
            '_type': 'url_transparent',
            'ie_key': VHXEmbedIE.ie_key(),
            'url': embed_url,
            'id': id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'release_date': release_date,
        }
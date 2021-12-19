# coding: utf-8
from .common import InfoExtractor
from .vimeo import VHXEmbedIE
from ..utils import urlencode_postdata


class DropoutIE(InfoExtractor):
    _LOGIN_URL = 'https://www.dropout.tv/login'
    _LOGOUT_URL = 'https://www.dropout.tv/logout'
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

    def _get_authenticity_token(self, id: str):
        signin_page = self._download_webpage(self._LOGIN_URL, video_id=id,
                                             note='Getting authenticity token')
        authenticity_token = self._html_search_regex(
            r'name=["\']authenticity_token["\'] value=["\'](.+?)["\']',
            signin_page, 'authenticity_token')
        return authenticity_token

    def _login(self, id: str):
        username, password = self._get_login_info()
        if not (username and password):
            self.raise_login_required()

        payload = {
            'email': username,
            'password': password,
            'authenticity_token': self._get_authenticity_token(id),
            'utf8': True
        }
        response = self._download_webpage(self._LOGIN_URL, video_id=id,
                                          note='Logging in', data=urlencode_postdata(payload))

        user_has_subscription = self._search_regex(r'user_has_subscription: ["\'](.+?)["\']',
                                                   response, 'success', default='none')
        if user_has_subscription.lower() == 'true':
            return response
        self._logout(id)
        if user_has_subscription.lower() == 'false':
            self.raise_login_required('Account is not subscribed')
        else:
            self.raise_login_required('Incorrect username/password')

    def _logout(self, id):
        self._download_webpage(self._LOGOUT_URL, id, note='Logging out')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        self._login(display_id)

        webpage = self._download_webpage(url, display_id, note='Downloading video webpage')
        self._logout(display_id)
        embed_url = self._search_regex(r'embed_url: ["\'](.+?)["\']', webpage, 'url')

        id = self._search_regex(r'embed.vhx.tv/videos/(.+?)\?', embed_url, 'id')
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        title = ' - '.join(title.split(' - ')[0:-2])  # Allows for " - " in title
        description = self._html_search_meta('description', webpage, display_name='description', fatal=False)
        thumbnail = self._og_search_thumbnail(webpage)
        thumbnail = thumbnail.split('?')[0] if thumbnail else None  # Ignore crop/downscale
        release_date = self._search_regex(
            r'data-meta-field-name=["\']release_dates["\'] data-meta-field-value=["\'](.+?)["\']',
            webpage, 'release_date', fatal=False)
        release_date = release_date.replace('-', '') if release_date else None
        # utils.get_element_by_attribute is not used because we want data-meta-field-value,
        # not what's actually in the element (inside is something like "15Dec2021", which
        # is much harder to parse than "2021-12-15")

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

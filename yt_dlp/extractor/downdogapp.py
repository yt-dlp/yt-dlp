import time
import urllib

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    urlencode_postdata,
)


class DownDogAppIE(InfoExtractor):
    SUBDOMAINS = ['www', 'meditation', 'pilates', 'hiit', 'barre', 'prenatal']
    _VALID_URL = rf'https?://({"|".join(SUBDOMAINS)})\.downdogapp\.com/play#(?P<id>[^\?]*)'
    _LOGIN_URL_PATH = '/json/login'
    _MANIFEST_URL_PATH = '/manifest'
    _NETRC_MACHINE = 'downdogapp'

    def _generate_device_description(
        self,
        device='Chrome%20135.0.0.0',
        os='Linux',
        timezone='Europe%2FBerlin',
        language='ENGLISH',
    ):
        # Option values are ignored by server, still necessary to pass them
        unix_timestamp = int(time.time())
        return {
            'deviceDescription': device,
            'osVersion': os,
            'timeZone': timezone,
            'locale': 'en-US',
            'appType': 'ORIGINAL',
            'timestamp': unix_timestamp,
            'languageOption': language,
        }

    def _get_token(self, hostname):
        """Get initial token, needed to log in"""
        post_data = self._generate_device_description()
        response = self._request_webpage(
            f'https://{hostname}{self._MANIFEST_URL_PATH}',
            None,
            data=urlencode_postdata(post_data),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        response_data = response.read().decode('utf-8')
        response_dict = self._parse_json(response_data, None)
        return response_dict['cred']

    def _login(self, hostname, username, password):
        login_url = f'https://{hostname}{self._LOGIN_URL_PATH}'
        token = self._get_token(hostname)
        # set required cookie
        self._set_cookie(hostname, 'credentials', token)
        post_data = self._generate_device_description()
        post_data['email'] = username
        post_data['password'] = password
        post_data['cred'] = token

        result = self._request_webpage(
            login_url,
            None,
            'Logging in',
            'Failed to log in',
            data=urlencode_postdata(post_data),
        )
        login_result = self._parse_json(result.read().decode('utf-8'), None)
        if login_result['type'] == 'WRONG_PASSWORD':
            raise ExtractorError(
                'Login failed (invalid username/password)', expected=True,
            )
        elif login_result['type'] == 'SUCCESS':
            new_credential = login_result['cred']
            self._set_cookie(hostname, 'credentials', new_credential)
        else:  # unexpected error
            raise ExtractorError('Login failed (unexpected)')

    def _get_credential_key(self, hostname):
        cookie = self._get_cookies(f'https://{hostname}')

        if cookie:
            return cookie['credentials'].coded_value
        else:
            return None

    def _real_extract(self, url):
        hostname = urllib.parse.urlparse(url).hostname
        username, password = self._get_login_info(netrc_machine=hostname)
        if username:
            self._login(hostname, username, password)

        sequence_id = self._match_id(url)

        api_key = self._get_credential_key(hostname)
        if not api_key:
            # most likely not logged in
            raise ExtractorError(
                'Unable to get access token, did you pass cookies or log in?',
                expected=True,
            )
        # These parameters seem to be irrelevant to what is returned,
        #  but are require to get a proper return.
        # Prepare the parameters for the POST data
        _params = self._generate_device_description()
        device = _params['deviceDescription']
        os = _params['osVersion']
        timezone = _params['timeZone']
        unix_timestamp = _params['timestamp']
        language = _params['languageOption']

        # Build the POST data string, order matters
        timings_data = (
            f'sequenceId={sequence_id}&'
            f'playlistSettings=%7B%2216%22%3A-1%7D&'
            f'forOffline=false&'
            f'deviceDescription={device}&'
            f'osVersion={os}&'
            f'timeZone={timezone}&'
            f'locale=en-US&'
            f'appType=ORIGINAL&'
            f'timestamp={unix_timestamp}&'
            f'cred={api_key}&'
            f'languageOption={language}'
        ).encode()

        timings = self._request_webpage(
            f'https://{hostname}/json/practice',
            sequence_id,
            data=timings_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        timings_dict = self._parse_json(timings.read().decode('utf-8'), sequence_id)
        try:
            length_in_minutes = int(
                timings_dict['sequence']['totalTime']['seconds'] // 60,
            )
            title = (
                f'Down Dog {timings_dict["sequence"]["activityType"].capitalize()} -'
                f' {timings_dict["sequence"]["trackerLabel"]} {length_in_minutes}min'
            )
        except KeyError:
            length_in_minutes = 80  # to be safe
            title = None

        playback_post_data = (
            f'sequenceId={sequence_id}&'
            f'videoOffsetTime=0&'
            f'audioBalance=0.5&'
            f'includeCountdown=true&'
            f'includeOverlay=true&'
            f'includePoseNames=true&'
            f'includeClosedCaptions=false&'
            f'mirrorVideo=false&'
            f'videoQualityId=4&'
            f'cellularConnection=false&'
            f'chromecast=false&'
            f'airplay=false&'
            f'deviceDescription={device}&'
            f'osVersion={os}&'
            f'timeZone={timezone}&'
            f'locale=en-US&'
            f'appType=ORIGINAL&'
            f'timestamp={unix_timestamp}&'
            f'cred={api_key}&'
            f'languageOption={language}'
        ).encode()

        response = self._request_webpage(f'https://{hostname}/json/playbackUrl',
                                         sequence_id,
                                         data=playback_post_data,
                                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                         )
        response_data = response.read().decode('utf-8')
        api_data = self._parse_json(response_data, sequence_id)
        m3u8_url = api_data['url']

        # wait for video to be 'stitched' by the server before downloading,
        #  otherwise will only get a partial file
        sleep_minutes = length_in_minutes / 6
        self.report_warning(
            f'Waiting for media to be created by the server, starting download in {sleep_minutes:.1f} minutes...',
        )
        time.sleep(sleep_minutes * 60)

        formats = self._extract_m3u8_formats(m3u8_url, sequence_id)
        return {
            'id': sequence_id,
            'title': title,
            'formats': formats,
        }

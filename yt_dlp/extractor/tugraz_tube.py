import re
from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata

class TugrazTubeIE(InfoExtractor):
    IE_DESC = 'tube.tugraz.at'
    IE_NAME = 'tube.tugraz.at'
    _VALID_URL = r"""(?x)^
        (?:https?://)?tube\.tugraz\.at/paella/ui/(?:
            (?P<series>browse\.html\?series=)|
            (?P<episode>watch.html\?id=)
        )(?P<id>[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})
    $"""
    _LOGIN_REQUIRED = True

    _LOGIN_URL = "https://tube.tugraz.at/Shibboleth.sso/Login?target=/paella/ui/index.html"
    _LOGIN_SUCCESS_URL = "https://tube.tugraz.at/paella/ui/index.html"

    _API_SERIES = "https://tube.tugraz.at/series/series.json"
    _API_EPISODE = "https://tube.tugraz.at/search/episode.json"

    def _login(self):
        username, password = self._get_login_info()

        if username is None:
            raise ExtractorError('No login info available, needed for using %s.' % self.IE_NAME)

        _, login_page_handle = self._download_webpage_handle(
            self._LOGIN_URL, None,
            note = 'Downloading login page',
            errnote = 'unable to fetch login page', fatal = True
        )

        _, result_page_handle = self._download_webpage_handle(
            login_page_handle.url, None,
            note = 'Logging in',
            errnote = 'unable to log in', fatal = True,
            data = urlencode_postdata({
                b"lang": "de",
                b"_eventId_proceed": "",
                b"j_username": username,
                b"j_password": password
            }),
            headers = {
                "referer": login_page_handle.url
            }
        )

        if result_page_handle.url != self._LOGIN_SUCCESS_URL:
            raise ExtractorError('Failed to log in, needed for using %s.' % self.IE_NAME)

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        match = re.match(self._VALID_URL, url)

        id = match.group('id')
        if match.group('series') is not None:
            return self._extract_series(id)
        elif match.group('episode') is not None:
            return self._extract_episode(id)
        else:
            return []

    def _get_series_info(self, id):
        data = self._download_json(
            self._API_SERIES, None,
            note = 'Downloading series metadata',
            errnote = 'failed to download series metadata', fatal = True,
            query = {
                "seriesId": id,
                "count": 1,
                "sort": "TITLE"
            }
        )

        return data["catalogs"][0]["http://purl.org/dc/terms/"]

    def _get_series_title(self, info):
        return info["title"][0]["value"]

    def _get_series_episode_info(self, id):
        data = self._download_json(
            self._API_EPISODE, None,
            note = 'Downloading episode list',
            errnote = 'failed to download episode list', fatal = True,
            query = {
                "sid": id,
                "limit": 128,
                "offset": 0
            }
        )

        return data["search-results"]["result"]

    def _get_episode_info(self, id):
        data = self._download_json(
            self._API_EPISODE, None,
            note = 'Downloading episode metadata',
            errnote = 'failed to download episode metadata', fatal = True,
            query = {
                "id": id,
                "limit": 1,
                "offset": 0
            }
        )

        return data["search-results"]["result"][0]

    def _get_episode_id(self, info):
        return info["id"]

    def _get_episode_title(self, info):
        return info["dcTitle"]

    def _get_episode_download_url(self, info):
        return info["mediapackage"]["media"]["track"][0]["url"]

    def _get_episode_download_ext(self, info):
        *_, ext = self._get_episode_download_url(info).rsplit('.', 1)
        return ext

    def _extract_series(self, id):
        info = self._get_series_info(id)
        episodes = self._get_series_episode_info(id)

        return [{
            "id": self._get_episode_id(episode),
            "url": self._get_episode_download_url(episode),
            "ext": self._get_episode_download_ext(episode),
            "title": self._get_episode_title(episode)
        } for episode in episodes]

    def _extract_episode(self, id):
        episode = self._get_episode_info(id)

        return [{
            "id": self._get_episode_id(episode),
            "url": self._get_episode_download_url(episode),
            "ext": self._get_episode_download_ext(episode),
            "title": self._get_episode_title(episode)
        }]

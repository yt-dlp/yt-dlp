# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata

import re

class TubeTuGrazIE(InfoExtractor):
    IE_DESC = 'tube.tugraz.at'
    IE_NAME = 'TubeTuGraz'
    _VALID_URL = r"""(?x)^
        (?:https?://)?tube\.tugraz\.at/paella/ui/(?:
            (?P<series>browse\.html\?series=)|
            (?P<episode>watch.html\?id=)
        )(?P<id>[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})
    $"""

    _LOGIN_REQUIRED = False
    _NETRC_MACHINE = None # wtf? needed for proper error message when no login details provided

    _LOGIN_URL = "https://tube.tugraz.at/Shibboleth.sso/Login?target=/paella/ui/index.html"
    _LOGIN_SUCCESS_URL = "https://tube.tugraz.at/paella/ui/index.html"

    _API_SERIES = "https://tube.tugraz.at/series/series.json"
    _API_EPISODE = "https://tube.tugraz.at/search/episode.json"

    def _login(self):
        username, password = self._get_login_info()

        if username is None:
            return

        result = self._download_webpage_handle(
            self._LOGIN_URL, None,
            note = 'Downloading login page',
            errnote = 'unable to fetch login page', fatal = False
        )
        if result is False:
            return
        else:
            _, login_page_handle = result

        result = self._download_webpage_handle(
            login_page_handle.url, None,
            note = 'Logging in',
            errnote = 'unable to log in', fatal = False,
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
        if result is False:
            return
        else:
            _, result_page_handle = result

        if result_page_handle.url != self._LOGIN_SUCCESS_URL:
            return

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
            raise ExtractorError("No video found on page")

    def _get_series_info(self, id):
        data = self._download_json(
            self._API_SERIES, None,
            note = 'Downloading series metadata',
            errnote = 'failed to download series metadata', fatal = False,
            query = {
                "seriesId": id,
                "count": 1,
                "sort": "TITLE"
            }
        )
        if data is False:
            return None

        return data["catalogs"][0]["http://purl.org/dc/terms/"]

    def _get_series_id(self, info):
        return info["identifier"][0]["value"]

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

        return data["search-results"]["result"]

    def _get_episode_id(self, info):
        return info["id"]

    def _get_episode_title(self, info):
        return info["dcTitle"]

    def _get_episode_download_url(self, info):
        return info["mediapackage"]["media"]["track"][0]["url"]

    def _get_episode_download_ext(self, info):
        *_, ext = self._get_episode_download_url(info).rsplit('.', 1)
        return ext

    def _build_series_info_dict(self, info, episodes):
        return {
            "_type": "playlist",
            "id": self._get_series_id(info),
            "title": self._get_series_title(info),
            "entries": [
                self._build_episode_info_dict(episode) for episode in episodes
            ]
        }

    def _build_episode_info_dict(self, info):
        return {
            "id": self._get_episode_id(info),
            "title": self._get_episode_title(info),
            "url": self._get_episode_download_url(info),
            "ext": self._get_episode_download_ext(info),
        }

    def _extract_series(self, id):
        info = self._get_series_info(id)
        episodes = self._get_series_episode_info(id)
        return self._build_series_info_dict(info, episodes)

    def _extract_episode(self, id):
        episode = self._get_episode_info(id)
        return self._build_episode_info_dict(episode)

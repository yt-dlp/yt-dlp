# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata, try_get, parse_duration

import re

def try_get_or(src, getters, expected_type=None):
    for getter in getters:
        v = try_get(src, getter, expected_type)
        if v is not None:
            return v

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
            note='downloading login page',
            errnote='unable to fetch login page',
            fatal=False)
        if result is False:
            return
        else:
            _, login_page_handle = result

        result = self._download_webpage_handle(
            login_page_handle.url, None,
            note='logging in',
            errnote='unable to log in',
            fatal=False,
            data=urlencode_postdata({
                b"lang": "de",
                b"_eventId_proceed": "",
                b"j_username": username,
                b"j_password": password
            }),
            headers={ "referer": login_page_handle.url })
        if result is False:
            return
        else:
            _, result_page_handle = result

        if result_page_handle.url != self._LOGIN_SUCCESS_URL:
            self._downloader.report_warning("unable to login: incorrect password")
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
            raise ExtractorError("no video found on page")

    def _extract_series(self, id):
        series_info_data = self._download_json(
            self._API_SERIES, None,
            note='downloading series metadata',
            errnote='failed to download series metadata',
            fatal=False,
            query={
                "seriesId": id,
                "count": 1,
                "sort": "TITLE"
            })
        series_info = try_get(series_info_data,
            lambda x: x["catalogs"][0]["http://purl.org/dc/terms/"]) or {}

        title = try_get(series_info, lambda x: x["title"][0]["value"])

        episodes_info_data = self._download_json(
            self._API_EPISODE, None,
            note='downloading episode list',
            errnote='failed to download episode list',
            fatal=False,
            query={ "sid": id })
        episodes_info = try_get(episodes_info_data,
            lambda x: x["search-results"]["result"]) or []

        if len(episodes_info == 0):
            raise ExtractorError("no videos found in series")

        return {
            "_type": "playlist",
            "id": id,
            "title": title,
            "entries": [self._extract_episode_from_info(episode_info)
                for episode_info in episodes_info]
        }

    def _extract_episode(self, id):
        episode_info_data = self._download_json(
            self._API_EPISODE, None,
            note='downloading episode metadata',
            errnote ='failed to download episode metadata',
            fatal=False,
            query={ "id": id, "limit": 1 })
        episode_info = try_get(episode_info_data,
            lambda x: x["search-results"]["result"]) or {}

        return self._extract_episode_inner(id, episode_info)

    def _extract_episode_from_info(self, episode_info):
        id = try_get(episode_info, lambda x: x["id"])
        return self._extract_episode_inner(id, episode_info)

    def _extract_episode_inner(self, id, episode_info):
        title = try_get_or(episode_info, [
            lambda x: x["mediapackage"]["title"],
            lambda x: x["dcTitle"]]) or id

        creator = try_get_or(episode_info, [
            lambda x: x["mediapackage"]["creators"]["creator"],
            lambda x: x["dcCreator"]])
        if isinstance(creator, list):
            creator = ", ".join(creator)

        duration = parse_duration(try_get_or(episode_info, [
            lambda x: x["mediapackage"]["duration"],
            lambda x: x["dcExtent"]]))

        series_id = try_get_or(episode_info, [
            lambda x: x["mediapackage"]["series"],
            lambda x: x["dcIsPartOf"]])

        series_title = try_get(episode_info,
            lambda x: x["mediapackage"]["seriestitle"]) or series_id

        format_info_data = try_get(episode_info,
            lambda x: x["mediapackage"]["media"]["track"]) or []
        formats = [self._extract_format(format_info)
            for format_info in format_info_data]

        # remove skipped formats
        formats = [format for format in formats if format is not None]

        self._add_guessed_formats(formats, id)

        return {
            "_type": "video",
            "id": id,
            "title": title,
            "creator": creator,
            "duration": duration,
            "series": series_title,
            "formats": formats
        }

    def _extract_format(self, format_info):
        PREFERRED_TYPE = "presentation/delivery"

        url = try_get(format_info, lambda x: x["url"])
        type = try_get(format_info, lambda x: x["type"])
        transport = try_get(format_info, lambda x: x["transport"]) or "HTTPS"
        audio_bitrate = try_get(format_info, lambda x: x["audio"]["bitrate"])
        video_bitrate = try_get(format_info, lambda x: x["video"]["bitrate"])
        framerate = try_get(format_info, lambda x: x["video"]["framerate"])
        resolution = try_get(format_info, lambda x: x["video"]["resolution"])

        if type == PREFERRED_TYPE:
            preference = -1
        else:
            preference = -2

        if type == "HTTPS":
            protocol = "https"
        elif type == "RTMP":
            protocol = "rtmp"
        elif type == "HLS":
            protocol = "m3u8"
        elif type == "DASH":
            protocol = "http_dash_segments"
        else:
            # let youtube-dl figure it out
            protocol = None

        if type == "RTMP":
            # hack: RTMP does not seem to work
            return None

        return {
            "url": url,
            "abr": audio_bitrate,
            "vbr": video_bitrate,
            "framerate": framerate,
            "resolution": resolution,
            "protocol": protocol
        }

    def _add_guessed_formats(self, formats, id):
        PREFERRED_TYPE = "presentation"

        guess_hls = not any([format["protocol"] == "m3u8" for format in formats])
        guess_dash = not any([format["protocol"] == "http_dash_segments"for format in formats])

        for type in ("presentation", "presenter"):
            m3u8_url = "https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_%s_%s.smil/playlist.m3u8" % (id, type)
            mpd_url = "https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_%s_%s.smil/manifest_mpm4sav_mvlist.mpd" % (id, type)

            if type == PREFERRED_TYPE:
                preference = -1
            else:
                preference = -2

            if guess_hls:
                formats.extend(self._extract_m3u8_formats(
                    m3u8_url, None,
                    note="guessing location of %s HLS manifest" % type,
                    fatal=False,
                    preference=preference))
            if guess_dash:
                dash_formats = self._extract_mpd_formats(
                    mpd_url, None,
                    note="guessing location of %s DASH manifest" % type,
                    fatal=False)

                # manually add preference since _extract_mpd_formats
                # lacks a preference keyword arg
                for format in dash_formats:
                    format["preference"] = preference

                formats.extend(dash_formats)

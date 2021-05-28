# coding: utf-8
from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata, try_get
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
    _TEST = {
        "url": "https://tube.tugraz.at/paella/ui/watch.html?id=f2634392-e40e-4ac7-9ddc-47764aa23d40",
        "md5": "a23a3d5c9aaca2b84932fdba66e17145",
        "info_dict": {
            "id": "f2634392-e40e-4ac7-9ddc-47764aa23d40",
            "ext": "mp4",
            "title": "#6 (23.11.2017)",
            "episode": "#6 (23.11.2017)",
            "series": "[INB03001UF] Einführung in die strukturierte Programmierung",
            "creator": "Safran C",
            "duration": 3295818,
        }
    }

    _LOGIN_REQUIRED = False
    _NETRC_MACHINE = None

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
            headers={
                "referer": login_page_handle.url
            })
        if result is False:
            return
        else:
            _, result_page_handle = result

        if result_page_handle.url != self._LOGIN_SUCCESS_URL:
            self.report_warning("unable to login: incorrect password")
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
        series_info = try_get_or(series_info_data, [
            lambda x: x["catalogs"][0]["http://purl.org/dc/terms/"]]) or {}

        if len(series_info) == 0:
            self.report_warning(
                "failed to download series metadata: "
                + "authentication required or series does not exist", id)

        title = try_get(
            series_info,
            lambda x: x["title"][0]["value"])

        episodes_info_data = self._download_json(
            self._API_EPISODE, None,
            note='downloading episode list',
            errnote='failed to download episode list',
            fatal=False,
            query={
                "sid": id
            })
        episodes_info = try_get(
            episodes_info_data,
            lambda x: x["search-results"]["result"]) or []

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
            errnote='failed to download episode metadata',
            fatal=False,
            query={
                "id": id,
                "limit": 1
            })
        episode_info = try_get(
            episode_info_data,
            lambda x: x["search-results"]["result"]) or {}

        if len(episode_info) == 0:
            self.report_warning(
                "failed to download series metadata: "
                + "authentication required or video does not exist", id)

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

        duration = try_get_or(episode_info, [
            lambda x: x["mediapackage"]["duration"],
            lambda x: x["dcExtent"]])

        series_id = try_get_or(episode_info, [
            lambda x: x["mediapackage"]["series"],
            lambda x: x["dcIsPartOf"]])

        series_title = try_get(
            episode_info,
            lambda x: x["mediapackage"]["seriestitle"]) or series_id

        episode_title = title if series_title is not None else None

        format_infos = try_get(
            episode_info,
            lambda x: x["mediapackage"]["media"]["track"]) or []

        formats = []
        format_types = set()
        for format_info in format_infos:
            formats.extend(self._extract_formats(format_info, format_types))

        self._guess_formats(formats, format_types, id)
        self._sort_formats(formats)

        return {
            "_type": "video",
            "id": id,
            "title": title,
            "creator": creator,
            "duration": duration,
            "series": series_title,
            "episode": episode_title,
            "formats": formats
        }

    def _extract_formats(self, format_info, format_types):
        PREFERRED_TYPE = "presentation/delivery"

        url = try_get(format_info, lambda x: x["url"])
        type = try_get(format_info, lambda x: x["type"])
        transport = try_get(format_info, lambda x: x["transport"]) or "HTTPS"
        audio_bitrate = try_get(format_info, lambda x: x["audio"]["bitrate"])
        video_bitrate = try_get(format_info, lambda x: x["video"]["bitrate"])
        framerate = try_get(format_info, lambda x: x["video"]["framerate"])
        resolution = try_get(format_info, lambda x: x["video"]["resolution"])

        strtype = str(type).replace("/delivery", "")
        if isinstance(audio_bitrate, int):
            audio_bitrate = audio_bitrate / 1000
        if isinstance(video_bitrate, int):
            video_bitrate = video_bitrate / 1000

        if type == PREFERRED_TYPE:
            preference = -1
        else:
            preference = -2

        format_types.add(transport)

        if transport == "HTTPS":
            return [{
                "url": url,
                "abr": audio_bitrate,
                "vbr": video_bitrate,
                "framerate": framerate,
                "resolution": resolution,
                "preference": preference
            }]
        elif transport == "HLS":
            return self._extract_m3u8_formats(
                url, None,
                note="downloading %s HLS manifest" % strtype,
                fatal=False,
                preference=preference,
                ext="mp4")
        elif transport == "DASH":
            dash_formats = self._extract_mpd_formats(
                url, None,
                note="downloading %s DASH manifest" % strtype,
                fatal=False)

            # manually add preference since _extract_mpd_formats
            # lacks a preference keyword arg
            for format in dash_formats:
                format["preference"] = preference

            return dash_formats
        else:
            # RTMP, HDS, SMOOTH, and unknown formats
            # - RTMP url doesn't work
            # - other formats are TODO
            return []

    def _guess_formats(self, formats, format_types, id):
        PREFERRED_TYPE = "presentation"

        for type in ("presentation", "presenter"):
            m3u8_url = "https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_%s_%s.smil/playlist.m3u8" % (id, type)
            mpd_url = "https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_%s_%s.smil/manifest_mpm4sav_mvlist.mpd" % (id, type)

            if type == PREFERRED_TYPE:
                preference = -1
            else:
                preference = -2

            if "HLS" not in format_types:
                hls_page = self._download_webpage_handle(
                    m3u8_url, None,
                    note="guessing location of %s HLS manifest" % type,
                    errnote=False,
                    fatal=False)
                if hls_page is not False:
                    formats.extend(self._extract_m3u8_formats(
                        m3u8_url, None,
                        note="downloading %s HLS manifest" % type,
                        fatal=False,
                        preference=preference,
                        ext="mp4"))
            if "DASH" not in format_types:
                dash_page = self._download_webpage_handle(
                    mpd_url, None,
                    note="guessing location of %s DASH manifest" % type,
                    errnote=False,
                    fatal=False)
                if dash_page is not False:
                    dash_formats = self._extract_mpd_formats(
                        mpd_url, None,
                        note="guessing location of %s DASH manifest" % type,
                        fatal=False)

                    # manually add preference since _extract_mpd_formats
                    # lacks a preference keyword arg
                    for format in dash_formats:
                        format["preference"] = preference

                    formats.extend(dash_formats)

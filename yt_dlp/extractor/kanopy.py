import json

from .common import InfoExtractor
from ..utils import ExtractorError, try_get


class KanopyIE(InfoExtractor):
    _API_BASE_URL = "https://www.kanopy.com/kapi/"
    _NETRC_MACHINE = "kanopy"
    _VALID_URL = r"https?://(?:www\.)?kanopy.com/(?P<lang>\w{2})/(?P<institution>.*?)/watch/video/(?P<id>[0-9]+)"
    _TESTS = [
        {
            "url": "https://www.kanopy.com/en/pleasantvalley/watch/video/114603",
            "info_dict": {
                "id": "114603",
                "ext": "m3u8",
                "title": "The Blue Kite",
                "description": "md5:6163af52ae92627ae7c58906991d3792",
            },
        },
        {
            "url": "https://www.kanopy.com/en/pleasantvalley/watch/video/14020947",
            "info_dict": {
                "id": "14020947",
                "ext": "mpd",
                "title": "The Whale",
                "description": "TBD",
            },
            "params": {
                "ignore_no_formats_error": True,
                "skip_download": True,
            },
	    "expected_warnings": ["This video is DRM protected"],
            "expected_exception": "DownloadError",
        }
    ]
    _LOGIN_REQUIRED = True
    _ACCESS_TOKEN = None
    _USER_ID = None

    headers = {
        "content-type": "application/json",
        "x-version": "web/prod/4.3.0/2024-01-08-15-13-05",
    }

    def _real_initialize(self):
        if not self._ACCESS_TOKEN and not self._USER_ID:
            self.raise_login_required()

    def _perform_login(self, username, password):
        self.report_login()
        try:
            access_json = self._download_json(
                self._API_BASE_URL + "login",
                None,
                "Logging in to site using credentials",
                "Unable to log in",
                fatal=False,
                headers=self.headers,
                data=json.dumps(
                    {
                        "credentialType": "email",
                        "emailUser": {"email": username, "password": password},
                    }
                ).encode(),
            )
            self._ACCESS_TOKEN = try_get(access_json, lambda x: x["jwt"])
            if self._ACCESS_TOKEN is None:
                self.report_warning("Failed to get Access token")
            else:
                self.headers.update({"Authorization": "Bearer %s" % self._ACCESS_TOKEN})
                self._USER_ID = try_get(access_json, lambda x: x["userId"])
        except ExtractorError as e:
            self.report_warning(e)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        memberships = self._download_json(
            self._API_BASE_URL + f"memberships?userId={self._USER_ID}",
            None,
            headers=self.headers,
        )

        video_info = self._download_json(
            self._API_BASE_URL
            + f"videos/{video_id}?domainId={memberships['list'][0]['domainId']}",
            video_id,
            headers=self.headers,
        )

        streams = self._download_json(
            self._API_BASE_URL + "plays",
            video_id,
            headers=self.headers,
            data=json.dumps(
                {
                    "domainId": memberships["list"][0]["domainId"],
                    "userId": self._USER_ID,
                    "videoId": video_id,
                }
            ).encode(),
        )

        manifests = streams["manifests"]
        drm_free = bool(list(filter(lambda x: 'drm' in x and x['drm'] == 'none', manifests)))

        self.write_debug(f"Params: {self._downloader.params}")
        if not drm_free:
            self.report_drm(video_id)

        return {
            "id": video_id,
            "title": video_info["video"]["title"],
            "description": video_info["video"]["descriptionHtml"],
            "url": streams["manifests"][0]["url"],
        }

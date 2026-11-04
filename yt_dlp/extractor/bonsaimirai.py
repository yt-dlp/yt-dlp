import re

from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import (
    ExtractorError,
    url_or_none,
    urlencode_postdata,
)


class BonsaiMiraiLiveIE(InfoExtractor):
    _VALID_URL = r"https?://(?:www\.)?live\.bonsaimirai\.com/library/video/(?P<id>[^/?#]+)"
    _NETRC_MACHINE = "bonsaimirai"
    _LOGIN_URL = "https://live.bonsaimirai.com/login"
    _TESTS = [{
        "url": "https://live.bonsaimirai.com/library/video/beginner-series-structural-wiring",
        "info_dict": {
            "id": "258047482",
            "ext": "mp4",
            "title": "Structural Wiring",
            "description": "md5:2d3305bad981a06ff79f027f19865021",
            "duration": 10800,
            "thumbnail": r"re:https?://i\.vimeocdn\.com/video/.+",
            "uploader": "Bonsai Mirai",
            "uploader_id": "bonsaimirai",
            "uploader_url": "https://vimeo.com/bonsaimirai",
        },
        "params": {"skip_download": "m3u8"},
        "expected_warnings": ["Failed to parse XML: not well-formed"],
    }, {
        "url": "https://live.bonsaimirai.com/library/video/structural-wiring",
        "only_matching": True,
    }]

    def _perform_login(self, username, password):
        login_page = self._download_webpage(self._LOGIN_URL, None, "Downloading login page")
        login_form = self._form_hidden_inputs("login-form", login_page)
        login_form.update({
            "email": username,
            "password": password,
        })
        response = self._download_webpage(
            self._LOGIN_URL, None, "Logging in",
            data=urlencode_postdata(login_form),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": self._LOGIN_URL,
            })
        if "Sign Out" not in response and "sign out" not in response.lower():
            raise ExtractorError("Unable to log in", expected=True)

    def _real_initialize(self):
        self._login()

    def _is_homepage(self, webpage):
        """Check if the webpage is the homepage (not a video page)"""
        return ("Academy | Bonsai Mirai Live" in webpage
                or "<title>Academy | Bonsai Mirai Live</title>" in webpage
                or "Bonsai Mirai Live" in webpage and "library/video" not in webpage)

    def _extract_vimeo_urls(self, webpage):
        """Extract all Vimeo embed URLs from the webpage"""
        urls = []
        # From JSON-LD
        for v in self._yield_json_ld(webpage, None):
            if v.get("@type") == "VideoObject" and (embed_url := url_or_none(v.get("embedUrl"))):
                if "player.vimeo.com" in embed_url:
                    urls.append(embed_url)
        # From iframe embeds
        urls.extend(re.findall(r"<iframe[^>]+src=[\"'](https?://player\.vimeo\.com/video/\d+)[^\"']*[\"']", webpage))
        # From direct player.vimeo.com URLs
        urls.extend(re.findall(r"(https?://player\.vimeo\.com/video/\d+)", webpage))
        # From vimeo.com URLs
        for vimeo_id in re.findall(r"(?:vimeo\.com/|player\.vimeo\.com/video/)(\d+)", webpage):
            urls.append(f"https://player.vimeo.com/video/{vimeo_id}")
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)
        return unique_urls

    def _real_extract(self, url):
        display_id = self._match_id(url)
        
        # Try to download the page
        webpage = self._download_webpage(
            url, display_id, "Downloading video page",
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
        
        # Check if we got the homepage instead of the video page (not logged in)
        if self._is_homepage(webpage):
            self.raise_login_required(method="cookies")
        
        vimeo_urls = self._extract_vimeo_urls(webpage)
        
        if not vimeo_urls:
            raise ExtractorError("No Vimeo embed URL found on the page")
        
        # Use the first Vimeo URL found
        vimeo_url = vimeo_urls[0]
        
        # Smuggle the referrer for the Vimeo extractor (use original URL as referrer)
        vimeo_url = VimeoIE._smuggle_referrer(vimeo_url, url)
        
        return self.url_result(vimeo_url, VimeoIE)
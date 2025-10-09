from __future__ import annotations

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
)
from ..utils.traversal import (
    traverse_obj,
)


class TVIPlayerIE(InfoExtractor):
    _VALID_URL = (
        r"https?://tviplayer\.iol\.pt(?:/programa/[\w-]+/[a-f0-9]+)?/\w+/(?P<id>\w+)"
    )
    _TESTS = [
        {
            "url": "https://tviplayer.iol.pt/programa/a-protegida/67a63479d34ef72ee441fa79/episodio/t1e120",
            "info_dict": {
                "id": "689683000cf20ac1d5f35341",
                "ext": "mp4",
                "duration": 1593,
                "title": "A Protegida - Clarice descobre o que une Óscar a Gonçalo e Mónica",
                "thumbnail": "https://img.iol.pt/image/id/68971037d34ef72ee44941a6/",
                "season_number": 1,
            },
        }
    ]

    def _real_initialize(self):
        # Obtain the wmsAuthSign token (non-fatal)
        self.wms_auth_sign_token = self._download_webpage(
            "https://services.iol.pt/matrix?userId=",
            "wmsAuthSign",
            note="Downloading wmsAuthSign token",
            fatal=False,
        )

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Try to locate a JS "video: [ {...} ]" block
        json_data = self._search_json(
            r"(?<!-)\bvideo\s*:\s*\[",
            webpage,
            "json_data",
            video_id,
            transform_source=js_to_json,
            default={},
        )

        # Structured metadata from ld+json
        _ = self._search_json_ld(webpage, video_id, default={}) or {}

        # Merge data safely without type errors
        def first_of(*keys):
            for k in keys:
                v = traverse_obj(json_data, (k,))
                if v:
                    return v
            return None

        info_id = first_of("id")
        title = first_of("title") or self._og_search_title(webpage)
        thumbnail = first_of("cover", "thumbnail") or self._og_search_thumbnail(webpage)
        duration = first_of("duration")

        try:
            duration = int(duration) if duration is not None else None
        except Exception:
            try:
                duration = int(float(duration))
            except Exception:
                duration = None

        video_url = first_of("videoUrl", "url", "video_url")
        if not video_url:
            m = re.search(
                r'["\']videoUrl["\']\s*:\s*["\'](https?://[^"\']+)["\']', webpage
            )
            if m:
                video_url = m.group(1)

        if not video_url:
            raise ExtractorError("Unable to locate video URL in webpage", expected=True)

        query = (
            {"wmsAuthSign": self.wms_auth_sign_token}
            if self.wms_auth_sign_token
            else {}
        )
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_url, video_id, ext="mp4", query=query, fatal=False
        )

        season_number = traverse_obj(json_data, ("program", "seasonNum"))

        return {
            "id": info_id or video_id,
            "display_id": video_id,
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "formats": formats,
            "subtitles": subtitles,
            "season_number": season_number,
        }

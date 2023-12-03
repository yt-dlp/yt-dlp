from yt_dlp.utils.traversal import traverse_obj
from .common import InfoExtractor
from ..utils import qualities, ExtractorError


class BoostyIE(InfoExtractor):
    _VALID_URL = r"https?://boosty.to(/[\w-]+/posts/)(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    _TESTS = [{
        "url": "https://boosty.to/ikakprosto/posts/595db00d-7906-4d0e-99d6-1067d79ecefe",
        "info_dict": {
            "id": "595db00d-7906-4d0e-99d6-1067d79ecefe",
            "ext": "mp4",
            "title": "КАК YOUTUBE и TWITTER СВОДЯТ РОССИЯН С УМА - [когнитивные воины 2]",
            "thumbnail": r"re:^https://i.mycdn.me/videoPreview.*",
            "author": "ikakprosto",
            "duration": 11186,
            "tags": [],
            "alt_title": "Уралов.mp4",
            "display_id": "https://ok.ru/videoembed/4358687697659",
            "channel": "ikakprosto",
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._search_json(
            r'<script type="text/plain" id="initial-state">',
            webpage, "boosty", video_id,
        )
        data = json_data["posts"]["postsList"]["data"]["posts"][0]
        for i in data["data"]:
            if i["type"] == "ok_video":
                playerUrls = i["playerUrls"]
                # H.264 AAC-LC
                # ultra_hd 2160p 256 type=7
                # quad_hd 1440p 256 type=6
                # full_hd 1080p 256 type=5
                # high 720p 256 type=3
                # medium 480p 128 type=2
                # low 360p 64 type=1
                # lowest 240p 48 type=0
                # tiny 144p 32 type=4

                # dash type=1
                # dash_uni type=2
                # hls type=4

                formats = []
                for f in playerUrls:
                    if f.get("url"):
                        source_type, source_url = f.get("type"), f.get("url")

                        if "hls" in source_type:
                            formats.extend(self._extract_m3u8_formats(source_url, video_id, fatal=False))
                        elif "dash" in source_type:
                            formats.extend(self._extract_mpd_formats(source_url, video_id, fatal=False))
                        else:
                            formats.append(
                                {
                                    "url": source_url,
                                    "format_id": source_type,
                                    "ext": "mp4"
                                }
                            )

                quality = qualities(("4", "0", "1", "2", "3", "5", "6", "7", "8", "9"))
                # 4 is for 'tiny' (144p) which is the worst quality, unlike 'lowest' (240p), but has type 4 for some reason,
                # which places it between 'high' (3) and 'full_hd' (5)

                for fmt in formats:
                    fmt_type = self._search_regex(
                        r"\btype[/=](\d)", fmt["url"], "format type", default=None
                    )
                    if fmt_type:
                        fmt["quality"] = quality(fmt_type)
                # This extracts &type=1 from url and places it to quality field

                return {
                    "id": video_id,
                    "title": data.get("title"),
                    "formats": formats,
                    "alt_title": i.get("title"),
                    "thumbnail": i.get("preview") or self._og_search_thumbnail(webpage),
                    "duration": i.get("duration"),
                    "display_id": f"https://ok.ru/videoembed/{i.get('vid')}" if i.get("vid") else None,
                    "author": traverse_obj(data, ("user", "name")),
                    "channel": traverse_obj(data, ("user", "blogUrl")),
                    "tags": data.get("tags")
                }

        raise ExtractorError("Video was not found on a page. You need to pass cookies to access paid content", expected=True)

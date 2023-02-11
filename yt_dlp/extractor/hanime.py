import json

from .common import InfoExtractor
from ..utils import parse_iso8601

_HANIME_BASE_URL: str = "https://hanime.tv"
_CDN_BASE_URL: str = "https://m3u8s.highwinds-cdn.com/api/v9/m3u8s"


class HanimeIE(InfoExtractor):
    _VALID_URL = r"https?://(?:www\.)?hanime\.tv/videos/hentai/(?P<id>[a-z-0-9]+)"
    _TESTS = [{
        "url": f"{_HANIME_BASE_URL}/videos/hentai/jewelry-1",
        "md5": "b04594683cc4e334abfcc664294756b0",
        "info_dict": {
            "id": "jewelry-1",
            "ext": "m3u8",
            "title": "Jewelry 1",
            "thumbnail": "https://git-posters.pages.dev/images/jewelry-1-xgDqYIRFqN.jpg",
            "description": "Eating a meal together, cozy and warm, legs under the kotatsu… "
                           "Whether we’re angry or laughing or just zoning out and watching TV… "
                           "Even the silly little things… Our love is so precious. I wouldn’t "
                           "change a thing.\n\nA loving couple is the world’s greatest treasure.",
            "uploader": "Bootleg",
            "uploader_id": 7,
            "timestamp": 1516440389,
            "upload_date": "20180120",
            "release_timestamp": 1515078000,
            "release_date": "20180104",
            "uploader_url": f"{_HANIME_BASE_URL}/browse/brands/bootleg",
            "duration": 1005.461,
            "view_count": int,
            "like_count": int,
            "dislike_count": int,
            "webpage_url": f"{_HANIME_BASE_URL}/videos/hentai/jewelry-1",
            "tags": ["creampie", "vanilla", "uncensored", "hd", "facial", "blow job"],
            "availability": "public",
            "formats": [
                {
                    "url": f"{_CDN_BASE_URL}/mhb33v3jdA28hrh5t23pgnAt07Zvt6qmxf2602v61yzgt5hms6bcq.m3u8",
                    "width": 640,
                    "height": 360,
                    "format_id": "cf-hls-1718-jewelry-1-v1x-360",
                    "filesize_approx": 33554432,
                }, {
                    "url": f"{_CDN_BASE_URL}/j432dj885r55mb2gy14Ak90g03Ztl6hrfl4h0q3tnh4hwrfnt628m.m3u8",
                    "width": 854,
                    "height": 480,
                    "format_id": "cf-hls-1718-jewelry-1-v1x-480",
                    "filesize_approx": 41943040,
                }, {
                    "url": f"{_CDN_BASE_URL}/6kj5r809cpzxxb7d7bdp37cqqmZhsy66q2vf2qvjjfxlh3m0ht1x1.m3u8",
                    "width": 1280,
                    "height": 720,
                    "format_id": "cf-hls-1718-jewelry-1-v1x-720",
                    "filesize_approx": 85983232,
                }
            ]
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        _json: dict = json.loads(
            self._download_webpage(f"{_HANIME_BASE_URL}/api/v8/video?id={video_id}", video_id=video_id)
        )

        brand = _json["brand"]
        metadata = _json["hentai_video"]
        streams: list = list(_json["videos_manifest"]["servers"][0]["streams"])
        streams.reverse()

        formats: list[dict] = [{
            'url': stream["url"],
            'width': int(stream["width"]),
            'height': int(stream["height"]),
            'format_id': stream["slug"],
            'filesize_approx': int(stream["filesize_mbs"]) * 1024 ** 2
        } for stream in streams if stream["is_guest_allowed"]]

        return {
            "id": video_id,
            "title": metadata["name"],
            "thumbnail": metadata["poster_url"],
            "description": metadata["description"].replace("<p>", "").replace("</p>", ""),
            "duration": int(streams[0]["duration_in_ms"]) / 1000,

            "uploader": brand["title"],
            "uploader_id": brand["id"],
            "uploader_url": f"{_HANIME_BASE_URL}/browse/brands/{brand['slug']}",

            "timestamp": parse_iso8601(metadata["created_at"][:-1]),
            "release_timestamp": parse_iso8601(metadata["released_at"][:-1]),

            "view_count": metadata["views"],
            "like_count": metadata["likes"],
            "dislike_count": metadata["dislikes"],
            "webpage_url": url,
            "tags": [tag["text"] for tag in metadata["hentai_tags"]],
            "availability": "public",
            "formats": formats
        }

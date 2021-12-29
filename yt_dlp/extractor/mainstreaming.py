# coding: utf-8
import re

from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj, base_url, urljoin, try_get, parse_duration


class MainStreamingIE(InfoExtractor):
    _VALID_URL = 'https?://[A-Za-z0-9-]+\.msvdn.net/(?:embed|amp_embed|content)/(?P<id>[^/?#]+)'
    # examples: https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/MfuWmzL2lGkA?autoPlay=false
    # https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/HVvPMzy?autoplay=true&skinid=6c2d8b44-9903-493c-bf85-ec27e4d04684&T=1639390944 live DVR (playlist.m3u8?DVR), content type = 20. has live source id.
  # live video (/live/id/playlist.m3u8): https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/zPnHWY2?autoPlay=true&skinId=6c2d8b44-9903-493c-bf85-ec27e4d04684, content type = 20, has live source id, dvr is disabled
    # https://www.lacplay.it/ gives the actual m3u8 url. but we can use the id and extract more formats
    # https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/uAsH3m14QWGx?autoPlay=true&skinId=6c2d8b44-9903-493c-bf85-ec27e4d04684 from lacplay.it
        # one site hit the api directly https://webtools-859c1818ed614cc5b0047439470927b0.msvdn.net/api/v2/content/tDoFkZD3T1Lw
    # https://video.milanofinanza.it and milanofinanza.it, youtg.net
    #

    def _real_extract(self, url):
        video_id = self._match_id(url)
        content_info = try_get(self._download_json(
            urljoin(base_url(url), f'/api/v2/content/{video_id}'), video_id, note='Downloading content info API JSON', fatal=False),
            lambda x: x['playerContentInfo'])
        # Fallback
        if not content_info:
            webpage = self._download_webpage(url, video_id)
            player_config = self._parse_json(
                self._search_regex(
                    r'config\s*=\s*({.+?})\s*;', webpage, 'mainstreaming player config',
                    default='{}', flags=re.DOTALL),
                video_id, transform_source=js_to_json, fatal=False) or {}
            content_info = player_config['contentInfo']

        formats = []
        is_live = False

        if content_info.get('drmEnabled'):
             self.report_drm(video_id)

        # Normal video content?
        if content_info.get('contentType') == 10:
            base_normal_url = f"https://{content_info['host']}/vod/{content_info['contentID']}/%s"
            formats.extend(self._extract_m3u8_formats(base_normal_url % 'playlist.m3u8', video_id=video_id))
            formats.extend(self._extract_mpd_formats(base_normal_url % 'manifest.mpd', video_id=video_id))
        # Live content
        elif content_info.get('contentType') == 20:
            dvr_enabled = traverse_obj(content_info, ('playerSettings', 'dvrEnabled'), expected_type=bool)  # TODO
            base_live_url = f"https://{content_info['host']}/live/{content_info['liveSourceID']}/{content_info['contentID']}/%s"
            base_live_url += '?DVR' if dvr_enabled else ''

            formats.extend(self._extract_m3u8_formats(base_live_url % 'playlist.m3u8', video_id=video_id))
            formats.extend(self._extract_mpd_formats(base_live_url % 'manifest.mpd', video_id=video_id))
            is_live = True

        # TODO: Progressive formats
        # TODO: "playlist contents"
        # TODO: subtitles (in subtitlesPath)
        # TODO: thumbnails
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': content_info.get('title') or video_id,
            'description': content_info.get('description'),
            'formats': formats,
            'is_live': is_live,
            'duration': parse_duration(content_info.get('duration')),
            'tags': content_info.get('tags')
        }

    # if live:
    # if DVR: generate DVR live link (dash + mpd)
    # else: generate normal live link (dash + mpd)
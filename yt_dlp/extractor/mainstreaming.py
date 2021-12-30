# coding: utf-8
import re

from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj, base_url, urljoin, try_get, parse_duration


class MainStreamingIE(InfoExtractor):
    _VALID_URL = 'https?://[A-Za-z0-9-]+\.msvdn.net/(?:embed|amp_embed|content)/(?P<id>\w+)'
    # examples: https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/MfuWmzL2lGkA?autoPlay=false
    # https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/HVvPMzy?autoplay=true&skinid=6c2d8b44-9903-493c-bf85-ec27e4d04684&T=1639390944 live DVR (playlist.m3u8?DVR), content type = 20. has live source id.
  # live video (/live/id/playlist.m3u8): https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/zPnHWY2?autoPlay=true&skinId=6c2d8b44-9903-493c-bf85-ec27e4d04684, content type = 20, has live source id, dvr is disabled
    # https://www.lacplay.it/ gives the actual m3u8 url. but we can use the id and extract more formats
    # https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/uAsH3m14QWGx?autoPlay=true&skinId=6c2d8b44-9903-493c-bf85-ec27e4d04684 from lacplay.it
        # one site hit the api directly https://webtools-859c1818ed614cc5b0047439470927b0.msvdn.net/api/v2/content/tDoFkZD3T1Lw
    # https://video.milanofinanza.it and milanofinanza.it, youtg.net
    #
    @staticmethod
    def _extract_urls(webpage):
        mobj = re.findall(
            r'<iframe[^>]+?src=["\']?(?P<url>%s)["\']?' % MainStreamingIE._VALID_URL, webpage)
        if mobj:
            return [group[0] for group in mobj]
        # TODO: we could extract the thumbnails (e.g. for https://video.milanofinanza.it/video/pnrr-le-sfide-del-2022-LPwjYU4lOOR4) and get the id that way
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
        alternative_content_id = content_info.get('alternativeContentID')
        if alternative_content_id:
            self.report_warning(f'Found alternative content ID: {alternative_content_id}')
        # Live content
        if content_info.get('contentType') == 20:
            dvr_enabled = traverse_obj(content_info, ('playerSettings', 'dvrEnabled'), expected_type=bool)  # TODO
            base_format_url = f"https://{content_info['host']}/live/{content_info['liveSourceID']}/{content_info['contentID']}/%s{'?DVR' if dvr_enabled else ''}"
            is_live = True
            heartbeat = self._download_json(urljoin(base_url(url), f'/api/v2/heartbeat/{video_id}'), video_id, note='Checking stream status', fatal=False) or {}
            if heartbeat.get('heartBeatUp') is False:
                self.raise_no_formats(f'MainStreaming said: {heartbeat.get("responseMessage")}', expected=True)
                # TODO: if stream does not exist, grab alternative content id?

        # Normal video content? (contentType == 10)
        else:
            base_format_url = f"https://{content_info['host']}/vod/{content_info['contentID']}/%s"
        m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(base_format_url % 'playlist.m3u8', video_id=video_id)
        mpd_formats, mpd_subs = self._extract_mpd_formats_and_subtitles(base_format_url % 'manifest.mpd', video_id=video_id)

        subtitles = self._merge_subtitles(m3u8_subs, mpd_subs)
        formats = m3u8_formats+mpd_formats
        # There is original.mp3, but it returns a video? I can specify any extension and I'd get the same video :/
        formats.extend([{
            'url': base_format_url % 'original.mp4',
        }])
        self._sort_formats(formats)
        # TODO: Progressive formats
        # TODO: "playlist contents" - https://webtools-e18da6642b684f8aa9ae449862783a56.msvdn.net/embed/WDAF1KOWUpH3
        # TODO: subtitles (in subtitlesPath)
        # TODO: thumbnails

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
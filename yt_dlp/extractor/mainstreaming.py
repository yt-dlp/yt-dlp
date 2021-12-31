# coding: utf-8
import re

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    js_to_json,
    parse_duration,
    traverse_obj,
    try_get,
    urljoin
)


class MainStreamingIE(InfoExtractor):
    _VALID_URL = 'https?://(?:webtools-?)?(?P<host>[A-Za-z0-9-]*\.msvdn.net)/(?:embed|amp_embed|content)/(?P<id>\w+)'
    IE_DESC = 'MainStreaming Player'
    # https://video.milanofinanza.it and milanofinanza.it, youtg.net, https://www.lactv.it

    _TESTS = [
        {
            'note': 'Live stream offline, has alternative content id',
            'url': 'https://webtools-e18da6642b684f8aa9ae449862783a56.msvdn.net/embed/53EN6GxbWaJC',
            'info_dict': {
                'id': '53EN6GxbWaJC',
                'title': 'Diretta homepage 2021-12-31 12:00',
                'description': '',
                'live_status': 'was_live',
                'ext': 'mp4',
                'thumbnail': r're:https?://[A-Za-z0-9-]*\.msvdn.net/image/\w+/poster',
            },
            'expected_warnings': [
                'Ignoring alternative content ID: WDAF1KOWUpH3',
                'MainStreaming said: Live event is OFFLINE'
            ],
            'skip': 'live stream offline'
        }, {
            'note': 'playlist',
            'url': 'https://webtools-e18da6642b684f8aa9ae449862783a56.msvdn.net/embed/WDAF1KOWUpH3',
            'info_dict': {
                'id': 'WDAF1KOWUpH3',
                'title': 'Playlist homepage',
            },
            'playlist_mincount': 8,
        }, {
            'note': 'livestream',
            'url': 'https://webtools-859c1818ed614cc5b0047439470927b0.msvdn.net/embed/tDoFkZD3T1Lw',
            'info_dict': {
                'id': 'tDoFkZD3T1Lw',
                'title': r're:Class CNBC Live \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
                'live_status': 'is_live',
                'ext': 'mp4',
                'thumbnail': r're:https?://[A-Za-z0-9-]*\.msvdn.net/image/\w+/poster',
            },
            'skip': 'live stream'
        }, {
            'note': 'video',
            'url': 'https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/EUlZfGWkGpOd?autoPlay=false',
            'info_dict': {
                'id': 'EUlZfGWkGpOd',
                'title': 'La Settimana ',
                'description': '03 Ottobre ore 02:00',
                'ext': 'mp4',
                'live_status': 'not_live',
                'thumbnail': r're:https?://[A-Za-z0-9-]*\.msvdn.net/image/\w+/poster',
                'duration': 1512
            }
        }, {
            'note': 'video without webtools- prefix',
            'url': 'https://f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/MfuWmzL2lGkA?autoplay=false&T=1635860445',
            'info_dict': {
                'id': 'MfuWmzL2lGkA',
                'title': 'TG Mattina',
                'description': '06 Ottobre ore 08:00',
                'ext': 'mp4',
                'live_status': 'not_live',
                'thumbnail': r're:https?://[A-Za-z0-9-]*\.msvdn.net/image/\w+/poster',
                'duration': 789.04  # TODO: this should be rounded?
            }
        }, {
            # TODO: can't get the title test working
            'note': 'always-on livestream with DVR',
            'url': 'https://webtools-f5842579ff984c1c98d63b8d789673eb.msvdn.net/embed/HVvPMzy',
            'info_dict': {
                'id': 'HVvPMzy',
                'title': r're:^Diretta LaC News24 \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
                'description': 'canale all news',
                'live_status': 'is_live',
                'ext': 'mp4',
                'thumbnail': r're:https?://[A-Za-z0-9-]*\.msvdn.net/image/\w+/poster',
            },
            'params': {
                'skip_download': True,
            },
        }, {
            'note': 'no host',
            'url': 'https://webtools.msvdn.net/embed/MfuWmzL2lGkA',
            'only_matching': True
        }, {
            'url': 'https://859c1818ed614cc5b0047439470927b0.msvdn.net/amp_embed/tDoFkZD3T1Lw',
            'only_matching': True
        }, {
            'url': 'https://859c1818ed614cc5b0047439470927b0.msvdn.net/content/tDoFkZD3T1Lw#',
            'only_matching': True
        }
    ]

    @staticmethod
    def _extract_urls(webpage):
        mobj = re.findall(
            r'<iframe[^>]+?src=["\']?(?P<url>%s)["\']?' % MainStreamingIE._VALID_URL, webpage)
        if mobj:
            return [group[0] for group in mobj]

    def _playlist_entries(self, host, playlist_content):
        for entry in playlist_content:
            content_id = entry.get('contentID')
            yield {
                '_type': 'url',
                'ie_key': MainStreamingIE.ie_key(),
                'id': content_id,
                'duration': int_or_none(traverse_obj(entry, ('duration', 'totalSeconds'))),
                'title': entry.get('title'),
                'url': f'https://{host}/embed/{content_id}'
            }

    @staticmethod
    def _get_webtools_host(host):
        if not host.startswith('webtools'):
            host = 'webtools' + ('-' if not host.startswith('.') else '') + host
        return host

    def _call_api(self, host: str, path: str, item_id: str, query=None, note='Downloading API JSON', fatal=False):
        # JSON API, does not appear to be documented
        return self._call_webtools_api(host, '/api/v2/' + path, item_id, query, note, fatal)

    def _call_webtools_api(self, host: str, path: str, item_id: str, query=None, note='Downloading webtools API JSON', fatal=False):
        # webtools docs: https://webtools.msvdn.net/
        return self._download_json(
            urljoin(f'https://{self._get_webtools_host(host)}/', path), item_id, query=query, note=note, fatal=fatal)

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).groups()
        content_info = try_get(
            self._call_api(
                host, f'content/{video_id}', video_id, note='Downloading content info API JSON'), lambda x: x['playerContentInfo'])
        # Fallback
        if not content_info:
            webpage = self._download_webpage(url, video_id)
            player_config = self._parse_json(
                self._search_regex(
                    r'config\s*=\s*({.+?})\s*;', webpage, 'mainstreaming player config',
                    default='{}', flags=re.DOTALL),
                video_id, transform_source=js_to_json, fatal=False) or {}
            content_info = player_config['contentInfo']
        host = content_info.get('host') or host

        video_id = content_info.get('contentID') or video_id
        title = content_info.get('title') or video_id
        description = traverse_obj(content_info, 'longDescription', 'shortDescription', expected_type=str, get_all=False)
        is_live = False
        was_live = False
        if content_info.get('drmEnabled'):
            self.report_drm(video_id)

        alternative_content_id = content_info.get('alternativeContentID')
        if alternative_content_id:
            self.report_warning(f'Ignoring alternative content ID: {alternative_content_id}')

        content_type = int_or_none(content_info.get('contentType'))
        format_base_url = None
        formats = []
        subtitles = {}
        # Live content
        if content_type == 20:
            dvr_enabled = traverse_obj(content_info, ('playerSettings', 'dvrEnabled'), expected_type=bool)  # TODO, add or  check --live-from-start support
            format_base_url = f"https://{host}/live/{content_info['liveSourceID']}/{video_id}/%s{'?DVR' if dvr_enabled else ''}"
            is_live = True
            heartbeat = self._call_api(host, f'heartbeat/{video_id}', video_id, note='Checking stream status') or {}
            if heartbeat.get('heartBeatUp') is False:
                self.raise_no_formats(f'MainStreaming said: {heartbeat.get("responseMessage")}', expected=True)
                is_live = False
                was_live = True
                # TODO: if stream does not exist, grab alternative content id?

        # Playlist
        elif content_type == 31:
            return self.playlist_result(self._playlist_entries(host, content_info.get('playlistContents')), video_id, title, description)
        # Normal video content?
        elif content_type == 10:
            format_base_url = f"https://{host}/vod/{video_id}/%s"
            # Progressive format: in https://webtools.msvdn.net/loader/playerV2.js there is mention of original.mp3 format,
            # however that seems to be the same as original.mp4.
            formats.append({'url': format_base_url % 'original.mp4'})
        else:
            self.raise_no_formats(f'Unknown content type {content_type}')

        if format_base_url:
            m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(format_base_url % 'playlist.m3u8', video_id=video_id, fatal=False)
            mpd_formats, mpd_subs = self._extract_mpd_formats_and_subtitles(format_base_url % 'manifest.mpd', video_id=video_id, fatal=False)

            subtitles = self._merge_subtitles(m3u8_subs, mpd_subs)
            formats.extend(m3u8_formats + mpd_formats)

        self._sort_formats(formats)
        # TODO: subtitles (in subtitlesPath)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
            'is_live': is_live,
            'was_live': was_live,
            'duration': parse_duration(content_info.get('duration')),
            'tags': content_info.get('tags'),
            'subtitles': subtitles,
            'thumbnail': f'https://{self._get_webtools_host(host)}/image/{video_id}/poster'  # may not always exist?
        }

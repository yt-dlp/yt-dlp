import re

from .common import InfoExtractor
from ..utils import js_to_json, determine_ext, mimetype2ext, KNOWN_EXTENSIONS, str_or_none, dict_get
import urllib.parse


class VideoJSEmbedIE(InfoExtractor):
    _VALID_URL = False
    IE_NAME = 'videojs'

    _WEBPAGE_TESTS = [
        {
            # Video.js embed, links to YouTube video
            'url': 'http://ortcam.com/solidworks-урок-6-настройка-чертежа_33f9b7351.html',
            'info_dict': {
                'id': 'yygqldloqIk',
                'ext': 'mp4',
                'title': 'SolidWorks. Урок 6 Настройка чертежа',
                'description': 'md5:baf95267792646afdbf030e4d06b2ab3',
                'upload_date': '20130314',
                'uploader': 'PROстое3D',
                'uploader_id': 'PROstoe3D',
                'uploader_url': 'http://www.youtube.com/user/PROstoe3D',
                'channel_follower_count': int,
                'playable_in_embed': True,
                'channel': 'PROстое3D',
                'like_count': int,
                'comment_count': int,
                'categories': ['Education'],
                'channel_id': 'UCy91Bug3dERhbwGh2m2Ijng',
                'tags': 'count:17',
                'live_status': 'not_live',
                'age_limit': 0,
                'channel_url': 'https://www.youtube.com/channel/UCy91Bug3dERhbwGh2m2Ijng',
                'thumbnail': 'https://i.ytimg.com/vi/yygqldloqIk/maxresdefault.jpg',
                'duration': 1160,
                'availability': 'public',
                'view_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # videojs embed
            # FIXME: test suite broken
            'url': 'https://video.sibnet.ru/shell.php?videoid=3422904',
            'info_dict': {
                'id': 'shell',
                'ext': 'mp4',
                'title': 'Доставщик пиццы спросил разрешения сыграть на фортепиано',
                'description': 'md5:89209cdc587dab1e4a090453dbaa2cb1',
                'thumbnail': r're:^https?://.*\.jpg$',
                'age_limit': 0,
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': ['Failed to download MPD manifest'],
        },
    ]

    def _extract_from_webpage(self, url, webpage):
        # Video.js embed
        video_id = self._generic_id(url)
        mobj = re.search(
            r'(?s)\bvideojs\s*\(.+?([a-zA-Z0-9_$]+)\.src\s*\(\s*((?:\[.+?\]|{.+?}))\s*\)\s*;',
            webpage)
        if mobj is not None:
            varname = mobj.group(1)
            sources = self._parse_json(
                mobj.group(2), video_id, transform_source=js_to_json,
                fatal=False) or []
            if not isinstance(sources, list):
                sources = [sources]
            formats = []
            subtitles = {}
            for source in sources:
                src = source.get('src')
                if not src or not isinstance(src, str):
                    continue
                src = urllib.parse.urljoin(url, src)
                src_type = source.get('type')
                if isinstance(src_type, str):
                    src_type = src_type.lower()
                ext = determine_ext(src).lower()
                if src_type == 'video/youtube':
                    yield self.url_result(src, 'Youtube')
                if src_type == 'application/dash+xml' or ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        src, video_id, mpd_id='dash', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                elif src_type == 'application/x-mpegurl' or ext == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        src, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id='hls', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    formats.append({
                        'url': src,
                        'ext': (mimetype2ext(src_type)
                                or ext if ext in KNOWN_EXTENSIONS else 'mp4'),
                        'http_headers': {
                            'Referer': url,
                        },
                    })
            # https://docs.videojs.com/player#addRemoteTextTrack
            # https://html.spec.whatwg.org/multipage/media.html#htmltrackelement
            for sub_match in re.finditer(
                rf'(?s){re.escape(varname)}' r'\.addRemoteTextTrack\(({.+?})\s*,\s*(?:true|false)\)', webpage):
                sub = self._parse_json(
                    sub_match.group(1), video_id, transform_source=js_to_json, fatal=False) or {}
                src = str_or_none(sub.get('src'))
                if not src:
                    continue
                subtitles.setdefault(dict_get(sub, ('language', 'srclang')) or 'und', []).append({
                    'url': urllib.parse.urljoin(url, src),
                    'name': sub.get('label'),
                    'http_headers': {
                        'Referer': url,
                    },
                })
            if formats or subtitles:
                self._sort_formats(formats)
                yield {
                    'formats': formats,
                    'subtitles': subtitles,
                    'id': video_id,
                    'title': (self._og_search_title(webpage, default=None)
                              or self._html_extract_title(webpage, 'video title', default='video')),
                    'description': self._og_search_description(webpage, default=None),
                    'thumbnail': self._og_search_thumbnail(webpage, default=None),
                    'age_limit': self._rta_search(webpage),
                }

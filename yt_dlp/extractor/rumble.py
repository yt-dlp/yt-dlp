import itertools
import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    int_or_none,
    parse_iso8601,
    unescapeHTML,
    ExtractorError,
)


class RumbleEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rumble\.com/embed/(?:[0-9a-z]+\.)?(?P<id>[0-9a-z]+)'
    _EMBED_REGEX = [fr'(?:<(?:script|iframe)[^>]+\bsrc=|["\']embedUrl["\']\s*:\s*)["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://rumble.com/embed/v5pv5f',
        'md5': '36a18a049856720189f30977ccbb2c34',
        'info_dict': {
            'id': 'v5pv5f',
            'ext': 'mp4',
            'title': 'WMAR 2 News Latest Headlines | October 20, 6pm',
            'timestamp': 1571611968,
            'upload_date': '20191020',
            'channel_url': 'https://rumble.com/c/WMAR',
            'channel': 'WMAR',
            'thumbnail': 'https://sp.rmbl.ws/s8/1/5/M/z/1/5Mz1a.OvCc-small-WMAR-2-News-Latest-Headline.jpg',
            'duration': 234,
            'uploader': 'WMAR',
            'live_status': 'not_live',
        }
    }, {
        'url': 'https://rumble.com/embed/vslb7v',
        'md5': '7418035de1a30a178b8af34dc2b6a52b',
        'info_dict': {
            'id': 'vslb7v',
            'ext': 'mp4',
            'title': 'Defense Sec. says US Commitment to NATO Defense \'Ironclad\'',
            'timestamp': 1645142135,
            'upload_date': '20220217',
            'channel_url': 'https://rumble.com/c/CyberTechNews',
            'channel': 'CTNews',
            'thumbnail': 'https://sp.rmbl.ws/s8/6/7/i/9/h/7i9hd.OvCc.jpg',
            'duration': 901,
            'uploader': 'CTNews',
            'live_status': 'not_live',
        }
    }, {
        'url': 'https://rumble.com/embed/vunh1h',
        'info_dict': {
            'id': 'vunh1h',
            'ext': 'mp4',
            'title': '‘Gideon, op zoek naar de waarheid’ including ENG SUBS',
            'timestamp': 1647197663,
            'upload_date': '20220313',
            'channel_url': 'https://rumble.com/user/BLCKBX',
            'channel': 'BLCKBX',
            'thumbnail': r're:https://.+\.jpg',
            'duration': 5069,
            'uploader': 'BLCKBX',
            'live_status': 'not_live',
            'subtitles': {
                'en': [
                    {
                        'url': r're:https://.+\.vtt',
                        'name': 'English',
                        'ext': 'vtt'
                    }
                ]
            },
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://rumble.com/embed/v1essrt',
        'info_dict': {
            'id': 'v1essrt',
            'ext': 'mp4',
            'title': 'startswith:lofi hip hop radio - beats to relax/study',
            'timestamp': 1661519399,
            'upload_date': '20220826',
            'channel_url': 'https://rumble.com/c/LofiGirl',
            'channel': 'Lofi Girl',
            'thumbnail': r're:https://.+\.jpg',
            'duration': None,
            'uploader': 'Lofi Girl',
            'live_status': 'is_live',
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://rumble.com/embed/ufe9n.v5pv5f',
        'only_matching': True,
    }]
    FORMAT_MAPPING = {'bitrate': 'tbr', 'size': 'filesize', 'w': 'width', 'h': 'height'}
    THUMBNAIL_MAPPING = {'i': 'url', 'w': 'width', 'h': 'height'}

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        embeds = tuple(super()._extract_embed_urls(url, webpage))
        if embeds:
            return embeds
        return [f'https://rumble.com/embed/{mobj.group("id")}' for mobj in re.finditer(
            r'<script>\s*Rumble\(\s*"play"\s*,\s*{\s*[\'"]video[\'"]\s*:\s*[\'"](?P<id>[0-9a-z]+)[\'"]', webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video = self._download_json(
            'https://rumble.com/embedJS/u3/', video_id,
            query={'request': 'video', 'ver': 2, 'v': video_id})

        if not video.get('livestream_has_dvr'):
            live_status = 'not_live'
        elif video.get('live') == 0:
            live_status = 'was_live'
        elif video.get('live') == 2:
            live_status = 'is_live'
        elif video.get('live') == 1:
            live_status = 'is_upcoming' if video.get('live_placeholder') else 'post_live'
        else:
            live_status = None

        formats = []
        for ext, ext_info in video.get('ua', {}).items():
            if not ext_info:
                continue
            for height, video_info in ext_info.items():
                meta = video_info.get('meta', {})
                if 'url' not in video_info:
                    continue
                if ext == 'hls':
                    formats.extend(
                        self._extract_m3u8_formats(
                            video_info['url'], video_id, ext='mp4', m3u8_id='hls', fatal=False))
                    if not video.get('livestream_has_dvr') and meta.get('live'):
                        live_status = 'is_live'
                    continue
                fmt = {
                    'ext': ext,
                    'url': video_info['url'],
                    'format_id': '%s-%sp' % (ext, height),
                    'height': int_or_none(height),
                    'fps': video.get('fps'),
                }
                fmt.update(
                    {key: meta[meta_key] for meta_key, key in self.FORMAT_MAPPING.items()
                     if meta_key in meta})
                formats.append(fmt)
        self._sort_formats(formats)

        subtitles = {
            lang: [{
                'url': sub_info['path'],
                'name': sub_info.get('language') or '',
            }] for lang, sub_info in (video.get('cc') or {}).items() if sub_info.get('path')
        }

        author = video.get('author', {})
        thumbnails = [{key: mapping[t_key] for t_key, key in self.THUMBNAIL_MAPPING.items()
                       if t_key in mapping} for mapping in video.get('t', ())]
        if not thumbnails and 'i' in video:
            thumbnails.append({'url': video['i']})

        if live_status in {'is_live', 'post_live'}:
            duration = None
        else:
            duration = int_or_none(video.get('duration'))

        return {
            'id': video_id,
            'title': unescapeHTML(video['title']),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'timestamp': parse_iso8601(video.get('pubDate')),
            'channel': author.get('name'),
            'channel_url': author.get('url'),
            'duration': duration,
            'uploader': author.get('name'),
            'live_status': live_status,
        }


class RumbleChannelIE(InfoExtractor):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?rumble\.com/(?:c|user)/(?P<id>[^&?#$/]+))'

    _TESTS = [{
        'url': 'https://rumble.com/c/Styxhexenhammer666',
        'playlist_mincount': 1160,
        'info_dict': {
            'id': 'Styxhexenhammer666',
        },
    }, {
        'url': 'https://rumble.com/user/goldenpoodleharleyeuna',
        'playlist_mincount': 4,
        'info_dict': {
            'id': 'goldenpoodleharleyeuna',
        },
    }]

    def entries(self, url, playlist_id):
        for page in itertools.count(1):
            try:
                webpage = self._download_webpage(f'{url}?page={page}', playlist_id, note='Downloading page %d' % page)
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 404:
                    break
                raise
            for video_url in re.findall(r'class=video-item--a\s?href=([^>]+\.html)', webpage):
                yield self.url_result('https://rumble.com' + video_url)

    def _real_extract(self, url):
        url, playlist_id = self._match_valid_url(url).groups()
        return self.playlist_result(self.entries(url, playlist_id), playlist_id=playlist_id)

import itertools
import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    UnsupportedError,
    clean_html,
    get_element_by_class,
    int_or_none,
    parse_count,
    parse_iso8601,
    traverse_obj,
    unescapeHTML,
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
        'url': 'https://rumble.com/embed/v1amumr',
        'info_dict': {
            'id': 'v1amumr',
            'ext': 'webm',
            'fps': 60,
            'title': 'Turning Point USA 2022 Student Action Summit DAY 1  - Rumble Exclusive Live',
            'timestamp': 1658518457,
            'upload_date': '20220722',
            'channel_url': 'https://rumble.com/c/RumbleEvents',
            'channel': 'Rumble Events',
            'thumbnail': r're:https://.+\.jpg',
            'duration': 16427,
            'uploader': 'Rumble Events',
            'live_status': 'was_live',
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://rumble.com/embed/ufe9n.v5pv5f',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [
        {
            'note': 'Rumble JS embed',
            'url': 'https://therightscoop.com/what-does-9-plus-1-plus-1-equal-listen-to-this-audio-of-attempted-kavanaugh-assassins-call-and-youll-get-it',
            'md5': '4701209ac99095592e73dbba21889690',
            'info_dict': {
                'id': 'v15eqxl',
                'ext': 'mp4',
                'channel': 'Mr Producer Media',
                'duration': 92,
                'title': '911 Audio From The Man Who Wanted To Kill Supreme Court Justice Kavanaugh',
                'channel_url': 'https://rumble.com/c/RichSementa',
                'thumbnail': 'https://sp.rmbl.ws/s8/1/P/j/f/A/PjfAe.OvCc-small-911-Audio-From-The-Man-Who-.jpg',
                'timestamp': 1654892716,
                'uploader': 'Mr Producer Media',
                'upload_date': '20220610',
                'live_status': 'not_live',
            }
        },
    ]

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

        sys_msg = traverse_obj(video, ('sys', 'msg'))
        if sys_msg:
            self.report_warning(sys_msg, video_id=video_id)

        if video.get('live') == 0:
            live_status = 'not_live' if video.get('livestream_has_dvr') is None else 'was_live'
        elif video.get('live') == 1:
            live_status = 'is_upcoming' if video.get('livestream_has_dvr') else 'was_live'
        elif video.get('live') == 2:
            live_status = 'is_live'
        else:
            live_status = None

        formats = []
        for ext, ext_info in (video.get('ua') or {}).items():
            for height, video_info in (ext_info or {}).items():
                meta = video_info.get('meta') or {}
                if not video_info.get('url'):
                    continue
                if ext == 'hls':
                    if meta.get('live') is True and video.get('live') == 1:
                        live_status = 'post_live'
                    formats.extend(self._extract_m3u8_formats(
                        video_info['url'], video_id,
                        ext='mp4', m3u8_id='hls', fatal=False, live=live_status == 'is_live'))
                    continue
                formats.append({
                    'ext': ext,
                    'url': video_info['url'],
                    'format_id': '%s-%sp' % (ext, height),
                    'height': int_or_none(height),
                    'fps': video.get('fps'),
                    **traverse_obj(meta, {
                        'tbr': 'bitrate',
                        'filesize': 'size',
                        'width': 'w',
                        'height': 'h',
                    }, expected_type=lambda x: int(x) or None)
                })

        subtitles = {
            lang: [{
                'url': sub_info['path'],
                'name': sub_info.get('language') or '',
            }] for lang, sub_info in (video.get('cc') or {}).items() if sub_info.get('path')
        }

        author = video.get('author') or {}
        thumbnails = traverse_obj(video, ('t', ..., {'url': 'i', 'width': 'w', 'height': 'h'}))
        if not thumbnails and video.get('i'):
            thumbnails = [{'url': video['i']}]

        if live_status in {'is_live', 'post_live'}:
            duration = None
        else:
            duration = int_or_none(video.get('duration'))

        return {
            'id': video_id,
            'title': unescapeHTML(video.get('title')),
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


class RumbleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rumble\.com/(?P<id>v(?!ideos)[\w.-]+)[^/]*$'
    _EMBED_REGEX = [r'<a class=video-item--a href=(?P<url>/v[\w.-]+\.html)>']
    _TESTS = [{
        'add_ie': ['RumbleEmbed'],
        'url': 'https://rumble.com/vdmum1-moose-the-dog-helps-girls-dig-a-snow-fort.html',
        'md5': '53af34098a7f92c4e51cf0bd1c33f009',
        'info_dict': {
            'id': 'vb0ofn',
            'ext': 'mp4',
            'timestamp': 1612662578,
            'uploader': 'LovingMontana',
            'channel': 'LovingMontana',
            'upload_date': '20210207',
            'title': 'Winter-loving dog helps girls dig a snow fort ',
            'description': 'Moose the dog is more than happy to help with digging out this epic snow fort. Great job, Moose!',
            'channel_url': 'https://rumble.com/c/c-546523',
            'thumbnail': r're:https://.+\.jpg',
            'duration': 103,
            'like_count': int,
            'view_count': int,
            'live_status': 'not_live',
        }
    }, {
        'url': 'http://www.rumble.com/vDMUM1?key=value',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://rumble.com/videos?page=2',
        'playlist_count': 25,
        'info_dict': {
            'id': 'videos?page=2',
            'title': 'All videos',
            'description': 'Browse videos uploaded to Rumble.com',
            'age_limit': 0,
        },
    }, {
        'url': 'https://rumble.com/live-videos',
        'playlist_mincount': 19,
        'info_dict': {
            'id': 'live-videos',
            'title': 'Live Videos',
            'description': 'Live videos on Rumble.com',
            'age_limit': 0,
        },
    }, {
        'url': 'https://rumble.com/search/video?q=rumble&sort=views',
        'playlist_count': 24,
        'info_dict': {
            'id': 'video?q=rumble&sort=views',
            'title': 'Search results for: rumble',
            'age_limit': 0,
        },
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        url_info = next(RumbleEmbedIE.extract_from_webpage(self._downloader, url, webpage), None)
        if not url_info:
            raise UnsupportedError(url)

        release_ts_str = self._search_regex(
            r'(?:Livestream begins|Streamed on):\s+<time datetime="([^"]+)',
            webpage, 'release date', fatal=False, default=None)
        view_count_str = self._search_regex(r'<span class="media-heading-info">([\d,]+) Views',
                                            webpage, 'view count', fatal=False, default=None)

        return self.url_result(
            url_info['url'], ie_key=url_info['ie_key'], url_transparent=True,
            view_count=parse_count(view_count_str),
            release_timestamp=parse_iso8601(release_ts_str),
            like_count=parse_count(get_element_by_class('rumbles-count', webpage)),
            description=clean_html(get_element_by_class('media-description', webpage)),
        )


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

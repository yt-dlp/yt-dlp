import itertools
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    UnsupportedError,
    clean_html,
    extract_attributes,
    format_field,
    get_element_by_class,
    get_elements_html_by_class,
    int_or_none,
    join_nonempty,
    parse_count,
    parse_iso8601,
    traverse_obj,
    unescapeHTML,
    urljoin,
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
            'thumbnail': r're:https://.+\.jpg',
            'duration': 234,
            'uploader': 'WMAR',
            'live_status': 'not_live',
        },
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
            'thumbnail': r're:https://.+\.jpg',
            'duration': 901,
            'uploader': 'CTNews',
            'live_status': 'not_live',
        },
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
                        'ext': 'vtt',
                    },
                ],
            },
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://rumble.com/embed/v1essrt',
        'info_dict': {
            'id': 'v1essrt',
            'ext': 'mp4',
            'title': 'startswith:lofi hip hop radio 📚 - beats to relax/study to',
            'timestamp': 1661519399,
            'upload_date': '20220826',
            'channel_url': 'https://rumble.com/c/LofiGirl',
            'channel': 'Lofi Girl',
            'thumbnail': r're:https://.+\.jpg',
            'uploader': 'Lofi Girl',
            'live_status': 'is_live',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://rumble.com/embed/v1amumr',
        'info_dict': {
            'id': 'v1amumr',
            'ext': 'mp4',
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
        'params': {'skip_download': True},
    }, {
        'url': 'https://rumble.com/embed/v6pezdb',
        'info_dict': {
            'id': 'v6pezdb',
            'ext': 'mp4',
            'title': '"Es war einmal ein Mädchen" – Ein filmisches Zeitzeugnis aus Leningrad 1944',
            'uploader': 'RT DE',
            'channel': 'RT DE',
            'channel_url': 'https://rumble.com/c/RTDE',
            'duration': 309,
            'thumbnail': 'https://1a-1791.com/video/fww1/dc/s8/1/n/z/2/y/nz2yy.qR4e-small-Es-war-einmal-ein-Mdchen-Ei.jpg',
            'timestamp': 1743703500,
            'upload_date': '20250403',
            'live_status': 'not_live',
        },
        'params': {'skip_download': True},
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
                'thumbnail': 'https://sp.rmbl.ws/s8/1/P/j/f/A/PjfAe.qR4e-small-911-Audio-From-The-Man-Who-.jpg',
                'timestamp': 1654892716,
                'uploader': 'Mr Producer Media',
                'upload_date': '20220610',
                'live_status': 'not_live',
            },
        },
    ]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        embeds = tuple(super()._extract_embed_urls(url, webpage))
        if embeds:
            return embeds
        return [f'https://rumble.com/embed/{mobj.group("id")}' for mobj in re.finditer(
            r'<script>[^<]*\bRumble\(\s*"play"\s*,\s*{[^}]*[\'"]?video[\'"]?\s*:\s*[\'"](?P<id>[0-9a-z]+)[\'"]', webpage)]

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
        for format_type, format_info in (video.get('ua') or {}).items():
            if isinstance(format_info, dict):
                for height, video_info in format_info.items():
                    if not traverse_obj(video_info, ('meta', 'h', {int_or_none})):
                        video_info.setdefault('meta', {})['h'] = height
                format_info = format_info.values()

            for video_info in format_info:
                meta = video_info.get('meta') or {}
                if not video_info.get('url'):
                    continue
                # With default query params returns m3u8 variants which are duplicates, without returns tar files
                if format_type == 'tar':
                    continue
                if format_type == 'hls':
                    if meta.get('live') is True and video.get('live') == 1:
                        live_status = 'post_live'
                    formats.extend(self._extract_m3u8_formats(
                        video_info['url'], video_id,
                        ext='mp4', m3u8_id='hls', fatal=False, live=live_status == 'is_live'))
                    continue
                is_timeline = format_type == 'timeline'
                is_audio = format_type == 'audio'
                formats.append({
                    'acodec': 'none' if is_timeline else None,
                    'vcodec': 'none' if is_audio else None,
                    'url': video_info['url'],
                    'format_id': join_nonempty(format_type, format_field(meta, 'h', '%sp')),
                    'format_note': 'Timeline' if is_timeline else None,
                    'fps': None if is_timeline or is_audio else video.get('fps'),
                    **traverse_obj(meta, {
                        'tbr': ('bitrate', {int_or_none}),
                        'filesize': ('size', {int_or_none}),
                        'width': ('w', {int_or_none}),
                        'height': ('h', {int_or_none}),
                    }),
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
    _EMBED_REGEX = [
        r'<a class=video-item--a href=(?P<url>/v[\w.-]+\.html)>',
        r'<a[^>]+class="videostream__link link"[^>]+href=(?P<url>/v[\w.-]+\.html)[^>]*>']
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
            'dislike_count': int,
            'view_count': int,
            'live_status': 'not_live',
        },
    }, {
        'url': 'http://www.rumble.com/vDMUM1?key=value',
        'only_matching': True,
    }, {
        'note': 'timeline format',
        'url': 'https://rumble.com/v2ea9qb-the-u.s.-cannot-hide-this-in-ukraine-anymore-redacted-with-natali-and-clayt.html',
        'md5': '40d61fec6c0945bca3d0e1dc1aa53d79',
        'params': {'format': 'wv'},
        'info_dict': {
            'id': 'v2bou5f',
            'ext': 'mp4',
            'uploader': 'Redacted News',
            'upload_date': '20230322',
            'timestamp': 1679445010,
            'title': 'The U.S. CANNOT hide this in Ukraine anymore | Redacted with Natali and Clayton Morris',
            'duration': 892,
            'channel': 'Redacted News',
            'description': 'md5:aaad0c5c3426d7a361c29bdaaced7c42',
            'channel_url': 'https://rumble.com/c/Redacted',
            'live_status': 'not_live',
            'thumbnail': 'https://sp.rmbl.ws/s8/1/d/x/2/O/dx2Oi.qR4e-small-The-U.S.-CANNOT-hide-this-i.jpg',
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
        },
    }, {
        'url': 'https://rumble.com/v2e7fju-the-covid-twitter-files-drop-protecting-fauci-while-censoring-the-truth-wma.html',
        'info_dict': {
            'id': 'v2blzyy',
            'ext': 'mp4',
            'live_status': 'was_live',
            'release_timestamp': 1679446804,
            'description': 'md5:2ac4908ccfecfb921f8ffa4b30c1e636',
            'release_date': '20230322',
            'timestamp': 1679445692,
            'duration': 4435,
            'upload_date': '20230322',
            'title': 'The Covid Twitter Files Drop: Protecting Fauci While Censoring The Truth w/Matt Taibbi',
            'uploader': 'Kim Iversen',
            'channel_url': 'https://rumble.com/c/KimIversen',
            'channel': 'Kim Iversen',
            'thumbnail': 'https://sp.rmbl.ws/s8/1/6/b/w/O/6bwOi.qR4e-small-The-Covid-Twitter-Files-Dro.jpg',
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
        },
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://rumble.com/videos?page=2',
        'playlist_mincount': 24,
        'info_dict': {
            'id': 'videos?page=2',
            'title': 'All videos',
            'description': 'Browse videos uploaded to Rumble.com',
            'age_limit': 0,
        },
    }, {
        'url': 'https://rumble.com/browse/live',
        'playlist_mincount': 25,
        'info_dict': {
            'id': 'live',
            'title': 'Browse',
            'age_limit': 0,
        },
    }, {
        'url': 'https://rumble.com/search/video?q=rumble&sort=views',
        'playlist_mincount': 24,
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

        return {
            '_type': 'url_transparent',
            'ie_key': url_info['ie_key'],
            'url': url_info['url'],
            'release_timestamp': parse_iso8601(self._search_regex(
                r'(?:Livestream begins|Streamed on):\s+<time datetime="([^"]+)', webpage, 'release date', default=None)),
            'view_count': int_or_none(self._search_regex(
                r'"userInteractionCount"\s*:\s*(\d+)', webpage, 'view count', default=None)),
            'like_count': parse_count(self._search_regex(
                r'<span data-js="rumbles_up_votes">\s*([\d,.KM]+)', webpage, 'like count', default=None)),
            'dislike_count': parse_count(self._search_regex(
                r'<span data-js="rumbles_down_votes">\s*([\d,.KM]+)', webpage, 'dislike count', default=None)),
            'description': clean_html(get_element_by_class('media-description', webpage)),
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
                webpage = self._download_webpage(f'{url}?page={page}', playlist_id, note=f'Downloading page {page}')
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                    break
                raise
            for video_url in traverse_obj(
                get_elements_html_by_class('videostream__link', webpage), (..., {extract_attributes}, 'href'),
            ):
                yield self.url_result(urljoin('https://rumble.com', video_url))

    def _real_extract(self, url):
        url, playlist_id = self._match_valid_url(url).groups()
        return self.playlist_result(self.entries(url, playlist_id), playlist_id=playlist_id)

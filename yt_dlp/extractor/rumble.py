import itertools
import re

from .common import InfoExtractor
from ..compat import compat_str, compat_HTTPError
from ..utils import (
    determine_ext,
    int_or_none,
    parse_iso8601,
    try_get,
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
        }
    }, {
        'url': 'https://rumble.com/embed/ufe9n.v5pv5f',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [
        {
            'note': 'Rumble embed',
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
                'channel_url': 'https://rumble.com/c/c-546523',
                'thumbnail': 'https://sp.rmbl.ws/s8/1/5/f/x/x/5fxxb.OvCc.1-small-Moose-The-Dog-Helps-Girls-D.jpg',
                'duration': 103,
            }
        },
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
            'https://rumble.com/embedJS/', video_id,
            query={'request': 'video', 'v': video_id})
        title = unescapeHTML(video['title'])

        formats = []
        for height, ua in (video.get('ua') or {}).items():
            for i in range(2):
                f_url = try_get(ua, lambda x: x[i], compat_str)
                if f_url:
                    ext = determine_ext(f_url)
                    f = {
                        'ext': ext,
                        'format_id': '%s-%sp' % (ext, height),
                        'height': int_or_none(height),
                        'url': f_url,
                    }
                    bitrate = try_get(ua, lambda x: x[i + 2]['bitrate'])
                    if bitrate:
                        f['tbr'] = int_or_none(bitrate)
                    formats.append(f)
        self._sort_formats(formats)

        subtitles = {
            lang: [{
                'url': sub_info['path'],
                'name': sub_info.get('language') or '',
            }] for lang, sub_info in (video.get('cc') or {}).items() if sub_info.get('path')
        }

        author = video.get('author') or {}

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': video.get('i'),
            'timestamp': parse_iso8601(video.get('pubDate')),
            'channel': author.get('name'),
            'channel_url': author.get('url'),
            'duration': int_or_none(video.get('duration')),
            'uploader': author.get('name'),
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
        'playlist_count': 4,
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

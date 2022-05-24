import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    parse_iso8601,
)


class AirMozillaIE(InfoExtractor):
    _VALID_URL = r'https?://air\.mozilla\.org/(?P<id>[0-9a-z-]+)/?'
    _TEST = {
        'url': 'https://air.mozilla.org/privacy-lab-a-meetup-for-privacy-minded-people-in-san-francisco/',
        'md5': '8d02f53ee39cf006009180e21df1f3ba',
        'info_dict': {
            'id': '6x4q2w',
            'ext': 'mp4',
            'title': 'Privacy Lab - a meetup for privacy minded people in San Francisco',
            'thumbnail': r're:https?://.*/poster\.jpg',
            'description': 'Brings together privacy professionals and others interested in privacy at for-profits, non-profits, and NGOs in an effort to contribute to the state of the ecosystem...',
            'timestamp': 1422487800,
            'upload_date': '20150128',
            'location': 'SFO Commons',
            'duration': 3780,
            'view_count': int,
            'categories': ['Main', 'Privacy'],
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._html_search_regex(r'//vid\.ly/(.*?)/embed', webpage, 'id')

        embed_script = self._download_webpage('https://vid.ly/{0}/embed'.format(video_id), video_id)
        jwconfig = self._parse_json(self._search_regex(
            r'initCallback\((.*)\);', embed_script, 'metadata'), video_id)['config']

        info_dict = self._parse_jwplayer_data(jwconfig, video_id)
        view_count = int_or_none(self._html_search_regex(
            r'Views since archived: ([0-9]+)',
            webpage, 'view count', fatal=False))
        timestamp = parse_iso8601(self._html_search_regex(
            r'<time datetime="(.*?)"', webpage, 'timestamp', fatal=False))
        duration = parse_duration(self._search_regex(
            r'Duration:\s*(\d+\s*hours?\s*\d+\s*minutes?)',
            webpage, 'duration', fatal=False))

        info_dict.update({
            'id': video_id,
            'title': self._og_search_title(webpage),
            'url': self._og_search_url(webpage),
            'display_id': display_id,
            'description': self._og_search_description(webpage),
            'timestamp': timestamp,
            'location': self._html_search_regex(r'Location: (.*)', webpage, 'location', default=None),
            'duration': duration,
            'view_count': view_count,
            'categories': re.findall(r'<a href=".*?" class="channel">(.*?)</a>', webpage),
        })

        return info_dict

import re

from .common import InfoExtractor
from ..utils import url_or_none, merge_dicts


class AngelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?angel\.com/watch/(?P<series>[^/?#]+)/episode/(?P<id>[\w-]+)/season-(?P<season_number>\d+)/episode-(?P<episode_number>\d+)/(?P<title>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.angel.com/watch/tuttle-twins/episode/2f3d0382-ea82-4cdc-958e-84fbadadc710/season-1/episode-1/when-laws-give-you-lemons',
        'md5': '4734e5cfdd64a568e837246aa3eaa524',
        'info_dict': {
            'id': '2f3d0382-ea82-4cdc-958e-84fbadadc710',
            'ext': 'mp4',
            'title': 'Tuttle Twins S1 E1: When Laws Give You Lemons',
            'description': 'md5:73b704897c20ab59c433a9c0a8202d5e',
            'thumbnail': r're:^https?://images.angelstudios.com/.*\.jpeg$',
            'duration': 1359.0
        }
    }, {
        'url': 'https://www.angel.com/watch/the-chosen/episode/8dfb714d-bca5-4812-8125-24fb9514cd10/season-1/episode-1/i-have-called-you-by-name',
        'md5': 'e4774bad0a5f0ad2e90d175cafdb797d',
        'info_dict': {
            'id': '8dfb714d-bca5-4812-8125-24fb9514cd10',
            'ext': 'mp4',
            'title': 'The Chosen S1 E1: I Have Called You By Name',
            'description': 'md5:aadfb4827a94415de5ff6426e6dee3be',
            'thumbnail': r're:^https?://images.angelstudios.com/.*\.jpeg$',
            'duration': 3276.0
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_ld = self._search_json_ld(webpage, video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            json_ld.pop('url'), video_id, note='Downloading HD m3u8 information')

        return merge_dicts(json_ld, {
            'id': video_id,
            'title': self._og_search_title,
            'description': self._og_search_description(webpage),
            'thumbnails': [{
                # Second group has unnecessary data about transformations of the thumbnail
                'url': re.sub(r'(/upload)/.+(/angel-app/.+)$', r'\1\2.jpeg', item['url'])
            } for item in json_ld.pop('thumbnails') or [] if url_or_none(item.get('url'))],
            'formats': formats,
            'subtitles': subtitles
        })

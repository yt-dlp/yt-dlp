from yt_dlp.utils import url_or_none
from .common import InfoExtractor
import re


class AngelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?angel\.com/watch/(?P<series>[a-zA-Z\-]+)/episode/(?P<id>[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12})/season-(?P<season_number>[0-9]+)/episode-(?P<episode_number>[0-9]+)/(?P<title>[a-zA-Z\-]+)'
    _TESTS = [{
        'url': 'https://www.angel.com/watch/tuttle-twins/episode/2f3d0382-ea82-4cdc-958e-84fbadadc710/season-1/episode-1/when-laws-give-you-lemons',
        'md5': '4734e5cfdd64a568e837246aa3eaa524',
        'info_dict': {
            'id': '2f3d0382-ea82-4cdc-958e-84fbadadc710',
            'ext': 'mp4',
            'title': 'Tuttle Twins S1 E1: When Laws Give You Lemons',
            'description': 'When Grandma Gabby moves in with the Tuttle family, she takes her twin grandkids on a wheelchair time machine to France and the Old West to learn about laws and try to save their lemonade stand.',
            'thumbnail': r're:^https?://images.angelstudios.com/.*\.jpeg$'
        }
    }, {
        'url': 'https://www.angel.com/watch/the-chosen/episode/8dfb714d-bca5-4812-8125-24fb9514cd10/season-1/episode-1/i-have-called-you-by-name',
        'md5': 'e4774bad0a5f0ad2e90d175cafdb797d',
        'info_dict': {
            'id': '8dfb714d-bca5-4812-8125-24fb9514cd10',
            'ext': 'mp4',
            'title': 'The Chosen S1 E1: I Have Called You By Name',
            'description': 'Two brothers struggle with their tax debts to Rome while a woman in the Red Quarter wrestles with her demons.',
            'thumbnail': r're:^https?://images.angelstudios.com/.*\.jpeg$'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_ld = self._search_json_ld(webpage, video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            json_ld.get('url'), video_id, m3u8_id='hls', note='Downloading HD m3u8 information',
            errnote='Unable to download HD m3u8 information')

        return {
            'id': video_id,
            'title': json_ld.get('title') or self._og_search_title or '',
            'description': json_ld.get('description') or self._og_search_description(webpage) or None,
            'thumbnails': [{
                # Second group has unnecessary data about transformations of the thumbnail
                'url': re.sub(r'^(.+/upload)(/.+)(/angel-app/.+)$', r'\1\3.jpeg', item.get('url'))
            } for item in json_ld.get('thumbnails') if url_or_none(item.get('url'))],
            'formats': formats,
            'subtitles': subtitles
        }

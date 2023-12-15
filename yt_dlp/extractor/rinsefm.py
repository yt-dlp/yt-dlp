from datetime import datetime, timezone

from .common import InfoExtractor


class RinseFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/episodes/(?P<id>.+)'
    _TESTS = [{
        'url': 'https://rinse.fm/episodes/cameo-blush-01-09-2023-2300/',
        'md5': '9284abbd785e6b86e67d1cdca6224feb',
        'info_dict': {
            'id': '1351562',
            'ext': 'mp3',
            'title': 'Cameo Blush - 01/09/2023 - 23:00',
            'thumbnail': r're:^https?://.*\.JPG$',
            'release_timestamp': 1693522800,
            'release_date': '20230831'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        info = self._search_nextjs_data(webpage, video_id)

        entry = info['props']['pageProps']['entry']

        track_id = entry['id']
        title = entry['title']

        date_obj = datetime.fromisoformat(entry['episodeDate'])
        unix_timestamp = int(date_obj.replace(tzinfo=timezone.utc).timestamp())

        url = entry['fileUrl']
        thumbnail = "https://rinse.imgix.net/media/" + entry['featuredImage'][0]['filename']

        return {
            'id': track_id,
            'title': title,
            'url': url,
            'release_timestamp': unix_timestamp,
            'thumbnail': thumbnail
        }

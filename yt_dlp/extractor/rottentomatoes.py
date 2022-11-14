from .common import InfoExtractor
from .internetvideoarchive import InternetVideoArchiveIE


class RottenTomatoesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rottentomatoes\.com/m/[^/]+/trailers/(?P<id>\d+)'

    _TEST = {
        'url': 'http://www.rottentomatoes.com/m/toy_story_3/trailers/11028566/',
        'info_dict': {
            'id': '11028566',
            'ext': 'mp4',
            'title': 'Toy Story 3',
            'description': 'From the creators of the beloved TOY STORY films, comes a story that will reunite the gang in a whole new way.',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        iva_id = self._search_regex(r'publishedid=(\d+)', webpage, 'internet video archive id')

        return {
            '_type': 'url_transparent',
            'url': 'http://video.internetvideoarchive.net/player/6/configuration.ashx?domain=www.videodetective.com&customerid=69249&playerid=641&publishedid=' + iva_id,
            'ie_key': InternetVideoArchiveIE.ie_key(),
            'id': video_id,
            'title': self._og_search_title(webpage),
        }

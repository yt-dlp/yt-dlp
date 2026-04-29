from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class AMCNetworksIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:amc|bbcamerica|ifc|(?:we|sundance)tv)\.com/(?P<id>(?:movies|shows(?:/[^/?#]+)+)/[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.amc.com/shows/dark-winds/videos/dark-winds-a-look-at-season-3--1072027',
        'info_dict': {
            'id': '6369261343112',
            'ext': 'mp4',
            'title': 'Dark Winds: A Look at Season 3',
            'uploader_id': '6240731308001',
            'duration': 176.427,
            'thumbnail': r're:https://[^/]+\.boltdns\.net/.+/image\.jpg',
            'tags': [],
            'timestamp': 1740414792,
            'upload_date': '20250224',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://www.bbcamerica.com/shows/the-hunt/full-episodes/season-1/episode-01-the-hardest-challenge',
        'only_matching': True,
    }, {
        'url': 'http://www.amc.com/shows/preacher/full-episodes/season-01/episode-00/pilot',
        'only_matching': True,
    }, {
        'url': 'http://www.wetv.com/shows/million-dollar-matchmaker/season-01/episode-06-the-dumped-dj-and-shallow-hal',
        'only_matching': True,
    }, {
        'url': 'http://www.ifc.com/movies/chaos',
        'only_matching': True,
    }, {
        'url': 'http://www.bbcamerica.com/shows/doctor-who/full-episodes/the-power-of-the-daleks/episode-01-episode-1-color-version',
        'only_matching': True,
    }, {
        'url': 'http://www.wetv.com/shows/mama-june-from-not-to-hot/full-episode/season-01/thin-tervention',
        'only_matching': True,
    }, {
        'url': 'http://www.wetv.com/shows/la-hair/videos/season-05/episode-09-episode-9-2/episode-9-sneak-peek-3',
        'only_matching': True,
    }, {
        'url': 'https://www.sundancetv.com/shows/riviera/full-episodes/season-1/episode-01-episode-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        initial_data = self._search_json(
            r'window\.initialData\s*=\s*JSON\.parse\(String\.raw`', webpage, 'initial data', display_id)
        video_id = traverse_obj(initial_data, ('initialData', 'properties', 'videoId', {str}))
        if not video_id:  # All locked videos are now DRM-protected
            self.report_drm(display_id)
        account_id = initial_data['config']['brightcove']['accountId']
        player_id = initial_data['config']['brightcove']['playerId']

        return self.url_result(
            f'https://players.brightcove.net/{account_id}/{player_id}_default/index.html?videoId={video_id}',
            BrightcoveNewIE, video_id)

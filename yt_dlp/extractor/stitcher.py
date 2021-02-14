from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    ExtractorError,
    int_or_none,
    str_or_none,
    try_get,
)


class StitcherIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?stitcher\.com/(?:podcast|show)/(?:[^/]+/)+e(?:pisode)?/(?:(?P<display_id>[^/#?&]+?)-)?(?P<id>\d+)(?:[/#?&]|$)'
    _TESTS = [{
        'url': 'http://www.stitcher.com/podcast/the-talking-machines/e/40789481?autoplay=true',
        'md5': 'e9635098e0da10b21a0e2b85585530f6',
        'info_dict': {
            'id': '40789481',
            'ext': 'mp3',
            'title': 'Machine Learning Mastery and Cancer Clusters',
            'description': 'md5:547adb4081864be114ae3831b4c2b42f',
            'duration': 1604,
            'thumbnail': r're:^https?://.*\.jpg',
            'upload_date': '20180126',
            'timestamp': 1516989316,
        },
    }, {
        'url': 'http://www.stitcher.com/podcast/panoply/vulture-tv/e/the-rare-hourlong-comedy-plus-40846275?autoplay=true',
        'info_dict': {
            'id': '40846275',
            'display_id': 'the-rare-hourlong-comedy-plus',
            'ext': 'mp3',
            'title': "The CW's 'Crazy Ex-Girlfriend'",
            'description': 'md5:04f1e2f98eb3f5cbb094cea0f9e19b17',
            'duration': 2235,
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Page Not Found',
    }, {
        # escaped title
        'url': 'http://www.stitcher.com/podcast/marketplace-on-stitcher/e/40910226?autoplay=true',
        'only_matching': True,
    }, {
        'url': 'http://www.stitcher.com/podcast/panoply/getting-in/e/episode-2a-how-many-extracurriculars-should-i-have-40876278?autoplay=true',
        'only_matching': True,
    }, {
        'url': 'https://www.stitcher.com/show/threedom/episode/circles-on-a-stick-200212584',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id, audio_id = re.match(self._VALID_URL, url).groups()

        resp = self._download_json(
            'https://api.prod.stitcher.com/episode/' + audio_id,
            display_id or audio_id)
        episode = try_get(resp, lambda x: x['data']['episodes'][0], dict)
        if not episode:
            raise ExtractorError(resp['errors'][0]['message'], expected=True)

        title = episode['title'].strip()
        audio_url = episode['audio_url']

        thumbnail = None
        show_id = episode.get('show_id')
        if show_id and episode.get('classic_id') != -1:
            thumbnail = 'https://stitcher-classic.imgix.net/feedimages/%s.jpg' % show_id

        return {
            'id': audio_id,
            'display_id': display_id,
            'title': title,
            'description': clean_html(episode.get('html_description') or episode.get('description')),
            'duration': int_or_none(episode.get('duration')),
            'thumbnail': thumbnail,
            'url': audio_url,
            'vcodec': 'none',
            'timestamp': int_or_none(episode.get('date_created')),
            'season_number': int_or_none(episode.get('season')),
            'season_id': str_or_none(episode.get('season_id')),
        }

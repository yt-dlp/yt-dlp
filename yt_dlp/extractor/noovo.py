from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    smuggle_url,
    try_get,
)


class NoovoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?noovo\.ca/videos/(?P<id>[^/]+/[^/?#&]+)'
    _TESTS = [{
        # clip
        'url': 'http://noovo.ca/videos/rpm-plus/chrysler-imperial',
        'info_dict': {
            'id': '5386045029001',
            'ext': 'mp4',
            'title': 'Chrysler Imperial',
            'description': 'md5:de3c898d1eb810f3e6243e08c8b4a056',
            'timestamp': 1491399228,
            'upload_date': '20170405',
            'uploader_id': '618566855001',
            'series': 'RPM+',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # episode
        'url': 'http://noovo.ca/videos/l-amour-est-dans-le-pre/episode-13-8',
        'info_dict': {
            'id': '5395865725001',
            'title': 'Épisode 13 : Les retrouvailles',
            'description': 'md5:888c3330f0c1b4476c5bc99a1c040473',
            'ext': 'mp4',
            'timestamp': 1492019320,
            'upload_date': '20170412',
            'uploader_id': '618566855001',
            'series': "L'amour est dans le pré",
            'season_number': 5,
            'episode': 'Épisode 13',
            'episode_number': 13,
        },
        'params': {
            'skip_download': True,
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/618566855001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        brightcove_id = self._search_regex(
            r'data-video-id=["\'](\d+)', webpage, 'brightcove id')

        data = self._parse_json(
            self._search_regex(
                r'(?s)dataLayer\.push\(\s*({.+?})\s*\);', webpage, 'data',
                default='{}'),
            video_id, transform_source=js_to_json, fatal=False)

        title = try_get(
            data, lambda x: x['video']['nom'],
            str) or self._html_search_meta(
            'dcterms.Title', webpage, 'title', fatal=True)

        description = self._html_search_meta(
            ('dcterms.Description', 'description'), webpage, 'description')

        series = try_get(
            data, lambda x: x['emission']['nom']) or self._search_regex(
            r'<div[^>]+class="banner-card__subtitle h4"[^>]*>([^<]+)',
            webpage, 'series', default=None)

        season_el = try_get(data, lambda x: x['emission']['saison'], dict) or {}
        season = try_get(season_el, lambda x: x['nom'], str)
        season_number = int_or_none(try_get(season_el, lambda x: x['numero']))

        episode_el = try_get(season_el, lambda x: x['episode'], dict) or {}
        episode = try_get(episode_el, lambda x: x['nom'], str)
        episode_number = int_or_none(try_get(episode_el, lambda x: x['numero']))

        return {
            '_type': 'url_transparent',
            'ie_key': BrightcoveNewIE.ie_key(),
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id,
                {'geo_countries': ['CA']}),
            'id': brightcove_id,
            'title': title,
            'description': description,
            'series': series,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
        }

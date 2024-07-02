from .common import InfoExtractor
from ..utils import (
    clean_html,
    clean_podcast_url,
    get_element_by_class,
    int_or_none,
    parse_iso8601,
    try_get,
)


class ApplePodcastsIE(InfoExtractor):
    _VALID_URL = r'https?://podcasts\.apple\.com/(?:[^/]+/)?podcast(?:/[^/]+){1,2}.*?\bi=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/us/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'md5': '41dc31cd650143e530d9423b6b5a344f',
        'info_dict': {
            'id': '1000482637777',
            'ext': 'mp3',
            'title': '207 - Whitney Webb Returns',
            'description': 'md5:75ef4316031df7b41ced4e7b987f79c6',
            'upload_date': '20200705',
            'timestamp': 1593932400,
            'duration': 6454,
            'series': 'The Tim Dillon Show',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/id1135137367?i=1000482637777',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        episode_data = {}
        ember_data = {}
        # new page type 2021-11
        amp_data = self._parse_json(self._search_regex(
            r'(?s)id="shoebox-media-api-cache-amp-podcasts"[^>]*>\s*({.+?})\s*<',
            webpage, 'AMP data', default='{}'), episode_id, fatal=False) or {}
        amp_data = try_get(amp_data,
                           lambda a: self._parse_json(
                               next(a[x] for x in iter(a) if episode_id in x),
                               episode_id),
                           dict) or {}
        amp_data = amp_data.get('d') or []
        episode_data = try_get(
            amp_data,
            lambda a: next(x for x in a
                           if x['type'] == 'podcast-episodes' and x['id'] == episode_id),
            dict)
        if not episode_data:
            # try pre 2021-11 page type: TODO: consider deleting if no longer used
            ember_data = self._parse_json(self._search_regex(
                r'(?s)id="shoebox-ember-data-store"[^>]*>\s*({.+?})\s*<',
                webpage, 'ember data'), episode_id) or {}
            ember_data = ember_data.get(episode_id) or ember_data
            episode_data = try_get(ember_data, lambda x: x['data'], dict)
        episode = episode_data['attributes']
        description = episode.get('description') or {}

        series = None
        for inc in (amp_data or ember_data.get('included') or []):
            if inc.get('type') == 'media/podcast':
                series = try_get(inc, lambda x: x['attributes']['name'])
        series = series or clean_html(get_element_by_class('podcast-header__identity', webpage))

        return {
            'id': episode_id,
            'title': episode.get('name'),
            'url': clean_podcast_url(episode['assetUrl']),
            'description': description.get('standard') or description.get('short'),
            'timestamp': parse_iso8601(episode.get('releaseDateTime')),
            'duration': int_or_none(episode.get('durationInMilliseconds'), 1000),
            'series': series,
            'thumbnail': self._og_search_thumbnail(webpage),
            'vcodec': 'none',
        }

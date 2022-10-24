import json

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
)


class AmericasTestKitchenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?americastestkitchen\.com/(?:cooks(?:country|illustrated)/)?(?P<resource_type>episode|videos)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.americastestkitchen.com/episode/582-weeknight-japanese-suppers',
        'md5': 'b861c3e365ac38ad319cfd509c30577f',
        'info_dict': {
            'id': '5b400b9ee338f922cb06450c',
            'title': 'Japanese Suppers',
            'ext': 'mp4',
            'display_id': 'weeknight-japanese-suppers',
            'description': 'md5:64e606bfee910627efc4b5f050de92b3',
            'timestamp': 1523304000,
            'upload_date': '20180409',
            'release_date': '20180409',
            'series': 'America\'s Test Kitchen',
            'season': 'Season 18',
            'episode': 'Japanese Suppers',
            'season_number': 18,
            'episode_number': 15,
            'duration': 1376,
            'thumbnail': r're:^https?://',
            'average_rating': 0,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Metadata parsing behaves differently for newer episodes (705) as opposed to older episodes (582 above)
        'url': 'https://www.americastestkitchen.com/episode/705-simple-chicken-dinner',
        'md5': '06451608c57651e985a498e69cec17e5',
        'info_dict': {
            'id': '5fbe8c61bda2010001c6763b',
            'title': 'Simple Chicken Dinner',
            'ext': 'mp4',
            'display_id': 'atktv_2103_simple-chicken-dinner_full-episode_web-mp4',
            'description': 'md5:eb68737cc2fd4c26ca7db30139d109e7',
            'timestamp': 1610737200,
            'upload_date': '20210115',
            'release_date': '20210115',
            'series': 'America\'s Test Kitchen',
            'season': 'Season 21',
            'episode': 'Simple Chicken Dinner',
            'season_number': 21,
            'episode_number': 3,
            'duration': 1397,
            'thumbnail': r're:^https?://',
            'view_count': int,
            'average_rating': 0,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.americastestkitchen.com/videos/3420-pan-seared-salmon',
        'only_matching': True,
    }, {
        'url': 'https://www.americastestkitchen.com/cookscountry/episode/564-when-only-chocolate-will-do',
        'only_matching': True,
    }, {
        'url': 'https://www.americastestkitchen.com/cooksillustrated/videos/4478-beef-wellington',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        resource_type, video_id = self._match_valid_url(url).groups()
        is_episode = resource_type == 'episode'
        if is_episode:
            resource_type = 'episodes'

        resource = self._download_json(
            'https://www.americastestkitchen.com/api/v6/%s/%s' % (resource_type, video_id), video_id)
        video = resource['video'] if is_episode else resource
        episode = resource if is_episode else resource.get('episode') or {}

        return {
            '_type': 'url_transparent',
            'url': 'https://player.zype.com/embed/%s.js?api_key=jZ9GUhRmxcPvX7M3SlfejB6Hle9jyHTdk2jVxG7wOHPLODgncEKVdPYBhuz9iWXQ' % video['zypeId'],
            'ie_key': 'Zype',
            'description': clean_html(video.get('description')),
            'timestamp': unified_timestamp(video.get('publishDate')),
            'release_date': unified_strdate(video.get('publishDate')),
            'episode_number': int_or_none(episode.get('number')),
            'season_number': int_or_none(episode.get('season')),
            'series': try_get(episode, lambda x: x['show']['title']),
            'episode': episode.get('title'),
        }


class AmericasTestKitchenSeasonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?americastestkitchen\.com(?P<show>/cookscountry)?/episodes/browse/season_(?P<id>\d+)'
    _TESTS = [{
        # ATK Season
        'url': 'https://www.americastestkitchen.com/episodes/browse/season_1',
        'info_dict': {
            'id': 'season_1',
            'title': 'Season 1',
        },
        'playlist_count': 13,
    }, {
        # Cooks Country Season
        'url': 'https://www.americastestkitchen.com/cookscountry/episodes/browse/season_12',
        'info_dict': {
            'id': 'season_12',
            'title': 'Season 12',
        },
        'playlist_count': 13,
    }]

    def _real_extract(self, url):
        show_path, season_number = self._match_valid_url(url).group('show', 'id')
        season_number = int(season_number)

        slug = 'cco' if show_path == '/cookscountry' else 'atk'

        season = 'Season %d' % season_number

        season_search = self._download_json(
            'https://y1fnzxui30-dsn.algolia.net/1/indexes/everest_search_%s_season_desc_production' % slug,
            season, headers={
                'Origin': 'https://www.americastestkitchen.com',
                'X-Algolia-API-Key': '8d504d0099ed27c1b73708d22871d805',
                'X-Algolia-Application-Id': 'Y1FNZXUI30',
            }, query={
                'facetFilters': json.dumps([
                    'search_season_list:' + season,
                    'search_document_klass:episode',
                    'search_show_slug:' + slug,
                ]),
                'attributesToRetrieve': 'description,search_%s_episode_number,search_document_date,search_url,title' % slug,
                'attributesToHighlight': '',
                'hitsPerPage': 1000,
            })

        def entries():
            for episode in (season_search.get('hits') or []):
                search_url = episode.get('search_url')  # always formatted like '/episode/123-title-of-episode'
                if not search_url:
                    continue
                yield {
                    '_type': 'url',
                    'url': f'https://www.americastestkitchen.com{show_path or ""}{search_url}',
                    'id': try_get(episode, lambda e: e['objectID'].split('_')[-1]),
                    'title': episode.get('title'),
                    'description': episode.get('description'),
                    'timestamp': unified_timestamp(episode.get('search_document_date')),
                    'season_number': season_number,
                    'episode_number': int_or_none(episode.get('search_%s_episode_number' % slug)),
                    'ie_key': AmericasTestKitchenIE.ie_key(),
                }

        return self.playlist_result(
            entries(), 'season_%d' % season_number, season)

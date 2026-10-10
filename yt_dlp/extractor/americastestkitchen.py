import itertools
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
    urljoin,
)


class AmericasTestKitchenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:americastestkitchen|cooks(?:country|illustrated))\.com/(?:cooks(?:country|illustrated)/)?(?P<resource_type>episode|videos)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.americastestkitchen.com/episode/582-weeknight-japanese-suppers',
        'md5': 'b861c3e365ac38ad319cfd509c30577f',
        'info_dict': {
            'id': '5b400b9ee338f922cb06450c',
            'title': 'Weeknight Japanese Suppers',
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
    }, {
        'url': 'https://www.cookscountry.com/episode/564-when-only-chocolate-will-do',
        'only_matching': True,
    }, {
        'url': 'https://www.cooksillustrated.com/videos/4478-beef-wellington',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        resource_type, video_id = self._match_valid_url(url).groups()
        is_episode = resource_type == 'episode'
        if is_episode:
            resource_type = 'episodes'

        resource = self._download_json(
            f'https://www.americastestkitchen.com/api/v6/{resource_type}/{video_id}', video_id)
        video = resource['video'] if is_episode else resource
        episode = resource if is_episode else resource.get('episode') or {}

        return {
            '_type': 'url_transparent',
            'url': 'https://player.zype.com/embed/{}.js?api_key=jZ9GUhRmxcPvX7M3SlfejB6Hle9jyHTdk2jVxG7wOHPLODgncEKVdPYBhuz9iWXQ'.format(video['zypeId']),
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
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?(?P<domain>americastestkitchen|cookscountry|cooksillustrated)\.com
        (?:/(?P<path>cookscountry|cooksillustrated))?
        (?:/episodes(?:/browse)?/season[-_](?P<season>\d+))?
        /?(?:[?#]|$)'''
    _SHOWS = {
        'americastestkitchen': ('', 'America\'s Test Kitchen'),
        'cookscountry': ('/cookscountry', 'Cook\'s Country'),
        'cooksillustrated': ('/cooksillustrated', 'Cook\'s Illustrated'),
    }
    _TESTS = [{
        # ATK Season
        'url': 'https://www.americastestkitchen.com/episodes/season-1',
        'info_dict': {
            'id': 'season_1',
            'title': 'Season 1',
        },
        'playlist_mincount': 13,
    }, {
        # Latest ATK Season (new URL scheme)
        'url': 'https://www.americastestkitchen.com/episodes/season-26',
        'info_dict': {
            'id': 'season_26',
            'title': 'Season 26',
        },
        'playlist_count': 26,
    }, {
        # Cooks Country Season
        'url': 'https://www.americastestkitchen.com/cookscountry/episodes/season-12',
        'info_dict': {
            'id': 'season_12',
            'title': 'Season 12',
        },
        'playlist_mincount': 13,
    }, {
        # Old-style URL (redirects to the new season page)
        'url': 'https://www.americastestkitchen.com/episodes/browse/season_1',
        'only_matching': True,
    }, {
        # America's Test Kitchen Series
        'url': 'https://www.americastestkitchen.com/',
        'info_dict': {
            'id': 'americastestkitchen',
            'title': 'America\'s Test Kitchen',
        },
        'playlist_mincount': 558,
    }, {
        # Cooks Country Series
        'url': 'https://www.americastestkitchen.com/cookscountry',
        'info_dict': {
            'id': 'cookscountry',
            'title': 'Cook\'s Country',
        },
        'playlist_mincount': 199,
    }, {
        'url': 'https://www.americastestkitchen.com/cookscountry/',
        'only_matching': True,
    }, {
        'url': 'https://www.cookscountry.com/episodes/browse/season_12',
        'only_matching': True,
    }, {
        'url': 'https://www.cookscountry.com',
        'only_matching': True,
    }, {
        'url': 'https://www.americastestkitchen.com/cooksillustrated/',
        'only_matching': True,
    }, {
        'url': 'https://www.cooksillustrated.com',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, url_path, season = self._match_valid_url(url).group('domain', 'path', 'season')
        show_path, title = self._SHOWS[url_path or domain]
        season = int_or_none(season)

        if season:
            playlist_id = f'season_{season}'
            playlist_title = f'Season {season}'

            def entries():
                yield from self._season_entries(show_path, season)
        else:
            playlist_id = url_path or domain
            playlist_title = title

            def entries():
                for season_number in itertools.count(1):
                    try:
                        yield from self._season_entries(show_path, season_number)
                    except ExtractorError as e:
                        if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                            break
                        raise

        return self.playlist_result(
            entries(), playlist_id, playlist_title)

    def _season_entries(self, show_path, season_number):
        webpage = self._download_webpage(
            f'https://www.americastestkitchen.com{show_path}/episodes/season-{season_number}',
            f'season-{season_number}', f'Downloading season {season_number} webpage')
        seen = set()
        for episode in re.finditer(
                r'<a [^>]*\bhref="(?P<path>/(?:cookscountry/|cooksillustrated/)?episode/(?P<id>\d+)-[^"]+)"[^>]*>\s*<h3[^>]*>(?P<title>[^<]+)</h3>',
                webpage):
            path = episode.group('path')
            if path in seen:
                continue
            seen.add(path)
            yield self.url_result(
                urljoin('https://www.americastestkitchen.com', path),
                AmericasTestKitchenIE, episode.group('id'),
                clean_html(episode.group('title')),
                season_number=season_number)

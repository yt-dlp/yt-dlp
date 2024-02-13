import itertools

from .cbs import CBSBaseIE
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    url_or_none,
)


class ParamountPlusIE(CBSBaseIE):
    _VALID_URL = r'''(?x)
        (?:
            paramountplus:|
            https?://(?:www\.)?(?:
                paramountplus\.com/(?:shows|movies)/(?:video|[^/]+/video|[^/]+)/
        )(?P<id>[\w-]+))'''

    # All tests are blocked outside US
    _TESTS = [{
        'url': 'https://www.paramountplus.com/shows/video/Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k/',
        'info_dict': {
            'id': 'Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k',
            'ext': 'mp4',
            'title': 'CatDog - Climb Every CatDog/The Canine Mutiny',
            'description': 'md5:7ac835000645a69933df226940e3c859',
            'duration': 1426,
            'timestamp': 920264400,
            'upload_date': '19990301',
            'uploader': 'CBSI-NEW',
            'episode_number': 5,
            'thumbnail': r're:https?://.+\.jpg$',
            'season': 'Season 2',
            'chapters': 'count:3',
            'episode': 'Episode 5',
            'season_number': 2,
            'series': 'CatDog',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.paramountplus.com/shows/video/6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd/',
        'info_dict': {
            'id': '6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd',
            'ext': 'mp4',
            'title': '7/23/21 WEEK IN REVIEW (Rep. Jahana Hayes/Howard Fineman/Sen. Michael Bennet/Sheera Frenkel & Cecilia Kang)',
            'description': 'md5:f4adcea3e8b106192022e121f1565bae',
            'duration': 2506,
            'timestamp': 1627063200,
            'upload_date': '20210723',
            'uploader': 'CBSI-NEW',
            'episode_number': 81,
            'thumbnail': r're:https?://.+\.jpg$',
            'season': 'Season 2',
            'chapters': 'count:4',
            'episode': 'Episode 81',
            'season_number': 2,
            'series': 'Tooning Out The News',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.paramountplus.com/movies/video/vM2vm0kE6vsS2U41VhMRKTOVHyQAr6pC/',
        'info_dict': {
            'id': 'vM2vm0kE6vsS2U41VhMRKTOVHyQAr6pC',
            'ext': 'mp4',
            'title': 'Daddy\'s Home',
            'upload_date': '20151225',
            'description': 'md5:9a6300c504d5e12000e8707f20c54745',
            'uploader': 'CBSI-NEW',
            'timestamp': 1451030400,
            'thumbnail': r're:https?://.+\.jpg$',
            'chapters': 'count:0',
            'duration': 5761,
            'series': 'Paramount+ Movies',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'DRM',
    }, {
        'url': 'https://www.paramountplus.com/movies/video/5EKDXPOzdVf9voUqW6oRuocyAEeJGbEc/',
        'info_dict': {
            'id': '5EKDXPOzdVf9voUqW6oRuocyAEeJGbEc',
            'ext': 'mp4',
            'uploader': 'CBSI-NEW',
            'description': 'md5:bc7b6fea84ba631ef77a9bda9f2ff911',
            'timestamp': 1577865600,
            'title': 'Sonic the Hedgehog',
            'upload_date': '20200101',
            'thumbnail': r're:https?://.+\.jpg$',
            'chapters': 'count:0',
            'duration': 5932,
            'series': 'Paramount+ Movies',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'DRM',
    }, {
        'url': 'https://www.paramountplus.com/shows/the-real-world/video/mOVeHeL9ub9yWdyzSZFYz8Uj4ZBkVzQg/the-real-world-reunion/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/shows/video/mOVeHeL9ub9yWdyzSZFYz8Uj4ZBkVzQg/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/movies/video/W0VyStQqUnqKzJkrpSAIARuCc9YuYGNy/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/movies/paw-patrol-the-movie/W0VyStQqUnqKzJkrpSAIARuCc9YuYGNy/',
        'only_matching': True,
    }]

    def _extract_video_info(self, content_id, mpx_acc=2198311517):
        items_data = self._download_json(
            f'https://www.paramountplus.com/apps-api/v2.0/androidtv/video/cid/{content_id}.json',
            content_id, query={
                'locale': 'en-us',
                'at': 'ABCXgPuoStiPipsK0OHVXIVh68zNys+G4f7nW9R6qH68GDOcneW6Kg89cJXGfiQCsj0=',
            }, headers=self.geo_verification_headers())

        asset_types = {
            item.get('assetType'): {
                'format': 'SMIL',
                'formats': 'M3U+none,MPEG4',  # '+none' specifies ProtectionScheme (no DRM)
            } for item in items_data['itemList']
        }
        item = items_data['itemList'][-1]

        info, error = {}, None
        metadata = {
            'title': item.get('title'),
            'series': item.get('seriesTitle'),
            'season_number': int_or_none(item.get('seasonNum')),
            'episode_number': int_or_none(item.get('episodeNum')),
            'duration': int_or_none(item.get('duration')),
            'thumbnail': url_or_none(item.get('thumbnail')),
        }
        try:
            info = self._extract_common_video_info(content_id, asset_types, mpx_acc, extra_info=metadata)
        except ExtractorError as e:
            error = e

        # Check for DRM formats to give appropriate error
        if not info.get('formats'):
            for query in asset_types.values():
                query['formats'] = 'MPEG-DASH,M3U,MPEG4'  # allows DRM formats

            try:
                drm_info = self._extract_common_video_info(content_id, asset_types, mpx_acc, extra_info=metadata)
            except ExtractorError:
                if error:
                    raise error from None
                raise
            if drm_info['formats']:
                self.report_drm(content_id)
            elif error:
                raise error

        return info


class ParamountPlusSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?paramountplus\.com/shows/(?P<id>[a-zA-Z0-9-_]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://www.paramountplus.com/shows/drake-josh',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'drake-josh',
        }
    }, {
        'url': 'https://www.paramountplus.com/shows/hawaii_five_0/',
        'playlist_mincount': 240,
        'info_dict': {
            'id': 'hawaii_five_0',
        }
    }, {
        'url': 'https://www.paramountplus.com/shows/spongebob-squarepants/',
        'playlist_mincount': 248,
        'info_dict': {
            'id': 'spongebob-squarepants',
        }
    }]

    def _entries(self, show_name):
        for page in itertools.count():
            show_json = self._download_json(
                f'https://www.paramountplus.com/shows/{show_name}/xhr/episodes/page/{page}/size/50/xs/0/season/0', show_name)
            if not show_json.get('success'):
                return
            for episode in show_json['result']['data']:
                yield self.url_result(
                    'https://www.paramountplus.com%s' % episode['url'],
                    ie=ParamountPlusIE.ie_key(), video_id=episode['content_id'])

    def _real_extract(self, url):
        show_name = self._match_id(url)
        return self.playlist_result(self._entries(show_name), playlist_id=show_name)

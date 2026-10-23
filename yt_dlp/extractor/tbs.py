import re
import urllib.parse

from .turner import TurnerBaseIE
from ..utils import (
    float_or_none,
    int_or_none,
    make_archive_id,
    strip_or_none,
)
from ..utils.traversal import traverse_obj


class TBSIE(TurnerBaseIE):
    _SITE_INFO = {
        'tbs': ('TBS', 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJkZTA0NTYxZS1iMTFhLTRlYTgtYTg5NC01NjI3MGM1NmM2MWIiLCJuYmYiOjE1MzcxODkzOTAsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTM3MTg5MzkwfQ.Z7ny66kaqNDdCHf9Y9KsV12LrBxrLkGGxlYe2XGm6qsw2T-k1OCKC1TMzeqiZP735292MMRAQkcJDKrMIzNbAuf9nCdIcv4kE1E2nqUnjPMBduC1bHffZp8zlllyrN2ElDwM8Vhwv_5nElLRwWGEt0Kaq6KJAMZA__WDxKWC18T-wVtsOZWXQpDqO7nByhfj2t-Z8c3TUNVsA_wHgNXlkzJCZ16F2b7yGLT5ZhLPupOScd3MXC5iPh19HSVIok22h8_F_noTmGzmMnIRQi6bWYWK2zC7TQ_MsYHfv7V6EaG5m1RKZTV6JAwwoJQF_9ByzarLV1DGwZxD9-eQdqswvg'),
        'tntdrama': ('TNT', 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIwOTMxYTU4OS1jZjEzLTRmNjMtYTJmYy03MzhjMjE1NWU5NjEiLCJuYmYiOjE1MzcxOTA4MjcsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTM3MTkwODI3fQ.AucKvtws7oekTXi80_zX4-BlgJD9GLvlOI9FlBCjdlx7Pa3eJ0AqbogynKMiatMbnLOTMHGjd7tTiq422unmZjBz70dhePAe9BbW0dIo7oQ57vZ-VBYw_tWYRPmON61MwAbLVlqROD3n_zURs85S8TlkQx9aNx9x_riGGELjd8l05CVa_pOluNhYvuIFn6wmrASOKI1hNEblBDWh468UWP571-fe4zzi0rlYeeHd-cjvtWvOB3bQsWrUVbK4pRmqvzEH59j0vNF-ihJF9HncmUicYONe47Mib3elfMok23v4dB1_UAlQY_oawfNcynmEnJQCcqFmbHdEwTW6gMiYsA'),
        'trutv': ('truTV', 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhYzQyOTkwMi0xMDYzLTQyNTQtYWJlYS1iZTY2ODM4MTVmZGIiLCJuYmYiOjE1MzcxOTA4NjgsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTM3MTkwODY4fQ.ewXl5LDMDvvx3nDXV4jCdSwUq_sOluKoOVsIjznAo6Zo4zrGe9rjlZ9DOmQKW66g6VRMexJsJ5vM1EkY8TC5-YcQw_BclK1FPGO1rH3Wf7tX_l0b1BVbSJQKIj9UgqDp_QbGcBXz24kN4So3U22mhs6di9PYyyfG68ccKL2iRprcVKWCslIHwUF-T7FaEqb0K57auilxeW1PONG2m-lIAcZ62DUwqXDWvw0CRoWI08aVVqkkhnXaSsQfLs5Ph1Pfh9Oq3g_epUm9Ss45mq6XM7gbOb5omTcKLADRKK-PJVB_JXnZnlsXbG0ttKE1cTKJ738qu7j4aipYTf-W0nKF5Q'),
    }
    _VALID_URL = fr'''(?x)
        https?://(?:www\.)?(?P<site>{"|".join(map(re.escape, _SITE_INFO))})\.com
        (?P<path>/(?:
            (?P<watch>watch(?:tnt|tbs|trutv))|
            movies|shows/[^/?#]+/(?:clips|season-\d+/episode-\d+)
        )/(?P<id>[^/?#]+))
    '''
    _TESTS = [{
        'url': 'https://www.tbs.com/shows/american-dad/season-6/episode-12/you-debt-your-life',
        'info_dict': {
            'id': '984bdcd8db0cc00dc699927f2a411c8c6e0e48f3',
            'ext': 'mp4',
            'title': 'You Debt Your Life',
            'description': 'md5:f211cfeb9187fd3cdb53eb0e8930d499',
            'duration': 1231.0,
            'thumbnail': r're:https://images\.tbs\.com/tbs/.+\.(?:jpe?g|png)',
            'chapters': 'count:4',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Episode 12',
            'episode_number': 12,
            'timestamp': 1478276239,
            'upload_date': '20161104',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.tntdrama.com/shows/the-librarians-the-next-chapter/season-1/episode-10/and-going-medieval',
        'info_dict': {
            'id': 'e487b31b663a8001864f62fd20907782f7b8ccb8',
            'ext': 'mp4',
            'title': 'And Going Medieval',
            'description': 'md5:5aed0ae23a6cf148a02fe3c1be8359fa',
            'duration': 2528.0,
            'thumbnail': r're:https://images\.tntdrama\.com/tnt/.+\.(?:jpe?g|png)',
            'chapters': 'count:7',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 10',
            'episode_number': 10,
            'timestamp': 1743107520,
            'upload_date': '20250327',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.trutv.com/shows/the-carbonaro-effect/season-1/episode-1/got-the-bug-out',
        'info_dict': {
            'id': 'b457dd7458fd9e64b596355950b13a1ca799dc39',
            'ext': 'mp4',
            'title': 'Got the Bug Out',
            'description': 'md5:9eeddf6248f73517b0e5969b8a43c025',
            'duration': 1283.0,
            'thumbnail': r're:https://images\.trutv\.com/tru/.+\.(?:jpe?g|png)',
            'chapters': 'count:4',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1570040829,
            'upload_date': '20191002',
            '_old_archive_ids': ['trutv b457dd7458fd9e64b596355950b13a1ca799dc39'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://www.tntdrama.com/shows/the-alienist/clips/monster',
        'only_matching': True,
    }, {
        'url': 'http://www.tbs.com/shows/search-party/season-1/episode-1/explicit-the-mysterious-disappearance-of-the-girl-no-one-knew',
        'only_matching': True,
    }, {
        'url': 'http://www.tntdrama.com/movies/star-wars-a-new-hope',
        'only_matching': True,
    }, {
        'url': 'https://www.trutv.com/shows/impractical-jokers/season-9/episode-1/you-dirty-dog',
        'only_matching': True,
    }, {
        'url': 'https://www.trutv.com/watchtrutv/east',
        'only_matching': True,
    }, {
        'url': 'https://www.tbs.com/watchtbs/east',
        'only_matching': True,
    }, {
        'url': 'https://www.tntdrama.com/watchtnt/east',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        site, path, display_id, watch = self._match_valid_url(url).group('site', 'path', 'id', 'watch')
        is_live = bool(watch)
        webpage = self._download_webpage(url, display_id)
        drupal_settings = self._search_json(
            r'<script\b[^>]+\bdata-drupal-selector="drupal-settings-json"[^>]*>',
            webpage, 'drupal settings', display_id)
        video_data = next(v for v in drupal_settings['turner_playlist'] if is_live or v.get('url') == path)

        media_id = video_data['mediaID']
        title = video_data['title']
        tokenizer_query = urllib.parse.parse_qs(urllib.parse.urlparse(
            drupal_settings['ngtv_token_url']).query)

        auth_info = traverse_obj(drupal_settings, ('top2', {dict})) or {}
        site_name = auth_info.get('siteName') or self._SITE_INFO[site][0]
        software_statement = auth_info.get('softwareStatement') or self._SITE_INFO[site][1]

        info = self._extract_ngtv_info(
            media_id, tokenizer_query, software_statement, {
                'url': url,
                'site_name': site_name,
                'auth_required': video_data.get('authRequired') == '1' or is_live,
                'is_live': is_live,
            })

        thumbnails = []
        for image_id, image in video_data.get('images', {}).items():
            image_url = image.get('url')
            if not image_url or image.get('type') != 'video':
                continue
            i = {
                'id': image_id,
                'url': image_url,
            }
            mobj = re.search(r'(\d+)x(\d+)', image_url)
            if mobj:
                i.update({
                    'width': int(mobj.group(1)),
                    'height': int(mobj.group(2)),
                })
            thumbnails.append(i)

        info.update({
            'id': media_id,
            'title': title,
            'description': strip_or_none(video_data.get('descriptionNoTags') or video_data.get('shortDescriptionNoTags')),
            'duration': float_or_none(video_data.get('duration')) or info.get('duration'),
            'timestamp': int_or_none(video_data.get('created')),
            'season_number': int_or_none(video_data.get('season')),
            'episode_number': int_or_none(video_data.get('episode')),
            'thumbnails': thumbnails,
            'is_live': is_live,
        })
        if site == 'trutv':
            info['_old_archive_ids'] = [make_archive_id(site, media_id)]
        return info

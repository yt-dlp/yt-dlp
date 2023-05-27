import urllib.error

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    filter_dict,
    float_or_none,
    int_or_none,
    jwt_decode_hs256,
    make_archive_id,
    parse_age_limit,
    traverse_obj,
    try_call,
    try_get,
    unified_strdate,
)


class VootIE(InfoExtractor):
    _NETRC_MACHINE = 'voot'
    _VALID_URL = r'''(?x)
                    (?:
                        voot:|
                        https?://(?:www\.)?voot\.com/?
                        (?:
                            movies?/[^/]+/|
                            (?:shows|kids)/(?:[^/]+/){4}
                        )
                     )
                    (?P<id>\d{3,})
                    '''
    _GEO_COUNTRIES = ['IN']
    _TESTS = [{
        'url': 'https://www.voot.com/shows/ishq-ka-rang-safed/1/360558/is-this-the-end-of-kamini-/441353',
        'info_dict': {
            'id': '0_8ledb18o',
            'ext': 'mp4',
            'title': 'Ishq Ka Rang Safed - Season 01 - Episode 340',
            'description': 'md5:06291fbbbc4dcbe21235c40c262507c1',
            'timestamp': 1472162937,
            'upload_date': '20160825',
            'series': 'Ishq Ka Rang Safed',
            'season_number': 1,
            'episode': 'Is this the end of Kamini?',
            'episode_number': 340,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://www.voot.com/kids/characters/mighty-cat-masked-niyander-e-/400478/school-bag-disappears/440925',
        'only_matching': True,
    }, {
        'url': 'https://www.voot.com/movies/pandavas-5/424627',
        'only_matching': True,
    }, {
        'url': 'https://www.voot.com/movie/fight-club/621842',
        'only_matching': True,
    }, {
        'url': 'https://www.voot.com/shows/parineetii/1/1273482/bebe-gets-a-nefarious-idea/1475903',
        'only_matching': True,
    }]

    _TOKEN = None

    def _perform_login(self, username, password):
        if username.lower() == 'token' and try_call(lambda: jwt_decode_hs256(password)):
            self._TOKEN = password
            self.report_login()
        else:
            raise ExtractorError(
                'Use "--username token" and "--password <access_token>" to login using access token.')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media_info = self._download_json(
            'https://psapi.voot.com/jio/voot/v1/voot-web/content/query/asset-details', video_id,
            query={
                'ids': f'include:{video_id}',
                'responseType': 'common',
            }, headers=filter_dict({'accesstoken': self._TOKEN}))

        headers = {'Origin': 'https://www.voot.com', 'Referer': 'https://www.voot.com/'}
        try:
            m3u8_url = self._download_json(
                'https://vootapi.media.jio.com/playback/v1/playbackrights', video_id,
                data=b'{}', headers=filter_dict({
                    **headers,
                    'Content-Type': 'application/json;charset=utf-8',
                    'platform': 'androidwebdesktop',
                    'vootid': video_id,
                    'voottoken': self._TOKEN,
                }))['m3u8']
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 400:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls'),
            'http_headers': headers,
            **traverse_obj(media_info, ('result', 0, {
                'title': ('fullTitle', {str}),
                'description': ('fullSynopsis', {str}),
                'series': ('showName', {str}),
                'season_number': ('season', {int_or_none}),
                'episode': ('fullTitle', {str}),
                'episode_number': ('episode', {int_or_none}),
                'timestamp': ('uploadTime', {int_or_none}),
                'release_date': ('telecastDate', {unified_strdate}),
                'age_limit': ('ageNemonic', {parse_age_limit}),
                'duration': ('duration', {float_or_none}),
                '_old_archive_ids': ('entryId', {lambda x: [make_archive_id('Kaltura', x)] if x else None}),
            })),
        }


class VootSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?voot\.com/shows/[^/]+/(?P<id>\d{3,})'
    _TESTS = [{
        'url': 'https://www.voot.com/shows/chakravartin-ashoka-samrat/100002',
        'playlist_mincount': 442,
        'info_dict': {
            'id': '100002',
        },
    }, {
        'url': 'https://www.voot.com/shows/ishq-ka-rang-safed/100003',
        'playlist_mincount': 341,
        'info_dict': {
            'id': '100003',
        },
    }]
    _SHOW_API = 'https://psapi.voot.com/media/voot/v1/voot-web/content/generic/season-by-show?sort=season%3Aasc&id={}&responseType=common'
    _SEASON_API = 'https://psapi.voot.com/media/voot/v1/voot-web/content/generic/series-wise-episode?sort=episode%3Aasc&id={}&responseType=common&page={:d}'

    def _entries(self, show_id):
        show_json = self._download_json(self._SHOW_API.format(show_id), video_id=show_id)
        for season in show_json.get('result', []):
            page_num = 1
            season_id = try_get(season, lambda x: x['id'], compat_str)
            season_json = self._download_json(self._SEASON_API.format(season_id, page_num),
                                              video_id=season_id,
                                              note='Downloading JSON metadata page %d' % page_num)
            episodes_json = season_json.get('result', [])
            while episodes_json:
                page_num += 1
                for episode in episodes_json:
                    video_id = episode.get('id')
                    yield self.url_result(
                        'voot:%s' % video_id, ie=VootIE.ie_key(), video_id=video_id)
                episodes_json = self._download_json(self._SEASON_API.format(season_id, page_num),
                                                    video_id=season_id,
                                                    note='Downloading JSON metadata page %d' % page_num)['result']

    def _real_extract(self, url):
        show_id = self._match_id(url)
        return self.playlist_result(self._entries(show_id), playlist_id=show_id)

import base64
import urllib.parse

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, traverse_obj


class AmazonMiniTVBaseIE(InfoExtractor):
    _PANAMA_API_BASE = 'https://www.amazon.in/minitv-op/api/web'
    _EPISODE_LIST_WIDGET_UUID = '8e0cefec-e190-46ba-854d-1f3ca7978b4a'

    def _seed_session_cookie(self):
        if not self._get_cookies('https://www.amazon.in').get('session-id'):
            self._download_webpage(
                'https://www.amazon.in/minitv', None,
                note='Fetching guest session cookies', fatal=False)

    def _call_panama_api(self, path, video_id, query=None, note='Downloading API JSON'):
        self._seed_session_cookie()
        return self._download_json(
            f'{self._PANAMA_API_BASE}{path}', video_id,
            note=note, query=query, headers={
                'Accept': 'application/json',
                'accounttype': 'NEW_GUEST_ACCOUNT',
                'currentpageurl': '/',
                'currentplatform': 'dWeb',
            })

    def _episode_list_widget_id(self, asin):
        b64 = base64.b64encode(asin.encode()).decode()
        return f'{self._EPISODE_LIST_WIDGET_UUID}:::{b64}:::[null]'

    def _entries_from_episode_list(self, episodes, ie):
        for ep in episodes or []:
            cid = traverse_obj(ep, ('data', 'contentId'))
            if cid:
                yield self.url_result(
                    f'amazonminitv:{cid}', ie, cid,
                    video_title=traverse_obj(ep, ('data', 'name')))


class AmazonMiniTVIE(AmazonMiniTVBaseIE):
    _VALID_URL = r'(?:https?://(?:www\.)?amazon\.in/minitv/tp/|amazonminitv:(?:amzn1\.dv\.gti\.)?)(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://www.amazon.in/minitv/tp/6a2e574e-2148-4415-9757-089537af6d1d',
        'info_dict': {
            'id': 'amzn1.dv.gti.6a2e574e-2148-4415-9757-089537af6d1d',
            'ext': 'mp4',
            'title': 'The Dead Never Lie',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'description': 'md5:1342528119e9e4d1a0986df8a70c7276',
            'release_timestamp': 1649376000,
            'release_date': '20220408',
            'duration': 1533,
            'chapters': 'count:2',
            'series': 'Murder in Agonda',
            'series_id': 'amzn1.dv.gti.b070ee6a-986c-4cbd-aabf-83940f34545c',
            'season': 'Murder In Agonda - Season 1',
            'season_number': 1,
            'season_id': 'amzn1.dv.gti.74271cb6-e19e-445b-a648-e15a3912b8ef',
            'episode': 'The Dead Never Lie',
            'episode_number': 1,
            'episode_id': 'amzn1.dv.gti.6a2e574e-2148-4415-9757-089537af6d1d',
            'cast': ['Shriya Pilgaonkar', 'Kubbra Sait', 'Aasif Khan', 'Lilette Dubey'],
            'genres': ['Suspense', 'Mystery'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.amazon.in/minitv/tp/75fe3a75-b8fe-4499-8100-5c9424344840?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'info_dict': {
            'id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
            'ext': 'mp4',
            'title': 'May I Kiss You?',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'description': 'md5:a549bfc747973e04feb707833474e59d',
            'release_timestamp': 1644710400,
            'release_date': '20220213',
            'duration': 846,
            'chapters': 'count:3',
            'series': 'Couple Goals',
            'series_id': 'amzn1.dv.gti.56521d46-b040-4fd5-872e-3e70476a04b0',
            'season': 'Couple Goals - Season 3',
            'season_number': 3,
            'season_id': 'amzn1.dv.gti.20331016-d9b9-4968-b991-c89fa4927a36',
            'episode': 'May I Kiss You?',
            'episode_number': 2,
            'episode_id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
            'cast': ['Akash Gupta', 'Mughda Agarwal'],
            'genres': ['Comedy', 'Romance'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.amazon.in/minitv/tp/280d2564-584f-452f-9c98-7baf906e01ab?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'info_dict': {
            'id': 'amzn1.dv.gti.280d2564-584f-452f-9c98-7baf906e01ab',
            'ext': 'mp4',
            'title': 'Jahaan',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'description': 'md5:05eb765a77bf703f322f120ec6867339',
            'release_timestamp': 1647475200,
            'release_date': '20220317',
            'duration': 783,
            'chapters': [],
            'cast': ['Mrunal Thakur', 'Avinash Tiwary'],
            'genres': [],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.amazon.in/minitv/tp/280d2564-584f-452f-9c98-7baf906e01ab',
        'only_matching': True,
    }, {
        'url': 'amazonminitv:amzn1.dv.gti.280d2564-584f-452f-9c98-7baf906e01ab',
        'only_matching': True,
    }, {
        'url': 'amazonminitv:280d2564-584f-452f-9c98-7baf906e01ab',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://www.amazon.in/minitv/tp/{video_id}', video_id)
        page_data = traverse_obj(
            self._search_nextjs_data(webpage, video_id),
            ('props', 'pageProps', 'ssrProps', 'pageLayoutData')) or {}

        widgets = {w.get('type'): w.get('data') or {} for w in page_data.get('widgets') or []}
        player_data = widgets.get('PLAYER') or {}
        playback_assets = player_data.get('playbackAssets') or {}
        player_content = player_data.get('contentDetails') or {}
        meta = traverse_obj(page_data, ('metaData', 'contentDetails')) or {}

        if not playback_assets.get('manifestURL') and not meta:
            raise ExtractorError(
                'Unable to find video data in page; the title may be unavailable in this region',
                expected=True)

        formats, subtitles = [], {}
        seen_manifests = set()

        def _add_dash(manifest_url, codec=None):
            if not manifest_url or manifest_url in seen_manifests:
                return
            seen_manifests.add(manifest_url)
            mpd_id = 'dash' if not codec else f'dash-{codec.lower()}'
            mpd_fmts, mpd_subs = self._extract_mpd_formats_and_subtitles(
                manifest_url, video_id, mpd_id=mpd_id, fatal=False)
            formats.extend(mpd_fmts)
            self._merge_subtitles(mpd_subs, target=subtitles)

        _add_dash(playback_assets.get('manifestURL'))
        for asset in playback_assets.get('manifestData') or []:
            _add_dash(asset.get('manifestURL'), asset.get('codec'))

        chapters = sorted(({
            'start_time': int_or_none(elem.get('start')),
            'end_time': int_or_none(elem.get('end')),
            'title': (elem.get('elementType') or '').replace('_', ' ').title() or None,
        } for elem in player_content.get('transitionElements') or []),
            key=lambda c: c['start_time'] if c['start_time'] is not None else -1)

        is_episode = meta.get('vodType') == 'EPISODE'
        content_id = meta.get('contentId') or f'amzn1.dv.gti.{video_id}'

        return {
            'id': content_id,
            'title': meta.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'language': traverse_obj(player_content, ('audioTracks', 0)),
            'thumbnail': meta.get('imageSrc'),
            'description': meta.get('synopsis'),
            'release_timestamp': int_or_none(meta.get('publicReleaseDateUTC'), scale=1000),
            'duration': int_or_none(meta.get('contentLengthInSeconds')),
            'chapters': chapters,
            'series': meta.get('seriesName'),
            'series_id': player_content.get('seriesId'),
            'season': meta.get('seasonName'),
            'season_number': int_or_none(meta.get('seasonNumber')),
            'season_id': player_content.get('seasonId'),
            'episode': meta.get('name') if is_episode else None,
            'episode_number': int_or_none(meta.get('episodeNumber')),
            'episode_id': content_id if is_episode else None,
            'cast': meta.get('starringCast'),
            'genres': meta.get('genres'),
        }


class AmazonMiniTVSeasonIE(AmazonMiniTVBaseIE):
    IE_NAME = 'amazonminitv:season'
    _VALID_URL = r'amazonminitv:season:(?:amzn1\.dv\.gti\.)?(?P<id>[a-f0-9-]+)'
    IE_DESC = 'Amazon MiniTV Season, "minitv:season:" prefix; ID can be a season ASIN or any season episode contentId'
    _TESTS = [{
        'url': 'amazonminitv:season:amzn1.dv.gti.6a2e574e-2148-4415-9757-089537af6d1d',
        'playlist_mincount': 6,
        'info_dict': {
            'id': 'amzn1.dv.gti.6a2e574e-2148-4415-9757-089537af6d1d',
        },
    }, {
        'url': 'amazonminitv:season:6a2e574e-2148-4415-9757-089537af6d1d',
        'only_matching': True,
    }]

    def _entries(self, asin):
        widget_id = self._episode_list_widget_id(asin)
        path = f'/widget/{urllib.parse.quote(widget_id, safe="")}'
        data = self._call_panama_api(
            path, asin, query={'cursorType': 'refresh'},
            note='Downloading season episode list')
        if traverse_obj(data, ('data', 'listType')) != 'SEASON_LIST':
            raise ExtractorError(
                'API did not return a season; pass an episode contentId or a season ASIN', expected=True)
        episodes = traverse_obj(data, ('data', 'widgets', 0, 'data', 'widgets'))
        yield from self._entries_from_episode_list(episodes, AmazonMiniTVIE)

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        return self.playlist_result(self._entries(asin), asin)


class AmazonMiniTVSeriesIE(AmazonMiniTVBaseIE):
    IE_NAME = 'amazonminitv:series'
    _VALID_URL = r'amazonminitv:series:(?:amzn1\.dv\.gti\.)?(?P<id>[a-f0-9-]+)'
    IE_DESC = (
        'Amazon MiniTV Series, "minitv:series:" prefix; '
        'ID must be an episode contentId or season ASIN of the series'
    )
    _TESTS = [{
        # Crimes Aaj Kal (3 seasons)
        'url': 'amazonminitv:series:amzn1.dv.gti.c85c18fa-567b-480a-b919-73f7fbc6515a',
        'playlist_mincount': 20,
        'info_dict': {
            'id': 'amzn1.dv.gti.c85c18fa-567b-480a-b919-73f7fbc6515a',
        },
    }, {
        'url': 'amazonminitv:series:c85c18fa-567b-480a-b919-73f7fbc6515a',
        'only_matching': True,
    }]

    def _episodes_for_season(self, season_data, asin, season_title):
        # When the season is the active tab, episodes are inlined; otherwise fetch via widget API.
        episodes = traverse_obj(season_data, ('widgets', 0, 'data', 'widgets'))
        if episodes:
            return episodes
        widget_id = season_data.get('widgetId')
        if not widget_id:
            return []
        path = f'/widget/{urllib.parse.quote(widget_id, safe="")}'
        data = self._call_panama_api(
            path, asin, query={'cursorType': 'refresh'},
            note=f'Downloading {season_title} episode list')
        return traverse_obj(data, ('data', 'widgets', 0, 'data', 'widgets')) or []

    def _entries(self, asin):
        try:
            page = self._call_panama_api(
                '/page/title', asin,
                query={'contentId': asin, 'cursor': f'{self._EPISODE_LIST_WIDGET_UUID}:::'},
                note='Downloading series page layout')
        except ExtractorError as e:
            raise ExtractorError(
                'Could not load series page; the ID must be an episode contentId or season ASIN, '
                'not a bare series ASIN', expected=True, cause=e)

        tab = next(
            (w for w in page.get('widgets') or [] if w.get('type') == 'TAB'), None)
        if not tab:
            raise ExtractorError(
                'No season tabs found in API response',
                expected=True)
        for opt in traverse_obj(tab, ('data', 'options')) or []:
            season_data = traverse_obj(opt, ('value', 'data')) or {}
            episodes = self._episodes_for_season(season_data, asin, opt.get('title') or 'season')
            yield from self._entries_from_episode_list(episodes, AmazonMiniTVIE)

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        return self.playlist_result(self._entries(asin), asin)

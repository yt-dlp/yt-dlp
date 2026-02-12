from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, traverse_obj, try_get


class AmazonMiniTVBaseIE(InfoExtractor):
    def _real_initialize(self):
        self._download_webpage(
            'https://www.amazon.in/minitv', None,
            note='Fetching guest session cookies')
        AmazonMiniTVBaseIE.urtk = self._get_cookies('https://www.amazon.in')['urtk'].value

    def _call_api(self, asin, data=None, note=None):
        query = {
            'contentId': asin,
        }
        if data:
            query.update(data)

        resp = self._download_json(
            'https://www.amazon.in/minitv-pr/api/web/page/title',
            asin, note=note, headers={
                'Content-Type': 'application/json',
                'accounttype': 'NEW_GUEST_ACCOUNT',
                'currentpageurl': '/',
                'currentplatform': 'dWeb',
            }, data=None,
            query=query)

        if resp.get('errors'):
            raise ExtractorError(f'MiniTV said: {resp["errors"][0]["message"]}')
        return resp


class AmazonMiniTVIE(AmazonMiniTVBaseIE):
    _VALID_URL = r'(?:https?://(?:www\.)?amazon\.in/minitv/tp/|amazonminitv:(?:amzn1\.dv\.gti\.)?)(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://www.amazon.in/minitv/tp/75fe3a75-b8fe-4499-8100-5c9424344840?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'info_dict': {
            'id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
            'ext': 'mp4',
            'title': 'May I Kiss You?',
            'language': 'Hindi',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'description': 'md5:a549bfc747973e04feb707833474e59d',
            'release_timestamp': 1644710400,
            'release_date': '20220213',
            'duration': 846,
            'chapters': 'count:2',
            'series': 'Couple Goals',
            'series_id': 'amzn1.dv.gti.56521d46-b040-4fd5-872e-3e70476a04b0',
            'season': 'Season 3',
            'season_number': 3,
            'season_id': 'amzn1.dv.gti.20331016-d9b9-4968-b991-c89fa4927a36',
            'episode': 'May I Kiss You?',
            'episode_number': 2,
            'episode_id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
        },
    }, {
        'url': 'https://www.amazon.in/minitv/tp/280d2564-584f-452f-9c98-7baf906e01ab?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'info_dict': {
            'id': 'amzn1.dv.gti.280d2564-584f-452f-9c98-7baf906e01ab',
            'ext': 'mp4',
            'title': 'Jahaan',
            'language': 'Hindi',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'description': 'md5:05eb765a77bf703f322f120ec6867339',
            'release_timestamp': 1647475200,
            'release_date': '20220317',
            'duration': 783,
            'chapters': [],
        },
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
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        prs = self._call_api(asin, note='Downloading playback info')
        playback_info = traverse_obj(prs, ('widgets', 0, 'data', 'playbackAssets', 'manifestData'))
        title_info = traverse_obj(prs, ('widgets', 0, 'data', 'contentDetails'))
        title_info_ = traverse_obj(prs, ('metaData', 'contentDetails'))

        formats, subtitles = [], {}
        for mpd in playback_info:
            mpd_fmts, mpd_subs = self._extract_mpd_formats_and_subtitles(
                mpd['manifestURL'], asin, mpd_id=mpd['codec'], fatal=False)
            formats.extend(mpd_fmts)
            subtitles = self._merge_subtitles(subtitles, mpd_subs)

        credits_time = try_get(title_info, lambda x: x['skipData']['INTRO']['endTime'])
        is_episode = title_info_.get('vodType') == 'EPISODE'

        return {
            'id': asin,
            'title': title_info_.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'language': traverse_obj(title_info, ('audioTracks', 0)),
            'thumbnails': [{
                'id': 'imageSrc',
                'url': title_info_.get('imageSrc'),
            }] if title_info_.get('imageSrc') else [],
            'description': traverse_obj(title_info_, ('synopsis')),
            'release_timestamp': int_or_none(try_get(title_info_, lambda x: x['publicReleaseDateUTC'] / 1000)),
            'duration': traverse_obj(title_info_, ('contentLengthInSeconds')),
            'chapters': [{
                'start_time': credits_time,
                'title': 'End Credits',
            }] if credits_time else [],
            'series': title_info_.get('seasonName') if is_episode else None,
            'series_id': title_info.get('seriesId') if is_episode else None,
            'season_number': title_info.get('seasonNumber') if is_episode else None,
            'season_id': title_info.get('seasonId') if is_episode else None,
            'episode': title_info.get('name') if is_episode else None,
            'episode_number': title_info.get('episodeNumber') if is_episode else None,
            'episode_id': asin if is_episode else None,
        }


class AmazonMiniTVSeasonIE(AmazonMiniTVBaseIE):
    IE_NAME = 'amazonminitv:season'
    _VALID_URL = r'amazonminitv:season:(?:amzn1\.dv\.gti\.)?(?P<id>[a-f0-9-]+)'
    IE_DESC = 'Amazon MiniTV Season, "minitv:season:" prefix'
    _TESTS = [{
        'url': 'amazonminitv:season:amzn1.dv.gti.0aa996eb-6a1b-4886-a342-387fbd2f1db0',
        'playlist_mincount': 6,
        'info_dict': {
            'id': 'amzn1.dv.gti.0aa996eb-6a1b-4886-a342-387fbd2f1db0',
        },
    }, {
        'url': 'amazonminitv:season:0aa996eb-6a1b-4886-a342-387fbd2f1db0',
        'only_matching': True,
    }]

    def _entries(self, asin):
        season_info = self._call_api(
            asin, note='Downloading season info',
            data={'cursor': '8e0cefec-e190-46ba-854d-1f3ca7978b4a:::'},
        )

        for season in season_info['widgets'][0]['data']['options']:
            if season['active']:
                for episode in season['value']['data']['widgets'][0]['data']['widgets']:
                    yield self.url_result(
                        f'amazonminitv:{episode["data"]["contentId"]}', AmazonMiniTVIE, episode['data']['contentId'])

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        return self.playlist_result(self._entries(asin), asin)

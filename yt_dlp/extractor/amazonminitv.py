import json

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, traverse_obj, try_get


class AmazonMiniTVIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:www\.)?amazon\.in/minitv/tp/|amazonminitv:(?:amzn1\.dv\.gti\.)?)(?P<id>[a-f0-9-]+)'
    _HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36',
    }
    _CLIENT_ID = 'ATVIN'
    _DEVICE_LOCALE = 'en_GB'
    _TESTS = [{
        'url': 'https://www.amazon.in/minitv/tp/75fe3a75-b8fe-4499-8100-5c9424344840?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'md5': '0045a5ea38dddd4de5a5fcec7274b476',
        'info_dict': {
            'id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
            'ext': 'mp4',
            'title': 'May I Kiss You?',
            'language': 'Hindi',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:a549bfc747973e04feb707833474e59d',
            'release_timestamp': 1644710400,
            'release_date': '20220213',
            'duration': 846,
            'chapters': [{
                'start_time': 815.0,
                'end_time': 846,
                'title': 'End Credits',
            }],
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
        'md5': '9a977bffd5d99c4dd2a32b360aee1863',
        'info_dict': {
            'id': 'amzn1.dv.gti.280d2564-584f-452f-9c98-7baf906e01ab',
            'ext': 'mp4',
            'title': 'Jahaan',
            'language': 'Hindi',
            'thumbnail': r're:^https?://.*\.jpg',
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
    _GRAPHQL_QUERY_CONTENT = '''
query content($sessionIdToken: String!, $deviceLocale: String, $contentId: ID!, $contentType: ContentType!, $clientId: String) {
  content(
    applicationContextInput: {deviceLocale: $deviceLocale, sessionIdToken: $sessionIdToken, clientId: $clientId}
    contentId: $contentId
    contentType: $contentType
  ) {
    contentId
    name
    ... on Episode {
      contentId
      vodType
      name
      images
      description {
        synopsis
        contentLengthInSeconds
      }
      publicReleaseDateUTC
      audioTracks
      seasonId
      seriesId
      seriesName
      seasonNumber
      episodeNumber
      timecode {
        endCreditsTime
      }
    }
    ... on MovieContent {
      contentId
      vodType
      name
      description {
        synopsis
        contentLengthInSeconds
      }
      images
      publicReleaseDateUTC
      audioTracks
    }
  }
}'''

    def _call_api(self, asin, data=None, note=None):
        query = {}
        headers = self._HEADERS.copy()
        if data:
            name = 'graphql'
            data['variables'].update({
                'clientId': self._CLIENT_ID,
                'contentType': 'VOD',
                'deviceLocale': self._DEVICE_LOCALE,
                'sessionIdToken': self.session_id,
            })
            headers.update({'Content-Type': 'application/json'})
        else:
            name = 'prs'
            query.update({
                'clientId': self._CLIENT_ID,
                'deviceType': 'A1WMMUXPCUJL4N',
                'contentId': asin,
                'deviceLocale': self._DEVICE_LOCALE,
            })

        resp = self._download_json(
            f'https://www.amazon.in/minitv/api/web/{name}',
            asin, query=query, data=json.dumps(data).encode() if data else None,
            headers=headers, note=note)

        if 'errors' in resp:
            raise ExtractorError(f'MiniTV said: {resp["errors"][0]["message"]}')

        if data:
            resp = resp['data'][data['operationName']]
        return resp

    def _real_initialize(self):
        # Download webpage to get the required guest session cookies
        self._download_webpage(
            'https://www.amazon.in/minitv',
            None,
            headers=self._HEADERS,
            note='Downloading webpage')

        self.session_id = self._get_cookies('https://www.amazon.in')['session-id'].value

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'

        title_info = self._call_api(
            asin, data={
                'operationName': 'content',
                'variables': {
                    'contentId': asin,
                },
                'query': self._GRAPHQL_QUERY_CONTENT,
            },
            note='Downloading title info')

        prs = self._call_api(asin, note='Downloading playback info')

        formats = []
        subtitles = {}
        for type_, asset in prs['playbackAssets'].items():
            if not isinstance(asset, dict):
                continue
            if type_ == 'hls':
                m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    asset['manifestUrl'], asin, ext='mp4', entry_protocol='m3u8_native',
                    m3u8_id=type_, fatal=False)
                formats.extend(m3u8_fmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif type_ == 'dash':
                mpd_fmts, mpd_subs = self._extract_mpd_formats_and_subtitles(
                    asset['manifestUrl'], asin, mpd_id=type_, fatal=False)
                formats.extend(mpd_fmts)
                subtitles = self._merge_subtitles(subtitles, mpd_subs)

        duration = traverse_obj(title_info, ('description', 'contentLengthInSeconds'))
        credits_time = try_get(title_info, lambda x: x['timecode']['endCreditsTime'] / 1000)
        chapters = [{
            'start_time': credits_time,
            'end_time': duration + credits_time,  # FIXME: I suppose this is correct
            'title': 'End Credits',
        }] if credits_time and duration else []
        is_episode = title_info.get('vodType') == 'EPISODE'

        return {
            'id': asin,
            'title': title_info.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'language': traverse_obj(title_info, ('audioTracks', 0)),
            'thumbnails': [{
                'id': type_,
                'url': url,
            } for type_, url in (title_info.get('images') or {}).items()],
            'description': traverse_obj(title_info, ('description', 'synopsis')),
            'release_timestamp': int_or_none(try_get(title_info, lambda x: x['publicReleaseDateUTC'] / 1000)),
            'duration': duration,
            'chapters': chapters,
            'series': title_info.get('seriesName'),
            'series_id': title_info.get('seriesId'),
            'season_number': title_info.get('seasonNumber'),
            'season_id': title_info.get('seasonId'),
            'episode': title_info.get('name') if is_episode else None,
            'episode_number': title_info.get('episodeNumber'),
            'episode_id': asin if is_episode else None,
        }


class AmazonMiniTVSeasonIE(AmazonMiniTVIE):
    IE_NAME = 'amazonminitv:season'
    _VALID_URL = r'amazonminitv:season:(?:amzn1\.dv\.gti\.)?(?P<id>[a-f0-9-]+)'
    IE_DESC = 'Amazon MiniTV Series, "minitv:season:" prefix'
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
    _GRAPHQL_QUERY = '''
query getEpisodes($sessionIdToken: String!, $clientId: String, $episodeOrSeasonId: ID!, $deviceLocale: String) {
  getEpisodes(
    applicationContextInput: {sessionIdToken: $sessionIdToken, deviceLocale: $deviceLocale, clientId: $clientId}
    episodeOrSeasonId: $episodeOrSeasonId
  ) {
    episodes {
      ... on Episode {
        contentId
        name
        images
        seriesName
        seasonId
        seriesId
        seasonNumber
        episodeNumber
        description {
          synopsis
          contentLengthInSeconds
        }
        publicReleaseDateUTC
      }
    }
  }
}
'''

    def _entries(self, asin):
        season_info = self._call_api(
            asin,
            data={
                'operationName': 'getEpisodes',
                'variables': {
                    'episodeOrSeasonId': asin,
                },
                'query': self._GRAPHQL_QUERY,
            },
            note='Downloading season info')

        for episode in season_info['episodes']:
            yield self.url_result(f'amazonminitv:{episode["contentId"]}', AmazonMiniTVIE, episode['contentId'])

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        return self.playlist_result(self._entries(asin), playlist_id=asin)


class AmazonMiniTVSeriesIE(AmazonMiniTVIE):
    IE_NAME = 'amazonminitv:series'
    _VALID_URL = r'amazonminitv:series:(?:amzn1\.dv\.gti\.)?(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'amazonminitv:series:amzn1.dv.gti.56521d46-b040-4fd5-872e-3e70476a04b0',
        'playlist_mincount': 3,
        'info_dict': {
            'id': 'amzn1.dv.gti.56521d46-b040-4fd5-872e-3e70476a04b0',
        },
    }, {
        'url': 'amazonminitv:series:56521d46-b040-4fd5-872e-3e70476a04b0',
        'only_matching': True,
    }]
    _GRAPHQL_QUERY = '''
query getSeasons($sessionIdToken: String!, $deviceLocale: String, $episodeOrSeasonOrSeriesId: ID!, $clientId: String) {
  getSeasons(
    applicationContextInput: {deviceLocale: $deviceLocale, sessionIdToken: $sessionIdToken, clientId: $clientId}
    episodeOrSeasonOrSeriesId: $episodeOrSeasonOrSeriesId
  ) {
    seasons {
      seasonId
    }
  }
}
'''

    def _entries(self, asin):
        season_info = self._call_api(
            asin,
            data={
                'operationName': 'getSeasons',
                'variables': {
                    'episodeOrSeasonOrSeriesId': asin,
                },
                'query': self._GRAPHQL_QUERY,
            },
            note='Downloading series info')

        for season in season_info['seasons']:
            yield self.url_result(f'amazonminitv:season:{season["seasonId"]}', AmazonMiniTVSeasonIE, season['seasonId'])

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        return self.playlist_result(self._entries(asin), playlist_id=asin)

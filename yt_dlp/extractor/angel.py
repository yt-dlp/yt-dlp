import json

from .common import InfoExtractor
from ..utils import unified_strdate
from ..utils.traversal import traverse_obj


class AngelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?angel\.com/watch/(?P<series>[^/?#]+)/episode/(?P<id>[\w-]+)(?:/season-(?P<season_number>\d+)/episode-(?P<episode_number>\d+)/(?P<title>[^/?#]+))?'
    _TESTS = [{
        'url': 'https://www.angel.com/watch/case-for-christ/episode/d427dcd9-2420-421c-9734-66672e67aa38',
        'md5': 'e84b896b0bb31282c9abb6c71a109ddc',
        'info_dict': {
            'id': 'd427dcd9-2420-421c-9734-66672e67aa38',
            'ext': 'mp4',
            'title': 'The Case for Christ',
            'description': 'md5:b1260a69567abdc396e5937073de2e48',
            'thumbnail': 'https://images.angelstudios.com/image/upload/v1743632142/studio-app/catalog/8b48b47a-32e0-40dc-8d0b-c0ed9cd158ab',
            'duration': 6815,
            'release_date': '20250415',
        },
    }, {
        'url': 'https://www.angel.com/watch/young-david/episode/de35a3e3-8046-4476-bf29-4b7b414f7cd6/season-1/episode-2/king',
        'md5': 'd56a2acce5b752093a059ee140f547a2',
        'info_dict': {
            'id': 'de35a3e3-8046-4476-bf29-4b7b414f7cd6',
            'ext': 'mp4',
            'title': 'King',
            'description': 'md5:cefc5a6398385e2166bbb618036da99f',
            'thumbnail': 'https://images.angelstudios.com/image/upload/v1701372336/studio-app/catalog/0a573fa6-8d9b-4ce0-b0a9-7bc6c8f97212',
            'duration': 372,
            'release_date': '20231130',
        },
    }]

    def _real_extract(self, url):
        slug, video_id = self._match_valid_url(url).group('series', 'id')

        auth_cookie = None
        if (self._cookies_passed):
            auth_cookie = self._get_cookies(url)['angel_jwt_v2'].value

        # DOWNLOADING METADATA
        metadata = traverse_obj(self._download_json(
            'https://api.angelstudios.com/graphql', video_id, data=json.dumps({
                'operationName': 'getEpisodeAndUserWatchData',
                'query': '''
                        fragment EpisodeGuildEarlyAccess on Episode {
                          isAngelGuildOnly, prereleaseAvailableFor, isTrailer, guildAvailableDate, publiclyAvailableDate, earlyAccessDate, unavailableReason, __typename
                        }

                        query getEpisodeAndUserWatchData($guid: ID!) {
                          episode(guid: $guid) {
                            description, episodeNumber, guid, id, name, posterCloudinaryPath, posterLandscapeCloudinaryPath, projectSlug, releaseDate, seasonId, seasonNumber, slug, subtitle,
                            source { credits, duration, skipsUrl: url(input: {segmentFormat: TS, muteAllSwears: true}), url(input: {segmentFormat: TS, maxH264Level: LEVEL_5_2}), __typename },
                            unavailableReason,
                            upNext { id, projectSlug, guid, seasonNumber, episodeNumber, subtitle, __typename },
                            vmapUrl,
                            watchPosition { position, __typename },
                            ...EpisodeGuildEarlyAccess, __typename
                          }
                        }''',
                'variables': {'authenticated': True,
                              'guid': video_id,
                              'includePrerelease': True,
                              'projectSlug': slug,
                              'reactionsRollupInterval': 4000,
                              'skipsEnabled': False},
            }).encode(), headers={
                'content-type': 'application/json',
                'authorization': auth_cookie,
            }), ('data', 'episode'))

        if (all(var is None for var in [metadata['guildAvailableDate'], metadata['publiclyAvailableDate'], metadata['earlyAccessDate']])):
            self.raise_geo_restricted('This video is unavailable!')
        elif (metadata['publiclyAvailableDate'] is None) and (traverse_obj(metadata, ('source', 'url')) is None):
            self.raise_login_required('This is Members Only video (' + metadata['unavailableReason'] + '). Please log in with your Guild account!')

        # DOWNLOADING LIST OF M3U8 FILES
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(traverse_obj(metadata, ('source', 'url')), video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': 'https://images.angelstudios.com/image/upload/' + metadata['posterLandscapeCloudinaryPath'],
            'duration': metadata['source']['duration'],
            **traverse_obj(metadata, {
                'title': 'subtitle',
                'description': 'description',
                'release_date': ('releaseDate', {unified_strdate}),
            }),
        }

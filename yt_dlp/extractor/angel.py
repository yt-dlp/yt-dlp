import json

from .common import InfoExtractor
from ..utils import ExtractorError, GeoRestrictedError, unified_strdate
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
        video_id = self._match_id(url)

        auth_cookie = ''
        if (self._cookies_passed):
            auth_cookie = self._get_cookies(url)['angel_jwt'].value

        # DOWNLOADING METADATA
        metadata = traverse_obj(self._download_json(
            'https://api.angelstudios.com/graphql', video_id, data=json.dumps({
                'operationName': 'getEpisodeAndUserWatchData',
                'query': '''
                        fragment EpisodeGuildEarlyAccess on Episode {
                          isAngelGuildOnly, prereleaseAvailableFor, isTrailer, guildAvailableDate, publiclyAvailableDate, earlyAccessDate, unavailableReason, __typename
                        }

                        query getEpisodeAndUserWatchData($guid: ID!, $projectSlug: String!, $skipsEnabled: Boolean = false, $includePrerelease: Boolean = false, $authenticated: Boolean = false, $reactionsRollupInterval: Int = 4000) {
                          project(slug: $projectSlug) {
                            id, projectType, pifEnabled,
                            metadata { contentRating, externalLinks, genres, __typename },
                            primaryFlowPhases { status, phaseSlugEnum, __typename },
                            discoveryPosterCloudinaryPath, discoveryPosterLandscapeCloudinaryPath, discoveryPosterTransformation, discoveryVideoLandscapeUrl,
                            name, slug,
                            seasons {
                              id, seasonNumber, name,
                              episodes(includePrerelease: $includePrerelease, includePresale: $includePrerelease) {
                                id, guid, slug, episodeNumber, seasonNumber, seasonId, subtitle, description, name,
                                posterCloudinaryPath, posterLandscapeCloudinaryPath, projectSlug, earlyAccessDate, publiclyAvailableDate, guildAvailableDate, releaseDate,
                                source { credits, duration, skipsUrl: url(input: {segmentFormat: TS, muteAllSwears: true}) @include(if: $skipsEnabled), url(input: {segmentFormat: TS}), __typename },
                                unavailableReason,
                                upNext { id, projectSlug, guid, seasonNumber, episodeNumber, subtitle, __typename },
                                watchPosition { position, __typename },
                                introStartTime, introEndTime,
                                ...EpisodeGuildEarlyAccess, __typename
                              }, __typename
                            },
                            logoCloudinaryPath,
                            publisher { name, __typename },
                            trailers { id, name, source { duration, url(input: {segmentFormat: TS}), __typename }, __typename },
                            title {
                              ... on ContentSharable { isGuildShareAvailable, __typename },
                              ... on ContentWatchable { muteAllSwearsAvailability, __typename },
                              ... on ContentWatchableAvailability { watchableAvailabilityStatus, __typename },
                              ... on ContentDisplayable {
                                id,
                                landscapeTitleImage: image(aspect: "16:9", category: TITLE_ART) { aspect, category, cloudinaryPath, __typename },
                                landscapeAngelImage: image(aspect: "16:9", category: ANGEL_KEY_ART_1) { aspect, category, cloudinaryPath, __typename },
                                landscapeAngelImage2: image(aspect: "16:9", category: ANGEL_KEY_ART_2) { aspect, category, cloudinaryPath, __typename },
                                landscapeAngelImage3: image(aspect: "16:9", category: ANGEL_KEY_ART_3) { aspect, category, cloudinaryPath, __typename },
                                portraitTitleImage: image(aspect: "2:3", category: TITLE_ART) { aspect, category, cloudinaryPath, __typename },
                                portraitAngelImage: image(aspect: "2:3", category: ANGEL_KEY_ART_1) { aspect, category, cloudinaryPath, __typename },
                                portraitAngelImage2: image(aspect: "2:3", category: ANGEL_KEY_ART_2) { aspect, category, cloudinaryPath, __typename },
                                portraitAngelImage3: image(aspect: "2:3", category: ANGEL_KEY_ART_3) { aspect, category, cloudinaryPath, __typename },
                                __typename
                              },
                              __typename
                            },
                            __typename
                          },

                          episode(guid: $guid) {
                            description, episodeNumber, guid, id, name, posterCloudinaryPath, posterLandscapeCloudinaryPath, projectSlug, releaseDate, seasonId, seasonNumber, slug, subtitle,
                            source { credits, duration, skipsUrl: url(input: {segmentFormat: TS, muteAllSwears: true}), url(input: {segmentFormat: TS}), __typename },
                            unavailableReason,
                            upNext { id, projectSlug, guid, seasonNumber, episodeNumber, subtitle, __typename },
                            vmapUrl,
                            watchPosition { position, __typename },
                            ...EpisodeGuildEarlyAccess, __typename
                          },

                          user @include(if: $authenticated) {
                            id,
                            videoReactions(videoId: $guid, rollupInterval: $reactionsRollupInterval) { id, momentId, reactedAt, videoGuid, viewerId, __typename },
                            __typename
                          }
                        }''',
                'variables': {'authenticated': True, 'guid': video_id, 'includePrerelease': True, 'projectSlug': 'case-for-christ', 'reactionsRollupInterval': 4000, 'skipsEnabled': False},
            }).encode(), headers={
                'content-type': 'application/json',
                'authorization': auth_cookie,
            }), ('data', 'episode'))

        if (all(var is None for var in [metadata['guildAvailableDate'], metadata['publiclyAvailableDate'], metadata['earlyAccessDate']])):
            raise GeoRestrictedError('This video is unavailable in your location!')
        elif (metadata['publiclyAvailableDate'] is None):
            raise ExtractorError('This is Members Only video. Please log in with your Guild account! ' + self._login_hint(), expected=True)

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

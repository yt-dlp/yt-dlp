import json

from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj


class PlaySuisseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?playsuisse\.ch/(?:watch|detail)/(?:[^#]*[?&]episodeId=)?(?P<id>[0-9]+)'
    _TESTS = [
        {
            # Old URL
            'url': 'https://www.playsuisse.ch/watch/763211/0',
            'only_matching': True,
        },
        {
            # episode in a series
            'url': 'https://www.playsuisse.ch/watch/763182?episodeId=763211',
            'md5': '82df2a470b2dfa60c2d33772a8a60cf8',
            'info_dict': {
                'id': '763211',
                'ext': 'mp4',
                'title': 'Knochen',
                'description': 'md5:8ea7a8076ba000cd9e8bc132fd0afdd8',
                'duration': 3344,
                'series': 'Wilder',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Knochen',
                'episode_number': 1,
                'thumbnail': 're:https://playsuisse-img.akamaized.net/',
            }
        }, {
            # film
            'url': 'https://www.playsuisse.ch/watch/808675',
            'md5': '818b94c1d2d7c4beef953f12cb8f3e75',
            'info_dict': {
                'id': '808675',
                'ext': 'mp4',
                'title': 'Der Läufer',
                'description': 'md5:9f61265c7e6dcc3e046137a792b275fd',
                'duration': 5280,
                'thumbnail': 're:https://playsuisse-img.akamaized.net/',
            }
        }, {
            # series (treated as a playlist)
            'url': 'https://www.playsuisse.ch/detail/1115687',
            'info_dict': {
                'description': 'md5:e4a2ae29a8895823045b5c3145a02aa3',
                'id': '1115687',
                'series': 'They all came out to Montreux',
                'title': 'They all came out to Montreux',
            },
            'playlist': [{
                'info_dict': {
                    'description': 'md5:f2462744834b959a31adc6292380cda2',
                    'duration': 3180,
                    'episode': 'Folge 1',
                    'episode_number': 1,
                    'id': '1112663',
                    'season': 'Season 1',
                    'season_number': 1,
                    'series': 'They all came out to Montreux',
                    'thumbnail': 're:https://playsuisse-img.akamaized.net/',
                    'title': 'Folge 1',
                    'ext': 'mp4'
                },
            }, {
                'info_dict': {
                    'description': 'md5:9dfd308699fe850d3bce12dc1bad9b27',
                    'duration': 2935,
                    'episode': 'Folge 2',
                    'episode_number': 2,
                    'id': '1112661',
                    'season': 'Season 1',
                    'season_number': 1,
                    'series': 'They all came out to Montreux',
                    'thumbnail': 're:https://playsuisse-img.akamaized.net/',
                    'title': 'Folge 2',
                    'ext': 'mp4'
                },
            }, {
                'info_dict': {
                    'description': 'md5:14a93a3356b2492a8f786ab2227ef602',
                    'duration': 2994,
                    'episode': 'Folge 3',
                    'episode_number': 3,
                    'id': '1112664',
                    'season': 'Season 1',
                    'season_number': 1,
                    'series': 'They all came out to Montreux',
                    'thumbnail': 're:https://playsuisse-img.akamaized.net/',
                    'title': 'Folge 3',
                    'ext': 'mp4'
                }
            }],
        }
    ]

    _GRAPHQL_QUERY = '''
        query AssetWatch($assetId: ID!) {
            assetV2(id: $assetId) {
                ...Asset
                episodes {
                    ...Asset
                }
            }
        }
        fragment Asset on AssetV2 {
            id
            name
            description
            duration
            episodeNumber
            seasonNumber
            seriesName
            medias {
                type
                url
            }
            thumbnail16x9 {
                ...ImageDetails
            }
            thumbnail2x3 {
                ...ImageDetails
            }
            thumbnail16x9WithTitle {
                ...ImageDetails
            }
            thumbnail2x3WithTitle {
                ...ImageDetails
            }
        }
        fragment ImageDetails on AssetImage {
            id
            url
        }'''

    def _get_media_data(self, media_id):
        # NOTE In the web app, the "locale" header is used to switch between languages,
        # However this doesn't seem to take effect when passing the header here.
        response = self._download_json(
            'https://4bbepzm4ef.execute-api.eu-central-1.amazonaws.com/prod/graphql',
            media_id, data=json.dumps({
                'operationName': 'AssetWatch',
                'query': self._GRAPHQL_QUERY,
                'variables': {'assetId': media_id}
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'locale': 'de'})

        return response['data']['assetV2']

    def _real_extract(self, url):
        media_id = self._match_id(url)
        media_data = self._get_media_data(media_id)
        info = self._extract_single(media_data)
        if media_data.get('episodes'):
            info.update({
                '_type': 'playlist',
                'entries': map(self._extract_single, media_data['episodes']),
            })
        return info

    def _extract_single(self, media_data):
        thumbnails = traverse_obj(media_data, lambda k, _: k.startswith('thumbnail'))

        formats, subtitles = [], {}
        for media in traverse_obj(media_data, 'medias', default=[]):
            if not media.get('url') or media.get('type') != 'HLS':
                continue
            f, subs = self._extract_m3u8_formats_and_subtitles(
                media['url'], media_data['id'], 'mp4', m3u8_id='HLS', fatal=False)
            formats.extend(f)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': media_data['id'],
            'title': media_data.get('name'),
            'description': media_data.get('description'),
            'thumbnails': thumbnails,
            'duration': int_or_none(media_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'series': media_data.get('seriesName'),
            'season_number': int_or_none(media_data.get('seasonNumber')),
            'episode': media_data.get('name') if media_data.get('episodeNumber') else None,
            'episode_number': int_or_none(media_data.get('episodeNumber')),
        }

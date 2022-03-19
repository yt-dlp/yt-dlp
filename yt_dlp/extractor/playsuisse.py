# coding: utf-8
import json

from .common import InfoExtractor
from ..utils import int_or_none


class PlaySuisseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?playsuisse\.ch/watch/(?P<id>[0-9]+)'
    _TESTS = [
        {
            'url': 'https://www.playsuisse.ch/watch/763211/0',
            'md5': '0d716b7a16c3e6ab784ef817ee9a20c1',
            'info_dict': {
                'id': '763211',
                'ext': 'mp4',
                'title': 'Knochen',
                'description': 'md5:8ea7a8076ba000cd9e8bc132fd0afdd8'
            }
        },
        {
            'url': 'https://www.playsuisse.ch/watch/808675/0',
            'md5': '7c59b60aadd84b3e36d46dea01125442',
            'info_dict': {
                'id': '808675',
                'ext': 'mp4',
                'title': 'Der Läufer',
                'description': 'md5:9f61265c7e6dcc3e046137a792b275fd'
            }
        },
        {
            'url': 'https://www.playsuisse.ch/watch/817193/0',
            'md5': 'eff6791c38784543f6d87a58bfe5de15',
            'info_dict': {
                'id': '817193',
                'ext': 'mp4',
                'title': 'Die Einweihungsparty',
                'series': 'Nr. 47',
                'season_number': 1,
                'episode': 'Die Einweihungsparty',
                'episode_number': 1,
                'description': 'md5:91ebf04d3a42cb3ab70666acf750a930'
            }
        }
    ]

    _GRAPHQL_QUERY = '''
        query AssetWatch($assetId: ID!) {
            asset(assetId: $assetId) {
                name
                description
                duration
                episodeNumber
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
        }
        fragment ImageDetails on Image {
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

        return response['data']['asset']

    def _real_extract(self, url):
        media_id = self._match_id(url)
        media_data = self._get_media_data(media_id)

        thumbnails = [{
            'id': thumb['id'],
            'url': thumb['url']
        } for key, thumb in media_data.items() if key.startswith('thumbnail') and thumb is not None]

        formats, subtitles = [], {}
        for media in media_data['medias']:
            if not media.get('url') or media.get('type') != 'HLS':
                continue
            f, subs = self._extract_m3u8_formats_and_subtitles(
                media['url'], media_id, 'mp4', 'm3u8_native', m3u8_id='HLS', fatal=False)
            formats.extend(f)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': media_id,
            'title': media_data.get('name'),
            'description': media_data.get('description'),
            'thumbnails': thumbnails,
            'duration': int_or_none(media_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'series': media_data.get('seriesName'),
            'season_number': int_or_none(media_data.get('seasonNumber')),
            'episode': media_data.get('name'),
            'episode_number': int_or_none(media_data.get('episodeNumber')),
        }

import json
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    int_or_none,
    merge_dicts,
    parse_duration,
    parse_iso8601,
    parse_resolution,
    try_call,
    update_url,
    url_or_none,
)
from ..utils.traversal import find_elements, traverse_obj


class CNNIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:edition|www|money|cnnespanol)\.)?cnn\.com/(?!audio/)(?P<display_id>[^?#]+?)(?:[?#]|$|/index\.html)'

    _TESTS = [{
        'url': 'https://www.cnn.com/2024/05/31/sport/video/jadon-sancho-borussia-dortmund-champions-league-exclusive-spt-intl',
        'info_dict': {
            'id': 'med0e97ad0d154f56e29aa96e57192a14226734b6b',
            'display_id': '2024/05/31/sport/video/jadon-sancho-borussia-dortmund-champions-league-exclusive-spt-intl',
            'ext': 'mp4',
            'upload_date': '20240531',
            'description': 'md5:844bcdb0629e1877a7a466c913f4c19c',
            'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/gettyimages-2151936122.jpg?c=original',
            'duration': 373.0,
            'timestamp': 1717148586,
            'title': 'Borussia Dortmund star Jadon Sancho seeks Wembley redemption after 2020 Euros hurt',
            'modified_date': '20240531',
            'modified_timestamp': 1717150140,
        },
    }, {
        'url': 'https://edition.cnn.com/2024/06/11/politics/video/inmates-vote-jail-nevada-murray-dnt-ac360-digvid',
        'info_dict': {
            'id': 'me522945c4709b299e5cb8657900a7a21ad3b559f9',
            'display_id': '2024/06/11/politics/video/inmates-vote-jail-nevada-murray-dnt-ac360-digvid',
            'ext': 'mp4',
            'description': 'md5:e0120fe5da9ad8259fd707c1cbb64a60',
            'title': 'Here’s how some inmates in closely divided state are now able to vote from jail',
            'timestamp': 1718158269,
            'upload_date': '20240612',
            'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/still-20701554-13565-571-still.jpg?c=original',
            'duration': 202.0,
            'modified_date': '20240612',
            'modified_timestamp': 1718158509,
        },
    }, {
        'url': 'https://edition.cnn.com/2024/06/11/style/king-charles-portrait-vandalized/index.html',
        'info_dict': {
            'id': 'mef5f52b9e1fe28b1ad192afcbc9206ae984894b68',
            'display_id': '2024/06/11/style/king-charles-portrait-vandalized',
            'ext': 'mp4',
            'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/still-20701257-8846-816-still.jpg?c=original',
            'description': 'md5:19f78338ccec533db0fa8a4511012dae',
            'title': 'Video shows King Charles\' portrait being vandalized by activists',
            'timestamp': 1718113852,
            'upload_date': '20240611',
            'duration': 51.0,
            'modified_timestamp': 1718116193,
            'modified_date': '20240611',
        },
    }, {
        'url': 'https://edition.cnn.com/videos/media/2022/12/05/robin-meade-final-sign-off-broadcast-hln-mxp-contd-vpx.hln',
        'info_dict': {
            'id': 'mefba13799201b084ea3b1d0f7ca820ae94d4bb5b2',
            'display_id': 'videos/media/2022/12/05/robin-meade-final-sign-off-broadcast-hln-mxp-contd-vpx.hln',
            'ext': 'mp4',
            'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/221205163510-robin-meade-sign-off.jpg?c=original',
            'duration': 158.0,
            'title': 'Robin Meade signs off after HLN\'s last broadcast',
            'description': 'md5:cff3c62d18d2fbc6c5c75cb029b7353b',
            'upload_date': '20221205',
            'timestamp': 1670284296,
            'modified_timestamp': 1670332404,
            'modified_date': '20221206',
        },
        'params': {'format': 'direct'},
    }, {
        'url': 'https://cnnespanol.cnn.com/video/ataque-misil-israel-beirut-libano-octubre-trax',
        'info_dict': {
            'id': 'me484a43722642aa00627b812fe928f2e99c6e2997',
            'ext': 'mp4',
            'display_id': 'video/ataque-misil-israel-beirut-libano-octubre-trax',
            'timestamp': 1729501452,
            'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/ataqeubeirut-1.jpg?c=original',
            'description': 'md5:256ee7137d161f776cda429654135e52',
            'upload_date': '20241021',
            'duration': 31.0,
            'title': 'VIDEO | Israel lanza un nuevo ataque sobre Beirut',
            'modified_date': '20241021',
            'modified_timestamp': 1729501530,
        },
    }, {
        'url': 'https://edition.cnn.com/2024/10/16/politics/kamala-harris-fox-news-interview/index.html',
        'info_dict': {
            'id': '2024/10/16/politics/kamala-harris-fox-news-interview',
        },
        'playlist_count': 2,
        'playlist': [{
            'md5': '073ffab87b8bef97c9913e71cc18ef9e',
            'info_dict': {
                'id': 'me19d548fdd54df0924087039283128ef473ab397d',
                'ext': 'mp4',
                'title': '\'I\'m not finished\': Harris interview with Fox News gets heated',
                'display_id': 'kamala-harris-fox-news-interview-ebof-digvid',
                'description': 'md5:e7dd3d1a04df916062230b60ca419a0a',
                'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/harris-20241016234916617.jpg?c=original',
                'duration': 173.0,
                'timestamp': 1729122182,
                'upload_date': '20241016',
                'modified_timestamp': 1729194706,
                'modified_date': '20241017',
            },
            'params': {'format': 'direct'},
        }, {
            'md5': '11604ab4af83b650826753f1ccb8ecff',
            'info_dict': {
                'id': 'med04507d8ca3da827001f63d22af321ec29c7d97b',
                'ext': 'mp4',
                'title': '\'Wise\': Buttigieg on Harris\' handling of interview question about gender transition surgery',
                'display_id': 'pete-buttigieg-harris-fox-newssrc-digvid',
                'description': 'md5:602a8a7e853ed5e574acd3159428c98e',
                'thumbnail': 'https://media.cnn.com/api/v1/images/stellar/prod/buttigieg-20241017040412074.jpg?c=original',
                'duration': 145.0,
                'timestamp': 1729137765,
                'upload_date': '20241017',
                'modified_timestamp': 1729138184,
                'modified_date': '20241017',
            },
            'params': {'format': 'direct'},
        }],
    }]

    def _real_extract(self, url):
        display_id = self._match_valid_url(url).group('display_id')
        webpage = self._download_webpage(url, display_id)
        app_id = traverse_obj(
            self._search_json(r'window\.env\s*=', webpage, 'window env', display_id, default={}),
            ('TOP_AUTH_SERVICE_APP_ID', {str}))

        entries = []
        for player_data in traverse_obj(webpage, (
                {find_elements(tag='div', attr='data-component-name', value='video-player', html=True)},
                ..., {extract_attributes}, all, lambda _, v: v['data-media-id'])):
            media_id = player_data['data-media-id']
            parent_uri = player_data.get('data-video-resource-parent-uri')
            formats, subtitles = [], {}

            video_data = {}
            if parent_uri:
                video_data = self._download_json(
                    'https://fave.api.cnn.io/v1/video', media_id, fatal=False,
                    query={
                        'id': media_id,
                        'stellarUri': parent_uri,
                    })
                for direct_url in traverse_obj(video_data, ('files', ..., 'fileUri', {url_or_none})):
                    resolution, bitrate = None, None
                    if mobj := re.search(r'-(?P<res>\d+x\d+)_(?P<tbr>\d+)k\.mp4', direct_url):
                        resolution, bitrate = mobj.group('res', 'tbr')
                    formats.append({
                        'url': direct_url,
                        'format_id': 'direct',
                        'quality': 1,
                        'tbr': int_or_none(bitrate),
                        **parse_resolution(resolution),
                    })
                for sub_data in traverse_obj(video_data, (
                        'closedCaptions', 'types', lambda _, v: url_or_none(v['track']['url']), 'track')):
                    subtitles.setdefault(sub_data.get('lang') or 'en', []).append({
                        'url': sub_data['url'],
                        'name': sub_data.get('label'),
                    })

            if app_id:
                media_data = self._download_json(
                    f'https://medium.ngtv.io/v2/media/{media_id}/desktop', media_id, fatal=False,
                    query={'appId': app_id})
                m3u8_url = traverse_obj(media_data, (
                    'media', 'desktop', 'unprotected', 'unencrypted', 'url', {url_or_none}))
                if m3u8_url:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        m3u8_url, media_id, 'mp4', m3u8_id='hls', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)

            entries.append({
                **traverse_obj(player_data, {
                    'title': ('data-headline', {clean_html}),
                    'description': ('data-description', {clean_html}),
                    'duration': ('data-duration', {parse_duration}),
                    'timestamp': ('data-publish-date', {parse_iso8601}),
                    'thumbnail': (
                        'data-poster-image-override', {json.loads}, 'big', 'uri', {url_or_none},
                        {update_url(query='c=original')}),
                    'display_id': 'data-video-slug',
                }),
                **traverse_obj(video_data, {
                    'timestamp': ('dateCreated', 'uts', {int_or_none(scale=1000)}),
                    'description': ('description', {clean_html}),
                    'title': ('headline', {str}),
                    'modified_timestamp': ('lastModified', 'uts', {int_or_none(scale=1000)}),
                    'duration': ('trt', {int_or_none}),
                }),
                'id': media_id,
                'formats': formats,
                'subtitles': subtitles,
            })

        if len(entries) == 1:
            return {
                **entries[0],
                'display_id': display_id,
            }

        return self.playlist_result(entries, display_id)


class CNNIndonesiaIE(InfoExtractor):
    _VALID_URL = r'https?://www\.cnnindonesia\.com/[\w-]+/(?P<upload_date>\d{8})\d+-\d+-(?P<id>\d+)/(?P<display_id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.cnnindonesia.com/ekonomi/20220909212635-89-845885/alasan-harga-bbm-di-indonesia-masih-disubsidi',
        'info_dict': {
            'id': '845885',
            'ext': 'mp4',
            'description': 'md5:e7954bfa6f1749bc9ef0c079a719c347',
            'upload_date': '20220909',
            'title': 'Alasan Harga BBM di Indonesia Masih Disubsidi',
            'timestamp': 1662859088,
            'duration': 120.0,
            'thumbnail': r're:https://akcdn\.detik\.net\.id/visual/2022/09/09/thumbnail-ekopedia-alasan-harga-bbm-disubsidi_169\.jpeg',
            'tags': ['ekopedia', 'subsidi bbm', 'subsidi', 'bbm', 'bbm subsidi', 'harga pertalite naik'],
            'age_limit': 0,
            'release_timestamp': 1662859088,
            'release_date': '20220911',
            'uploader': 'Asfahan Yahsyi',
        },
    }, {
        'url': 'https://www.cnnindonesia.com/internasional/20220911104341-139-846189/video-momen-charles-disambut-meriah-usai-dilantik-jadi-raja-inggris',
        'info_dict': {
            'id': '846189',
            'ext': 'mp4',
            'upload_date': '20220911',
            'duration': 76.0,
            'timestamp': 1662869995,
            'description': 'md5:ece7b003b3ee7d81c6a5cfede7d5397d',
            'thumbnail': r're:https://akcdn\.detik\.net\.id/visual/2022/09/11/thumbnail-video-1_169\.jpeg',
            'title': 'VIDEO: Momen Charles Disambut Meriah usai Dilantik jadi Raja Inggris',
            'tags': ['raja charles', 'raja charles iii', 'ratu elizabeth', 'ratu elizabeth meninggal dunia', 'raja inggris', 'inggris'],
            'age_limit': 0,
            'release_date': '20220911',
            'uploader': 'REUTERS',
            'release_timestamp': 1662869995,
        },
    }]

    def _real_extract(self, url):
        upload_date, video_id, display_id = self._match_valid_url(url).group('upload_date', 'id', 'display_id')
        webpage = self._download_webpage(url, display_id)

        json_ld_list = list(self._yield_json_ld(webpage, display_id))
        json_ld_data = self._json_ld(json_ld_list, display_id)
        embed_url = next(
            json_ld.get('embedUrl') for json_ld in json_ld_list if json_ld.get('@type') == 'VideoObject')

        return merge_dicts(json_ld_data, {
            '_type': 'url_transparent',
            'url': embed_url,
            'upload_date': upload_date,
            'tags': try_call(lambda: self._html_search_meta('keywords', webpage).split(', ')),
        })

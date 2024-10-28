import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_iso8601,
    strip_or_none,
    unified_timestamp,
    update_url_query,
)
from ..utils.traversal import traverse_obj


class FifaContentIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?plus\.fifa\.com/(?P<locale>\w{2})/content/(?P<display_id>[\w-]+)/(?P<id>[\w-]+)/?(?:[#?]|$)'

    def _real_initialize(self):
        self._HEADERS = {
            'content-type': 'application/json; charset=UTF-8',
            'x-chili-accept-language': 'en',
            'x-chili-api-version': '1.1',
            'x-chili-authenticated': 'false',
            'x-chili-device-id': 'undefined',
            'x-chili-device-profile': 'WEB',
            'x-chili-device-store': 'CHILI',
            'x-chili-user-country': 'US',
            'x-chili-accept-stream-mode': 'multi/codec-compatibility;q=0.8, mono/strict;q=0.7',
            'x-chili-avod-compatibility': 'free,free-ads',
            'x-chili-manifest-properties': 'subtitles',
            'x-chili-streaming-proto': 'https',
        }
        device_info = self._download_json(
            'https://www.plus.fifa.com/gatekeeper/api/v1/devices/', None, 'Getting device info',
            headers=self._HEADERS,
            data=json.dumps({
                'appVersion': '2.6.93',
                'displayName': None,
                'model': 'Chrome',
                'manufacturer': 'Google Inc.',
                'osName': 'Windows',
                'osVersion': '10',
                'platform': 'Chrome',
                'platformVersion': '129.0.0.0',
                'architecture': 'unknown',
                'profile': 'WEB',
                'store': 'CHILI',
                'screenWidth': '1920',
                'screenHeight': '1080',
            }).encode())
        self._HEADERS['x-chili-device-id'] = device_info['id']

    def _call_api(self, path, video_id, note=None, headers=None, query=None, data=None):
        return self._download_json(
            f'https://www.plus.fifa.com/flux-capacitor/api/v1//{path}', video_id, note, headers={
                **self._HEADERS,
                **(headers or {}),
            }, query=query, data=data)

    def _real_extract(self, url):
        urlh = self._request_webpage(url, self._match_id(url))
        video_id, display_id, locale = self._match_valid_url(urlh.url).group('id', 'display_id', 'locale')

        video_info = self._call_api(
            'videoasset', video_id, 'Downloading video asset', query={'catalog': video_id})[0]

        formats = []
        subtitles = {}

        for stream_type in [
            'hls/cbcs+h265.sdr;q=0.9, hls/cbcs+h264;q=0.5, hls/clear+h264;q=0.4, mp4/;q=0.1',
            'mpd/cenc+h264;q=0.9, mpd/clear+h264;q=0.7, mp4/;q=0.1',
        ]:
            session_info = self._call_api(
                'streaming/session', video_id, 'Getting streaming session',
                headers={'x-chili-accept-stream': stream_type},
                data=json.dumps({'videoAssetId': video_info['id'], 'autoPlay': False}).encode())

            streams_info = self._call_api(
                'streaming/urls', video_id, 'Getting streaming urls',
                headers={'x-chili-streaming-session': session_info['id']})

            for playlist_url in traverse_obj(streams_info, (..., 'url')):
                ext = determine_ext(playlist_url)
                if ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(playlist_url, video_id)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                elif ext == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(playlist_url, video_id, m3u8_id='hls')
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    raise ExtractorError(f'Unknown playlist URL {playlist_url}', video_id=video_id)

        self._remove_duplicate_formats(formats)

        return {
            'id': video_id,
            'title': video_info['title'],
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [{
                'url': update_url_query(x, {'width': 1408}),
                'width': 1408,
            } for x in [video_info.get('posterUrl'), video_info.get('wideCoverUrl')] if x],
        }


class FifaBaseIE(InfoExtractor):
    @functools.cached_property
    def _preconnect_link(self):
        return self._search_regex(
            r'<link\b[^>]+\brel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"',
            self._download_webpage('https://fifa.com/', None), 'Preconnect Link')

    def _call_api(self, path, video_id, note=None, query=None, fatal=True):
        return self._download_json(
            f'{self._preconnect_link}/{path}', video_id, note, query=query, fatal=fatal)


class FifaIE(FifaBaseIE):
    _VALID_URL = r'https?://(www\.)?fifa\.com/(fifaplus/)?(?P<locale>\w{2})/watch/(?P<id>[-\w]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/7on10qPcnyLajDDU3ntg6y',
        'info_dict': {
            'id': 'fee2f7e8-92fa-42c5-805c-a2c949015eae',
            'title': 'Italy v France | Final | 2006 FIFA World Cup Germany™ | Full Match Replay',
            'display_id': 'italy-v-france-final-2006-fifa-world-cup-germany-full-match-replay',
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
    }, {
        'url': 'https://www.fifa.com/fifaplus/pt/watch/1cg5r5Qt6Qt12ilkDgb1sV',
        'info_dict': {
            'id': 'd4f4a2cb-5966-4af7-8a05-98ef4732af2b',
            'title': 'Brazil v Germany | Semi-finals | 2014 FIFA World Cup Brazil™ | Extended Highlights',
            'display_id': 'brasil-x-alemanha-semifinais-copa-do-mundo-fifa-brasil-2014-compacto',
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
    }, {
        'url': 'https://www.fifa.com/fifaplus/fr/watch/3C6gQH9C2DLwzNx7BMRQdp',
        'info_dict': {
            'id': '3C6gQH9C2DLwzNx7BMRQdp',
            'ext': 'mp4',
            'title': 'Josimar goal against Northern Ireland | Classic Goals',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'HTTP Error 403: Forbidden',
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/2KhLLn6aiGW3nr8sNm8Hkv',
        'info_dict': {
            'id': '2KhLLn6aiGW3nr8sNm8Hkv',
            'ext': 'mp4',
            'title': "Le Sommer: Lyon-Barcelona a beautiful final for women's football",
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'HTTP Error 403: Forbidden',
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/4V8H8qv7QM1LNVk5gUwYFa',
        'info_dict': {
            'id': '709abaec-5eef-4ad8-a02d-19a8932f42a2',
            'title': "Christine Sinclair at 19 | FIFA U-19 Women's World Championship Canada 2002™",
            'display_id': 'christine-sinclair-at-19-fifa-u-19-womens-world-championship-canada-2002',
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/d85632f9-7009-4ea0-aaf1-8d6847e4a148',
        'info_dict': {
            'id': 'bbe5d2a3-3dfd-4283-a1af-3a66022e8254',
            'title': 'Croatia v Australia | Group F | 2006 FIFA World Cup Germany™ | Full Match Replay',
            'display_id': 'croatia-v-australia-or-group-f-or-2006-fifa-world-cup',
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
    }, {
        'url': 'https://www.fifa.com/fifaplus/pt/watch/Ny88zzqsVnxCBUJ6fZzPy',
        'info_dict': {
            'id': '3d2612ff-c06f-4a7e-a2d7-ec73504515b5',
            'title': 'The Happiest Man in the World',
            'display_id': 'o-homem-mais-feliz-do-mundo',
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
    }]

    def _real_extract(self, url):
        video_id, locale = self._match_valid_url(url).group('id', 'locale')

        if redirect_url := traverse_obj(self._call_api(
                f'pages/{locale}/watch/{video_id}', video_id, 'Downloading redirection info'), 'redirectUrl'):
            return self.url_result(redirect_url)
        urlh = self._request_webpage(url, self._match_id(url))
        if urlh.url != url:
            return self.url_result(urlh.url)

        video_details = self._call_api(
            f'sections/videoDetails/{video_id}', video_id, 'Downloading Video Details', fatal=False)

        preplay_parameters = self._call_api(
            f'videoPlayerData/{video_id}', video_id, 'Downloading Preplay Parameters')['preplayParameters']

        content_data = self._download_json(
            'https://content.uplynk.com/preplay/{contentId}/multiple.json?{queryStr}&sig={signature}'.format(**preplay_parameters),
            video_id, 'Downloading Content Data')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(content_data['playURL'], video_id)

        return {
            'id': video_id,
            'title': video_details.get('title'),
            'description': video_details.get('description'),
            'duration': int_or_none(video_details.get('duration')),
            'release_timestamp': unified_timestamp(video_details.get('dateOfRelease')),
            'categories': traverse_obj(video_details, (('videoCategory', 'videoSubcategory'),)),
            'thumbnail': traverse_obj(video_details, ('backgroundImage', 'src')),
            'formats': formats,
            'subtitles': subtitles,
        }


class FifaArticleIE(FifaBaseIE):
    _VALID_URL = r'https?://(www\.)?fifa\.com/(fifaplus/)?(?P<locale>\w{2})/articles/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.fifa.com/en/articles/foord-talks-2023-and-battling-kerr-for-the-wsl-title',
        'info_dict': {
            '_type': 'multi_video',
            'id': 'foord-talks-2023-and-battling-kerr-for-the-wsl-title',
            'title': 'Foord talks 2023 and battling Kerr for the WSL title',
            'timestamp': 1651136400,
            'upload_date': '20220428',
        },
        'playlist': [{
            'info_dict': {
                'id': '6B2xtOT2SDMB4JeF3i9n2y',
                'ext': 'mp4',
                'title': 'Foord & Kerr: Friends and rivals',
                'description': 'md5:756e14e1814196948ec4d2a9663f7214',
                'duration': 82,
                'categories': ['News', 'Interview'],
                'thumbnail': r're:https://digitalhub\.fifa\.com/transform/[^/]+/\w+',
            },
        }, {
            'info_dict': {
                'id': 'R2Y1vbwvggrlSr02Cfr99',
                'ext': 'mp4',
                'title': 'Foord: 2023 will be the best Women\'s World Cup yet',
                'description': 'Matildas star Caitlin Foord looks ahead to the FIFA Women\'s World Cup Australia & New Zealand 2023™.',
                'duration': 44,
                'categories': ['News', 'Interview'],
                'thumbnail': r're:https://digitalhub\.fifa\.com/transform/[^/]+/\w+',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/articles/stars-set-to-collide-in-uwcl-final',
        'info_dict': {
            '_type': 'multi_video',
            'id': 'stars-set-to-collide-in-uwcl-final',
            'title': 'Stars set to collide in Women’s Champions League final ',
            'timestamp': 1652950800,
            'upload_date': '20220519',
        },
        'playlist_count': 3,
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        article_id, locale = self._match_valid_url(url).group('id', 'locale')

        page_id = self._call_api(f'pages/en/articles/{article_id}', article_id)['pageId']
        page_info = self._call_api(f'sections/article/{page_id}', article_id, query={'locale': locale})

        video_ids = []
        if hero_video_entry_id := page_info.get('heroVideoEntryId'):
            video_ids.append(hero_video_entry_id)

        video_ids.extend(traverse_obj(page_info, (
            'richtext', 'content', lambda _, v: v['data']['target']['contentTypesCheckboxValue'] == 'Video',
            'data', 'target', 'sys', 'id')))

        return self.playlist_from_matches(
            video_ids, article_id, page_info.get('articleTitle'),
            getter=lambda x: f'https://www.fifa.com/fifaplus/{locale}/watch/{x}',
            ie=FifaIE, multi_video=True, timestamp=parse_iso8601(page_info.get('articlePublishedDate')))


class FifaMovieIE(FifaBaseIE):
    _VALID_URL = r'https?://(www\.)?fifa\.com/fifaplus/(?P<locale>\w{2})/watch/movie/(?P<id>\w+)[/?\?\#]?'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/2OFuZ9TGyPH6x7nZsgnVBN',
        'info_dict': {
            '_type': 'multi_video',
            'id': '2OFuZ9TGyPH6x7nZsgnVBN',
            'title': 'Bravas de Juárez',
            'description': 'md5:1c36885f34d1c142f66ddd5acd5226b2',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/01ioUo8QHiajSisrvP3ES2',
        'info_dict': {
            '_type': 'multi_video',
            'id': '01ioUo8QHiajSisrvP3ES2',
            'title': 'Le Moment | The Official Film of the 2019 FIFA Women’s World Cup™',
            'description': 'md5:fbc803feb6fcbc82d2a73e914244484c',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/69GbI9lVcwhOeBvea5eKUB',
        'info_dict': {
            '_type': 'multi_video',
            'id': '69GbI9lVcwhOeBvea5eKUB',
            'title': 'Dreams | The Official Film of the 2018 FIFA World Cup™',
            'description': 'md5:e79dd17af4dcab1dd446ef6e22a79330',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        movie_id, locale = self._match_valid_url(url).group('id', 'locale')

        movie_details = self._call_api(
            f'sections/movieDetails/{movie_id}', movie_id, 'Downloading Movie Details', query={'locale': locale})

        video_ids = traverse_obj(movie_details, ('trailers', ..., 'entryId'))
        if video_entry_id := traverse_obj(movie_details, ('video', 'videoEntryId')):
            video_ids.append(video_entry_id)

        return self.playlist_from_matches(
            video_ids, movie_id, traverse_obj(movie_details, ('video', 'title')),
            getter=lambda x: f'https://www.fifa.com/fifaplus/{locale}/watch/{x}',
            ie=FifaIE, multi_video=True, playlist_description=traverse_obj(movie_details, ('video', 'description')))


class FifaSeriesIE(FifaBaseIE):
    _VALID_URL = r'https?://(www\.)?fifa\.com/fifaplus/(?P<locale>\w{2})/watch/series/(?P<serie_id>\w+)/(?P<season_id>\w+)/(?P<episode_id>\w+)[/?\?\#]?'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/series/48PQFX2J4TiDJcxWOxUPho/2ka5yomq8MBvfxe205zdQ9/6H72309PLWXafBIavvPzPQ#ReadMore',
        'info_dict': {
            '_type': 'multi_video',
            'id': '48PQFX2J4TiDJcxWOxUPho',
            'title': 'Episode 1 | Kariobangi',
            'description': 'md5:ecbc8668f828d3cc2c0d00edcc0af04f',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://www.fifa.com/fifaplus/en/watch/series/5Ja1dDLuudkFF95OVHcYBG/5epcWav73zMbjTJh2RxIOt/1NIHdDxPlYodbNobjS1iX5',
        'info_dict': {
            '_type': 'multi_video',
            'id': '5Ja1dDLuudkFF95OVHcYBG',
            'title': 'Paul Pogba and Aaron Wan Bissaka | HD Cutz',
            'description': 'md5:16dc373774f503ef91f4489ca17c3f49',
        },
        'playlist_count': 10,
    }]

    def _real_extract(self, url):
        series_id, locale, season_id, episode_id = self._match_valid_url(url).group('serie_id', 'locale', 'season_id', 'episode_id')

        serie_details = self._call_api(
            'sections/videoEpisodeDetails', series_id, 'Downloading Serie Details', query={
                'locale': locale,
                'seriesId': series_id,
                'seasonId': season_id,
                'episodeId': episode_id,
            })

        video_ids = traverse_obj(serie_details, ('seasons', ..., 'episodes', ..., 'entryId'))
        video_ids.extend(traverse_obj(serie_details, ('trailers', ..., 'entryId')))

        return self.playlist_from_matches(
            video_ids, series_id, strip_or_none(serie_details.get('title')),
            getter=lambda x: f'https://www.fifa.com/fifaplus/{locale}/watch/{x}',
            ie=FifaIE, multi_video=True, playlist_description=strip_or_none(serie_details.get('description')))

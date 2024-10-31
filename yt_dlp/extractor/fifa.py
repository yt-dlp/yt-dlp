import functools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    parse_iso8601,
    strip_or_none,
    unified_timestamp,
    update_url_query,
)
from ..utils.traversal import traverse_obj


class FifaBaseIE(InfoExtractor):
    _HEADERS = {
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

    def _call_api(self, path, video_id, note=None, headers=None, query=None, data=None):
        return self._download_json(
            f'https://www.plus.fifa.com/{path}', video_id, note, headers={
                **self._HEADERS,
                **(headers or {}),
            }, query=query, data=data)

    def _real_initialize(self):
        device_info = self._call_api(
            'gatekeeper/api/v1/devices/', None, 'Getting device info',
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

    def _extract_video(self, video_info, video_id):
        formats = []
        subtitles = {}

        for stream_type in [
            'hls/cbcs+h265.sdr;q=0.9, hls/cbcs+h264;q=0.5, hls/clear+h264;q=0.4, mp4/;q=0.1',
            'mpd/cenc+h264;q=0.9, mpd/clear+h264;q=0.7, mp4/;q=0.1',
        ]:
            session_info = self._call_api(
                'flux-capacitor/api/v1/streaming/session', video_id,
                'Getting streaming session', headers={'x-chili-accept-stream': stream_type},
                data=json.dumps({'videoAssetId': video_info['id'], 'autoPlay': False}).encode())
            streams_info = self._call_api(
                'flux-capacitor/api/v1/streaming/urls', video_id, 'Getting streaming urls',
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
            'title': strip_or_none(video_info['title']),
            'duration': float_or_none(video_info.get('duration'), scale=1000),
            'formats': formats,
            'subtitles': subtitles,
            'age_limit': traverse_obj(video_info, ('parental', 'age', {int_or_none})),
            'thumbnails': [{
                'url': update_url_query(x, {'width': 1408}),
                'width': 1408,
            } for x in [video_info.get('posterUrl'), video_info.get('wideCoverUrl')] if x],
        }


class FifaPlayerIE(FifaBaseIE):
    _VALID_URL = r'https?://(www\.)?plus\.fifa\.com/(?:\w{2})/player/(?P<id>[\w-]+)/?\?(?:[^#]+&)?catalogId=(?P<catalog_id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.plus.fifa.com/en/player/f67b9d46-38c3-4e38-bbf3-89cf14cbcc1a?catalogId=b9c32230-1426-46d0-8448-ca824ae48603&entryPoint=Slider',
        'info_dict': {
            'id': 'f67b9d46-38c3-4e38-bbf3-89cf14cbcc1a',
            'ext': 'mp4',
            'title': 'Trailer | HD Cutz',
            'age_limit': 0,
            'duration': 195.84,
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.plus.fifa.com/en/player/af65939f-bbce-4b8f-8462-5140af533c5f?catalogId=fac6685c-a900-4e78-b5cd-192af5131ffe&entryPoint=Slider',
        'md5': '2c4f5c591448d372f6ba85b8f3be37df',
        'info_dict': {
            'id': 'af65939f-bbce-4b8f-8462-5140af533c5f',
            'ext': 'mp4',
            'title': 'Trailer | Bravas de Juárez',
            'age_limit': 0,
            'duration': 73.984,
            'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
        },
    }, {
        'url': 'https://plus.fifa.com/en/player/eeebdd38-5d51-4891-8307-ab5dd62c2c32?catalogId=ed3b2dcb-6886-4b34-8ba7-c8800027f7dd',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, catalog_id = self._match_valid_url(url).group('id', 'catalog_id')
        video_asset = self._call_api(
            'flux-capacitor/api/v1/videoasset', video_id,
            'Downloading video asset', query={'catalog': catalog_id})
        video_info = traverse_obj(video_asset, (lambda _, v: v['id'] == video_id), get_all=False)
        if not video_info:
            raise ExtractorError('Unable to extract video info')
        return self._extract_video(video_info, video_id)


class FifaContentIE(FifaBaseIE):
    _VALID_URL = r'https?://(www\.)?plus\.fifa\.com/(?:\w{2})/content/(?P<display_id>[\w-]+)/(?P<id>[\w-]+)/?(?:[#?]|$)'
    _TESTS = [{
        # from https://www.fifa.com/fifaplus/en/watch/series/48PQFX2J4TiDJcxWOxUPho/2ka5yomq8MBvfxe205zdQ9/6H72309PLWXafBIavvPzPQ#ReadMore
        'url': 'https://www.plus.fifa.com/en/content/kariobangi/6f3be63f-76d9-4290-9e60-fd62afa95ed7',
        'info_dict': {
            'id': '6f3be63f-76d9-4290-9e60-fd62afa95ed7',
            'title': 'Kariobangi',
            'description': 'md5:b57eb012db2b84d482adedda82faf1c8',
            'display_id': 'kariobangi',
            'thumbnails': 'count:2',
        },
        'playlist_count': 0,
    }, {
        # from https://www.fifa.com/fifaplus/en/watch/series/5Ja1dDLuudkFF95OVHcYBG/5epcWav73zMbjTJh2RxIOt/1NIHdDxPlYodbNobjS1iX5
        'url': 'https://www.plus.fifa.com/en/content/hd-cutz/b9c32230-1426-46d0-8448-ca824ae48603',
        'info_dict': {
            'id': 'b9c32230-1426-46d0-8448-ca824ae48603',
            'title': 'HD Cutz',
            'description': 'md5:86dd1e6d9b4463b3ccc2063ab3180c44',
            'display_id': 'hd-cutz',
            'thumbnails': 'count:2',
        },
        'playlist': [{
            'info_dict': {
                'id': 'b9c32230-1426-46d0-8448-ca824ae48603',
                'ext': 'mp4',
                'title': 'Trailer | HD Cutz',
                'age_limit': 0,
                'duration': 195.840,
                'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }, {
        # from https://www.fifa.com/fifaplus/en/watch/movie/2OFuZ9TGyPH6x7nZsgnVBN
        'url': 'https://www.plus.fifa.com/en/content/bravas-de-juarez/fac6685c-a900-4e78-b5cd-192af5131ffe',
        'info_dict': {
            'id': 'fac6685c-a900-4e78-b5cd-192af5131ffe',
            'title': 'Bravas de Juárez',
            'description': 'md5:e48e0f56fb27ac334e616976e0e62362',
            'display_id': 'bravas-de-juarez',
        },
        'playlist': [{
            'info_dict': {
                'id': 'fac6685c-a900-4e78-b5cd-192af5131ffe',
                'ext': 'mp4',
                'title': 'Trailer | Bravas de Juárez',
                'age_limit': 0,
                'duration': 73.984,
                'thumbnail': r're:https://cdn\.plus\.fifa\.com//images/public/cms/[/\w-]+\.jpg\?width=1408',
            },
        }],
    }]
    _WEBPAGE_TESTS = [{
        # https://www.plus.fifa.com/en/content/le-moment-the-official-film-of-the-2019-fifa-womens-world-cup/68a89002-0182-4cc7-b858-e548de0fb9cc
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/01ioUo8QHiajSisrvP3ES2',
        'info_dict': {
            'id': '68a89002-0182-4cc7-b858-e548de0fb9cc',
            'title': 'Le Moment',
            'description': 'md5:155f0c28ea9de733668d7eb1f7dbcb52',
            'display_id': 'le-moment-the-official-film-of-the-2019-fifa-womens-world-cup',
        },
        'playlist_count': 0,
    }, {
        # https://www.plus.fifa.com/en/content/dreams-2018-fifa-world-cup-official-film/ebdce1da-ab82-4c0b-a7d3-b4fc71030339
        'url': 'https://www.fifa.com/fifaplus/en/watch/movie/69GbI9lVcwhOeBvea5eKUB',
        'info_dict': {
            'id': 'ebdce1da-ab82-4c0b-a7d3-b4fc71030339',
            'title': 'Dreams',
            'description': 'md5:b795d218d5c2b88bff3c1569cb617acb',
            'display_id': 'dreams-2018-fifa-world-cup-official-film',
        },
        'playlist_count': 0,
    }]

    def _entries(self, video_asset, video_id):
        # trailers are non-DRM'd
        for video_info in traverse_obj(video_asset, (lambda _, v: v['type'] == 'TRAILER', {dict})):
            yield self._extract_video(video_info, video_id)

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')

        video_content = self._call_api(
            f'entertainment/api/v1/contents/{video_id}', video_id, 'Downloading video content')
        video_asset = self._call_api(
            'flux-capacitor/api/v1/videoasset', video_id,
            'Downloading video asset', query={'catalog': video_id})

        thumbnails = []
        for key, width in [('coverUrl', 330), ('wideCoverUrl', 1408)]:
            if thumbnail_url := video_content.get(key):
                thumbnails.append({
                    'url': update_url_query(thumbnail_url, {'width': width}),
                    'width': width,
                })

        return self.playlist_result(
            self._entries(video_asset, video_id), video_id,
            strip_or_none(video_content['title']), strip_or_none(video_content.get('storyLine')),
            display_id=display_id, thumbnails=thumbnails)


class FifaArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?fifa\.com/(fifaplus/)?(?P<locale>\w{2})/articles/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.fifa.com/en/articles/foord-talks-2023-and-battling-kerr-for-the-wsl-title',
        'info_dict': {
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
        # https://www.fifa.com/en/articles/stars-set-to-collide-in-uwcl-final
        'url': 'https://www.fifa.com/fifaplus/en/articles/stars-set-to-collide-in-uwcl-final',
        'only_matching': True,
    }]

    @functools.cached_property
    def _preconnect_link(self):
        return self._search_regex(
            r'<link\b[^>]+\brel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"',
            self._download_webpage('https://fifa.com/', None), 'Preconnect Link')

    def _call_api(self, path, video_id, note=None, query=None, fatal=True):
        return self._download_json(
            f'{self._preconnect_link}/{path}', video_id, note, query=query, fatal=fatal)

    def _entries(self, video_ids, article_id):
        for video_id in video_ids:
            video_details = self._call_api(
                f'sections/videoDetails/{video_id}', article_id,
                'Downloading Video Details', fatal=False)

            preplay_parameters = self._call_api(
                f'videoPlayerData/{video_id}', article_id,
                'Downloading Preplay Parameters')['preplayParameters']
            content_data = self._download_json(
                'https://content.uplynk.com/preplay/{contentId}/multiple.json?{queryStr}&sig={signature}'.format(
                    **preplay_parameters), article_id, 'Downloading Content Data')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(content_data['playURL'], article_id)

            yield {
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

        return self.playlist_result(
            self._entries(video_ids, article_id), article_id, page_info.get('articleTitle'),
            timestamp=parse_iso8601(page_info.get('articlePublishedDate')))

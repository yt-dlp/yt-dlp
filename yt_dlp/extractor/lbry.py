import functools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    UnsupportedError,
    determine_ext,
    int_or_none,
    mimetype2ext,
    parse_qs,
    traverse_obj,
    try_get,
    url_or_none,
    urlhandle_detect_ext,
    urljoin,
)


class LBRYBaseIE(InfoExtractor):
    _BASE_URL_REGEX = r'(?x)(?:https?://(?:www\.)?(?:lbry\.tv|odysee\.com)/|lbry://)'
    _CLAIM_ID_REGEX = r'[0-9a-f]{1,40}'
    _OPT_CLAIM_ID = f'[^$@:/?#&]+(?:[:#]{_CLAIM_ID_REGEX})?'
    _SUPPORTED_STREAM_TYPES = ['video', 'audio']
    _PAGE_SIZE = 50

    def _call_api_proxy(self, method, display_id, params, resource):
        headers = {'Content-Type': 'application/json-rpc'}
        token = try_get(self._get_cookies('https://odysee.com'), lambda x: x['auth_token'].value)
        if token:
            headers['x-lbry-auth-token'] = token
        response = self._download_json(
            'https://api.lbry.tv/api/v1/proxy',
            display_id, f'Downloading {resource} JSON metadata',
            headers=headers,
            data=json.dumps({
                'method': method,
                'params': params,
            }).encode())
        err = response.get('error')
        if err:
            raise ExtractorError(
                f'{self.IE_NAME} said: {err.get("code")} - {err.get("message")}', expected=True)
        return response['result']

    def _resolve_url(self, url, display_id, resource):
        return self._call_api_proxy(
            'resolve', display_id, {'urls': url}, resource)[url]

    def _permanent_url(self, url, claim_name, claim_id):
        return urljoin(
            url.replace('lbry://', 'https://lbry.tv/'),
            f'/{claim_name}:{claim_id}')

    def _parse_stream(self, stream, url):
        stream_type = traverse_obj(stream, ('value', 'stream_type', {str}))

        info = traverse_obj(stream, {
            'title': ('value', 'title', {str}),
            'thumbnail': ('value', 'thumbnail', 'url', {url_or_none}),
            'description': ('value', 'description', {str}),
            'license': ('value', 'license', {str}),
            'timestamp': ('timestamp', {int_or_none}),
            'release_timestamp': ('value', 'release_time', {int_or_none}),
            'tags': ('value', 'tags', ..., {lambda x: x or None}),
            'duration': ('value', stream_type, 'duration', {int_or_none}),
            'channel': ('signing_channel', 'value', 'title', {str}),
            'channel_id': ('signing_channel', 'claim_id', {str}),
            'uploader_id': ('signing_channel', 'name', {str}),
        })

        if info.get('uploader_id') and info.get('channel_id'):
            info['channel_url'] = self._permanent_url(url, info['uploader_id'], info['channel_id'])

        return info

    def _fetch_page(self, display_id, url, params, page):
        page += 1
        page_params = {
            'no_totals': True,
            'page': page,
            'page_size': self._PAGE_SIZE,
            **params,
        }
        result = self._call_api_proxy(
            'claim_search', display_id, page_params, f'page {page}')
        for item in traverse_obj(result, ('items', lambda _, v: v['name'] and v['claim_id'])):
            yield {
                **self._parse_stream(item, url),
                '_type': 'url',
                'id': item['claim_id'],
                'url': self._permanent_url(url, item['name'], item['claim_id']),
            }

    def _playlist_entries(self, url, display_id, claim_param, metadata):
        qs = parse_qs(url)
        content = qs.get('content', [None])[0]
        params = {
            'fee_amount': qs.get('fee_amount', ['>=0'])[0],
            'order_by': {
                'new': ['release_time'],
                'top': ['effective_amount'],
                'trending': ['trending_group', 'trending_mixed'],
            }[qs.get('order', ['new'])[0]],
            'claim_type': 'stream',
            'stream_types': [content] if content in ['audio', 'video'] else self._SUPPORTED_STREAM_TYPES,
            **claim_param,
        }
        duration = qs.get('duration', [None])[0]
        if duration:
            params['duration'] = {
                'long': '>=1200',
                'short': '<=240',
            }[duration]
        language = qs.get('language', ['all'])[0]
        if language != 'all':
            languages = [language]
            if language == 'en':
                languages.append('none')
            params['any_languages'] = languages

        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, display_id, url, params),
            self._PAGE_SIZE)

        return self.playlist_result(
            entries, display_id, **traverse_obj(metadata, ('value', {
                'title': 'title',
                'description': 'description',
            })))


class LBRYIE(LBRYBaseIE):
    IE_NAME = 'lbry'
    _VALID_URL = LBRYBaseIE._BASE_URL_REGEX + rf'''
        (?:\$/(?:download|embed)/)?
        (?P<id>
            [^$@:/?#]+/{LBRYBaseIE._CLAIM_ID_REGEX}
            |(?:@{LBRYBaseIE._OPT_CLAIM_ID}/)?{LBRYBaseIE._OPT_CLAIM_ID}
        )'''
    _TESTS = [{
        # Video
        'url': 'https://lbry.tv/@Mantega:1/First-day-LBRY:1',
        'md5': '65bd7ec1f6744ada55da8e4c48a2edf9',
        'info_dict': {
            'id': '17f983b61f53091fb8ea58a9c56804e4ff8cff4d',
            'ext': 'mp4',
            'title': 'First day in LBRY? Start HERE!',
            'description': 'md5:f6cb5c704b332d37f5119313c2c98f51',
            'timestamp': 1595694354,
            'upload_date': '20200725',
            'release_timestamp': 1595340697,
            'release_date': '20200721',
            'width': 1280,
            'height': 720,
            'thumbnail': 'https://spee.ch/7/67f2d809c263288c.png',
            'license': 'None',
            'uploader_id': '@Mantega',
            'duration': 346,
            'channel': 'LBRY/Odysee rats united!!!',
            'channel_id': '1c8ad6a2ab4e889a71146ae4deeb23bb92dab627',
            'channel_url': 'https://lbry.tv/@Mantega:1c8ad6a2ab4e889a71146ae4deeb23bb92dab627',
            'tags': [
                'first day in lbry',
                'lbc',
                'lbry',
                'start',
                'tutorial',
            ],
        },
    }, {
        # Audio
        'url': 'https://lbry.tv/@LBRYFoundation:0/Episode-1:e',
        'md5': 'c94017d3eba9b49ce085a8fad6b98d00',
        'info_dict': {
            'id': 'e7d93d772bd87e2b62d5ab993c1c3ced86ebb396',
            'ext': 'mp3',
            'title': 'The LBRY Foundation Community Podcast Episode 1 - Introduction, Streaming on LBRY, Transcoding',
            'description': 'md5:661ac4f1db09f31728931d7b88807a61',
            'timestamp': 1591312601,
            'upload_date': '20200604',
            'release_timestamp': 1591312421,
            'release_date': '20200604',
            'tags': list,
            'duration': 2570,
            'channel': 'The LBRY Foundation',
            'channel_id': '0ed629d2b9c601300cacf7eabe9da0be79010212',
            'channel_url': 'https://lbry.tv/@LBRYFoundation:0ed629d2b9c601300cacf7eabe9da0be79010212',
            'vcodec': 'none',
            'thumbnail': 'https://spee.ch/d/0bc63b0e6bf1492d.png',
            'license': 'None',
            'uploader_id': '@LBRYFoundation',
        },
    }, {
        'url': 'https://odysee.com/@gardeningincanada:b/plants-i-will-never-grow-again.-the:e',
        'md5': 'c35fac796f62a14274b4dc2addb5d0ba',
        'info_dict': {
            'id': 'e51671357333fe22ae88aad320bde2f6f96b1410',
            'ext': 'mp4',
            'title': 'PLANTS I WILL NEVER GROW AGAIN. THE BLACK LIST PLANTS FOR A CANADIAN GARDEN | Gardening in Canada 🍁',
            'description': 'md5:9c539c6a03fb843956de61a4d5288d5e',
            'timestamp': 1618254123,
            'upload_date': '20210412',
            'release_timestamp': 1618254002,
            'release_date': '20210412',
            'tags': list,
            'duration': 554,
            'channel': 'Gardening In Canada',
            'channel_id': 'b8be0e93b423dad221abe29545fbe8ec36e806bc',
            'channel_url': 'https://odysee.com/@gardeningincanada:b8be0e93b423dad221abe29545fbe8ec36e806bc',
            'uploader_id': '@gardeningincanada',
            'formats': 'mincount:3',
            'thumbnail': 'https://thumbnails.lbry.com/AgHSc_HzrrE',
            'license': 'Copyrighted (contact publisher)',
        },
    }, {
        # HLS live stream (might expire)
        'url': 'https://odysee.com/@RT:fd/livestream_RT:d',
        'info_dict': {
            'id': 'fdd11cb3ab75f95efb7b3bc2d726aa13ac915b66',
            'ext': 'mp4',
            'live_status': 'is_live',
            'title': 'startswith:RT News | Livestream 24/7',
            'description': 'md5:fe68d0056dfe79c1a6b8ce8c34d5f6fa',
            'timestamp': int,
            'upload_date': str,
            'release_timestamp': int,
            'release_date': str,
            'tags': list,
            'channel': 'RT',
            'channel_id': 'fdd11cb3ab75f95efb7b3bc2d726aa13ac915b66',
            'channel_url': 'https://odysee.com/@RT:fdd11cb3ab75f95efb7b3bc2d726aa13ac915b66',
            'formats': 'mincount:1',
            'thumbnail': 'startswith:https://thumb',
            'license': 'None',
            'uploader_id': '@RT',
        },
        'params': {'skip_download': True},
    }, {
        # original quality format w/higher resolution than HLS formats
        'url': 'https://odysee.com/@wickedtruths:2/Biotechnological-Invasion-of-Skin-(April-2023):4',
        'md5': '305b0b3b369bde1b984961f005b67193',
        'info_dict': {
            'id': '41fbfe805eb73c8d3012c0c49faa0f563274f634',
            'ext': 'mp4',
            'title': 'Biotechnological Invasion of Skin (April 2023)',
            'description': 'md5:fe28689db2cb7ba3436d819ac3ffc378',
            'channel': 'Wicked Truths',
            'channel_id': '23d2bbf856b0ceed5b1d7c5960bcc72da5a20cb0',
            'channel_url': 'https://odysee.com/@wickedtruths:23d2bbf856b0ceed5b1d7c5960bcc72da5a20cb0',
            'uploader_id': '@wickedtruths',
            'timestamp': 1695114347,
            'upload_date': '20230919',
            'release_timestamp': 1685617473,
            'release_date': '20230601',
            'duration': 1063,
            'thumbnail': 'https://thumbs.odycdn.com/4e6d39da4df0cfdad45f64e253a15959.webp',
            'tags': ['smart skin surveillance', 'biotechnology invasion of skin', 'morgellons'],
            'license': 'None',
            'protocol': 'https',  # test for direct mp4 download
        },
    }, {
        'url': 'https://odysee.com/@BrodieRobertson:5/apple-is-tracking-everything-you-do-on:e',
        'only_matching': True,
    }, {
        'url': 'https://odysee.com/@ScammerRevolts:b0/I-SYSKEY\'D-THE-SAME-SCAMMERS-3-TIMES!:b',
        'only_matching': True,
    }, {
        'url': 'https://lbry.tv/Episode-1:e7d93d772bd87e2b62d5ab993c1c3ced86ebb396',
        'only_matching': True,
    }, {
        'url': 'https://lbry.tv/$/embed/Episode-1/e7d93d772bd87e2b62d5ab993c1c3ced86ebb396',
        'only_matching': True,
    }, {
        'url': 'https://lbry.tv/Episode-1:e7',
        'only_matching': True,
    }, {
        'url': 'https://lbry.tv/@LBRYFoundation/Episode-1',
        'only_matching': True,
    }, {
        'url': 'https://lbry.tv/$/download/Episode-1/e7d93d772bd87e2b62d5ab993c1c3ced86ebb396',
        'only_matching': True,
    }, {
        'url': 'https://lbry.tv/@lacajadepandora:a/TRUMP-EST%C3%81-BIEN-PUESTO-con-Pilar-Baselga,-Carlos-Senra,-Luis-Palacios-(720p_30fps_H264-192kbit_AAC):1',
        'only_matching': True,
    }, {
        'url': 'lbry://@lbry#3f/odysee#7',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        if display_id.startswith('@'):
            display_id = display_id.replace(':', '#')
        else:
            display_id = display_id.replace('/', ':')
        display_id = urllib.parse.unquote(display_id)
        uri = 'lbry://' + display_id
        result = self._resolve_url(uri, display_id, 'stream')
        headers = {'Referer': 'https://odysee.com/'}

        formats = []
        stream_type = traverse_obj(result, ('value', 'stream_type', {str}))

        if stream_type in self._SUPPORTED_STREAM_TYPES:
            claim_id, is_live = result['claim_id'], False
            streaming_url = self._call_api_proxy(
                'get', claim_id, {'uri': uri}, 'streaming url')['streaming_url']

            # GET request to v3 API returns original video/audio file if available
            direct_url = re.sub(r'/api/v\d+/', '/api/v3/', streaming_url)
            urlh = self._request_webpage(
                direct_url, display_id, 'Checking for original quality', headers=headers, fatal=False)
            if urlh and urlhandle_detect_ext(urlh) != 'm3u8':
                formats.append({
                    'url': direct_url,
                    'format_id': 'original',
                    'quality': 1,
                    **traverse_obj(result, ('value', {
                        'ext': ('source', (('name', {determine_ext}), ('media_type', {mimetype2ext}))),
                        'filesize': ('source', 'size', {int_or_none}),
                        'width': ('video', 'width', {int_or_none}),
                        'height': ('video', 'height', {int_or_none}),
                    }), get_all=False),
                    'vcodec': 'none' if stream_type == 'audio' else None,
                })

            # HEAD request returns redirect response to m3u8 URL if available
            final_url = self._request_webpage(
                HEADRequest(streaming_url), display_id, headers=headers,
                note='Downloading streaming redirect url info').url

        elif result.get('value_type') == 'stream':
            claim_id, is_live = result['signing_channel']['claim_id'], True
            live_data = self._download_json(
                'https://api.odysee.live/livestream/is_live', claim_id,
                query={'channel_claim_id': claim_id},
                note='Downloading livestream JSON metadata')['data']
            final_url = live_data.get('VideoURL')
            # Upcoming videos may still give VideoURL
            if not live_data.get('Live'):
                final_url = None
                self.raise_no_formats('This stream is not live', True, claim_id)

        else:
            raise UnsupportedError(url)

        if determine_ext(final_url) == 'm3u8':
            formats.extend(self._extract_m3u8_formats(
                final_url, display_id, 'mp4', m3u8_id='hls', live=is_live, headers=headers))

        return {
            **self._parse_stream(result, url),
            'id': claim_id,
            'formats': formats,
            'is_live': is_live,
            'http_headers': headers,
        }


class LBRYChannelIE(LBRYBaseIE):
    IE_NAME = 'lbry:channel'
    _VALID_URL = LBRYBaseIE._BASE_URL_REGEX + rf'(?P<id>@{LBRYBaseIE._OPT_CLAIM_ID})/?(?:[?&]|$)'
    _TESTS = [{
        'url': 'https://lbry.tv/@LBRYFoundation:0',
        'info_dict': {
            'id': '0ed629d2b9c601300cacf7eabe9da0be79010212',
            'title': 'The LBRY Foundation',
            'description': 'Channel for the LBRY Foundation. Follow for updates and news.',
        },
        'playlist_mincount': 29,
    }, {
        'url': 'https://lbry.tv/@LBRYFoundation',
        'only_matching': True,
    }, {
        'url': 'lbry://@lbry#3f',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url).replace(':', '#')
        result = self._resolve_url(f'lbry://{display_id}', display_id, 'channel')
        claim_id = result['claim_id']

        return self._playlist_entries(url, claim_id, {'channel_ids': [claim_id]}, result)


class LBRYPlaylistIE(LBRYBaseIE):
    IE_NAME = 'lbry:playlist'
    _VALID_URL = LBRYBaseIE._BASE_URL_REGEX + r'\$/(?:play)?list/(?P<id>[0-9a-f-]+)'
    _TESTS = [{
        'url': 'https://odysee.com/$/playlist/ffef782f27486f0ac138bde8777f72ebdd0548c2',
        'info_dict': {
            'id': 'ffef782f27486f0ac138bde8777f72ebdd0548c2',
            'title': 'Théâtre Classique',
            'description': 'Théâtre Classique',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://odysee.com/$/list/9c6658b3dd21e4f2a0602d523a13150e2b48b770',
        'info_dict': {
            'id': '9c6658b3dd21e4f2a0602d523a13150e2b48b770',
            'title': 'Social Media Exposed',
            'description': 'md5:98af97317aacd5b85d595775ea37d80e',
        },
        'playlist_mincount': 34,
    }, {
        'url': 'https://odysee.com/$/playlist/938fb11d-215f-4d1c-ad64-723954df2184',
        'info_dict': {
            'id': '938fb11d-215f-4d1c-ad64-723954df2184',
        },
        'playlist_mincount': 1000,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        result = traverse_obj(self._call_api_proxy('claim_search', display_id, {
            'claim_ids': [display_id],
            'no_totals': True,
            'page': 1,
            'page_size': self._PAGE_SIZE,
        }, 'playlist'), ('items', 0))
        claim_param = {'claim_ids': traverse_obj(result, ('value', 'claims', ..., {str}))}

        return self._playlist_entries(url, display_id, claim_param, result)

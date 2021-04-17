# coding: utf-8
from __future__ import unicode_literals

import functools
import json

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_str,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    mimetype2ext,
    OnDemandPagedList,
    try_get,
    urljoin,
)


class LBRYBaseIE(InfoExtractor):
    _BASE_URL_REGEX = r'(?:https?://(?:www\.)?(?:lbry\.tv|odysee\.com)/|lbry://)'
    _CLAIM_ID_REGEX = r'[0-9a-f]{1,40}'
    _OPT_CLAIM_ID = '[^:/?#&]+(?:[:#]%s)?' % _CLAIM_ID_REGEX
    _SUPPORTED_STREAM_TYPES = ['video', 'audio']

    def _call_api_proxy(self, method, display_id, params, resource):
        return self._download_json(
            'https://api.lbry.tv/api/v1/proxy',
            display_id, 'Downloading %s JSON metadata' % resource,
            headers={'Content-Type': 'application/json-rpc'},
            data=json.dumps({
                'method': method,
                'params': params,
            }).encode())['result']

    def _resolve_url(self, url, display_id, resource):
        return self._call_api_proxy(
            'resolve', display_id, {'urls': url}, resource)[url]

    def _permanent_url(self, url, claim_name, claim_id):
        return urljoin(
            url.replace('lbry://', 'https://lbry.tv/'),
            '/%s:%s' % (claim_name, claim_id))

    def _parse_stream(self, stream, url):
        stream_value = stream.get('value') or {}
        stream_type = stream_value.get('stream_type')
        source = stream_value.get('source') or {}
        media = stream_value.get(stream_type) or {}
        signing_channel = stream.get('signing_channel') or {}
        channel_name = signing_channel.get('name')
        channel_claim_id = signing_channel.get('claim_id')
        channel_url = None
        if channel_name and channel_claim_id:
            channel_url = self._permanent_url(url, channel_name, channel_claim_id)

        info = {
            'thumbnail': try_get(stream_value, lambda x: x['thumbnail']['url'], compat_str),
            'description': stream_value.get('description'),
            'license': stream_value.get('license'),
            'timestamp': int_or_none(stream.get('timestamp')),
            'release_timestamp': int_or_none(stream_value.get('release_time')),
            'tags': stream_value.get('tags'),
            'duration': int_or_none(media.get('duration')),
            'channel': try_get(signing_channel, lambda x: x['value']['title']),
            'channel_id': channel_claim_id,
            'channel_url': channel_url,
            'ext': determine_ext(source.get('name')) or mimetype2ext(source.get('media_type')),
            'filesize': int_or_none(source.get('size')),
        }
        if stream_type == 'audio':
            info['vcodec'] = 'none'
        else:
            info.update({
                'width': int_or_none(media.get('width')),
                'height': int_or_none(media.get('height')),
            })
        return info


class LBRYIE(LBRYBaseIE):
    IE_NAME = 'lbry'
    _VALID_URL = LBRYBaseIE._BASE_URL_REGEX + r'(?P<id>\$/[^/]+/[^/]+/{1}|@{0}/{0}|(?!@){0})'.format(LBRYBaseIE._OPT_CLAIM_ID, LBRYBaseIE._CLAIM_ID_REGEX)
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
        }
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
        }
    }, {
        # HLS
        'url': 'https://odysee.com/@gardeningincanada:b/plants-i-will-never-grow-again.-the:e',
        'md5': 'fc82f45ea54915b1495dd7cb5cc1289f',
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
            'formats': 'mincount:3',
        }
    }, {
        'url': 'https://odysee.com/@BrodieRobertson:5/apple-is-tracking-everything-you-do-on:e',
        'only_matching': True,
    }, {
        'url': "https://odysee.com/@ScammerRevolts:b0/I-SYSKEY'D-THE-SAME-SCAMMERS-3-TIMES!:b",
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
        if display_id.startswith('$/'):
            display_id = display_id.split('/', 2)[-1].replace('/', ':')
        else:
            display_id = display_id.replace(':', '#')
        display_id = compat_urllib_parse_unquote(display_id)
        uri = 'lbry://' + display_id
        result = self._resolve_url(uri, display_id, 'stream')
        result_value = result['value']
        if result_value.get('stream_type') not in self._SUPPORTED_STREAM_TYPES:
            raise ExtractorError('Unsupported URL', expected=True)
        claim_id = result['claim_id']
        title = result_value['title']
        streaming_url = self._call_api_proxy(
            'get', claim_id, {'uri': uri}, 'streaming url')['streaming_url']
        info = self._parse_stream(result, url)
        urlh = self._request_webpage(
            streaming_url, display_id, note='Downloading streaming redirect url info')
        if determine_ext(urlh.geturl()) == 'm3u8':
            info['formats'] = self._extract_m3u8_formats(
                urlh.geturl(), display_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls')
            self._sort_formats(info['formats'])
        else:
            info['url'] = streaming_url
        info.update({
            'id': claim_id,
            'title': title,
        })
        return info


class LBRYChannelIE(LBRYBaseIE):
    IE_NAME = 'lbry:channel'
    _VALID_URL = LBRYBaseIE._BASE_URL_REGEX + r'(?P<id>@%s)/?(?:[?&]|$)' % LBRYBaseIE._OPT_CLAIM_ID
    _TESTS = [{
        'url': 'https://lbry.tv/@LBRYFoundation:0',
        'info_dict': {
            'id': '0ed629d2b9c601300cacf7eabe9da0be79010212',
            'title': 'The LBRY Foundation',
            'description': 'Channel for the LBRY Foundation. Follow for updates and news.',
        },
        'playlist_count': 29,
    }, {
        'url': 'https://lbry.tv/@LBRYFoundation',
        'only_matching': True,
    }, {
        'url': 'lbry://@lbry#3f',
        'only_matching': True,
    }]
    _PAGE_SIZE = 50

    def _fetch_page(self, claim_id, url, params, page):
        page += 1
        page_params = {
            'channel_ids': [claim_id],
            'claim_type': 'stream',
            'no_totals': True,
            'page': page,
            'page_size': self._PAGE_SIZE,
        }
        page_params.update(params)
        result = self._call_api_proxy(
            'claim_search', claim_id, page_params, 'page %d' % page)
        for item in (result.get('items') or []):
            stream_claim_name = item.get('name')
            stream_claim_id = item.get('claim_id')
            if not (stream_claim_name and stream_claim_id):
                continue

            info = self._parse_stream(item, url)
            info.update({
                '_type': 'url',
                'id': stream_claim_id,
                'title': try_get(item, lambda x: x['value']['title']),
                'url': self._permanent_url(url, stream_claim_name, stream_claim_id),
            })
            yield info

    def _real_extract(self, url):
        display_id = self._match_id(url).replace(':', '#')
        result = self._resolve_url(
            'lbry://' + display_id, display_id, 'channel')
        claim_id = result['claim_id']
        qs = compat_parse_qs(compat_urllib_parse_urlparse(url).query)
        content = qs.get('content', [None])[0]
        params = {
            'fee_amount': qs.get('fee_amount', ['>=0'])[0],
            'order_by': {
                'new': ['release_time'],
                'top': ['effective_amount'],
                'trending': ['trending_group', 'trending_mixed'],
            }[qs.get('order', ['new'])[0]],
            'stream_types': [content] if content in ['audio', 'video'] else self._SUPPORTED_STREAM_TYPES,
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
            functools.partial(self._fetch_page, claim_id, url, params),
            self._PAGE_SIZE)
        result_value = result.get('value') or {}
        return self.playlist_result(
            entries, claim_id, result_value.get('title'),
            result_value.get('description'))

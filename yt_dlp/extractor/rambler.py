import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    base_url,
    clean_html,
    float_or_none,
    join_nonempty,
    js_to_json,
    parse_iso8601,
    parse_qs,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class RamblerBaseIE(InfoExtractor):
    def _extract_from_rambler_api(self, rambler_id, referrer):
        key = 'uuid' if rambler_id.startswith('record::') else 'id'

        player_data = self._download_json(
            'https://api.vp.rambler.ru/api/v3/records/getPlayerData',
            rambler_id, query={
                'params': json.dumps({
                    'checkReferrerCount': True,
                    'referrer': referrer,
                    key: rambler_id,
                }).encode(),
            })
        if not player_data.get('success'):
            error_type = traverse_obj(player_data, ('error', 'type', {str}, filter))
            error_subtype = traverse_obj(player_data, ('error', 'subtype', {str}, filter))
            raise ExtractorError(
                join_nonempty(error_type, error_subtype, delim=': '), expected=True)
        playlist = player_data['result']['playList']

        formats = []
        for m3u8_url in traverse_obj(playlist, (
            ('directSource', 'source'), {url_or_none}, filter,
        )):
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, rambler_id, 'mp4', fatal=False))
        self._remove_duplicate_formats(formats)

        return {
            'channel': traverse_obj(player_data, ('channel', {str})),
            'formats': formats,
            **traverse_obj(playlist, {
                'id': ('uuid', {str}),
                'title': ('title', {clean_html}),
                'duration': ('duration', {float_or_none(scale=1000)}),
                'release_timestamp': ('startsAt', {parse_iso8601}),
                'thumbnail': (('customScreenshotOrig', 'snapshot'), {url_or_none}, any),
                'webpage_url': ('defaultShareUrl', {url_or_none}),
            }),
        }


class RamblerIE(RamblerBaseIE):
    IE_NAME = 'rambler'
    IE_DESC = 'Рамблер'

    _VALID_URL = [
        r'https?://(?:api\.)?vp\.rambler\.ru/(?:api/(?:other|v3)/)?(?:player/(?:embed|export)\.html|records/getPlayerData)',
        r'https?://(?:[^/]+\.)?rambler\.ru/\w+/(?P<id>[^/?#]+)',
    ]
    _TESTS = [{
        'url': 'https://auto.rambler.ru/roadaccidents/54816856-v-moskve-mashina-s-diplomaticheskimi-nomerami-vrezalas-v-pushku/',
        'info_dict': {
            'id': 'record::356179de-2b91-4e01-9a2c-409dc2f3171d',
            'ext': 'mp4',
            'title': 'Автомобиль с дипномерами врезался в пушку',
            'display_id': '54816856-v-moskve-mashina-s-diplomaticheskimi-nomerami-vrezalas-v-pushku',
            'duration': 26.0,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://api.vp.rambler.ru/api/v3/records/getPlayerData?params=%7B%22referrer%22%3A%22https%3A%2F%2Feda.ru%2Fmediaproject%2Fbystrye-uzhiny%22%2C%22uuid%22%3A%22record%3A%3A13ff0e0c-8f62-41bb-80eb-2a4664854596%22%2C%22playerTemplateId%22%3A12310%2C%22checkReferrerCount%22%3Atrue%7D',
        'info_dict': {
            'id': 'record::13ff0e0c-8f62-41bb-80eb-2a4664854596',
            'ext': 'mp4',
            'title': 'Гречневая лапша с индейкой и арахисом в азиатском стиле',
            'duration': 293.0,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://api.vp.rambler.ru/api/other/player/export.html?id=2314034',
        'info_dict': {
            'id': 'record::6f10ddd6-1222-4ee4-828b-9eba92e7c26f',
            'ext': 'mp4',
            'title': 'Baby Melo.mp4',
            'duration': 65.0,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://vp.rambler.ru/player/embed.html?widget=Player&id=record::9afb91a9-999a-9d9a-b9f9-b9f99999d51b&referrer=https%3A%2F%2Fexample.com',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = None if 'vp.rambler.ru' in base_url(url) else self._match_id(url)

        if display_id:
            webpage = self._download_webpage(url, display_id)
            preloaded_state = self._search_json(
                r'window\.__PRELOADED_STATE__\s*=', webpage,
                'preloaded state', display_id, transform_source=js_to_json)
            rambler_id = traverse_obj(preloaded_state, (
                'commonData', 'entries', 'entities', ..., 'video',
                ('recordId', ('videoData', 'embed-id')), {str}, any, {require('rambler ID')}))
            referrer = url
        else:
            query = {k: v[0] for k, v in parse_qs(url).items() if v}
            rambler_id = traverse_obj(query, (
                ('id', ('params', {json.loads}, ('id', 'uuid'))), {str}, any, {require('rambler ID')}))
            referrer = traverse_obj(query, (
                ('referrer', ('params', {json.loads}, 'referrer')), {url_or_none}, any), default=url)

        return {
            'display_id': display_id,
            **self._extract_from_rambler_api(rambler_id, referrer),
        }

import json
import urllib.parse

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
            'channel': traverse_obj(player_data, ('result', 'channel', {str})),
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
        r'https?://(?:(?!vp\.)[^/]+\.)?rambler\.ru/\w+/(?P<id>[^/?#]+)',
        r'https?://vp\.rambler\.ru/player(?:/[\d.]+)?/(?P<type>embed|player)\.html',
    ]
    _TESTS = [{
        'url': 'https://auto.rambler.ru/roadaccidents/54816856-v-moskve-mashina-s-diplomaticheskimi-nomerami-vrezalas-v-pushku',
        'info_dict': {
            'id': 'record::356179de-2b91-4e01-9a2c-409dc2f3171d',
            'ext': 'mp4',
            'title': 'Автомобиль с дипномерами врезался в пушку',
            'channel': 'ramblernews',
            'display_id': '54816856-v-moskve-mashina-s-diplomaticheskimi-nomerami-vrezalas-v-pushku',
            'duration': 26,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://news.rambler.ru/moscow_city/55584944-sinoptik-ilin-nastuplenie-meteorologicheskoy-zimy-v-moskve-perenositsya',
        'info_dict': {
            'id': 'record::7d02afbf-4f77-438e-b302-394ac617d5e4',
            'ext': 'mp4',
            'title': 'Метеорологическая зима наступит в Москве на следующей неделе',
            'channel': 'ramblernews',
            'display_id': '55584944-sinoptik-ilin-nastuplenie-meteorologicheskoy-zimy-v-moskve-perenositsya',
            'duration': 77,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://vp.rambler.ru/player/1.151.0/player.html#id=record%3A%3Afdb0a65e-dac4-4e48-abcb-6ec09e02d88f&referrer=https%3A%2F%2Fnews.rambler.ru%2Fcommunity%2F55274681-v-peterburge-muzhchina-otbil-podrostka-u-sluzhby-bezopasnosti-metro%2F',
        'info_dict': {
            'id': 'record::fdb0a65e-dac4-4e48-abcb-6ec09e02d88f',
            'ext': 'mp4',
            'title': 'В Петербурге мужчина отбил подростка у службы безопасности метро',
            'channel': 'ramblernews',
            'duration': 65,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://vp.rambler.ru/player/embed.html?id=record::01a9982f-da18-4e95-b3a1-c5bcf6e112fb',
        'info_dict': {
            'id': 'record::01a9982f-da18-4e95-b3a1-c5bcf6e112fb',
            'ext': 'mp4',
            'title': 'Ученый раскрыл тайну зеленого свечения над Москвой',
            'channel': 'ramblernews',
            'duration': 16,
            'thumbnail': r're:https?://.+\.(?:jpe?g|png)',
        },
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
            if self._match_valid_url(url).group('type') == 'embed':
                query = parse_qs(url)
            else:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment)
            query = {k: v[0] for k, v in query.items() if v}
            rambler_id = traverse_obj(query, ('id', {str}, {require('rambler ID')}))
            referrer = traverse_obj(query, ('referrer', {url_or_none}), default=url)

        return {
            'display_id': display_id,
            **self._extract_from_rambler_api(rambler_id, referrer),
        }

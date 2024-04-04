import functools

from .common import InfoExtractor
from ..utils import str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class AsobiStageIE(InfoExtractor):
    IE_DESC = 'ASOBISTAGE (アソビステージ)'
    _VALID_URL = r'https?://asobistage\.asobistore\.jp/event/(?P<id>(?P<event>\w+)/(?P<type>archive|player)/(?P<slug>\w+))(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://asobistage.asobistore.jp/event/315passionhour_2022summer/archive/frame',
        'info_dict': {
            'id': '315passionhour_2022summer/archive/frame',
            'title': '315プロダクションプレゼンツ 315パッションアワー!!!',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': 'edff52f2',
                'ext': 'mp4',
                'title': '315passion_FRAME_only',
                'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
            },
        }],
    }, {
        'url': 'https://asobistage.asobistore.jp/event/idolmaster_idolworld2023_goods/archive/live',
        'info_dict': {
            'id': 'idolmaster_idolworld2023_goods/archive/live',
            'title': 'md5:378510b6e830129d505885908bd6c576',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '3aef7110',
                'ext': 'mp4',
                'title': 'asobistore_station_1020_serverREC',
                'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
            },
        }],
    }, {
        'url': 'https://asobistage.asobistore.jp/event/sidem_fclive_bpct/archive/premium_hc',
        'playlist_count': 4,
        'info_dict': {
            'id': 'sidem_fclive_bpct/archive/premium_hc',
            'title': '315 Production presents F＠NTASTIC COMBINATION LIVE ～BRAINPOWER!!～/～CONNECTIME!!!!～',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
    }, {
        'url': 'https://asobistage.asobistore.jp/event/ijigenfes_utagassen/player/day1',
        'only_matching': True,
    }]

    _API_HOST = 'https://asobistage-api.asobistore.jp'
    _HEADERS = {}
    _is_logged_in = False

    @functools.cached_property
    def _owned_tickets(self):
        owned_tickets = set()
        if not self._is_logged_in:
            return owned_tickets

        for path, name in [
            ('api/v1/purchase_history/list', 'ticket purchase history'),
            ('api/v1/serialcode/list', 'redemption history'),
        ]:
            response = self._download_json(
                f'{self._API_HOST}/{path}', None, f'Downloading {name}',
                f'Unable to download {name}', expected_status=400)
            if traverse_obj(response, ('payload', 'error_message'), 'error') == 'notlogin':
                self._is_logged_in = False
                break
            owned_tickets.update(
                traverse_obj(response, ('payload', 'value', ..., 'digital_product_id', {str_or_none})))

        return owned_tickets

    def _get_available_channel_id(self, channel):
        channel_id = traverse_obj(channel, ('chennel_vspf_id', {str}))
        if not channel_id:
            return None
        # if rights_type_id == 6, then 'No conditions (no login required - non-members are OK)'
        if traverse_obj(channel, ('viewrights', lambda _, v: v['rights_type_id'] == 6)):
            return channel_id
        available_tickets = traverse_obj(channel, (
            'viewrights', ..., ('tickets', 'serialcodes'), ..., 'digital_product_id', {str_or_none}))
        if not self._owned_tickets.intersection(available_tickets):
            self.report_warning(
                f'You are not a ticketholder for "{channel.get("channel_name") or channel_id}"')
            return None
        return channel_id

    def _real_initialize(self):
        if self._get_cookies(self._API_HOST):
            self._is_logged_in = True
        token = self._download_json(
            f'{self._API_HOST}/api/v1/vspf/token', None, 'Getting token', 'Unable to get token')
        self._HEADERS['Authorization'] = f'Bearer {token}'

    def _real_extract(self, url):
        video_id, event, type_, slug = self._match_valid_url(url).group('id', 'event', 'type', 'slug')
        video_type = {'archive': 'archives', 'player': 'broadcasts'}[type_]
        webpage = self._download_webpage(url, video_id)
        event_data = traverse_obj(
            self._search_nextjs_data(webpage, video_id, default='{}'),
            ('props', 'pageProps', 'eventCMSData', {
                'title': ('event_name', {str}),
                'thumbnail': ('event_thumbnail_image', {url_or_none}),
            }))

        available_channels = traverse_obj(self._download_json(
            f'https://asobistage.asobistore.jp/cdn/v101/events/{event}/{video_type}.json',
            video_id, 'Getting channel list', 'Unable to get channel list'), (
            video_type, lambda _, v: v['broadcast_slug'] == slug,
            'channels', lambda _, v: v['chennel_vspf_id'] != '00000'))

        entries = []
        for channel_id in traverse_obj(available_channels, (..., {self._get_available_channel_id})):
            if video_type == 'archives':
                channel_json = self._download_json(
                    f'https://survapi.channel.or.jp/proxy/v1/contents/{channel_id}/get_by_cuid', channel_id,
                    'Getting archive channel info', 'Unable to get archive channel info', fatal=False,
                    headers=self._HEADERS)
                channel_data = traverse_obj(channel_json, ('ex_content', {
                    'm3u8_url': 'streaming_url',
                    'title': 'title',
                    'thumbnail': ('thumbnail', 'url'),
                }))
            else:  # video_type == 'broadcasts'
                channel_json = self._download_json(
                    f'https://survapi.channel.or.jp/ex/events/{channel_id}', channel_id,
                    'Getting live channel info', 'Unable to get live channel info', fatal=False,
                    headers=self._HEADERS, query={'embed': 'channel'})
                channel_data = traverse_obj(channel_json, ('data', {
                    'm3u8_url': ('Channel', 'Custom_live_url'),
                    'title': 'Name',
                    'thumbnail': 'Poster_url',
                }))

            entries.append({
                'id': channel_id,
                'title': channel_data.get('title'),
                'formats': self._extract_m3u8_formats(channel_data.get('m3u8_url'), channel_id, fatal=False),
                'is_live': video_type == 'broadcasts',
                'thumbnail': url_or_none(channel_data.get('thumbnail')),
            })

        if not self._is_logged_in and not entries:
            self.raise_login_required()

        return self.playlist_result(entries, video_id, **event_data)

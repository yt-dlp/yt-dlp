from .common import InfoExtractor
from ..utils import ExtractorError, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class AsobiStageIE(InfoExtractor):
    IE_DESC = 'ASOBISTAGE (アソビステージ)'
    _VALID_URL = r'https?://asobistage\.asobistore\.jp/event/(?P<id>\w+/(?P<type>\w+)/\w+)(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://asobistage.asobistore.jp/event/315passionhour_2022summer/archive/frame',
        'info_dict': {
            'id': '315passionhour_2022summer/archive/frame/edff52f2',
            'title': '315passion_FRAME_only',
            'live_status': 'was_live',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://asobistage.asobistore.jp/event/idolmaster_idolworld2023_goods/archive/live',
        'info_dict': {
            'id': 'idolmaster_idolworld2023_goods/archive/live/3aef7110',
            'title': 'asobistore_station_1020_serverREC',
            'live_status': 'was_live',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://asobistage.asobistore.jp/event/ijigenfes_utagassen/player/day1',
        'only_matching': True,
    }]

    _TOKEN = ''

    def _check_login(self, video_id):
        check_login_json = self._download_json(
            'https://asobistage-api.asobistore.jp/api/v1/check_login', video_id, expected_status=(400),
            note='Checking login status', errnote='Unable to check login status')
        error = traverse_obj(check_login_json, ('payload', 'error_message'), ('error'), get_all=False)

        if not error:
            return
        elif error == 'notlogin':
            self.raise_login_required()
        else:
            raise ExtractorError(f'Unknown error: {error!r}')

    def _get_owned_tickets(self, video_id):
        for url, name in [
            ('https://asobistage-api.asobistore.jp/api/v1/purchase_history/list', 'ticket purchase history'),
            ('https://asobistage-api.asobistore.jp/api/v1/serialcode/list', 'redemption history'),
        ]:
            yield from traverse_obj(self._download_json(
                url, video_id, note=f'Downloading {name}', errnote=f'Unable to download {name}'),
                ('payload', 'value', ..., 'digital_product_id', {str}))

    def _real_initialize(self):
        self._TOKEN = self._download_json(
            'https://asobistage-api.asobistore.jp/api/v1/vspf/token', None,
            note='Getting token', errnote='Unable to get token')

    def _real_extract(self, url):
        video_id, video_type_name = self._match_valid_url(url).group('id', 'type')
        self._check_login(video_id)

        webpage = self._download_webpage(url, video_id)

        video_type_id = {
            'archive': 'archives',
            'player': 'broadcasts',
        }.get(video_type_name)
        if not video_type_id:
            raise ExtractorError('Unknown video type')

        event_data = self._search_nextjs_data(webpage, video_id)
        event_id = traverse_obj(event_data, ('query', 'event', {str}))
        event_slug = traverse_obj(event_data, ('query', 'player_slug', {str}))
        event_title = traverse_obj(event_data, ('props', 'pageProps', 'eventCMSData', 'event_name', {str}))
        if not all((event_id, event_slug, event_title)):
            raise ExtractorError('Unable to get required event data')

        channels_json = self._download_json(
            f'https://asobistage.asobistore.jp/cdn/v101/events/{event_id}/{video_type_id}.json', video_id,
            fatal=False, note='Getting channel list', errnote='Unable to get channel list')
        available_channels = traverse_obj(channels_json, (
            video_type_id, lambda _, v: v['broadcast_slug'] == event_slug, 'channels',
            lambda _, v: v['chennel_vspf_id'] != '00000', {dict}))

        owned_tickets = set(self._get_owned_tickets(video_id))
        available_tickets = traverse_obj(
            available_channels, (..., 'viewrights', ..., 'tickets', ..., 'digital_product_id', {str_or_none}))
        if not owned_tickets.intersection(available_tickets):
            raise ExtractorError('No valid ticket for this event', expected=True)

        entries = []
        for channel_id in traverse_obj(available_channels, (..., 'chennel_vspf_id', {str})):
            channel_data = {}

            if video_type_name == 'archive':
                channel_json = self._download_json(
                    f'https://survapi.channel.or.jp/proxy/v1/contents/{channel_id}/get_by_cuid', f'{video_id}/{channel_id}',
                    note='Getting archive channel info', errnote='Unable to get archive channel info',
                    headers={'Authorization': f'Bearer {self._TOKEN}'})
                channel_data = traverse_obj(channel_json, ('ex_content', {
                    'm3u8_url': 'streaming_url',
                    'title': 'title',
                    'thumbnail': ('thumbnail', 'url'),
                }))
            elif video_type_name == 'player':
                channel_json = self._download_json(
                    f'https://survapi.channel.or.jp/ex/events/{channel_id}', f'{video_id}/{channel_id}',
                    note='Getting live channel info', errnote='Unable to get live channel info',
                    headers={'Authorization': f'Bearer {self._TOKEN}'}, query={'embed': 'channel'})
                channel_data = traverse_obj(channel_json, ('data', {
                    'm3u8_url': ('Channel', 'Custom_live_url'),
                    'title': 'Name',
                    'thumbnail': 'Poster_url',
                }))

            m3u8_url = channel_data.get('m3u8_url')
            if not m3u8_url:
                self.report_warning('Unable to get channel m3u8 url', video_id)
                continue

            entries.append({
                'id': channel_id,
                'title': channel_data.get('title'),
                'formats': self._extract_m3u8_formats(m3u8_url, video_id=f'{video_id}/{channel_id}', fatal=False),
                'is_live': video_type_id == 'broadcasts',
                'thumbnail': channel_data.get('thumbnail'),
            })

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': event_title,
            'entries': entries,
            'thumbnail': traverse_obj(
                event_data, ('props', 'pageProps', 'eventCMSData', 'event_thumbnail_image', {url_or_none})),
        }

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    merge_dicts,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class AsobiChannelBaseIE(InfoExtractor):
    _MICROCMS_HEADER = {'X-MICROCMS-API-KEY': 'qRaKehul9AHU8KtL0dnq1OCLKnFec6yrbcz3'}

    def _extract_info(self, metadata):
        return traverse_obj(metadata, {
            'id': ('id', {str}),
            'title': ('title', {str}),
            'description': ('body', {clean_html}),
            'thumbnail': ('contents', 'video_thumb', 'url', {url_or_none}),
            'timestamp': ('publishedAt', {parse_iso8601}),
            'modified_timestamp': ('updatedAt', {parse_iso8601}),
            'channel': ('channel', 'name', {str}),
            'channel_id': ('channel', 'id', {str}),
        })


class AsobiChannelIE(AsobiChannelBaseIE):
    IE_NAME = 'asobichannel'
    IE_DESC = 'ASOBI CHANNEL'

    _VALID_URL = r'https?://asobichannel\.asobistore\.jp/watch/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://asobichannel.asobistore.jp/watch/1ypp48qd32p',
        'md5': '39df74e872afe032c4eb27b89144fc92',
        'info_dict': {
            'id': '1ypp48qd32p',
            'ext': 'mp4',
            'title': 'アイドルマスター ミリオンライブ！ 765プロch 原っぱ通信 #1',
            'description': 'md5:b930bd2199c9b2fd75951ce4aaa7efd2',
            'thumbnail': 'https://images.microcms-assets.io/assets/d2420de4b9194e11beb164f99edb1f95/a8e6f84119f54eb9ab4ce16729239905/%E3%82%B5%E3%83%A0%E3%83%8D%20(1).png',
            'timestamp': 1697098247,
            'upload_date': '20231012',
            'modified_timestamp': 1698381162,
            'modified_date': '20231027',
            'channel': 'アイドルマスター',
            'channel_id': 'idolmaster',
        },
    }, {
        'url': 'https://asobichannel.asobistore.jp/watch/redigiwnjzqj',
        'md5': '229fa8fb5c591c75ce8c37a497f113f6',
        'info_dict': {
            'id': 'redigiwnjzqj',
            'ext': 'mp4',
            'title': '【おまけ放送】アイドルマスター ミリオンライブ！ 765プロch 原っぱ通信 #1',
            'description': 'md5:7d9cd35fb54425a6967822bd564ea2d9',
            'thumbnail': 'https://images.microcms-assets.io/assets/d2420de4b9194e11beb164f99edb1f95/20e5c1d6184242eebc2512a5dec59bf0/P1_%E5%8E%9F%E3%81%A3%E3%81%B1%E3%82%B5%E3%83%A0%E3%83%8D.png',
            'modified_timestamp': 1697797125,
            'modified_date': '20231020',
            'timestamp': 1697261769,
            'upload_date': '20231014',
            'channel': 'アイドルマスター',
            'channel_id': 'idolmaster',
        },
    }]

    _survapi_header = None

    def _real_initialize(self):
        token = self._download_json(
            'https://asobichannel-api.asobistore.jp/api/v1/vspf/token', None,
            note='Retrieving API token')
        self._survapi_header = {'Authorization': f'Bearer {token}'}

    def _process_vod(self, video_id, metadata):
        content_id = metadata['contents']['video_id']

        vod_data = self._download_json(
            f'https://survapi.channel.or.jp/proxy/v1/contents/{content_id}/get_by_cuid', video_id,
            headers=self._survapi_header, note='Downloading vod data')

        return {
            'formats': self._extract_m3u8_formats(vod_data['ex_content']['streaming_url'], video_id),
        }

    def _process_live(self, video_id, metadata):
        content_id = metadata['contents']['video_id']
        event_data = self._download_json(
            f'https://survapi.channel.or.jp/ex/events/{content_id}?embed=channel', video_id,
            headers=self._survapi_header, note='Downloading event data')

        player_type = traverse_obj(event_data, ('data', 'Player_type', {str}))
        if player_type == 'poster':
            self.raise_no_formats('Live event has not yet started', expected=True)
            live_status = 'is_upcoming'
            formats = []
        elif player_type == 'player':
            live_status = 'is_live'
            formats = self._extract_m3u8_formats(
                event_data['data']['Channel']['Custom_live_url'], video_id, live=True)
        else:
            raise ExtractorError('Unsupported player type {player_type!r}')

        return {
            'release_timestamp': traverse_obj(metadata, ('period', 'start', {parse_iso8601})),
            'live_status': live_status,
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            f'https://channel.microcms.io/api/v1/media/{video_id}', video_id,
            headers=self._MICROCMS_HEADER)

        info = self._extract_info(metadata)

        video_type = traverse_obj(metadata, ('contents', 'video_type', 0, {str}))
        if video_type == 'VOD':
            return merge_dicts(info, self._process_vod(video_id, metadata))
        if video_type == 'LIVE':
            return merge_dicts(info, self._process_live(video_id, metadata))

        raise ExtractorError(f'Unexpected video type {video_type!r}')


class AsobiChannelTagURLIE(AsobiChannelBaseIE):
    IE_NAME = 'asobichannel:tag'
    IE_DESC = 'ASOBI CHANNEL'

    _VALID_URL = r'https?://asobichannel\.asobistore\.jp/tag/(?P<id>[a-z0-9-_]+)'
    _TESTS = [{
        'url': 'https://asobichannel.asobistore.jp/tag/bjhh-nbcja',
        'info_dict': {
            'id': 'bjhh-nbcja',
            'title': 'アイドルマスター ミリオンライブ！ 765プロch 原っぱ通信',
        },
        'playlist_mincount': 16,
    }, {
        'url': 'https://asobichannel.asobistore.jp/tag/hvm5qw3c6od',
        'info_dict': {
            'id': 'hvm5qw3c6od',
            'title': 'アイマスMOIW2023ラジオ',
        },
        'playlist_mincount': 13,
    }]

    def _real_extract(self, url):
        tag_id = self._match_id(url)
        webpage = self._download_webpage(url, tag_id)
        title = traverse_obj(self._search_nextjs_data(
            webpage, tag_id, fatal=False), ('props', 'pageProps', 'data', 'name', {str}))

        media = self._download_json(
            f'https://channel.microcms.io/api/v1/media?limit=999&filters=(tag[contains]{tag_id})',
            tag_id, headers=self._MICROCMS_HEADER)

        def entries():
            for metadata in traverse_obj(media, ('contents', lambda _, v: v['id'])):
                yield {
                    '_type': 'url',
                    'url': f'https://asobichannel.asobistore.jp/watch/{metadata["id"]}',
                    'ie_key': AsobiChannelIE.ie_key(),
                    **self._extract_info(metadata),
                }

        return self.playlist_result(entries(), tag_id, title)

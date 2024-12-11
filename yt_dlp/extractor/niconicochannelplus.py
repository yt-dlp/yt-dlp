import functools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    filter_dict,
    int_or_none,
    parse_qs,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class NiconicoChannelPlusBaseIE(InfoExtractor):
    _SITE_SETTINGS = {}
    _DOMAIN_SITE_ID = {}
    _CHANNEL_NAMES = {}
    _CHANNEL_AGE_LIMIT = {}

    def _get_settings(self, url, video_id=None):
        base_url = urljoin(url, '/')
        if base_url not in self._SITE_SETTINGS:
            self._SITE_SETTINGS[base_url] = self._download_json(
                urljoin(base_url, '/site/settings.json'), video_id, note='Downloading site settings')
        if self._SITE_SETTINGS[base_url].get('platform_id') not in ['CHPL', 'SHTA', 'JOQR', 'TKFM']:
            self.report_warning(f'Unknown platform type: {self._SITE_SETTINGS[base_url].get("platform_id")}')
        return self._SITE_SETTINGS[base_url]

    def _download_api_json(self, site_url, path, video_id, headers={}, **kwargs):
        path = f'/{path}' if path[0] != '/' else path
        settings = self._get_settings(site_url, video_id)
        headers = {
            'origin': urljoin(site_url, '/').strip('/'),
            'referer': urljoin(site_url, '/'),
            'fc_site_id': settings['fanclub_site_id'],
            'fc_use_device': 'null',
            **headers,
        }
        return self._download_json(f'{settings["api_base_url"]}{path}', video_id, headers=headers, **kwargs)

    def _get_fanclub_site_id(self, url):
        settings = self._get_settings(url)
        if settings['platform_id'] == 'SHTA':
            return str(settings['fanclub_site_id'])
        else:
            parsed = urllib.parse.urlparse(url)
            # parsed.path starts with '/', so index 0 is empty string
            domain_url = f'{parsed.scheme}://{parsed.netloc}/{parsed.path.split("/")[1].lower()}'
            if domain_url not in self._DOMAIN_SITE_ID:
                self._DOMAIN_SITE_ID[domain_url] = str(self._download_api_json(
                    url, '/content_providers/channel_domain', domain_url,
                    query={'current_site_domain': domain_url})['data']['content_providers']['id'])
            return self._DOMAIN_SITE_ID[domain_url]

    def _get_channel_id(self, url):
        parsed = urllib.parse.urlparse(url)
        if self._get_settings(url)['platform_id'] == 'SHTA':
            return parsed.hostname.replace('.', '_')
        elif self._get_settings(url)['platform_id'] == 'CHPL':
            return parsed.path.split('/')[1]
        else:
            return f'{parsed.hostname.replace(".", "_")}_{parsed.path.split("/")[1]}'

    def _get_channel_url(self, url):
        parsed = urllib.parse.urlparse(url)
        if self._get_settings(url)['platform_id'] == 'SHTA':
            return f'{parsed.scheme}://{parsed.netloc}'
        else:
            return f'{parsed.scheme}://{parsed.netloc}/{parsed.path.split("/")[1]}'

    def _get_channel_name(self, url):
        fanclub_site_id = self._get_fanclub_site_id(url)
        if fanclub_site_id not in self._CHANNEL_NAMES:
            self._CHANNEL_NAMES[fanclub_site_id] = traverse_obj(self._download_api_json(
                url, f'/fanclub_sites/{fanclub_site_id}/page_base_info', video_id=str(fanclub_site_id),
                note='Downloading channel name', fatal=False,
            ), ('data', 'fanclub_site', 'fanclub_site_name', {str}))
        return self._CHANNEL_NAMES[fanclub_site_id]

    def _get_age_limit(self, url):
        fanclub_site_id = self._get_fanclub_site_id(url)
        if fanclub_site_id not in self._CHANNEL_AGE_LIMIT:
            self._CHANNEL_AGE_LIMIT[fanclub_site_id] = traverse_obj(self._download_api_json(
                url, f'/fanclub_sites/{fanclub_site_id}/user_info', video_id=str(fanclub_site_id), data=b'',
                note='Downloading channel age limit', fatal=False,
            ), ('data', 'fanclub_site', 'content_provider', 'age_limit', {int}))
        return self._CHANNEL_AGE_LIMIT[fanclub_site_id]

    def _is_channel_plus_webpage(self, webpage):
        return 'GTM-KXT7G5G' in webpage or 'NicoGoogleTagManagerDataLayer' in webpage


class NiconicoChannelPlusIE(NiconicoChannelPlusBaseIE):
    IE_NAME = 'NiconicoChannelPlus'
    IE_DESC = 'ニコニコチャンネルプラス'
    _VALID_URL = r'https?://nicochannel\.jp/(?P<channel>[\w.-]+)/(?:video|live)/(?P<code>sm\w+)'
    _TESTS = [{
        'url': 'https://nicochannel.jp/renge/video/smjHSEPCxd4ohY4zg8iyGKnX',
        'info_dict': {
            'id': 'smjHSEPCxd4ohY4zg8iyGKnX',
            'title': '【両耳舐め】あまいちゃトロらぶ両耳舐め【本多ぽこちゃんと耳舐めASMR②】',
            'ext': 'mp4',
            'channel': '狐月れんげのあまとろASMR＋',
            'channel_id': 'renge',
            'channel_url': 'https://nicochannel.jp/renge',
            'live_status': 'not_live',
            'thumbnail': 'https://nicochannel.jp/public_html/contents/video_pages/35690/thumbnail_path?time=1722439868',
            'description': 'お耳が癒されて疲れもヌケる♡\n本多ぽこちゃんとの2024年7月24日の耳舐めコラボアーカイブです。',
            'timestamp': 1722439866,
            'duration': 2698,
            'comment_count': int,
            'view_count': int,
            'tags': list,
            'upload_date': '20240731',
        },
    }, {
        'url': 'https://nicochannel.jp/kaorin/video/smsDd8EdFLcVZk9yyAhD6H7H',
        'info_dict': {
            'id': 'smsDd8EdFLcVZk9yyAhD6H7H',
            'title': '前田佳織里はニコ生がしたい！',
            'ext': 'mp4',
            'channel': '前田佳織里の世界攻略計画',
            'channel_id': 'kaorin',
            'channel_url': 'https://nicochannel.jp/kaorin',
            'live_status': 'not_live',
            'thumbnail': 'https://nicochannel.jp/public_html/contents/video_pages/74/thumbnail_path',
            'description': '２０２１年１１月に放送された\n「前田佳織里はニコ生がしたい！」アーカイブになります。',
            'timestamp': 1641360276,
            'duration': 4097,
            'comment_count': int,
            'view_count': int,
            'tags': [],
            'upload_date': '20220105',
        },
        'skip': 'subscriber only',
    }, {
        # age limited video; test purpose channel.
        'url': 'https://nicochannel.jp/testman/video/smDXbcrtyPNxLx9jc4BW69Ve',
        'info_dict': {
            'id': 'smDXbcrtyPNxLx9jc4BW69Ve',
            'title': 'test oshiro',
            'ext': 'mp4',
            'channel': '本番チャンネルプラステストマン',
            'channel_id': 'testman',
            'channel_url': 'https://nicochannel.jp/testman',
            'age_limit': 18,
            'live_status': 'was_live',
            'timestamp': 1666344616,
            'duration': 86465,
            'comment_count': int,
            'view_count': int,
            'tags': [],
            'upload_date': '20221021',
        },
        'skip': 'subscriber only',
    }]

    def _extract_from_webpage(self, url, webpage):
        if self._match_video_id(url) and self._is_channel_plus_webpage(webpage):
            yield self._real_extract(url)

    def _match_video_id(self, url):
        return re.search(r'/(?:video|audio|live)/(?P<id>sm\w+)', urllib.parse.urlparse(url).path)

    def _real_extract(self, url):
        video_id = self._match_video_id(url).group('id')

        video_info = self._download_api_json(url, f'/video_pages/{video_id}', video_id,
                                             note='Downloading video info')['data']['video_page']

        live_status, session_payload, timestamp = self._parse_live_status(video_id, video_info)
        session_id = self._download_api_json(
            url, f'/video_pages/{video_id}/session_ids', video_id, data=json.dumps(session_payload).encode(),
            headers={'content-type': 'application/json'}, note='Downloading video session')['data']['session_id']
        formats = self._extract_m3u8_formats(
            video_info['video_stream']['authenticated_url'].format(session_id=session_id), video_id)

        return {
            'id': video_id,
            'formats': formats,
            '_format_sort_fields': ('tbr', 'vcodec', 'acodec'),
            'channel': self._get_channel_name(url),
            'channel_id': self._get_channel_id(url),
            'channel_url': self._get_channel_url(url),
            'age_limit': self._get_age_limit(url),
            'live_status': live_status,
            'release_timestamp': timestamp,
            **traverse_obj(video_info, {
                'title': ('title', {str}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'description': ('description', {str}),
                'timestamp': ('released_at', {unified_timestamp}),
                'duration': ('active_video_filename', 'length', {int_or_none}),
                'comment_count': ('video_aggregate_info', 'number_of_comments', {int_or_none}),
                'view_count': ('video_aggregate_info', 'total_views', {int_or_none}),
                'tags': ('video_tags', ..., 'tag', {str}),
            }),
            '__post_extractor': self.extract_comments(
                url=url,
                comment_group_id=traverse_obj(video_info, ('video_comment_setting', 'comment_group_id'))),
        }

    def _get_comments(self, url, comment_group_id):
        if not comment_group_id:
            return None
        video_id = self._parse_video_id(url)

        comment_access_token = self._download_api_json(
            url, f'video_pages/{video_id}/comments_user_token', f'{video_id}/comments',
            note='Getting comment token', errnote='Unable to get comment token',
        )['data']['access_token']

        comment_list = self._download_json(
            'https://comm-api.sheeta.com/messages.history', video_id=f'{video_id}/comments',
            note='Fetching comments', errnote='Unable to fetch comments',
            headers={'Content-Type': 'application/json'},
            query={
                'sort_direction': 'asc',
                'limit': int_or_none(self._configuration_arg('max_comments', [''])[0]) or 120,
            },
            data=json.dumps({
                'token': comment_access_token,
                'group_id': comment_group_id,
            }).encode('ascii'))

        for comment in traverse_obj(comment_list, ...):
            yield traverse_obj(comment, {
                'author': ('nickname', {str}),
                'author_id': ('sender_id', {str_or_none}),
                'id': ('id', {str_or_none}),
                'text': ('message', {str}),
                'timestamp': (('updated_at', 'sent_at', 'created_at'), {unified_timestamp}),
                'author_is_uploader': ('sender_id', {lambda x: x == '-1'}),
            }, get_all=False)

    def _parse_live_status(self, video_id, video_info):
        video_type = video_info.get('type')
        live_finished_at = video_info.get('live_finished_at')
        release_timestamp_str = video_info.get('live_scheduled_start_at')

        payload = {}
        if video_type == 'vod':
            if live_finished_at:
                live_status = 'was_live'
            else:
                live_status = 'not_live'
        elif video_type == 'live':
            if not video_info.get('live_started_at'):
                live_status = 'is_upcoming'
                if release_timestamp_str:
                    msg = f'This live event will begin at {release_timestamp_str} UTC'
                else:
                    msg = 'This event has not started yet'
                self.raise_no_formats(msg, expected=True, video_id=video_id)

            if not live_finished_at:
                live_status = 'is_live'
            else:
                live_status = 'was_live'
                payload = {'broadcast_type': 'dvr'}

                video_allow_dvr_flg = traverse_obj(video_info, ('video', 'allow_dvr_flg'))
                video_convert_to_vod_flg = traverse_obj(video_info, ('video', 'convert_to_vod_flg'))

                self.write_debug(f'allow_dvr_flg = {video_allow_dvr_flg}, convert_to_vod_flg = {video_convert_to_vod_flg}.')

                if not (video_allow_dvr_flg and video_convert_to_vod_flg):
                    raise ExtractorError(
                        'Live was ended, there is no video for download.', video_id=video_id, expected=True)
        else:
            raise ExtractorError(f'Unknown type: {video_type}', video_id=video_id, expected=False)

        self.write_debug(f'{video_id}: video_type={video_type}, live_status={live_status}')

        return live_status, payload, unified_timestamp(release_timestamp_str)


class NiconicoChannelPlusChannelBaseIE(NiconicoChannelPlusBaseIE):
    _PAGE_SIZE = 12

    def _fetch_paged_channel_video_list(self, site_url, path, query, video_id, page):
        response = self._download_api_json(
            site_url, path, video_id, query={
                **query,
                'page': (page + 1),
                'per_page': self._PAGE_SIZE,
            },
            note=f'Getting channel info (page {page + 1})',
            errnote=f'Unable to get channel info (page {page + 1})')

        for content_code in traverse_obj(response, ('data', 'video_pages', 'list', ..., 'content_code')):
            # "video/{content_code}" works for both VOD and live, but "live/{content_code}" doesn't work for VOD
            yield self.url_result(f'{self._get_channel_url(site_url)}/video/{content_code}')


class NiconicoChannelPlusChannelVideosIE(NiconicoChannelPlusChannelBaseIE):
    IE_NAME = 'NiconicoChannelPlus:channel:videos'
    IE_DESC = 'ニコニコチャンネルプラス - チャンネル - 動画リスト. nicochannel.jp/channel/videos'
    _VALID_URL = r'https?://nicochannel\.jp/(?P<id>[a-z\d\._-]+)/videos(?:\?.*)?'
    _TESTS = [{
        # query: None
        'url': 'https://nicochannel.jp/testman/videos',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: None
        'url': 'https://nicochannel.jp/testtarou/videos',
        'info_dict': {
            'id': 'testtarou-videos',
            'title': 'チャンネルプラステスト太郎-videos',
        },
        'playlist_mincount': 2,
    }, {
        # query: None
        'url': 'https://nicochannel.jp/testjirou/videos',
        'info_dict': {
            'id': 'testjirou-videos',
            'title': 'チャンネルプラステスト"二郎21-videos',
        },
        'playlist_mincount': 12,
    }, {
        # query: tag
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }, {
        # query: vodType
        'url': 'https://nicochannel.jp/testman/videos?vodType=1',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: sort
        'url': 'https://nicochannel.jp/testman/videos?sort=-released_at',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: tag, vodType
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8&vodType=1',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }, {
        # query: tag, sort
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8&sort=-released_at',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }, {
        # query: vodType, sort
        'url': 'https://nicochannel.jp/testman/videos?vodType=1&sort=-released_at',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: tag, vodType, sort
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8&vodType=1&sort=-released_at',
        'info_dict': {
            'id': 'testman-videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }]

    def _extract_from_webpage(self, url, webpage):
        if re.search(r'/videos/?(?:[\?#]|$)', url) and self._is_channel_plus_webpage(webpage):
            yield self._real_extract(url)

    def _real_extract(self, url):
        """
        API parameters:
            sort:
                -released_at         公開日が新しい順 (newest to oldest)
                 released_at         公開日が古い順 (oldest to newest)
                -number_of_vod_views 再生数が多い順 (most play count)
                 number_of_vod_views コメントが多い順 (most comments)
            vod_type (is "vodType" in "url"):
                0 すべて (all)
                1 会員限定 (members only)
                2 一部無料 (partially free)
                3 レンタル (rental)
                4 生放送アーカイブ (live archives)
                5 アップロード動画 (uploaded videos)
        """

        channel_id = self._get_channel_id(url)
        qs = parse_qs(url)

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._fetch_paged_channel_video_list,
                    url,
                    f'fanclub_sites/{self._get_fanclub_site_id(url)}/video_pages',
                    filter_dict({
                        'tag': traverse_obj(qs, ('tag', 0)),
                        'sort': traverse_obj(qs, ('sort', 0), default='-released_at'),
                        'vod_type': traverse_obj(qs, ('vodType', 0), default='0'),
                    }),
                    f'{channel_id}/videos'),
                self._PAGE_SIZE),
            playlist_id=f'{channel_id}-videos', playlist_title=f'{self._get_channel_name(url)}-videos')


class NiconicoChannelPlusChannelLivesIE(NiconicoChannelPlusChannelBaseIE):
    IE_NAME = 'NiconicoChannelPlus:channel:lives'
    IE_DESC = 'ニコニコチャンネルプラス - チャンネル - ライブリスト. nicochannel.jp/channel/lives'
    _VALID_URL = r'https?://nicochannel\.jp/(?P<id>[a-z\d\._-]+)/lives'
    _TESTS = [{
        'url': 'https://nicochannel.jp/testman/lives',
        'info_dict': {
            'id': 'testman-lives',
            'title': '本番チャンネルプラステストマン-lives',
        },
        'playlist_mincount': 18,
    }, {
        'url': 'https://nicochannel.jp/testtarou/lives',
        'info_dict': {
            'id': 'testtarou-lives',
            'title': 'チャンネルプラステスト太郎-lives',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://nicochannel.jp/testjirou/lives',
        'info_dict': {
            'id': 'testjirou-lives',
            'title': 'チャンネルプラステスト二郎-lives',
        },
        'playlist_mincount': 6,
    }]

    def _extract_from_webpage(self, url, webpage):
        if re.search(r'/lives/?(?:[\?#]|$)', url) and self._is_channel_plus_webpage(webpage):
            yield self._real_extract(url)

    def _real_extract(self, url):
        """
        API parameters:
            live_type:
                1 放送中 (on air)
                2 放送予定 (scheduled live streams, oldest to newest)
                3 過去の放送 - すべて (all ended live streams, newest to oldest)
                4 過去の放送 - 生放送アーカイブ (all archives for live streams, oldest to newest)
            We use "4" instead of "3" because some recently ended live streams could not be downloaded.
        """

        channel_id = self._get_channel_id(url)

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._fetch_paged_channel_video_list,
                    url,
                    f'fanclub_sites/{self._get_fanclub_site_id(url)}/live_pages',
                    {'live_type': 4},
                    f'{channel_id}/lives'),
                self._PAGE_SIZE),
            playlist_id=f'{channel_id}-lives', playlist_title=f'{self._get_channel_name(url)}-lives')

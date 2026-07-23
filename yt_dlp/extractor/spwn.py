import datetime as dt
import json
import time
import urllib.parse

from .wrestleuniverse import WrestleUniverseBaseIE
from ..cookies import LenientSimpleCookie
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    parse_qs,
    str_or_none,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import (
    require,
    traverse_obj,
    unpack,
)


class SPWNBaseIE(WrestleUniverseBaseIE):
    _BASE_URL = 'https://spwn.jp'
    _LOGIN_HEADERS = {'Content-Type': 'application/json'}
    _LOGIN_HINT = (
        'Use --username refresh --password <refreshToken>, --username and --password, '
        '--netrc-cmd, or --netrc (spwn) to provide account credentials')
    _LOGIN_QUERY = {'key': 'AIzaSyC-RDWv-QnYNWsJ6geLPpFYArlo2uPWCpA'}
    _NETRC_MACHINE = 'spwn'

    @WrestleUniverseBaseIE._TOKEN.getter
    def _TOKEN(self):
        if not self._REAL_TOKEN or self._TOKEN_EXPIRY <= int(time.time()):
            if not self._REFRESH_TOKEN:
                self.raise_login_required(
                    f'No refreshToken provided. {self._LOGIN_HINT}', method=None)
            self._refresh_token()
        return self._REAL_TOKEN

    def _perform_login(self, username, password):
        if username.lower() == 'refresh':
            self._REFRESH_TOKEN = password
            return self._refresh_token()
        return super()._perform_login(username, password)

    def _call_api(self, path, item_id, note):
        url = f'https://firestore.googleapis.com/v1/projects/spwn-balus/databases/(default)/documents/{path}'
        firestore_data = self._download_json(
            url, item_id, f'Downloading {note}', fatal=False)

        return traverse_obj(firestore_data, ('fields', {dict}), default={})

    def _extract_formats(self, content_data, video_id, crew=False):
        if crew:
            key = 'streamingSource'
            content_type = traverse_obj(content_data, ('type', {str}, filter))
            playback_data = traverse_obj(content_data, ('details', {dict}))
        else:
            key = video_id
            playback_data = traverse_obj(content_data, ('cookies', {dict}))

        if not crew or content_type == 'streaming':
            default = traverse_obj(playback_data, (key, 'default', {dict}))
            cookies = traverse_obj(default, ('cookie', {dict}))
            m3u8_url = traverse_obj(default, (
                'url', {url_or_none}, {require('m3u8 URL')}))
        elif content_type == 'video':
            cookies = LenientSimpleCookie()
            for cookie_header in traverse_obj(playback_data, (
                'signedCookies', ..., {str},
            )):
                cookies.load(cookie_header)
            m3u8_url = traverse_obj(playback_data, (
                'videoURL', {url_or_none}, {require('m3u8 URL')}))
        else:
            raise ExtractorError(f'Unsupported content type: {content_type}')

        key_pair_id = traverse_obj(cookies, (
            'CloudFront-Key-Pair-Id', (None, 'value'),
            {str}, any, {require('CloudFront Key-Pair-Id')}))
        policy = traverse_obj(cookies, (
            'CloudFront-Policy', (None, 'value'),
            {str}, any, {require('CloudFront Policy')}))
        signature = traverse_obj(cookies, (
            'CloudFront-Signature', (None, 'value'),
            {str}, any, {require('CloudFront Signature')}))

        auth_query = {
            'Key-Pair-Id': key_pair_id,
            'Policy': policy,
            'Signature': signature,
        }
        auth_query_string = urllib.parse.urlencode(auth_query)

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4', query=auth_query)
        for fmt in formats:
            fmt.update({
                'extra_param_to_segment_url': auth_query_string,
                'url': update_url_query(fmt['url'], auth_query),
            })

        return formats


class SPWNIE(SPWNBaseIE):
    _VALID_URL = r'https?://spwn\.jp/events/(?P<id>[^/?#]+)(/streaming)?'
    _TESTS = [{
        'url': 'https://spwn.jp/events/181217-tubeout-vol1/streaming?vid=Vi181217-tubeout-vol1C1v1',
        'info_dict': {
            'id': 'Vi181217-tubeout-vol1C1v1',
            'ext': 'mp4',
            'title': 'アーカイブ配信チケット',
            'categories': 'count:1',
            'description': 'md5:fa2f5419b00ef1bb294d8f8f11e66a37',
            'release_date': '20181217',
            'release_timestamp': 1545039000,
            'series': 'TUBEOUT! Vol.1 〜ときのそら・銀河アリス リアルタイムARライブ〜',
            'series_id': '181217-tubeout-vol1',
            'thumbnail': r're:https?://.+',
            'timestamp': 1545042600,
            'upload_date': '20181217',
        },
        'skip': 'Paid only',
    }, {
        'url': 'https://spwn.jp/events/evt_wG62Svb4HkCQkK3QwDqI',
        'info_dict': {
            'id': 'evt_wG62Svb4HkCQkK3QwDqI',
            'title': '劇場版「ポールプリンセス!!」【劇場版アニメ本編配信】',
        },
        'playlist_count': 2,
        'skip': 'Paid only',
    }]

    def _real_extract(self, url):
        event_id = self._match_id(url)
        content_data = self._download_json(
            'https://us-central1-spwn-balus.cloudfunctions.net/getStreamingKeyV2/',
            event_id, headers={
                'Authorization': f'Bearer {self._TOKEN}',
                'Content-Type': 'application/json',
                'Origin': self._BASE_URL,
            }, data=json.dumps({'eid': event_id}).encode())
        if traverse_obj(content_data, ('isError', {bool})):
            err_msg = traverse_obj(content_data, ('msg', {clean_html}, filter))

            raise ExtractorError(
                err_msg or 'API returned an error response', expected=bool(err_msg))

        event_data = self._call_api(f'events/{event_id}', event_id, 'event info')
        event_title = traverse_obj(event_data, ('title', 'stringValue', {clean_html}, filter))

        video_id = traverse_obj(parse_qs(url), ('vid', -1, {str}, filter))
        if not video_id:
            entries = [self.url_result(
                update_url_query(f'{self._BASE_URL}/events/{event_id}/streaming', {'vid': vid}),
            ) for vid in traverse_obj(content_data, ('videoIds', ..., {str_or_none}))]

            return self.playlist_result(entries, event_id, event_title)

        video_data = self._call_api(f'streaming/{event_id}/videos/{video_id}', video_id, 'video info')

        return {
            'id': video_id,
            'title': traverse_obj(video_data, ('name', 'stringValue', {clean_html}, filter)),
            'formats': self._extract_formats(content_data, video_id),
            'series': event_title,
            'series_id': event_id,
            **traverse_obj(event_data, {
                'categories': ('categories', 'arrayValue', 'values', ..., 'stringValue', {clean_html}, filter, all, filter),
                'description': ('description', 'stringValue', {clean_html}, filter),
                'tags': ('twitterHashTag', 'arrayValue', 'values', ..., 'stringValue', {clean_html}, filter, all, filter),
                'thumbnail': ('defaultImg', 'stringValue', {url_or_none}),
            }),
            **traverse_obj(event_data, ('parts', 'arrayValue', 'values', ..., 'mapValue', 'fields', any, {
                'release_timestamp': ('openTime', 'timestampValue', {parse_iso8601}),
                'timestamp': ('startTime', 'timestampValue', {parse_iso8601}),
            })),
        }


class SPWNCrewIE(SPWNBaseIE):
    _VALID_URL = [
        r'https?://spwn\.jp/streams/(?P<id>\w+)\?(?:[^#]+&)?crewBrandSlug=(?P<brand_slug>\w+)',
        r'https?://crew\.spwn\.jp/(?P<brand_slug>\w+)/contents/(?P<id>\w+)',
    ]
    _TESTS = [{
        'url': 'https://spwn.jp/streams/4is8dCxPgTAdsoZkeHnd?planContentId=pcon_5WCeTfNqMcSyGOQsRSAc&crewBrandSlug=azupri',
        'info_dict': {
            'id': 'pcon_5WCeTfNqMcSyGOQsRSAc',
            'ext': 'mp4',
            'title': '紫月杏朱彩のお姫様になるんだもん☆ No.006 無料配信',
            'channel': '紫月杏朱彩のお姫様になるんだもん☆',
            'channel_id': 'azupri',
            'display_id': '4is8dCxPgTAdsoZkeHnd',
            'live_status': 'was_live',
            'release_date': '20251217',
            'release_timestamp': 1765969800,
            'media_type': 'streaming',
            'thumbnail': r're:https?://.+',
            'timestamp': 1765970400,
            'upload_date': '20251217',
        },
    }, {
        'url': 'https://crew.spwn.jp/azupri/contents/pcon_Nk7dGd7Vf3yMH5Pja6pY',
        'info_dict': {
            'id': 'pcon_Nk7dGd7Vf3yMH5Pja6pY',
            'ext': 'mp4',
            'title': '【プレミアムプラン限定】紫月杏朱彩のお姫様になるんだもん☆プリンセスロケ#12',
            'channel': '紫月杏朱彩のお姫様になるんだもん☆',
            'channel_id': 'azupri',
            'comment_count': int,
            'description': 'md5:bf0ba4ad06749bd6312d398739c6fc7e',
            'like_count': int,
            'media_type': 'video',
            'thumbnail': r're:https?://.+',
            'timestamp': 1782468035,
            'upload_date': '20260626',
        },
        'skip': 'Premium members only',
    }]

    def _real_extract(self, url):
        display_id, brand_slug = self._match_valid_url(url).group('id', 'brand_slug')
        if urllib.parse.urlparse(url).netloc == 'spwn.jp':
            plan_content_id = traverse_obj(parse_qs(url), (
                'planContentId', -1, {str}, {require('plan content ID')}))
        else:
            plan_content_id = display_id

        webpage = self._download_webpage(
            f'https://crew.spwn.jp/{brand_slug}', brand_slug)
        nextjs_data = self._search_nextjs_data(webpage, brand_slug)
        brand_metadata = traverse_obj(nextjs_data, (
            'props', 'pageProps', 'brandMetadata', {dict}))
        tenant_id = traverse_obj(brand_metadata, (
            'tenantId', {str}, {require('tenant ID')}))

        content = self._download_json(
            'https://prod-crew-api-vllpz7fe5q-an.a.run.app/public/fanclub/getPublicPlanContent',
            display_id, headers={
                'Authorization': f'Bearer {self._TOKEN}',
                'Content-Type': 'application/json',
                'Origin': self._BASE_URL,
            }, data=json.dumps({
                'planContentId': plan_content_id,
                'tenantId': tenant_id,
            }).encode())
        if not traverse_obj(content, ('ok', {bool})):
            status = traverse_obj(content, ('status', {str}, filter))

            raise ExtractorError(
                status or 'API returned an error response', expected=bool(status))

        content_data = traverse_obj(content, ('planContent', {dict}))

        metadata = {}
        if event_id := traverse_obj(content_data, (
            'details', 'eventId', {str}, filter,
        )):
            event_data = self._call_api(f'events/{event_id}', event_id, 'event info')
            metadata = {
                **traverse_obj(event_data, {
                    'title': ('title', {clean_html}, filter),
                    'description': ('description', 'stringValue', {clean_html}, filter),
                    'thumbnail': ('defaultImg', 'stringValue', {url_or_none}),
                }),
                **traverse_obj(event_data, ('parts', 'arrayValue', 'values', ..., 'mapValue', 'fields', any, {
                    'release_timestamp': ('openTime', 'timestampValue', {parse_iso8601}),
                    'timestamp': ('startTime', 'timestampValue', {parse_iso8601}),
                })),
            }

            streaming_status = traverse_obj(content_data, ('details', 'streamingStatus', {str}, filter))
            live_status = {
                'beforeLive': 'is_upcoming',
                'beforeVOD': 'post_live',
                'ended': 'was_live',
                'live': 'is_live',
                'vod': 'was_live',
            }.get(streaming_status)
            metadata['live_status'] = live_status

            release_timestamp = metadata.get('release_timestamp')
            if release_timestamp and time.time() < release_timestamp:
                start_time = dt.datetime.fromtimestamp(
                    release_timestamp, dt.timezone.utc,
                ).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
                self.raise_no_formats(
                    f'This livestream is scheduled to start at {start_time}', expected=True)

                return {
                    'id': plan_content_id,
                    'live_status': live_status,
                    'release_timestamp': release_timestamp,
                }

        return {
            'id': plan_content_id,
            'channel_id': brand_slug,
            'display_id': display_id,
            'formats': self._extract_formats(content_data, plan_content_id, crew=True),
            **traverse_obj(content_data, {
                'title': ('planContentName', {clean_html}, filter),
                'channel': ('brand', 'name', {clean_html}, filter),
                'comment_count': ('countOfComments', {int_or_none}),
                'like_count': ('countOfLoves', {int_or_none}),
                'media_type': ('type', {str}, filter),
                'timestamp': ('publishedAt', {int_or_none(scale=1000)}),
            }),
            **traverse_obj(content_data, ('details', {
                'description': (
                    'text', 'content', ..., 'content', ..., 'text',
                    {clean_html}, all, {unpack(join_nonempty, delim='\n')}, filter),
                'thumbnail': ('videoThumbnail', {url_or_none}),
            })),
            **metadata,
        }

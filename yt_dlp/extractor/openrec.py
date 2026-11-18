import collections
import datetime as dt
import functools
import itertools
import json
import math
import time
import urllib.parse
import xml.etree.ElementTree

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    clean_html,
    extract_attributes,
    filter_dict,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    parse_qs,
    str_or_none,
    update_url_query,
    url_or_none,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    require,
    traverse_obj,
)


class OpenRecBaseIE(InfoExtractor):
    _API_BASE = 'https://apiv5.mellow-fan.com/api/v5'
    _BASE_URL = 'https://www.mellow-fan.com'
    _HEADERS = {'Referer': f'{_BASE_URL}/'}
    _NETRC_MACHINE = 'mellowfan'
    _PUBLIC_API_BASE = 'https://public.mellow-fan.com/external/api/v5'

    def _perform_login(self, username, password):
        if self._get_cookies(self._BASE_URL).get('access-token'):
            return

        login = self._download_json(
            f'{self._BASE_URL}/apiv5/email/login',
            None, 'Logging in', headers={
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'email': username,
                'password': password,
            }).encode())
        if traverse_obj(login, ('status', {int_or_none})) != 0:
            err_msg = traverse_obj(login, ('message', {clean_html}, filter))
            raise ExtractorError(err_msg or 'Failed to log in', expected=True)

    def _real_initialize(self):
        cookies = self._get_cookies(self._BASE_URL)
        self._api_headers = traverse_obj(cookies, {
            'access-token': ('access_token', 'value', {str}, filter),
            'random': ('random', 'value', {str}, filter),
            'token': ('token', 'value', {str}, filter),
            'uuid': ('uuid', 'value', {str}, filter),
        })

    def _extract_pagestore(self, webpage, video_id):
        start = r'window\.pageStore\s*='

        if store := self._search_regex(
                rf'{start}\s*JSON\.parse\s*\(\s*decodeURIComponent'
                r'\s*\(\s*(?P<q>["\'])(?P<json>.*?)(?P=q)\s*\)\s*\)',
                webpage, 'encoded window pagestore', group='json', default=None,
        ):
            return self._parse_json(store, video_id, transform_source=urllib.parse.unquote)
        return self._search_json(start, webpage, 'window pagestore', video_id)

    def _call_api(self, path, item_id):
        return self._download_json(
            f'{self._API_BASE}/{path}', item_id,
            headers=self._api_headers, expected_status=401)

    def _parse_openrec_metadata(self, page_store, video_id):
        info = traverse_obj(page_store, ('v8', 'movie', {dict}))

        target_members = traverse_obj(info, (
            'targetMembers', ..., 'type', {str}, filter, any))
        needs_subscription = target_members == 'subscription'
        needs_auth = target_members == 'ppv'

        me = self._call_api('users/me', video_id)
        needs_premium = traverse_obj(info, (
            'publicType', {str}, filter)) == 'premium'
        is_premium = traverse_obj(me, (
            'data', 'items', ..., 'is_premium', {bool}, any)) or False

        detail = self._call_api(f'movies/{video_id}/detail', video_id)
        is_member = traverse_obj(detail, (
            'data', 'items', ..., 'membership', 'is_active', {bool}, any)) or False
        has_ppv = traverse_obj(detail, (
            'data', 'items', ..., 'ppv_ticket_products', ..., {dict}, any)) or False

        need = None
        if needs_premium and not is_premium:
            need = 'premium membership'
        elif needs_subscription and not is_member:
            need = 'channel subscription'
        elif needs_auth and not has_ppv:
            need = 'PPV purchase'

        if need:
            self.raise_login_required(
                f'This content requires a {need}', metadata_available=True)

        return info, detail, {
            'id': video_id,
            'availability': self._availability(
                needs_premium=needs_premium,
                needs_subscription=needs_subscription,
                needs_auth=needs_auth,
            ) or 'public',
            'http_headers': self._HEADERS,
            'tags': traverse_obj(page_store, (
                'movieStore', 'tags', ..., {clean_html}, filter, all, filter)),
            **traverse_obj(info, {
                'title': ('title', {clean_html}, filter),
                'cast': ('casts', ..., 'name', {clean_html}, filter, all, filter),
                'categories': ('game', 'title', {clean_html}, filter, all, filter),
                'description': ('introduction', {clean_html}, filter),
                'duration': ('playTime', 'value', {int_or_none(scale=1000)}),
                'thumbnail': (('lThumbnailUrl', 'thumbnailUrl'), {url_or_none}, any),
                'timestamp': ('startedAt', 'time', {int_or_none(scale=1000)}),
                'view_count': ('totalViews', {int_or_none}),
            }),
            **traverse_obj(info, ('channel', 'user', {
                'channel_follower_count': ('followers', {int_or_none}),
                'channel_id': ('id', {str_or_none}),
                'channel': ('name', {clean_html}, filter),
                'channel_is_verified': ('isOfficial', {bool}),
            })),
        }


class OpenRecIE(OpenRecBaseIE):
    IE_NAME = 'mellowfan'
    IE_DESC = 'mellow-fan'

    _VALID_URL = r'https?://(?:www\.)?(?:mellow-fan\.com|openrec\.tv)/(?:m/)?live/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.openrec.tv/live/e2zwj0mp6ro',
        'info_dict': {
            'id': 'e2zwj0mp6ro',
            'ext': 'mp4',
            'title': '収束',
            'availability': 'public',
            'categories': ['雑談'],
            'channel': 'おおえのたかゆき',
            'channel_follower_count': int,
            'channel_id': 'oekaki',
            'channel_is_verified': True,
            'comment_count': int,
            'description': 'md5:62260f3060b40187282f3213bcd97abd',
            'duration': 14257,
            'live_status': 'was_live',
            'tags': ['雑談'],
            'thumbnail': r're:https?://.+',
            'timestamp': 1685271819,
            'upload_date': '20230528',
            'view_count': int,
        },
        'skip': '404 Not Found',
    }, {
        # SP
        'url': 'https://www.mellow-fan.com/live/2p8vv29438y',
        'info_dict': {
            'id': '2p8vv29438y',
            'ext': 'mp4',
            'title': 'それいけ加藤純一探検隊！ 〜南の孤島で希少生物を探せスペシャル〜 (OPENRECプレミアム会員限定)',
            'availability': 'premium_only',
            'categories': ['雑談'],
            'channel': '加藤 純一',
            'channel_follower_count': int,
            'channel_id': 'junichi_kato_channel',
            'channel_is_verified': True,
            'comment_count': int,
            'description': 'md5:693bc0c838ff6080f9ca00d41dc5e840',
            'duration': 24336,
            'live_status': 'was_live',
            'release_date': '20251008',
            'release_timestamp': 1759892400,
            'thumbnail': r're:https?://.+',
            'timestamp': 1759891802,
            'upload_date': '20251008',
            'view_count': int,
        },
    }, {
        # Members only
        'url': 'https://www.mellow-fan.com/live/kdr7nldqgzj',
        'info_dict': {
            'id': 'kdr7nldqgzj',
            'ext': 'mp4',
            'title': '【ゲーム実況生配信】小森結梨のひきこもりゲーム部屋#20[ゲスト:梅澤めぐ]',
            'availability': 'subscriber_only',
            'categories': ['Human Fall Flat'],
            'channel': 'セカンドショットGAME部',
            'channel_follower_count': int,
            'channel_id': 'secondshot_games',
            'channel_is_verified': True,
            'chapters': [
                {'start_time': 0, 'title': 'バイオハザード RE：2', 'end_time': 443},
                {'start_time': 443, 'title': 'ぷにゃん', 'end_time': 3215},
                {'start_time': 3215, 'title': 'Human Fall Flat', 'end_time': 7163},
            ],
            'comment_count': int,
            'description': 'md5:b77fac6fb0ad86048dc6377ec2c22646',
            'duration': 7163,
            'live_status': 'was_live',
            'release_date': '20260220',
            'release_timestamp': 1771581300,
            'tags': ['声優'],
            'thumbnail': r're:https?://.+',
            'timestamp': 1771581322,
            'upload_date': '20260220',
            'view_count': int,
        },
        'skip': 'Subscribers only',
    }, {
        # PPV
        'url': 'https://www.mellow-fan.com/live/e5rk93xn1zv',
        'info_dict': {
            'id': 'e5rk93xn1zv',
            'ext': 'mp4',
            'title': '三川華月生誕パーティー2026 【ゲスト：幸村恵理/北原沙弥香】',
            'availability': 'needs_auth',
            'categories': ['雑談'],
            'channel': '三川華月の開店！はるちゃん食堂',
            'channel_follower_count': int,
            'channel_id': 'haruna_harusyoku',
            'channel_is_verified': True,
            'description': 'md5:912d0c2d60d343e28300fc18bd491d6c',
            'duration': 6451,
            'live_status': 'was_live',
            'release_date': '20260222',
            'release_timestamp': 1771758000,
            'thumbnail': r're:https?://.+',
            'timestamp': 1771758062,
            'upload_date': '20260222',
            'view_count': int,
        },
        'skip': 'Paid video',
    }]

    @staticmethod
    def _json2xml(subs, started_at):
        def filter_valid(items):
            yield from traverse_obj(items, (
                lambda _, v: clean_html(v['message']) and not v['stamp']))

        total = collections.Counter(
            traverse_obj(subs, (..., 'posted_at', {parse_iso8601})))
        order = collections.defaultdict(int)

        root = xml.etree.ElementTree.Element('packet')
        for i, s in enumerate(filter_valid(subs), 1):
            posted_at = traverse_obj(s, ('posted_at', {parse_iso8601}))
            offset = order[posted_at] / total[posted_at] + 1
            order[posted_at] += 1
            vpos = int_or_none((posted_at - started_at + offset) * 100)

            xml.etree.ElementTree.SubElement(
                root, 'chat', filter_dict({
                    **traverse_obj(s, ('user', {
                        'premium': ('is_premium', {bool}, {lambda x: '1' if x else '0'}),
                        'user_id': ('id', {str_or_none}),
                        'name': ('nickname', {str}, filter),
                    })),
                    'no': str(i),
                    'vpos': str_or_none(vpos),
                    'date': str_or_none(posted_at),
                }),
            ).text = traverse_obj(s, ('message', {clean_html}, filter))
        xml.etree.ElementTree.indent(root, space='  ')

        return xml.etree.ElementTree.tostring(
            root, encoding='utf-8', xml_declaration=True).decode()

    def _get_subtitles(self, duration, started_at, video_id):
        ended_at = started_at + duration
        timestamp = started_at

        subs = []
        for page in itertools.count(1):
            created_at = dt.datetime.fromtimestamp(
                timestamp, dt.timezone(dt.timedelta(hours=9))).strftime('%Y-%m-%dT%H:%M:%S%z')

            chats = self._download_json(
                f'{self._PUBLIC_API_BASE}/movies/{video_id}/chats',
                video_id, f'Downloading chats page {page}', query={
                    'from_created_at': created_at,
                    'is_including_system_message': 'true',
                })
            if not chats:
                break

            subs.extend(chats)
            last_posted_at = traverse_obj(chats, (-1, 'posted_at', {parse_iso8601}))
            if ended_at < last_posted_at:
                break

            timestamp = last_posted_at + 1
            time.sleep(0.1)

        return {
            'chats': [{
                'data': json.dumps(subs, indent=2, ensure_ascii=False),
                'ext': 'json',
            }, {
                'data': self._json2xml(subs, started_at),
                'ext': 'xml',
            }],
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, expected_status=404)
        page_store = self._extract_pagestore(webpage, video_id)
        if traverse_obj(page_store, ('movieStore', 'notFound', {bool})):
            raise ExtractorError('This video in no longer available', expected=True)

        info, detail, metadata = self._parse_openrec_metadata(page_store, video_id)
        live_status = {
            'ARCHIVE': 'was_live',
            'COMING_UP': 'is_upcoming',
            'LIVE_STREAMING': 'is_live',
            'UPLOADED': 'not_live',
        }.get(info.get('onAirStatus'))

        release_timestamp = traverse_obj(page_store, ('movieStore', 'willStartAt', {parse_iso8601}))
        if live_status == 'is_upcoming':
            if release_timestamp is not None:
                start_time = dt.datetime.fromtimestamp(
                    release_timestamp, dt.UTC,
                ).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
                msg = f'This livestream is scheduled to start at {start_time}'
            else:
                msg = 'This livestream has not yet started'

            self.raise_no_formats(msg, expected=True)

            return {
                'id': video_id,
                'live_status': live_status,
                'release_timestamp': release_timestamp,
            }

        duration = metadata['duration']
        started_at = metadata['timestamp']

        chapters = []
        for chapter in traverse_obj(info, (
            'chapters', lambda _, v: int_or_none(v['chapterAt']['time']),
        )):
            chapter_at = traverse_obj(chapter, ('chapterAt', 'time', {int_or_none(scale=1000)}))
            chapters.append({
                'start_time': chapter_at - started_at,
                'title': traverse_obj(chapter, ('title', {clean_html}, filter)),
            })

        formats = []
        is_dvr = live_status == 'is_live' and self.get_param('live_from_start')
        media_keys = ('url_dvr', 'url_dvr_audio') if is_dvr else ('url', 'url_audio')
        for m3u8_url in traverse_obj(detail, (
            'data', 'items', ...,
            ('media', 'subs_trial_media'), media_keys, {url_or_none},
        )):
            fmts = self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', headers=self._HEADERS)
            for fmt in fmts:
                if is_dvr:
                    fmt.setdefault('downloader_options', {}).update({'ffmpeg_args': ['-live_start_index', '0']})
                    fmt['is_from_start'] = True
            formats.extend(fmts)

        return {
            'chapters': chapters or None,
            'comment_count': traverse_obj(page_store, (
                'commentStore', 'commentCount', {int_or_none})),
            'formats': formats,
            'live_status': live_status,
            'release_timestamp': release_timestamp,
            'subtitles': self.extract_subtitles(duration, started_at, video_id),
            **metadata,
        }


class OpenRecCaptureIE(OpenRecBaseIE):
    IE_NAME = 'mellowfan:capture'

    _VALID_URL = r'https?://(?:www\.)?(?:mellow-fan\.com|openrec\.tv)/(?:m/)?capture/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.mellow-fan.com/capture/l2q00vxl8q8',
        'info_dict': {
            'id': 'l2q00vxl8q8',
            'ext': 'mp4',
            'title': '？？？？',
            'channel': '布団ちゃん',
            'channel_id': 'indegnasen',
            'duration': 89,
            'thumbnail': r're:https?://.+',
            'timestamp': 1637589871,
            'upload_date': '20211122',
        },
    }, {
        'url': 'https://www.mellow-fan.com/capture/9pdz9334vng',
        'info_dict': {
            'id': '9pdz9334vng',
            'ext': 'mp4',
            'title': 'オプレの現実',
            'channel': 'ゆゆうた&みゃこの泥沼バラエティ',
            'channel_id': 'doronuma-variety',
            'duration': 64,
            'thumbnail': r're:https?://.+',
            'timestamp': 1677585253,
            'upload_date': '20230228',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        page_store = self._extract_pagestore(webpage, video_id)

        capture = page_store['capture']
        m3u8_url = traverse_obj(capture, ('source', {url_or_none}))

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', headers=self._HEADERS),
            'http_headers': self._HEADERS,
            **traverse_obj(page_store, ('movie', 'channel', {
                'channel': ('name', {clean_html}, filter),
                'channel_id': ('id', {str}),
            })),
            **traverse_obj(capture, {
                'title': ('title', {clean_html}, filter),
                'duration': ({lambda x: int_or_none(x['endTime']) - int_or_none(x['startTime'])}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'timestamp': ('publishedAt', {parse_iso8601}),
            }),
        }


class OpenRecMovieIE(OpenRecBaseIE):
    IE_NAME = 'mellowfan:movie'

    _VALID_URL = r'https?://(?:www\.)?(?:mellow-fan\.com|openrec\.tv)/(?:m/)?movie/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.mellow-fan.com/movie/e5rk9k4o6zv',
        'info_dict': {
            'id': 'e5rk9k4o6zv',
            'ext': 'mp4',
            'title': 'みゃこRaMuの企画会議#3 ～2人のやってみたいこと～',
            'availability': 'public',
            'categories': ['雑談'],
            'channel': 'みゃことRaMuの何して遊ぶ？',
            'channel_follower_count': int,
            'channel_id': 'myakoramu',
            'channel_is_verified': True,
            'description': 'md5:90924fd73356ebd574bec8d761d4fa62',
            'duration': 771,
            'tags': ['雑談'],
            'thumbnail': r're:https?://.+',
            'view_count': int,
        },
    }, {
        # Members only
        'url': 'https://www.mellow-fan.com/movie/n9ze6q3eo84',
        'info_dict': {
            'id': 'n9ze6q3eo84',
            'ext': 'mp4',
            'title': '大西亜玖璃・高尾奏音のあぐのんる～むらぼ♪第123回傑作選vol.3【高画質・完全版】',
            'availability': 'subscriber_only',
            'categories': ['雑談'],
            'channel': 'セカンドショットGAME部',
            'channel_follower_count': int,
            'channel_id': 'secondshot_games',
            'channel_is_verified': True,
            'description': 'md5:b7ab5ddd71ba5edc1141cb427af7a9c6',
            'duration': 1800,
            'tags': ['声優'],
            'thumbnail': r're:https?://.+',
            'view_count': int,
        },
        'skip': 'Subscribers only',
    }, {
        # PPV
        'url': 'https://www.mellow-fan.com/movie/em8xvd4ljr2',
        'info_dict': {
            'id': 'em8xvd4ljr2',
            'ext': 'mp4',
            'title': '【PPV購入特典映像】KAWAII LAB. SESSION in OKINAWA',
            'availability': 'needs_auth',
            'categories': ['ミュージック'],
            'channel': 'KAWAII LAB.チャンネル',
            'channel_follower_count': int,
            'channel_id': 'KAWAIILAB',
            'channel_is_verified': True,
            'description': 'md5:e9f67d8648d3cbe35df1dd689afc29a8',
            'duration': 2002,
            'tags': ['アイドル'],
            'thumbnail': r're:https?://.+',
            'view_count': int,
        },
        'skip': 'Paid video',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        page_store = self._extract_pagestore(webpage, video_id)
        _, detail, metadata = self._parse_openrec_metadata(page_store, video_id)

        formats = []
        for m3u8_url in traverse_obj(detail, (
            'data', 'items', ..., 'media',
            ('url', 'url_audio'), {url_or_none},
        )):
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', headers=self._HEADERS))

        return {
            'formats': formats,
            **metadata,
        }


class OpenRecPlaylistIE(OpenRecBaseIE):
    IE_NAME = 'mellowfan:playlist'

    _VALID_URL = r'https?://(?:www\.)?(?:mellow-fan\.com|openrec\.tv)/(?:m/)?user/[^/?#]+/playlist/(?P<id>[^/?#]+)'
    _TESTS = [{
        # live
        'url': 'https://www.mellow-fan.com/user/DbD_BPF/playlist/j59svruhtua2z8t',
        'info_dict': {
            'id': 'j59svruhtua2z8t',
            'title': 'BPFのおすすめ',
        },
        'playlist_mincount': 10,
    }, {
        # capture
        'url': 'https://www.mellow-fan.com/user/sagara_mayu/playlist/xngNMzv71yLjGdW',
        'info_dict': {
            'id': 'xngNMzv71yLjGdW',
            'title': '相良茉優のFAN!FUN!FACTORY!キャプチャ',
        },
        'playlist_mincount': 4,
    }, {
        # movie
        'url': 'https://www.mellow-fan.com/user/oreranohonoka/playlist/sficoshvi9dgkqh',
        'info_dict': {
            'id': 'sficoshvi9dgkqh',
            'title': 'SP（スペシャル）映像：（短編映像）おにいたむプランだけが視聴できます',
        },
        'playlist_mincount': 111,
    }]

    def _entries(self, items):
        for movie in traverse_obj(items, (
            'playlist_movies', ..., 'movie', 'id', {str_or_none},
        )):
            is_live = traverse_obj(movie, ('movie', 'is_live', {bool}))
            path, ie = ('live', OpenRecIE) if is_live else ('movie', OpenRecMovieIE)
            movie_id = movie['movie']['id']

            yield self.url_result(f'{self._BASE_URL}/{path}/{movie_id}', ie)

        for capture in traverse_obj(items, (
            'playlist_captures', ...,
            'capture_relation', 'capture', 'id', {str_or_none},
        )):
            capture_id = capture['capture_relation']['capture']['id']

            yield self.url_result(
                f'{self._BASE_URL}/capture/{capture_id}', OpenRecCaptureIE)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        me = self._call_api(f'users/me/playlists/{playlist_id}', playlist_id)

        if items := traverse_obj(me, (
            'data', 'items', ..., {dict}, any,
        )):
            return self.playlist_result(
                self._entries(items), playlist_id,
                traverse_obj(items, ('title', {clean_html}, filter)))

        webpage = self._download_webpage(url, playlist_id)
        playlist_title = traverse_obj(webpage, (
            {find_element(cls='sc-1ak77bz-10')}, {clean_html}, filter))

        return self.playlist_from_matches(traverse_obj(webpage, (
            {find_elements(cls='sc-vc0xhn-0')}, ...,
            {find_element(cls='sc-1ddd11y-0', html=True)},
            {extract_attributes}, 'href', {str},
        )), playlist_id, playlist_title, getter=urljoin(f'{self._BASE_URL}/'))


class OpenRecChannelIE(OpenRecBaseIE):
    IE_NAME = 'mellowfan:channel'

    _PAGE_SIZE = 40
    _VALID_URL = r'https?://(?:www\.)?(?:mellow-fan\.com|openrec\.tv)/(?:m/)?user/(?P<id>[^/?#]+)$'
    _TESTS = [{
        'url': 'https://www.mellow-fan.com/user/OPENRECPARK',
        'info_dict': {
            'id': 'OPENRECPARK',
            'title': 'OPENREC PARK',
        },
        'playlist_mincount': 40,
    }]

    def _fetch_page(self, channel_id, page):
        page += 1
        search_movies = self._download_json(
            f'{self._PUBLIC_API_BASE}/search-movies', channel_id,
            f'Downloading page {page}', query={
                'channel_ids': channel_id,
                'include_live': 'true',
                'include_upload': 'true',
                'onair_status': '2',
                'include_deleted': 'true',
                'sort': 'published_at',
                'page': str(page),
            })

        for movie in traverse_obj(search_movies, (
            lambda _, v: str_or_none(v['movie_type']) and str_or_none(v['id']),
        )):
            path, ie = ('live', OpenRecIE) if movie['movie_type'] == '1' else ('movie', OpenRecMovieIE)

            yield self.url_result(f'{self._BASE_URL}/{path}/{movie["id"]}', ie)

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        webpage = self._download_webpage(url, channel_id)
        page_store = self._extract_pagestore(webpage, channel_id)

        channel = traverse_obj(page_store, ('state', '_channel', {dict}))
        movie_count = traverse_obj(channel, ('movieCount', {int_or_none}))

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._fetch_page, channel_id),
            math.ceil(movie_count / self._PAGE_SIZE), self._PAGE_SIZE,
        ), channel_id, traverse_obj(channel, ('user', 'name', {clean_html}, filter)))


class OpenRecChannelSearchIE(OpenRecBaseIE):
    IE_NAME = 'mellowfan:channel:search'

    _VALID_URL = r'https?://(?:www\.)?(?:mellow-fan\.com|openrec\.tv)/(?:m/)?user/(?P<id>[^/?#]+)/search(?:/(?P<type>capture|movie))?(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://www.mellow-fan.com/user/indegnasen/search?search_query=%E3%82%B9%E3%82%A4%E3%82%AB',
        'info_dict': {
            'id': 'indegnasen',
            'title': 'indegnasen:スイカ',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.mellow-fan.com/user/ofurekodesu/search/movie?search_query=%E3%82%A2%E3%83%AA%E3%82%AA%E5%85%AB%E5%B0%BE',
        'info_dict': {
            'id': 'ofurekodesu',
            'title': 'ofurekodesu:アリオ八尾:movie',
        },
        'playlist_mincount': 31,
    }, {
        'url': 'https://www.mellow-fan.com/user/DbD_BPF/search/capture?search_query=%E3%81%82%E3%81%A3%E3%81%95%E3%82%8A%E3%81%97%E3%82%87%E3%81%93',
        'info_dict': {
            'id': 'DbD_BPF',
            'title': 'DbD_BPF:あっさりしょこ:capture',
        },
        'playlist_mincount': 10,
    }]

    def _entries(self, channel_id, search_type, search_query):
        api_url = f'{self._PUBLIC_API_BASE}/search-{search_type}s'
        type_map = {
            'capture': OpenRecCaptureIE,
            'live': OpenRecIE,
            'movie': OpenRecMovieIE,
        }

        for page in itertools.count(1):
            search_items = self._download_json(
                api_url, channel_id, f'Downloading page {page}', query={
                    'channel_ids': channel_id,
                    'page': page,
                    'search_query': search_query,
                })
            if not search_items:
                break

            for item in search_items:
                item_type = 'live' if search_type == 'movie' and traverse_obj(item, ('is_live', {bool})) else search_type
                item_id = traverse_obj(item, ((None, 'capture'), 'id', {str_or_none}, any))

                yield self.url_result(
                    f'{self._BASE_URL}/{item_type}/{item_id}', type_map[item_type])

    def _real_extract(self, url):
        channel_id, search_type = self._match_valid_url(url).group('id', 'type')
        search_query = traverse_obj(url, (
            {parse_qs}, 'search_query', -1, {str}, filter,
            {require('search query', expected=True)}))

        if not search_type:
            entries = []
            for search_type in ('capture', 'movie'):
                search_url = update_url_query(
                    f'{self._BASE_URL}/user/{channel_id}/search/{search_type}', {'search_query': search_query})
                entries.append(self.url_result(search_url, OpenRecChannelSearchIE))

            return self.playlist_result(
                entries, channel_id, join_nonempty(channel_id, search_query, delim=':'))

        return self.playlist_result(
            self._entries(channel_id, search_type, search_query),
            channel_id, join_nonempty(channel_id, search_query, search_type, delim=':'))

import datetime as dt
import itertools
import json
import re
import time
import urllib.parse

from .streaks import StreaksBaseIE
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    clean_html,
    decode_lzstring,
    filter_dict,
    int_or_none,
    join_nonempty,
    make_archive_id,
    parse_qs,
    str_or_none,
    time_seconds,
    unified_timestamp,
    url_or_none,
    urljoin,
)
from ..utils.traversal import (
    require,
    traverse_obj,
    trim_str,
)


class TVerBaseIE(StreaksBaseIE):
    _BASE_URL = 'https://tver.jp'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['JP']
    _HEADERS = {
        'Origin': _BASE_URL,
        'Referer': f'{_BASE_URL}/',
    }
    _IMG_BASE = 'https://image-cdn.tver.jp'
    _platform_query = None

    def _real_initialize(self):
        if self._platform_query is None:
            session_info = self._download_json(
                'https://platform-api.tver.jp/v2/api/platform_users/browser/create',
                None, 'Creating session', data=b'device_type=pc')
            TVerBaseIE._platform_query = traverse_obj(session_info, ('result', {
                'platform_token': ('platform_token', {str_or_none}),
                'platform_uid': ('platform_uid', {str_or_none}),
            })) or {}

    def _streaks_api_headers(self, project_id):
        streaks_info = self._download_json(
            'https://player.tver.jp/player/streaks_info_v2.json', None,
            'Downloading STREAKS API info', 'Unable to download STREAKS API info')
        key = dt.datetime.fromtimestamp(time_seconds(hours=9), dt.timezone.utc).month % 6 or 6

        return {
            **self._HEADERS,
            'X-Streaks-Api-Key': streaks_info[project_id]['api_key'][f'key{key:02d}'],
        }

    def _call_api(self, api_type, path, video_id, fatal=False, headers=None, query=None, **kwargs):
        api_base = {
            'contents': 'https://contents-api.tver.jp/contents',
            'member': 'https://member-api.tver.jp/service',
            'platform': 'https://platform-api.tver.jp/service',
            'service': 'https://service-api.tver.jp',
            'user': 'https://user-api.tver.jp/user',
        }[api_type]

        return self._download_json(
            f'{api_base}/api/{path}{f"/{video_id}" if video_id else ""}',
            video_id, fatal=fatal, headers={
                'x-tver-platform-type': 'web',
                **(headers or {}),
            }, query={
                **self._platform_query,
                **(query or {}),
            }, **kwargs)

    def _thumbnails(self, content_type, video_id):
        return [{
            'id': quality,
            'url': f'{self._IMG_BASE}/images/content/thumbnail/{content_type}/{quality}/{video_id}.jpg',
            'width': width,
            'height': height,
        } for quality, width, height in [
            ('small', 480, 270),
            ('medium', 640, 360),
            ('large', 960, 540),
            ('xlarge', 1280, 720),
        ]]


class TVerIE(TVerBaseIE):
    _VALID_URL = r'https?://tver\.jp/(?P<type>corner|episodes?|feature|lp)/(?P<id>[a-zA-Z0-9]+)(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://tver.jp/episodes/epjmuz7b1r',
        'info_dict': {
            'id': 'epjmuz7b1r',
            'ext': 'mp4',
            'title': '【なるほどッ！】絶景から穴場まで…「温泉総選挙」人気は？',
            'alt_title': '11月6日(木)放送分',
            'channel': '日テレ',
            'channel_id': 'ntv',
            'description': 'md5:b3e80d110373ab1a64d55241f7f0b22a',
            'display_id': 'ref:102343d6e76048edbeab05fb6e70d800',
            'duration': 647,
            'episode': '【なるほどッ！】絶景から穴場まで…「温泉総選挙」人気は？',
            'episode_id': 'epjmuz7b1r',
            'episode_number': 1238,
            'like_count': int,
            'live_status': 'not_live',
            'modified_date': '20251110',
            'modified_timestamp': 1762758822,
            'release_date': '20251110',
            'release_timestamp': 1762804800,
            'season': '本編',
            'season_id': 'sspo4y3d1n',
            'series': '日テレNEWSセレクト',
            'series_id': 'sru578is4n',
            'tags': ['報道／ドキュメンタリー'],
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1762757822,
            'upload_date': '20251110',
            'uploader_id': 'tver-ntv',
            '_old_archive_ids': ['brightcovenew ref:102343d6e76048edbeab05fb6e70d800'],
        },
    }, {
        'url': 'https://tver.jp/corner/f0103888',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/lp/f0087789',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')

        if video_type != 'episodes':
            if video_type == 'lp' and video_id in {'episodes', 'series'}:
                return self.url_result(url.replace('/lp', ''))
            webpage = self._download_webpage(url, video_id)
            redirect_url = self._og_search_url(webpage) or self._search_regex(
                r'<link\s+rel="canonical"\s+href="(https?://tver\.jp/[^"]*)"/>', webpage, 'redirect URL')
            if redirect_url == f'{self._BASE_URL}/':
                raise ExtractorError('This URL is currently unavailable', expected=True)
            return self.url_result(redirect_url)

        video_info = self._call_api('contents', 'v1/episodes', video_id)
        streaks_ids = video_info['streaks']
        project_id = traverse_obj(streaks_ids, (
            'project_id', {str_or_none}, {require('project ID')}))
        media_id = traverse_obj(streaks_ids, (
            'ovp_player_callback_id', {str_or_none}, {require('STREAKS media ID')}))
        brightcove_id = traverse_obj(streaks_ids, (
            'video_ref_id', {lambda x: f'ref:{x}' if x else None}))

        try:
            streaks_metadata = self._extract_from_streaks_api(
                project_id, media_id, self._streaks_api_headers(project_id))
        except GeoRestrictedError as e:
            # Re-raise with metadata_available=True to support --ignore-no-formats-error
            self.raise_geo_restricted(e.orig_msg, countries=self._GEO_COUNTRIES, metadata_available=True)
            streaks_metadata = {}

        return {
            **streaks_metadata,
            **traverse_obj(video_info, {
                'id': ('id', {str_or_none}),
                'title': ('title', {clean_html}, filter),
                'alt_title': ('broadcast_date_label', {clean_html}, filter),
                'channel': ('broadcast_provider_label', {clean_html}, filter),
                'channel_id': ('broadcast_provider_id', {str_or_none}),
                'description': ('description', {clean_html}, filter),
                'duration': ('duration', {int_or_none}),
                'episode': ('title', {clean_html}, filter),
                'episode_id': ('id', {str_or_none}),
                'episode_number': ('index_number', {int_or_none}),
                'tags': (('genres', 'sub_genres'), ..., 'name', {clean_html}, filter, all, filter),
                'like_count': ('like_count', {int_or_none}),
                'release_timestamp': ('view_status', 'start_at', {int_or_none}),
            }),
            **traverse_obj(video_info, ('channel', {
                'channel': ('broadcast_provider_name', {clean_html}, filter),
                'channel_id': ('url_key', {str_or_none}),
            })),
            **traverse_obj(video_info, ('season', {
                'season': ('title', {clean_html}, filter),
                'season_id': ('id', {str_or_none}),
            })),
            **traverse_obj(video_info, ('series', {
                'series': ('title', {clean_html}, filter),
                'series_id': ('id', {str_or_none}),
            })),
            'thumbnails': self._thumbnails('episode', video_id),
            '_old_archive_ids': [make_archive_id('BrightcoveNew', brightcove_id)] if brightcove_id else None,
        }


class TVerShortsIE(TVerBaseIE):
    IE_NAME = 'tver:shorts'

    _VALID_URL = r'https?://tver\.jp/shorts/(?P<id>[a-zA-Z0-9]+)(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://tver.jp/shorts/sej1hua0vh',
        'info_dict': {
            'id': 'sej1hua0vh',
            'ext': 'mp4',
            'title': '若葉と潮風そよぐ港町 広島・呉 海軍の歴史＆瀬戸内の絶景を巡る',
            'channel_id': 'tvo',
            'description': 'md5:750a7d2a2f94bc88f07ba58da4223fde',
            'display_id': 'ref:otonatabi20260523-00033-1',
            'duration': 70,
            'like_count': int,
            'live_status': 'not_live',
            'modified_date': '20260521',
            'modified_timestamp': 1779351746,
            'series': 'おとな旅あるき旅',
            'series_id': 'sr6q8agywz',
            'tags': ['TVer', 'ショート'],
            'thumbnail': r're:https?://.+\.png',
            'timestamp': 1779350850,
            'upload_date': '20260521',
            'uploader_id': 'tver-short-tvo',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api(
            'contents', 'v2/short_episodes', video_id, expected_status=404)
        if traverse_obj(video_info, ('code', {int_or_none})) == 4007:
            raise ExtractorError('This video is no longer available', expected=True)

        streaks_ids = video_info['streaks']
        project_id = traverse_obj(streaks_ids, ('project_id', {str_or_none}))
        media_id = traverse_obj(streaks_ids, (
            'ref_id', {lambda x: f'ref:{x}' if x else None}, {require('STREAKS media ID')}))

        return {
            **self._extract_from_streaks_api(
                project_id, media_id, self._streaks_api_headers(project_id)),
            **traverse_obj(video_info, {
                'id': ('id', {str_or_none}),
                'channel_id': ('broadcast_provider_id', {str_or_none}),
                'duration': ('duration', {int_or_none}),
                'tags': ('sns_share_body', 'hashtags', ...,
                         {clean_html}, {trim_str(start='#')}, filter, all, filter),
                'thumbnail': ('vertical_thumbnail_path', {urljoin(f'{self._IMG_BASE}/')}),
            }),
            **traverse_obj(video_info, ('episode', {
                'title': ('title', {clean_html}, filter),
                'description': ('description', {clean_html}, filter),
                'like_count': ('like_count', {int_or_none}),
            })),
            **traverse_obj(video_info, ('series', {
                'series': ('title', {clean_html}, filter),
                'series_id': ('id', {str_or_none}),
            })),
        }


class TVerLiveIE(TVerBaseIE):
    IE_NAME = 'tver:live'

    _STATION_RE = '|'.join(map(re.escape, ('cx', 'ex', 'ntv', 'tbs', 'tx')))
    _VALID_URL = rf'https?://tver\.jp/live/(?P<type>simul|special|{_STATION_RE})(?:/(?P<id>[a-zA-Z0-9]+))?(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://tver.jp/live/simul/lec0q2882d',
        'info_dict': {
            'id': 'lec0q2882d',
            'ext': 'mp4',
            'title': 'ＷＢＳ【利上げはあるか？ 日銀・植田総裁の発言分析】',
            'alt_title': '6月3日(水)放送分',
            'channel': 'テレ東',
            'channel_id': 'tx',
            'description': 'md5:d46ec2475fc614f7335e7291070d3c99',
            'display_id': 'ref:lec0q2882d',
            'duration': 3389.952,
            'live_status': 'was_live',
            'modified_date': '20260603',
            'modified_timestamp': 1780530183,
            'release_date': '20260603',
            'release_timestamp': 1780491600,
            'season_id': 's0000152',
            'series': 'ＷＢＳ（ワールドビジネスサテライト）',
            'series_id': 'srx2o7o3c8',
            'tags': 'count:5',
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1780491626,
            'upload_date': '20260603',
            'uploader_id': 'tver-simul-tx',
        },
    }, {
        'url': 'https://tver.jp/live/tx',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).group('type', 'id')
        live_from_start = self.get_param('live_from_start')
        now = time_seconds()

        if video_type not in ('simul', 'special'):
            timeline = self._call_api('service', 'v1/callLiveTimeline', video_type)
            video_id = traverse_obj(timeline, (
                'result', 'contents',
                lambda _, v: v['content']['onairStartAt'] <= now < v['content']['onairEndAt'],
                'content', 'id', {str_or_none}, any))
            if not video_id:
                raise ExtractorError('This channel is offline', expected=True)

        episode_status = self._call_api(
            'service', 'v1/callEpisodeStatusCheck', None,
            query={'episode_id': video_id, 'type': 'live'}, expected_status=404)
        if traverse_obj(episode_status, ('code', {int_or_none})) == 70006:
            raise ExtractorError('This livestream is no longer available', expected=True)

        result = episode_status['result']
        content = traverse_obj(result, ('content', {dict}))
        if traverse_obj(result, ('type', {str})) == 'live':
            start_at = traverse_obj(content, ('startAt', {int_or_none}))
            end_at = traverse_obj(content, ('endAt', {int_or_none}))

            if now < start_at:
                self.raise_no_formats(
                    f'This livestream is scheduled to start at {start_at} UTC', expected=True)

                return {
                    'id': video_id,
                    'live_status': 'is_upcoming',
                    'release_timestamp': start_at,
                }
            elif start_at <= now < end_at:
                live_status = 'is_live'
                if live_from_start and traverse_obj(content, (
                    'dvr', 'isDVR', {bool},
                )):
                    key = 'dvrVideo'
                else:
                    key = 'liveVideo'
            elif traverse_obj(content, ('isDVRNow', {bool})):
                live_status = 'was_live'
                key = 'dvrVideo'
            else:
                raise ExtractorError(
                    'This livestream has ended and no archive is available', expected=True)
        else:
            return self.url_result(
                f'{self._BASE_URL}/episodes/{content["id"]}', TVerIE)

        live_info = self._download_json(
            f'https://statics.tver.jp/content/live/{video_id}.json', video_id)
        project_id = traverse_obj(live_info, (
            key, 'projectID', {str_or_none}, {require('project ID')}))
        media_id = traverse_obj(live_info, (
            key, 'mediaID', {str_or_none}, {require('STREAKS media ID')}))

        return {
            **self._extract_from_streaks_api(
                project_id, media_id,
                self._streaks_api_headers(project_id),
                live_from_start=live_from_start),
            **traverse_obj(live_info, {
                'id': ('id', {str_or_none}),
                'title': ('title', {clean_html}, filter),
                'alt_title': ('broadcastDateLabel', {clean_html}, filter),
                'channel': ('broadcastProviderLabel', {clean_html}, filter),
                'channel_id': ('broadcastChannelID', {str_or_none}),
                'description': ('description', {clean_html}, filter),
                'release_timestamp': ('viewStatus', 'startAt', {int_or_none}),
                'season_id': ('seasonID', {str_or_none}),
                'series': ('share', 'text', {clean_html}, {trim_str(end=' #TVer')}, filter),
                'series_id': ('seriesID', {str_or_none}),
                'tags': ('tags', ..., 'name', {clean_html}, filter, all, filter),
            }),
            'live_status': live_status,
            'thumbnails': self._thumbnails('live', video_id),
        }


class TVerChannelsIE(TVerBaseIE):
    IE_NAME = 'tver:channels'

    _VALID_URL = r'https?://tver\.jp/channels/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://tver.jp/channels/news-nnn',
        'info_dict': {
            'id': 'news-nnn',
            'title': '日テレNEWS NNN',
        },
        'playlist_mincount': 5956,
    }]
    _PAGE_SIZE = 100

    def _entries(self, channel_id):
        next_cursor = None
        for page in itertools.count(1):
            latest_episodes = self._call_api(
                'contents', f'v1/channels/{channel_id}/pages/latest_episodes',
                None, note=f'Downloading page {page}', query=filter_dict({
                    'limit': self._PAGE_SIZE,
                    'next_cursor': next_cursor,
                }))

            for episode_id in traverse_obj(latest_episodes, (
                'episodes', ..., 'episode_id', {str_or_none},
            )):
                yield self.url_result(
                    f'{self._BASE_URL}/episodes/{episode_id}', TVerIE)

            next_cursor = traverse_obj(latest_episodes, ('next_cursor', {str_or_none}))
            if not next_cursor:
                break

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel = self._call_api('contents', 'v1/channels', channel_id)

        return self.playlist_result(
            self._entries(channel_id), channel_id,
            traverse_obj(channel, ('title', {clean_html}, filter)))


class TVerPlaylistBaseIE(TVerBaseIE):
    def _entries(self, result, keys):
        type_map = {
            'episode': ('episodes', TVerIE),
            'live': ('live/simul', TVerLiveIE),
            'series': ('series', TVerPlaylistIE),
            'specialMain': ('specials', TVerPlaylistIE),
            'talent': ('talents', TVerPlaylistIE),
        }

        for item in traverse_obj(result, (
            'contents', *keys, all,
            lambda _, v: v['type'] != 'live' or v['content']['isDVRNow'],
        )):
            path, ie = type_map.get(item['type'])
            item_id = traverse_obj(item, ('content', 'id', {str_or_none}))

            yield self.url_result(f'{self._BASE_URL}/{path}/{item_id}', ie)


class TVerPlaylistIE(TVerPlaylistBaseIE):
    IE_NAME = 'tver:playlist'

    _PLAYLIST_TYPE_RE = '|'.join((
        'ender', 'newer', 'series', 'rankings/episode',
        r'specials/[\w-]+', 'tags', 'talents',
    ))
    _VALID_URL = rf'https?://tver\.jp/(?P<type>{_PLAYLIST_TYPE_RE})(?:/(?P<id>[\w-]+))?(?:/episodes)?'
    _TESTS = [{
        'url': 'https://tver.jp/series/srqbg9lpzc',
        'info_dict': {
            'id': 'srqbg9lpzc',
            'title': '【しらべてみたら】Live News イット！特集',
        },
        'playlist_mincount': 13,
    }, {
        'url': 'https://tver.jp/rankings/episode/drama',
        'info_dict': {
            'id': 'drama',
            'title': 'ドラマ',
        },
        'playlist_count': 50,
    }, {
        'url': 'https://tver.jp/ender/anime',
        'info_dict': {
            'id': 'anime',
            'title': 'アニメ／ヒーロー',
        },
        'playlist_count': 100,
    }]

    def _real_extract(self, url):
        playlist_type, playlist_id = self._match_valid_url(url).group('type', 'id')
        playlist_key = playlist_type.split('/')[0]

        if playlist_key == 'specials' and not playlist_id:
            main_id = playlist_type.split('/')[-1]
            special = self._call_api('platform', 'v1/callSpecialContents', main_id)
            all_id = traverse_obj(special, (
                'result', 'specialContents', ..., 'content', 'id', {str_or_none}, any))

            return self.url_result(
                f'{self._BASE_URL}/specials/{main_id}/{all_id}', TVerPlaylistIE)

        api_type, endpoint, keys = {
            'series': ('platform', 'v1/callSeriesEpisodes', (..., 'contents', ...)),
            'specials': ('platform', 'v1/callSpecialContentsDetail', ('content', 'contents', ...)),
            'tags': ('platform', 'v1/callTagSearch', (...,)),
            'talents': ('platform', 'v1/callTalentEpisode', (...,)),
            'ender': ('service', f'v1/callEnderDetail{"/all" * (not playlist_id)}', ('contents', ...)),
            'newer': ('service', f'v1/callNewerDetail{"/all" * (not playlist_id)}', ('contents', ...)),
            'rankings': ('service', 'v1/callEpisodeRankingDetail', ('contents', ...)),
        }[playlist_key]
        result = self._call_api(api_type, endpoint, playlist_id)['result']

        if playlist_key == 'series':
            playlist_title = traverse_obj(result, (
                'contents', ..., 'contents', ...,
                'content', 'seriesTitle', {clean_html}, filter, any))
        elif playlist_key == 'specials':
            playlist_title = traverse_obj(result, (
                'contents', 'content',
                ('specialMainTitle', 'title'), {clean_html},
                filter, all, {lambda x: join_nonempty(*x, delim=' - ')}))
        elif playlist_key in ('tags', 'ender', 'newer', 'rankings'):
            playlist_title = traverse_obj(result, ((
                ('contents', 'content', 'title'),
                ('tag', 'name'),
            ), {clean_html}, filter, any))
        elif playlist_key == 'talents':
            talents = self._call_api('contents', 'v1/talents', playlist_id)
            playlist_title = traverse_obj(talents, (
                'name', {clean_html}, {lambda x: re.sub(r'\s+', '', x)}, filter))
        else:
            playlist_title = None

        return self.playlist_result(
            self._entries(result, keys), playlist_id or playlist_type, playlist_title)


class TVerSearchIE(TVerPlaylistBaseIE):
    IE_NAME = 'tver:search'

    _VALID_URL = r'https?://(?:www\.)?tver\.jp/search/(?P<id>[^\?]+)(?:\?|$)'
    _TESTS = [{
        'url': 'https://tver.jp/search/%E3%83%A9%E3%83%B4%E3%82%A3%E3%83%83%E3%83%88%EF%BC%81',
        'info_dict': {
            'id': 'ラヴィット！',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://tver.jp/search/%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9?genre=news_documentary&weekday=mon&tvnetwork=txn',
        'info_dict': {
            'id': 'ニュース',
        },
        'playlist_mincount': 4,
    }]

    def _real_extract(self, url):
        keyword = urllib.parse.unquote(self._match_id(url))
        playlist_info = self._call_api(
            'platform', 'v2/callKeywordSearch', None, query={
                'filterKey': ','.join(v[0].replace(' ', ',') for v in parse_qs(url).values()),
                'keyword': keyword,
            })

        return self.playlist_result(
            self._entries(playlist_info['result'], (...,)), keyword)


class TVerMyPageIE(TVerPlaylistBaseIE):
    IE_NAME = 'tver:mypage'

    _VALID_URL = r'https?://(?:www\.)?tver\.jp/mypage/(?P<id>fav|later|resume)(?:\?|$)'
    _TESTS = [{
        'url': 'https://tver.jp/mypage/fav?filter=series',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/mypage/later',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/mypage/resume',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        cookies = self._get_cookies('https://s.tver.jp')
        member_sid = traverse_obj(cookies, (
            'tversdk.plfProfiles', 'value', {decode_lzstring},
            {json.loads}, ..., 'member', 'member_sid', {str_or_none}, any))
        if not member_sid:
            self.raise_login_required(
                'Login is required to access TVer My Page')

        playlist_type = self._match_id(url)
        query = traverse_obj(parse_qs(url), (
            'filter', -1, {str}, filter,
        )) or 'all' if playlist_type == 'fav' else None
        playlist_id = join_nonempty(playlist_type, query, delim=':')

        if query == 'channel':
            channels = self._call_api(
                'user', 'v1/favorites/channels',
                None, headers={'X-Member-Sid': member_sid})

            return self.playlist_result([
                self.url_result(f'{self._BASE_URL}/channels/{channel_id}', TVerChannelsIE)
                for channel_id in traverse_obj(channels, (
                    'channels', ..., 'url_key', {str_or_none},
                ))
            ], playlist_id)

            return self.playlist_result(self._entries(channels), playlist_id)

        fav_keys = (...,) if query == 'all' else (..., 'favorite')
        endpoint, keys, require_data = {
            'fav': (f'v2/callMylistDetail/{int(time.time())}', fav_keys, 'mylist'),
            'later': ('v2/callMyLater', (...,), 'later'),
            'resume': ('v2/callMyResume', (...,), 'resume'),
        }[playlist_type]
        result = self._call_api(
            'member', endpoint, None, query=filter_dict({
                'filter': query,
                'member_sid': member_sid,
                'require_data': require_data,
            }))['result']

        return self.playlist_result(self._entries(result, keys), playlist_id)


class TVerOlympicIE(StreaksBaseIE):
    IE_NAME = 'tver:olympic'

    _API_BASE = 'https://olympic-data.tver.jp/api'
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/olympic/milanocortina2026/(?P<type>live|video)/play/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://tver.jp/olympic/milanocortina2026/video/play/3b1d4462150b42558d9cc8aabb5238d0/',
        'info_dict': {
            'id': '3b1d4462150b42558d9cc8aabb5238d0',
            'ext': 'mp4',
            'title': '【開会式】ぎゅっと凝縮ハイライト',
            'display_id': 'ref:3b1d4462150b42558d9cc8aabb5238d0',
            'duration': 712.045,
            'live_status': 'not_live',
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'tags': 'count:1',
            'thumbnail': r're:https://.+\.(?:jpg|png)',
            'timestamp': 1770420187,
            'upload_date': '20260206',
            'uploader_id': 'tver-olympic',
        },
    }, {
        'url': 'https://tver.jp/olympic/milanocortina2026/live/play/glts313itwvj/',
        'info_dict': {
            'id': 'glts313itwvj',
            'ext': 'mp4',
            'title': '開会式ハイライト',
            'channel_id': 'ntv',
            'display_id': 'ref:sp_260207_spc_01_dvr',
            'duration': 7680,
            'live_status': 'was_live',
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'thumbnail': r're:https://.+\.(?:jpg|png)',
            'timestamp': 1770420300,
            'upload_date': '20260206',
            'uploader_id': 'tver-olympic-live',
        },
    }]

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).group('type', 'id')
        live_from_start = self.get_param('live_from_start')

        if video_type == 'live':
            project_id = 'tver-olympic-live'
            api_key = 'a35ebb1ca7d443758dc7fcc5d99b1f72'
            olympic_data = traverse_obj(self._download_json(
                f'{self._API_BASE}/live/{video_id}', video_id), ('contents', 'live', {dict}))
            media_id = traverse_obj(olympic_data, ('video_id', {str}))

            now = time_seconds()
            start_timestamp_str = traverse_obj(olympic_data, ('onair_start_date', {str}))
            start_timestamp = unified_timestamp(start_timestamp_str, tz_offset=9)
            if not start_timestamp:
                raise ExtractorError('Unable to extract on-air start time')
            end_timestamp = traverse_obj(olympic_data, (
                'onair_end_date', {unified_timestamp(tz_offset=9)}, {require('on-air end time')}))

            if now < start_timestamp:
                self.raise_no_formats(
                    f'This program is scheduled to start at {start_timestamp_str} JST', expected=True)

                return {
                    'id': video_id,
                    'live_status': 'is_upcoming',
                    'release_timestamp': start_timestamp,
                }
            elif start_timestamp <= now < end_timestamp:
                live_status = 'is_live'
                if live_from_start:
                    media_id += '_dvr'
            elif end_timestamp <= now:
                dvr_end_timestamp = traverse_obj(olympic_data, (
                    'dvr_end_date', {unified_timestamp(tz_offset=9)}))
                if dvr_end_timestamp and now < dvr_end_timestamp:
                    live_status = 'was_live'
                    media_id += '_dvr'
                else:
                    raise ExtractorError(
                        'This program is no longer available', expected=True)
        else:
            project_id = 'tver-olympic'
            api_key = '4b55a4db3cce4ad38df6dd8543e3e46a'
            media_id = video_id
            live_status = 'not_live'
            olympic_data = traverse_obj(self._download_json(
                f'{self._API_BASE}/video/{video_id}', video_id), ('contents', 'video', {dict}))

        return {
            **self._extract_from_streaks_api(project_id, f'ref:{media_id}', {
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
                'X-Streaks-Api-Key': api_key,
            }, live_from_start=live_from_start),
            **traverse_obj(olympic_data, {
                'title': ('title', {clean_html}, filter),
                'alt_title': ('sub_title', {clean_html}, filter),
                'channel': ('channel', {clean_html}, filter),
                'channel_id': ('channel_id', {clean_html}, filter),
                'description': (('description', 'description_l', 'description_s'), {clean_html}, filter, any),
                'timestamp': ('onair_start_date', {unified_timestamp(tz_offset=9)}),
                'thumbnail': (('picture_l_url', 'picture_m_url', 'picture_s_url'), {url_or_none}, any),
            }),
            'id': video_id,
            'live_status': live_status,
        }

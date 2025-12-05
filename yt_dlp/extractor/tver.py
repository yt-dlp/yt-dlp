import datetime as dt
import urllib.parse

from .streaks import StreaksBaseIE
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    clean_html,
    int_or_none,
    make_archive_id,
    parse_qs,
    str_or_none,
    time_seconds,
)
from ..utils.traversal import (
    require,
    traverse_obj,
    trim_str,
)


class TVerBaseIE(StreaksBaseIE):
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['JP']
    _HEADERS = {
        'Origin': 'https://tver.jp',
        'Referer': 'https://tver.jp/',
    }
    _PLATFORM_QUERY = {}
    _STREAKS_API_INFO = {}

    def _real_initialize(self):
        session_info = self._download_json(
            'https://platform-api.tver.jp/v2/api/platform_users/browser/create',
            None, 'Creating session', data=b'device_type=pc')
        self._PLATFORM_QUERY = traverse_obj(session_info, ('result', {
            'platform_token': 'platform_token',
            'platform_uid': 'platform_uid',
        }))
        self._STREAKS_API_INFO = self._download_json(
            'https://player.tver.jp/player/streaks_info_v2.json', None,
            'Downloading STREAKS API info', 'Unable to download STREAKS API info')

    def _call_api(self, api_type, path, video_id, fatal=False, query=None, **kwargs):
        api_base = {
            'platform': 'https://platform-api.tver.jp/service',
            'service': 'https://service-api.tver.jp',
        }.get(api_type)

        return self._download_json(
            f'{api_base}/api/{path}{f"/{video_id}" if video_id else ""}',
            video_id, fatal=fatal, headers={'x-tver-platform-type': 'web'},
            query={**self._PLATFORM_QUERY, **(query or {})}, **kwargs)

    @staticmethod
    def _thumbnails(content_type, video_id):
        return [{
            'id': quality,
            'url': f'https://statics.tver.jp/images/content/thumbnail/{content_type}/{quality}/{video_id}.jpg',
            'width': width,
            'height': height,
        } for quality, width, height in [
            ('small', 480, 270),
            ('medium', 640, 360),
            ('large', 960, 540),
            ('xlarge', 1280, 720),
        ]]

    @staticmethod
    def _parse_tver_metadata(json_data):
        return traverse_obj(json_data, {
            'id': ('id', {str_or_none}),
            'title': ('title', {clean_html}),
            'alt_title': ('broadcastDateLabel', {clean_html}, filter),
            'channel': ('broadcastProviderLabel', {clean_html}),
            'channel_id': (('broadcastChannelID', 'broadcastProviderID'), {str_or_none}, any),
            'description': ('description', {clean_html}, filter),
            'episode': ('title', {clean_html}),
            'episode_id': ('id', {str_or_none}),
            'episode_number': ('no', {int_or_none}),
            'release_timestamp': ('viewStatus', 'startAt', {int_or_none}),
            'season_id': ('seasonID', {str_or_none}),
            'series': ('share', 'text', {trim_str(end='\n#TVer')}),
            'series_id': ('seriesID', {str_or_none}),
            'tags': ('tags', ..., 'name', {clean_html}, filter, all, filter),
        })


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
            'display_id': 'e85df0d0d6e94b708239803595ca3d29',
            'duration': 647.48,
            'episode': '【なるほどッ！】絶景から穴場まで…「温泉総選挙」人気は？',
            'episode_id': 'epjmuz7b1r',
            'episode_number': 1238,
            'live_status': 'not_live',
            'modified_date': '20251110',
            'modified_timestamp': 1762758822,
            'release_date': '20251110',
            'release_timestamp': 1762804800,
            'season_id': 'sspo4y3d1n',
            'series': '日テレNEWSセレクト',
            'series_id': 'sru578is4n',
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
            if redirect_url == 'https://tver.jp/':
                raise ExtractorError('This URL is currently unavailable', expected=True)
            return self.url_result(redirect_url)

        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id)
        media_id = traverse_obj(video_info, (
            'streaks', ('mediaID', ('videoRefID', {lambda x: f'ref:{x}' if x else None})),
            {str}, filter, any, {require('STREAKS media ID')}))

        brightcove_id = traverse_obj(video_info, (
            'video', 'videoRefID', {lambda x: f'ref:{x}' if x else None}, {str}, filter))
        project_id = video_info['streaks']['projectID']
        key_idx = dt.datetime.fromtimestamp(time_seconds(hours=9), dt.timezone.utc).month % 6 or 6

        try:
            streaks_info = self._extract_from_streaks_api(project_id, media_id, {
                **self._HEADERS,
                'X-Streaks-Api-Key': self._STREAKS_API_INFO[project_id]['api_key'][f'key0{key_idx}'],
            })
        except GeoRestrictedError as e:
            # Catch and re-raise with metadata_available to support --ignore-no-formats-error
            self.raise_geo_restricted(e.orig_msg, countries=self._GEO_COUNTRIES, metadata_available=True)
            streaks_info = {}

        return {
            **streaks_info,
            **self._parse_tver_metadata(video_info),
            'thumbnails': self._thumbnails('episode', video_id),
            '_old_archive_ids': [make_archive_id('BrightcoveNew', brightcove_id)] if brightcove_id else None,
        }


class TVerPlaylistBaseIE(TVerBaseIE):
    def _entries(self, playlist_info, keys):
        types = {
            'episode': ('episodes', TVerIE),
            'series': ('series', TVerPlaylistIE),
        }

        for item in traverse_obj(playlist_info, (
            'result', 'contents', *keys, all, lambda _, v: v['type'] != 'live',
        )):
            path, ie = types.get(item['type'])
            yield self.url_result(
                f'https://tver.jp/{path}/{item["content"]["id"]}', ie)


class TVerPlaylistIE(TVerPlaylistBaseIE):
    IE_NAME = 'tver:playlist'

    _VALID_URL = r'https?://tver\.jp/(?P<type>{})(?:/(?P<id>[\w-]+))?(?:/episodes)?'.format(
        '|'.join(('ender', 'newer', 'series', 'rankings/episode', r'specials/[\w-]+', 'tags', 'talents', 'topics')))
    _TESTS = [{
        'url': 'https://tver.jp/series/srqbg9lpzc',
        'info_dict': {
            'id': 'srqbg9lpzc',
        },
        'playlist_mincount': 17,
    }, {
        'url': 'https://tver.jp/rankings/episode/drama',
        'info_dict': {
            'id': 'drama',
        },
        'playlist_count': 50,
    }, {
        'url': 'https://tver.jp/ender/anime',
        'info_dict': {
            'id': 'anime',
        },
        'playlist_count': 100,
    }]

    def _real_extract(self, url):
        playlist_type, playlist_id = self._match_valid_url(url).group('type', 'id')

        api_type, endpoint, keys = {
            'series': ('platform', 'v1/callSeriesEpisodes', (..., 'contents', ...)),
            'specials': ('platform', 'v1/callSpecialContentsDetail', ('content', 'contents')),
            'tags': ('platform', 'v1/callTagSearch', (...,)),
            'talents': ('platform', 'v1/callTalentEpisode', (...,)),
            'ender': ('service', f'v1/callEnderDetail{"/all" * (not playlist_id)}', ('contents', ...)),
            'newer': ('service', f'v1/callNewerDetail{"/all" * (not playlist_id)}', ('contents', ...)),
            'rankings': ('service', 'v1/callEpisodeRankingDetail', ('contents', ...)),
            'topics': ('service', 'v1/callTopics', (..., 'content', 'content')),
        }[playlist_type.split('/')[0]]
        playlist_info = self._call_api(api_type, endpoint, playlist_id)

        return self.playlist_result(
            self._entries(playlist_info, keys), playlist_id or playlist_type)


class TVerSearchIE(TVerPlaylistBaseIE):
    IE_NAME = 'tver:search'

    _VALID_URL = r'https?://(?:www\.)?tver\.jp/search/(?P<id>[^\?]+)(?:\?|$)'
    _TESTS = [{
        'url': 'https://tver.jp/search/%E3%83%A9%E3%83%B4%E3%82%A3%E3%83%83%E3%83%88%EF%BC%81',
        'info_dict': {
            'id': 'ラヴィット！',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://tver.jp/search/%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9?genre=news_documentary&weekday=mon&tvnetwork=jnn',
        'info_dict': {
            'id': 'ニュース',
        },
        'playlist_mincount': 57,
    }]

    def _real_extract(self, url):
        keyword = urllib.parse.unquote(self._match_id(url))
        playlist_info = self._call_api(
            'platform', 'v2/callKeywordSearch', None, query={
                'filterKey': ','.join(v[0].replace(' ', ',') for v in parse_qs(url).values()),
                'keyword': keyword,
            })

        return self.playlist_result(self._entries(playlist_info, (...,)), keyword)

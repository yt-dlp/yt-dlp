from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    join_nonempty,
    smuggle_url,
    str_or_none,
    strip_or_none,
    traverse_obj,
    update_url_query,
)


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?:(?P<type>lp|corner|series|episodes?|feature)/)+(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'skip': 'videos are only available for 7 days',
        'url': 'https://tver.jp/episodes/ep83nf3w4p',
        'info_dict': {
            'title': '家事ヤロウ!!! 売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！',
            'description': 'md5:dc2c06b6acc23f1e7c730c513737719b',
            'series': '家事ヤロウ!!!',
            'episode': '売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！',
            'alt_title': '売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！',
            'channel': 'テレビ朝日',
            'id': 'ep83nf3w4p',
            'ext': 'mp4',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'url': 'https://tver.jp/corner/f0103888',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/lp/f0033031',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/series/srtxft431v',
        'info_dict': {
            'id': 'srtxft431v',
            'title': '名探偵コナン',
        },
        'playlist': [
            {
                'md5': '779ffd97493ed59b0a6277ea726b389e',
                'info_dict': {
                    'id': 'ref:conan-1137-241005',
                    'ext': 'mp4',
                    'title': '名探偵コナン #1137「行列店、味変の秘密」',
                    'uploader_id': '5330942432001',
                    'tags': [],
                    'channel': '読売テレビ',
                    'series': '名探偵コナン',
                    'description': 'md5:601fccc1d2430d942a2c8068c4b33eb5',
                    'episode': '#1137「行列店、味変の秘密」',
                    'duration': 1469.077,
                    'timestamp': 1728030405,
                    'upload_date': '20241004',
                    'alt_title': '名探偵コナン #1137「行列店、味変の秘密」 読売テレビ 10月5日(土)放送分',
                    'thumbnail': r're:https://.+\.jpg',
                },
            }],
    }, {
        'url': 'https://tver.jp/series/sru35hwdd2',
        'info_dict': {
            'id': 'sru35hwdd2',
            'title': '神回だけ見せます！',
        },
        'playlist_count': 11,
    }, {
        'url': 'https://tver.jp/series/srkq2shp9d',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _HEADERS = {'x-tver-platform-type': 'web'}
    _PLATFORM_QUERY = {}

    def _real_initialize(self):
        session_info = self._download_json(
            'https://platform-api.tver.jp/v2/api/platform_users/browser/create',
            None, 'Creating session', data=b'device_type=pc')
        self._PLATFORM_QUERY = traverse_obj(session_info, ('result', {
            'platform_uid': 'platform_uid',
            'platform_token': 'platform_token',
        }))

    def _call_platform_api(self, path, video_id, note=None, fatal=True, query=None):
        return self._download_json(
            f'https://platform-api.tver.jp/service/api/{path}', video_id, note,
            fatal=fatal, headers=self._HEADERS, query={
                **self._PLATFORM_QUERY,
                **(query or {}),
            })

    def _yield_episode_ids_for_series(self, series_id):
        seasons_info = self._download_json(
            f'https://service-api.tver.jp/api/v1/callSeriesSeasons/{series_id}',
            series_id, 'Downloading seasons info', headers=self._HEADERS)
        for season_id in traverse_obj(
                seasons_info, ('result', 'contents', lambda _, v: v['type'] == 'season', 'content', 'id', {str})):
            episodes_info = self._call_platform_api(
                f'v1/callSeasonEpisodes/{season_id}', series_id, f'Downloading season {season_id} episodes info')
            yield from traverse_obj(episodes_info, (
                'result', 'contents', lambda _, v: v['type'] == 'episode', 'content', 'id', {str}))

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')

        if video_type == 'series':
            series_info = self._call_platform_api(
                f'v2/callSeries/{video_id}', video_id, 'Downloading series info')
            return self.playlist_from_matches(
                self._yield_episode_ids_for_series(video_id), video_id,
                traverse_obj(series_info, ('result', 'content', 'content', 'title', {str})),
                ie=TVerIE, getter=lambda x: f'https://tver.jp/episodes/{x}')

        if video_type != 'episodes':
            webpage = self._download_webpage(url, video_id, note='Resolving to new URL')
            video_id = self._match_id(self._search_regex(
                (r'canonical"\s*href="(https?://tver\.jp/[^"]+)"', r'&link=(https?://tver\.jp/[^?&]+)[?&]'),
                webpage, 'url regex'))

        episode_info = self._call_platform_api(
            f'v1/callEpisode/{video_id}', video_id, 'Downloading episode info', fatal=False, query={
                'require_data': 'mylist,later[epefy106ur],good[epefy106ur],resume[epefy106ur]',
            })
        episode_content = traverse_obj(
            episode_info, ('result', 'episode', 'content')) or {}

        version = traverse_obj(episode_content, ('version', {str_or_none}), default='5')
        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id, 'Downloading video info',
            query={'v': version}, headers={'Referer': 'https://tver.jp/'})
        p_id = video_info['video']['accountID']
        r_id = traverse_obj(video_info, ('video', ('videoRefID', 'videoID')), get_all=False)
        if not r_id:
            raise ExtractorError('Failed to extract reference ID for Brightcove')
        if not r_id.isdigit():
            r_id = f'ref:{r_id}'

        episode = strip_or_none(episode_content.get('title'))
        series = str_or_none(episode_content.get('seriesTitle'))
        title = (
            join_nonempty(series, episode, delim=' ')
            or str_or_none(video_info.get('title')))
        provider = str_or_none(episode_content.get('productionProviderName'))
        onair_label = str_or_none(episode_content.get('broadcastDateLabel'))

        thumbnails = [
            {
                'id': quality,
                'url': update_url_query(
                    f'https://statics.tver.jp/images/content/thumbnail/episode/{quality}/{video_id}.jpg',
                    {'v': version}),
                'width': width,
                'height': height,
            }
            for quality, width, height in [
                ('small', 480, 270),
                ('medium', 640, 360),
                ('large', 960, 540),
                ('xlarge', 1280, 720),
            ]
        ]

        return {
            '_type': 'url_transparent',
            'title': title,
            'series': series,
            'episode': episode,
            # an another title which is considered "full title" for some viewers
            'alt_title': join_nonempty(title, provider, onair_label, delim=' '),
            'channel': provider,
            'description': str_or_none(video_info.get('description')),
            'thumbnails': thumbnails,
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id), {'geo_countries': ['JP']}),
            'ie_key': 'BrightcoveNew',
        }

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    join_nonempty,
    smuggle_url,
    str_or_none,
    strip_or_none,
    traverse_obj,
)


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?:(?P<type>lp|corner|series|episodes?|feature|tokyo2020/video)/)+(?P<id>[a-zA-Z0-9]+)'
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
        'url': 'https://tver.jp/series/srkq2shp9d',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _PLATFORM_UID = None
    _PLATFORM_TOKEN = None

    def _real_initialize(self):
        create_response = self._download_json(
            'https://platform-api.tver.jp/v2/api/platform_users/browser/create', None,
            note='Creating session', data=b'device_type=pc', headers={
                'Origin': 'https://s.tver.jp',
                'Referer': 'https://s.tver.jp/',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        self._PLATFORM_UID = traverse_obj(create_response, ('result', 'platform_uid'))
        self._PLATFORM_TOKEN = traverse_obj(create_response, ('result', 'platform_token'))

    def _entries(self, series_id):
        season_json = self._download_json(f'https://service-api.tver.jp/api/v1/callSeriesSeasons/{series_id}', series_id, headers={'x-tver-platform-type': 'web'})
        seasons = traverse_obj(season_json, ('result', 'contents', lambda _, s: s['type'] == 'season', 'content', 'id'), default=[])
        for season_id in seasons:
            episode_json = self._download_json(
                f'https://platform-api.tver.jp/service/api/v1/callSeasonEpisodes/{season_id}',
                season_id,
                headers={'x-tver-platform-type': 'web'},
                query={
                    'platform_uid': self._PLATFORM_UID,
                    'platform_token': self._PLATFORM_TOKEN,
                },
            )
            episodes = traverse_obj(episode_json, ('result', 'contents', lambda _, e: e['type'] == 'episode', 'content', 'id'), default=[])
            for video_id in episodes:
                yield self.url_result(f'https://tver.jp/episodes/{video_id}', TVerIE, video_id)

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')

        if video_type == 'series':
            return self.playlist_result(self._entries(video_id), video_id)

        if video_type not in {'series', 'episodes'}:
            webpage = self._download_webpage(url, video_id, note='Resolving to new URL')
            video_id = self._match_id(self._search_regex(
                (r'canonical"\s*href="(https?://tver\.jp/[^"]+)"', r'&link=(https?://tver\.jp/[^?&]+)[?&]'),
                webpage, 'url regex'))

        episode_info = self._download_json(
            f'https://platform-api.tver.jp/service/api/v1/callEpisode/{video_id}?require_data=mylist,later[epefy106ur],good[epefy106ur],resume[epefy106ur]',
            video_id, fatal=False,
            query={
                'platform_uid': self._PLATFORM_UID,
                'platform_token': self._PLATFORM_TOKEN,
            }, headers={
                'x-tver-platform-type': 'web'
            })
        episode_content = traverse_obj(
            episode_info, ('result', 'episode', 'content')) or {}

        version = str_or_none(episode_content.get('version')) or '5'
        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id,
            query={
                'v': version,
            },
            headers={
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
            })
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
                'url': f'https://statics.tver.jp/images/content/thumbnail/episode/{quality}/{video_id}.jpg?v={version}',
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

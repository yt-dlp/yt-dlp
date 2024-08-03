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
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?:(?P<type>lp|corner|series|episodes?|feature|tokyo2020/video|olympic/paris2024/video)/)+(?P<id>[a-zA-Z0-9]+)'
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
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'url': 'https://tver.jp/olympic/paris2024/video/6359578055112/',
        'info_dict': {
            'id': '6359578055112',
            'ext': 'mp4',
            'title': '堀米雄斗 金メダルで五輪連覇！「みんなの応援が最後に乗れたカギ」',
            'timestamp': 1722279928,
            'upload_date': '20240729',
            'tags': ['20240729', 'japanese', 'japanmedal', 'paris'],
            'uploader_id': '4774017240001',
            'thumbnail': r're:https?://[^/?#]+boltdns\.net/[^?#]+/1920x1080/match/image\.jpg',
            'duration': 670.571,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://tver.jp/corner/f0103888',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/lp/f0033031',
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

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')

        if video_type == 'olympic/paris2024/video':
            # Player ID is taken from .content.brightcove.E200.pro.pc.account_id:
            # https://tver.jp/olympic/paris2024/req/api/hook?q=https%3A%2F%2Folympic-assets.tver.jp%2Fweb-static%2Fjson%2Fconfig.json&d=
            return self.url_result(smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % ('4774017240001', video_id),
                {'geo_countries': ['JP']}), 'BrightcoveNew')

        elif video_type not in {'series', 'episodes'}:
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
                'x-tver-platform-type': 'web',
            })
        episode_content = traverse_obj(
            episode_info, ('result', 'episode', 'content')) or {}

        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id,
            query={
                'v': str_or_none(episode_content.get('version')) or '5',
            }, headers={
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

        return {
            '_type': 'url_transparent',
            'title': title,
            'series': series,
            'episode': episode,
            # an another title which is considered "full title" for some viewers
            'alt_title': join_nonempty(title, provider, onair_label, delim=' '),
            'channel': provider,
            'description': str_or_none(video_info.get('description')),
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id), {'geo_countries': ['JP']}),
            'ie_key': 'BrightcoveNew',
        }

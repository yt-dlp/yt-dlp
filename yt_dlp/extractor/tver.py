# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    smuggle_url,
    str_or_none,
    traverse_obj,
)


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?:(?:lp|corner|series|episodes?|feature|tokyo2020/video)/)+(?P<id>[a-zA-Z0-9]+)'
    # NOTE: episode/ is an old URL
    _NEW_URL_COMPONENT = '|'.join(re.escape(f'/{x}/') for x in ('series', 'episodes'))
    _TESTS = [{
        'skip': 'videos are only available for 7 days',
        'url': 'https://tver.jp/episodes/ephss8yveb',
        'info_dict': {
            'title': '#44　料理と値段と店主にびっくり　オモてなしすぎウマい店　2時間SP',
            'description': '【宮城】極厚とんかつ定食５００円　マル秘女性歌手大ファン店主\n【福岡】学生感動パワー店主！！名物パワー定食って！？\n【埼玉】暴れん坊そば名人！！弟子５０人に！？師弟愛シーズン３',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'skip': 'videos are only available for 7 days',
        'url': 'https://tver.jp/lp/episodes/ep6f16g26p',
        'info_dict': {
            # sorry but this is "correct"
            'title': '4月11日(月)23時06分 ~ 放送予定',
            'description': '吉祥寺の格安シェアハウスに引っ越して来た高校教師の安彦聡（増田貴久）や、元ファッション誌編集長の大庭桜（田中みな実）など6人。鍵が掛かった部屋に絶対入らないことが絶対ルール。奇妙な共同生活が今始まる！　テレビ東京にて4月11日(月)夜11時6分放送スタート！',
        },
        'add_ie': ['BrightcoveNew'],
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
        video_id = self._match_id(url)
        if not re.search(self._NEW_URL_COMPONENT, url):
            webpage = self._download_webpage(
                url, video_id, note='Resolving to new URL')
            video_id = self._match_id(self._search_regex(
                (r'canonical"\s*href="(https?://tver\.jp/.+?)"', r'&link=(https?://tver\.jp/.+?)[?&]'),
                webpage, 'url regex'))
        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id,
            query={'v': '5'}, headers={
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
            })
        p_id = video_info['video']['accountID']
        r_id = traverse_obj(video_info, ('video', ('videoRefID', 'videoID')), get_all=False)
        if not r_id:
            raise ExtractorError('Failed to extract reference ID for Brightcove')
        if not r_id.isdigit():
            r_id = f'ref:{r_id}'

        additional_info = self._download_json(
            f'https://platform-api.tver.jp/service/api/v1/callEpisode/{video_id}?require_data=mylist,later[epefy106ur],good[epefy106ur],resume[epefy106ur]',
            video_id,
            query={
                'platform_uid': self._PLATFORM_UID,
                'platform_token': self._PLATFORM_TOKEN,
            }, headers={
                'x-tver-platform-type': 'web'
            })

        return {
            '_type': 'url_transparent',
            'title': str_or_none(video_info.get('title')),
            'description': str_or_none(video_info.get('description')),
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id), {'geo_countries': ['JP']}),
            'series': traverse_obj(
                additional_info, ('result', ('episode', 'series'), 'content', ('seriesTitle', 'title')),
                get_all=False),
            'ie_key': 'BrightcoveNew',
        }

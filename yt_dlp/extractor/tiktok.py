# coding: utf-8
from __future__ import unicode_literals

import itertools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    try_get
)


class TikTokIE(InfoExtractor):
    _VALID_URL = r'https?://www\.tiktok\.com/@[\w\._]+/video/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.tiktok.com/@leenabhushan/video/6748451240264420610',
        'md5': '34a7543afd5a151b0840ba6736fb633b',
        'info_dict': {
            'id': '6748451240264420610',
            'ext': 'mp4',
            'title': '#jassmanak #lehanga #leenabhushan',
            'description': '#jassmanak #lehanga #leenabhushan',
            'duration': 13,
            'height': 1280,
            'width': 720,
            'uploader': 'leenabhushan',
            'uploader_id': '6691488002098119685',
            'uploader_url': 'https://www.tiktok.com/@leenabhushan',
            'creator': 'facestoriesbyleenabh',
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20191016',
            'timestamp': 1571246252,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.tiktok.com/@patroxofficial/video/6742501081818877190?langCountry=en',
        'md5': '06b9800d47d5fe51a19e322dd86e61c9',
        'info_dict': {
            'id': '6742501081818877190',
            'ext': 'mp4',
            'title': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'description': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'duration': 27,
            'height': 960,
            'width': 540,
            'uploader': 'patrox',
            'uploader_id': '18702747',
            'uploader_url': 'https://www.tiktok.com/@patrox',
            'creator': 'patroX',
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'upload_date': '20190930',
            'timestamp': 1569860870,
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }]

    def _extract_aweme(self, props_data, webpage, url):
        video_info = try_get(
            props_data, lambda x: x['pageProps']['itemInfo']['itemStruct'], dict)
        author_info = try_get(
            props_data, lambda x: x['pageProps']['itemInfo']['itemStruct']['author'], dict) or {}
        stats_info = try_get(props_data, lambda x: x['pageProps']['itemInfo']['itemStruct']['stats'], dict) or {}

        user_id = str_or_none(author_info.get('uniqueId'))
        download_url = try_get(video_info, (lambda x: x['video']['playAddr'],
                                            lambda x: x['video']['downloadAddr']))
        height = try_get(video_info, lambda x: x['video']['height'], int)
        width = try_get(video_info, lambda x: x['video']['width'], int)
        thumbnails = [{
            'url': video_info.get('thumbnail') or self._og_search_thumbnail(webpage),
            'width': width,
            'height': height
        }]
        tracker = try_get(props_data, lambda x: x['initialProps']['$wid'])

        return {
            'id': str_or_none(video_info.get('id')),
            'url': download_url,
            'ext': 'mp4',
            'height': height,
            'width': width,
            'title': video_info.get('desc') or self._og_search_title(webpage),
            'duration': try_get(video_info, lambda x: x['video']['duration'], int),
            'view_count': int_or_none(stats_info.get('playCount')),
            'like_count': int_or_none(stats_info.get('diggCount')),
            'repost_count': int_or_none(stats_info.get('shareCount')),
            'comment_count': int_or_none(stats_info.get('commentCount')),
            'timestamp': try_get(video_info, lambda x: int(x['createTime']), int),
            'creator': str_or_none(author_info.get('nickname')),
            'uploader': user_id,
            'uploader_id': str_or_none(author_info.get('id')),
            'uploader_url': f'https://www.tiktok.com/@{user_id}',
            'thumbnails': thumbnails,
            'description': str_or_none(video_info.get('desc')),
            'webpage_url': self._og_search_url(webpage),
            'http_headers': {
                'Referer': url,
                'Cookie': 'tt_webid=%s; tt_webid_v2=%s' % (tracker, tracker),
            }
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # If we only call once, we get a 403 when downlaoding the video.
        self._download_webpage(url, video_id)
        webpage = self._download_webpage(url, video_id, note='Downloading video webpage')
        json_string = self._search_regex(
            r'id=\"__NEXT_DATA__\"\s+type=\"application\/json\"\s*[^>]+>\s*(?P<json_string_ld>[^<]+)',
            webpage, 'json_string', group='json_string_ld')
        json_data = self._parse_json(json_string, video_id)
        props_data = try_get(json_data, lambda x: x['props'], expected_type=dict)

        # Chech statusCode for success
        status = props_data.get('pageProps').get('statusCode')
        if status == 0:
            return self._extract_aweme(props_data, webpage, url)
        elif status == 10216:
            raise ExtractorError('This video is private', expected=True)

        raise ExtractorError('Video not available', video_id=video_id)


class TikTokUserIE(InfoExtractor):
    IE_NAME = 'tiktok:user'
    _VALID_URL = r'(?!.*/video/)https?://www\.tiktok\.com/@(?P<id>[\w\._]+)'
    _TESTS = [{
        'url': 'https://www.tiktok.com/@corgibobaa?lang=en',
        'playlist_mincount': 45,
        'info_dict': {
            'id': '6935371178089399301',
        },
        'skip': 'Cookies (not necessarily logged in) are needed.'
    }, {
        'url': 'https://www.tiktok.com/@meme',
        'playlist_mincount': 593,
        'info_dict': {
            'id': '79005827461758976',
        },
        'skip': 'Cookies (not necessarily logged in) are needed.'
    }]

    def _entries(self, url, user_id):
        webpage = self._download_webpage(url, user_id)
        own_id = self._search_regex(r'\"id\":\"(?P<userid>\d+)', webpage, user_id, default=None)
        if not own_id:
            raise ExtractorError('Cookies (not necessarily logged in) are needed.', expected=True)
        secuid = self._search_regex(r'\"secUid\":\"(?P<secUid>[^\"]+)', webpage, user_id)
        verifyfp_cookie = self._get_cookies('https://www.tiktok.com').get('s_v_web_id')
        if not verifyfp_cookie:
            raise ExtractorError('Improper cookies (missing s_v_web_id).', expected=True)
        api_url = f'https://m.tiktok.com/api/post/item_list/?aid=1988&cookie_enabled=true&count=30&verifyFp={verifyfp_cookie.value}&secUid={secuid}&cursor='
        cursor = '0'
        for page in itertools.count():
            data_json = self._download_json(api_url + cursor, user_id, note='Downloading Page %d' % page)
            for video in data_json.get('itemList', []):
                video_id = video['id']
                video_url = f'https://www.tiktok.com/@{user_id}/video/{video_id}'
                download_url = try_get(video, (lambda x: x['video']['playAddr'],
                                               lambda x: x['video']['downloadAddr']))
                thumbnail = try_get(video, lambda x: x['video']['originCover'])
                height = try_get(video, lambda x: x['video']['height'], int)
                width = try_get(video, lambda x: x['video']['width'], int)
                yield {
                    'id': video_id,
                    'ie_key': TikTokIE.ie_key(),
                    'extractor': 'TikTok',
                    'url': download_url,
                    'ext': 'mp4',
                    'height': height,
                    'width': width,
                    'title': str_or_none(video.get('desc')),
                    'duration': try_get(video, lambda x: x['video']['duration'], int),
                    'view_count': try_get(video, lambda x: x['stats']['playCount'], int),
                    'like_count': try_get(video, lambda x: x['stats']['diggCount'], int),
                    'comment_count': try_get(video, lambda x: x['stats']['commentCount'], int),
                    'repost_count': try_get(video, lambda x: x['stats']['shareCount'], int),
                    'timestamp': video.get('createTime'),
                    'creator': try_get(video, lambda x: x['author']['nickname'], str),
                    'uploader': try_get(video, lambda x: x['author']['uniqueId'], str),
                    'uploader_id': try_get(video, lambda x: x['author']['id'], str),
                    'uploader_url': f'https://www.tiktok.com/@{user_id}',
                    'thumbnails': [{'url': thumbnail, 'height': height, 'width': width}],
                    'description': str_or_none(video.get('desc')),
                    'webpage_url': video_url,
                    'http_headers': {
                        'Referer': video_url,
                    }
                }
            if not data_json['hasMore']:
                break
            cursor = data_json['cursor']

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self.playlist_result(self._entries(url, user_id), user_id)

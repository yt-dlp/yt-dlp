import base64
import json
import re
import time
import uuid

from .anvato import AnvatoIE
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    get_element_by_class,
    traverse_obj,
    urlencode_postdata,
)


class NFLBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'''(?x)
                    https?://
                        (?P<host>
                            (?:www\.)?
                            (?:
                                (?:
                                    nfl|
                                    buffalobills|
                                    miamidolphins|
                                    patriots|
                                    newyorkjets|
                                    baltimoreravens|
                                    bengals|
                                    clevelandbrowns|
                                    steelers|
                                    houstontexans|
                                    colts|
                                    jaguars|
                                    (?:titansonline|tennesseetitans)|
                                    denverbroncos|
                                    (?:kc)?chiefs|
                                    raiders|
                                    chargers|
                                    dallascowboys|
                                    giants|
                                    philadelphiaeagles|
                                    (?:redskins|washingtonfootball)|
                                    chicagobears|
                                    detroitlions|
                                    packers|
                                    vikings|
                                    atlantafalcons|
                                    panthers|
                                    neworleanssaints|
                                    buccaneers|
                                    azcardinals|
                                    (?:stlouis|the)rams|
                                    49ers|
                                    seahawks
                                )\.com|
                                .+?\.clubs\.nfl\.com
                            )
                        )/
                    '''
    _VIDEO_CONFIG_REGEX = r'<script[^>]+id="[^"]*video-config-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}[^"]*"[^>]*>\s*({.+});?\s*</script>'
    _ANVATO_PREFIX = 'anvato:GXvEgwyJeWem8KCYXfeoHWknwP48Mboj:'

    _CLIENT_DATA = {
        'clientKey': '4cFUW6DmwJpzT9L7LrG3qRAcABG5s04g',
        'clientSecret': 'CZuvCL49d9OwfGsR',
        'deviceId': str(uuid.uuid4()),
        'deviceInfo': base64.b64encode(json.dumps({
            'model': 'desktop',
            'version': 'Chrome',
            'osName': 'Windows',
            'osVersion': '10.0',
        }, separators=(',', ':')).encode()).decode(),
        'networkType': 'other',
        'nflClaimGroupsToAdd': [],
        'nflClaimGroupsToRemove': [],
    }
    _ACCOUNT_INFO = {}
    _API_KEY = None

    _TOKEN = None
    _TOKEN_EXPIRY = 0

    def _get_account_info(self, url, slug):
        if not self._API_KEY:
            webpage = self._download_webpage(url, slug, fatal=False) or ''
            self._API_KEY = self._search_regex(
                r'window\.gigyaApiKey\s*=\s*["\'](\w+)["\'];', webpage, 'API key',
                fatal=False) or '3_Qa8TkWpIB8ESCBT8tY2TukbVKgO5F6BJVc7N1oComdwFzI7H2L9NOWdm11i_BY9f'

        cookies = self._get_cookies('https://auth-id.nfl.com/')
        login_token = traverse_obj(cookies, (
            (f'glt_{self._API_KEY}', lambda k, _: k.startswith('glt_')), {lambda x: x.value}), get_all=False)
        if not login_token:
            self.raise_login_required()
        if 'ucid' not in cookies:
            raise ExtractorError(
                'Required cookies for the auth-id.nfl.com domain were not found among passed cookies. '
                'If using --cookies, these cookies must be exported along with .nfl.com cookies, '
                'or else try using --cookies-from-browser instead', expected=True)

        account = self._download_json(
            'https://auth-id.nfl.com/accounts.getAccountInfo', slug,
            note='Downloading account info', data=urlencode_postdata({
                'include': 'profile,data',
                'lang': 'en',
                'APIKey': self._API_KEY,
                'sdk': 'js_latest',
                'login_token': login_token,
                'authMode': 'cookie',
                'pageURL': url,
                'sdkBuild': traverse_obj(cookies, (
                    'gig_canary_ver', {lambda x: x.value.partition('-')[0]}), default='15170'),
                'format': 'json',
            }), headers={'Content-Type': 'application/x-www-form-urlencoded'})

        self._ACCOUNT_INFO = traverse_obj(account, {
            'signatureTimestamp': 'signatureTimestamp',
            'uid': 'UID',
            'uidSignature': 'UIDSignature',
        })

        if len(self._ACCOUNT_INFO) != 3:
            raise ExtractorError('Failed to retrieve account info with provided cookies', expected=True)

    def _get_auth_token(self, url, slug):
        if self._TOKEN and self._TOKEN_EXPIRY > int(time.time() + 30):
            return

        if not self._ACCOUNT_INFO:
            self._get_account_info(url, slug)

        token = self._download_json(
            'https://api.nfl.com/identity/v3/token%s' % (
                '/refresh' if self._ACCOUNT_INFO.get('refreshToken') else ''),
            slug, headers={'Content-Type': 'application/json'}, note='Downloading access token',
            data=json.dumps({**self._CLIENT_DATA, **self._ACCOUNT_INFO}, separators=(',', ':')).encode())

        self._TOKEN = token['accessToken']
        self._TOKEN_EXPIRY = token['expiresIn']
        self._ACCOUNT_INFO['refreshToken'] = token['refreshToken']

    def _parse_video_config(self, video_config, display_id):
        video_config = self._parse_json(video_config, display_id)
        item = video_config['playlist'][0]
        mcp_id = item.get('mcpID')
        if mcp_id:
            info = self.url_result(f'{self._ANVATO_PREFIX}{mcp_id}', AnvatoIE, mcp_id)
        else:
            media_id = item.get('id') or item['entityId']
            title = item.get('title')
            item_url = item['url']
            info = {'id': media_id}
            ext = determine_ext(item_url)
            if ext == 'm3u8':
                info['formats'] = self._extract_m3u8_formats(item_url, media_id, 'mp4')
            else:
                info['url'] = item_url
                if item.get('audio') is True:
                    info['vcodec'] = 'none'
            is_live = video_config.get('live') is True
            thumbnails = None
            image_url = item.get(item.get('imageSrc')) or item.get(item.get('posterImage'))
            if image_url:
                thumbnails = [{
                    'url': image_url,
                    'ext': determine_ext(image_url, 'jpg'),
                }]
            info.update({
                'title': title,
                'is_live': is_live,
                'description': clean_html(item.get('description')),
                'thumbnails': thumbnails,
            })
        return info


class NFLIE(NFLBaseIE):
    IE_NAME = 'nfl.com'
    _VALID_URL = NFLBaseIE._VALID_URL_BASE + r'(?:videos?|listen|audio)/(?P<id>[^/#?&]+)'
    _TESTS = [{
        'url': 'https://www.nfl.com/videos/baker-mayfield-s-game-changing-plays-from-3-td-game-week-14',
        'info_dict': {
            'id': '899441',
            'ext': 'mp4',
            'title': "Baker Mayfield's game-changing plays from 3-TD game Week 14",
            'description': 'md5:85e05a3cc163f8c344340f220521136d',
            'upload_date': '20201215',
            'timestamp': 1608009755,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'NFL',
            'tags': 'count:6',
            'duration': 157,
            'categories': 'count:3',
        }
    }, {
        'url': 'https://www.chiefs.com/listen/patrick-mahomes-travis-kelce-react-to-win-over-dolphins-the-breakdown',
        'md5': '6886b32c24b463038c760ceb55a34566',
        'info_dict': {
            'id': 'd87e8790-3e14-11eb-8ceb-ff05c2867f99',
            'ext': 'mp3',
            'title': 'Patrick Mahomes, Travis Kelce React to Win Over Dolphins | The Breakdown',
            'description': 'md5:12ada8ee70e6762658c30e223e095075',
        },
        'skip': 'HTTP Error 404: Not Found',
    }, {
        'url': 'https://www.buffalobills.com/video/buffalo-bills-military-recognition-week-14',
        'only_matching': True,
    }, {
        'url': 'https://www.raiders.com/audio/instant-reactions-raiders-week-14-loss-to-indianapolis-colts-espn-jason-fitz',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        return self._parse_video_config(self._search_regex(
            self._VIDEO_CONFIG_REGEX, webpage, 'video config'), display_id)


class NFLArticleIE(NFLBaseIE):
    IE_NAME = 'nfl.com:article'
    _VALID_URL = NFLBaseIE._VALID_URL_BASE + r'news/(?P<id>[^/#?&]+)'
    _TEST = {
        'url': 'https://www.buffalobills.com/news/the-only-thing-we-ve-earned-is-the-noise-bills-coaches-discuss-handling-rising-e',
        'info_dict': {
            'id': 'the-only-thing-we-ve-earned-is-the-noise-bills-coaches-discuss-handling-rising-e',
            'title': "'The only thing we've earned is the noise' | Bills coaches discuss handling rising expectations",
        },
        'playlist_count': 4,
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        entries = []
        for video_config in re.findall(self._VIDEO_CONFIG_REGEX, webpage):
            entries.append(self._parse_video_config(video_config, display_id))
        title = clean_html(get_element_by_class(
            'nfl-c-article__title', webpage)) or self._html_search_meta(
            ['og:title', 'twitter:title'], webpage)
        return self.playlist_result(entries, display_id, title)


class NFLPlusReplayIE(NFLBaseIE):
    IE_NAME = 'nfl.com:plus:replay'
    _VALID_URL = r'https?://(?:www\.)?nfl\.com/plus/games/(?P<slug>[\w-]+)(?:/(?P<id>\d+))?'
    _TESTS = [{
        'url': 'https://www.nfl.com/plus/games/giants-at-vikings-2022-post-1/1572108',
        'info_dict': {
            'id': '1572108',
            'ext': 'mp4',
            'title': 'New York Giants at Minnesota Vikings',
            'description': 'New York Giants play the Minnesota Vikings at U.S. Bank Stadium on January 15, 2023',
            'uploader': 'NFL',
            'upload_date': '20230116',
            'timestamp': 1673864520,
            'duration': 7157,
            'categories': ['Game Highlights'],
            'tags': ['Minnesota Vikings', 'New York Giants', 'Minnesota Vikings vs. New York Giants'],
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Subscription required',
        'url': 'https://www.nfl.com/plus/games/giants-at-vikings-2022-post-1',
        'playlist_count': 4,
        'info_dict': {
            'id': 'giants-at-vikings-2022-post-1',
        },
    }, {
        'note': 'Subscription required',
        'url': 'https://www.nfl.com/plus/games/giants-at-patriots-2011-pre-4',
        'playlist_count': 2,
        'info_dict': {
            'id': 'giants-at-patriots-2011-pre-4',
        },
    }, {
        'note': 'Subscription required',
        'url': 'https://www.nfl.com/plus/games/giants-at-patriots-2011-pre-4',
        'info_dict': {
            'id': '950701',
            'ext': 'mp4',
            'title': 'Giants @ Patriots',
            'description': 'Giants at Patriots on September 01, 2011',
            'uploader': 'NFL',
            'upload_date': '20210724',
            'timestamp': 1627085874,
            'duration': 1532,
            'categories': ['Game Highlights'],
            'tags': ['play-by-play'],
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {
            'skip_download': 'm3u8',
            'extractor_args': {'nflplusreplay': {'type': ['condensed_game']}},
        },
    }]

    _REPLAY_TYPES = {
        'full_game': 'Full Game',
        'full_game_spanish': 'Full Game - Spanish',
        'condensed_game': 'Condensed Game',
        'all_22': 'All-22',
    }

    def _real_extract(self, url):
        slug, video_id = self._match_valid_url(url).group('slug', 'id')
        requested_types = self._configuration_arg('type', ['all'])
        if 'all' in requested_types:
            requested_types = list(self._REPLAY_TYPES.keys())
        requested_types = traverse_obj(self._REPLAY_TYPES, (None, requested_types))

        if not video_id:
            self._get_auth_token(url, slug)
            headers = {'Authorization': f'Bearer {self._TOKEN}'}
            game_id = self._download_json(
                f'https://api.nfl.com/football/v2/games/externalId/slug/{slug}', slug,
                'Downloading game ID', query={'withExternalIds': 'true'}, headers=headers)['id']
            replays = self._download_json(
                'https://api.nfl.com/content/v1/videos/replays', slug, 'Downloading replays JSON',
                query={'gameId': game_id}, headers=headers)
            if len(requested_types) == 1:
                video_id = traverse_obj(replays, (
                    'items', lambda _, v: v['subType'] == requested_types[0], 'mcpPlaybackId'), get_all=False)

        if video_id:
            return self.url_result(f'{self._ANVATO_PREFIX}{video_id}', AnvatoIE, video_id)

        def entries():
            for replay in traverse_obj(
                replays, ('items', lambda _, v: v['mcpPlaybackId'] and v['subType'] in requested_types)
            ):
                video_id = replay['mcpPlaybackId']
                yield self.url_result(f'{self._ANVATO_PREFIX}{video_id}', AnvatoIE, video_id)

        return self.playlist_result(entries(), slug)


class NFLPlusEpisodeIE(NFLBaseIE):
    IE_NAME = 'nfl.com:plus:episode'
    _VALID_URL = r'https?://(?:www\.)?nfl\.com/plus/episodes/(?P<id>[\w-]+)'
    _TESTS = [{
        'note': 'Subscription required',
        'url': 'https://www.nfl.com/plus/episodes/kurt-s-qb-insider-conference-championships',
        'info_dict': {
            'id': '1576832',
            'ext': 'mp4',
            'title': 'Conference Championships',
            'description': 'md5:944f7fab56f7a37430bf8473f5473857',
            'uploader': 'NFL',
            'upload_date': '20230127',
            'timestamp': 1674782760,
            'duration': 730,
            'categories': ['Analysis'],
            'tags': ['Cincinnati Bengals at Kansas City Chiefs (2022-POST-3)'],
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        self._get_auth_token(url, slug)
        video_id = self._download_json(
            f'https://api.nfl.com/content/v1/videos/episodes/{slug}', slug, headers={
                'Authorization': f'Bearer {self._TOKEN}',
            })['mcpPlaybackId']

        return self.url_result(f'{self._ANVATO_PREFIX}{video_id}', AnvatoIE, video_id)

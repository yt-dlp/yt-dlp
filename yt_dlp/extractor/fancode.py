from .common import InfoExtractor

from ..compat import compat_str
from ..utils import (
    parse_iso8601,
    ExtractorError,
    try_get,
    mimetype2ext
)


class FancodeVodIE(InfoExtractor):
    _WORKING = False
    IE_NAME = 'fancode:vod'

    _VALID_URL = r'https?://(?:www\.)?fancode\.com(?:/[a-zA-Z0-9].*)?/videos?/(?:(?:[^/])*?/)?(?P<id>[0-9]+)\b'

    _TESTS = [{
        'url': 'https://fancode.com/video/15043/match-preview-pbks-vs-mi',
        'only_matching': True
    }, {
        'url': 'https://fancode.com/video/15043',
        'only_matching': True,
    }, {
        'url': 'https://www.fancode.com/cricket/videos/thriller-india-fightback-to-clinch-2wicket-win/35441',
        'params': {
            'skip_download': True,
        },
        'info_dict': {
            'id': '35441',
            'ext': 'mp4',
            'title': 'Thriller! India fightback to clinch 2-wicket win',
            'view_count': int,
            'like_count': int,
            'release_timestamp': 1658702382,
            'tags': list,
            'release_date': '20220724'
        }
    }]

    _ACCESS_TOKEN = None
    _NETRC_MACHINE = 'fancode'

    _LOGIN_HINT = 'Use "--username refresh --password <refresh_token>" to login using a refresh token'

    headers = {
        'content-type': 'application/json',
        'origin': 'https://fancode.com',
        'referer': 'https://fancode.com',
    }

    def _perform_login(self, username, password):
        # Access tokens are shortlived, so get them using the refresh token.
        if username != 'refresh':
            self.report_warning(f'Login using username and password is not currently supported. {self._LOGIN_HINT}')

        self.report_login()
        data = '''{
            "query":"mutation RefreshToken($refreshToken: String\\u0021) { refreshToken(refreshToken: $refreshToken) { accessToken }}",
            "variables":{
                "refreshToken":"%s"
            },
            "operationName":"RefreshToken"
        }''' % password

        token_json = self.download_gql('refresh token', data, "Getting the Access token")
        self._ACCESS_TOKEN = try_get(token_json, lambda x: x['data']['refreshToken']['accessToken'])
        if self._ACCESS_TOKEN is None:
            self.report_warning('Failed to get Access token')
        else:
            self.headers.update({'Authorization': 'Bearer %s' % self._ACCESS_TOKEN})

    def _check_login_required(self, is_available, is_premium):
        msg = None
        if is_premium and self._ACCESS_TOKEN is None:
            msg = f'This video is only available for registered users. {self._LOGIN_HINT}'
        elif not is_available and self._ACCESS_TOKEN is not None:
            msg = 'This video isn\'t available to the current logged in account'
        if msg:
            self.raise_login_required(msg, metadata_available=True, method=None)

    def download_gql(self, variable, data, note, fatal=False, headers=headers):
        return self._download_json(
            'https://www.fancode.com/graphql', variable,
            data=data.encode(), note=note,
            headers=headers, fatal=fatal)

    def _real_extract(self, url):

        BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/%s/default_default/index.html?videoId=%s'
        video_id = self._match_id(url)

        brightcove_user_id = '6008340455001'
        data = '''{
            "query":"query Video($id: Int\\u0021, $filter: SegmentFilter) { media(id: $id, filter: $filter) { id contentId title contentId publishedTime totalViews totalUpvotes provider thumbnail { src } mediaSource {brightcove } duration isPremium source {url} isUserEntitled tags duration }}",
            "variables":{
                "id":%s,
                "filter":{
                    "contentDataType":"DEFAULT"
                }
            },
            "operationName":"Video"
        }''' % video_id

        metadata_json = self.download_gql(video_id, data, note='Downloading metadata')

        media = try_get(metadata_json, lambda x: x['data']['media'], dict) or {}
        source_url = try_get(media, lambda x: x['source']['url'])
        brightcove_video_id = try_get(media, lambda x: x['mediaSource']['brightcove'], compat_str)

        if not brightcove_video_id and not source_url:
            raise ExtractorError('Unable to extract Video URL')

        is_premium = media.get('isPremium')

        self._check_login_required(media.get('isUserEntitled'), is_premium)

        result = {
            'id': video_id,
            'title': media['title'],
            'like_count': media.get('totalUpvotes'),
            'view_count': media.get('totalViews'),
            'tags': media.get('tags'),
            'release_timestamp': parse_iso8601(media.get('publishedTime')),
            'availability': self._availability(needs_premium=is_premium),
        }

        if brightcove_video_id:
            result.update({
                '_type': 'url_transparent',
                'url': BRIGHTCOVE_URL_TEMPLATE % (brightcove_user_id, brightcove_video_id),
                'ie_key': 'BrightcoveNew'
            })

        else:
            result['formats'] = self._extract_m3u8_formats(source_url, video_id)

        return result


class FancodeLiveIE(FancodeVodIE):  # XXX: Do not subclass from concrete IE
    _WORKING = False
    IE_NAME = 'fancode:live'

    _VALID_URL = r'https?://(www\.)?fancode\.com/match/(?P<id>[0-9]+).+'

    _TESTS = [{
        'url': 'https://fancode.com/match/35328/cricket-fancode-ecs-hungary-2021-bub-vs-blb?slug=commentary',
        'info_dict': {
            'id': '35328',
            'ext': 'mp4',
            'title': 'BUB vs BLB',
            "timestamp": 1624863600,
            'is_live': True,
            'upload_date': '20210628',
        },
        'skip': 'Ended'
    }, {
        'url': 'https://fancode.com/match/35328/',
        'only_matching': True,
    }, {
        'url': 'https://fancode.com/match/35567?slug=scorecard',
        'only_matching': True,
    }]

    def _real_extract(self, url):

        id = self._match_id(url)
        data = '''{
            "query":"query MatchResponse($id: Int\\u0021, $isLoggedIn: Boolean\\u0021) { match: matchWithScores(id: $id) { id matchDesc mediaId videoStreamId videoStreamUrl { ...VideoSource } liveStreams { videoStreamId videoStreamUrl { ...VideoSource } contentId } name startTime streamingStatus isPremium isUserEntitled @include(if: $isLoggedIn) status metaTags bgImage { src } sport { name slug } tour { id name } squads { name shortName } liveStreams { contentId } mediaId }}fragment VideoSource on VideoSource { title description posterUrl url deliveryType playerType}",
            "variables":{
                "id":%s,
                "isLoggedIn":true
            },
            "operationName":"MatchResponse"
        }''' % id

        info_json = self.download_gql(id, data, "Info json")

        match_info = try_get(info_json, lambda x: x['data']['match'])

        if match_info.get('streamingStatus') != "STARTED":
            raise ExtractorError('The stream can\'t be accessed', expected=True)
        self._check_login_required(match_info.get('isUserEntitled'), True)  # all live streams are premium only

        return {
            'id': id,
            'title': match_info.get('name'),
            'formats': self._extract_akamai_formats(try_get(match_info, lambda x: x['videoStreamUrl']['url']), id),
            'ext': mimetype2ext(try_get(match_info, lambda x: x['videoStreamUrl']['deliveryType'])),
            'is_live': True,
            'release_timestamp': parse_iso8601(match_info.get('startTime'))
        }

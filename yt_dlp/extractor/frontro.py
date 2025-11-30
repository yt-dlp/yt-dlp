import json

from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, url_or_none
from ..utils.traversal import traverse_obj


class FrontoBaseIE(InfoExtractor):
    def _get_auth_headers(self, url):
        return traverse_obj(self._get_cookies(url), {
            'authorization': ('frAccessToken', 'value', {lambda token: f'Bearer {token}' if token else None}),
        })


class FrontroVideoBaseIE(FrontoBaseIE):
    _CHANNEL_ID = None

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            'https://api.frontrow.cc/query', video_id, data=json.dumps({
                'operationName': 'Video',
                'variables': {'channelID': self._CHANNEL_ID, 'videoID': video_id},
                'query': '''query Video($channelID: ID!, $videoID: ID!) {
                    video(ChannelID: $channelID, VideoID: $videoID) {
                        ... on Video {title description updatedAt thumbnail createdAt duration likeCount comments views url hasAccess}
                    }
                }''',
            }).encode(), headers={
                'content-type': 'application/json',
                **self._get_auth_headers(url),
            })['data']['video']
        if not traverse_obj(metadata, 'hasAccess'):
            self.raise_login_required()

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(metadata['url'], video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(metadata, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('thumbnail', {url_or_none}),
                'timestamp': ('createdAt', {parse_iso8601}),
                'modified_timestamp': ('updatedAt', {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
                'like_count': ('likeCount', {int_or_none}),
                'comment_count': ('comments', {int_or_none}),
                'view_count': ('views', {int_or_none}),
            }),
        }


class FrontroGroupBaseIE(FrontoBaseIE):
    _CHANNEL_ID = None
    _VIDEO_EXTRACTOR = None
    _VIDEO_URL_TMPL = None

    def _real_extract(self, url):
        group_id = self._match_id(url)

        metadata = self._download_json(
            'https://api.frontrow.cc/query', group_id, note='Downloading playlist metadata',
            data=json.dumps({
                'operationName': 'PaginatedStaticPageContainer',
                'variables': {'channelID': self._CHANNEL_ID, 'first': 500, 'pageContainerID': group_id},
                'query': '''query PaginatedStaticPageContainer($channelID: ID!, $pageContainerID: ID!) {
                              pageContainer(ChannelID: $channelID, PageContainerID: $pageContainerID) {
                                ... on StaticPageContainer { id title updatedAt createdAt itemRefs {edges {node {
                                        id contentItem { ... on ItemVideo { videoItem: item {
                                            id
                                        }}}
                                    }}}
                                }
                              }
                            }''',
            }).encode(), headers={
                'content-type': 'application/json',
                **self._get_auth_headers(url),
            })['data']['pageContainer']

        entries = []
        for video_id in traverse_obj(metadata, (
            'itemRefs', 'edges', ..., 'node', 'contentItem', 'videoItem', 'id', {str}),
        ):
            entries.append(self.url_result(
                self._VIDEO_URL_TMPL % video_id, self._VIDEO_EXTRACTOR, video_id))

        return {
            '_type': 'playlist',
            'id': group_id,
            'entries': entries,
            **traverse_obj(metadata, {
                'title': ('title', {str}),
                'timestamp': ('createdAt', {parse_iso8601}),
                'modified_timestamp': ('updatedAt', {parse_iso8601}),
            }),
        }


class TheChosenIE(FrontroVideoBaseIE):
    _CHANNEL_ID = '12884901895'

    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/video/184683594325',
        'md5': '3f878b689588c71b38ec9943c54ff5b0',
        'info_dict': {
            'id': '184683594325',
            'ext': 'mp4',
            'title': 'Season 3 Episode 2: Two by Two',
            'description': 'md5:174c373756ecc8df46b403f4fcfbaf8c',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 4212,
            'thumbnail': r're:https://fastly\.frontrowcdn\.com/channels/12884901895/VIDEO_THUMBNAIL/184683594325/',
            'timestamp': 1698954546,
            'upload_date': '20231102',
            'modified_timestamp': int,
            'modified_date': str,
        },
    }, {
        'url': 'https://watch.thechosen.tv/video/184683596189',
        'md5': 'd581562f9d29ce82f5b7770415334151',
        'info_dict': {
            'id': '184683596189',
            'ext': 'mp4',
            'title': 'Season 4 Episode 8: Humble',
            'description': 'md5:20a57bead43da1cf77cd5b0fe29bbc76',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 5092,
            'thumbnail': r're:https://fastly\.frontrowcdn\.com/channels/12884901895/VIDEO_THUMBNAIL/184683596189/',
            'timestamp': 1715019474,
            'upload_date': '20240506',
            'modified_timestamp': int,
            'modified_date': str,
        },
    }]


class TheChosenGroupIE(FrontroGroupBaseIE):
    _CHANNEL_ID = '12884901895'
    _VIDEO_EXTRACTOR = TheChosenIE
    _VIDEO_URL_TMPL = 'https://watch.thechosen.tv/video/%s'

    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/group/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/group/309237658592',
        'info_dict': {
            'id': '309237658592',
            'title': 'Season 3',
            'timestamp': 1746203969,
            'upload_date': '20250502',
            'modified_timestamp': int,
            'modified_date': str,
        },
        'playlist_count': 8,
    }]

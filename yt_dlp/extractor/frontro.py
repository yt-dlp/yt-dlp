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

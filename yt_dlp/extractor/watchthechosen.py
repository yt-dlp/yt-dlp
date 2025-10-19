import json
import urllib

from .common import InfoExtractor
from ..utils import ExtractorError, unified_strdate
from ..utils.traversal import traverse_obj


class WatchTheChosenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/(?:video|group)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/video/184683594325',
        'md5': '3f878b689588c71b38ec9943c54ff5b0',
        'info_dict': {
            'id': '184683594325',
            'ext': 'mp4',
            'title': 'Season 3 Episode 2: Two by Two',
            'description': 'Jesus is a problem for the Romans. With pilgrims from everywhere setting up a tent city at the gates of Capernaum to see Jesus, tensions rise. Jesus officially sends the twelve apostles on an exciting but dangerous mission, causing Little James to ask why he hasn’t been healed.',
            'thumbnail': 'https://fastly.frontrowcdn.com/channels/12884901895/VIDEO_THUMBNAIL/184683594325/3b180a4a-797e-403d-8929-ffcd3f29db4d.VIDEO_THUMBNAIL',
            'modified_date': str,
            'upload_date': '20231102',
            'duration': 4212,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
    }, {
        'url': 'https://watch.thechosen.tv/video/184683596189',
        'md5': 'd581562f9d29ce82f5b7770415334151',
        'info_dict': {
            'id': '184683596189',
            'ext': 'mp4',
            'title': 'Season 4 Episode 8: Humble',
            'description': 'Jesus refuses to look and act like the Messiah everyone expects—arriving like a lamb instead of a lion and riding a donkey instead of a war horse.',
            'thumbnail': 'https://fastly.frontrowcdn.com/channels/12884901895/VIDEO_THUMBNAIL/184683596189/a6c070e0-0f8e-4813-a264-85b9944c98ea.VIDEO_THUMBNAIL',
            'modified_date': str,
            'upload_date': '20240506',
            'duration': 5092,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        pageID = self._match_id(url)
        info = {}
        pathBase = urllib.parse.urlparse(url).path.strip('/').split('/')[0]
        auth_cookie = try_call(lambda: self._get_cookies(url)['frAccessToken'].value)
        token_type = try_call(lambda: self._get_cookies(url)['frTokenType'].value)

        if pathBase == 'group':
            info['_type'] = 'playlist'
            entries = []
            metadata = traverse_obj(self._download_json(
                'https://api.frontrow.cc/query', pageID, note='Downloading playlist metadata', data=json.dumps({
                    'operationName': 'PaginatedStaticPageContainer',
                    'variables': {'channelID': '12884901895', 'first': 500, 'pageContainerID': pageID},
                    'query': '''query PaginatedStaticPageContainer($after: Cursor, $channelID: ID!, $first: Int, $pageContainerID: ID!) {
                                  pageContainer(ChannelID: $channelID, PageContainerID: $pageContainerID) {
                                    ... on StaticPageContainer { ...PaginatedBasicStaticPageContainer __typename }
                                    ... on DynamicPageContainer { ...PaginatedBasicDynamicPageContainer __typename }
                                    __typename
                                  }
                                }

                                fragment PaginatedBasicStaticPageContainer on StaticPageContainer {
                                  id
                                  audiences { id name __typename }
                                  channelID pageID title layout language visibility position
                                  itemRefs(First: $first, After: $after, OrderBy: {direction: ASC, field: POSITION}) {
                                    ...BasicItemRefConnection __typename
                                  }
                                  createdAt updatedAt __typename
                                }
                                fragment PaginatedBasicDynamicPageContainer on DynamicPageContainer {
                                  id
                                  audiences { id name __typename }
                                  channelID pageID title layout language visibility position
                                  itemRefs(First: $first, After: $after) { ...BasicItemRefConnection __typename }
                                  createdAt updatedAt __typename
                                }

                                fragment BasicItemRefConnection on ItemRefConnection {
                                  edges { node { ...BasicItemRef __typename } cursor __typename }
                                  totalCount __typename
                                }

                                fragment BasicItemRef on ItemRef {
                                  id contentType contentID position
                                  contentItem {
                                    ... on ItemVideo     { videoItem: item     { ...PageContainerVideo __typename } __typename }
                                    __typename
                                  }
                                  __typename
                                }

                                fragment PageContainerVideo on Video {
                                  audiences { id name __typename }
                                  title description updatedAt thumbnail createdAt duration likeCount comments views url hasAccess id __typename
                                }''',
                }).encode(), headers={
                    'channelid': '12884901895',
                    'content-type': 'application/json',
                    'authorization': token_type + ' ' + auth_cookie,
                }), ('data', 'pageContainer'))

            if metadata is None:
                raise ExtractorError('This group does not exist!', expected=True)

            for i in traverse_obj(metadata, ('itemRefs', 'edges')):
                video_metadata = traverse_obj(i, ('node', 'contentItem', 'videoItem'))
                # Skipping ghost-video
                if video_metadata is None:
                    continue
                if not video_metadata['hasAccess']:
                    self.report_warning('Skipping Members Only video. ' + self._login_hint())
                    continue

                formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_metadata['url'], video_metadata['id'])
                entry = {'formats': formats,
                         'subtitles': subtitles,
                         **traverse_obj(video_metadata, {
                             'id': 'id',
                             'title': 'title',
                             'description': 'description',
                             'thumbnail': 'thumbnail',
                             'modified_date': ('updatedAt', {unified_strdate}),
                             'upload_date': ('createdAt', {unified_strdate}),
                             'duration': 'duration',
                             'like_count': 'likeCount',
                             'comment_count': 'comments',
                             'view_count': 'views',
                         }),
                         }
                entries.append(entry)
            info['entries'] = entries
            info['playlist_count'] = traverse_obj(metadata, ('itemRefs', 'totalCount'))

        elif pathBase == 'video':
            metadata = traverse_obj(self._download_json(
                'https://api.frontrow.cc/query', pageID, data=json.dumps({
                    'operationName': 'Video',
                    'variables': {'channelID': '12884901895', 'videoID': pageID},
                    'query': r'''query Video($channelID: ID!, $videoID: ID!) {
                        video(ChannelID: $channelID, VideoID: $videoID) {
                            ...VideoFragment __typename
                        }
                    }
                    fragment VideoFragment on Video {
                        title description updatedAt thumbnail createdAt duration likeCount comments views url hasAccess
                    }''',
                }).encode(), headers={
                    'channelid': '12884901895',
                    'content-type': 'application/json',
                    'authorization': token_type + ' ' + auth_cookie,
                }), ('data', 'video'))
            if metadata is None:
                raise ExtractorError('This video does not exist!', expected=True)
            if not metadata['hasAccess']:
                raise ExtractorError('This is Members Only video. Please log in with your account! ' + self._login_hint(), expected=True)

            formats, subtitles = self._extract_m3u8_formats_and_subtitles(metadata['url'], pageID)

            info = {
                'id': pageID,
                'formats': formats,
                'subtitles': subtitles,
                **traverse_obj(metadata, {
                    'title': 'title',
                    'description': 'description',
                    'thumbnail': 'thumbnail',
                    'modified_date': ('updatedAt', {unified_strdate}),
                    'upload_date': ('createdAt', {unified_strdate}),
                    'duration': 'duration',
                    'like_count': 'likeCount',
                    'comment_count': 'comments',
                    'view_count': 'views',
                }),
            }

        return info

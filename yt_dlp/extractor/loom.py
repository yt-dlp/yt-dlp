import json
import textwrap
import urllib.parse
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    filter_dict,
    get_first,
    int_or_none,
    parse_iso8601,
    update_url,
    url_or_none,
    variadic,
)
from ..utils.traversal import traverse_obj


class LoomIE(InfoExtractor):
    IE_NAME = 'loom'
    _VALID_URL = r'https?://(?:www\.)?loom\.com/(?:share|embed)/(?P<id>[\da-f]{32})'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        # m3u8 raw-url, mp4 transcoded-url, cdn url == raw-url, json subs only
        'url': 'https://www.loom.com/share/43d05f362f734614a2e81b4694a3a523',
        'md5': 'bfc2d7e9c2e0eb4813212230794b6f42',
        'info_dict': {
            'id': '43d05f362f734614a2e81b4694a3a523',
            'ext': 'mp4',
            'title': 'A Ruler for Windows - 28 March 2022',
            'uploader': 'wILLIAM PIP',
            'upload_date': '20220328',
            'timestamp': 1648454238,
            'duration': 27,
        },
    }, {
        # webm raw-url, mp4 transcoded-url, cdn url == transcoded-url, no subs
        'url': 'https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d',
        'md5': '70f529317be8cf880fcc2c649a531900',
        'info_dict': {
            'id': 'c43a642f815f4378b6f80a889bb73d8d',
            'ext': 'webm',
            'title': 'Lilah Nielsen Intro Video',
            'uploader': 'Lilah Nielsen',
            'upload_date': '20200826',
            'timestamp': 1598480716,
            'duration': 20,
        },
    }, {
        # m3u8 raw-url, mp4 transcoded-url, cdn url == raw-url, vtt sub and json subs
        'url': 'https://www.loom.com/share/9458bcbf79784162aa62ffb8dd66201b',
        'md5': '51737ec002969dd28344db4d60b9cbbb',
        'info_dict': {
            'id': '9458bcbf79784162aa62ffb8dd66201b',
            'ext': 'mp4',
            'title': 'Sharing screen with gpt-4',
            'description': 'Sharing screen with GPT 4 vision model and asking questions to guide through blender.',
            'uploader': 'Suneel Matham',
            'chapters': 'count:3',
            'upload_date': '20231109',
            'timestamp': 1699518978,
            'duration': 93,
        },
    }, {
        # mpd raw-url, mp4 transcoded-url, cdn url == raw-url, no subs
        'url': 'https://www.loom.com/share/24351eb8b317420289b158e4b7e96ff2',
        'info_dict': {
            'id': '24351eb8b317420289b158e4b7e96ff2',
            'ext': 'webm',
            'title': 'OMFG clown',
            'description': 'md5:285c5ee9d62aa087b7e3271b08796815',
            'uploader': 'MrPumkin B',
            'upload_date': '20210924',
            'timestamp': 1632519618,
            'duration': 210,
        },
        'params': {'skip_download': 'dash'},
    }, {
        # password-protected
        'url': 'https://www.loom.com/share/50e26e8aeb7940189dff5630f95ce1f4',
        'md5': '5cc7655e7d55d281d203f8ffd14771f7',
        'info_dict': {
            'id': '50e26e8aeb7940189dff5630f95ce1f4',
            'ext': 'mp4',
            'title': 'iOS Mobile Upload',
            'uploader': 'Simon Curran',
            'upload_date': '20200520',
            'timestamp': 1590000123,
            'duration': 35,
        },
        'params': {'videopassword': 'seniorinfants2'},
    }, {
        # embed, transcoded-url endpoint sends empty JSON response, split video and audio HLS formats
        'url': 'https://www.loom.com/embed/ddcf1c1ad21f451ea7468b1e33917e4e',
        'md5': 'b321d261656848c184a94e3b93eae28d',
        'info_dict': {
            'id': 'ddcf1c1ad21f451ea7468b1e33917e4e',
            'ext': 'mp4',
            'title': 'CF Reset User\'s Password',
            'uploader': 'Aimee Heintz',
            'upload_date': '20220707',
            'timestamp': 1657216459,
            'duration': 181,
        },
        'params': {'format': 'bestvideo'},  # Test video-only fixup
        'expected_warnings': ['Failed to parse JSON'],
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.loom.com/community/e1229802a8694a09909e8ba0fbb6d073-pg',
        'md5': 'ec838cd01b576cf0386f32e1ae424609',
        'info_dict': {
            'id': 'e1229802a8694a09909e8ba0fbb6d073',
            'ext': 'mp4',
            'title': 'Rexie Jane Cimafranca - Founder\'s Presentation',
            'uploader': 'Rexie Cimafranca',
            'upload_date': '20230213',
            'duration': 247,
            'timestamp': 1676274030,
        },
    }]

    _GRAPHQL_VARIABLES = {
        'GetVideoSource': {
            'acceptableMimes': ['DASH', 'M3U8', 'MP4'],
        },
    }
    _GRAPHQL_QUERIES = {
        'GetVideoSSR': textwrap.dedent('''\
            query GetVideoSSR($videoId: ID!, $password: String) {
              getVideo(id: $videoId, password: $password) {
                __typename
                ... on PrivateVideo {
                  id
                  status
                  message
                  __typename
                }
                ... on VideoPasswordMissingOrIncorrect {
                  id
                  message
                  __typename
                }
                ... on RegularUserVideo {
                  id
                  __typename
                  createdAt
                  description
                  download_enabled
                  folder_id
                  is_protected
                  needs_password
                  owner {
                    display_name
                    __typename
                  }
                  privacy
                  s3_id
                  name
                  video_properties {
                    avgBitRate
                    client
                    camera_enabled
                    client_version
                    duration
                    durationMs
                    format
                    height
                    microphone_enabled
                    os
                    os_version
                    recordingClient
                    recording_type
                    recording_version
                    screen_type
                    tab_audio
                    trim_duration
                    width
                    __typename
                  }
                  playable_duration
                  source_duration
                  visibility
                }
              }
            }\n'''),
        'GetVideoSource': textwrap.dedent('''\
            query GetVideoSource($videoId: ID!, $password: String, $acceptableMimes: [CloudfrontVideoAcceptableMime]) {
              getVideo(id: $videoId, password: $password) {
                ... on RegularUserVideo {
                  id
                  nullableRawCdnUrl(acceptableMimes: $acceptableMimes, password: $password) {
                    url
                    __typename
                  }
                  __typename
                }
                __typename
              }
            }\n'''),
        'FetchVideoTranscript': textwrap.dedent('''\
            query FetchVideoTranscript($videoId: ID!, $password: String) {
              fetchVideoTranscript(videoId: $videoId, password: $password) {
                ... on VideoTranscriptDetails {
                  id
                  video_id
                  source_url
                  captions_source_url
                  __typename
                }
                ... on GenericError {
                  message
                  __typename
                }
                __typename
              }
            }\n'''),
        'FetchChapters': textwrap.dedent('''\
            query FetchChapters($videoId: ID!, $password: String) {
              fetchVideoChapters(videoId: $videoId, password: $password) {
                ... on VideoChapters {
                  video_id
                  content
                  __typename
                }
                ... on EmptyChaptersPayload {
                  content
                  __typename
                }
                ... on InvalidRequestWarning {
                  message
                  __typename
                }
                ... on Error {
                  message
                  __typename
                }
                __typename
              }
            }\n'''),
    }
    _APOLLO_GRAPHQL_VERSION = '0a1856c'

    def _call_graphql_api(self, operations, video_id, note=None, errnote=None):
        password = self.get_param('videopassword')
        return self._download_json(
            'https://www.loom.com/graphql', video_id, note or 'Downloading GraphQL JSON',
            errnote or 'Failed to download GraphQL JSON', headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'x-loom-request-source': f'loom_web_{self._APOLLO_GRAPHQL_VERSION}',
                'apollographql-client-name': 'web',
                'apollographql-client-version': self._APOLLO_GRAPHQL_VERSION,
            }, data=json.dumps([{
                'operationName': operation_name,
                'variables': {
                    'videoId': video_id,
                    'password': password,
                    **self._GRAPHQL_VARIABLES.get(operation_name, {}),
                },
                'query': self._GRAPHQL_QUERIES[operation_name],
            } for operation_name in variadic(operations)], separators=(',', ':')).encode())

    def _call_url_api(self, endpoint, video_id):
        response = self._download_json(
            f'https://www.loom.com/api/campaigns/sessions/{video_id}/{endpoint}', video_id,
            f'Downloading {endpoint} JSON', f'Failed to download {endpoint} JSON', fatal=False,
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            data=json.dumps({
                'anonID': str(uuid.uuid4()),
                'deviceID': None,
                'force_original': False,  # HTTP error 401 if True
                'password': self.get_param('videopassword'),
            }, separators=(',', ':')).encode())
        return traverse_obj(response, ('url', {url_or_none}))

    def _extract_formats(self, video_id, metadata, gql_data):
        formats = []
        video_properties = traverse_obj(metadata, ('video_properties', {
            'width': ('width', {int_or_none}),
            'height': ('height', {int_or_none}),
            'acodec': ('microphone_enabled', {lambda x: 'none' if x is False else None}),
        }))

        def get_formats(format_url, format_id, quality):
            if not format_url:
                return
            ext = determine_ext(format_url)
            query = urllib.parse.urlparse(format_url).query

            if ext == 'm3u8':
                # Extract pre-merged HLS formats to avoid buggy parsing of metadata in split playlists
                format_url = format_url.replace('-split.m3u8', '.m3u8')
                m3u8_formats = self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', m3u8_id=f'hls-{format_id}', fatal=False, quality=quality)
                # Sometimes only split video/audio formats are available, need to fixup video-only formats
                is_not_premerged = 'none' in traverse_obj(m3u8_formats, (..., 'vcodec'))
                for fmt in m3u8_formats:
                    if is_not_premerged and fmt.get('vcodec') != 'none':
                        fmt['acodec'] = 'none'
                    yield {
                        **fmt,
                        'url': update_url(fmt['url'], query=query),
                        'extra_param_to_segment_url': query,
                    }

            elif ext == 'mpd':
                dash_formats = self._extract_mpd_formats(
                    format_url, video_id, mpd_id=f'dash-{format_id}', fatal=False)
                for fmt in dash_formats:
                    yield {
                        **fmt,
                        'extra_param_to_segment_url': query,
                        'quality': quality,
                    }

            else:
                yield {
                    'url': format_url,
                    'ext': ext,
                    'format_id': f'http-{format_id}',
                    'quality': quality,
                    **video_properties,
                }

        raw_url = self._call_url_api('raw-url', video_id)
        formats.extend(get_formats(raw_url, 'raw', quality=1))  # original quality

        transcoded_url = self._call_url_api('transcoded-url', video_id)
        formats.extend(get_formats(transcoded_url, 'transcoded', quality=-1))  # transcoded quality

        cdn_url = get_first(gql_data, ('data', 'getVideo', 'nullableRawCdnUrl', 'url', {url_or_none}))
        # cdn_url is usually a dupe, but the raw-url/transcoded-url endpoints could return errors
        valid_urls = [update_url(url, query=None) for url in (raw_url, transcoded_url) if url]
        if cdn_url and update_url(cdn_url, query=None) not in valid_urls:
            formats.extend(get_formats(cdn_url, 'cdn', quality=0))  # could be original or transcoded

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = get_first(
            self._call_graphql_api('GetVideoSSR', video_id, 'Downloading GraphQL metadata JSON'),
            ('data', 'getVideo', {dict})) or {}

        if metadata.get('__typename') == 'VideoPasswordMissingOrIncorrect':
            if not self.get_param('videopassword'):
                raise ExtractorError(
                    'This video is password-protected, use the --video-password option', expected=True)
            raise ExtractorError('Invalid video password', expected=True)

        gql_data = self._call_graphql_api(['FetchChapters', 'FetchVideoTranscript', 'GetVideoSource'], video_id)
        duration = traverse_obj(metadata, ('video_properties', 'duration', {int_or_none}))

        return {
            'id': video_id,
            'duration': duration,
            'chapters': self._extract_chapters_from_description(
                get_first(gql_data, ('data', 'fetchVideoChapters', 'content', {str})), duration) or None,
            'formats': self._extract_formats(video_id, metadata, gql_data),
            'subtitles': filter_dict({
                'en': traverse_obj(gql_data, (
                    ..., 'data', 'fetchVideoTranscript',
                    ('source_url', 'captions_source_url'), {
                        'url': {url_or_none},
                    })) or None,
            }),
            **traverse_obj(metadata, {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'uploader': ('owner', 'display_name', {str}),
                'timestamp': ('createdAt', {parse_iso8601}),
            }),
        }


class LoomFolderIE(InfoExtractor):
    IE_NAME = 'loom:folder'
    _VALID_URL = r'https?://(?:www\.)?loom\.com/share/folder/(?P<id>[\da-f]{32})'
    _TESTS = [{
        # 2 subfolders, no videos in root
        'url': 'https://www.loom.com/share/folder/997db4db046f43e5912f10dc5f817b5c',
        'playlist_mincount': 16,
        'info_dict': {
            'id': '997db4db046f43e5912f10dc5f817b5c',
            'title': 'Blending Lessons',
        },
    }, {
        # only videos, no subfolders
        'url': 'https://www.loom.com/share/folder/9a8a87f6b6f546d9a400c8e7575ff7f2',
        'playlist_mincount': 12,
        'info_dict': {
            'id': '9a8a87f6b6f546d9a400c8e7575ff7f2',
            'title': 'List A- a, i, o',
        },
    }, {
        # videos in root and empty subfolder
        'url': 'https://www.loom.com/share/folder/886e534218c24fd292e97e9563078cc4',
        'playlist_mincount': 21,
        'info_dict': {
            'id': '886e534218c24fd292e97e9563078cc4',
            'title': 'Medicare Agent Training videos',
        },
    }, {
        # videos in root and videos in subfolders
        'url': 'https://www.loom.com/share/folder/b72c4ecdf04745da9403926d80a40c38',
        'playlist_mincount': 21,
        'info_dict': {
            'id': 'b72c4ecdf04745da9403926d80a40c38',
            'title': 'Quick Altos Q & A Tutorials',
        },
    }, {
        # recursive folder extraction
        'url': 'https://www.loom.com/share/folder/8b458a94e0e4449b8df9ea7a68fafc4e',
        'playlist_count': 23,
        'info_dict': {
            'id': '8b458a94e0e4449b8df9ea7a68fafc4e',
            'title': 'Sezer Texting Guide',
        },
    }, {
        # more than 50 videos in 1 folder
        'url': 'https://www.loom.com/share/folder/e056a91d290d47ca9b00c9d1df56c463',
        'playlist_mincount': 61,
        'info_dict': {
            'id': 'e056a91d290d47ca9b00c9d1df56c463',
            'title': 'User Videos',
        },
    }, {
        # many subfolders
        'url': 'https://www.loom.com/share/folder/c2dde8cc67454f0e99031677279d8954',
        'playlist_mincount': 75,
        'info_dict': {
            'id': 'c2dde8cc67454f0e99031677279d8954',
            'title': 'Honors 1',
        },
    }, {
        'url': 'https://www.loom.com/share/folder/bae17109a68146c7803454f2893c8cf8/Edpuzzle',
        'only_matching': True,
    }]

    def _extract_folder_data(self, folder_id):
        return self._download_json(
            f'https://www.loom.com/v1/folders/{folder_id}', folder_id,
            'Downloading folder info JSON', query={'limit': '10000'})

    def _extract_folder_entries(self, folder_id, initial_folder_data=None):
        folder_data = initial_folder_data or self._extract_folder_data(folder_id)

        for video in traverse_obj(folder_data, ('videos', lambda _, v: v['id'])):
            video_id = video['id']
            yield self.url_result(
                f'https://www.loom.com/share/{video_id}', LoomIE, video_id, video.get('name'))

        # Recurse into subfolders
        for subfolder_id in traverse_obj(folder_data, (
                'folders', lambda _, v: v['id'] != folder_id, 'id', {str})):
            yield from self._extract_folder_entries(subfolder_id)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_data = self._extract_folder_data(playlist_id)

        return self.playlist_result(
            self._extract_folder_entries(playlist_id, playlist_data), playlist_id,
            traverse_obj(playlist_data, ('folder', 'name', {str.strip})))

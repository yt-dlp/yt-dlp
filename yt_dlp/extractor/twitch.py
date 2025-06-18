import collections
import itertools
import json
import random
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    base_url,
    clean_html,
    dict_get,
    float_or_none,
    int_or_none,
    join_nonempty,
    make_archive_id,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    str_or_none,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj, value


class TwitchBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:(?:www|go|m)\.)?twitch\.tv'

    _API_BASE = 'https://api.twitch.tv'
    _USHER_BASE = 'https://usher.ttvnw.net'
    _LOGIN_FORM_URL = 'https://www.twitch.tv/login'
    _LOGIN_POST_URL = 'https://passport.twitch.tv/login'
    _NETRC_MACHINE = 'twitch'

    _OPERATION_HASHES = {
        'CollectionSideBar': '27111f1b382effad0b6def325caef1909c733fe6a4fbabf54f8d491ef2cf2f14',
        'FilterableVideoTower_Videos': 'a937f1d22e269e39a03b509f65a7490f9fc247d7f83d6ac1421523e3b68042cb',
        'ClipsCards__User': 'b73ad2bfaecfd30a9e6c28fada15bd97032c83ec77a0440766a56fe0bd632777',
        'ShareClipRenderStatus': 'f130048a462a0ac86bb54d653c968c514e9ab9ca94db52368c1179e97b0f16eb',
        'ChannelCollectionsContent': '447aec6a0cc1e8d0a8d7732d47eb0762c336a2294fdb009e9c9d854e49d484b9',
        'StreamMetadata': 'a647c2a13599e5991e175155f798ca7f1ecddde73f7f341f39009c14dbf59962',
        'ComscoreStreamingQuery': 'e1edae8122517d013405f237ffcc124515dc6ded82480a88daef69c83b53ac01',
        'VideoPreviewOverlay': '3006e77e51b128d838fa4e835723ca4dc9a05c5efd4466c1085215c6e437e65c',
        'VideoMetadata': '49b5b8f268cdeb259d75b58dcb0c1a748e3b575003448a2333dc5cdafd49adad',
        'VideoPlayer_ChapterSelectButtonVideo': '8d2793384aac3773beab5e59bd5d6f585aedb923d292800119e03d40cd0f9b41',
        'VideoPlayer_VODSeekbarPreviewVideo': '07e99e4d56c5a7c67117a154777b0baf85a5ffefa393b213f4bc712ccaf85dd6',
    }

    @property
    def _CLIENT_ID(self):
        return self._configuration_arg(
            'client_id', ['ue6666qo983tsx6so1t0vnawi233wa'], ie_key='Twitch', casesense=True)[0]

    def _perform_login(self, username, password):
        def fail(message):
            raise ExtractorError(
                f'Unable to login. Twitch said: {message}', expected=True)

        def login_step(page, urlh, note, data):
            form = self._hidden_inputs(page)
            form.update(data)

            page_url = urlh.url
            post_url = self._search_regex(
                r'<form[^>]+action=(["\'])(?P<url>.+?)\1', page,
                'post url', default=self._LOGIN_POST_URL, group='url')
            post_url = urljoin(page_url, post_url)

            headers = {
                'Referer': page_url,
                'Origin': 'https://www.twitch.tv',
                'Content-Type': 'text/plain;charset=UTF-8',
            }

            response = self._download_json(
                post_url, None, note, data=json.dumps(form).encode(),
                headers=headers, expected_status=400)
            error = dict_get(response, ('error', 'error_description', 'error_code'))
            if error:
                fail(error)

            if 'Authenticated successfully' in response.get('message', ''):
                return None, None

            redirect_url = urljoin(
                post_url,
                response.get('redirect') or response['redirect_path'])
            return self._download_webpage_handle(
                redirect_url, None, 'Downloading login redirect page',
                headers=headers)

        login_page, handle = self._download_webpage_handle(
            self._LOGIN_FORM_URL, None, 'Downloading login page')

        # Some TOR nodes and public proxies are blocked completely
        if 'blacklist_message' in login_page:
            fail(clean_html(login_page))

        redirect_page, handle = login_step(
            login_page, handle, 'Logging in', {
                'username': username,
                'password': password,
                'client_id': self._CLIENT_ID,
            })

        # Successful login
        if not redirect_page:
            return

        if re.search(r'(?i)<form[^>]+id="two-factor-submit"', redirect_page) is not None:
            # TODO: Add mechanism to request an SMS or phone call
            tfa_token = self._get_tfa_info('two-factor authentication token')
            login_step(redirect_page, handle, 'Submitting TFA token', {
                'authy_token': tfa_token,
                'remember_2fa': 'true',
            })

    def _prefer_source(self, formats):
        try:
            source = next(f for f in formats if f['format_id'] == 'Source')
            source['quality'] = 10
        except StopIteration:
            for f in formats:
                if '/chunked/' in f['url']:
                    f.update({
                        'quality': 10,
                        'format_note': 'Source',
                    })

    def _download_base_gql(self, video_id, ops, note, fatal=True):
        headers = {
            'Content-Type': 'text/plain;charset=UTF-8',
            'Client-ID': self._CLIENT_ID,
        }
        gql_auth = self._get_cookies('https://gql.twitch.tv').get('auth-token')
        if gql_auth:
            headers['Authorization'] = 'OAuth ' + gql_auth.value
        return self._download_json(
            'https://gql.twitch.tv/gql', video_id, note,
            data=json.dumps(ops).encode(),
            headers=headers, fatal=fatal)

    def _download_gql(self, video_id, ops, note, fatal=True):
        for op in ops:
            op['extensions'] = {
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': self._OPERATION_HASHES[op['operationName']],
                },
            }
        return self._download_base_gql(video_id, ops, note)

    def _download_access_token(self, video_id, token_kind, param_name):
        method = f'{token_kind}PlaybackAccessToken'
        ops = {
            'query': '''{
              %s(
                %s: "%s",
                params: {
                  platform: "web",
                  playerBackend: "mediaplayer",
                  playerType: "site"
                }
              )
              {
                value
                signature
              }
            }''' % (method, param_name, video_id),  # noqa: UP031
        }
        return self._download_base_gql(
            video_id, ops,
            f'Downloading {token_kind} access token GraphQL')['data'][method]

    def _get_thumbnails(self, thumbnail):
        return [{
            'url': re.sub(r'\d+x\d+(\.\w+)($|(?=[?#]))', r'0x0\g<1>', thumbnail),
            'preference': 1,
        }, {
            'url': thumbnail,
        }] if thumbnail else None

    def _extract_twitch_m3u8_formats(self, path, video_id, token, signature, live_from_start=False):
        formats = self._extract_m3u8_formats(
            f'{self._USHER_BASE}/{path}/{video_id}.m3u8', video_id, 'mp4', query={
                'allow_source': 'true',
                'allow_audio_only': 'true',
                'allow_spectre': 'true',
                'p': random.randint(1000000, 10000000),
                'platform': 'web',
                'player': 'twitchweb',
                'supported_codecs': 'av1,h265,h264',
                'playlist_include_framerate': 'true',
                'sig': signature,
                'token': token,
            })
        for fmt in formats:
            if fmt.get('vcodec') and fmt['vcodec'].startswith('av01'):
                # mpegts does not yet have proper support for av1
                fmt.setdefault('downloader_options', {}).update({'ffmpeg_args_out': ['-f', 'mp4']})
            if live_from_start:
                fmt.setdefault('downloader_options', {}).update({'ffmpeg_args': ['-live_start_index', '0']})
                fmt['is_from_start'] = True

        return formats


class TwitchVodIE(TwitchBaseIE):
    IE_NAME = 'twitch:vod'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:(?:www|go|m)\.)?twitch\.tv/(?:[^/]+/v(?:ideo)?|videos)/|
                            player\.twitch\.tv/\?.*?\bvideo=v?|
                            www\.twitch\.tv/[^/]+/schedule\?vodID=
                        )
                        (?P<id>\d+)
                    '''

    _TESTS = [{
        'url': 'http://www.twitch.tv/riotgames/v/6528877?t=5m10s',
        'info_dict': {
            'id': 'v6528877',
            'ext': 'mp4',
            'title': 'LCK Summer Split - Week 6 Day 1',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 17208,
            'timestamp': 1435131734,
            'upload_date': '20150624',
            'uploader': 'Riot Games',
            'uploader_id': 'riotgames',
            'view_count': int,
            'start_time': 310,
            'chapters': [
                {
                    'start_time': 0,
                    'end_time': 17208,
                    'title': 'League of Legends',
                },
            ],
            'live_status': 'was_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # Untitled broadcast (title is None)
        'url': 'http://www.twitch.tv/belkao_o/v/11230755',
        'info_dict': {
            'id': 'v11230755',
            'ext': 'mp4',
            'title': 'Untitled Broadcast',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1638,
            'timestamp': 1439746708,
            'upload_date': '20150816',
            'uploader': 'BelkAO_o',
            'uploader_id': 'belkao_o',
            'view_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'HTTP Error 404: Not Found',
    }, {
        'url': 'http://player.twitch.tv/?t=5m10s&video=v6528877',
        'only_matching': True,
    }, {
        'url': 'https://www.twitch.tv/videos/6528877',
        'only_matching': True,
    }, {
        'url': 'https://m.twitch.tv/beagsandjam/v/247478721',
        'only_matching': True,
    }, {
        'url': 'https://www.twitch.tv/northernlion/video/291940395',
        'only_matching': True,
    }, {
        'url': 'https://player.twitch.tv/?video=480452374',
        'only_matching': True,
    }, {
        'url': 'https://www.twitch.tv/videos/635475444',
        'info_dict': {
            'id': 'v635475444',
            'ext': 'mp4',
            'title': 'Riot Games',
            'duration': 11643,
            'uploader': 'Riot Games',
            'uploader_id': 'riotgames',
            'timestamp': 1590770569,
            'upload_date': '20200529',
            'chapters': [
                {
                    'start_time': 0,
                    'end_time': 573,
                    'title': 'League of Legends',
                },
                {
                    'start_time': 573,
                    'end_time': 3922,
                    'title': 'Legends of Runeterra',
                },
                {
                    'start_time': 3922,
                    'end_time': 11643,
                    'title': 'Art',
                },
            ],
            'live_status': 'was_live',
            'thumbnail': r're:^https?://.*\.jpg$',
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'note': 'Storyboards',
        'url': 'https://www.twitch.tv/videos/635475444',
        'info_dict': {
            'id': 'v635475444',
            'format_id': 'sb0',
            'ext': 'mhtml',
            'title': 'Riot Games',
            'duration': 11643,
            'uploader': 'Riot Games',
            'uploader_id': 'riotgames',
            'timestamp': 1590770569,
            'upload_date': '20200529',
            'chapters': [
                {
                    'start_time': 0,
                    'end_time': 573,
                    'title': 'League of Legends',
                },
                {
                    'start_time': 573,
                    'end_time': 3922,
                    'title': 'Legends of Runeterra',
                },
                {
                    'start_time': 3922,
                    'end_time': 11643,
                    'title': 'Art',
                },
            ],
            'live_status': 'was_live',
            'thumbnail': r're:^https?://.*\.jpg$',
            'view_count': int,
            'columns': int,
            'rows': int,
        },
        'params': {
            'format': 'mhtml',
            'skip_download': True,
        },
    }, {
        'note': 'VOD with single chapter',
        'url': 'https://www.twitch.tv/videos/1536751224',
        'info_dict': {
            'id': 'v1536751224',
            'ext': 'mp4',
            'title': 'Porter Robinson Star Guardian Stream Tour with LilyPichu',
            'duration': 8353,
            'uploader': 'Riot Games',
            'uploader_id': 'riotgames',
            'timestamp': 1658267731,
            'upload_date': '20220719',
            'chapters': [
                {
                    'start_time': 0,
                    'end_time': 8353,
                    'title': 'League of Legends',
                },
            ],
            'live_status': 'was_live',
            'thumbnail': r're:^https?://.*\.jpg$',
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download JSON metadata: HTTP Error 403: Forbidden'],
    }, {
        'url': 'https://www.twitch.tv/tangotek/schedule?vodID=1822395420',
        'only_matching': True,
    }]

    def _download_info(self, item_id):
        data = self._download_gql(
            item_id, [{
                'operationName': 'VideoMetadata',
                'variables': {
                    'channelLogin': '',
                    'videoID': item_id,
                },
            }, {
                'operationName': 'VideoPlayer_ChapterSelectButtonVideo',
                'variables': {
                    'includePrivate': False,
                    'videoID': item_id,
                },
            }, {
                'operationName': 'VideoPlayer_VODSeekbarPreviewVideo',
                'variables': {
                    'includePrivate': False,
                    'videoID': item_id,
                },
            }],
            'Downloading stream metadata GraphQL')

        video = traverse_obj(data, (..., 'data', 'video'), get_all=False)
        if video is None:
            raise ExtractorError(f'Video {item_id} does not exist', expected=True)

        video['moments'] = traverse_obj(data, (..., 'data', 'video', 'moments', 'edges', ..., 'node'))
        video['storyboard'] = traverse_obj(
            data, (..., 'data', 'video', 'seekPreviewsURL', {url_or_none}), get_all=False)

        return video

    def _extract_info(self, info):
        status = info.get('status')
        if status == 'recording':
            is_live = True
        elif status == 'recorded':
            is_live = False
        else:
            is_live = None
        _QUALITIES = ('small', 'medium', 'large')
        quality_key = qualities(_QUALITIES)
        thumbnails = []
        preview = info.get('preview')
        if isinstance(preview, dict):
            for thumbnail_id, thumbnail_url in preview.items():
                thumbnail_url = url_or_none(thumbnail_url)
                if not thumbnail_url:
                    continue
                if thumbnail_id not in _QUALITIES:
                    continue
                thumbnails.append({
                    'url': thumbnail_url,
                    'preference': quality_key(thumbnail_id),
                })
        return {
            'id': info['_id'],
            'title': info.get('title') or 'Untitled Broadcast',
            'description': info.get('description'),
            'duration': int_or_none(info.get('length')),
            'thumbnails': thumbnails,
            'uploader': info.get('channel', {}).get('display_name'),
            'uploader_id': info.get('channel', {}).get('name'),
            'timestamp': parse_iso8601(info.get('recorded_at')),
            'view_count': int_or_none(info.get('views')),
            'is_live': is_live,
            'was_live': True,
        }

    def _extract_chapters(self, info, item_id):
        if not info.get('moments'):
            game = traverse_obj(info, ('game', 'displayName'))
            if game:
                yield {'title': game}
            return

        for moment in info['moments']:
            start_time = int_or_none(moment.get('positionMilliseconds'), 1000)
            duration = int_or_none(moment.get('durationMilliseconds'), 1000)
            name = str_or_none(moment.get('description'))

            if start_time is None or duration is None:
                self.report_warning(f'Important chapter information missing for chapter {name}', item_id)
                continue
            yield {
                'start_time': start_time,
                'end_time': start_time + duration,
                'title': name,
            }

    def _extract_info_gql(self, info, item_id):
        vod_id = info.get('id') or item_id
        # id backward compatibility for download archives
        if vod_id[0] != 'v':
            vod_id = f'v{vod_id}'
        thumbnail = url_or_none(info.get('previewThumbnailURL'))
        is_live = None
        if thumbnail:
            if re.findall(r'/404_processing_[^.?#]+\.png', thumbnail):
                is_live, thumbnail = True, None
            else:
                is_live = False

        return {
            'id': vod_id,
            'title': info.get('title') or 'Untitled Broadcast',
            'description': info.get('description'),
            'duration': int_or_none(info.get('lengthSeconds')),
            'thumbnails': self._get_thumbnails(thumbnail),
            'uploader': try_get(info, lambda x: x['owner']['displayName'], str),
            'uploader_id': try_get(info, lambda x: x['owner']['login'], str),
            'timestamp': unified_timestamp(info.get('publishedAt')),
            'view_count': int_or_none(info.get('viewCount')),
            'chapters': list(self._extract_chapters(info, item_id)),
            'is_live': is_live,
            'was_live': True,
        }

    def _extract_storyboard(self, item_id, storyboard_json_url, duration):
        if not duration or not storyboard_json_url:
            return
        spec = self._download_json(storyboard_json_url, item_id, 'Downloading storyboard metadata JSON', fatal=False) or []
        # sort from highest quality to lowest
        # This makes sb0 the highest-quality format, sb1 - lower, etc which is consistent with youtube sb ordering
        spec.sort(key=lambda x: int_or_none(x.get('width')) or 0, reverse=True)
        base = base_url(storyboard_json_url)
        for i, s in enumerate(spec):
            count = int_or_none(s.get('count'))
            images = s.get('images')
            if not (images and count):
                continue
            fragment_duration = duration / len(images)
            yield {
                'format_id': f'sb{i}',
                'format_note': 'storyboard',
                'ext': 'mhtml',
                'protocol': 'mhtml',
                'acodec': 'none',
                'vcodec': 'none',
                'url': urljoin(base, images[0]),
                'width': int_or_none(s.get('width')),
                'height': int_or_none(s.get('height')),
                'fps': count / duration,
                'rows': int_or_none(s.get('rows')),
                'columns': int_or_none(s.get('cols')),
                'fragments': [{
                    'url': urljoin(base, path),
                    'duration': fragment_duration,
                } for path in images],
            }

    def _real_extract(self, url):
        vod_id = self._match_id(url)

        video = self._download_info(vod_id)
        info = self._extract_info_gql(video, vod_id)
        access_token = self._download_access_token(vod_id, 'video', 'id')

        formats = self._extract_twitch_m3u8_formats(
            'vod', vod_id, access_token['value'], access_token['signature'],
            live_from_start=self.get_param('live_from_start'))
        formats.extend(self._extract_storyboard(vod_id, video.get('storyboard'), info.get('duration')))

        self._prefer_source(formats)
        info['formats'] = formats

        parsed_url = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed_url.query)
        if 't' in query:
            info['start_time'] = parse_duration(query['t'][0])

        if info.get('timestamp') is not None:
            info['subtitles'] = {
                'rechat': [{
                    'url': update_url_query(
                        f'https://api.twitch.tv/v5/videos/{vod_id}/comments', {
                            'client_id': self._CLIENT_ID,
                        }),
                    'ext': 'json',
                }],
            }

        return info


def _make_video_result(node):
    assert isinstance(node, dict)
    video_id = node.get('id')
    if not video_id:
        return
    return {
        '_type': 'url_transparent',
        'ie_key': TwitchVodIE.ie_key(),
        'id': 'v' + video_id,
        'url': f'https://www.twitch.tv/videos/{video_id}',
        'title': node.get('title'),
        'thumbnail': node.get('previewThumbnailURL'),
        'duration': float_or_none(node.get('lengthSeconds')),
        'view_count': int_or_none(node.get('viewCount')),
    }


class TwitchCollectionIE(TwitchBaseIE):
    _VALID_URL = r'https?://(?:(?:www|go|m)\.)?twitch\.tv/collections/(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.twitch.tv/collections/wlDCoH0zEBZZbQ',
        'info_dict': {
            'id': 'wlDCoH0zEBZZbQ',
            'title': 'Overthrow Nook, capitalism for children',
        },
        'playlist_mincount': 13,
    }]

    _OPERATION_NAME = 'CollectionSideBar'

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        collection = self._download_gql(
            collection_id, [{
                'operationName': self._OPERATION_NAME,
                'variables': {'collectionID': collection_id},
            }],
            'Downloading collection GraphQL')[0]['data']['collection']
        title = collection.get('title')
        entries = []
        for edge in collection['items']['edges']:
            if not isinstance(edge, dict):
                continue
            node = edge.get('node')
            if not isinstance(node, dict):
                continue
            video = _make_video_result(node)
            if video:
                entries.append(video)
        return self.playlist_result(
            entries, playlist_id=collection_id, playlist_title=title)


class TwitchPlaylistBaseIE(TwitchBaseIE):
    _PAGE_LIMIT = 100

    def _entries(self, channel_name, *args):
        """
        Subclasses must define _make_variables() and _extract_entry(),
        as well as set _OPERATION_NAME, _ENTRY_KIND, _EDGE_KIND, and _NODE_KIND
        """
        cursor = None
        variables_common = self._make_variables(channel_name, *args)
        entries_key = f'{self._ENTRY_KIND}s'
        for page_num in itertools.count(1):
            variables = variables_common.copy()
            variables['limit'] = self._PAGE_LIMIT
            if cursor:
                variables['cursor'] = cursor
            page = self._download_gql(
                channel_name, [{
                    'operationName': self._OPERATION_NAME,
                    'variables': variables,
                }],
                f'Downloading {self._NODE_KIND}s GraphQL page {page_num}',
                fatal=False)
            if not page:
                break
            edges = try_get(
                page, lambda x: x[0]['data']['user'][entries_key]['edges'], list)
            if not edges:
                break
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                if edge.get('__typename') != self._EDGE_KIND:
                    continue
                node = edge.get('node')
                if not isinstance(node, dict):
                    continue
                if node.get('__typename') != self._NODE_KIND:
                    continue
                entry = self._extract_entry(node)
                if entry:
                    cursor = edge.get('cursor')
                    yield entry
            if not cursor or not isinstance(cursor, str):
                break


class TwitchVideosBaseIE(TwitchPlaylistBaseIE):
    _OPERATION_NAME = 'FilterableVideoTower_Videos'
    _ENTRY_KIND = 'video'
    _EDGE_KIND = 'VideoEdge'
    _NODE_KIND = 'Video'

    @staticmethod
    def _make_variables(channel_name, broadcast_type, sort):
        return {
            'channelOwnerLogin': channel_name,
            'broadcastType': broadcast_type,
            'videoSort': sort.upper(),
        }


class TwitchVideosIE(TwitchVideosBaseIE):
    _VALID_URL = r'https?://(?:(?:www|go|m)\.)?twitch\.tv/(?P<id>[^/]+)/(?:videos|profile)'

    _TESTS = [{
        # All Videos sorted by Date
        'url': 'https://www.twitch.tv/spamfish/videos?filter=all',
        'info_dict': {
            'id': 'spamfish',
            'title': 'spamfish - All Videos sorted by Date',
        },
        'playlist_mincount': 924,
    }, {
        # All Videos sorted by Popular
        'url': 'https://www.twitch.tv/spamfish/videos?filter=all&sort=views',
        'info_dict': {
            'id': 'spamfish',
            'title': 'spamfish - All Videos sorted by Popular',
        },
        'playlist_mincount': 931,
    }, {
        # Past Broadcasts sorted by Date
        'url': 'https://www.twitch.tv/spamfish/videos?filter=archives',
        'info_dict': {
            'id': 'spamfish',
            'title': 'spamfish - Past Broadcasts sorted by Date',
        },
        'playlist_mincount': 27,
    }, {
        # Highlights sorted by Date
        'url': 'https://www.twitch.tv/spamfish/videos?filter=highlights',
        'info_dict': {
            'id': 'spamfish',
            'title': 'spamfish - Highlights sorted by Date',
        },
        'playlist_mincount': 901,
    }, {
        # Uploads sorted by Date
        'url': 'https://www.twitch.tv/esl_csgo/videos?filter=uploads&sort=time',
        'info_dict': {
            'id': 'esl_csgo',
            'title': 'esl_csgo - Uploads sorted by Date',
        },
        'playlist_mincount': 5,
    }, {
        # Past Premieres sorted by Date
        'url': 'https://www.twitch.tv/spamfish/videos?filter=past_premieres',
        'info_dict': {
            'id': 'spamfish',
            'title': 'spamfish - Past Premieres sorted by Date',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://www.twitch.tv/spamfish/videos/all',
        'only_matching': True,
    }, {
        'url': 'https://m.twitch.tv/spamfish/videos/all',
        'only_matching': True,
    }, {
        'url': 'https://www.twitch.tv/spamfish/videos',
        'only_matching': True,
    }]

    Broadcast = collections.namedtuple('Broadcast', ['type', 'label'])

    _DEFAULT_BROADCAST = Broadcast(None, 'All Videos')
    _BROADCASTS = {
        'archives': Broadcast('ARCHIVE', 'Past Broadcasts'),
        'highlights': Broadcast('HIGHLIGHT', 'Highlights'),
        'uploads': Broadcast('UPLOAD', 'Uploads'),
        'past_premieres': Broadcast('PAST_PREMIERE', 'Past Premieres'),
        'all': _DEFAULT_BROADCAST,
    }

    _DEFAULT_SORTED_BY = 'Date'
    _SORTED_BY = {
        'time': _DEFAULT_SORTED_BY,
        'views': 'Popular',
    }

    @classmethod
    def suitable(cls, url):
        return (False
                if any(ie.suitable(url) for ie in (
                    TwitchVideosClipsIE,
                    TwitchVideosCollectionsIE))
                else super().suitable(url))

    @staticmethod
    def _extract_entry(node):
        return _make_video_result(node)

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        qs = parse_qs(url)
        video_filter = qs.get('filter', ['all'])[0]
        sort = qs.get('sort', ['time'])[0]
        broadcast = self._BROADCASTS.get(video_filter, self._DEFAULT_BROADCAST)
        return self.playlist_result(
            self._entries(channel_name, broadcast.type, sort),
            playlist_id=channel_name,
            playlist_title=(
                f'{channel_name} - {broadcast.label} '
                f'sorted by {self._SORTED_BY.get(sort, self._DEFAULT_SORTED_BY)}'))


class TwitchVideosClipsIE(TwitchPlaylistBaseIE):
    _VALID_URL = r'https?://(?:(?:www|go|m)\.)?twitch\.tv/(?P<id>[^/]+)/(?:clips|videos/*?\?.*?\bfilter=clips)'

    _TESTS = [{
        # Clips
        'url': 'https://www.twitch.tv/vanillatv/clips?filter=clips&range=all',
        'info_dict': {
            'id': 'vanillatv',
            'title': 'vanillatv - Clips Top All',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://www.twitch.tv/dota2ruhub/videos?filter=clips&range=7d',
        'only_matching': True,
    }]

    Clip = collections.namedtuple('Clip', ['filter', 'label'])

    _DEFAULT_CLIP = Clip('LAST_WEEK', 'Top 7D')
    _RANGE = {
        '24hr': Clip('LAST_DAY', 'Top 24H'),
        '7d': _DEFAULT_CLIP,
        '30d': Clip('LAST_MONTH', 'Top 30D'),
        'all': Clip('ALL_TIME', 'Top All'),
    }

    # NB: values other than 20 result in skipped videos
    _PAGE_LIMIT = 20

    _OPERATION_NAME = 'ClipsCards__User'
    _ENTRY_KIND = 'clip'
    _EDGE_KIND = 'ClipEdge'
    _NODE_KIND = 'Clip'

    @staticmethod
    def _make_variables(channel_name, channel_filter):
        return {
            'login': channel_name,
            'criteria': {
                'filter': channel_filter,
            },
        }

    @staticmethod
    def _extract_entry(node):
        assert isinstance(node, dict)
        clip_url = url_or_none(node.get('url'))
        if not clip_url:
            return
        return {
            '_type': 'url_transparent',
            'ie_key': TwitchClipsIE.ie_key(),
            'id': node.get('id'),
            'url': clip_url,
            'title': node.get('title'),
            'thumbnail': node.get('thumbnailURL'),
            'duration': float_or_none(node.get('durationSeconds')),
            'timestamp': unified_timestamp(node.get('createdAt')),
            'view_count': int_or_none(node.get('viewCount')),
            'language': node.get('language'),
        }

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        qs = parse_qs(url)
        date_range = qs.get('range', ['7d'])[0]
        clip = self._RANGE.get(date_range, self._DEFAULT_CLIP)
        return self.playlist_result(
            self._entries(channel_name, clip.filter),
            playlist_id=channel_name,
            playlist_title=f'{channel_name} - Clips {clip.label}')


class TwitchVideosCollectionsIE(TwitchPlaylistBaseIE):
    _VALID_URL = r'https?://(?:(?:www|go|m)\.)?twitch\.tv/(?P<id>[^/]+)/videos/*?\?.*?\bfilter=collections'

    _TESTS = [{
        # Collections
        'url': 'https://www.twitch.tv/spamfish/videos?filter=collections',
        'info_dict': {
            'id': 'spamfish',
            'title': 'spamfish - Collections',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://www.twitch.tv/monstercat/videos?filter=collections',
        'info_dict': {
            'id': 'monstercat',
            'title': 'monstercat - Collections',
        },
        'playlist_mincount': 13,
    }]

    _OPERATION_NAME = 'ChannelCollectionsContent'
    _ENTRY_KIND = 'collection'
    _EDGE_KIND = 'CollectionsItemEdge'
    _NODE_KIND = 'Collection'

    @staticmethod
    def _make_variables(channel_name):
        return {
            'ownerLogin': channel_name,
        }

    @staticmethod
    def _extract_entry(node):
        assert isinstance(node, dict)
        collection_id = node.get('id')
        if not collection_id:
            return
        return {
            '_type': 'url_transparent',
            'ie_key': TwitchCollectionIE.ie_key(),
            'id': collection_id,
            'url': f'https://www.twitch.tv/collections/{collection_id}',
            'title': node.get('title'),
            'thumbnail': node.get('thumbnailURL'),
            'duration': float_or_none(node.get('lengthSeconds')),
            'timestamp': unified_timestamp(node.get('updatedAt')),
            'view_count': int_or_none(node.get('viewCount')),
        }

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        return self.playlist_result(
            self._entries(channel_name), playlist_id=channel_name,
            playlist_title=f'{channel_name} - Collections')


class TwitchStreamIE(TwitchVideosBaseIE):
    IE_NAME = 'twitch:stream'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:(?:www|go|m)\.)?twitch\.tv/|
                            player\.twitch\.tv/\?.*?\bchannel=
                        )
                        (?P<id>[^/#?]+)
                    '''

    _TESTS = [{
        'url': 'http://www.twitch.tv/shroomztv',
        'info_dict': {
            'id': '12772022048',
            'display_id': 'shroomztv',
            'ext': 'mp4',
            'title': 're:^ShroomzTV [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'H1Z1 - lonewolfing with ShroomzTV | A3 Battle Royale later - @ShroomzTV',
            'is_live': True,
            'timestamp': 1421928037,
            'upload_date': '20150122',
            'uploader': 'ShroomzTV',
            'uploader_id': 'shroomztv',
            'view_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'User does not exist',
    }, {
        'url': 'http://www.twitch.tv/miracle_doto#profile-0',
        'only_matching': True,
    }, {
        'url': 'https://player.twitch.tv/?channel=lotsofs',
        'only_matching': True,
    }, {
        'url': 'https://go.twitch.tv/food',
        'only_matching': True,
    }, {
        'url': 'https://m.twitch.tv/food',
        'only_matching': True,
    }, {
        'url': 'https://www.twitch.tv/monstercat',
        'info_dict': {
            'id': '40500071752',
            'display_id': 'monstercat',
            'title': 're:Monstercat',
            'description': 'md5:0945ad625e615bc8f0469396537d87d9',
            'is_live': True,
            'timestamp': 1677107190,
            'upload_date': '20230222',
            'uploader': 'Monstercat',
            'uploader_id': 'monstercat',
            'live_status': 'is_live',
            'thumbnail': 're:https://.*.jpg',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }]
    _PAGE_LIMIT = 1

    @classmethod
    def suitable(cls, url):
        return (False
                if any(ie.suitable(url) for ie in (
                    TwitchVodIE,
                    TwitchCollectionIE,
                    TwitchVideosIE,
                    TwitchVideosClipsIE,
                    TwitchVideosCollectionsIE,
                    TwitchClipsIE))
                else super().suitable(url))

    @staticmethod
    def _extract_entry(node):
        if not isinstance(node, dict) or not node.get('id'):
            return None
        video_id = node['id']
        return {
            '_type': 'url',
            'ie_key': TwitchVodIE.ie_key(),
            'id': 'v' + video_id,
            'url': f'https://www.twitch.tv/videos/{video_id}',
            'title': node.get('title'),
            'timestamp': unified_timestamp(node.get('publishedAt')) or 0,
        }

    def _real_extract(self, url):
        channel_name = self._match_id(url).lower()

        gql = self._download_gql(
            channel_name, [{
                'operationName': 'StreamMetadata',
                'variables': {'channelLogin': channel_name},
            }, {
                'operationName': 'ComscoreStreamingQuery',
                'variables': {
                    'channel': channel_name,
                    'clipSlug': '',
                    'isClip': False,
                    'isLive': True,
                    'isVodOrCollection': False,
                    'vodID': '',
                },
            }, {
                'operationName': 'VideoPreviewOverlay',
                'variables': {'login': channel_name},
            }],
            'Downloading stream GraphQL')

        user = gql[0]['data']['user']

        if not user:
            raise ExtractorError(
                f'{channel_name} does not exist', expected=True)

        stream = user['stream']

        if not stream:
            raise UserNotLive(video_id=channel_name)

        timestamp = unified_timestamp(stream.get('createdAt'))

        if self.get_param('live_from_start'):
            self.to_screen(f'{channel_name}: Extracting VOD to download live from start')
            entry = next(self._entries(channel_name, None, 'time'), None)
            if entry and entry.pop('timestamp') >= (timestamp or float('inf')):
                return entry
            self.report_warning(
                'Unable to extract the VOD associated with this livestream', video_id=channel_name)

        access_token = self._download_access_token(
            channel_name, 'stream', 'channelName')

        stream_id = stream.get('id') or channel_name
        formats = self._extract_twitch_m3u8_formats(
            'api/channel/hls', channel_name, access_token['value'], access_token['signature'])
        self._prefer_source(formats)

        view_count = stream.get('viewers')

        sq_user = try_get(gql, lambda x: x[1]['data']['user'], dict) or {}
        uploader = sq_user.get('displayName')
        description = try_get(
            sq_user, lambda x: x['broadcastSettings']['title'], str)

        thumbnail = url_or_none(try_get(
            gql, lambda x: x[2]['data']['user']['stream']['previewImageURL'],
            str))

        title = uploader or channel_name
        stream_type = stream.get('type')
        if stream_type in ['rerun', 'live']:
            title += f' ({stream_type})'

        return {
            'id': stream_id,
            'display_id': channel_name,
            'title': title,
            'description': description,
            'thumbnails': self._get_thumbnails(thumbnail),
            'uploader': uploader,
            'uploader_id': channel_name,
            'timestamp': timestamp,
            'view_count': view_count,
            'formats': formats,
            'is_live': stream_type == 'live',
        }


class TwitchClipsIE(TwitchBaseIE):
    IE_NAME = 'twitch:clips'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            clips\.twitch\.tv/(?:embed\?.*?\bclip=|(?:[^/]+/)*)|
                            (?:(?:www|go|m)\.)?twitch\.tv/(?:[^/]+/)?clip/
                        )
                        (?P<id>[^/?#&]+)
                    '''

    _TESTS = [{
        'url': 'https://clips.twitch.tv/FaintLightGullWholeWheat',
        'md5': '761769e1eafce0ffebfb4089cb3847cd',
        'info_dict': {
            'id': '396245304',
            'display_id': 'FaintLightGullWholeWheat',
            'ext': 'mp4',
            'title': 'EA Play 2016 Live from the Novo Theatre',
            'duration': 32,
            'view_count': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1465767393,
            'upload_date': '20160612',
            'creators': ['EA'],
            'channel': 'EA',
            'channel_id': '25163635',
            'channel_is_verified': False,
            'channel_follower_count': int,
            'uploader': 'EA',
            'uploader_id': '25163635',
        },
    }, {
        'url': 'https://www.twitch.tv/xqc/clip/CulturedAmazingKuduDatSheffy-TiZ_-ixAGYR3y2Uy',
        'md5': 'e90fe616b36e722a8cfa562547c543f0',
        'info_dict': {
            'id': '3207364882',
            'display_id': 'CulturedAmazingKuduDatSheffy-TiZ_-ixAGYR3y2Uy',
            'ext': 'mp4',
            'title': 'A day in the life of xQc',
            'duration': 60,
            'view_count': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1742869615,
            'upload_date': '20250325',
            'creators': ['xQc'],
            'channel': 'xQc',
            'channel_id': '71092938',
            'channel_is_verified': True,
            'channel_follower_count': int,
            'uploader': 'xQc',
            'uploader_id': '71092938',
            'categories': ['Just Chatting'],
        },
    }, {
        # multiple formats
        'url': 'https://clips.twitch.tv/rflegendary/UninterestedBeeDAESuppy',
        'only_matching': True,
    }, {
        'url': 'https://www.twitch.tv/sergeynixon/clip/StormyThankfulSproutFutureMan',
        'only_matching': True,
    }, {
        'url': 'https://clips.twitch.tv/embed?clip=InquisitiveBreakableYogurtJebaited',
        'only_matching': True,
    }, {
        'url': 'https://m.twitch.tv/rossbroadcast/clip/ConfidentBraveHumanChefFrank',
        'only_matching': True,
    }, {
        'url': 'https://go.twitch.tv/rossbroadcast/clip/ConfidentBraveHumanChefFrank',
        'only_matching': True,
    }, {
        'url': 'https://m.twitch.tv/clip/FaintLightGullWholeWheat',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)

        clip = self._download_gql(
            slug, [{
                'operationName': 'ShareClipRenderStatus',
                'variables': {'slug': slug},
            }],
            'Downloading clip GraphQL')[0]['data']['clip']

        if not clip:
            raise ExtractorError(
                'This clip is no longer available', expected=True)

        access_query = {
            'sig': clip['playbackAccessToken']['signature'],
            'token': clip['playbackAccessToken']['value'],
        }
        asset_default = traverse_obj(clip, ('assets', 0, {dict})) or {}
        asset_portrait = traverse_obj(clip, ('assets', 1, {dict})) or {}

        formats = []
        default_aspect_ratio = float_or_none(asset_default.get('aspectRatio'))
        formats.extend(traverse_obj(asset_default, ('videoQualities', lambda _, v: url_or_none(v['sourceURL']), {
            'url': ('sourceURL', {update_url_query(query=access_query)}),
            'format_id': ('quality', {str}),
            'height': ('quality', {int_or_none}),
            'fps': ('frameRate', {float_or_none}),
            'aspect_ratio': {value(default_aspect_ratio)},
        })))
        portrait_aspect_ratio = float_or_none(asset_portrait.get('aspectRatio'))
        for source in traverse_obj(asset_portrait, ('videoQualities', lambda _, v: url_or_none(v['sourceURL']))):
            formats.append({
                'url': update_url_query(source['sourceURL'], access_query),
                'format_id': join_nonempty('portrait', source.get('quality')),
                'height': int_or_none(source.get('quality')),
                'fps': float_or_none(source.get('frameRate')),
                'aspect_ratio': portrait_aspect_ratio,
                'quality': -2,
            })

        thumbnails = []
        thumb_asset_default_url = url_or_none(asset_default.get('thumbnailURL'))
        if thumb_asset_default_url:
            thumbnails.append({
                'id': 'default',
                'url': thumb_asset_default_url,
                'preference': 0,
            })
        if thumb_asset_portrait_url := url_or_none(asset_portrait.get('thumbnailURL')):
            thumbnails.append({
                'id': 'portrait',
                'url': thumb_asset_portrait_url,
                'preference': -1,
            })
        thumb_default_url = url_or_none(clip.get('thumbnailURL'))
        if thumb_default_url and thumb_default_url != thumb_asset_default_url:
            thumbnails.append({
                'id': 'small',
                'url': thumb_default_url,
                'preference': -2,
            })

        old_id = self._search_regex(r'%7C(\d+)(?:-\d+)?.mp4', formats[-1]['url'], 'old id', default=None)

        return {
            'id': clip.get('id') or slug,
            '_old_archive_ids': [make_archive_id(self, old_id)] if old_id else None,
            'display_id': slug,
            'formats': formats,
            'thumbnails': thumbnails,
            **traverse_obj(clip, {
                'title': ('title', {str}),
                'duration': ('durationSeconds', {int_or_none}),
                'view_count': ('viewCount', {int_or_none}),
                'timestamp': ('createdAt', {parse_iso8601}),
                'creators': ('broadcaster', 'displayName', {str}, filter, all),
                'channel': ('broadcaster', 'displayName', {str}),
                'channel_id': ('broadcaster', 'id', {str}),
                'channel_follower_count': ('broadcaster', 'followers', 'totalCount', {int_or_none}),
                'channel_is_verified': ('broadcaster', 'isPartner', {bool}),
                'uploader': ('curator', 'displayName', {str}),
                'uploader_id': ('curator', 'id', {str}),
                'categories': ('game', 'displayName', {str}, filter, all, filter),
            }),
        }

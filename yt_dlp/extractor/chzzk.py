import functools

from .common import InfoExtractor
from ..utils import (
    UserNotLive,
    float_or_none,
    int_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class CHZZKLiveIE(InfoExtractor):
    IE_NAME = 'chzzk:live'
    _VALID_URL = r'https?://chzzk\.naver\.com/live/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://chzzk.naver.com/live/c68b8ef525fb3d2fa146344d84991753',
        'info_dict': {
            'id': 'c68b8ef525fb3d2fa146344d84991753',
            'ext': 'mp4',
            'title': str,
            'channel': '진짜도현',
            'channel_id': 'c68b8ef525fb3d2fa146344d84991753',
            'channel_is_verified': False,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1705510344,
            'upload_date': '20240117',
            'live_status': 'is_live',
            'view_count': int,
            'concurrent_view_count': int,
        },
        'skip': 'The channel is not currently live',
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        live_detail = self._download_json(
            f'https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail', channel_id,
            note='Downloading channel info', errnote='Unable to download channel info')['content']

        if live_detail.get('status') == 'CLOSE':
            raise UserNotLive(video_id=channel_id)

        live_playback = self._parse_json(live_detail['livePlaybackJson'], channel_id)

        thumbnails = []
        thumbnail_template = traverse_obj(
            live_playback, ('thumbnail', 'snapshotThumbnailTemplate', {url_or_none}))
        if thumbnail_template and '{type}' in thumbnail_template:
            for width in traverse_obj(live_playback, ('thumbnail', 'types', ..., {str})):
                thumbnails.append({
                    'id': width,
                    'url': thumbnail_template.replace('{type}', width),
                    'width': int_or_none(width),
                })

        formats, subtitles = [], {}
        for media in traverse_obj(live_playback, ('media', lambda _, v: url_or_none(v['path']))):
            is_low_latency = media.get('mediaId') == 'LLHLS'
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                media['path'], channel_id, 'mp4', fatal=False, live=True,
                m3u8_id='hls-ll' if is_low_latency else 'hls')
            for f in fmts:
                if is_low_latency:
                    f['source_preference'] = -2
                if '-afragalow.stream-audio.stream' in f['format_id']:
                    f['quality'] = -2
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': channel_id,
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            **traverse_obj(live_detail, {
                'title': ('liveTitle', {str}),
                'timestamp': ('openDate', {functools.partial(parse_iso8601, delimiter=' ')}),
                'concurrent_view_count': ('concurrentUserCount', {int_or_none}),
                'view_count': ('accumulateCount', {int_or_none}),
                'channel': ('channel', 'channelName', {str}),
                'channel_id': ('channel', 'channelId', {str}),
                'channel_is_verified': ('channel', 'verifiedMark', {bool}),
            }),
        }


def _make_vod_result(data):
    assert isinstance(data, dict)
    if not data.get('videoId'):
        return
    return {
        '_type': 'url_transparent',
        'id': data.get('videoId'),
        'title': data.get('videoTitle'),
        'url': f'https://chzzk.naver.com/video/{data.get("videoNo")}',
        'thumbnail': data.get('thumbnailImageUrl'),
        'timestamp': data.get('publishDateAt'),
        'view_count': data.get('readCount'),
        'duration': data.get('duration'),
        'age_limit': 19 if data.get('adult') else 0,
        'was_live': True if data.get('videoType') == 'REPLAY' else False,
    }


class CHZZKChannelIE(InfoExtractor):
    IE_NAME = 'chzzk:channel'
    _VALID_URL = r'https?://chzzk\.naver\.com/(?P<id>[\da-f]{32})'
    _TESTS = [{
        'note': 'Both video and replay included',
        'url': 'https://chzzk.naver.com/68f895c59a1043bc5019b5e08c83a5c5',
        'info_dict': {
            'id': '68f895c59a1043bc5019b5e08c83a5c5',
            'channel_id': '68f895c59a1043bc5019b5e08c83a5c5',
            'description': '나는 머찐 라디유 나는 머찐 라디유' * 26 + '나는 라디유',
            'channel': '라디유radiyu',
            'title': '라디유radiyu',
            'channel_is_verified': False,
        },
        'playlist_mincount': 4,
    }, {
        'note': 'Video list paging',
        'url': 'https://chzzk.naver.com/2d4aa2f79b0a397d032c479ef1b37a67',
        'info_dict': {
            'id': '2d4aa2f79b0a397d032c479ef1b37a67',
            'channel_id': '2d4aa2f79b0a397d032c479ef1b37a67',
            'description': '',
            'channel': '진짜후추',
            'title': '진짜후추',
            'channel_is_verified': False,
        },
        'playlist_mincount': 86,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        # even if channel got banned, the video list is still available. but downloading videos leads to error
        channel_meta = self._download_json(
            f'https://api.chzzk.naver.com/service/v1/channels/{channel_id}', channel_id,
            note='Downloading channel info', errnote='Unable to download channel info')
        if channel_meta.get('code') != 200:
            raise ExtractorError('The channel is not available: %s(%s)' % (
                channel_meta.get("message"), channel_meta.get("code")), expected=True)

        channel_meta = channel_meta.get('content')
        if not channel_meta or not channel_meta.get('channelId'):
            raise ExtractorError('The channel does not exist', expected=True)

        total_count = 0
        videos = []
        current_count = 0
        while current_count <= total_count:
            videos_page = self._download_json(
                f'https://api.chzzk.naver.com/service/v1/channels/{channel_id}/videos', channel_meta['channelName'],
                query={'sortType': 'LATEST', 'pagingType': 'PAGE', 'size': 18, 'videoType': '', 'page': current_count},
                note='Downloading videos page(%s/%s)' % (current_count + 1, total_count + 1), errnote='Unable to download videos page')
            if videos_page.get('code') != 200:
                raise ExtractorError('Unable to download videos page: %s(%s){videos_page.get("message")}' % (
                    videos_page.get("message"), videos_page.get("code")), expected=True)
            videos_page = videos_page['content']
            videos.extend(map(_make_vod_result, videos_page['data']))
            total_count = videos_page['totalPages']
            current_count += 1
        if len(videos) != total_count:
            self.to_screen('Warning: The total count of videos is not equal to the actual count: %s != %s' % (len(videos), total_count))

        return self.playlist_result(
            videos, channel_id, channel_meta['channelName'], channel_meta['channelDescription'],
            channel=channel_meta['channelName'], channel_id=channel_id, channel_is_verified=channel_meta['verifiedMark'],
        )


class CHZZKVideoIE(InfoExtractor):
    IE_NAME = 'chzzk:video'
    _VALID_URL = r'https?://chzzk\.naver\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://chzzk.naver.com/video/1754',
        'md5': 'b0c0c1bb888d913b93d702b1512c7f06',
        'info_dict': {
            'id': '1754',
            'ext': 'mp4',
            'title': '치지직 테스트 방송',
            'channel': '침착맨',
            'channel_id': 'bb382c2c0cc9fa7c86ab3b037fb5799c',
            'channel_is_verified': False,
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 15577,
            'timestamp': 1702970505.417,
            'upload_date': '20231219',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_meta = self._download_json(
            f'https://api.chzzk.naver.com/service/v2/videos/{video_id}', video_id,
            note='Downloading video info', errnote='Unable to download video info')['content']
        formats, subtitles = self._extract_mpd_formats_and_subtitles(
            f'https://apis.naver.com/neonplayer/vodplay/v1/playback/{video_meta["videoId"]}', video_id,
            query={
                'key': video_meta['inKey'],
                'env': 'real',
                'lc': 'en_US',
                'cpl': 'en_US',
            }, note='Downloading video playback', errnote='Unable to download video playback')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_meta, {
                'title': ('videoTitle', {str}),
                'thumbnail': ('thumbnailImageUrl', {url_or_none}),
                'timestamp': ('publishDateAt', {functools.partial(float_or_none, scale=1000)}),
                'view_count': ('readCount', {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'channel': ('channel', 'channelName', {str}),
                'channel_id': ('channel', 'channelId', {str}),
                'channel_is_verified': ('channel', 'verifiedMark', {bool}),
            }),
        }

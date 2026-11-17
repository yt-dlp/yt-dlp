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
            'thumbnail': r're:https?://.+/.+\.jpg',
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
            f'https://api.chzzk.naver.com/service/v3/channels/{channel_id}/live-detail', channel_id,
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
                'timestamp': ('openDate', {parse_iso8601(delimiter=' ')}),
                'concurrent_view_count': ('concurrentUserCount', {int_or_none}),
                'view_count': ('accumulateCount', {int_or_none}),
                'channel': ('channel', 'channelName', {str}),
                'channel_id': ('channel', 'channelId', {str}),
                'channel_is_verified': ('channel', 'verifiedMark', {bool}),
            }),
        }


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
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 15577,
            'timestamp': 1702970505.417,
            'upload_date': '20231219',
            'view_count': int,
        },
        'skip': 'Replay video is expired',
    }, {
        # Manually uploaded video
        'url': 'https://chzzk.naver.com/video/1980',
        'info_dict': {
            'id': '1980',
            'ext': 'mp4',
            'title': '※시청주의※한번보면 잊기 힘든 영상',
            'channel': '라디유radiyu',
            'channel_id': '68f895c59a1043bc5019b5e08c83a5c5',
            'channel_is_verified': False,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 95,
            'timestamp': 1703102631.722,
            'upload_date': '20231220',
            'view_count': int,
        },
    }, {
        # Partner channel replay video
        'url': 'https://chzzk.naver.com/video/2458',
        'info_dict': {
            'id': '2458',
            'ext': 'mp4',
            'title': '첫 방송',
            'channel': '강지',
            'channel_id': 'b5ed5db484d04faf4d150aedd362f34b',
            'channel_is_verified': True,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'duration': 4433,
            'timestamp': 1703307460.214,
            'upload_date': '20231223',
            'view_count': int,
        },
    }, {
        # video_status == 'NONE' but is downloadable
        'url': 'https://chzzk.naver.com/video/6325166',
        'info_dict': {
            'id': '6325166',
            'ext': 'mp4',
            'title': '와이프 숙제빼주기',
            'channel': '이 다',
            'channel_id': '0076a519f147ee9fd0959bf02f9571ca',
            'channel_is_verified': False,
            'view_count': int,
            'duration': 28167,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'timestamp': 1742139216.86,
            'upload_date': '20250316',
            'live_status': 'was_live',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_meta = self._download_json(
            f'https://api.chzzk.naver.com/service/v3/videos/{video_id}', video_id,
            note='Downloading video info', errnote='Unable to download video info')['content']

        live_status = 'was_live' if video_meta.get('liveOpenDate') else 'not_live'
        video_status = video_meta.get('vodStatus')
        if video_status == 'ABR_HLS':
            formats, subtitles = self._extract_mpd_formats_and_subtitles(
                f'https://apis.naver.com/neonplayer/vodplay/v1/playback/{video_meta["videoId"]}',
                video_id, query={
                    'key': video_meta['inKey'],
                    'env': 'real',
                    'lc': 'en_US',
                    'cpl': 'en_US',
                })
        else:
            fatal = video_status == 'UPLOAD'
            playback = self._parse_json(video_meta['liveRewindPlaybackJson'], video_id, fatal=fatal)
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                traverse_obj(playback, ('media', 0, 'path')), video_id, 'mp4', m3u8_id='hls', fatal=fatal)
            if formats and video_status != 'UPLOAD':
                self.write_debug(f'Video found with status: "{video_status}"')
            elif not formats:
                self.raise_no_formats(
                    f'Unknown video status detected: "{video_status}"', expected=True, video_id=video_id)
                formats, subtitles = [], {}
                live_status = 'post_live' if live_status == 'was_live' else None

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'live_status': live_status,
            **traverse_obj(video_meta, {
                'title': ('videoTitle', {str}),
                'thumbnail': ('thumbnailImageUrl', {url_or_none}),
                'timestamp': ('publishDateAt', {float_or_none(scale=1000)}),
                'view_count': ('readCount', {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'channel': ('channel', 'channelName', {str}),
                'channel_id': ('channel', 'channelId', {str}),
                'channel_is_verified': ('channel', 'verifiedMark', {bool}),
            }),
        }

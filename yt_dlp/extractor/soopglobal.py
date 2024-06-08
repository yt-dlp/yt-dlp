import uuid

from yt_dlp import int_or_none, traverse_obj
from yt_dlp.compat import functools
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import UserNotLive, bool_or_none, parse_iso8601


class SoopGlobalLiveIE(InfoExtractor):
    IE_NAME = 'soopglobal:live'
    _VALID_URL = r'https?://www\.sooplive\.com/(?P<id>[\w]+$)'
    _TESTS = [{
        'url': 'https://www.sooplive.com/soopbowl',
        'info_dict': {
            'id': 'soopbowl',
            'ext': 'mp4',
            'title': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'channel': 'SoopBowl',
            'channel_id': 'soopbowl',
            'concurrent_view_count': int,
            'channel_follower_count': int,
            'timestamp': 1717852526,
            'upload_date': '20240608',
            'live_status': 'is_live',
            'view_count': int,
            'age_limit': False,
        },
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        client_id = str(uuid.uuid4())
        live_detail = self._download_json(
            f'https://api.sooplive.com/stream/info/{channel_id}', channel_id,
            headers={'client-id': client_id},
            note='Downloading live info', errnote='Unable to download live info')
        if not live_detail.get('isStream'):
            raise UserNotLive(video_id=channel_id)

        age_limit = 0
        if traverse_obj(live_detail, ('data', 'isAdult', {bool_or_none})):
            age_limit = 19

        live_statistic = self._download_json(
            f'https://api.sooplive.com/stream/info/{channel_id}/live', channel_id,
            headers={'client-id': client_id},
            note='Downloading live statistics', errnote='Unable to download live statistics')

        channel_info = self._download_json(
            f'https://api.sooplive.com/channel/info/{channel_id}', channel_id,
            headers={'client-id': client_id},
            note='Downloading channel information', errnote='Unable to download channel information')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://api.sooplive.com/media/live/{channel_id}/master.m3u8', channel_id,
            headers={'client-id': client_id},
            note='Downloading live stream', errnote='Unable to download live stream')

        return {
            'id': channel_id,
            'channel_id': channel_id,
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
            'view_count': live_statistic.get('viewer'),
            'age_limit': age_limit,
            **traverse_obj(channel_info.get('streamerChannelInfo'), {
                'channel': ('nickname', {str}),
                'channel_id': ('channelId', {str}),
                'channel_follower_count': ('totalFollowerCount', {int_or_none}),
            }),
            **traverse_obj(live_detail.get('data'), {
                'title': ('title', {str}),
                'timestamp': ('streamStartDate', {functools.partial(parse_iso8601)}),
                'concurrent_view_count': ('totalStreamCumulativeViewer', {int_or_none}),
                'thumbnail': ('thumbnailUrl', {str}),
            }),
        }


class SoopGlobalVodIE(InfoExtractor):
    IE_NAME = 'soopglobal:vod'
    _VALID_URL = r'https?://www\.sooplive\.com/video/(?P<id>[\d]+)'
    _TESTS = [{
        'url': 'https://www.sooplive.com/video/607',
        'info_dict': {
            'id': '607',
            'ext': 'mp4',
            'title': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'channel': '샤미요',
            'channel_id': 'shamiyo',
            'timestamp': 1717051284,
            'upload_date': '20240530',
            'view_count': int,
            'age_limit': False,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        client_id = str(uuid.uuid4())
        video_info = self._download_json(
            f'https://api.sooplive.com/vod/info/{video_id}', video_id,
            headers={'client-id': client_id},
            note='Downloading video info', errnote='Unable to download video info')
        channel_id = video_info.get('channelId')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://api.sooplive.com/media/vod/{channel_id}/{video_id}/master.m3u8', video_id,
            headers={'client-id': client_id},
            note='Downloading video stream', errnote='Unable to download video stream')
        return {
            'id': video_id,
            'channel': video_info.get('nickName'),
            'channel_id': channel_id,
            'title': video_info.get('titleName'),
            'thumbnail': video_info.get('thumb'),
            'timestamp': parse_iso8601(video_info.get('createDate')),
            'view_count': video_info.get('readCnt'),
            'age_limit': 0 if not video_info.get('isAdult') else 19,
            'formats': formats,
            'subtitles': subtitles,
        }

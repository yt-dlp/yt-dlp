from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    parse_iso8601,
)


class CHZZKLiveIE(InfoExtractor):
    IE_NAME = 'chzzk:live'
    _VALID_URL = r'https?://chzzk\.naver\.com/live/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://chzzk.naver.com/live/c68b8ef525fb3d2fa146344d84991753',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        live_detail_response = self._download_json(
            f'https://api.chzzk.naver.com/service/v1/channels/{channel_id}/live-detail', channel_id,
            note='Downloading channel info',
            errnote='Unable to download channel info')
        live_detail = live_detail_response.get('content')

        if live_detail.get('status') == 'CLOSE':
            raise ExtractorError('The channel is not currently live', expected=True)

        live_playback = self._parse_json(live_detail.get('livePlaybackJson'), channel_id)

        thumbnails = []
        thumbnail_template = traverse_obj(live_playback, ('thumbnail', 'snapshotThumbnailTemplate'))
        for width in traverse_obj(live_playback, ('thumbnail', 'types')):
            thumbnails.append({
                'id': width,
                'url': thumbnail_template.replace('{type}', width),
                'width': int(width),
            })

        formats, subtitles = [], {}
        for media in live_playback.get('media'):
            media_url = media.get('path')
            fmts, subs = self._extract_m3u8_formats_and_subtitles(media_url, channel_id, 'mp4')
            if media.get('mediaId') == 'LLHLS':
                for fmt in fmts:
                    fmt['format_id'] += '-ll'
            formats.extend(fmts)
            self._merge_subtitles(subtitles, subs)

        return {
            'id': str(channel_id),
            'title': live_detail.get('liveTitle'),
            'thumbnails': thumbnails,
            'timestamp': parse_iso8601(live_detail.get('openDate')),
            'view_count': live_detail.get('concurrentUserCount'),
            'channel': traverse_obj(live_detail, ('channel', 'channelName')),
            'channel_id': traverse_obj(live_detail, ('channel', 'channelId')),
            'channel_is_verified': traverse_obj(live_detail, ('channel', 'verifiedMark')),
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
        }


class CHZZKVideoIE(InfoExtractor):
    IE_NAME = 'chzzk:video'
    _VALID_URL = r'https?://chzzk\.naver\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://chzzk.naver.com/video/1754',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        NS_MAP = {
            'nvod': "urn:naver:vod:2020",
            '': "urn:mpeg:dash:schema:mpd:2011",
        }

        video_id = self._match_id(url)
        video_meta_response = self._download_json(
            f'https://api.chzzk.naver.com/service/v1/videos/{video_id}', video_id,
            note='Downloading video info',
            errnote='Unable to download video info')
        video_meta = video_meta_response.get('content')
        vod_id = video_meta.get('videoId')
        in_key = video_meta.get('inKey')
        playback_xml = self._download_xml(
            f'https://apis.naver.com/neonplayer/vodplay/v1/playback/{vod_id}', video_id,
            query={
                'key': in_key,
                'env': 'real',
                'lc': 'en_US',
                'cpl': 'en_US',
            },
            note='Downloading video playback',
            errnote='Unable to download video playback')

        thumbnails = []
        i = 0
        for source in playback_xml.iterfind(
            './Period/SupplementalProperty/nvod:Thumbnails/nvod:ThumbnailSet/nvod:Thumbnail/nvod:Source',
            NS_MAP,
        ):
            thumbnails.append({'id': str(i), 'url': source.text.split('?')[0]})
            i += 1

        formats, subtitles = self._parse_mpd_formats_and_subtitles(playback_xml)

        return {
            'id': video_id,
            'title': video_meta.get('videoTitle'),
            'thumbnail': video_meta.get('thumbnailImageUrl'),
            'thumbnails': thumbnails,
            'timestamp': video_meta.get('publishDateAt'),
            'view_count': video_meta.get('readCount'),
            'duration': video_meta.get('duration'),
            'channel': traverse_obj(video_meta, ('channel', 'channelName')),
            'channel_id': traverse_obj(video_meta, ('channel', 'channelId')),
            'channel_is_verified': traverse_obj(video_meta, ('channel', 'verifiedMark')),
            'formats': formats,
            'subtitles': subtitles,
        }

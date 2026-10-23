from ._tab import YoutubeTabBaseInfoExtractor
from ._video import YoutubeIE
from ...utils import ExtractorError, traverse_obj


class YoutubeClipIE(YoutubeTabBaseInfoExtractor):
    IE_NAME = 'youtube:clip'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/clip/(?P<id>[^/?#]+)'
    _TESTS = [{
        # FIXME: Other metadata should be extracted from the clip, not from the base video
        'url': 'https://www.youtube.com/clip/UgytZKpehg-hEMBSn3F4AaABCQ',
        'info_dict': {
            'id': 'UgytZKpehg-hEMBSn3F4AaABCQ',
            'ext': 'mp4',
            'section_start': 29.0,
            'section_end': 39.7,
            'duration': 10.7,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Gaming'],
            'channel': 'Scott The Woz',
            'channel_id': 'UC4rqhyiTs7XyuODcECvuiiQ',
            'channel_url': 'https://www.youtube.com/channel/UC4rqhyiTs7XyuODcECvuiiQ',
            'description': 'md5:7a4517a17ea9b4bd98996399d8bb36e7',
            'like_count': int,
            'playable_in_embed': True,
            'tags': 'count:17',
            'thumbnail': 'https://i.ytimg.com/vi_webp/ScPX26pdQik/maxresdefault.webp',
            'title': 'Mobile Games on Console - Scott The Woz',
            'upload_date': '20210920',
            'uploader': 'Scott The Woz',
            'uploader_id': '@ScottTheWoz',
            'uploader_url': 'https://www.youtube.com/@ScottTheWoz',
            'view_count': int,
            'live_status': 'not_live',
            'channel_follower_count': int,
            'chapters': 'count:20',
            'comment_count': int,
            'heatmap': 'count:100',
            'media_type': 'clip',
        },
    }]

    def _real_extract(self, url):
        clip_id = self._match_id(url)
        _, data = self._extract_webpage(url, clip_id)

        video_id = traverse_obj(data, ('currentVideoEndpoint', 'watchEndpoint', 'videoId'))
        if not video_id:
            raise ExtractorError('Unable to find video ID')

        clip_data = traverse_obj(data, (
            'engagementPanels', ..., 'engagementPanelSectionListRenderer', 'content', 'clipSectionRenderer',
            'contents', ..., 'clipAttributionRenderer', 'onScrubExit', 'commandExecutorCommand', 'commands', ...,
            'openPopupAction', 'popup', 'notificationActionRenderer', 'actionButton', 'buttonRenderer', 'command',
            'commandExecutorCommand', 'commands', ..., 'loopCommand'), get_all=False)

        return {
            '_type': 'url_transparent',
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'ie_key': YoutubeIE.ie_key(),
            'id': clip_id,
            'media_type': 'clip',
            'section_start': int(clip_data['startTimeMs']) / 1000,
            'section_end': int(clip_data['endTimeMs']) / 1000,
            '_format_sort_fields': (  # https protocol is prioritized for ffmpeg compatibility
                'proto:https', 'quality', 'res', 'fps', 'hdr:12', 'source', 'vcodec', 'channels', 'acodec', 'lang'),
        }

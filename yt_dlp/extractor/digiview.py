from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import clean_html, int_or_none, traverse_obj, url_or_none, urlencode_postdata


class DigiviewIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ladigitale\.dev/digiview/#/v/(?P<id>[0-9a-f]+)'
    _TESTS = [{
        # normal video
        'url': 'https://ladigitale.dev/digiview/#/v/67a8e50aee2ec',
        'info_dict': {
            'id': '67a8e50aee2ec',
            'ext': 'mp4',
            'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
            'thumbnail': 'https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg',
            'upload_date': '20141110',
            'playable_in_embed': True,
            'duration': 635,
            'view_count': int,
            'comment_count': int,
            'channel': 'Blender',
            'license': 'Creative Commons Attribution license (reuse allowed)',
            'like_count': int,
            'tags': 'count:8',
            'live_status': 'not_live',
            'channel_id': 'UCSMOQeBJ2RAnuFungnQOxLg',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCSMOQeBJ2RAnuFungnQOxLg',
            'uploader_id': '@BlenderOfficial',
            'description': 'md5:8f3ed18a53a1bb36cbb3b70a15782fd0',
            'categories': ['Film & Animation'],
            'channel_is_verified': True,
            'heatmap': 'count:100',
            'section_end': 635,
            'uploader': 'Blender',
            'timestamp': 1415628355,
            'uploader_url': 'https://www.youtube.com/@BlenderOfficial',
            'age_limit': 0,
            'section_start': 0,
            'availability': 'public',
        },
    }, {
        # cut video
        'url': 'https://ladigitale.dev/digiview/#/v/67a8e51d0dd58',
        'info_dict': {
            'id': '67a8e51d0dd58',
            'ext': 'mp4',
            'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
            'thumbnail': 'https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg',
            'upload_date': '20141110',
            'playable_in_embed': True,
            'duration': 5,
            'view_count': int,
            'comment_count': int,
            'channel': 'Blender',
            'license': 'Creative Commons Attribution license (reuse allowed)',
            'like_count': int,
            'tags': 'count:8',
            'live_status': 'not_live',
            'channel_id': 'UCSMOQeBJ2RAnuFungnQOxLg',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCSMOQeBJ2RAnuFungnQOxLg',
            'uploader_id': '@BlenderOfficial',
            'description': 'md5:8f3ed18a53a1bb36cbb3b70a15782fd0',
            'categories': ['Film & Animation'],
            'channel_is_verified': True,
            'heatmap': 'count:100',
            'section_end': 10,
            'uploader': 'Blender',
            'timestamp': 1415628355,
            'uploader_url': 'https://www.youtube.com/@BlenderOfficial',
            'age_limit': 0,
            'section_start': 5,
            'availability': 'public',
        },
    }, {
        # changed title
        'url': 'https://ladigitale.dev/digiview/#/v/67a8ea5644d7a',
        'info_dict': {
            'id': '67a8ea5644d7a',
            'ext': 'mp4',
            'title': 'Big Buck Bunny (with title changed)',
            'thumbnail': 'https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg',
            'upload_date': '20141110',
            'playable_in_embed': True,
            'duration': 5,
            'view_count': int,
            'comment_count': int,
            'channel': 'Blender',
            'license': 'Creative Commons Attribution license (reuse allowed)',
            'like_count': int,
            'tags': 'count:8',
            'live_status': 'not_live',
            'channel_id': 'UCSMOQeBJ2RAnuFungnQOxLg',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCSMOQeBJ2RAnuFungnQOxLg',
            'uploader_id': '@BlenderOfficial',
            'description': 'md5:8f3ed18a53a1bb36cbb3b70a15782fd0',
            'categories': ['Film & Animation'],
            'channel_is_verified': True,
            'heatmap': 'count:100',
            'section_end': 15,
            'uploader': 'Blender',
            'timestamp': 1415628355,
            'uploader_url': 'https://www.youtube.com/@BlenderOfficial',
            'age_limit': 0,
            'section_start': 10,
            'availability': 'public',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            'https://ladigitale.dev/digiview/inc/recuperer_video.php', video_id,
            data=urlencode_postdata({'id': video_id}))

        clip_id = video_data['videoId']
        return self.url_result(
            f'https://www.youtube.com/watch?v={clip_id}',
            YoutubeIE, video_id, url_transparent=True,
            **traverse_obj(video_data, {
                'section_start': ('debut', {int_or_none}),
                'section_end': ('fin', {int_or_none}),
                'description': ('description', {clean_html}, filter),
                'title': ('titre', {str}),
                'thumbnail': ('vignette', {url_or_none}),
                'view_count': ('vues', {int_or_none}),
            }),
        )

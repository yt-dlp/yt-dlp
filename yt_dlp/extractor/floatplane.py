from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    parse_iso8601,
    determine_ext,
    unified_strdate,
    traverse_obj
)


class FloatplaneIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:www\.)?floatplane\.com/post/(?P<id>[a-zA-Z0-9-]+))'
    _TESTS = [{
        'url': 'https://www.floatplane.com/post/DdShecU983',
        'info_dict': {
            'id': 'DdShecU983',
            'ext': 'mp4',
            'title': 'TQ: Are Intel Arc Graphics A Bad Idea?',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'skip': 'Requires premium Floatplane account',
    }]

    def _real_initialize(self):
        self._download_webpage(
            'https://www.floatplane.com/', None,
            note='Fetching session cookie')

        sessionIdCookie = self._get_cookies(
            'https://www.floatplane.com').get('sails.sid')

        if sessionIdCookie is None:
            raise ExtractorError(
                'Cookie not found for floatplane.com.  Please login in your browser and retype', expected=True)

        self.session_id = sessionIdCookie.value

    def _real_extract(self, url):
        post_id = self._match_id(url)

        self._set_cookie("floatplane.com", "Cookie", f'sails.sid={self.session_id}')

        post_metadata = self._download_json(
            f'https://www.floatplane.com/api/v3/content/post?id={post_id}', post_id, note='Fetching post details')

        if not traverse_obj(post_metadata, ('metadata', 'hasVideo')):
            raise ExtractorError(
                'Provided Floatplane post does not contain a video', expected=True)

        video_id = traverse_obj(post_metadata, ('videoAttachments', 0, 'id'))

        video_metadata = self._download_json(
            f'https://www.floatplane.com/api/v3/content/video?id={video_id}', post_id, note='Fetching video details')

        video_format_metadata = self._download_json(
            f'https://www.floatplane.com/api/v2/cdn/delivery?type=vod&guid={video_metadata["guid"]}', post_id, note='Fetching video format details')

        # Generate formats
        remote_qualities = traverse_obj(
            video_format_metadata, ('resource', 'data', 'qualityLevels'))
        remote_qualities_params = traverse_obj(
            video_format_metadata, ('resource', 'data', 'qualityLevelParams'))
        remote_cdn = video_format_metadata['cdn']
        format_path_template = traverse_obj(
            video_format_metadata, ('resource', 'uri'))
        formats = []
        for current_format in remote_qualities:
            current_params = remote_qualities_params[current_format['name']]
            extension = determine_ext(current_params["2"])  # Get 'mp4' from '720p.mp4'

            replaced_path = format_path_template.replace('{qualityLevelParams.2}', current_params['2']).replace(
                '{qualityLevelParams.4}', current_params['4'])

            formats.append({
                'format_id': current_format['name'],
                'width': current_format.get('width'),
                'height': current_format.get('height'),
                'url': f"{remote_cdn}{replaced_path}",
                'ext': extension
            })

        creator_id = traverse_obj(post_metadata, ('creator', 'id'))
        creator_url_name = traverse_obj(post_metadata, ('creator', 'urlname'))

        creator_api_url = f"https://www.floatplane.com/api/v2/plan/info?creatorId={creator_id}"

        creator_metadata = self._download_json(
            creator_api_url, post_id, note='Fetching creator details')

        return {
            'url': url,
            'webpage_url': url,
            'id': post_id,
            'title': post_metadata['title'],
            'description': post_metadata.get('text'),

            'channel': traverse_obj(post_metadata, ('creator', 'title')),
            'channel_id': creator_id,
            'channel_url': f"https://www.floatplane.com/channel/{creator_url_name}/home",
            'channel_follower_count': creator_metadata['totalSubscriberCount'],

            # Video metadata
            'formats': formats,
            'duration': video_metadata['duration'],
            'thumbnail': traverse_obj(video_metadata, ('thumbnail', 'path')),

            # Post metadata
            'like_count': post_metadata['likes'],
            'dislike_count': post_metadata['dislikes'],
            'comment_count': post_metadata['comments'],
            'release_timestamp': parse_iso8601(post_metadata['releaseDate']),
            'release_date': unified_strdate(post_metadata['releaseDate']),

            # I think all content on Floatplane is 'premium' only?
            'availability': self._availability(needs_premium=True),
        }

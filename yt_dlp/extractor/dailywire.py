import json

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    traverse_obj,
    unified_timestamp,
)


class DailyWireIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dailywire\.com/episode/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.dailywire.com/episode/1-fauci',
        'info_dict': {
            'id': 'ckzsl50xnqpy30850in3v4bu7',
            'ext': 'mp4',
            'display_id': '1-fauci',
            'title': '1. Fauci',
            'description': 'md5:9df630347ef85081b7e97dd30bc22853',
            'thumbnail': r're:https://daily-wire-production\.imgix\.net/episodes/ckzsl50xnqpy30850in3v4bu7/.+\.jpg',
            'series_id': 'ckzplm0a097fn0826r2vc3j7h',
            'series': 'China: The Enemy Within',
            'duration': 1391.681967,
            'upload_date': '20220218',
            'timestamp': 1645182003,
            'uploader': 'China: The Enemy Within',
            'uploader_id': 'china-the-enemy-within',
            'uploader_url': 'https://www.dailywire.com/show/china-the-enemy-within',
            'channel': 'China: The Enemy Within',
            'channel_id': 'china-the-enemy-within',
            'channel_url': 'https://www.dailywire.com/show/china-the-enemy-within',
            'availability': 'public',
        },
    }, {
        'url': 'https://www.dailywire.com/episode/ep-124-bill-maher',
        'info_dict': {
            'id': 'cl0ngbaalplc80894sfdo9edf',
            'ext': 'mp4',
            'display_id': 'ep-124-bill-maher',
            'title': 'Ep. 124 - Bill Maher',
            'description': 'md5:adb0de584bcfa9c41374999d9e324e98',
            'thumbnail': r're:https://daily-wire-production\.imgix\.net/episodes/.+\.jpg',
            'series_id': 'cjzvep7270hp00786l9hwccob',
            'series': 'The Sunday Special',
            'duration': 3976.605967,
            'upload_date': '20220312',
            'timestamp': 1647065568,
            'uploader': 'The Sunday Special',
            'uploader_id': 'sunday-special',
            'uploader_url': 'https://www.dailywire.com/show/sunday-special',
            'channel': 'The Sunday Special',
            'channel_id': 'sunday-special',
            'channel_url': 'https://www.dailywire.com/show/sunday-special',
            'availability': 'subscriber_only',
        },
        'skip': 'requires subscription',
    }]

    _GRAPHQL_QUERY = '''
query getEpisodeBySlug($slug: String!) {
  episode(where: {slug: $slug}) {
    id
    title
    status
    slug
    isLive
    description
    createdAt
    scheduleAt
    image
    show {
      id
      name
      slug
    }
    segments {
      id
      title
      video
      duration
      videoAccess
    }
  }
}'''

    def _real_extract(self, url):
        slug = self._match_id(url)

        # Get access token from cookies for authentication
        access_token = self._get_cookies('https://www.dailywire.com').get('accessToken')
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://www.dailywire.com',
            'Referer': 'https://www.dailywire.com/',
            'apollographql-client-name': 'DW_WEBSITE',
        }
        if access_token:
            headers['Authorization'] = f'Bearer {access_token.value}'

        # Fetch episode data from GraphQL API (returns video URL with auth token for subscribers)
        gql_response = self._download_json(
            'https://v2server.dailywire.com/app/graphql', slug,
            headers=headers,
            data=json.dumps({
                'query': self._GRAPHQL_QUERY,
                'variables': {'slug': slug},
                'operationName': 'getEpisodeBySlug',
            }).encode())

        episode_info = traverse_obj(gql_response, ('data', 'episode')) or {}
        segment = traverse_obj(episode_info, ('segments', 0)) or {}

        video_url = segment.get('video')
        if not video_url or video_url == 'Access Denied':
            self.raise_login_required('This content requires a subscription')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_url, slug, 'mp4')

        show_name = traverse_obj(episode_info, ('show', 'name'))
        show_slug = traverse_obj(episode_info, ('show', 'slug'))

        video_access = segment.get('videoAccess') or []
        # Empty videoAccess means free/public content; non-empty means subscriber-only
        availability = 'public' if not video_access else 'subscriber_only'

        return {
            'id': episode_info['id'],
            'display_id': slug,
            'title': episode_info.get('title'),
            'description': episode_info.get('description'),
            'duration': float_or_none(segment.get('duration')),
            'is_live': episode_info.get('isLive'),
            'thumbnail': episode_info.get('image'),
            'formats': formats,
            'subtitles': subtitles,
            'series_id': traverse_obj(episode_info, ('show', 'id')),
            'series': show_name,
            'timestamp': unified_timestamp(episode_info.get('createdAt')),
            'release_timestamp': unified_timestamp(episode_info.get('scheduleAt')),
            'uploader': show_name,
            'uploader_id': show_slug,
            'uploader_url': f'https://www.dailywire.com/show/{show_slug}' if show_slug else None,
            'channel': show_name,
            'channel_id': show_slug,
            'channel_url': f'https://www.dailywire.com/show/{show_slug}' if show_slug else None,
            'availability': availability,
        }

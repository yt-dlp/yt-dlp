import functools

from .common import InfoExtractor
from ..utils import (
    format_field,
    int_or_none,
    OnDemandPagedList,
    smuggle_url,
)


class StoryFireBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?storyfire\.com/'

    def _call_api(self, path, video_id, resource, query=None):
        return self._download_json(
            'https://storyfire.com/app/%s/%s' % (path, video_id), video_id,
            'Downloading %s JSON metadata' % resource, query=query)

    def _parse_video(self, video):
        title = video['title']
        vimeo_id = self._search_regex(
            r'https?://player\.vimeo\.com/external/(\d+)',
            video['vimeoVideoURL'], 'vimeo id')

        uploader_id = video.get('hostID')

        return {
            '_type': 'url_transparent',
            'id': vimeo_id,
            'title': title,
            'description': video.get('description'),
            'url': smuggle_url(
                'https://player.vimeo.com/video/' + vimeo_id, {
                    'http_headers': {
                        'Referer': 'https://storyfire.com/',
                    }
                }),
            'thumbnail': video.get('storyImage'),
            'view_count': int_or_none(video.get('views')),
            'like_count': int_or_none(video.get('likesCount')),
            'comment_count': int_or_none(video.get('commentsCount')),
            'duration': int_or_none(video.get('videoDuration')),
            'timestamp': int_or_none(video.get('publishDate')),
            'uploader': video.get('username'),
            'uploader_id': uploader_id,
            'uploader_url': format_field(uploader_id, template='https://storyfire.com/user/%s/video'),
            'episode_number': int_or_none(video.get('episodeNumber') or video.get('episode_number')),
        }


class StoryFireIE(StoryFireBaseIE):
    _VALID_URL = StoryFireBaseIE._VALID_URL_BASE + r'video-details/(?P<id>[0-9a-f]{24})'
    _TEST = {
        'url': 'https://storyfire.com/video-details/5df1d132b6378700117f9181',
        'md5': 'caec54b9e4621186d6079c7ec100c1eb',
        'info_dict': {
            'id': '378954662',
            'ext': 'mp4',
            'title': 'Buzzfeed Teaches You About Memes',
            'uploader_id': 'ntZAJFECERSgqHSxzonV5K2E89s1',
            'timestamp': 1576129028,
            'description': 'md5:0b4e28021548e144bed69bb7539e62ea',
            'uploader': 'whang!',
            'upload_date': '20191212',
            'duration': 418,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download JSON metadata']
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video = self._call_api(
            'generic/video-detail', video_id, 'video')['video']
        return self._parse_video(video)


class StoryFireUserIE(StoryFireBaseIE):
    _VALID_URL = StoryFireBaseIE._VALID_URL_BASE + r'user/(?P<id>[^/]+)/video'
    _TEST = {
        'url': 'https://storyfire.com/user/UQ986nFxmAWIgnkZQ0ftVhq4nOk2/video',
        'info_dict': {
            'id': 'UQ986nFxmAWIgnkZQ0ftVhq4nOk2',
        },
        'playlist_mincount': 151,
    }
    _PAGE_SIZE = 20

    def _fetch_page(self, user_id, page):
        videos = self._call_api(
            'publicVideos', user_id, 'page %d' % (page + 1), {
                'skip': page * self._PAGE_SIZE,
            })['videos']
        for video in videos:
            yield self._parse_video(video)

    def _real_extract(self, url):
        user_id = self._match_id(url)
        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, user_id), self._PAGE_SIZE)
        return self.playlist_result(entries, user_id)


class StoryFireSeriesIE(StoryFireBaseIE):
    _VALID_URL = StoryFireBaseIE._VALID_URL_BASE + r'write/series/stories/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://storyfire.com/write/series/stories/-Lq6MsuIHLODO6d2dDkr/',
        'info_dict': {
            'id': '-Lq6MsuIHLODO6d2dDkr',
        },
        'playlist_mincount': 13,
    }, {
        'url': 'https://storyfire.com/write/series/stories/the_mortal_one/',
        'info_dict': {
            'id': 'the_mortal_one',
        },
        'playlist_count': 0,
    }]

    def _extract_videos(self, stories):
        for story in stories.values():
            if story.get('hasVideo'):
                yield self._parse_video(story)

    def _real_extract(self, url):
        series_id = self._match_id(url)
        stories = self._call_api(
            'seriesStories', series_id, 'series stories')
        return self.playlist_result(self._extract_videos(stories), series_id)

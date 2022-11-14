from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    clean_html,
    format_field,
    int_or_none,
    str_or_none,
    strip_or_none,
)


class MindsBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?minds\.com/'

    def _call_api(self, path, video_id, resource, query=None):
        api_url = 'https://www.minds.com/api/' + path
        token = self._get_cookies(api_url).get('XSRF-TOKEN')
        return self._download_json(
            api_url, video_id, 'Downloading %s JSON metadata' % resource, headers={
                'Referer': 'https://www.minds.com/',
                'X-XSRF-TOKEN': token.value if token else '',
            }, query=query)


class MindsIE(MindsBaseIE):
    IE_NAME = 'minds'
    _VALID_URL = MindsBaseIE._VALID_URL_BASE + r'(?:media|newsfeed|archive/view)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.minds.com/media/100000000000086822',
        'md5': '215a658184a419764852239d4970b045',
        'info_dict': {
            'id': '100000000000086822',
            'ext': 'mp4',
            'title': 'Minds intro sequence',
            'thumbnail': r're:https?://.+\.png',
            'uploader_id': 'ottman',
            'upload_date': '20130524',
            'timestamp': 1369404826,
            'uploader': 'Bill Ottman',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'tags': ['animation'],
            'comment_count': int,
            'license': 'attribution-cc',
        },
    }, {
        # entity.type == 'activity' and empty title
        'url': 'https://www.minds.com/newsfeed/798025111988506624',
        'md5': 'b2733a74af78d7fd3f541c4cbbaa5950',
        'info_dict': {
            'id': '798022190320226304',
            'ext': 'mp4',
            'title': '798022190320226304',
            'uploader': 'ColinFlaherty',
            'upload_date': '20180111',
            'timestamp': 1515639316,
            'uploader_id': 'ColinFlaherty',
        },
    }, {
        'url': 'https://www.minds.com/archive/view/715172106794442752',
        'only_matching': True,
    }, {
        # youtube perma_url
        'url': 'https://www.minds.com/newsfeed/1197131838022602752',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        entity_id = self._match_id(url)
        entity = self._call_api(
            'v1/entities/entity/' + entity_id, entity_id, 'entity')['entity']
        if entity.get('type') == 'activity':
            if entity.get('custom_type') == 'video':
                video_id = entity['entity_guid']
            else:
                return self.url_result(entity['perma_url'])
        else:
            assert entity['subtype'] == 'video'
            video_id = entity_id
        # 1080p and webm formats available only on the sources array
        video = self._call_api(
            'v2/media/video/' + video_id, video_id, 'video')

        formats = []
        for source in (video.get('sources') or []):
            src = source.get('src')
            if not src:
                continue
            formats.append({
                'format_id': source.get('label'),
                'height': int_or_none(source.get('size')),
                'url': src,
            })
        self._sort_formats(formats)

        entity = video.get('entity') or entity
        owner = entity.get('ownerObj') or {}
        uploader_id = owner.get('username')

        tags = entity.get('tags')
        if tags and isinstance(tags, compat_str):
            tags = [tags]

        thumbnail = None
        poster = video.get('poster') or entity.get('thumbnail_src')
        if poster:
            urlh = self._request_webpage(poster, video_id, fatal=False)
            if urlh:
                thumbnail = urlh.geturl()

        return {
            'id': video_id,
            'title': entity.get('title') or video_id,
            'formats': formats,
            'description': clean_html(entity.get('description')) or None,
            'license': str_or_none(entity.get('license')),
            'timestamp': int_or_none(entity.get('time_created')),
            'uploader': strip_or_none(owner.get('name')),
            'uploader_id': uploader_id,
            'uploader_url': format_field(uploader_id, None, 'https://www.minds.com/%s'),
            'view_count': int_or_none(entity.get('play:count')),
            'like_count': int_or_none(entity.get('thumbs:up:count')),
            'dislike_count': int_or_none(entity.get('thumbs:down:count')),
            'tags': tags,
            'comment_count': int_or_none(entity.get('comments:count')),
            'thumbnail': thumbnail,
        }


class MindsFeedBaseIE(MindsBaseIE):
    _PAGE_SIZE = 150

    def _entries(self, feed_id):
        query = {'limit': self._PAGE_SIZE, 'sync': 1}
        i = 1
        while True:
            data = self._call_api(
                'v2/feeds/container/%s/videos' % feed_id,
                feed_id, 'page %s' % i, query)
            entities = data.get('entities') or []
            for entity in entities:
                guid = entity.get('guid')
                if not guid:
                    continue
                yield self.url_result(
                    'https://www.minds.com/newsfeed/' + guid,
                    MindsIE.ie_key(), guid)
            query['from_timestamp'] = data['load-next']
            if not (query['from_timestamp'] and len(entities) == self._PAGE_SIZE):
                break
            i += 1

    def _real_extract(self, url):
        feed_id = self._match_id(url)
        feed = self._call_api(
            'v1/%s/%s' % (self._FEED_PATH, feed_id),
            feed_id, self._FEED_TYPE)[self._FEED_TYPE]

        return self.playlist_result(
            self._entries(feed['guid']), feed_id,
            strip_or_none(feed.get('name')),
            feed.get('briefdescription'))


class MindsChannelIE(MindsFeedBaseIE):
    _FEED_TYPE = 'channel'
    IE_NAME = 'minds:' + _FEED_TYPE
    _VALID_URL = MindsBaseIE._VALID_URL_BASE + r'(?!(?:newsfeed|media|api|archive|groups)/)(?P<id>[^/?&#]+)'
    _FEED_PATH = 'channel'
    _TEST = {
        'url': 'https://www.minds.com/ottman',
        'info_dict': {
            'id': 'ottman',
            'title': 'Bill Ottman',
            'description': 'Co-creator & CEO @minds',
        },
        'playlist_mincount': 54,
    }


class MindsGroupIE(MindsFeedBaseIE):
    _FEED_TYPE = 'group'
    IE_NAME = 'minds:' + _FEED_TYPE
    _VALID_URL = MindsBaseIE._VALID_URL_BASE + r'groups/profile/(?P<id>[0-9]+)'
    _FEED_PATH = 'groups/group'
    _TEST = {
        'url': 'https://www.minds.com/groups/profile/785582576369672204/feed/videos',
        'info_dict': {
            'id': '785582576369672204',
            'title': 'Cooking Videos',
        },
        'playlist_mincount': 1,
    }

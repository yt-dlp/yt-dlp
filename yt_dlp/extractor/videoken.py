import base64
import functools
import math
import re
import time
import urllib.parse

from .common import InfoExtractor
from .slideslive import SlidesLiveIE
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    int_or_none,
    traverse_obj,
    update_url_query,
    url_or_none,
)


class VideoKenBaseIE(InfoExtractor):
    _ORGANIZATIONS = {
        'videos.icts.res.in': 'icts',
        'videos.cncf.io': 'cncf',
        'videos.neurips.cc': 'neurips',
    }
    _BASE_URL_RE = rf'https?://(?P<host>{"|".join(map(re.escape, _ORGANIZATIONS))})/'

    _PAGE_SIZE = 12

    def _get_org_id_and_api_key(self, org, video_id):
        details = self._download_json(
            f'https://analytics.videoken.com/api/videolake/{org}/details', video_id,
            note='Downloading organization ID and API key', headers={
                'Accept': 'application/json',
            })
        return details['id'], details['apikey']

    def _create_slideslive_url(self, video_url, video_id, referer):
        if not video_url and not video_id:
            return
        elif not video_url or 'embed/sign-in' in video_url:
            video_url = f'https://slideslive.com/embed/{video_id.lstrip("slideslive-")}'
        if url_or_none(referer):
            return update_url_query(video_url, {
                'embed_parent_url': referer,
                'embed_container_origin': f'https://{urllib.parse.urlparse(referer).netloc}',
            })
        return video_url

    def _extract_videos(self, videos, url):
        for video in traverse_obj(videos, (('videos', 'results'), ...)):
            video_id = traverse_obj(video, 'youtube_id', 'videoid')
            if not video_id:
                continue
            ie_key = None
            if traverse_obj(video, 'type', 'source') == 'youtube':
                video_url = video_id
                ie_key = 'Youtube'
            else:
                video_url = traverse_obj(video, 'embed_url', 'embeddableurl')
                if urllib.parse.urlparse(video_url).netloc == 'slideslive.com':
                    ie_key = SlidesLiveIE
                    video_url = self._create_slideslive_url(video_url, video_id, url)
            if not video_url:
                continue
            yield self.url_result(video_url, ie_key, video_id)


class VideoKenIE(VideoKenBaseIE):
    _VALID_URL = VideoKenBaseIE._BASE_URL_RE + r'(?:(?:topic|category)/[^/#?]+/)?video/(?P<id>[\w-]+)'
    _TESTS = [{
        # neurips -> videoken -> slideslive
        'url': 'https://videos.neurips.cc/video/slideslive-38922815',
        'info_dict': {
            'id': '38922815',
            'ext': 'mp4',
            'title': 'Efficient Processing of Deep Neural Network: from Algorithms to Hardware Architectures',
            'timestamp': 1630939331,
            'upload_date': '20210906',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:330',
            'chapters': 'count:329',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': ['Failed to download VideoKen API JSON'],
    }, {
        # neurips -> videoken -> slideslive -> youtube
        'url': 'https://videos.neurips.cc/topic/machine%20learning/video/slideslive-38923348',
        'info_dict': {
            'id': '2Xa_dt78rJE',
            'ext': 'mp4',
            'display_id': '38923348',
            'title': 'Machine Education',
            'description': 'Watch full version of this video at https://slideslive.com/38923348.',
            'channel': 'SlidesLive Videos - G2',
            'channel_id': 'UCOExahQQ588Da8Nft_Ltb9w',
            'channel_url': 'https://www.youtube.com/channel/UCOExahQQ588Da8Nft_Ltb9w',
            'uploader': 'SlidesLive Videos - G2',
            'uploader_id': 'UCOExahQQ588Da8Nft_Ltb9w',
            'uploader_url': 'http://www.youtube.com/channel/UCOExahQQ588Da8Nft_Ltb9w',
            'duration': 2504,
            'timestamp': 1618922125,
            'upload_date': '20200131',
            'age_limit': 0,
            'channel_follower_count': int,
            'view_count': int,
            'availability': 'unlisted',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'categories': ['People & Blogs'],
            'tags': [],
            'thumbnail': r're:^https?://.*\.(?:jpg|webp)',
            'thumbnails': 'count:78',
            'chapters': 'count:77',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': ['Failed to download VideoKen API JSON'],
    }, {
        # icts -> videoken -> youtube
        'url': 'https://videos.icts.res.in/topic/random%20variable/video/zysIsojYdvc',
        'info_dict': {
            'id': 'zysIsojYdvc',
            'ext': 'mp4',
            'title': 'Small-worlds, complex networks and random graphs (Lecture 3)  by Remco van der Hofstad',
            'description': 'md5:87433069d79719eeadc1962cc2ace00b',
            'channel': 'International Centre for Theoretical Sciences',
            'channel_id': 'UCO3xnVTHzB7l-nc8mABUJIQ',
            'channel_url': 'https://www.youtube.com/channel/UCO3xnVTHzB7l-nc8mABUJIQ',
            'uploader': 'International Centre for Theoretical Sciences',
            'uploader_id': 'ICTStalks',
            'uploader_url': 'http://www.youtube.com/user/ICTStalks',
            'duration': 3372,
            'upload_date': '20191004',
            'age_limit': 0,
            'live_status': 'not_live',
            'availability': 'public',
            'playable_in_embed': True,
            'channel_follower_count': int,
            'like_count': int,
            'view_count': int,
            'categories': ['Science & Technology'],
            'tags': [],
            'thumbnail': r're:^https?://.*\.(?:jpg|webp)',
            'thumbnails': 'count:42',
            'chapters': 'count:20',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://videos.cncf.io/category/478/video/IL4nxbmUIX8',
        'only_matching': True,
    }, {
        'url': 'https://videos.cncf.io/topic/kubernetes/video/YAM2d7yTrrI',
        'only_matching': True,
    }, {
        'url': 'https://videos.icts.res.in/video/d7HuP_abpKU',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        hostname, video_id = self._match_valid_url(url).group('host', 'id')
        org_id, _ = self._get_org_id_and_api_key(self._ORGANIZATIONS[hostname], video_id)
        details = self._download_json(
            'https://analytics.videoken.com/api/videoinfo_private', video_id, query={
                'videoid': video_id,
                'org_id': org_id,
            }, headers={'Accept': 'application/json'}, note='Downloading VideoKen API JSON',
            errnote='Failed to download VideoKen API JSON', fatal=False)
        if details:
            return next(self._extract_videos({'videos': [details]}, url))
        # fallback for API error 400 response
        elif video_id.startswith('slideslive-'):
            return self.url_result(
                self._create_slideslive_url(None, video_id, url), SlidesLiveIE, video_id)
        elif re.match(r'^[\w-]{11}$', video_id):
            self.url_result(video_id, 'Youtube', video_id)
        else:
            raise ExtractorError('Unable to extract without VideoKen API response')


class VideoKenPlayerIE(VideoKenBaseIE):
    _VALID_URL = r'https?://player\.videoken\.com/embed/slideslive-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://player.videoken.com/embed/slideslive-38968434',
        'info_dict': {
            'id': '38968434',
            'ext': 'mp4',
            'title': 'Deep Learning with Label Differential Privacy',
            'timestamp': 1643377020,
            'upload_date': '20220128',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:30',
            'chapters': 'count:29',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            self._create_slideslive_url(None, video_id, url), SlidesLiveIE, video_id)


class VideoKenPlaylistIE(VideoKenBaseIE):
    _VALID_URL = VideoKenBaseIE._BASE_URL_RE + r'(?:category/\d+/)?playlist/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://videos.icts.res.in/category/1822/playlist/381',
        'playlist_mincount': 117,
        'info_dict': {
            'id': '381',
            'title': 'Cosmology - The Next Decade',
        },
    }]

    def _real_extract(self, url):
        hostname, playlist_id = self._match_valid_url(url).group('host', 'id')
        org_id, _ = self._get_org_id_and_api_key(self._ORGANIZATIONS[hostname], playlist_id)
        videos = self._download_json(
            f'https://analytics.videoken.com/api/{org_id}/playlistitems/{playlist_id}/',
            playlist_id, headers={'Accept': 'application/json'}, note='Downloading API JSON')
        return self.playlist_result(self._extract_videos(videos, url), playlist_id, videos.get('title'))


class VideoKenCategoryIE(VideoKenBaseIE):
    _VALID_URL = VideoKenBaseIE._BASE_URL_RE + r'category/(?P<id>\d+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://videos.icts.res.in/category/1822/',
        'playlist_mincount': 500,
        'info_dict': {
            'id': '1822',
            'title': 'Programs',
        },
    }, {
        'url': 'https://videos.neurips.cc/category/350/',
        'playlist_mincount': 34,
        'info_dict': {
            'id': '350',
            'title': 'NeurIPS 2018',
        },
    }, {
        'url': 'https://videos.cncf.io/category/479/',
        'playlist_mincount': 328,
        'info_dict': {
            'id': '479',
            'title': 'KubeCon + CloudNativeCon Europe\'19',
        },
    }]

    def _get_category_page(self, category_id, org_id, page=1, note=None):
        return self._download_json(
            f'https://analytics.videoken.com/api/videolake/{org_id}/category_videos', category_id,
            fatal=False, note=note if note else f'Downloading category page {page}',
            query={
                'category_id': category_id,
                'page_number': page,
                'length': self._PAGE_SIZE,
            }, headers={'Accept': 'application/json'}) or {}

    def _entries(self, category_id, org_id, url, page):
        videos = self._get_category_page(category_id, org_id, page + 1)
        yield from self._extract_videos(videos, url)

    def _real_extract(self, url):
        hostname, category_id = self._match_valid_url(url).group('host', 'id')
        org_id, _ = self._get_org_id_and_api_key(self._ORGANIZATIONS[hostname], category_id)
        category_info = self._get_category_page(category_id, org_id, note='Downloading category info')
        category = category_info['category_name']
        total_pages = math.ceil(int(category_info['recordsTotal']) / self._PAGE_SIZE)
        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, category_id, org_id, url),
            total_pages, self._PAGE_SIZE), category_id, category)


class VideoKenTopicIE(VideoKenBaseIE):
    _VALID_URL = VideoKenBaseIE._BASE_URL_RE + r'topic/(?P<id>[^/#?]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://videos.neurips.cc/topic/machine%20learning/',
        'playlist_mincount': 500,
        'info_dict': {
            'id': 'machine_learning',
            'title': 'machine learning',
        },
    }, {
        'url': 'https://videos.icts.res.in/topic/gravitational%20waves/',
        'playlist_mincount': 77,
        'info_dict': {
            'id': 'gravitational_waves',
            'title': 'gravitational waves'
        },
    }, {
        'url': 'https://videos.cncf.io/topic/prometheus/',
        'playlist_mincount': 134,
        'info_dict': {
            'id': 'prometheus',
            'title': 'prometheus',
        },
    }]

    def _get_topic_page(self, topic, org_id, search_id, api_key, page=1, note=None):
        return self._download_json(
            'https://es.videoken.com/api/v1.0/get_results', topic, fatal=False, query={
                'orgid': org_id,
                'size': self._PAGE_SIZE,
                'query': topic,
                'page': page,
                'sort': 'upload_desc',
                'filter': 'all',
                'token': api_key,
                'is_topic': 'true',
                'category': '',
                'searchid': search_id,
            }, headers={'Accept': 'application/json'},
            note=note if note else f'Downloading topic page {page}') or {}

    def _entries(self, topic, org_id, search_id, api_key, url, page):
        videos = self._get_topic_page(topic, org_id, search_id, api_key, page + 1)
        yield from self._extract_videos(videos, url)

    def _real_extract(self, url):
        hostname, topic_id = self._match_valid_url(url).group('host', 'id')
        topic = urllib.parse.unquote(topic_id)
        topic_id = topic.replace(' ', '_')
        org_id, api_key = self._get_org_id_and_api_key(self._ORGANIZATIONS[hostname], topic)
        search_id = base64.b64encode(f':{topic}:{int(time.time())}:transient'.encode()).decode()
        total_pages = int_or_none(self._get_topic_page(
            topic, org_id, search_id, api_key, note='Downloading topic info')['total_no_of_pages'])
        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, topic, org_id, search_id, api_key, url),
            total_pages, self._PAGE_SIZE), topic_id, topic)

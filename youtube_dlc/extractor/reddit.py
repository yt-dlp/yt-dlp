from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    try_get,
    unescapeHTML,
    url_or_none,
)


class RedditIE(InfoExtractor):
    _VALID_URL = r'https?://v\.redd\.it/(?P<id>[^/?#&]+)'
    _TEST = {
        # from https://www.reddit.com/r/videos/comments/6rrwyj/that_small_heart_attack/
        'url': 'https://v.redd.it/zv89llsvexdz',
        'md5': '0a070c53eba7ec4534d95a5a1259e253',
        'info_dict': {
            'id': 'zv89llsvexdz',
            'ext': 'mp4',
            'title': 'zv89llsvexdz',
        },
        'params': {
            'format': 'bestvideo',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats = self._extract_m3u8_formats(
            'https://v.redd.it/%s/HLSPlaylist.m3u8' % video_id, video_id,
            'mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)

        formats.extend(self._extract_mpd_formats(
            'https://v.redd.it/%s/DASHPlaylist.mpd' % video_id, video_id,
            mpd_id='dash', fatal=False))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }


class RedditRIE(InfoExtractor):
    _VALID_URL = r'(?P<url>https?://(?:[^/]+\.)?reddit\.com/r/[^/]+/comments/(?P<id>[^/?#&]+))'
    _TESTS = [{
        'url': 'https://www.reddit.com/r/videos/comments/6rrwyj/that_small_heart_attack/',
        'info_dict': {
            'id': 'zv89llsvexdz',
            'ext': 'mp4',
            'title': 'That small heart attack.',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:4',
            'timestamp': 1501941939,
            'upload_date': '20170805',
            'uploader': 'Antw87',
            'duration': 12,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'age_limit': 0,
        },
        'params': {
            'format': 'bestvideo',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.reddit.com/r/videos/comments/6rrwyj',
        'only_matching': True,
    }, {
        # imgur
        'url': 'https://www.reddit.com/r/MadeMeSmile/comments/6t7wi5/wait_for_it/',
        'only_matching': True,
    }, {
        # imgur @ old reddit
        'url': 'https://old.reddit.com/r/MadeMeSmile/comments/6t7wi5/wait_for_it/',
        'only_matching': True,
    }, {
        # streamable
        'url': 'https://www.reddit.com/r/videos/comments/6t7sg9/comedians_hilarious_joke_about_the_guam_flag/',
        'only_matching': True,
    }, {
        # youtube
        'url': 'https://www.reddit.com/r/videos/comments/6t75wq/southern_man_tries_to_speak_without_an_accent/',
        'only_matching': True,
    }, {
        # reddit video @ nm reddit
        'url': 'https://nm.reddit.com/r/Cricket/comments/8idvby/lousy_cameraman_finds_himself_in_cairns_line_of/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        url, video_id = mobj.group('url', 'id')

        video_id = self._match_id(url)

        data = self._download_json(
            url + '/.json', video_id)[0]['data']['children'][0]['data']

        video_url = data['url']

        # Avoid recursing into the same reddit URL
        if 'reddit.com/' in video_url and '/%s/' % video_id in video_url:
            raise ExtractorError('No media found', expected=True)

        over_18 = data.get('over_18')
        if over_18 is True:
            age_limit = 18
        elif over_18 is False:
            age_limit = 0
        else:
            age_limit = None

        thumbnails = []

        def add_thumbnail(src):
            if not isinstance(src, dict):
                return
            thumbnail_url = url_or_none(src.get('url'))
            if not thumbnail_url:
                return
            thumbnails.append({
                'url': unescapeHTML(thumbnail_url),
                'width': int_or_none(src.get('width')),
                'height': int_or_none(src.get('height')),
            })

        for image in try_get(data, lambda x: x['preview']['images']) or []:
            if not isinstance(image, dict):
                continue
            add_thumbnail(image.get('source'))
            resolutions = image.get('resolutions')
            if isinstance(resolutions, list):
                for resolution in resolutions:
                    add_thumbnail(resolution)

        return {
            '_type': 'url_transparent',
            'url': video_url,
            'title': data.get('title'),
            'thumbnails': thumbnails,
            'timestamp': float_or_none(data.get('created_utc')),
            'uploader': data.get('author'),
            'duration': int_or_none(try_get(
                data,
                (lambda x: x['media']['reddit_video']['duration'],
                 lambda x: x['secure_media']['reddit_video']['duration']))),
            'like_count': int_or_none(data.get('ups')),
            'dislike_count': int_or_none(data.get('downs')),
            'comment_count': int_or_none(data.get('num_comments')),
            'age_limit': age_limit,
        }

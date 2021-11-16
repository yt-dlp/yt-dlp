import random

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    try_get,
    unescapeHTML,
    url_or_none,
    traverse_obj
)


class RedditIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<subdomain>[^/]+\.)?reddit(?:media)?\.com/r/(?P<slug>[^/]+/comments/(?P<id>[^/?#&]+))'
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
    }, {
        'url': 'https://www.redditmedia.com/r/serbia/comments/pu9wbx/ako_vu%C4%8Di%C4%87_izgubi_izbore_ja_%C4%87u_da_crknem/',
        'only_matching': True,
    }]

    @staticmethod
    def _gen_session_id():
        id_length = 16
        rand_max = 1 << (id_length * 4)
        return '%0.*x' % (id_length, random.randrange(rand_max))

    def _real_extract(self, url):
        subdomain, slug, video_id = self._match_valid_url(url).group('subdomain', 'slug', 'id')

        self._set_cookie('.reddit.com', 'reddit_session', self._gen_session_id())
        self._set_cookie('.reddit.com', '_options', '%7B%22pref_quarantine_optin%22%3A%20true%7D')
        data = self._download_json(f'https://{subdomain}reddit.com/r/{slug}/.json', video_id, fatal=False)
        if not data:
            # Fall back to old.reddit.com in case the requested subdomain fails
            data = self._download_json(f'https://old.reddit.com/r/{slug}/.json', video_id)
        data = data[0]['data']['children'][0]['data']
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

        info = {
            'title': data.get('title'),
            'thumbnails': thumbnails,
            'timestamp': float_or_none(data.get('created_utc')),
            'uploader': data.get('author'),
            'like_count': int_or_none(data.get('ups')),
            'dislike_count': int_or_none(data.get('downs')),
            'comment_count': int_or_none(data.get('num_comments')),
            'age_limit': age_limit,
        }

        # Check if media is hosted on reddit:
        reddit_video = traverse_obj(data, (('media', 'secure_media'), 'reddit_video'), get_all=False)
        if reddit_video:
            playlist_urls = [
                try_get(reddit_video, lambda x: unescapeHTML(x[y]))
                for y in ('dash_url', 'hls_url')
            ]

            # Update video_id
            display_id = video_id
            video_id = self._search_regex(
                r'https?://v\.redd\.it/(?P<id>[^/?#&]+)', reddit_video['fallback_url'],
                'video_id', default=display_id)

            dash_playlist_url = playlist_urls[0] or f'https://v.redd.it/{video_id}/DASHPlaylist.mpd'
            hls_playlist_url = playlist_urls[1] or f'https://v.redd.it/{video_id}/HLSPlaylist.m3u8'

            formats = self._extract_m3u8_formats(
                hls_playlist_url, display_id, 'mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
            formats.extend(self._extract_mpd_formats(
                dash_playlist_url, display_id, mpd_id='dash', fatal=False))
            self._sort_formats(formats)

            return {
                **info,
                'id': video_id,
                'display_id': display_id,
                'formats': formats,
                'duration': int_or_none(reddit_video.get('duration')),
            }

        # Not hosted on reddit, must continue extraction
        return {
            **info,
            'display_id': video_id,
            '_type': 'url_transparent',
            'url': video_url,
        }

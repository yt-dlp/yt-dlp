# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
    urlencode_postdata
)


class TumblrIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<blog_name>[^/?#&]+)\.tumblr\.com/(?:post|video)/(?P<id>[0-9]+)(?:$|[/?#])'
    _NETRC_MACHINE = 'tumblr'
    _LOGIN_URL = 'https://www.tumblr.com/login'
    _OAUTH_URL = 'https://www.tumblr.com/api/v2/oauth2/token'
    _TESTS = [{
        'url': 'http://tatianamaslanydaily.tumblr.com/post/54196191430/orphan-black-dvd-extra-behind-the-scenes',
        'md5': '479bb068e5b16462f5176a6828829767',
        'info_dict': {
            'id': '54196191430',
            'ext': 'mp4',
            'title': 'md5:dfac39636969fe6bf1caa2d50405f069',
            'description': 'md5:390ab77358960235b6937ab3b8528956',
            'uploader_id': 'tatianamaslanydaily',
            'uploader_url': 'https://tatianamaslanydaily.tumblr.com/',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 127,
            'like_count': int,
            'repost_count': int,
            'age_limit': 0,
            'tags': ['Orphan Black', 'Tatiana Maslany', 'Interview', 'Video', 'OB S1 DVD Extras'],
        }
    }, {
        'note': 'multiple formats',
        'url': 'https://maskofthedragon.tumblr.com/post/626907179849564160/mona-talking-in-english',
        'md5': 'f43ff8a8861712b6cf0e0c2bd84cfc68',
        'info_dict': {
            'id': '626907179849564160',
            'ext': 'mp4',
            'title': 'Mona\xa0“talking” in\xa0“english”',
            'description': 'md5:082a3a621530cb786ad2b7592a6d9e2c',
            'uploader_id': 'maskofthedragon',
            'uploader_url': 'https://maskofthedragon.tumblr.com/',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 7,
            'like_count': int,
            'repost_count': int,
            'age_limit': 0,
            'tags': 'count:19',
        },
        'params': {
            'format': 'hd',
        },
    }, {
        'note': 'non-iframe video (with related posts)',
        'url': 'https://shieldfoss.tumblr.com/post/675519763813908480',
        'md5': '12bdb75661ef443bffe5a4dac1dbf118',
        'info_dict': {
            'id': '675519763813908480',
            'ext': 'mp4',
            'title': 'Shieldfoss',
            'uploader_id': 'nerviovago',
            'uploader_url': 'https://nerviovago.tumblr.com/',
            'thumbnail': r're:^https?://.*\.jpg',
            'like_count': int,
            'repost_count': int,
            'age_limit': 0,
            'tags': [],
        }
    }, {
        'note': 'dashboard only (original post)',
        'url': 'https://nerviovago.tumblr.com/post/674979046803800064',
        'md5': '12bdb75661ef443bffe5a4dac1dbf118',
        'info_dict': {
            'id': '674979046803800064',
            'ext': 'mp4',
            'title': 'nerviovago',
            'uploader_id': 'nerviovago',
            'uploader_url': 'https://nerviovago.tumblr.com/',
            'thumbnail': r're:^https?://.*\.jpg',
            'like_count': int,
            'repost_count': int,
            'age_limit': 0,
            'tags': ['pig', 'cuddly', 'cute animals', 'animals', 'sound', 'pigs'],
        }
    }, {
        'note': 'dashboard only (reblog)',
        'url': 'https://bartlebyshop.tumblr.com/post/180294460076/duality-of-bird',
        'md5': '04334e7cadb1af680d162912559f51a5',
        'info_dict': {
            'id': '180294460076',
            'ext': 'mp4',
            'title': 'duality of bird',
            'description': 'duality of bird',
            'uploader_id': 'todaysbird',
            'uploader_url': 'https://todaysbird.tumblr.com/',
            'thumbnail': r're:^https?://.*\.jpg',
            'like_count': int,
            'repost_count': int,
            'age_limit': 0,
            'tags': [],
        }
    }, {
        'note': 'dashboard only (external)',
        'url': 'https://afloweroutofstone.tumblr.com/post/675661759168823296/the-blues-remembers-everything-the-country-forgot',
        'info_dict': {
            'id': 'q67_fd7b8SU',
            'ext': 'mp4',
            'title': 'The Blues Remembers Everything the Country Forgot',
            'alt_title': 'The Blues Remembers Everything the Country Forgot',
            'description': 'md5:1a6b4097e451216835a24c1023707c79',
            'release_date': '20201224',
            'creator': 'md5:c2239ba15430e87c3b971ba450773272',
            'uploader': 'Moor Mother - Topic',
            'upload_date': '20201223',
            'uploader_id': 'UCxrMtFBRkFvQJ_vVM4il08w',
            'uploader_url': 'http://www.youtube.com/channel/UCxrMtFBRkFvQJ_vVM4il08w',
            'thumbnail': r're:^https?://i.ytimg.com/.*',
            'channel': 'Moor Mother - Topic',
            'channel_id': 'UCxrMtFBRkFvQJ_vVM4il08w',
            'channel_url': 'https://www.youtube.com/channel/UCxrMtFBRkFvQJ_vVM4il08w',
            'channel_follower_count': int,
            'duration': 181,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'categories': ['Music'],
            'tags': 'count:7',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'availability': 'public',
            'track': 'The Blues Remembers Everything the Country Forgot',
            'artist': 'md5:c2239ba15430e87c3b971ba450773272',
            'album': 'Brass',
            'release_year': 2020,
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'http://naked-yogi.tumblr.com/post/118312946248/naked-smoking-stretching',
        'md5': 'de07e5211d60d4f3a2c3df757ea9f6ab',
        'info_dict': {
            'id': 'Wmur',
            'ext': 'mp4',
            'title': 'naked smoking & stretching',
            'upload_date': '20150506',
            'timestamp': 1430931613,
            'age_limit': 18,
            'uploader_id': '1638622',
            'uploader': 'naked-yogi',
        },
        # 'add_ie': ['Vidme'],
        'skip': 'dead embedded video host'
    }, {
        'url': 'https://prozdvoices.tumblr.com/post/673201091169681408/what-recording-voice-acting-sounds-like',
        'md5': 'a0063fc8110e6c9afe44065b4ea68177',
        'info_dict': {
            'id': 'eomhW5MLGWA',
            'ext': 'mp4',
            'title': 'what recording voice acting sounds like',
            'description': 'md5:1da3faa22d0e0b1d8b50216c284ee798',
            'uploader': 'ProZD',
            'upload_date': '20220112',
            'uploader_id': 'ProZD',
            'uploader_url': 'http://www.youtube.com/user/ProZD',
            'thumbnail': r're:^https?://i.ytimg.com/.*',
            'channel': 'ProZD',
            'channel_id': 'UC6MFZAOHXlKK1FI7V0XQVeA',
            'channel_url': 'https://www.youtube.com/channel/UC6MFZAOHXlKK1FI7V0XQVeA',
            'channel_follower_count': int,
            'duration': 20,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'categories': ['Film & Animation'],
            'tags': [],
            'live_status': 'not_live',
            'playable_in_embed': True,
            'availability': 'public',
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'https://dominustempori.tumblr.com/post/673572712813297664/youtubes-all-right-for-some-pretty-cool',
        'md5': '203e9eb8077e3f45bfaeb4c86c1467b8',
        'info_dict': {
            'id': '87816359',
            'ext': 'mov',
            'title': 'Harold Ramis',
            'description': 'md5:be8e68cbf56ce0785c77f0c6c6dfaf2c',
            'uploader': 'Resolution Productions Group',
            'uploader_id': 'resolutionproductions',
            'uploader_url': 'https://vimeo.com/resolutionproductions',
            'upload_date': '20140227',
            'thumbnail': r're:^https?://i.vimeocdn.com/video/.*',
            'timestamp': 1393523719,
            'duration': 291,
        },
        'add_ie': ['Vimeo'],
    }, {
        'url': 'http://sutiblr.tumblr.com/post/139638707273',
        'md5': '2dd184b3669e049ba40563a7d423f95c',
        'info_dict': {
            'id': 'ir7qBEIKqvq',
            'ext': 'mp4',
            'title': 'Vine by sutiblr',
            'alt_title': 'Vine by sutiblr',
            'uploader': 'sutiblr',
            'uploader_id': '1198993975374495744',
            'upload_date': '20160220',
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1455940159,
            'view_count': int,
        },
        'add_ie': ['Vine'],
    }, {
        'url': 'https://silami.tumblr.com/post/84250043974/my-bad-river-flows-in-you-impression-on-maschine',
        'md5': '3c92d7c3d867f14ccbeefa2119022277',
        'info_dict': {
            'id': 'nYtvtTPuTl',
            'ext': 'mp4',
            'title': 'Video by silbulterman',
            'description': '#maschine',
            'uploader_id': '242859024',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1398801174,
            'like_count': int,
            'uploader': 'Sil',
            'channel': 'silbulterman',
            'comment_count': int,
            'upload_date': '20140429',
        },
        'add_ie': ['Instagram'],
    }]

    _providers = {
        'instagram': 'Instagram',
        'vimeo': 'Vimeo',
        'vine': 'Vine',
        'youtube': 'Youtube',
    }

    def _real_initialize(self):
        self._ACCESS_TOKEN = None
        self.get_access_token()
        self._login()

    def get_access_token(self):
        try:
            login_page = self._download_webpage(
                self._LOGIN_URL, None, 'Downloading login page')
            self._ACCESS_TOKEN = self._search_regex(
                r'"API_TOKEN":\s*"(\w+)"', login_page, 'API access token')
        except ExtractorError:
            self.report_warning('Failed to get access token; metadata will be missing and some videos may not work')

    def _login(self):
        username, password = self._get_login_info()
        if not username:
            return

        if not self._ACCESS_TOKEN:
            self.report_warning('Cannot log in without access token')
            return

        try:
            self._download_json(
                self._OAUTH_URL, None, 'Logging in',
                data=urlencode_postdata({
                    'password': password,
                    'grant_type': 'password',
                    'username': username,
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'Bearer {self._ACCESS_TOKEN}',
                })
        except ExtractorError:
            self.report_warning('Login failed')

    def _real_extract(self, url):
        m_url = self._match_valid_url(url)
        video_id = m_url.group('id')
        blog = m_url.group('blog_name')

        url = f'http://{blog}.tumblr.com/post/{video_id}/'
        webpage, urlh = self._download_webpage_handle(url, video_id)

        redirect_url = urlh.geturl()

        api_only = bool(self._search_regex(
            r'(tumblr.com|^)/(safe-mode|login_required|blog/view)',
            redirect_url, 'redirect', default=None))

        if api_only and not self._ACCESS_TOKEN:
            raise ExtractorError('Cannot get data for dashboard-only post without access token')

        post_json = traverse_obj(
            self._download_json(
                f'https://www.tumblr.com/api/v2/blog/{blog}/posts/{video_id}/permalink',
                video_id,
                headers={
                    'Authorization': f'Bearer {self._ACCESS_TOKEN}',
                },
                fatal=False) if self._ACCESS_TOKEN else None,
            ('response', 'timeline', 'elements', 0), default={})
        content_json = traverse_obj(
            post_json, ('trail', 0, 'content'), ('content'), default=[])
        video_json = next(
            (item for item in content_json if item.get('type') == 'video'),
            {})
        media_json = video_json.get('media', {})
        if api_only and 'url' not in media_json and 'url' not in video_json:
            raise ExtractorError('Failed to find video data for dashboard-only post')

        if 'url' not in media_json and 'url' in video_json:
            # external video host
            return self.url_result(
                video_json['url'],
                self._providers.get(video_json.get('provider'), 'Generic'))

        video_url = self._og_search_video_url(webpage, default=None)
        duration = None
        formats = None

        # iframes can supply duration and sometimes additional formats, so check for one
        iframe_url = self._search_regex(
            fr'src=\'(https?://www\.tumblr\.com/video/{blog}/{video_id}/[^\']+)\'',
            webpage, 'iframe url', default=None)
        if iframe_url:
            iframe = self._download_webpage(
                iframe_url, video_id, 'Downloading iframe page',
                headers={'Referer': redirect_url})

            options = self._parse_json(
                self._search_regex(
                    r'data-crt-options=(["\'])(?P<options>.+?)\1', iframe,
                    'hd video url', default='', group='options'),
                video_id, fatal=False)
            if options:
                duration = int_or_none(options.get('duration'))

                hd_url = options.get('hdUrl')
                if hd_url:
                    # there are multiple formats; extract them
                    # (and ignore other sources of width/height data as they may be wrong)
                    sources = []
                    sd_url = self._search_regex(
                        r'<source[^>]+src=(["\'])(?P<url>.+?)\1', iframe,
                        'sd video url', default=None, group='url')
                    if sd_url:
                        sources.append((sd_url, 'sd'))
                    sources.append((hd_url, 'hd'))

                    formats = [{
                        'url': video_url,
                        'format_id': format_id,
                        'height': int_or_none(self._search_regex(
                            r'_(\d+)\.\w+$', video_url, 'height', default=None)),
                        'quality': quality,
                    } for quality, (video_url, format_id) in enumerate(sources)]
                    self._sort_formats(formats)

        if 'url' not in media_json and not video_url and not iframe_url:
            # external video host (but we weren't able to figure it out from the api)
            iframe_url = self._search_regex(
                r'src=["\'](https?://safe\.txmblr\.com/svc/embed/inline/[^"\']+)["\']',
                webpage, 'embed iframe url', default=None)
            return self.url_result(iframe_url or redirect_url, 'Generic')

        formats = formats or [{
            'url': media_json.get('url') or video_url,
            'format_id': '0',
            'width': media_json.get('width') or int_or_none(
                self._og_search_property('video:width', webpage, default=None)),
            'height': media_json.get('height') or int_or_none(
                self._og_search_property('video:height', webpage, default=None)),
        }]

        uploader_id = traverse_obj(post_json, ('reblogged_root_name'), ('blog_name'))

        return {
            'id': video_id,
            'title': (post_json.get('summary')
                      or (blog if api_only else self._html_search_regex(
                          r'(?s)<title>(?P<title>.*?)(?: \| Tumblr)?</title>',
                          webpage, 'title'))),
            # the url we're extracting from might be an original post or it might be a reblog.
            # if it's a reblog, og:description will be the reblogger's comment, not the uploader's.
            # content_json is the op's post, so if it exists but has no text, there's no description
            'description': ('\n\n'.join(
                            (
                                item.get('text') for item in content_json
                                if item.get('type') == 'text'
                            ))
                            or (None if content_json
                                else self._og_search_description(webpage, default=None))),
            'thumbnail': (traverse_obj(video_json, ('poster', 0, 'url'))
                          or self._og_search_thumbnail(webpage, default=None)),
            'uploader_id': uploader_id,
            'uploader_url': f'https://{uploader_id}.tumblr.com/' if uploader_id else None,
            'duration': duration,
            'like_count': post_json.get('like_count'),
            'repost_count': post_json.get('reblog_count'),
            'age_limit': ((18 if post_json.get('is_nsfw') else 0)
                          if 'is_nsfw' in post_json else None),
            'tags': post_json.get('tags'),
            'formats': formats,
        }

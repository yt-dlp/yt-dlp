import functools
import hashlib
import itertools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..networking.impersonate import ImpersonateTarget
from ..utils import (
    ExtractorError,
    bug_reports_message,
    decode_base_n,
    encode_base_n,
    filter_dict,
    float_or_none,
    format_field,
    get_element_by_attribute,
    int_or_none,
    join_nonempty,
    str_or_none,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)

_ENCODING_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'


def _pk_to_id(media_id):
    """Source: https://stackoverflow.com/questions/24437823/getting-instagram-post-url-from-media-id"""
    pk = int(str(media_id).split('_')[0])
    return encode_base_n(pk, table=_ENCODING_CHARS)


def _id_to_pk(shortcode):
    """Convert a shortcode to a numeric value"""
    if len(shortcode) > 28:
        shortcode = shortcode[:-28]
    return decode_base_n(shortcode, table=_ENCODING_CHARS)


class InstagramBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://i.instagram.com/api/v1'
    _BASE_URL = 'https://www.instagram.com/'
    _APP_IDS = {
        'ios': '124024574287414',
        'web': '936619743392459',  # default
    }
    _AUTH_COOKIE_NAME = 'sessionid'
    _COOKIE_DOMAINS = (
        'i.instagram.com',
        '.i.instagram.com',
        'www.instagram.com',
        '.www.instagram.com',
        'instagram.com',
        '.instagram.com',
    )

    @functools.cached_property
    def _can_impersonate(self):
        return self._downloader._impersonate_target_available(ImpersonateTarget())

    @property
    def _is_logged_in(self):
        return bool(self._get_cookies(self._BASE_URL).get(self._AUTH_COOKIE_NAME))

    @functools.cached_property
    def _app_id(self):
        user_input = self._configuration_arg('app_id', [None], ie_key=InstagramIE)[0]
        return self._APP_IDS.get(user_input, user_input or self._APP_IDS['web'])

    @property
    def _is_web_app(self):
        return self._app_id == self._APP_IDS['web']

    @property
    def _api_headers(self):
        return {
            'X-IG-App-ID': self._app_id,
            'X-ASBD-ID': '359341',
            'X-IG-WWW-Claim': '0',
            'Origin': 'https://www.instagram.com',
            'Accept': '*/*',
        }

    @staticmethod
    def _is_login_redirect(url):
        return urllib.parse.urlparse(url).path.startswith('/accounts/login')

    def _get_count(self, media, kind, *keys):
        return traverse_obj(
            media, (kind, 'count'), *((f'edge_media_{key}', 'count') for key in keys),
            expected_type=int_or_none)

    def _get_dimension(self, name, media, webpage=None):
        return (
            traverse_obj(media, ('dimensions', name), expected_type=int_or_none)
            or int_or_none(self._html_search_meta(
                (f'og:video:{name}', f'video:{name}'), webpage or '', default=None)))

    def _extract_nodes(self, nodes, is_direct=False):
        for idx, node in enumerate(nodes, start=1):
            if node.get('__typename') != 'GraphVideo' and node.get('is_video') is not True:
                continue

            video_id = node.get('shortcode')

            if is_direct:
                info = {
                    'id': video_id or node['id'],
                    'url': node.get('video_url'),
                    'width': self._get_dimension('width', node),
                    'height': self._get_dimension('height', node),
                    'http_headers': {
                        'Referer': 'https://www.instagram.com/',
                    },
                }
            elif not video_id:
                continue
            else:
                info = {
                    '_type': 'url',
                    'ie_key': 'Instagram',
                    'id': video_id,
                    'url': f'https://instagram.com/p/{video_id}',
                }

            yield {
                **info,
                'title': node.get('title') or (f'Video {idx}' if is_direct else None),
                'description': traverse_obj(
                    node, ('edge_media_to_caption', 'edges', 0, 'node', 'text'), expected_type=str),
                'thumbnail': traverse_obj(
                    node, 'display_url', 'thumbnail_src', 'display_src', expected_type=url_or_none),
                'duration': float_or_none(node.get('video_duration')),
                'timestamp': int_or_none(node.get('taken_at_timestamp')),
                'view_count': int_or_none(node.get('video_view_count')),
                'comment_count': self._get_count(node, 'comments', 'preview_comment', 'to_comment', 'to_parent_comment'),
                'like_count': self._get_count(node, 'likes', 'preview_like'),
            }

    def _extract_product_media(self, product_media):
        video_id = traverse_obj(product_media, ('pk', {_pk_to_id}))

        formats = traverse_obj(product_media, ('video_versions', lambda _, v: url_or_none(v['url']), {
            'url': 'url',
            'format_id': (('id', {str}), ('type', {int}, {str_or_none}), any),
            'width': ('width', {int_or_none}),
            'height': ('height', {int_or_none}),
        }))
        format_info = traverse_obj(product_media, {
            'vcodec': ('video_codec', {str}),
            'acodec': ('has_audio', {bool}, {lambda x: 'none' if x is False else None}),
        })
        for f in formats:
            f.update(format_info)

        dash = traverse_obj(product_media, ('video_dash_manifest', {str}))
        if dash:
            formats.extend(self._parse_mpd_formats(self._parse_xml(dash, video_id), mpd_id='dash'))

        return {
            'id': video_id,
            'formats': formats,
            'duration': traverse_obj(product_media, ('video_duration', {float_or_none})),
            'thumbnails': list(reversed(traverse_obj(product_media, (
                'image_versions2', 'candidates',
                lambda _, v: url_or_none(v['url']), {
                    'url': 'url',
                    'width': ('width', {int}),
                    'height': 'height',
                },
            )))),
        }

    def _extract_product(self, product_info, video_id=None, get_comments=True):
        if isinstance(product_info, list):
            product_info = product_info[0]

        info_dict = {
            'id': video_id,
            'title': format_field(product_info, [('user', 'username', {str})], 'Video by %s', default=None),
            **traverse_obj(product_info, {
                'id': ('pk', {_pk_to_id}),
                'title': ('title', {str}),
                'description': ('caption', 'text', {str}),
                'channel': ('user', 'username', {str}),
                'uploader_id': ('user', 'pk', {str_or_none}),
                'uploader': ('user', 'full_name', {str}),
                'timestamp': ('taken_at', {int_or_none}),
                'view_count': ('view_count', {int_or_none}),
                'like_count': ('like_count', {int_or_none}),
                'comment_count': ('comment_count', {int_or_none}),
            }),
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
            },
        }

        if carousel_media := traverse_obj(product_info, ('carousel_media', ..., {dict})):
            comments = None
            if get_comments and self.get_param('getcomments'):
                comments = self._get_comments(info_dict.get('id'))

            return {
                '_type': 'playlist',
                **info_dict,
                'title': format_field(info_dict, 'channel', 'Post by %s', default=None),
                'entries': [{
                    **info_dict,
                    **self._extract_product_media(product_media),
                    'comments': comments,
                } for product_media in carousel_media],
            }

        return {
            **info_dict,
            **self._extract_product_media(product_info),
            '__post_extractor': self.extract_comments(info_dict.get('id')) if get_comments else None,
        }

    def _get_comments(self, video_id):
        comments_info = self._download_json(
            f'{self._API_BASE_URL}/media/{_id_to_pk(video_id)}/comments/?can_support_threading=true&permalink_enabled=false', video_id,
            fatal=False, errnote='Comments extraction failed', note='Downloading comments info', headers=self._api_headers) or {}

        comment_data = traverse_obj(comments_info, ('edge_media_to_parent_comment', 'edges'), 'comments')
        for comment_dict in comment_data or []:
            yield {
                'author': traverse_obj(comment_dict, ('node', 'owner', 'username'), ('user', 'username')),
                'author_id': traverse_obj(comment_dict, ('node', 'owner', 'id'), ('user', 'pk'), expected_type=str_or_none),
                'author_thumbnail': traverse_obj(comment_dict, ('node', 'owner', 'profile_pic_url'), ('user', 'profile_pic_url'), expected_type=url_or_none),
                'id': traverse_obj(comment_dict, ('node', 'id'), 'pk', expected_type=str_or_none),
                'text': traverse_obj(comment_dict, ('node', 'text'), 'text'),
                'like_count': traverse_obj(comment_dict, ('node', 'edge_liked_by', 'count'), 'comment_like_count', expected_type=int_or_none),
                'timestamp': traverse_obj(comment_dict, ('node', 'created_at'), 'created_at', expected_type=int_or_none),
            }


class InstagramIOSIE(InfoExtractor):
    IE_DESC = 'IOS instagram:// URL'
    _VALID_URL = r'instagram://media\?id=(?P<id>[\d_]+)'
    _TESTS = [{
        'url': 'instagram://media?id=482584233761418119',
        'md5': '0d2da106a9d2631273e192b372806516',
        'info_dict': {
            'id': 'aye83DjauH',
            'ext': 'mp4',
            'title': 'Video by naomipq',
            'description': 'md5:1f17f0ab29bd6fe2bfad705f58de3cb8',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 0,
            'timestamp': 1371748545,
            'upload_date': '20130620',
            'uploader_id': 'naomipq',
            'uploader': 'B E A U T Y  F O R  A S H E S',
            'like_count': int,
            'comment_count': int,
            'comments': list,
        },
        'add_ie': ['Instagram'],
    }]

    def _real_extract(self, url):
        video_id = _pk_to_id(self._match_id(url))
        return self.url_result(f'http://instagram.com/tv/{video_id}', InstagramIE, video_id)


class InstagramIE(InstagramBaseIE):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?instagram\.com(?:/(?!share/)[^/?#]+)?/(?:p|tv|reels?(?!/audio/))/(?P<id>[^/?#&]+))'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?instagram\.com/p/[^/]+/embed.*?)\1']
    _TESTS = [{
        'url': 'https://instagram.com/p/aye83DjauH/?foo=bar#abc',
        'md5': '0d2da106a9d2631273e192b372806516',
        'info_dict': {
            'id': 'aye83DjauH',
            'ext': 'mp4',
            'title': 'Video by naomipq',
            'description': 'md5:1f17f0ab29bd6fe2bfad705f58de3cb8',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 8.747,
            'timestamp': 1371748545,
            'upload_date': '20130620',
            'uploader_id': '2815873',
            'uploader': 'B E A U T Y  F O R  A S H E S',
            'channel': 'naomipq',
            'like_count': int,
            'comment_count': int,
            'comments': list,
        },
        'expected_warnings': [
            'General metadata extraction failed',
            'Main webpage is locked behind the login page',
        ],
    }, {
        # reel
        'url': 'https://www.instagram.com/reel/Chunk8-jurw/',
        'md5': 'f6d8277f74515fa3ff9f5791426e42b1',
        'info_dict': {
            'id': 'Chunk8-jurw',
            'ext': 'mp4',
            'title': 'Video by instagram',
            'description': 'md5:c9cde483606ed6f80fbe9283a6a2b290',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 5.016,
            'timestamp': 1661529231,
            'upload_date': '20220826',
            'uploader_id': '25025320',
            'uploader': 'Instagram',
            'channel': 'instagram',
            'like_count': int,
            'comment_count': int,
            'comments': list,
        },
        'expected_warnings': [
            'General metadata extraction failed',
            'Main webpage is locked behind the login page',
        ],
    }, {
        # multi video post
        'url': 'https://www.instagram.com/p/BQ0eAlwhDrw/',
        'playlist': [{
            'info_dict': {
                'id': 'BQ0dSaohpPW',
                'ext': 'mp4',
                'title': 'Video 1',
                'thumbnail': r're:^https?://.*\.jpg',
                'view_count': int,
            },
        }, {
            'info_dict': {
                'id': 'BQ0dTpOhuHT',
                'ext': 'mp4',
                'title': 'Video 2',
                'thumbnail': r're:^https?://.*\.jpg',
                'view_count': int,
            },
        }, {
            'info_dict': {
                'id': 'BQ0dT7RBFeF',
                'ext': 'mp4',
                'title': 'Video 3',
                'thumbnail': r're:^https?://.*\.jpg',
                'view_count': int,
            },
        }],
        'info_dict': {
            'id': 'BQ0eAlwhDrw',
            'title': 'Post by instagram',
            'description': 'md5:0f9203fc6a2ce4d228da5754bcf54957',
        },
        'expected_warnings': [
            'General metadata extraction failed',
            'Main webpage is locked behind the login page',
        ],
    }, {
        # IGTV
        'url': 'https://www.instagram.com/tv/BkfuX9UB-eK/',
        'info_dict': {
            'id': 'BkfuX9UB-eK',
            'ext': 'mp4',
            'title': 'Fingerboarding Tricks with @cass.fb',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 53.83,
            'timestamp': 1530032919,
            'upload_date': '20180626',
            'uploader_id': '25025320',
            'uploader': 'Instagram',
            'channel': 'instagram',
            'like_count': int,
            'comment_count': int,
            'comments': list,
            'description': 'Meet Cass Hirst (@cass.fb), a fingerboarding pro who can perform tiny ollies and kickflips while blindfolded.',
        },
        'expected_warnings': [
            'General metadata extraction failed',
            'Main webpage is locked behind the login page',
        ],
    }, {
        'url': 'https://instagram.com/p/-Cmh1cukG2/',
        'only_matching': True,
    }, {
        'url': 'http://instagram.com/p/9o6LshA7zy/embed/',
        'only_matching': True,
    }, {
        'url': 'https://www.instagram.com/tv/aye83DjauH/',
        'only_matching': True,
    }, {
        'url': 'https://www.instagram.com/reel/CDUMkliABpa/',
        'only_matching': True,
    }, {
        'url': 'https://www.instagram.com/marvelskies.fc/reel/CWqAgUZgCku/',
        'only_matching': True,
    }, {
        'url': 'https://www.instagram.com/reels/Cop84x6u7CP/',
        'only_matching': True,
    }]

    _SJS_RE = re.compile(r'<script\b[^>]+\bdata-sjs>(\{.+?\})</script>')

    _lsd_token = None

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        res = tuple(super()._extract_embed_urls(url, webpage))
        if res:
            return res

        mobj = re.search(r'<a[^>]+href=([\'"])(?P<link>[^\'"]+)\1',
                         get_element_by_attribute('class', 'instagram-media', webpage) or '')
        if mobj:
            return [mobj.group('link')]

    def _real_initialize(self):
        if self._is_logged_in:
            self.write_debug('Found Instagram account cookies')
            return
        if not self._lsd_token:
            webpage = self._download_webpage(
                self._BASE_URL, None, 'Setting up session', impersonate=self._can_impersonate)
            eqmc = self._search_json(
                r'<script\b[^>]*\bid="__eqmc"[^>]*>', webpage, 'eqmc JSON', None, default={})
            self._lsd_token = (
                traverse_obj(eqmc, ('l', {str}))
                or self._search_regex(r'\["LSD",\[\],\{"token":"([^"]+)"', webpage, 'LSD token'))

    def _real_extract(self, url):
        video_id, url = self._match_valid_url(url).group('id', 'url')
        media_id = str(_id_to_pk(video_id))

        if self._is_logged_in:
            try:
                return self._extract_product(self._download_json(
                    f'{self._API_BASE_URL}/media/{media_id}/info/', video_id,
                    'Downloading video info', 'Video info extraction failed',
                    impersonate=self._can_impersonate and self._is_web_app,
                    headers=self._api_headers)['items'][0])
            except ExtractorError as e:
                if not (isinstance(e.cause, HTTPError) and self._is_login_redirect(e.cause.response.url)):
                    raise

            self.report_warning('The provided Instagram account cookies are no longer valid')
            # XXX: With curl-cffi, the error response may not invalidate the cookie in our jar
            for domain in self._COOKIE_DOMAINS:
                self.cookiejar.clear(domain=domain, path='/', name=self._AUTH_COOKIE_NAME)
            # Re-initialize to set lsd token for logged-out extraction
            self._real_initialize()

        api_check = self._download_json(
            f'{self._API_BASE_URL}/web/get_ruling_for_content/', video_id,
            'Checking post accessibility', errnote=False, fatal=False,
            impersonate=self._can_impersonate, headers=self._api_headers,
            query={'content_type': 'MEDIA', 'target_id': media_id}) or {}

        csrf_token = self._get_cookies('https://www.instagram.com').get('csrftoken')
        if not csrf_token:
            self.report_warning('No CSRF token set by Instagram API', video_id)
        else:
            csrf_token = csrf_token.value if api_check.get('status') == 'ok' else None
            if not csrf_token:
                self.report_warning('Instagram API is not granting access', video_id)

        response = self._download_json(
            'https://www.instagram.com/api/graphql', video_id,
            fatal=False, impersonate=True,
            headers=filter_dict({
                **self._api_headers,
                'X-FB-Friendly-Name': 'PolarisLoggedOutDesktopWWWPostRootContentQuery',
                'X-CSRFToken': csrf_token,
                'X-FB-LSD': self._lsd_token,
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url,
            }), data=urlencode_postdata({
                'lsd': self._lsd_token,
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'PolarisLoggedOutDesktopWWWPostRootContentQuery',
                'server_timestamps': 'true',
                'variables': json.dumps({'media_id': media_id}, separators=(',', ':')),
                'doc_id': '27130156389949648',
            })) if self._can_impersonate else None

        media = traverse_obj(response, ('data', 'xig_polaris_media', {dict}))
        product_info = traverse_obj(media, ('if_not_gated_logged_out', {dict}))

        if not product_info:
            error = join_nonempty('title', 'description', delim=': ', from_dict=api_check)
            if 'Restricted Video' in error:
                self.raise_login_required(error)
            elif error:
                raise ExtractorError(error, expected=True)
            elif len(video_id) > 28:
                # It's a private post (video_id == shortcode + 28 extra characters)
                # Only raise after getting empty response; sometimes "long"-shortcode posts are public
                self.raise_login_required(
                    'This content is only available for registered users who follow this account')

            webpage, urlh = self._download_webpage_handle(
                f'https://www.instagram.com/p/{video_id}', video_id, impersonate=self._can_impersonate)
            if self._is_login_redirect(urlh.url):
                self.raise_login_required(
                    'The webpage request was redirected to the login page. '
                    'You have exceeded the rate-limit for accessing posts anonymously')

            media = traverse_obj(webpage, (
                {self._SJS_RE.findall}, ..., {json.loads},
                'require', ..., ..., ..., '__bbox', 'require',
                lambda _, v: v[0] == 'RelayPrefetchedStreamCache', ...,
                lambda _, v: v['__bbox']['result']['data']['xig_polaris_media'],
                '__bbox', 'result', 'data', 'xig_polaris_media', {dict}, any))
            product_info = traverse_obj(media, ('if_not_gated_logged_out', {dict}))

        if not product_info:
            raise ExtractorError(
                'Instagram sent an empty media response. Check if this post is accessible in your '
                f'browser without being logged-in. If it is not, then u{self._login_hint()[1:]}. '
                'Otherwise, if the post is accessible in browser without being logged-in'
                f'{bug_reports_message(before=",")}', expected=True)

        info_dict = self._extract_product(product_info, video_id=video_id, get_comments=False)
        is_playlist = info_dict.get('_type') == 'playlist'
        if not is_playlist and not info_dict.get('formats'):
            self.raise_no_formats('There is no video in this post', expected=True)

        comments = traverse_obj(media, (
            'comments_connection', 'edges', lambda _, v: v['node']['text'], 'node', {
                'author': ('user', 'username', {str}),
                'author_id': ('user', 'pk', {str_or_none}),
                'id': ('pk', {str_or_none}),
                'text': ('text', {str}),
                'timestamp': ('created_at', {int_or_none}),
                'like_count': ('comment_like_count', {int_or_none}),
            }))

        if is_playlist:
            for entry in info_dict['entries']:
                entry['comments'] = comments
        else:
            info_dict['comments'] = comments

        return info_dict


class InstagramPlaylistBaseIE(InstagramBaseIE):
    _gis_tmpl = None  # used to cache GIS request type

    def _parse_graphql(self, webpage, item_id):
        # Reads a webpage and returns its GraphQL data.
        return self._parse_json(
            self._search_regex(
                r'sharedData\s*=\s*({.+?})\s*;\s*[<\n]', webpage, 'data'),
            item_id)

    def _extract_graphql(self, data, url):
        # Parses GraphQL queries containing videos and generates a playlist.
        uploader_id = self._match_id(url)
        csrf_token = data['config']['csrf_token']
        rhx_gis = data.get('rhx_gis') or '3c7ca9dcefcf966d11dacf1f151335e8'

        cursor = ''
        for page_num in itertools.count(1):
            variables = {
                'first': 12,
                'after': cursor,
            }
            variables.update(self._query_vars_for(data))
            variables = json.dumps(variables)

            if self._gis_tmpl:
                gis_tmpls = [self._gis_tmpl]
            else:
                gis_tmpls = [
                    f'{rhx_gis}',
                    '',
                    f'{rhx_gis}:{csrf_token}',
                    '{}:{}:{}'.format(rhx_gis, csrf_token, self.get_param('http_headers')['User-Agent']),
                ]

            # try all of the ways to generate a GIS query, and not only use the
            # first one that works, but cache it for future requests
            for gis_tmpl in gis_tmpls:
                try:
                    json_data = self._download_json(
                        'https://www.instagram.com/graphql/query/', uploader_id,
                        f'Downloading JSON page {page_num}', headers={
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-Instagram-GIS': hashlib.md5(
                                (f'{gis_tmpl}:{variables}').encode()).hexdigest(),
                        }, query={
                            'query_hash': self._QUERY_HASH,
                            'variables': variables,
                        })
                    media = self._parse_timeline_from(json_data)
                    self._gis_tmpl = gis_tmpl
                    break
                except ExtractorError as e:
                    # if it's an error caused by a bad query, and there are
                    # more GIS templates to try, ignore it and keep trying
                    if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                        if gis_tmpl != gis_tmpls[-1]:
                            continue
                    raise

            nodes = traverse_obj(media, ('edges', ..., 'node'), expected_type=dict) or []
            if not nodes:
                break
            yield from self._extract_nodes(nodes)

            has_next_page = traverse_obj(media, ('page_info', 'has_next_page'))
            cursor = traverse_obj(media, ('page_info', 'end_cursor'), expected_type=str)
            if not has_next_page or not cursor:
                break

    def _real_extract(self, url):
        user_or_tag = self._match_id(url)
        webpage = self._download_webpage(url, user_or_tag)
        data = self._parse_graphql(webpage, user_or_tag)

        self._set_cookie('instagram.com', 'ig_pr', '1')

        return self.playlist_result(
            self._extract_graphql(data, url), user_or_tag, user_or_tag)


class InstagramUserIE(InstagramPlaylistBaseIE):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?instagram\.com/(?P<id>[^/]{2,})/?(?:$|[?#])'
    IE_DESC = 'Instagram user profile'
    IE_NAME = 'instagram:user'
    _TESTS = [{
        'url': 'https://instagram.com/porsche',
        'info_dict': {
            'id': 'porsche',
            'title': 'porsche',
        },
        'playlist_count': 5,
        'params': {
            'extract_flat': True,
            'skip_download': True,
            'playlistend': 5,
        },
    }]

    _QUERY_HASH = ('42323d64886122307be10013ad2dcc44',)

    @staticmethod
    def _parse_timeline_from(data):
        # extracts the media timeline data from a GraphQL result
        return data['data']['user']['edge_owner_to_timeline_media']

    @staticmethod
    def _query_vars_for(data):
        # returns a dictionary of variables to add to the timeline query based
        # on the GraphQL of the original page
        return {
            'id': data['entry_data']['ProfilePage'][0]['graphql']['user']['id'],
        }


class InstagramTagIE(InstagramPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?instagram\.com/explore/tags/(?P<id>[^/]+)'
    IE_DESC = 'Instagram hashtag search URLs'
    IE_NAME = 'instagram:tag'
    _TESTS = [{
        'url': 'https://instagram.com/explore/tags/lolcats',
        'info_dict': {
            'id': 'lolcats',
            'title': 'lolcats',
        },
        'playlist_count': 50,
        'params': {
            'extract_flat': True,
            'skip_download': True,
            'playlistend': 50,
        },
    }]

    _QUERY_HASH = ('f92f56d47dc7a55b606908374b43a314',)

    @staticmethod
    def _parse_timeline_from(data):
        # extracts the media timeline data from a GraphQL result
        return data['data']['hashtag']['edge_hashtag_to_media']

    @staticmethod
    def _query_vars_for(data):
        # returns a dictionary of variables to add to the timeline query based
        # on the GraphQL of the original page
        return {
            'tag_name':
                data['entry_data']['TagPage'][0]['graphql']['hashtag']['name'],
        }


class InstagramStoryIE(InstagramBaseIE):
    _VALID_URL = r'https?://(?:www\.)?instagram\.com/stories/(?P<user>[^/?#]+)(?:/(?P<id>\d+))?'
    IE_NAME = 'instagram:story'

    _TESTS = [{
        'url': 'https://www.instagram.com/stories/highlights/18090946048123978/',
        'info_dict': {
            'id': '18090946048123978',
            'title': 'Rare',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://www.instagram.com/stories/fruits_zipper/3570766765028588805/',
        'only_matching': True,
    }, {
        'url': 'https://www.instagram.com/stories/fruits_zipper',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        username, story_id = self._match_valid_url(url).group('user', 'id')
        if username == 'highlights' and not story_id:  # story id is only mandatory for highlights
            raise ExtractorError('Input URL is missing a highlight ID', expected=True)
        display_id = story_id or username
        story_info = self._download_webpage(
            url, display_id, impersonate=self._can_impersonate and self._is_web_app)
        user_info = self._search_json(r'"user":', story_info, 'user info', display_id, fatal=False)
        if not user_info:
            self.raise_login_required('This content is unreachable')

        user_id = traverse_obj(user_info, 'pk', 'id', expected_type=str_or_none)
        if username == 'highlights':
            story_info_url = f'highlight:{story_id}'
        else:
            if not user_id:  # user id is only mandatory for non-highlights
                raise ExtractorError('Unable to extract user id')
            story_info_url = user_id

        videos = traverse_obj(self._download_json(
            f'{self._API_BASE_URL}/feed/reels_media/?reel_ids={story_info_url}',
            display_id, errnote=False, fatal=False, headers=self._api_headers,
            impersonate=self._can_impersonate and self._is_web_app), 'reels')
        if not videos:
            self.raise_login_required('You need to log in to access this content')
        user_info = traverse_obj(videos, (user_id, 'user', {dict})) or {}

        full_name = traverse_obj(videos, (f'highlight:{story_id}', 'user', 'full_name'), (user_id, 'user', 'full_name'))
        story_title = traverse_obj(videos, (f'highlight:{story_id}', 'title'))
        if not story_title:
            story_title = f'Story by {username}'

        highlights = traverse_obj(videos, (f'highlight:{story_id}', 'items'), (user_id, 'items'))
        info_data = []
        for highlight in highlights:
            highlight.setdefault('user', {}).update(user_info)
            highlight_data = self._extract_product(highlight)
            if highlight_data.get('formats'):
                info_data.append({
                    'uploader': full_name,
                    'uploader_id': user_id,
                    **filter_dict(highlight_data),
                })
        if username != 'highlights' and story_id and not self._yes_playlist(username, story_id):
            return traverse_obj(info_data, (lambda _, v: v['id'] == _pk_to_id(story_id), any))

        return self.playlist_result(info_data, playlist_id=story_id, playlist_title=story_title)

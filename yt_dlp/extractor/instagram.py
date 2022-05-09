import itertools
import hashlib
import json
import re
import time

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
)
from ..utils import (
    ExtractorError,
    format_field,
    float_or_none,
    get_element_by_attribute,
    int_or_none,
    lowercase_escape,
    str_or_none,
    str_to_int,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class InstagramBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'instagram'
    _IS_LOGGED_IN = False

    def _perform_login(self, username, password):
        if self._IS_LOGGED_IN:
            return

        login_webpage = self._download_webpage(
            'https://www.instagram.com/accounts/login/', None,
            note='Downloading login webpage', errnote='Failed to download login webpage')

        shared_data = self._parse_json(
            self._search_regex(
                r'window\._sharedData\s*=\s*({.+?});',
                login_webpage, 'shared data', default='{}'),
            None)

        login = self._download_json('https://www.instagram.com/accounts/login/ajax/', None, note='Logging in', headers={
            'Accept': '*/*',
            'X-IG-App-ID': '936619743392459',
            'X-ASBD-ID': '198387',
            'X-IG-WWW-Claim': '0',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': shared_data['config']['csrf_token'],
            'X-Instagram-AJAX': shared_data['rollout_hash'],
            'Referer': 'https://www.instagram.com/',
        }, data=urlencode_postdata({
            'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}',
            'username': username,
            'queryParams': '{}',
            'optIntoOneTap': 'false',
            'stopDeletionNonce': '',
            'trustedDeviceRecords': '{}',
        }))

        if not login.get('authenticated'):
            if login.get('message'):
                raise ExtractorError(f'Unable to login: {login["message"]}')
            elif login.get('user'):
                raise ExtractorError('Unable to login: Sorry, your password was incorrect. Please double-check your password.', expected=True)
            elif login.get('user') is False:
                raise ExtractorError('Unable to login: The username you entered doesn\'t belong to an account. Please check your username and try again.', expected=True)
            raise ExtractorError('Unable to login')
        InstagramBaseIE._IS_LOGGED_IN = True

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
                    }
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
        media_id = product_media.get('code') or product_media.get('id')
        vcodec = product_media.get('video_codec')
        dash_manifest_raw = product_media.get('video_dash_manifest')
        videos_list = product_media.get('video_versions')
        if not (dash_manifest_raw or videos_list):
            return {}

        formats = [{
            'format_id': format.get('id'),
            'url': format.get('url'),
            'width': format.get('width'),
            'height': format.get('height'),
            'vcodec': vcodec,
        } for format in videos_list or []]
        if dash_manifest_raw:
            formats.extend(self._parse_mpd_formats(self._parse_xml(dash_manifest_raw, media_id), mpd_id='dash'))
        self._sort_formats(formats)

        thumbnails = [{
            'url': thumbnail.get('url'),
            'width': thumbnail.get('width'),
            'height': thumbnail.get('height')
        } for thumbnail in traverse_obj(product_media, ('image_versions2', 'candidates')) or []]
        return {
            'id': media_id,
            'duration': float_or_none(product_media.get('video_duration')),
            'formats': formats,
            'thumbnails': thumbnails
        }

    def _extract_product(self, product_info):
        if isinstance(product_info, list):
            product_info = product_info[0]

        user_info = product_info.get('user') or {}
        info_dict = {
            'id': product_info.get('code') or product_info.get('id'),
            'title': product_info.get('title') or f'Video by {user_info.get("username")}',
            'description': traverse_obj(product_info, ('caption', 'text'), expected_type=str_or_none),
            'timestamp': int_or_none(product_info.get('taken_at')),
            'channel': user_info.get('username'),
            'uploader': user_info.get('full_name'),
            'uploader_id': str_or_none(user_info.get('pk')),
            'view_count': int_or_none(product_info.get('view_count')),
            'like_count': int_or_none(product_info.get('like_count')),
            'comment_count': int_or_none(product_info.get('comment_count')),
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
            }
        }
        carousel_media = product_info.get('carousel_media')
        if carousel_media:
            return {
                '_type': 'playlist',
                **info_dict,
                'title': f'Post by {user_info.get("username")}',
                'entries': [{
                    **info_dict,
                    **self._extract_product_media(product_media),
                } for product_media in carousel_media],
            }

        return {
            **info_dict,
            **self._extract_product_media(product_info)
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
        'add_ie': ['Instagram']
    }]

    def _get_id(self, id):
        """Source: https://stackoverflow.com/questions/24437823/getting-instagram-post-url-from-media-id"""
        chrs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        media_id = int(id.split('_')[0])
        shortened_id = ''
        while media_id > 0:
            r = media_id % 64
            media_id = (media_id - r) // 64
            shortened_id = chrs[r] + shortened_id
        return shortened_id

    def _real_extract(self, url):
        return {
            '_type': 'url_transparent',
            'url': f'http://instagram.com/tv/{self._get_id(self._match_id(url))}/',
            'ie_key': 'Instagram',
        }


class InstagramIE(InstagramBaseIE):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?instagram\.com(?:/[^/]+)?/(?:p|tv|reel)/(?P<id>[^/?#&]+))'
    _TESTS = [{
        'url': 'https://instagram.com/p/aye83DjauH/?foo=bar#abc',
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
            'uploader_id': '2815873',
            'uploader': 'B E A U T Y  F O R  A S H E S',
            'channel': 'naomipq',
            'like_count': int,
            'comment_count': int,
            'comments': list,
        },
    }, {
        # missing description
        'url': 'https://www.instagram.com/p/BA-pQFBG8HZ/?taken-by=britneyspears',
        'info_dict': {
            'id': 'BA-pQFBG8HZ',
            'ext': 'mp4',
            'title': 'Video by britneyspears',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 0,
            'timestamp': 1453760977,
            'upload_date': '20160125',
            'uploader_id': '12246775',
            'uploader': 'Britney Spears',
            'channel': 'britneyspears',
            'like_count': int,
            'comment_count': int,
            'comments': list,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # multi video post
        'url': 'https://www.instagram.com/p/BQ0eAlwhDrw/',
        'playlist': [{
            'info_dict': {
                'id': 'BQ0dSaohpPW',
                'ext': 'mp4',
                'title': 'Video 1',
            },
        }, {
            'info_dict': {
                'id': 'BQ0dTpOhuHT',
                'ext': 'mp4',
                'title': 'Video 2',
            },
        }, {
            'info_dict': {
                'id': 'BQ0dT7RBFeF',
                'ext': 'mp4',
                'title': 'Video 3',
            },
        }],
        'info_dict': {
            'id': 'BQ0eAlwhDrw',
            'title': 'Post by instagram',
            'description': 'md5:0f9203fc6a2ce4d228da5754bcf54957',
        },
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
        }
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
    }]

    @staticmethod
    def _extract_embed_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?instagram\.com/p/[^/]+/embed.*?)\1',
            webpage)
        if mobj:
            return mobj.group('url')

        blockquote_el = get_element_by_attribute(
            'class', 'instagram-media', webpage)
        if blockquote_el is None:
            return

        mobj = re.search(
            r'<a[^>]+href=([\'"])(?P<link>[^\'"]+)\1', blockquote_el)
        if mobj:
            return mobj.group('link')

    def _real_extract(self, url):
        video_id, url = self._match_valid_url(url).group('id', 'url')
        webpage, urlh = self._download_webpage_handle(url, video_id)
        if 'www.instagram.com/accounts/login' in urlh.geturl():
            self.report_warning('Main webpage is locked behind the login page. '
                                'Retrying with embed webpage (Note that some metadata might be missing)')
            webpage = self._download_webpage(
                'https://www.instagram.com/p/%s/embed/' % video_id, video_id, note='Downloading embed webpage')

        shared_data = self._parse_json(
            self._search_regex(
                r'window\._sharedData\s*=\s*({.+?});',
                webpage, 'shared data', default='{}'),
            video_id, fatal=False)
        media = traverse_obj(
            shared_data,
            ('entry_data', 'PostPage', 0, 'graphql', 'shortcode_media'),
            ('entry_data', 'PostPage', 0, 'media'),
            expected_type=dict)

        # _sharedData.entry_data.PostPage is empty when authenticated (see
        # https://github.com/ytdl-org/youtube-dl/pull/22880)
        if not media:
            additional_data = self._parse_json(
                self._search_regex(
                    r'window\.__additionalDataLoaded\s*\(\s*[^,]+,\s*({.+?})\s*\);',
                    webpage, 'additional data', default='{}'),
                video_id, fatal=False)
            product_item = traverse_obj(additional_data, ('items', 0), expected_type=dict)
            if product_item:
                return self._extract_product(product_item)
            media = traverse_obj(additional_data, ('graphql', 'shortcode_media'), 'shortcode_media', expected_type=dict) or {}

        if not media and 'www.instagram.com/accounts/login' in urlh.geturl():
            self.raise_login_required('You need to log in to access this content')

        username = traverse_obj(media, ('owner', 'username')) or self._search_regex(
            r'"owner"\s*:\s*{\s*"username"\s*:\s*"(.+?)"', webpage, 'username', fatal=False)

        description = (
            traverse_obj(media, ('edge_media_to_caption', 'edges', 0, 'node', 'text'), expected_type=str)
            or media.get('caption'))
        if not description:
            description = self._search_regex(
                r'"caption"\s*:\s*"(.+?)"', webpage, 'description', default=None)
            if description is not None:
                description = lowercase_escape(description)

        video_url = media.get('video_url')
        if not video_url:
            nodes = traverse_obj(media, ('edge_sidecar_to_children', 'edges', ..., 'node'), expected_type=dict) or []
            if nodes:
                return self.playlist_result(
                    self._extract_nodes(nodes, True), video_id,
                    format_field(username, template='Post by %s'), description)

            video_url = self._og_search_video_url(webpage, secure=False)

        formats = [{
            'url': video_url,
            'width': self._get_dimension('width', media, webpage),
            'height': self._get_dimension('height', media, webpage),
        }]
        dash = traverse_obj(media, ('dash_info', 'video_dash_manifest'))
        if dash:
            formats.extend(self._parse_mpd_formats(self._parse_xml(dash, video_id), mpd_id='dash'))
        self._sort_formats(formats)

        comment_data = traverse_obj(media, ('edge_media_to_parent_comment', 'edges'))
        comments = [{
            'author': traverse_obj(comment_dict, ('node', 'owner', 'username')),
            'author_id': traverse_obj(comment_dict, ('node', 'owner', 'id')),
            'id': traverse_obj(comment_dict, ('node', 'id')),
            'text': traverse_obj(comment_dict, ('node', 'text')),
            'timestamp': traverse_obj(comment_dict, ('node', 'created_at'), expected_type=int_or_none),
        } for comment_dict in comment_data] if comment_data else None

        display_resources = (
            media.get('display_resources')
            or [{'src': media.get(key)} for key in ('display_src', 'display_url')]
            or [{'src': self._og_search_thumbnail(webpage)}])
        thumbnails = [{
            'url': thumbnail['src'],
            'width': thumbnail.get('config_width'),
            'height': thumbnail.get('config_height'),
        } for thumbnail in display_resources if thumbnail.get('src')]

        return {
            'id': video_id,
            'formats': formats,
            'title': media.get('title') or 'Video by %s' % username,
            'description': description,
            'duration': float_or_none(media.get('video_duration')),
            'timestamp': traverse_obj(media, 'taken_at_timestamp', 'date', expected_type=int_or_none),
            'uploader_id': traverse_obj(media, ('owner', 'id')),
            'uploader': traverse_obj(media, ('owner', 'full_name')),
            'channel': username,
            'like_count': self._get_count(media, 'likes', 'preview_like') or str_to_int(self._search_regex(
                r'data-log-event="likeCountClick"[^>]*>[^\d]*([\d,\.]+)', webpage, 'like count', fatal=False)),
            'comment_count': self._get_count(media, 'comments', 'preview_comment', 'to_comment', 'to_parent_comment'),
            'comments': comments,
            'thumbnails': thumbnails,
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
            }
        }


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
                    '%s' % rhx_gis,
                    '',
                    '%s:%s' % (rhx_gis, csrf_token),
                    '%s:%s:%s' % (rhx_gis, csrf_token, self.get_param('http_headers')['User-Agent']),
                ]

            # try all of the ways to generate a GIS query, and not only use the
            # first one that works, but cache it for future requests
            for gis_tmpl in gis_tmpls:
                try:
                    json_data = self._download_json(
                        'https://www.instagram.com/graphql/query/', uploader_id,
                        'Downloading JSON page %d' % page_num, headers={
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-Instagram-GIS': hashlib.md5(
                                ('%s:%s' % (gis_tmpl, variables)).encode('utf-8')).hexdigest(),
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
                    if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
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
        }
    }]

    _QUERY_HASH = '42323d64886122307be10013ad2dcc44',

    @staticmethod
    def _parse_timeline_from(data):
        # extracts the media timeline data from a GraphQL result
        return data['data']['user']['edge_owner_to_timeline_media']

    @staticmethod
    def _query_vars_for(data):
        # returns a dictionary of variables to add to the timeline query based
        # on the GraphQL of the original page
        return {
            'id': data['entry_data']['ProfilePage'][0]['graphql']['user']['id']
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
        }
    }]

    _QUERY_HASH = 'f92f56d47dc7a55b606908374b43a314',

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
                data['entry_data']['TagPage'][0]['graphql']['hashtag']['name']
        }


class InstagramStoryIE(InstagramBaseIE):
    _VALID_URL = r'https?://(?:www\.)?instagram\.com/stories/(?P<user>[^/]+)/(?P<id>\d+)'
    IE_NAME = 'instagram:story'

    _TESTS = [{
        'url': 'https://www.instagram.com/stories/highlights/18090946048123978/',
        'info_dict': {
            'id': '18090946048123978',
            'title': 'Rare',
        },
        'playlist_mincount': 50
    }]

    def _real_extract(self, url):
        username, story_id = self._match_valid_url(url).groups()

        story_info_url = f'{username}/{story_id}/?__a=1' if username == 'highlights' else f'{username}/?__a=1'
        story_info = self._download_json(f'https://www.instagram.com/stories/{story_info_url}', story_id, headers={
            'X-IG-App-ID': 936619743392459,
            'X-ASBD-ID': 198387,
            'X-IG-WWW-Claim': 0,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': url,
        })
        user_id = story_info['user']['id']
        highlight_title = traverse_obj(story_info, ('highlight', 'title'))

        story_info_url = user_id if username != 'highlights' else f'highlight:{story_id}'
        videos = self._download_json(f'https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={story_info_url}', story_id, headers={
            'X-IG-App-ID': 936619743392459,
            'X-ASBD-ID': 198387,
            'X-IG-WWW-Claim': 0,
        })['reels']

        full_name = traverse_obj(videos, ('user', 'full_name'))

        user_info = {}
        if not (username and username != 'highlights' and full_name):
            user_info = self._download_json(
                f'https://i.instagram.com/api/v1/users/{user_id}/info/', story_id, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SM-A505F Build/RP1A.200720.012; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/96.0.4664.45 Mobile Safari/537.36 Instagram 214.1.0.29.120 Android (30/11; 450dpi; 1080x2122; samsung; SM-A505F; a50; exynos9610; en_US; 333717274)',
                }, note='Downloading user info')

        username = traverse_obj(user_info, ('user', 'username')) or username
        full_name = traverse_obj(user_info, ('user', 'full_name')) or full_name

        highlights = traverse_obj(videos, (f'highlight:{story_id}', 'items'), (str(user_id), 'items'))
        return self.playlist_result([{
            **self._extract_product(highlight),
            'title': f'Story by {username}',
            'uploader': full_name,
            'uploader_id': user_id,
        } for highlight in highlights], playlist_id=story_id, playlist_title=highlight_title)

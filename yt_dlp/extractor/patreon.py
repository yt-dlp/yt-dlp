# coding: utf-8
from __future__ import unicode_literals

import itertools

from .common import InfoExtractor
from .vimeo import VimeoIE

from ..compat import compat_urllib_parse_unquote
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    KNOWN_EXTENSIONS,
    mimetype2ext,
    parse_iso8601,
    str_or_none,
    try_get,
    url_or_none,
)


class PatreonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?patreon\.com/(?:creation\?hid=|posts/(?:[\w-]+-)?)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.patreon.com/creation?hid=743933',
        'md5': 'e25505eec1053a6e6813b8ed369875cc',
        'info_dict': {
            'id': '743933',
            'ext': 'mp3',
            'title': 'Episode 166: David Smalley of Dogma Debate',
            'description': 'md5:713b08b772cd6271b9f3906683cfacdf',
            'uploader': 'Cognitive Dissonance Podcast',
            'thumbnail': 're:^https?://.*$',
            'timestamp': 1406473987,
            'upload_date': '20140727',
            'uploader_id': '87145',
        },
    }, {
        'url': 'http://www.patreon.com/creation?hid=754133',
        'md5': '3eb09345bf44bf60451b8b0b81759d0a',
        'info_dict': {
            'id': '754133',
            'ext': 'mp3',
            'title': 'CD 167 Extra',
            'uploader': 'Cognitive Dissonance Podcast',
            'thumbnail': 're:^https?://.*$',
        },
        'skip': 'Patron-only content',
    }, {
        'url': 'https://www.patreon.com/creation?hid=1682498',
        'info_dict': {
            'id': 'SU4fj_aEMVw',
            'ext': 'mp4',
            'title': 'I\'m on Patreon!',
            'uploader': 'TraciJHines',
            'thumbnail': 're:^https?://.*$',
            'upload_date': '20150211',
            'description': 'md5:c5a706b1f687817a3de09db1eb93acd4',
            'uploader_id': 'TraciJHines',
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        }
    }, {
        'url': 'https://www.patreon.com/posts/episode-166-of-743933',
        'only_matching': True,
    }, {
        'url': 'https://www.patreon.com/posts/743933',
        'only_matching': True,
    }, {
        'url': 'https://www.patreon.com/posts/kitchen-as-seen-51706779',
        'md5': '96656690071f6d64895866008484251b',
        'info_dict': {
            'id': '555089736',
            'ext': 'mp4',
            'title': 'KITCHEN AS SEEN ON DEEZ NUTS EXTENDED!',
            'uploader': 'Cold Ones',
            'thumbnail': 're:^https?://.*$',
            'upload_date': '20210526',
            'description': 'md5:557a409bd79d3898689419094934ba79',
            'uploader_id': '14936315',
        },
        'skip': 'Patron-only content'
    }]

    # Currently Patreon exposes download URL via hidden CSS, so login is not
    # needed. Keeping this commented for when this inevitably changes.
    '''
    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        login_form = {
            'redirectUrl': 'http://www.patreon.com/',
            'email': username,
            'password': password,
        }

        request = sanitized_Request(
            'https://www.patreon.com/processLogin',
            compat_urllib_parse_urlencode(login_form).encode('utf-8')
        )
        login_page = self._download_webpage(request, None, note='Logging in')

        if re.search(r'onLoginFailed', login_page):
            raise ExtractorError('Unable to login, incorrect username and/or password', expected=True)

    def _real_initialize(self):
        self._login()
    '''

    def _real_extract(self, url):
        video_id = self._match_id(url)
        post = self._download_json(
            'https://www.patreon.com/api/posts/' + video_id, video_id, query={
                'fields[media]': 'download_url,mimetype,size_bytes',
                'fields[post]': 'comment_count,content,embed,image,like_count,post_file,published_at,title',
                'fields[user]': 'full_name,url',
                'json-api-use-default-includes': 'false',
                'include': 'media,user',
            })
        attributes = post['data']['attributes']
        title = attributes['title'].strip()
        image = attributes.get('image') or {}
        info = {
            'id': video_id,
            'title': title,
            'description': clean_html(attributes.get('content')),
            'thumbnail': image.get('large_url') or image.get('url'),
            'timestamp': parse_iso8601(attributes.get('published_at')),
            'like_count': int_or_none(attributes.get('like_count')),
            'comment_count': int_or_none(attributes.get('comment_count')),
        }

        for i in post.get('included', []):
            i_type = i.get('type')
            if i_type == 'media':
                media_attributes = i.get('attributes') or {}
                download_url = media_attributes.get('download_url')
                ext = mimetype2ext(media_attributes.get('mimetype'))
                if download_url and ext in KNOWN_EXTENSIONS:
                    info.update({
                        'ext': ext,
                        'filesize': int_or_none(media_attributes.get('size_bytes')),
                        'url': download_url,
                    })
            elif i_type == 'user':
                user_attributes = i.get('attributes')
                if user_attributes:
                    info.update({
                        'uploader': user_attributes.get('full_name'),
                        'uploader_id': str_or_none(i.get('id')),
                        'uploader_url': user_attributes.get('url'),
                    })

        if not info.get('url'):
            # handle Vimeo embeds
            if try_get(attributes, lambda x: x['embed']['provider']) == 'Vimeo':
                embed_html = try_get(attributes, lambda x: x['embed']['html'])
                v_url = url_or_none(compat_urllib_parse_unquote(
                    self._search_regex(r'(https(?:%3A%2F%2F|://)player\.vimeo\.com.+app_id(?:=|%3D)+\d+)', embed_html, 'vimeo url', fatal=False)))
                if v_url:
                    info.update({
                        '_type': 'url_transparent',
                        'url': VimeoIE._smuggle_referrer(v_url, 'https://patreon.com'),
                        'ie_key': 'Vimeo',
                    })

        if not info.get('url'):
            embed_url = try_get(attributes, lambda x: x['embed']['url'])
            if embed_url:
                info.update({
                    '_type': 'url',
                    'url': embed_url,
                })

        if not info.get('url'):
            post_file = attributes['post_file']
            ext = determine_ext(post_file.get('name'))
            if ext in KNOWN_EXTENSIONS:
                info.update({
                    'ext': ext,
                    'url': post_file['url'],
                })

        return info


class PatreonUserIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.)?patreon\.com/(?!rss)(?P<id>[-\w]+)'

    _TESTS = [{
        'url': 'https://www.patreon.com/dissonancepod/',
        'info_dict': {
            'title': 'dissonancepod',
        },
        'playlist_mincount': 68,
        'expected_warnings': 'Post not viewable by current user! Skipping!',
    }, {
        'url': 'https://www.patreon.com/dissonancepod/posts',
        'only_matching': True
    }, ]

    @classmethod
    def suitable(cls, url):
        return False if PatreonIE.suitable(url) else super(PatreonUserIE, cls).suitable(url)

    def _entries(self, campaign_id, user_id):
        cursor = None
        params = {
            'fields[campaign]': 'show_audio_post_download_links,name,url',
            'fields[post]': 'current_user_can_view,embed,image,is_paid,post_file,published_at,patreon_url,url,post_type,thumbnail_url,title',
            'filter[campaign_id]': campaign_id,
            'filter[is_draft]': 'false',
            'sort': '-published_at',
            'json-api-version': 1.0,
            'json-api-use-default-includes': 'false',
        }

        for page in itertools.count(1):

            params.update({'page[cursor]': cursor} if cursor else {})
            posts_json = self._download_json('https://www.patreon.com/api/posts', user_id, note='Downloading posts page %d' % page, query=params, headers={'Cookie': '.'})

            cursor = try_get(posts_json, lambda x: x['meta']['pagination']['cursors']['next'])

            for post in posts_json.get('data') or []:
                yield self.url_result(url_or_none(try_get(post, lambda x: x['attributes']['patreon_url'])), 'Patreon')

            if cursor is None:
                break

    def _real_extract(self, url):

        user_id = self._match_id(url)
        webpage = self._download_webpage(url, user_id, headers={'Cookie': '.'})
        campaign_id = self._search_regex(r'https://www.patreon.com/api/campaigns/(\d+)/?', webpage, 'Campaign ID')
        return self.playlist_result(self._entries(campaign_id, user_id), playlist_title=user_id)

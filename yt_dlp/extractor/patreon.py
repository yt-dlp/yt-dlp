# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    KNOWN_EXTENSIONS,
    mimetype2ext,
    parse_iso8601,
    str_or_none,
    try_get,
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

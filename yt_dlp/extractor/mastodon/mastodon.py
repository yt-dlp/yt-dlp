# coding: utf-8
from __future__ import unicode_literals

import itertools
import json
import re

try:
    from .instances import instances
except ImportError:
    instances = ('gab.com', )

from ..common import SelfHostedInfoExtractor
from ..peertube.peertube import PeerTubeIE
from ...utils import (
    ExtractorError,
    clean_html,
    parse_duration,
    get_first_group,
    str_or_none,
    int_or_none,
    float_or_none,
    traverse_obj,
    try_get,
    parse_qs,
    url_or_none,
)
from ...compat import (
    compat_urllib_parse_urlencode as urlencode,
    compat_urlparse as urlparse,
)


known_valid_instances = set()


class MastodonBaseIE(SelfHostedInfoExtractor):
    _SH_VALID_CONTENT_STRINGS = (
        ',"settings":{"known_fediverse":',  # Mastodon initial-state
        '<li><a href="https://docs.joinmastodon.org/">Documentation</a></li>',
        '<title>Pleroma</title>',
        '<noscript>To use Pleroma, please enable JavaScript.</noscript>',
        '<noscript>To use Soapbox, please enable JavaScript.</noscript>',
        'Alternatively, try one of the <a href="https://apps.gab.com">native apps</a> for Gab Social for your platform.',
    )
    _SH_VALID_CONTENT_SOFTWARES = ('mastodon', 'mastodon', 'pleroma', 'pleroma', 'pleroma', 'gab')
    _SH_VALID_CONTENT_REGEXES = (
        # double quotes on Mastodon, single quotes on Gab Social
        r'<script id=[\'"]initial-state[\'"] type=[\'"]application/json[\'"]>{"meta":{"streaming_api_base_url":"wss://',
    )
    _NETRC_MACHINE = 'mastodon'

    _IMPOSSIBLE_HOSTNAMES = ('medium.com', 'lbry.tv')
    _HOSTNAME_GROUPS = ('domain_1', 'domain_2', 'domain')
    _INSTANCE_LIST = instances
    _DYNAMIC_INSTANCE_LIST = known_valid_instances
    _NODEINFO_SOFTWARE = ('mastodon', 'pleroma', 'gab')
    _SOFTWARE_NAME = 'Mastodon'

    def _login(self):
        username, password = self._get_login_info()
        if not username:
            return False

        # very basic regex, but the instance domain (the one where user has an account)
        # must be separated from the user login
        mobj = re.match(r'^(?P<username>[^@]+(?:@[^@]+)?)@(?P<instance>.+)$', username)
        if not mobj:
            self.report_error(
                'Invalid login format - must be in format [username or email]@[instance]')
        username, instance = mobj.group('username', 'instance')

        app_info = self._downloader.cache.load('mastodon-apps', instance)
        if not app_info:
            app_info = self._download_json(
                f'https://{instance}/api/v1/apps', None, 'Creating an app', headers={
                    'Content-Type': 'application/json',
                }, data=bytes(json.dumps({
                    'client_name': 'ytdl-patched Mastodon Extractor',
                    'redirect_uris': 'urn:ietf:wg:oauth:2.0:oob',
                    'scopes': 'read',
                    'website': 'https://github.com/ytdl-patched/ytdl-patched',
                }).encode('utf-8')))
            self._downloader.cache.store('mastodon-apps', instance, app_info)

        login_webpage = self._download_webpage(
            f'https://{instance}/oauth/authorize', None, 'Downloading login page', query={
                'client_id': app_info['client_id'],
                'scope': 'read',
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'response_type': 'code',
            })
        oauth_token = None
        # this needs to be codebase-specific, as the HTML page differs between codebases
        if 'xlink:href="#mastodon-svg-logo-full"' in login_webpage:
            # mastodon
            if '@' not in username:
                self.report_warning(
                    'Invalid login format - for Mastodon instances e-mail address is required')
            login_form = self._hidden_inputs(login_webpage)
            login_form['user[email]'] = username
            login_form['user[password]'] = password
            login_req, urlh = self._download_webpage_handle(
                f'https://{instance}/auth/sign_in', None, 'Sending login details',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }, data=bytes(urlencode(login_form).encode('utf-8')))
            # cached apps may already be authorized
            if '/oauth/authorize/native' in urlh.url:
                oauth_token = parse_qs(urlparse(urlh.url).query)['code'][0]
            else:
                auth_form = self._hidden_inputs(
                    self._search_regex(
                        r'(?s)(<form\b[^>]+>.+?>Authorize</.+?</form>)',
                        login_req, 'authorization form'))
                _, urlh = self._download_webpage_handle(
                    f'https://{instance}/oauth/authorize', None, 'Confirming authorization',
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }, data=bytes(urlencode(auth_form).encode('utf-8')))
                oauth_token = parse_qs(urlparse(urlh.url).query)['code'][0]
        elif 'content: "✔\\fe0e";' in login_webpage:
            # pleroma
            login_form = self._hidden_inputs(login_webpage)
            login_form['authorization[scope][]'] = 'read'
            login_form['authorization[name]'] = username
            login_form['authorization[password]'] = password
            login_req = self._download_webpage(
                f'https://{instance}/oauth/authorize', None, 'Sending login details',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }, data=bytes(urlencode(login_form).encode('utf-8')))
            # TODO: 2FA, error handling
            oauth_token = self._search_regex(
                r'<h2>\s*Token code is\s*<br>\s*([a-zA-Z\d_-]+)\s*</h2>',
                login_req, 'oauth token')
        else:
            raise ExtractorError('Unknown instance type')

        actual_token = self._download_json(
            f'https://{instance}/oauth/token', None, 'Downloading the actual token',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            }, data=bytes(urlencode({
                'client_id': app_info['client_id'],
                'client_secret': app_info['client_secret'],
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'scope': 'read',
                'code': oauth_token,
                'grant_type': 'authorization_code',
            }).encode('utf-8')))
        return {
            'instance': instance,
            'authorization': f"{actual_token['token_type']} {actual_token['access_token']}",
        }

    @staticmethod
    def _is_probe_enabled(ydl):
        return ydl.params.get('check_mastodon_instance', False)

    def _determine_instance_software(self, host, webpage=None):
        if webpage:
            for i, string in enumerate(self._SH_VALID_CONTENT_STRINGS):
                if string in webpage:
                    return self._SH_VALID_CONTENT_SOFTWARES[i]
            if any(s in webpage for s in PeerTubeIE._SH_VALID_CONTENT_STRINGS):
                return 'peertube'

        return self._fetch_nodeinfo_software(self, host)


class MastodonIE(MastodonBaseIE):
    # NOTE: currently, compatible self-hosted products like Gab Social requires probing for each instances.
    IE_NAME = 'mastodon'
    _VALID_URL = r'''(?x)
        (?P<prefix>(?:mastodon|mstdn|mtdn):)?
        (?:
            # URL with or without prefix
            https?://(?P<domain_1>[^/\s]+)/
            (?:
                # mastodon
                @[a-zA-Z0-9_-]+
                |web/statuses
                # gab social
                |[a-zA-Z0-9_-]+/posts
                # mastodon legacy (?)
                |users/[a-zA-Z0-9_-]+/statuses
                # pleroma
                |notice
                # pleroma (OStatus standard?) - https://git.pleroma.social/pleroma/pleroma/-/blob/e9859b68fcb9c38b2ec27a45ffe0921e8d78b5e1/lib/pleroma/web/router.ex#L607
                |objects
                |activities
            )/
        # haruhi-dl compatible: "mastodon:example.com:blablabla"
        |(?P<domain_2>[^:\s]+)(?P<short_form>:))
        (?P<id>[0-9a-zA-Z-]+)
    '''

    @classmethod
    def suitable(cls, url):
        mobj = cls._match_valid_url(url)
        if not mobj:
            return False
        prefix, is_short = mobj.group('prefix', 'short_form')
        if is_short and prefix:
            return True
        return super(MastodonIE, cls).suitable(url)

    _TESTS = [{
        'note': 'embed video without NSFW',
        'url': 'https://mstdn.jp/@nao20010128nao/105395495018076252',
        'info_dict': {
            'id': '105395495018076252',
            'title': 'てすや\nhttps://www.youtube.com/watch?v=jx0fBBkaF1w',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 0,
        },
    }, {
        'note': 'embed video with NSFW',
        'url': 'https://mstdn.jp/@nao20010128nao/105395503690401921',
        'info_dict': {
            'id': '105395503690401921',
            'title': 'Mastodonダウンローダーのテストケース用なので別に注意要素無いよ',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 18,
        },
    }, {
        'note': 'uploader_id not present in URL',
        'url': 'https://mstdn.jp/web/statuses/105395503690401921',
        'info_dict': {
            'id': '105395503690401921',
            'title': 'Mastodonダウンローダーのテストケース用なので別に注意要素無いよ',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 18,
        },
    }, {
        'note': 'has YouTube as card',
        'url': 'https://mstdn.jp/@vaporeon/105389634797745542',
        'add_ie': ['Youtube'],
        'info_dict': {},
    }, {
        'note': 'has radiko as card',
        'url': 'https://mstdn.jp/@vaporeon/105389280534065010',
        'only_matching': True,
    }, {
        'url': 'https://pawoo.net/@iriomote_yamaneko/105370643258491818',
        'only_matching': True,
    }, {
        'note': 'uploader_id has only one character',
        'url': 'https://mstdn.kemono-friends.info/@m/103997543924688111',
        'info_dict': {
            'id': '103997543924688111',
            'uploader_id': 'm',
        },
    }, {
        'note': 'short form, compatible with haruhi-dl\'s usage',
        'url': 'mastodon:mstdn.jp:105395495018076252',
        'info_dict': {
            'id': '105395495018076252',
            'title': 'てすや\nhttps://www.youtube.com/watch?v=jx0fBBkaF1w',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 0,
        },
    }, {
        # mastodon, video description
        'url': 'https://mastodon.technology/@BadAtNames/104254332187004304',
        'info_dict': {
            'id': '104254332187004304',
            'title': 're:.+ - Mfw trump supporters complain about twitter',
            'ext': 'mp4',
        },
    }, {
        # pleroma, multiple videos in single post
        'url': 'https://donotsta.re/notice/9xN1v6yM7WhzE7aIIC',
        'info_dict': {
            'id': '9xN1v6yM7WhzE7aIIC',
            'title': 're:.+ - ',
        },
        'playlist': [{
            'info_dict': {
                'id': '1264363435',
                'title': 'Cherry Gold💭 - French is one interesting language but this is so funny 🤣🤣🤣🤣-1258667021920845824.mp4',
                'ext': 'mp4',
            },
        }, {
            'info_dict': {
                'id': '825092418',
                'title': 'Santi 🇨🇴 - @mhizgoldbedding same guy but i liked this one better-1259242534557167617.mp4',
                'ext': 'mp4',
            },
        }]
    }, {
        # pleroma, with /objects/
        'url': 'https://outerheaven.club/objects/a5046e74-07b4-49a3-9f1c-da11cf97e939',
        'info_dict': {
            'id': 'ADbaHO2V0zmsFFjlTM',
            'title': 'ah yes\nthe legendary stealth tactics of sam fisher',
            'uploader': 'Hans',
            'uploader_id': 'Talloran',
        },
    }, {
        # pleroma, with /objects/
        'url': 'https://stereophonic.space/objects/e0779154-ebbe-4b55-911b-03a03eba7c71',
        'info_dict': {
            'id': 'ADcmeAWAoQlsEg1KFs',
            'title': 'this is the test case for stereophonic.space',
            'uploader': 'lesmi',
            'uploader_id': 'lesmi',
        },
    }, {
        # gab social
        'url': 'https://gab.com/ACT1TV/posts/104450493441154721',
        'info_dict': {
            'id': '104450493441154721',
            'title': 're:.+ - He shoots, he scores and the crowd went wild.... #Animal #Sports',
            'ext': 'mp4',
        },
    }, {
        # Soapbox, audio file
        'url': 'https://gleasonator.com/notice/9zvJY6h7jJzwopKAIi',
        'info_dict': {
            'id': '9zvJY6h7jJzwopKAIi',
            'title': 're:.+ - #FEDIBLOCK',
            'ext': 'oga',
        },
    }, {
        # mastodon, card to youtube
        'url': 'https://mstdn.social/@polamatysiak/106183574509332910',
        'info_dict': {
            'id': 'RWDU0BjcYp0',
            'ext': 'mp4',
            'title': 'polamatysiak - Moje wczorajsze wystąpienie w Sejmie, koniecznie zobaczcie do końca 🙂 \n#pracaposłanki\n\nhttps://youtu.be/RWDU0BjcYp0',
            'description': 'md5:0c16fa11a698d5d1b171963fd6833297',
            'uploader': 'Paulina Matysiak',
            'uploader_id': 'UCLRAd9-Hw6kEI1aPBrSaF9A',
            'upload_date': '20210505',
        },
    }, {
        'url': 'https://gab.com/SomeBitchIKnow/posts/107163961867310434',
        'md5': '8ca34fb00f1e1033b5c5988d79ec531d',
        'info_dict': {
            'id': '107163961867310434',
            'ext': 'mp4',
            'title': 'md5:204055fafd5e1a519f5d6db953567ca3',
            'uploader_id': '946600',
            'uploader': 'SomeBitchIKnow',
            'timestamp': 1635192289,
            'upload_date': '20211025',
        }
    }, {
        'url': 'https://gab.com/TheLonelyProud/posts/107045884469287653',
        'md5': 'f9cefcfdff6418e392611a828d47839d',
        'info_dict': {
            'id': '107045884469287653',
            'ext': 'mp4',
            'uploader_id': '1390705',
            'timestamp': 1633390571,
            'upload_date': '20211004',
            'uploader': 'TheLonelyProud',
        }
    }]

    def _real_extract(self, url):
        webpage = None
        mobj = self._match_valid_url(url)

        video_id = mobj.group('id')
        domain = get_first_group(mobj, 'domain_1', 'domain_2')

        login_info = self._login()
        if login_info and domain != login_info['instance']:
            wf_url = url
            if not url.startswith('http'):
                software = self._determine_instance_software(domain, webpage)
                url_part = None
                if software == 'pleroma':
                    if '-' in video_id:   # UUID
                        url_part = 'objects'
                    else:
                        url_part = 'notice'
                elif software == 'peertube':
                    url_part = 'videos/watch'
                elif software in ('mastodon', 'gab'):
                    # mastodon and gab social require usernames in the url,
                    # but we can't determine the username without fetching the post,
                    # but we can't fetch the post without determining the username...
                    raise ExtractorError(f'Use the full url with --force-use-mastodon to download from {software}', expected=True)
                else:
                    raise ExtractorError(f'Unknown software: {software}')
                wf_url = f'https://{domain}/{url_part}/{video_id}'
            search = self._download_json(
                f"https://{login_info['instance']}/api/v2/search", '%s:%s' % (domain, video_id),
                query={
                    'q': wf_url,
                    'type': 'statuses',
                    'resolve': True,
                }, headers={
                    'Authorization': login_info['authorization'],
                })
            assert len(search['statuses']) == 1
            metadata = search['statuses'][0]
        else:
            if not login_info and any(frag in url for frag in ('/objects/', '/activities/')):
                if not webpage:
                    webpage = self._download_webpage(url, '%s:%s' % (domain, video_id), expected_status=302)
                real_url = self._og_search_property('url', webpage, default=None)
                if real_url:
                    return self.url_result(real_url, ie='Mastodon')
            metadata = self._download_json(
                'https://%s/api/v1/statuses/%s' % (domain, video_id), '%s:%s' % (domain, video_id),
                headers={
                    'Authorization': login_info['authorization'],
                } if login_info else {})

        title = clean_html(metadata.get('content'))

        info_dict = {
            'id': video_id,
            'title': title,

            'duration': metadata.get('duration') or parse_duration(metadata.get('length')),
            'like_count': metadata.get('favourites_count'),
            'comment_count': metadata.get('replies_count'),
            'repost_count': metadata.get('reblogs_count'),

            'uploader': traverse_obj(metadata, ('account', 'display_name')),
            'uploader_id': traverse_obj(metadata, ('account', 'username')),
            'uploader_url': traverse_obj(metadata, ('account', 'url')),
        }

        entries = []
        for media in metadata.get('media_attachments') or ():
            if media['type'] in ('video', 'audio'):
                entries.append({
                    'id': media['id'],
                    'title': str_or_none(media['description']) or title,
                    'url': str_or_none(media['url']),
                    'thumbnail': str_or_none(media['preview_url']) if media['type'] == 'video' else None,
                    'vcodec': 'none' if media['type'] == 'audio' else None,
                    'duration': float_or_none(try_get(media, lambda x: x['meta']['original']['duration'])),
                    'width': int_or_none(try_get(media, lambda x: x['meta']['original']['width'])),
                    'height': int_or_none(try_get(media, lambda x: x['meta']['original']['height'])),
                    'tbr': int_or_none(try_get(media, lambda x: x['meta']['original']['bitrate'])),
                })

        if len(entries) == 0:
            card = metadata.get('card')
            if card:
                return {
                    '_type': 'url_transparent',
                    'url': card['url'],
                    'title': title,
                    'thumbnail': url_or_none(card.get('image')),
                    **info_dict,
                }
            raise ExtractorError('No audio/video attachments')

        if len(entries) == 1:
            del entries[0]['id']
            info_dict.update(entries[0])
        else:
            info_dict.update({
                "_type": "playlist",
                "entries": entries,
            })

        return info_dict


class MastodonUserIE(MastodonBaseIE):
    IE_NAME = 'mastodon:user'
    _VALID_URL = r'(?P<prefix>(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/@(?P<id>[a-zA-Z0-9_-]+)/?(?:\?.*)?$'
    _TESTS = [{
        'url': 'https://pawoo.net/@iriomote_yamaneko',
        'info_dict': {
            'title': 'Toots from @iriomote_yamaneko@pawoo.net',
            'id': 'iriomote_yamaneko',
        },
        'playlist_mincount': 80500,
    }]

    def _entries(self, domain, user_id):
        # FIXME: filter toots with video or youtube attached
        # TODO: replace to api calls if possible
        next_url = 'https://%s/@%s' % (domain, user_id)
        for index in itertools.count(1):
            webpage = self._download_webpage(next_url, user_id, note='Downloading page %d' % index)
            for matches in re.finditer(r'(?x)<a class=(["\'])(?:.*?\s+)*status__relative-time(?:\s+.*)*\1\s+(?:rel=(["\'])noopener\2)?\s+href=(["\'])(https://%s/@%s/(\d+))\3>'
                                       % (re.escape(domain), re.escape(user_id)), webpage):
                _, _, _, url, video_id = matches.groups()
                yield self.url_result(url, id=video_id)
            next_url = self._search_regex(
                # other instances may have different tags
                # r'<div\s+class=(["\'])entry\1>.*?<a\s+class=(["\'])(?:.*\s+)*load-more(?:\s+.*)*\2\s+href=(["\'])(.+)\3>.+</a></div>\s*</div>',
                r'class=\"load-more load-gap\" href=\"([^\"]+)\">.+<\/a><\/div>\s*<\/div>',
                webpage, 'next cursor url', default=None, fatal=False)
            if not next_url:
                break

    def _real_extract(self, url):
        domain, user_id = self._match_valid_url(url).group('domain', 'id')

        entries = self._entries(domain, user_id)
        return self.playlist_result(entries, user_id, 'Toots from @%s@%s' % (user_id, domain))


class MastodonUserNumericIE(MastodonBaseIE):
    IE_NAME = 'mastodon:user:numeric_id'
    _VALID_URL = r'(?P<prefix>(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/web/accounts/(?P<id>\d+)/?'
    _TESTS = [{
        'url': 'https://mstdn.jp/web/accounts/330076',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        prefix, domain, user_id = self._match_valid_url(url).group('prefix', 'domain', 'id')

        if not prefix and not self._test_mastodon_instance(domain):
            return self.url_result(url, ie='Generic')

        api_response = self._download_json('https://%s/api/v1/accounts/%s' % (domain, user_id), user_id)
        username = api_response.get('username')
        return self.url_result('https://%s/@%s' % (domain, username), video_id=username)

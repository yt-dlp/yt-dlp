import json
import re
import urllib.parse

from .common import SelfHostedInfoExtractor
# from .peertube import PeerTubeIE  # TODO
from ..utils import (
    ExtractorError,
    clean_html,
    dict_get,
    float_or_none,
    int_or_none,
    make_archive_id,
    parse_duration,
    parse_qs,
    str_or_none,
    traverse_obj,
    try_get,
    url_or_none,
)


class MastodonBaseIE(SelfHostedInfoExtractor):
    _VALID_URL = r'''(?x)
        (?:
            https?://(?P<domain>[^/\s]+)/(?:
                @[\w-]+|web/statuses  # mastodon
                |[\w-]+/posts  # gab social
                |users/[\w-]+/statuses  # mastodon legacy
                |notice  # pleroma
                |objects|activities  # pleroma (OStatus standard?) - https://git.pleroma.social/pleroma/pleroma/-/blob/e9859b68fcb9c38b2ec27a45ffe0921e8d78b5e1/lib/pleroma/web/router.ex#L607
            )/
            |(?P<domain_2>[^/\s]+)(?P<short_form>:)  # "mastodon:example.com:blablabla"
        )(?P<id>[\w-]+)
    '''

    _NETRC_MACHINE = 'mastodon'
    _KEY = 'mastodon'
    _NODEINFO_SOFTWARES = {k: v for v, k in (
        ('mastodon', ',"settings":{"known_fediverse":'),  # Mastodon initial-state
        ('mastodon', '<li><a href="https://docs.joinmastodon.org/">Documentation</a></li>'),
        ('pleroma', '<title>Pleroma</title>'),
        ('pleroma', '<noscript>To use Pleroma, please enable JavaScript.</noscript>'),
        ('pleroma', '<noscript>To use Soapbox, please enable JavaScript.</noscript>'),
        ('gab', 'Alternatively, try one of the <a href="https://apps.gab.com">native apps</a> for Gab Social for your platform.'),
    )}
    _SH_VALID_CONTENT_REGEXES = (
        # double quotes on Mastodon, single quotes on Gab Social
        r'<script id=[\'"]initial-state[\'"] type=[\'"]application/json[\'"]>{"meta":{"streaming_api_base_url":"wss://',
    )
    _KNOWN_INSTANCES = {
        # DO NOT DELETE THE FOLLOWING TWO
        'gab.com', 'truthsocial.com',

        # Fallback instances  # TODO: Which of these are actually needed?
        'mstdn.jp', 'pawoo.net', 'mstdn.kemono-friends.info',
        'mastodon.technology', 'donotsta.re', 'outerheaven.club',
        'stereophonic.space', 'mstdn.social',
        # 'gleasonator.com',
    }
    _login_info = {}

    def _determine_instance_software(self, host, webpage=None):
        if webpage:
            for string, hostname in self._NODEINFO_SOFTWARES.items():
                if string in webpage:
                    return hostname
            # if any(s in webpage for s in PeerTubeIE._SH_VALID_CONTENT_STRINGS):
            #     return 'peertube'

        return self._fetch_nodeinfo_software(host)

    def _perform_login(self, username, password):
        mobj = re.fullmatch(r'(?P<username>.+?)@(?P<instance>[^@]+)', username)
        if not mobj:
            raise ExtractorError(
                'Invalid login format - must be in format [username or email]@[instance]', expected=True)
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

        # this needs to be codebase-specific, as the HTML page differs between codebases
        if 'xlink:href="#mastodon-svg-logo-full"' in login_webpage:  # mastodon
            if '@' not in username:
                raise ExtractorError('Invalid login format: for Mastodon instances, e-mail is required', expected=True)

            login_form = self._hidden_inputs(login_webpage)
            login_form['user[email]'] = username
            login_form['user[password]'] = password
            login_req, urlh = self._download_webpage_handle(
                f'https://{instance}/auth/sign_in', None, 'Sending login details',
                headers={
                    'Content-Type': 'application/x-www-form-urllib.parse.urlencoded',
                }, data=bytes(urllib.parse.urlencode(login_form).encode('utf-8')))

            if '/oauth/authorize/native' in urlh.url:  # cached apps may already be authorized
                oauth_token = parse_qs(urllib.parse(urlh.url).query)['code'][0]
            else:
                auth_form = self._hidden_inputs(
                    self._search_regex(
                        r'(?s)(<form\b[^>]+>.+?>Authorize</.+?</form>)',
                        login_req, 'authorization form'))
                urlh = self._request_webpage(
                    f'https://{instance}/oauth/authorize', None, 'Confirming authorization',
                    headers={
                        'Content-Type': 'application/x-www-form-urllib.parse.urlencoded',
                    }, data=bytes(urllib.parse.urlencode(auth_form).encode('utf-8')))
                oauth_token = parse_qs(urllib.parse(urlh.url).query)['code'][0]

        elif 'content: "✔\\fe0e";' in login_webpage:  # pleroma
            login_form = self._hidden_inputs(login_webpage)
            login_form['authorization[scope][]'] = 'read'
            login_form['authorization[name]'] = username
            login_form['authorization[password]'] = password
            login_req = self._download_webpage(
                f'https://{instance}/oauth/authorize', None, 'Sending login details',
                headers={
                    'Content-Type': 'application/x-www-form-urllib.parse.urlencoded',
                }, data=bytes(urllib.parse.urlencode(login_form).encode('utf-8')))
            # TODO: 2FA, error handling
            oauth_token = self._search_regex(
                r'<h2>\s*Token code is\s*<br>\s*([a-zA-Z\d_-]+)\s*</h2>',
                login_req, 'oauth token')

        else:
            raise ExtractorError('Unknown instance type')

        actual_token = self._download_json(
            f'https://{instance}/oauth/token', None, 'Downloading the actual token',
            headers={
                'Content-Type': 'application/x-www-form-urllib.parse.urlencoded',
            }, data=bytes(urllib.parse.urlencode({
                'client_id': app_info['client_id'],
                'client_secret': app_info['client_secret'],
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'scope': 'read',
                'code': oauth_token,
                'grant_type': 'authorization_code',
            }).encode('utf-8')))
        MastodonBaseIE._login_info = {
            'instance': instance,
            'authorization': f"{actual_token['token_type']} {actual_token['access_token']}",
        }

    def _real_extract(self, url):
        video_id, domain = self._match_id(url), self._match_hostname(url)
        display_id = self._make_video_id(video_id, domain)

        if domain == self._login_info.get('instance', domain):
            if not self._login_info and any(frag in url for frag in ('/objects/', '/activities/')):
                webpage = self._download_webpage(url, display_id, expected_status=302)
                real_url = self._og_search_property('url', webpage, default=None)
                if real_url:
                    return self.url_result(f'{self._KEY}:{real_url}', MastodonIE)

            metadata = self._download_json(
                f'https://{domain}/api/v1/statuses/{video_id}', display_id,
                headers={
                    'Authorization': self._login_info['authorization'],
                } if self._login_info else {})

        else:
            if not url.startswith('http'):
                software = self._determine_instance_software(domain, None)
                if software == 'pleroma':
                    url_part = 'objects' if '-' in video_id else 'notice'
                elif software == 'peertube':
                    url_part = 'videos/watch'
                elif software in ('mastodon', 'gab'):
                    raise ExtractorError(f'Use the full url to download from {software}', expected=True)
                else:
                    raise ExtractorError(f'Unknown software: {software}')
                url = f'https://{domain}/{url_part}/{video_id}'

            search = self._download_json(
                f'https://{self._login_info["instance"]}/api/v2/search', display_id,
                query={
                    'q': url,
                    'type': 'statuses',
                    'resolve': True,
                }, headers={
                    'Authorization': self._login_info['authorization'],
                })
            assert len(search['statuses']) == 1
            metadata = search['statuses'][0]

        title = clean_html(metadata.get('content'))
        info_dict = {
            'id': display_id,
            'title': title,
            'duration': metadata.get('duration') or parse_duration(metadata.get('length')),
            'like_count': metadata.get('favourites_count'),
            'comment_count': metadata.get('replies_count'),
            'repost_count': metadata.get('reblogs_count'),
            'uploader': traverse_obj(metadata, ('account', 'display_name')),
            'uploader_id': traverse_obj(metadata, ('account', 'username')),
            'uploader_url': traverse_obj(metadata, ('account', 'url')),
        }

        if domain == 'gab.com':
            info_dict['_old_archive_ids'] = [make_archive_id('Gab', video_id)]
        elif domain == 'truthsocial.com':
            info_dict['_old_archive_ids'] = [make_archive_id('Truth', video_id)]

        entries = [{
            'id': self._make_video_id(media['id'], domain),
            'title': str_or_none(media['description']) or title,
            'url': str_or_none(dict_get(media, ('url', 'source_mp4'))),
            'thumbnail': str_or_none(media['preview_url']) if media['type'] == 'video' else None,
            'vcodec': 'none' if media['type'] == 'audio' else None,
            'duration': float_or_none(try_get(media, lambda x: x['meta']['original']['duration'])),
            'width': int_or_none(try_get(media, lambda x: x['meta']['original']['width'])),
            'height': int_or_none(try_get(media, lambda x: x['meta']['original']['height'])),
            'tbr': int_or_none(try_get(media, lambda x: x['meta']['original']['bitrate'])),
        } for media in metadata.get('media_attachments') or [] if media.get('type') in ('video', 'audio')]

        if not entries:
            card = metadata.get('card')
            if not card:
                raise ExtractorError('No audio/video attachments', expected=True)
            return {
                '_type': 'url_transparent',  # TODO: Sure it should be transparent?
                'url': card['url'],
                'title': title,
                'thumbnail': url_or_none(card.get('image')),
                **info_dict,
            }

        if len(entries) == 1:
            del entries[0]['id']
            info_dict.update(entries[0])
        else:
            info_dict.update({
                '_type': 'playlist',
                'entries': entries,
            })

        return info_dict


class MastodonIE(MastodonBaseIE):
    _TESTS = [{
        # TODO: Add md5s
        'note': 'embed video without NSFW',
        'url': 'https://mstdn.jp/@nao20010128nao/105395495018076252',
        'info_dict': {
            'id': '105395495018076252@mstdn.jp',
            'ext': 'mp4',
            'like_count': int,
            'comment_count': int,
            'uploader': 'Lesmiscore',
            'repost_count': int,
            'uploader_id': 'nao20010128nao',
            'title': 'てすや\nhttps://www.youtube.com/watch?v=jx0fBBkaF1w',
            'uploader_url': 'https://mstdn.jp/@nao20010128nao',
            'thumbnail': 'https://media.mstdn.jp/media_attachments/files/033/830/003/small/e8429d6ee1013c3e.png',
            'duration': 131.598,
        },
    }, {
        'note': 'embed video with NSFW',
        'url': 'https://mstdn.jp/@nao20010128nao/105395503690401921',
        'info_dict': {
            'id': '105395503690401921@mstdn.jp',
            'ext': 'mp4',
            'comment_count': int,
            'uploader_id': 'nao20010128nao',
            'uploader_url': 'https://mstdn.jp/@nao20010128nao',
            'like_count': int,
            'repost_count': int,
            'thumbnail': 'https://media.mstdn.jp/media_attachments/files/033/830/052/small/3c6bdd3e3aa4ed65.png',
            'uploader': 'Lesmiscore',
            'duration': 131.598,
            'title': 'Mastodonダウンローダーのテストケース用なので別に注意要素無いよ',
            'age_limit': 18,  # TODO
        },
    }, {
        'note': 'uploader_id not present in URL',
        'url': 'https://mstdn.jp/web/statuses/105395503690401921',
        'info_dict': {
            'id': '105395503690401921@mstdn.jp',
            'ext': 'mp4',
            'comment_count': int,
            'uploader_id': 'nao20010128nao',
            'uploader_url': 'https://mstdn.jp/@nao20010128nao',
            'like_count': int,
            'repost_count': int,
            'thumbnail': 'https://media.mstdn.jp/media_attachments/files/033/830/052/small/3c6bdd3e3aa4ed65.png',
            'uploader': 'Lesmiscore',
            'duration': 131.598,
            'title': 'Mastodonダウンローダーのテストケース用なので別に注意要素無いよ',
            'age_limit': 18,
        },
    }, {
        'note': 'has YouTube as card',
        'url': 'https://mstdn.jp/@vaporeon/105389634797745542',
        'add_ie': ['Youtube'],
        'info_dict': {
            'id': 'lMi261UCA_U',
            'ext': 'mp4',
            'duration': 11154,
            'playable_in_embed': True,
            'uploader_id': 'vaporeon',
            'availability': 'public',
            'categories': ['Gaming'],
            'release_date': '20201216',
            'uploader_url': 'https://mstdn.jp/@vaporeon',
            'tags': ['MOTTY', 'ゲーム実況', '生放送', 'スーパーマリオ64', 'マリオ64', '120枚RTA', 'スーパーマリオ3Dコレクション', 'ニンテンドースイッチ'],
            'view_count': int,
            'comment_count': int,
            'age_limit': 0,
            'uploader': 'シャワーズ＠ mstdn',
            'thumbnail': 'https://i.ytimg.com/vi/lMi261UCA_U/maxresdefault.jpg',
            'description': 'md5:32ee1ffa017c9de9cb1b53b659513e74',
            'channel_id': 'UCPfJisP85wKhzK9Lv3pQLRg',
            'channel': 'MOTTV - MOTTYのゲーム実況ちゃんねる！',
            'live_status': 'was_live',
            'like_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCPfJisP85wKhzK9Lv3pQLRg',
            'release_timestamp': 1608118219,
            'channel_follower_count': int,
            'title': 'md5:93ea3384b48def4e6e4084ec28d5862a',
            'upload_date': '20201216',
            'repost_count': int,
        },
    }, {
        'note': 'has radiko as card',
        'url': 'https://mstdn.jp/@vaporeon/105389280534065010',
        'only_matching': True,
    }, {
        'url': 'https://pawoo.net/@iriomote_yamaneko/105370643258491818',
        'only_matching': True,
    }, {  # FIXME
        'note': 'uploader_id has only one character',
        'url': 'https://mstdn.kemono-friends.info/@m/103997543924688111',
        'info_dict': {
            'id': '103997543924688111',
            'ext': 'mp4',
            'uploader_id': 'm',
        },
    }, {
        'note': 'short form, compatible with haruhi-dl\'s usage',
        'url': 'mastodon:mstdn.jp:105395495018076252',
        'info_dict': {
            'id': '105395495018076252@mstdn.jp',
            'ext': 'mp4',
            'uploader_id': 'nao20010128nao',
            'like_count': int,
            'comment_count': int,
            'duration': 131.598,
            'thumbnail': 'https://media.mstdn.jp/media_attachments/files/033/830/003/small/e8429d6ee1013c3e.png',
            'title': 'てすや\nhttps://www.youtube.com/watch?v=jx0fBBkaF1w',
            'uploader': 'Lesmiscore',
            'uploader_url': 'https://mstdn.jp/@nao20010128nao',
            'repost_count': int,
        },
    }, {
        # mastodon, video description
        'url': 'https://mastodon.technology/@BadAtNames/104254332187004304',
        'info_dict': {
            'id': '104254332187004304@mastodon.technology',
            'ext': 'mp4',
            'comment_count': int,
            'repost_count': int,
            'uploader_id': 'BadAtNames',
            'title': 'md5:53f4428d4dc7e25a8255cf2a08488f2e',
            'like_count': int,
            'thumbnail': 'https://cdn.mastodon.technology/media_attachments/files/006/823/243/small/34571725c91899c8.png',
            'uploader': '#1 inpost stan',
            'duration': 12.72,
            'uploader_url': 'https://mastodon.technology/@BadAtNames',
        },
    }, {
        # pleroma, multiple videos in single post
        'url': 'https://donotsta.re/notice/9xN1v6yM7WhzE7aIIC',
        'info_dict': {
            'id': '9xN1v6yM7WhzE7aIIC@donotsta.re',
            'uploader_url': 'https://donotsta.re/users/selfisekai',
            'repost_count': int,
            'title': '',  # FIXME
            'uploader_id': 'selfisekai',
            'comment_count': int,
            'uploader': 'lauren',
            'like_count': int,
        },
        'playlist': [{
            'info_dict': {
                'id': '1264363435@donotsta.re',
                'ext': 'mp4',
                'title': 'Cherry Gold💭 - French is one interesting language but this is so funny 🤣🤣🤣🤣-1258667021920845824.mp4',
                'thumbnail': 'https://donotsta.re/media/888cc71a35dd91acb14d2e180d818c94c34a114d1c9a1f9ebf1365484022a40e.mp4',
            },
        }, {
            'info_dict': {
                'id': '825092418@donotsta.re',
                'ext': 'mp4',
                'title': 'Santi 🇨🇴 - @mhizgoldbedding same guy but i liked this one better-1259242534557167617.mp4',
                'thumbnail': 'https://donotsta.re/media/4cf3beffd7836b336ab986952c69c2016d0352d50245a2bf1f844efeba194aab.mp4',
            },
        }]
    }, {
        # pleroma, with /objects/
        'url': 'https://outerheaven.club/objects/a5046e74-07b4-49a3-9f1c-da11cf97e939',
        'info_dict': {
            'id': 'ADbaHO2V0zmsFFjlTM@outerheaven.club',
            'ext': 'mp4',
            'uploader': 'Talloran',
            'comment_count': int,
            'title': 'ah yes\nthe legendary stealth tactics of sam fisher',
            'repost_count': int,
            'like_count': int,
            'uploader_id': 'Talloran',
            'thumbnail': 'https://outerheaven.club/media/e478abfb-8dc2-4249-bd0e-81bee9b008b1/Husky_1637445043856_JS39YH64JB.mp4',
            'uploader_url': 'https://outerheaven.club/users/Talloran',
        },
    }, {
        # gab social
        'url': 'https://gab.com/ACT1TV/posts/104450493441154721',  # FIXME: 404
        'info_dict': {
            'id': '104450493441154721@gab.com',
            'ext': 'mp4',
        },
    }, {
        # mastodon, card to youtube
        'url': 'https://mstdn.social/@polamatysiak/106183574509332910',
        'info_dict': {
            'id': 'RWDU0BjcYp0',
            'ext': 'mp4',
            'playable_in_embed': True,
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCLRAd9-Hw6kEI1aPBrSaF9A',
            'channel': 'Paulina Matysiak',
            'categories': ['News & Politics'],
            'live_status': 'not_live',
            'comment_count': int,
            'age_limit': 0,
            'duration': 87,
            'uploader_url': 'https://mstdn.social/@polamatysiak',  # FIXME: L241
            'like_count': int,
            'uploader': 'polamatysiak',
            'availability': 'public',
            'title': 'md5:353abeccefc902473630a9cbc34ce77a',
            'repost_count': int,
            'thumbnail': 'https://i.ytimg.com/vi_webp/RWDU0BjcYp0/maxresdefault.webp',
            'description': 'md5:0c16fa11a698d5d1b171963fd6833297',
            'upload_date': '20210505',
            'channel_id': 'UCLRAd9-Hw6kEI1aPBrSaF9A',
            'uploader_id': 'polamatysiak',
            'tags': ['fundusz odbudowy', 'sejm', 'posłanka', 'praca posłanki', 'matysiak w sejmie', 'partia razem'],
            'location': 'SEJM RZECZYPOSPOLITEJ POLSKIEJ',
            'channel_follower_count': int,
        },
    }, {
        'url': 'https://gab.com/SomeBitchIKnow/posts/107163961867310434',
        'md5': '8ca34fb00f1e1033b5c5988d79ec531d',
        'info_dict': {
            'id': '107163961867310434@gab.com',
            'ext': 'mp4',
            'comment_count': int,
            'repost_count': int,
            'title': 'md5:204055fafd5e1a519f5d6db953567ca3',
            'uploader_id': 'SomeBitchIKnow',
            'duration': 104.213333,
            'uploader_url': 'https://gab.com/SomeBitchIKnow',
            'like_count': int,
            'uploader': 'L',
            'thumbnail': 'https://media.gab.com/system/media_attachments/files/088/718/344/small/fded4ef06989f1bb.png',
        }
    }, {  # FIXME
        'url': 'https://gab.com/TheLonelyProud/posts/107045884469287653',
        'md5': 'f9cefcfdff6418e392611a828d47839d',
        'info_dict': {
            'id': '107045884469287653@gab.com',
            'ext': 'mp4',
        }
    }]


class MastodonInstancesIE(MastodonBaseIE):
    _BASE_IE = MastodonIE
    _WEBPAGE_TESTS = [{
        # Soapbox, audio file
        'url': 'https://gleasonator.com/notice/9zvJY6h7jJzwopKAIi',  #
        'info_dict': {
            'id': '9zvJY6h7jJzwopKAIi@gleasonator.com',
            'title': '#FEDIBLOCK',
            'ext': 'oga',
            'comment_count': int,
            'repost_count': int,
            'uploader_url': 'https://gleasonator.com/users/alex',
            'uploader': 'Alex Gleason',
            'uploader_id': 'alex',
            'like_count': int,
        },
        'params': {'allowed_extractors': ['mastodon:instances', 'default']},  # FIXME: Should be automatic
    }]

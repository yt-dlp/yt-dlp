# coding: utf-8
from __future__ import unicode_literals

import json
import re
import socket

from .common import InfoExtractor
from ..compat import (
    compat_etree_fromstring,
    compat_http_client,
    compat_str,
    compat_urllib_error,
    compat_urllib_parse_unquote,
    compat_urllib_parse_unquote_plus,
)
from ..utils import (
    clean_html,
    error_to_compat_str,
    ExtractorError,
    float_or_none,
    get_element_by_id,
    int_or_none,
    js_to_json,
    limit_length,
    parse_count,
    qualities,
    sanitized_Request,
    try_get,
    urlencode_postdata,
    urljoin,
)


class FacebookIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                (?:
                    https?://
                        (?:[\w-]+\.)?(?:facebook\.com|facebookcorewwwi\.onion)/
                        (?:[^#]*?\#!/)?
                        (?:
                            (?:
                                video/video\.php|
                                photo\.php|
                                video\.php|
                                video/embed|
                                story\.php|
                                watch(?:/live)?/?
                            )\?(?:.*?)(?:v|video_id|story_fbid)=|
                            [^/]+/videos/(?:[^/]+/)?|
                            [^/]+/posts/|
                            groups/[^/]+/permalink/|
                            watchparty/
                        )|
                    facebook:
                )
                (?P<id>[0-9]+)
                '''
    _LOGIN_URL = 'https://www.facebook.com/login.php?next=http%3A%2F%2Ffacebook.com%2Fhome.php&login_attempt=1'
    _CHECKPOINT_URL = 'https://www.facebook.com/checkpoint/?next=http%3A%2F%2Ffacebook.com%2Fhome.php&_fb_noscript=1'
    _NETRC_MACHINE = 'facebook'
    IE_NAME = 'facebook'

    _VIDEO_PAGE_TEMPLATE = 'https://www.facebook.com/video/video.php?v=%s'
    _VIDEO_PAGE_TAHOE_TEMPLATE = 'https://www.facebook.com/video/tahoe/async/%s/?chain=true&isvideo=true&payloadtype=primary'

    _TESTS = [{
        'url': 'https://www.facebook.com/video.php?v=637842556329505&fref=nf',
        'md5': '6a40d33c0eccbb1af76cf0485a052659',
        'info_dict': {
            'id': '637842556329505',
            'ext': 'mp4',
            'title': 're:Did you know Kei Nishikori is the first Asian man to ever reach a Grand Slam',
            'uploader': 'Tennis on Facebook',
            'upload_date': '20140908',
            'timestamp': 1410199200,
        },
        'skip': 'Requires logging in',
    }, {
        # data.video
        'url': 'https://www.facebook.com/video.php?v=274175099429670',
        'info_dict': {
            'id': '274175099429670',
            'ext': 'mp4',
            'title': 're:^Asif Nawab Butt posted a video',
            'uploader': 'Asif Nawab Butt',
            'upload_date': '20140506',
            'timestamp': 1399398998,
            'thumbnail': r're:^https?://.*',
        },
        'expected_warnings': [
            'title'
        ]
    }, {
        'note': 'Video with DASH manifest',
        'url': 'https://www.facebook.com/video.php?v=957955867617029',
        'md5': 'b2c28d528273b323abe5c6ab59f0f030',
        'info_dict': {
            'id': '957955867617029',
            'ext': 'mp4',
            'title': 'When you post epic content on instagram.com/433 8 million followers, this is ...',
            'uploader': 'Demy de Zeeuw',
            'upload_date': '20160110',
            'timestamp': 1452431627,
        },
        'skip': 'Requires logging in',
    }, {
        'url': 'https://www.facebook.com/maxlayn/posts/10153807558977570',
        'md5': '037b1fa7f3c2d02b7a0d7bc16031ecc6',
        'info_dict': {
            'id': '544765982287235',
            'ext': 'mp4',
            'title': '"What are you doing running in the snow?"',
            'uploader': 'FailArmy',
        },
        'skip': 'Video gone',
    }, {
        'url': 'https://m.facebook.com/story.php?story_fbid=1035862816472149&id=116132035111903',
        'md5': '1deb90b6ac27f7efcf6d747c8a27f5e3',
        'info_dict': {
            'id': '1035862816472149',
            'ext': 'mp4',
            'title': 'What the Flock Is Going On In New Zealand  Credit: ViralHog',
            'uploader': 'S. Saint',
        },
        'skip': 'Video gone',
    }, {
        'note': 'swf params escaped',
        'url': 'https://www.facebook.com/barackobama/posts/10153664894881749',
        'md5': '97ba073838964d12c70566e0085c2b91',
        'info_dict': {
            'id': '10153664894881749',
            'ext': 'mp4',
            'title': 'Average time to confirm recent Supreme Court nominees: 67 days Longest it\'s t...',
            'thumbnail': r're:^https?://.*',
            'timestamp': 1456259628,
            'upload_date': '20160223',
            'uploader': 'Barack Obama',
        },
    }, {
        # have 1080P, but only up to 720p in swf params
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/cnn/videos/10155529876156509/',
        'md5': '9571fae53d4165bbbadb17a94651dcdc',
        'info_dict': {
            'id': '10155529876156509',
            'ext': 'mp4',
            'title': 'She survived the holocaust — and years later, she’s getting her citizenship s...',
            'timestamp': 1477818095,
            'upload_date': '20161030',
            'uploader': 'CNN',
            'thumbnail': r're:^https?://.*',
            'view_count': int,
        },
    }, {
        # bigPipe.onPageletArrive ... onPageletArrive pagelet_group_mall
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.media
        'url': 'https://www.facebook.com/yaroslav.korpan/videos/1417995061575415/',
        'info_dict': {
            'id': '1417995061575415',
            'ext': 'mp4',
            'title': 'md5:1db063d6a8c13faa8da727817339c857',
            'timestamp': 1486648217,
            'upload_date': '20170209',
            'uploader': 'Yaroslav Korpan',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.facebook.com/LaGuiaDelVaron/posts/1072691702860471',
        'info_dict': {
            'id': '1072691702860471',
            'ext': 'mp4',
            'title': 'md5:ae2d22a93fbb12dad20dc393a869739d',
            'timestamp': 1477305000,
            'upload_date': '20161024',
            'uploader': 'La Guía Del Varón',
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.media
        'url': 'https://www.facebook.com/groups/1024490957622648/permalink/1396382447100162/',
        'info_dict': {
            'id': '1396382447100162',
            'ext': 'mp4',
            'title': 'md5:19a428bbde91364e3de815383b54a235',
            'timestamp': 1486035494,
            'upload_date': '20170202',
            'uploader': 'Elisabeth Ahtn',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.facebook.com/video.php?v=10204634152394104',
        'only_matching': True,
    }, {
        'url': 'https://www.facebook.com/amogood/videos/1618742068337349/?fref=nf',
        'only_matching': True,
    }, {
        # data.mediaset.currMedia.edges
        'url': 'https://www.facebook.com/ChristyClarkForBC/videos/vb.22819070941/10153870694020942/?type=2&theater',
        'only_matching': True,
    }, {
        # data.video.story.attachments[].media
        'url': 'facebook:544765982287235',
        'only_matching': True,
    }, {
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.media
        'url': 'https://www.facebook.com/groups/164828000315060/permalink/764967300301124/',
        'only_matching': True,
    }, {
        # data.video.creation_story.attachments[].media
        'url': 'https://zh-hk.facebook.com/peoplespower/videos/1135894589806027/',
        'only_matching': True,
    }, {
        # data.video
        'url': 'https://www.facebookcorewwwi.onion/video.php?v=274175099429670',
        'only_matching': True,
    }, {
        # no title
        'url': 'https://www.facebook.com/onlycleverentertainment/videos/1947995502095005/',
        'only_matching': True,
    }, {
        # data.video
        'url': 'https://www.facebook.com/WatchESLOne/videos/359649331226507/',
        'info_dict': {
            'id': '359649331226507',
            'ext': 'mp4',
            'title': '#ESLOne VoD - Birmingham Finals Day#1 Fnatic vs. @Evil Geniuses',
            'uploader': 'ESL One Dota 2',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.all_subattachments.nodes[].media
        'url': 'https://www.facebook.com/100033620354545/videos/106560053808006/',
        'info_dict': {
            'id': '106560053808006',
        },
        'playlist_count': 2,
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/watch/?v=647537299265662',
        'only_matching': True,
    }, {
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.all_subattachments.nodes[].media
        'url': 'https://www.facebook.com/PankajShahLondon/posts/10157667649866271',
        'info_dict': {
            'id': '10157667649866271',
        },
        'playlist_count': 3,
    }, {
        # data.nodes[].comet_sections.content.story.attachments[].style_type_renderer.attachment.media
        'url': 'https://m.facebook.com/Alliance.Police.Department/posts/4048563708499330',
        'info_dict': {
            'id': '117576630041613',
            'ext': 'mp4',
            # TODO: title can be extracted from video page
            'title': 'Facebook video #117576630041613',
            'uploader_id': '189393014416438',
            'upload_date': '20201123',
            'timestamp': 1606162592,
        },
        'skip': 'Requires logging in',
    }, {
        # node.comet_sections.content.story.attached_story.attachments.style_type_renderer.attachment.media
        'url': 'https://www.facebook.com/groups/ateistiskselskab/permalink/10154930137678856/',
        'info_dict': {
            'id': '211567722618337',
            'ext': 'mp4',
            'title': 'Facebook video #211567722618337',
            'uploader_id': '127875227654254',
            'upload_date': '20161122',
            'timestamp': 1479793574,
        },
    }, {
        # data.video.creation_story.attachments[].media
        'url': 'https://www.facebook.com/watch/live/?v=1823658634322275',
        'only_matching': True,
    }, {
        'url': 'https://www.facebook.com/watchparty/211641140192478',
        'info_dict': {
            'id': '211641140192478',
        },
        'playlist_count': 1,
        'skip': 'Requires logging in',
    }]
    _SUPPORTED_PAGLETS_REGEX = r'(?:pagelet_group_mall|permalink_video_pagelet|hyperfeed_story_id_[0-9a-f]+)'
    _api_config = {
        'graphURI': '/api/graphql/'
    }

    @staticmethod
    def _extract_urls(webpage):
        urls = []
        for mobj in re.finditer(
                r'<iframe[^>]+?src=(["\'])(?P<url>https?://www\.facebook\.com/(?:video/embed|plugins/video\.php).+?)\1',
                webpage):
            urls.append(mobj.group('url'))
        # Facebook API embed
        # see https://developers.facebook.com/docs/plugins/embedded-video-player
        for mobj in re.finditer(r'''(?x)<div[^>]+
                class=(?P<q1>[\'"])[^\'"]*\bfb-(?:video|post)\b[^\'"]*(?P=q1)[^>]+
                data-href=(?P<q2>[\'"])(?P<url>(?:https?:)?//(?:www\.)?facebook.com/.+?)(?P=q2)''', webpage):
            urls.append(mobj.group('url'))
        return urls

    def _login(self):
        useremail, password = self._get_login_info()
        if useremail is None:
            return

        login_page_req = sanitized_Request(self._LOGIN_URL)
        self._set_cookie('facebook.com', 'locale', 'en_US')
        login_page = self._download_webpage(login_page_req, None,
                                            note='Downloading login page',
                                            errnote='Unable to download login page')
        lsd = self._search_regex(
            r'<input type="hidden" name="lsd" value="([^"]*)"',
            login_page, 'lsd')
        lgnrnd = self._search_regex(r'name="lgnrnd" value="([^"]*?)"', login_page, 'lgnrnd')

        login_form = {
            'email': useremail,
            'pass': password,
            'lsd': lsd,
            'lgnrnd': lgnrnd,
            'next': 'http://facebook.com/home.php',
            'default_persistent': '0',
            'legacy_return': '1',
            'timezone': '-60',
            'trynum': '1',
        }
        request = sanitized_Request(self._LOGIN_URL, urlencode_postdata(login_form))
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        try:
            login_results = self._download_webpage(request, None,
                                                   note='Logging in', errnote='unable to fetch login page')
            if re.search(r'<form(.*)name="login"(.*)</form>', login_results) is not None:
                error = self._html_search_regex(
                    r'(?s)<div[^>]+class=(["\']).*?login_error_box.*?\1[^>]*><div[^>]*>.*?</div><div[^>]*>(?P<error>.+?)</div>',
                    login_results, 'login error', default=None, group='error')
                if error:
                    raise ExtractorError('Unable to login: %s' % error, expected=True)
                self._downloader.report_warning('unable to log in: bad username/password, or exceeded login rate limit (~3/min). Check credentials or wait.')
                return

            fb_dtsg = self._search_regex(
                r'name="fb_dtsg" value="(.+?)"', login_results, 'fb_dtsg', default=None)
            h = self._search_regex(
                r'name="h"\s+(?:\w+="[^"]+"\s+)*?value="([^"]+)"', login_results, 'h', default=None)

            if not fb_dtsg or not h:
                return

            check_form = {
                'fb_dtsg': fb_dtsg,
                'h': h,
                'name_action_selected': 'dont_save',
            }
            check_req = sanitized_Request(self._CHECKPOINT_URL, urlencode_postdata(check_form))
            check_req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            check_response = self._download_webpage(check_req, None,
                                                    note='Confirming login')
            if re.search(r'id="checkpointSubmitButton"', check_response) is not None:
                self._downloader.report_warning('Unable to confirm login, you have to login in your browser and authorize the login.')
        except (compat_urllib_error.URLError, compat_http_client.HTTPException, socket.error) as err:
            self._downloader.report_warning('unable to log in: %s' % error_to_compat_str(err))
            return

    def _real_initialize(self):
        self._login()

    def _extract_from_url(self, url, video_id):
        webpage = self._download_webpage(
            url.replace('://m.facebook.com/', '://www.facebook.com/'), video_id)

        video_data = None

        def extract_video_data(instances):
            video_data = []
            for item in instances:
                if try_get(item, lambda x: x[1][0]) == 'VideoConfig':
                    video_item = item[2][0]
                    if video_item.get('video_id'):
                        video_data.append(video_item['videoData'])
            return video_data

        server_js_data = self._parse_json(self._search_regex(
            [r'handleServerJS\(({.+})(?:\);|,")', r'\bs\.handle\(({.+?})\);'],
            webpage, 'server js data', default='{}'), video_id, fatal=False)

        if server_js_data:
            video_data = extract_video_data(server_js_data.get('instances', []))

        def extract_from_jsmods_instances(js_data):
            if js_data:
                return extract_video_data(try_get(
                    js_data, lambda x: x['jsmods']['instances'], list) or [])

        def extract_dash_manifest(video, formats):
            dash_manifest = video.get('dash_manifest')
            if dash_manifest:
                formats.extend(self._parse_mpd_formats(
                    compat_etree_fromstring(compat_urllib_parse_unquote_plus(dash_manifest))))

        def process_formats(formats):
            # Downloads with browser's User-Agent are rate limited. Working around
            # with non-browser User-Agent.
            for f in formats:
                f.setdefault('http_headers', {})['User-Agent'] = 'facebookexternalhit/1.1'

            self._sort_formats(formats)

        def extract_relay_data(_filter):
            return self._parse_json(self._search_regex(
                r'handleWithCustomApplyEach\([^,]+,\s*({.*?%s.*?})\);' % _filter,
                webpage, 'replay data', default='{}'), video_id, fatal=False) or {}

        def extract_relay_prefetched_data(_filter):
            replay_data = extract_relay_data(_filter)
            for require in (replay_data.get('require') or []):
                if require[0] == 'RelayPrefetchedStreamCache':
                    return try_get(require, lambda x: x[3][1]['__bbox']['result']['data'], dict) or {}

        if not video_data:
            server_js_data = self._parse_json(self._search_regex([
                r'bigPipe\.onPageletArrive\(({.+?})\)\s*;\s*}\s*\)\s*,\s*["\']onPageletArrive\s+' + self._SUPPORTED_PAGLETS_REGEX,
                r'bigPipe\.onPageletArrive\(({.*?id\s*:\s*"%s".*?})\);' % self._SUPPORTED_PAGLETS_REGEX
            ], webpage, 'js data', default='{}'), video_id, js_to_json, False)
            video_data = extract_from_jsmods_instances(server_js_data)

        if not video_data:
            data = extract_relay_prefetched_data(
                r'"(?:dash_manifest|playable_url(?:_quality_hd)?)"\s*:\s*"[^"]+"')
            if data:
                entries = []

                def parse_graphql_video(video):
                    formats = []
                    q = qualities(['sd', 'hd'])
                    for (suffix, format_id) in [('', 'sd'), ('_quality_hd', 'hd')]:
                        playable_url = video.get('playable_url' + suffix)
                        if not playable_url:
                            continue
                        formats.append({
                            'format_id': format_id,
                            'quality': q(format_id),
                            'url': playable_url,
                        })
                    extract_dash_manifest(video, formats)
                    process_formats(formats)
                    v_id = video.get('videoId') or video.get('id') or video_id
                    info = {
                        'id': v_id,
                        'formats': formats,
                        'thumbnail': try_get(video, lambda x: x['thumbnailImage']['uri']),
                        'uploader_id': try_get(video, lambda x: x['owner']['id']),
                        'timestamp': int_or_none(video.get('publish_time')),
                        'duration': float_or_none(video.get('playable_duration_in_ms'), 1000),
                    }
                    description = try_get(video, lambda x: x['savable_description']['text'])
                    title = video.get('name')
                    if title:
                        info.update({
                            'title': title,
                            'description': description,
                        })
                    else:
                        info['title'] = description or 'Facebook video #%s' % v_id
                    entries.append(info)

                def parse_attachment(attachment, key='media'):
                    media = attachment.get(key) or {}
                    if media.get('__typename') == 'Video':
                        return parse_graphql_video(media)

                nodes = data.get('nodes') or []
                node = data.get('node') or {}
                if not nodes and node:
                    nodes.append(node)
                for node in nodes:
                    story = try_get(node, lambda x: x['comet_sections']['content']['story'], dict) or {}
                    attachments = try_get(story, [
                        lambda x: x['attached_story']['attachments'],
                        lambda x: x['attachments']
                    ], list) or []
                    for attachment in attachments:
                        attachment = try_get(attachment, lambda x: x['style_type_renderer']['attachment'], dict)
                        ns = try_get(attachment, lambda x: x['all_subattachments']['nodes'], list) or []
                        for n in ns:
                            parse_attachment(n)
                        parse_attachment(attachment)

                edges = try_get(data, lambda x: x['mediaset']['currMedia']['edges'], list) or []
                for edge in edges:
                    parse_attachment(edge, key='node')

                video = data.get('video') or {}
                if video:
                    attachments = try_get(video, [
                        lambda x: x['story']['attachments'],
                        lambda x: x['creation_story']['attachments']
                    ], list) or []
                    for attachment in attachments:
                        parse_attachment(attachment)
                    if not entries:
                        parse_graphql_video(video)

                return self.playlist_result(entries, video_id)

        if not video_data:
            m_msg = re.search(r'class="[^"]*uiInterstitialContent[^"]*"><div>(.*?)</div>', webpage)
            if m_msg is not None:
                raise ExtractorError(
                    'The video is not available, Facebook said: "%s"' % m_msg.group(1),
                    expected=True)
            elif '>You must log in to continue' in webpage:
                self.raise_login_required()

        if not video_data and '/watchparty/' in url:
            post_data = {
                'doc_id': 3731964053542869,
                'variables': json.dumps({
                    'livingRoomID': video_id,
                }),
            }

            prefetched_data = extract_relay_prefetched_data(r'"login_data"\s*:\s*{')
            if prefetched_data:
                lsd = try_get(prefetched_data, lambda x: x['login_data']['lsd'], dict)
                if lsd:
                    post_data[lsd['name']] = lsd['value']

            relay_data = extract_relay_data(r'\[\s*"RelayAPIConfigDefaults"\s*,')
            for define in (relay_data.get('define') or []):
                if define[0] == 'RelayAPIConfigDefaults':
                    self._api_config = define[2]

            living_room = self._download_json(
                urljoin(url, self._api_config['graphURI']), video_id,
                data=urlencode_postdata(post_data))['data']['living_room']

            entries = []
            for edge in (try_get(living_room, lambda x: x['recap']['watched_content']['edges']) or []):
                video = try_get(edge, lambda x: x['node']['video']) or {}
                v_id = video.get('id')
                if not v_id:
                    continue
                v_id = compat_str(v_id)
                entries.append(self.url_result(
                    self._VIDEO_PAGE_TEMPLATE % v_id,
                    self.ie_key(), v_id, video.get('name')))

            return self.playlist_result(entries, video_id)

        if not video_data:
            # Video info not in first request, do a secondary request using
            # tahoe player specific URL
            tahoe_data = self._download_webpage(
                self._VIDEO_PAGE_TAHOE_TEMPLATE % video_id, video_id,
                data=urlencode_postdata({
                    '__a': 1,
                    '__pc': self._search_regex(
                        r'pkg_cohort["\']\s*:\s*["\'](.+?)["\']', webpage,
                        'pkg cohort', default='PHASED:DEFAULT'),
                    '__rev': self._search_regex(
                        r'client_revision["\']\s*:\s*(\d+),', webpage,
                        'client revision', default='3944515'),
                    'fb_dtsg': self._search_regex(
                        r'"DTSGInitialData"\s*,\s*\[\]\s*,\s*{\s*"token"\s*:\s*"([^"]+)"',
                        webpage, 'dtsg token', default=''),
                }),
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                })
            tahoe_js_data = self._parse_json(
                self._search_regex(
                    r'for\s+\(\s*;\s*;\s*\)\s*;(.+)', tahoe_data,
                    'tahoe js data', default='{}'),
                video_id, fatal=False)
            video_data = extract_from_jsmods_instances(tahoe_js_data)

        if not video_data:
            raise ExtractorError('Cannot parse data')

        if len(video_data) > 1:
            entries = []
            for v in video_data:
                video_url = v[0].get('video_url')
                if not video_url:
                    continue
                entries.append(self.url_result(urljoin(
                    url, video_url), self.ie_key(), v[0].get('video_id')))
            return self.playlist_result(entries, video_id)
        video_data = video_data[0]

        formats = []
        subtitles = {}
        for f in video_data:
            format_id = f['stream_type']
            if f and isinstance(f, dict):
                f = [f]
            if not f or not isinstance(f, list):
                continue
            for quality in ('sd', 'hd'):
                for src_type in ('src', 'src_no_ratelimit'):
                    src = f[0].get('%s_%s' % (quality, src_type))
                    if src:
                        preference = -10 if format_id == 'progressive' else 0
                        if quality == 'hd':
                            preference += 5
                        formats.append({
                            'format_id': '%s_%s_%s' % (format_id, quality, src_type),
                            'url': src,
                            'preference': preference,
                        })
            extract_dash_manifest(f[0], formats)
            subtitles_src = f[0].get('subtitles_src')
            if subtitles_src:
                subtitles.setdefault('en', []).append({'url': subtitles_src})
        if not formats:
            raise ExtractorError('Cannot find video formats')

        process_formats(formats)

        video_title = self._html_search_regex(
            r'<h2\s+[^>]*class="uiHeaderTitle"[^>]*>([^<]*)</h2>', webpage,
            'title', default=None)
        if not video_title:
            video_title = self._html_search_regex(
                r'(?s)<span class="fbPhotosPhotoCaption".*?id="fbPhotoPageCaption"><span class="hasCaption">(.*?)</span>',
                webpage, 'alternative title', default=None)
        if not video_title:
            video_title = self._html_search_meta(
                'description', webpage, 'title', default=None)
        if video_title:
            video_title = limit_length(video_title, 80)
        else:
            video_title = 'Facebook video #%s' % video_id
        uploader = clean_html(get_element_by_id(
            'fbPhotoPageAuthorName', webpage)) or self._search_regex(
            r'ownerName\s*:\s*"([^"]+)"', webpage, 'uploader',
            default=None) or self._og_search_title(webpage, fatal=False)
        timestamp = int_or_none(self._search_regex(
            r'<abbr[^>]+data-utime=["\'](\d+)', webpage,
            'timestamp', default=None))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage)

        view_count = parse_count(self._search_regex(
            r'\bviewCount\s*:\s*["\']([\d,.]+)', webpage, 'view count',
            default=None))

        info_dict = {
            'id': video_id,
            'title': video_title,
            'formats': formats,
            'uploader': uploader,
            'timestamp': timestamp,
            'thumbnail': thumbnail,
            'view_count': view_count,
            'subtitles': subtitles,
        }

        return info_dict

    def _real_extract(self, url):
        video_id = self._match_id(url)

        real_url = self._VIDEO_PAGE_TEMPLATE % video_id if url.startswith('facebook:') else url
        return self._extract_from_url(real_url, video_id)


class FacebookPluginsVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/plugins/video\.php\?.*?\bhref=(?P<id>https.+)'

    _TESTS = [{
        'url': 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fgov.sg%2Fvideos%2F10154383743583686%2F&show_text=0&width=560',
        'md5': '5954e92cdfe51fe5782ae9bda7058a07',
        'info_dict': {
            'id': '10154383743583686',
            'ext': 'mp4',
            'title': 'What to do during the haze?',
            'uploader': 'Gov.sg',
            'upload_date': '20160826',
            'timestamp': 1472184808,
        },
        'add_ie': [FacebookIE.ie_key()],
    }, {
        'url': 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fvideo.php%3Fv%3D10204634152394104',
        'only_matching': True,
    }, {
        'url': 'https://www.facebook.com/plugins/video.php?href=https://www.facebook.com/gov.sg/videos/10154383743583686/&show_text=0&width=560',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            compat_urllib_parse_unquote(self._match_id(url)),
            FacebookIE.ie_key())

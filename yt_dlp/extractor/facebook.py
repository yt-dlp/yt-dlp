import json
import re
import urllib.parse

from .common import InfoExtractor
from ..compat import (
    compat_etree_fromstring,
    compat_str,
    compat_urllib_parse_unquote,
)
from ..networking import Request
from ..networking.exceptions import network_exceptions
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    error_to_compat_str,
    float_or_none,
    format_field,
    get_element_by_id,
    get_first,
    int_or_none,
    join_nonempty,
    js_to_json,
    merge_dicts,
    parse_count,
    parse_qs,
    qualities,
    str_or_none,
    traverse_obj,
    try_get,
    url_or_none,
    urlencode_postdata,
    urljoin,
    variadic,
)


class FacebookIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                (?:
                    https?://
                        (?:[\w-]+\.)?(?:facebook\.com|facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd\.onion)/
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
                            groups/[^/]+/(?:permalink|posts)/|
                            watchparty/
                        )|
                    facebook:
                )
                (?P<id>pfbid[A-Za-z0-9]+|\d+)
                '''
    _EMBED_REGEX = [
        r'<iframe[^>]+?src=(["\'])(?P<url>https?://www\.facebook\.com/(?:video/embed|plugins/video\.php).+?)\1',
        # Facebook API embed https://developers.facebook.com/docs/plugins/embedded-video-player
        r'''(?x)<div[^>]+
                class=(?P<q1>[\'"])[^\'"]*\bfb-(?:video|post)\b[^\'"]*(?P=q1)[^>]+
                data-href=(?P<q2>[\'"])(?P<url>(?:https?:)?//(?:www\.)?facebook.com/.+?)(?P=q2)''',
    ]
    _LOGIN_URL = 'https://www.facebook.com/login.php?next=http%3A%2F%2Ffacebook.com%2Fhome.php&login_attempt=1'
    _CHECKPOINT_URL = 'https://www.facebook.com/checkpoint/?next=http%3A%2F%2Ffacebook.com%2Fhome.php&_fb_noscript=1'
    _NETRC_MACHINE = 'facebook'
    IE_NAME = 'facebook'

    _VIDEO_PAGE_TEMPLATE = 'https://www.facebook.com/video/video.php?v=%s'
    _VIDEO_PAGE_TAHOE_TEMPLATE = 'https://www.facebook.com/video/tahoe/async/%s/?chain=true&isvideo=true&payloadtype=primary'

    _TESTS = [{
        'url': 'https://www.facebook.com/radiokicksfm/videos/3676516585958356/',
        'info_dict': {
            'id': '3676516585958356',
            'ext': 'mp4',
            'title': 'dr Adam Przygoda',
            'description': 'md5:34675bda53336b1d16400265c2bb9b3b',
            'uploader': 'RADIO KICKS FM',
            'upload_date': '20230818',
            'timestamp': 1692346159,
            'thumbnail': r're:^https?://.*',
            'uploader_id': '100063551323670',
            'duration': 3132.184,
            'view_count': int,
            'concurrent_view_count': 0,
        },
    }, {
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
            'title': 'Asif',
            'description': '',
            'uploader': 'Asif Nawab Butt',
            'upload_date': '20140506',
            'timestamp': 1399398998,
            'thumbnail': r're:^https?://.*',
            'uploader_id': 'pfbid028wxorhX2ErLFJ578N6P3crHD3PHmXTCqCvfBpsnbSLmbokwSY75p5hWBjHGkG4zxl',
            'duration': 131.03,
            'concurrent_view_count': int,
        },
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
        'skip': 'Gif on giphy.com gone',
    }, {
        # have 1080P, but only up to 720p in swf params
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/cnn/videos/10155529876156509/',
        'md5': 'ca63897a90c9452efee5f8c40d080e25',
        'info_dict': {
            'id': '10155529876156509',
            'ext': 'mp4',
            'title': 'Holocaust survivor becomes US citizen',
            'description': 'She survived the holocaust — and years later, she’s getting her citizenship so she can vote for Hillary Clinton http://cnn.it/2eERh5f',
            'timestamp': 1477818095,
            'upload_date': '20161030',
            'uploader': 'CNN',
            'thumbnail': r're:^https?://.*',
            'view_count': int,
            'uploader_id': '100059479812265',
            'concurrent_view_count': int,
            'duration': 44.478,
        },
    }, {
        # bigPipe.onPageletArrive ... onPageletArrive pagelet_group_mall
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.media
        'url': 'https://www.facebook.com/yaroslav.korpan/videos/1417995061575415/',
        'info_dict': {
            'id': '1417995061575415',
            'ext': 'mp4',
            'title': 'Довгоочікуване відео | By Yaroslav - Facebook',
            'description': 'Довгоочікуване відео',
            'timestamp': 1486648217,
            'upload_date': '20170209',
            'uploader': 'Yaroslav Korpan',
            'uploader_id': 'pfbid06AScABAWcW91qpiuGrLt99Ef9tvwHoXP6t8KeFYEqkSfreMtfa9nTveh8b2ZEVSWl',
            'concurrent_view_count': int,
            'thumbnail': r're:^https?://.*',
            'view_count': int,
            'duration': 11736.446,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # FIXME
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
        'skip': 'Requires logging in',
    }, {
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.media
        'url': 'https://www.facebook.com/groups/1024490957622648/permalink/1396382447100162/',
        'info_dict': {
            'id': '202882990186699',
            'ext': 'mp4',
            'title': 'birb (O v O") | Hello? Yes your uber ride is here',
            'description': 'Hello? Yes your uber ride is here * Jukin Media Verified * Find this video and others like it by visiting...',
            'timestamp': 1486035513,
            'upload_date': '20170202',
            'uploader': 'Elisabeth Ahtn',
            'uploader_id': '100013949973717',
        },
        'skip': 'Requires logging in',
    }, {
        # data.node.comet_sections.content.story.attachments[].throwbackStyles.attachment_target_renderer.attachment.target.attachments[].styles.attachment.media
        'url': 'https://www.facebook.com/groups/1645456212344334/posts/3737828833107051/',
        'info_dict': {
            'id': '1569199726448814',
            'ext': 'mp4',
            'title': 'Pence MUST GO!',
            'description': 'Vickie Gentry shared a memory.',
            'timestamp': 1511548260,
            'upload_date': '20171124',
            'uploader': 'Vickie Gentry',
            'uploader_id': 'pfbid0FuZhHCeWDAxWxEbr3yKPFaRstXvRxgsp9uCPG6GjD4J2AitB35NUAuJ4Q75KcjiDl',
            'thumbnail': r're:^https?://.*',
            'duration': 148.435,
        },
    }, {
        'url': 'https://www.facebook.com/attn/posts/pfbid0j1Czf2gGDVqeQ8KiMLFm3pWN8GxsQmeRrVhimWDzMuKQoR8r4b1knNsejELmUgyhl',
        'info_dict': {
            'id': '6968553779868435',
            'ext': 'mp4',
            'description': 'md5:2f2fcf93e97ac00244fe64521bbdb0cb',
            'uploader': 'ATTN:',
            'upload_date': '20231207',
            'title': 'ATTN:',
            'duration': 132.675,
            'uploader_id': '100064451419378',
            'view_count': int,
            'thumbnail': r're:^https?://.*',
            'timestamp': 1701975646,
        },
    }, {
        'url': 'https://www.facebook.com/story.php?story_fbid=pfbid0Fnzhm8UuzjBYpPMNFzaSpFE9UmLdU4fJN8qTANi1Dmtj5q7DNrL5NERXfsAzDEV7l&id=100073071055552',
        'only_matching': True,
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
        'url': 'https://www.facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion/video.php?v=274175099429670',
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
            'title': 'Fnatic vs. EG - Group A - Opening Match - ESL One Birmingham Day 1',
            'description': '#ESLOne VoD - Birmingham Finals Day#1 Fnatic vs. @Evil Geniuses',
            'timestamp': 1527084179,
            'upload_date': '20180523',
            'uploader': 'ESL One Dota 2',
            'uploader_id': '100066514874195',
            'duration': 4524.212,
            'view_count': int,
            'thumbnail': r're:^https?://.*',
            'concurrent_view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.all_subattachments.nodes[].media
        'url': 'https://www.facebook.com/100033620354545/videos/106560053808006/',
        'info_dict': {
            'id': '106560053808006',
            'ext': 'mp4',
            'title': 'Josef',
            'thumbnail': r're:^https?://.*',
            'concurrent_view_count': int,
            'uploader_id': 'pfbid0cibUN6tV7DYgdbJdsUFN46wc4jKpVSPAvJQhFofGqBGmVn3V3JtAs2tfUwziw2hUl',
            'timestamp': 1549275572,
            'duration': 3.413,
            'uploader': 'Josef Novak',
            'description': '',
            'upload_date': '20190204',
        },
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/watch/?v=647537299265662',
        'only_matching': True,
    }, {
        # FIXME: https://github.com/yt-dlp/yt-dlp/issues/542
        # data.node.comet_sections.content.story.attachments[].style_type_renderer.attachment.all_subattachments.nodes[].media
        'url': 'https://www.facebook.com/PankajShahLondon/posts/10157667649866271',
        'info_dict': {
            'id': '10157667649866271',
        },
        'playlist_count': 3,
        'skip': 'Requires logging in',
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
        'skip': 'No video',
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

    def _perform_login(self, username, password):
        login_page_req = Request(self._LOGIN_URL)
        self._set_cookie('facebook.com', 'locale', 'en_US')
        login_page = self._download_webpage(login_page_req, None,
                                            note='Downloading login page',
                                            errnote='Unable to download login page')
        lsd = self._search_regex(
            r'<input type="hidden" name="lsd" value="([^"]*)"',
            login_page, 'lsd')
        lgnrnd = self._search_regex(r'name="lgnrnd" value="([^"]*?)"', login_page, 'lgnrnd')

        login_form = {
            'email': username,
            'pass': password,
            'lsd': lsd,
            'lgnrnd': lgnrnd,
            'next': 'http://facebook.com/home.php',
            'default_persistent': '0',
            'legacy_return': '1',
            'timezone': '-60',
            'trynum': '1',
        }
        request = Request(self._LOGIN_URL, urlencode_postdata(login_form))
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            login_results = self._download_webpage(request, None,
                                                   note='Logging in', errnote='unable to fetch login page')
            if re.search(r'<form(.*)name="login"(.*)</form>', login_results) is not None:
                error = self._html_search_regex(
                    r'(?s)<div[^>]+class=(["\']).*?login_error_box.*?\1[^>]*><div[^>]*>.*?</div><div[^>]*>(?P<error>.+?)</div>',
                    login_results, 'login error', default=None, group='error')
                if error:
                    raise ExtractorError('Unable to login: %s' % error, expected=True)
                self.report_warning('unable to log in: bad username/password, or exceeded login rate limit (~3/min). Check credentials or wait.')
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
            check_req = Request(self._CHECKPOINT_URL, urlencode_postdata(check_form))
            check_req.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            check_response = self._download_webpage(check_req, None,
                                                    note='Confirming login')
            if re.search(r'id="checkpointSubmitButton"', check_response) is not None:
                self.report_warning('Unable to confirm login, you have to login in your browser and authorize the login.')
        except network_exceptions as err:
            self.report_warning('unable to log in: %s' % error_to_compat_str(err))
            return

    def _extract_from_url(self, url, video_id):
        webpage = self._download_webpage(
            url.replace('://m.facebook.com/', '://www.facebook.com/'), video_id)

        def extract_metadata(webpage):
            post_data = [self._parse_json(j, video_id, fatal=False) for j in re.findall(
                r'data-sjs>({.*?ScheduledServerJS.*?})</script>', webpage)]
            post = traverse_obj(post_data, (
                ..., 'require', ..., ..., ..., '__bbox', 'require', ..., ..., ..., '__bbox', 'result', 'data'), expected_type=dict) or []

            automatic_captions, subtitles = {}, {}
            subs_data = traverse_obj(post, (..., 'video', ..., 'attachments', ..., lambda k, v: (
                k == 'media' and str(v['id']) == video_id and v['__typename'] == 'Video')))
            is_video_broadcast = get_first(subs_data, 'is_video_broadcast', expected_type=bool)
            captions = get_first(subs_data, 'video_available_captions_locales', 'captions_url')
            if url_or_none(captions):  # if subs_data only had a 'captions_url'
                locale = self._html_search_meta(['og:locale', 'twitter:locale'], webpage, 'locale', default='en_US')
                subtitles[locale] = [{'url': captions}]
            # or else subs_data had 'video_available_captions_locales', a list of dicts
            for caption in traverse_obj(captions, (
                {lambda x: sorted(x, key=lambda c: c['locale'])}, lambda _, v: v['captions_url'])
            ):
                lang = caption.get('localized_language') or ''
                subs = {
                    'url': caption['captions_url'],
                    'name': format_field(caption, 'localized_country', f'{lang} (%s)', default=lang),
                }
                if caption.get('localized_creation_method') or is_video_broadcast:
                    automatic_captions.setdefault(caption['locale'], []).append(subs)
                else:
                    subtitles.setdefault(caption['locale'], []).append(subs)

            media = traverse_obj(post, (..., 'attachments', ..., lambda k, v: (
                k == 'media' and str(v['id']) == video_id and v['__typename'] == 'Video')), expected_type=dict)
            title = get_first(media, ('title', 'text'))
            description = get_first(media, ('creation_story', 'comet_sections', 'message', 'story', 'message', 'text'))
            uploader_data = (
                get_first(media, ('owner', {dict}))
                or get_first(post, (..., 'video', lambda k, v: k == 'owner' and v['name']))
                or get_first(post, ('node', 'actors', ..., {dict})) or {})

            page_title = title or self._html_search_regex((
                r'<h2\s+[^>]*class="uiHeaderTitle"[^>]*>(?P<content>[^<]*)</h2>',
                r'(?s)<span class="fbPhotosPhotoCaption".*?id="fbPhotoPageCaption"><span class="hasCaption">(?P<content>.*?)</span>',
                self._meta_regex('og:title'), self._meta_regex('twitter:title'), r'<title>(?P<content>.+?)</title>'
            ), webpage, 'title', default=None, group='content')
            description = description or self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, 'description', default=None)
            uploader = uploader_data.get('name') or (
                clean_html(get_element_by_id('fbPhotoPageAuthorName', webpage))
                or self._search_regex(
                    (r'ownerName\s*:\s*"([^"]+)"', *self._og_regexes('title')), webpage, 'uploader', fatal=False))

            timestamp = int_or_none(self._search_regex(
                r'<abbr[^>]+data-utime=["\'](\d+)', webpage,
                'timestamp', default=None))
            thumbnail = self._html_search_meta(
                ['og:image', 'twitter:image'], webpage, 'thumbnail', default=None)
            # some webpages contain unretrievable thumbnail urls
            # like https://lookaside.fbsbx.com/lookaside/crawler/media/?media_id=10155168902769113&get_thumbnail=1
            # in https://www.facebook.com/yaroslav.korpan/videos/1417995061575415/
            if thumbnail and not re.search(r'\.(?:jpg|png)', thumbnail):
                thumbnail = None
            info_dict = {
                'description': description,
                'uploader': uploader,
                'uploader_id': uploader_data.get('id'),
                'timestamp': timestamp,
                'thumbnail': thumbnail,
                'view_count': parse_count(self._search_regex(
                    (r'\bviewCount\s*:\s*["\']([\d,.]+)', r'video_view_count["\']\s*:\s*(\d+)',),
                    webpage, 'view count', default=None)),
                'concurrent_view_count': get_first(post, (
                    ('video', (..., ..., 'attachments', ..., 'media')), 'liveViewerCount', {int_or_none})),
                'automatic_captions': automatic_captions,
                'subtitles': subtitles,
            }

            info_json_ld = self._search_json_ld(webpage, video_id, default={})
            info_json_ld['title'] = (re.sub(r'\s*\|\s*Facebook$', '', title or info_json_ld.get('title') or page_title or '')
                                     or (description or '').replace('\n', ' ') or f'Facebook video #{video_id}')
            return merge_dicts(info_json_ld, info_dict)

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
                    compat_etree_fromstring(urllib.parse.unquote_plus(dash_manifest)),
                    mpd_url=video.get('dash_manifest_url')))

        def process_formats(info):
            # Downloads with browser's User-Agent are rate limited. Working around
            # with non-browser User-Agent.
            for f in info['formats']:
                # Downloads with browser's User-Agent are rate limited. Working around
                # with non-browser User-Agent.
                f.setdefault('http_headers', {})['User-Agent'] = 'facebookexternalhit/1.1'
                # Formats larger than ~500MB will return error 403 unless chunk size is regulated
                f.setdefault('downloader_options', {})['http_chunk_size'] = 250 << 20

        def extract_relay_data(_filter):
            return self._parse_json(self._search_regex(
                r'data-sjs>({.*?%s.*?})</script>' % _filter,
                webpage, 'replay data', default='{}'), video_id, fatal=False) or {}

        def extract_relay_prefetched_data(_filter):
            return traverse_obj(extract_relay_data(_filter), (
                'require', (None, (..., ..., ..., '__bbox', 'require')),
                lambda _, v: 'RelayPrefetchedStreamCache' in v, ..., ...,
                '__bbox', 'result', 'data', {dict}), get_all=False) or {}

        if not video_data:
            server_js_data = self._parse_json(self._search_regex([
                r'bigPipe\.onPageletArrive\(({.+?})\)\s*;\s*}\s*\)\s*,\s*["\']onPageletArrive\s+' + self._SUPPORTED_PAGLETS_REGEX,
                r'bigPipe\.onPageletArrive\(({.*?id\s*:\s*"%s".*?})\);' % self._SUPPORTED_PAGLETS_REGEX
            ], webpage, 'js data', default='{}'), video_id, js_to_json, False)
            video_data = extract_from_jsmods_instances(server_js_data)

        if not video_data:
            data = extract_relay_prefetched_data(
                r'"(?:dash_manifest|playable_url(?:_quality_hd)?)')
            if data:
                entries = []

                def parse_graphql_video(video):
                    v_id = video.get('videoId') or video.get('id') or video_id
                    reel_info = traverse_obj(
                        video, ('creation_story', 'short_form_video_context', 'playback_video', {dict}))
                    if reel_info:
                        video = video['creation_story']
                        video['owner'] = traverse_obj(video, ('short_form_video_context', 'video_owner'))
                        video.update(reel_info)
                    formats = []
                    q = qualities(['sd', 'hd'])
                    for key, format_id in (('playable_url', 'sd'), ('playable_url_quality_hd', 'hd'),
                                           ('playable_url_dash', ''), ('browser_native_hd_url', 'hd'),
                                           ('browser_native_sd_url', 'sd')):
                        playable_url = video.get(key)
                        if not playable_url:
                            continue
                        if determine_ext(playable_url) == 'mpd':
                            formats.extend(self._extract_mpd_formats(playable_url, video_id))
                        else:
                            formats.append({
                                'format_id': format_id,
                                # sd, hd formats w/o resolution info should be deprioritized below DASH
                                'quality': q(format_id) - 3,
                                'url': playable_url,
                            })
                    extract_dash_manifest(video, formats)
                    info = {
                        'id': v_id,
                        'formats': formats,
                        'thumbnail': traverse_obj(
                            video, ('thumbnailImage', 'uri'), ('preferred_thumbnail', 'image', 'uri')),
                        'uploader_id': traverse_obj(video, ('owner', 'id', {str_or_none})),
                        'timestamp': traverse_obj(video, 'publish_time', 'creation_time', expected_type=int_or_none),
                        'duration': (float_or_none(video.get('playable_duration_in_ms'), 1000)
                                     or float_or_none(video.get('length_in_second'))),
                    }
                    process_formats(info)
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

                nodes = variadic(traverse_obj(data, 'nodes', 'node') or [])
                attachments = traverse_obj(nodes, (
                    ..., 'comet_sections', 'content', 'story', (None, 'attached_story'), 'attachments',
                    ..., ('styles', 'style_type_renderer', ('throwbackStyles', 'attachment_target_renderer')),
                    'attachment', {dict}))
                for attachment in attachments:
                    ns = traverse_obj(attachment, ('all_subattachments', 'nodes', ..., {dict}),
                                      ('target', 'attachments', ..., 'styles', 'attachment', {dict}))
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

                if len(entries) > 1:
                    return self.playlist_result(entries, video_id)

                video_info = entries[0] if entries else {'id': video_id}
                webpage_info = extract_metadata(webpage)
                # honor precise duration in video info
                if video_info.get('duration'):
                    webpage_info['duration'] = video_info['duration']
                return merge_dicts(webpage_info, video_info)

        if not video_data:
            m_msg = re.search(r'class="[^"]*uiInterstitialContent[^"]*"><div>(.*?)</div>', webpage)
            if m_msg is not None:
                raise ExtractorError(
                    'The video is not available, Facebook said: "%s"' % m_msg.group(1),
                    expected=True)
            elif any(p in webpage for p in (
                    '>You must log in to continue',
                    'id="login_form"',
                    'id="loginbutton"')):
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
                        # sd, hd formats w/o resolution info should be deprioritized below DASH
                        # TODO: investigate if progressive or src formats still exist
                        preference = -10 if format_id == 'progressive' else -3
                        if quality == 'hd':
                            preference += 1
                        formats.append({
                            'format_id': '%s_%s_%s' % (format_id, quality, src_type),
                            'url': src,
                            'quality': preference,
                            'height': 720 if quality == 'hd' else None
                        })
            extract_dash_manifest(f[0], formats)
            subtitles_src = f[0].get('subtitles_src')
            if subtitles_src:
                subtitles.setdefault('en', []).append({'url': subtitles_src})

        info_dict = {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
        }
        process_formats(info_dict)
        info_dict.update(extract_metadata(webpage))

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
            # TODO: Fix title, uploader
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


class FacebookRedirectURLIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/flx/warn[/?]'
    _TESTS = [{
        'url': 'https://www.facebook.com/flx/warn/?h=TAQHsoToz&u=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DpO8h3EaFRdo&s=1',
        'info_dict': {
            'id': 'pO8h3EaFRdo',
            'ext': 'mp4',
            'title': 'Tripeo Boiler Room x Dekmantel Festival DJ Set',
            'description': 'md5:2d713ccbb45b686a1888397b2c77ca6b',
            'channel_id': 'UCGBpxWJr9FNOcFYA5GkKrMg',
            'playable_in_embed': True,
            'categories': ['Music'],
            'channel': 'Boiler Room',
            'uploader_id': 'brtvofficial',
            'uploader': 'Boiler Room',
            'tags': 'count:11',
            'duration': 3332,
            'live_status': 'not_live',
            'thumbnail': 'https://i.ytimg.com/vi/pO8h3EaFRdo/maxresdefault.jpg',
            'channel_url': 'https://www.youtube.com/channel/UCGBpxWJr9FNOcFYA5GkKrMg',
            'availability': 'public',
            'uploader_url': 'http://www.youtube.com/user/brtvofficial',
            'upload_date': '20150917',
            'age_limit': 0,
            'view_count': int,
            'like_count': int,
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'Youtube'},
    }]

    def _real_extract(self, url):
        redirect_url = url_or_none(parse_qs(url).get('u', [None])[-1])
        if not redirect_url:
            raise ExtractorError('Invalid facebook redirect URL', expected=True)
        return self.url_result(redirect_url)


class FacebookReelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/reel/(?P<id>\d+)'
    IE_NAME = 'facebook:reel'

    _TESTS = [{
        'url': 'https://www.facebook.com/reel/1195289147628387',
        'md5': 'f13dd37f2633595982db5ed8765474d3',
        'info_dict': {
            'id': '1195289147628387',
            'ext': 'mp4',
            'title': 'md5:b05800b5b1ad56c0ca78bd3807b6a61e',
            'description': 'md5:22f03309b216ac84720183961441d8db',
            'uploader': 'md5:723e6cb3091241160f20b3c5dc282af1',
            'uploader_id': '100040874179269',
            'duration': 9.579,
            'timestamp': 1637502609,
            'upload_date': '20211121',
            'thumbnail': r're:^https?://.*',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'https://m.facebook.com/watch/?v={video_id}&_rdr', FacebookIE, video_id)


class FacebookAdsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/ads/library/?\?(?:[^#]+&)?id=(?P<id>\d+)'
    IE_NAME = 'facebook:ads'

    _TESTS = [{
        'url': 'https://www.facebook.com/ads/library/?id=899206155126718',
        'info_dict': {
            'id': '899206155126718',
            'ext': 'mp4',
            'title': 'video by Kandao',
            'uploader': 'Kandao',
            'uploader_id': '774114102743284',
            'uploader_url': r're:^https?://.*',
            'timestamp': 1702548330,
            'thumbnail': r're:^https?://.*',
            'upload_date': '20231214',
            'like_count': int,
        }
    }, {
        'url': 'https://www.facebook.com/ads/library/?id=893637265423481',
        'info_dict': {
            'id': '893637265423481',
            'title': 'Jusqu\u2019\u00e0 -25% sur une s\u00e9lection de vins p\u00e9tillants italiens ',
            'uploader': 'Eataly Paris Marais',
            'uploader_id': '2086668958314152',
            'uploader_url': r're:^https?://.*',
            'timestamp': 1703571529,
            'upload_date': '20231226',
            'like_count': int,
        },
        'playlist_count': 3,
    }, {
        'url': 'https://es-la.facebook.com/ads/library/?id=901230958115569',
        'only_matching': True,
    }, {
        'url': 'https://m.facebook.com/ads/library/?id=901230958115569',
        'only_matching': True,
    }]

    _FORMATS_MAP = {
        'watermarked_video_sd_url': ('sd-wmk', 'SD, watermarked'),
        'video_sd_url': ('sd', None),
        'watermarked_video_hd_url': ('hd-wmk', 'HD, watermarked'),
        'video_hd_url': ('hd', None),
    }

    def _extract_formats(self, video_dict):
        formats = []
        for format_key, format_url in traverse_obj(video_dict, (
            {dict.items}, lambda _, v: v[0] in self._FORMATS_MAP and url_or_none(v[1])
        )):
            formats.append({
                'format_id': self._FORMATS_MAP[format_key][0],
                'format_note': self._FORMATS_MAP[format_key][1],
                'url': format_url,
                'ext': 'mp4',
                'quality': qualities(tuple(self._FORMATS_MAP))(format_key),
            })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        post_data = [self._parse_json(j, video_id, fatal=False)
                     for j in re.findall(r's\.handle\(({.*})\);requireLazy\(', webpage)]
        data = traverse_obj(post_data, (
            ..., 'require', ..., ..., ..., 'props', 'deeplinkAdCard', 'snapshot', {dict}), get_all=False)
        if not data:
            raise ExtractorError('Unable to extract ad data')

        title = data.get('title')
        if not title or title == '{{product.name}}':
            title = join_nonempty('display_format', 'page_name', delim=' by ', from_dict=data)

        info_dict = traverse_obj(data, {
            'description': ('link_description', {str}, {lambda x: x if x != '{{product.description}}' else None}),
            'uploader': ('page_name', {str}),
            'uploader_id': ('page_id', {str_or_none}),
            'uploader_url': ('page_profile_uri', {url_or_none}),
            'timestamp': ('creation_time', {int_or_none}),
            'like_count': ('page_like_count', {int_or_none}),
        })

        entries = []
        for idx, entry in enumerate(traverse_obj(
            data, (('videos', 'cards'), lambda _, v: any([url_or_none(v[f]) for f in self._FORMATS_MAP]))), 1
        ):
            entries.append({
                'id': f'{video_id}_{idx}',
                'title': entry.get('title') or title,
                'description': entry.get('link_description') or info_dict.get('description'),
                'thumbnail': url_or_none(entry.get('video_preview_image_url')),
                'formats': self._extract_formats(entry),
            })

        if len(entries) == 1:
            info_dict.update(entries[0])

        elif len(entries) > 1:
            info_dict.update({
                'title': entries[0]['title'],
                'entries': entries,
                '_type': 'playlist',
            })

        info_dict['id'] = video_id

        return info_dict

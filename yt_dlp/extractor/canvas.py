from __future__ import unicode_literals
import json


from .common import InfoExtractor
from .gigya import GigyaBaseIE
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    get_element_by_class,
    int_or_none,
    merge_dicts,
    str_or_none,
    strip_or_none,
    url_or_none,
    urlencode_postdata
)


class CanvasIE(InfoExtractor):
    _VALID_URL = r'https?://mediazone\.vrt\.be/api/v1/(?P<site_id>canvas|een|ketnet|vrt(?:video|nieuws)|sporza|dako)/assets/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://mediazone.vrt.be/api/v1/ketnet/assets/md-ast-4ac54990-ce66-4d00-a8ca-9eac86f4c475',
        'md5': '37b2b7bb9b3dcaa05b67058dc3a714a9',
        'info_dict': {
            'id': 'md-ast-4ac54990-ce66-4d00-a8ca-9eac86f4c475',
            'display_id': 'md-ast-4ac54990-ce66-4d00-a8ca-9eac86f4c475',
            'ext': 'mp4',
            'title': 'Nachtwacht: De Greystook',
            'description': 'Nachtwacht: De Greystook',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1468.02,
        },
        'expected_warnings': ['is not a supported codec'],
    }, {
        'url': 'https://mediazone.vrt.be/api/v1/canvas/assets/mz-ast-5e5f90b6-2d72-4c40-82c2-e134f884e93e',
        'only_matching': True,
    }]
    _GEO_BYPASS = False
    _HLS_ENTRY_PROTOCOLS_MAP = {
        'HLS': 'm3u8_native',
        'HLS_AES': 'm3u8_native',
    }
    _REST_API_BASE = 'https://media-services-public.vrt.be/vualto-video-aggregator-web/rest/external/v2'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        site_id, video_id = mobj.group('site_id'), mobj.group('id')

        data = None
        if site_id != 'vrtvideo':
            # Old API endpoint, serves more formats but may fail for some videos
            data = self._download_json(
                'https://mediazone.vrt.be/api/v1/%s/assets/%s'
                % (site_id, video_id), video_id, 'Downloading asset JSON',
                'Unable to download asset JSON', fatal=False)

        # New API endpoint
        if not data:
            vrtnutoken = self._download_json('https://token.vrt.be/refreshtoken',
                                             video_id, note='refreshtoken: Retrieve vrtnutoken',
                                             errnote='refreshtoken failed')['vrtnutoken']
            headers = self.geo_verification_headers()
            headers.update({'Content-Type': 'application/json; charset=utf-8'})
            vrtPlayerToken = self._download_json(
                '%s/tokens' % self._REST_API_BASE, video_id,
                'Downloading token', headers=headers, data=json.dumps({
                    'identityToken': vrtnutoken
                }).encode('utf-8'))['vrtPlayerToken']
            data = self._download_json(
                '%s/videos/%s' % (self._REST_API_BASE, video_id),
                video_id, 'Downloading video JSON', query={
                    'vrtPlayerToken': vrtPlayerToken,
                    'client': 'null',
                }, expected_status=400)
            if 'title' not in data:
                code = data.get('code')
                if code == 'AUTHENTICATION_REQUIRED':
                    self.raise_login_required()
                elif code == 'INVALID_LOCATION':
                    self.raise_geo_restricted(countries=['BE'])
                raise ExtractorError(data.get('message') or code, expected=True)

        # Note: The title may be an empty string
        title = data['title'] or f'{site_id} {video_id}'
        description = data.get('description')

        formats = []
        subtitles = {}
        for target in data['targetUrls']:
            format_url, format_type = url_or_none(target.get('url')), str_or_none(target.get('type'))
            if not format_url or not format_type:
                continue
            format_type = format_type.upper()
            if format_type in self._HLS_ENTRY_PROTOCOLS_MAP:
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', self._HLS_ENTRY_PROTOCOLS_MAP[format_type],
                    m3u8_id=format_type, fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif format_type == 'HDS':
                formats.extend(self._extract_f4m_formats(
                    format_url, video_id, f4m_id=format_type, fatal=False))
            elif format_type == 'MPEG_DASH':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id=format_type, fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif format_type == 'HSS':
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    format_url, video_id, ism_id='mss', fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            else:
                formats.append({
                    'format_id': format_type,
                    'url': format_url,
                })
        self._sort_formats(formats)

        subtitle_urls = data.get('subtitleUrls')
        if isinstance(subtitle_urls, list):
            for subtitle in subtitle_urls:
                subtitle_url = subtitle.get('url')
                if subtitle_url and subtitle.get('type') == 'CLOSED':
                    subtitles.setdefault('nl', []).append({'url': subtitle_url})

        return {
            'id': video_id,
            'display_id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
            'duration': float_or_none(data.get('duration'), 1000),
            'thumbnail': data.get('posterImageUrl'),
            'subtitles': subtitles,
        }


class CanvasEenIE(InfoExtractor):
    IE_DESC = 'canvas.be and een.be'
    _VALID_URL = r'https?://(?:www\.)?(?P<site_id>canvas|een)\.be/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.canvas.be/video/de-afspraak/najaar-2015/de-afspraak-veilt-voor-de-warmste-week',
        'md5': 'ed66976748d12350b118455979cca293',
        'info_dict': {
            'id': 'mz-ast-5e5f90b6-2d72-4c40-82c2-e134f884e93e',
            'display_id': 'de-afspraak-veilt-voor-de-warmste-week',
            'ext': 'flv',
            'title': 'De afspraak veilt voor de Warmste Week',
            'description': 'md5:24cb860c320dc2be7358e0e5aa317ba6',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 49.02,
        },
        'expected_warnings': ['is not a supported codec'],
    }, {
        # with subtitles
        'url': 'http://www.canvas.be/video/panorama/2016/pieter-0167',
        'info_dict': {
            'id': 'mz-ast-5240ff21-2d30-4101-bba6-92b5ec67c625',
            'display_id': 'pieter-0167',
            'ext': 'mp4',
            'title': 'Pieter 0167',
            'description': 'md5:943cd30f48a5d29ba02c3a104dc4ec4e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2553.08,
            'subtitles': {
                'nl': [{
                    'ext': 'vtt',
                }],
            },
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Pagina niet gevonden',
    }, {
        'url': 'https://www.een.be/thuis/emma-pakt-thilly-aan',
        'info_dict': {
            'id': 'md-ast-3a24ced2-64d7-44fb-b4ed-ed1aafbf90b8',
            'display_id': 'emma-pakt-thilly-aan',
            'ext': 'mp4',
            'title': 'Emma pakt Thilly aan',
            'description': 'md5:c5c9b572388a99b2690030afa3f3bad7',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 118.24,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['is not a supported codec'],
    }, {
        'url': 'https://www.canvas.be/check-point/najaar-2016/de-politie-uw-vriend',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        site_id, display_id = mobj.group('site_id'), mobj.group('id')

        webpage = self._download_webpage(url, display_id)

        title = strip_or_none(self._search_regex(
            r'<h1[^>]+class="video__body__header__title"[^>]*>(.+?)</h1>',
            webpage, 'title', default=None) or self._og_search_title(
            webpage, default=None))

        video_id = self._html_search_regex(
            r'data-video=(["\'])(?P<id>(?:(?!\1).)+)\1', webpage, 'video id',
            group='id')

        return {
            '_type': 'url_transparent',
            'url': 'https://mediazone.vrt.be/api/v1/%s/assets/%s' % (site_id, video_id),
            'ie_key': CanvasIE.ie_key(),
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': self._og_search_description(webpage),
        }


class VrtNUIE(GigyaBaseIE):
    IE_DESC = 'VrtNU.be'
    _VALID_URL = r'https?://(?:www\.)?vrt\.be/vrtnu/a-z/(?:[^/]+/){2}(?P<id>[^/?#&]+)'
    _TESTS = [{
        # Available via old API endpoint
        'url': 'https://www.vrt.be/vrtnu/a-z/postbus-x/1989/postbus-x-s1989a1/',
        'info_dict': {
            'id': 'pbs-pub-e8713dac-899e-41de-9313-81269f4c04ac$vid-90c932b1-e21d-4fb8-99b1-db7b49cf74de',
            'ext': 'mp4',
            'title': 'Postbus X - Aflevering 1 (Seizoen 1989)',
            'description': 'md5:b704f669eb9262da4c55b33d7c6ed4b7',
            'duration': 1457.04,
            'thumbnail': r're:^https?://.*\.jpg$',
            'series': 'Postbus X',
            'season': 'Seizoen 1989',
            'season_number': 1989,
            'episode': 'De zwarte weduwe',
            'episode_number': 1,
            'timestamp': 1595822400,
            'upload_date': '20200727',
        },
        'skip': 'This video is only available for registered users',
        'params': {
            'username': '<snip>',
            'password': '<snip>',
        },
        'expected_warnings': ['is not a supported codec'],
    }, {
        # Only available via new API endpoint
        'url': 'https://www.vrt.be/vrtnu/a-z/kamp-waes/1/kamp-waes-s1a5/',
        'info_dict': {
            'id': 'pbs-pub-0763b56c-64fb-4d38-b95b-af60bf433c71$vid-ad36a73c-4735-4f1f-b2c0-a38e6e6aa7e1',
            'ext': 'mp4',
            'title': 'Aflevering 5',
            'description': 'Wie valt door de mand tijdens een missie?',
            'duration': 2967.06,
            'season': 'Season 1',
            'season_number': 1,
            'episode_number': 5,
        },
        'skip': 'This video is only available for registered users',
        'params': {
            'username': '<snip>',
            'password': '<snip>',
        },
        'expected_warnings': ['Unable to download asset JSON', 'is not a supported codec', 'Unknown MIME type'],
    }]
    _NETRC_MACHINE = 'vrtnu'
    _APIKEY = '3_0Z2HujMtiWq_pkAjgnS2Md2E11a1AwZjYiBETtwNE-EoEHDINgtnvcAOpNgmrVGy'
    _CONTEXT_ID = 'R3595707040'

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        auth_info = self._gigya_login({
            'APIKey': self._APIKEY,
            'targetEnv': 'jssdk',
            'loginID': username,
            'password': password,
            'authMode': 'cookie',
        })

        if auth_info.get('errorDetails'):
            raise ExtractorError('Unable to login: VrtNU said: ' + auth_info.get('errorDetails'), expected=True)

        # Sometimes authentication fails for no good reason, retry
        login_attempt = 1
        while login_attempt <= 3:
            try:
                self._request_webpage('https://token.vrt.be/vrtnuinitlogin',
                                      None, note='Requesting XSRF Token', errnote='Could not get XSRF Token',
                                      query={'provider': 'site', 'destination': 'https://www.vrt.be/vrtnu/'})

                post_data = {
                    'UID': auth_info['UID'],
                    'UIDSignature': auth_info['UIDSignature'],
                    'signatureTimestamp': auth_info['signatureTimestamp'],
                    '_csrf': self._get_cookies('https://login.vrt.be').get('OIDCXSRF').value,
                }

                self._request_webpage(
                    'https://login.vrt.be/perform_login',
                    None, note='Performing login', errnote='perform login failed',
                    headers={}, query={
                        'client_id': 'vrtnu-site'
                    }, data=urlencode_postdata(post_data))

            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    login_attempt += 1
                    self.report_warning('Authentication failed')
                    self._sleep(1, None, msg_template='Waiting for %(timeout)s seconds before trying again')
                else:
                    raise e
            else:
                break

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        attrs = extract_attributes(self._search_regex(
            r'(<nui-media[^>]+>)', webpage, 'media element'))
        video_id = attrs['videoid']
        publication_id = attrs.get('publicationid')
        if publication_id:
            video_id = publication_id + '$' + video_id

        page = (self._parse_json(self._search_regex(
            r'digitalData\s*=\s*({.+?});', webpage, 'digial data',
            default='{}'), video_id, fatal=False) or {}).get('page') or {}

        info = self._search_json_ld(webpage, display_id, default={})
        return merge_dicts(info, {
            '_type': 'url_transparent',
            'url': 'https://mediazone.vrt.be/api/v1/vrtvideo/assets/%s' % video_id,
            'ie_key': CanvasIE.ie_key(),
            'id': video_id,
            'display_id': display_id,
            'season_number': int_or_none(page.get('episode_season')),
        })


class DagelijkseKostIE(InfoExtractor):
    IE_DESC = 'dagelijksekost.een.be'
    _VALID_URL = r'https?://dagelijksekost\.een\.be/gerechten/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://dagelijksekost.een.be/gerechten/hachis-parmentier-met-witloof',
        'md5': '30bfffc323009a3e5f689bef6efa2365',
        'info_dict': {
            'id': 'md-ast-27a4d1ff-7d7b-425e-b84f-a4d227f592fa',
            'display_id': 'hachis-parmentier-met-witloof',
            'ext': 'mp4',
            'title': 'Hachis parmentier met witloof',
            'description': 'md5:9960478392d87f63567b5b117688cdc5',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 283.02,
        },
        'expected_warnings': ['is not a supported codec'],
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        title = strip_or_none(get_element_by_class(
            'dish-metadata__title', webpage
        ) or self._html_search_meta(
            'twitter:title', webpage))

        description = clean_html(get_element_by_class(
            'dish-description', webpage)
        ) or self._html_search_meta(
            ('description', 'twitter:description', 'og:description'),
            webpage)

        video_id = self._html_search_regex(
            r'data-url=(["\'])(?P<id>(?:(?!\1).)+)\1', webpage, 'video id',
            group='id')

        return {
            '_type': 'url_transparent',
            'url': 'https://mediazone.vrt.be/api/v1/dako/assets/%s' % video_id,
            'ie_key': CanvasIE.ie_key(),
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
        }

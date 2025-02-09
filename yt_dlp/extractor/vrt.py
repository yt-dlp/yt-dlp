import json
import time
import urllib.parse

from .gigya import GigyaBaseIE
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    get_element_by_class,
    get_element_html_by_class,
    int_or_none,
    join_nonempty,
    jwt_encode_hs256,
    make_archive_id,
    merge_dicts,
    parse_age_limit,
    parse_iso8601,
    str_or_none,
    strip_or_none,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class VRTBaseIE(GigyaBaseIE):
    _GEO_BYPASS = False
    _PLAYER_INFO = {
        'platform': 'desktop',
        'app': {
            'type': 'browser',
            'name': 'Chrome',
        },
        'device': 'undefined (undefined)',
        'os': {
            'name': 'Windows',
            'version': 'x86_64',
        },
        'player': {
            'name': 'VRT web player',
            'version': '2.7.4-prod-2023-04-19T06:05:45',
        },
    }
    # From https://player.vrt.be/vrtnws/js/main.js & https://player.vrt.be/ketnet/js/main.8cdb11341bcb79e4cd44.js
    _JWT_KEY_ID = '0-0Fp51UZykfaiCJrfTE3+oMI8zvDteYfPtR+2n1R+z8w='
    _JWT_SIGNING_KEY = 'b5f500d55cb44715107249ccd8a5c0136cfb2788dbb71b90a4f142423bacaf38'  # -dev
    # player-stag.vrt.be key:    d23987504521ae6fbf2716caca6700a24bb1579477b43c84e146b279de5ca595
    # player.vrt.be key:         2a9251d782700769fb856da5725daf38661874ca6f80ae7dc2b05ec1a81a24ae

    def _extract_formats_and_subtitles(self, data, video_id):
        if traverse_obj(data, 'drm'):
            self.report_drm(video_id)

        formats, subtitles = [], {}
        for target in traverse_obj(data, ('targetUrls', lambda _, v: url_or_none(v['url']) and v['type'])):
            format_type = target['type'].upper()
            format_url = target['url']
            if format_type in ('HLS', 'HLS_AES'):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', m3u8_id=format_type, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif format_type == 'HDS':
                formats.extend(self._extract_f4m_formats(
                    format_url, video_id, f4m_id=format_type, fatal=False))
            elif format_type == 'MPEG_DASH':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id=format_type, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif format_type == 'HSS':
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    format_url, video_id, ism_id='mss', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'format_id': format_type,
                    'url': format_url,
                })

        for sub in traverse_obj(data, ('subtitleUrls', lambda _, v: v['url'] and v['type'] == 'CLOSED')):
            subtitles.setdefault('nl', []).append({'url': sub['url']})

        return formats, subtitles

    def _call_api(self, video_id, client='null', id_token=None, version='v2'):
        player_info = {'exp': (round(time.time(), 3) + 900), **self._PLAYER_INFO}
        player_token = self._download_json(
            'https://media-services-public.vrt.be/vualto-video-aggregator-web/rest/external/v2/tokens',
            video_id, 'Downloading player token', headers={
                **self.geo_verification_headers(),
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'identityToken': id_token or {},
                'playerInfo': jwt_encode_hs256(player_info, self._JWT_SIGNING_KEY, headers={
                    'kid': self._JWT_KEY_ID,
                }).decode(),
            }, separators=(',', ':')).encode())['vrtPlayerToken']

        return self._download_json(
            f'https://media-services-public.vrt.be/media-aggregator/{version}/media-items/{video_id}',
            video_id, 'Downloading API JSON', query={
                'vrtPlayerToken': player_token,
                'client': client,
            }, expected_status=400)


class VRTIE(VRTBaseIE):
    IE_DESC = 'VRT NWS, Flanders News, Flandern Info and Sporza'
    _VALID_URL = r'https?://(?:www\.)?(?P<site>vrt\.be/vrtnws|sporza\.be)/[a-z]{2}/\d{4}/\d{2}/\d{2}/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.vrt.be/vrtnws/nl/2019/05/15/beelden-van-binnenkant-notre-dame-een-maand-na-de-brand/',
        'info_dict': {
            'id': 'pbs-pub-7855fc7b-1448-49bc-b073-316cb60caa71$vid-2ca50305-c38a-4762-9890-65cbd098b7bd',
            'ext': 'mp4',
            'title': 'Beelden van binnenkant Notre-Dame, één maand na de brand',
            'description': 'md5:6fd85f999b2d1841aa5568f4bf02c3ff',
            'duration': 31.2,
            'thumbnail': 'https://images.vrt.be/orig/2019/05/15/2d914d61-7710-11e9-abcc-02b7b76bf47f.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://sporza.be/nl/2019/05/15/de-belgian-cats-zijn-klaar-voor-het-ek/',
        'info_dict': {
            'id': 'pbs-pub-f2c86a46-8138-413a-a4b9-a0015a16ce2c$vid-1f112b31-e58e-4379-908d-aca6d80f8818',
            'ext': 'mp4',
            'title': 'De Belgian Cats zijn klaar voor het EK',
            'description': 'Video: De Belgian Cats zijn klaar voor het EK mét Ann Wauters | basketbal, sport in het journaal',
            'duration': 115.17,
            'thumbnail': 'https://images.vrt.be/orig/2019/05/15/11c0dba3-770e-11e9-abcc-02b7b76bf47f.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _CLIENT_MAP = {
        'vrt.be/vrtnws': 'vrtnieuws',
        'sporza.be': 'sporza',
    }

    def _real_extract(self, url):
        site, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, display_id)
        attrs = extract_attributes(get_element_html_by_class('vrtvideo', webpage) or '')

        asset_id = attrs.get('data-video-id') or attrs['data-videoid']
        publication_id = traverse_obj(attrs, 'data-publication-id', 'data-publicationid')
        if publication_id:
            asset_id = f'{publication_id}${asset_id}'
        client = traverse_obj(attrs, 'data-client-code', 'data-client') or self._CLIENT_MAP[site]

        data = self._call_api(asset_id, client)
        formats, subtitles = self._extract_formats_and_subtitles(data, asset_id)

        description = self._html_search_meta(
            ['og:description', 'twitter:description', 'description'], webpage)
        if description == '…':
            description = None

        return {
            'id': asset_id,
            'formats': formats,
            'subtitles': subtitles,
            'description': description,
            'thumbnail': url_or_none(attrs.get('data-posterimage')),
            'duration': float_or_none(attrs.get('data-duration'), 1000),
            '_old_archive_ids': [make_archive_id('Canvas', asset_id)],
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('shortDescription', {str}),
                'duration': ('duration', {float_or_none(scale=1000)}),
                'thumbnail': ('posterImageUrl', {url_or_none}),
            }),
        }


class VrtNUIE(VRTBaseIE):
    IE_DESC = 'VRT MAX'
    _VALID_URL = r'https?://(?:www\.)?vrt\.be/vrtnu/a-z/(?:[^/]+/){2}(?P<id>[^/?#&]+)'
    _TESTS = [{
        # CONTENT_IS_AGE_RESTRICTED
        'url': 'https://www.vrt.be/vrtnu/a-z/de-ideale-wereld/2023-vj/de-ideale-wereld-d20230116/',
        'info_dict': {
            'id': 'pbs-pub-855b00a8-6ce2-4032-ac4f-1fcf3ae78524$vid-d2243aa1-ec46-4e34-a55b-92568459906f',
            'ext': 'mp4',
            'title': 'Tom Waes',
            'description': 'Satirisch actualiteitenmagazine met Ella Leyers. Tom Waes is te gast.',
            'timestamp': 1673905125,
            'release_timestamp': 1673905125,
            'series': 'De ideale wereld',
            'season_id': '1672830988794',
            'episode': 'Aflevering 1',
            'episode_number': 1,
            'episode_id': '1672830988861',
            'display_id': 'de-ideale-wereld-d20230116',
            'channel': 'VRT',
            'duration': 1939.0,
            'thumbnail': 'https://images.vrt.be/orig/2023/01/10/1bb39cb3-9115-11ed-b07d-02b7b76bf47f.jpg',
            'release_date': '20230116',
            'upload_date': '20230116',
            'age_limit': 12,
        },
    }, {
        'url': 'https://www.vrt.be/vrtnu/a-z/buurman--wat-doet-u-nu-/6/buurman--wat-doet-u-nu--s6-trailer/',
        'info_dict': {
            'id': 'pbs-pub-ad4050eb-d9e5-48c2-9ec8-b6c355032361$vid-0465537a-34a8-4617-8352-4d8d983b4eee',
            'ext': 'mp4',
            'title': 'Trailer seizoen 6 \'Buurman, wat doet u nu?\'',
            'description': 'md5:197424726c61384b4e5c519f16c0cf02',
            'timestamp': 1652940000,
            'release_timestamp': 1652940000,
            'series': 'Buurman, wat doet u nu?',
            'season': 'Seizoen 6',
            'season_number': 6,
            'season_id': '1652344200907',
            'episode': 'Aflevering 0',
            'episode_number': 0,
            'episode_id': '1652951873524',
            'display_id': 'buurman--wat-doet-u-nu--s6-trailer',
            'channel': 'VRT',
            'duration': 33.13,
            'thumbnail': 'https://images.vrt.be/orig/2022/05/23/3c234d21-da83-11ec-b07d-02b7b76bf47f.jpg',
            'release_date': '20220519',
            'upload_date': '20220519',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _NETRC_MACHINE = 'vrtnu'
    _authenticated = False

    def _perform_login(self, username, password):
        auth_info = self._gigya_login({
            'APIKey': '3_0Z2HujMtiWq_pkAjgnS2Md2E11a1AwZjYiBETtwNE-EoEHDINgtnvcAOpNgmrVGy',
            'targetEnv': 'jssdk',
            'loginID': username,
            'password': password,
            'authMode': 'cookie',
        })

        if auth_info.get('errorDetails'):
            raise ExtractorError(f'Unable to login. VrtNU said: {auth_info["errorDetails"]}', expected=True)

        # Sometimes authentication fails for no good reason, retry
        for retry in self.RetryManager():
            if retry.attempt > 1:
                self._sleep(1, None)
            try:
                self._request_webpage(
                    'https://token.vrt.be/vrtnuinitlogin', None, note='Requesting XSRF Token',
                    errnote='Could not get XSRF Token', query={
                        'provider': 'site',
                        'destination': 'https://www.vrt.be/vrtnu/',
                    })
                self._request_webpage(
                    'https://login.vrt.be/perform_login', None,
                    note='Performing login', errnote='Login failed',
                    query={'client_id': 'vrtnu-site'}, data=urlencode_postdata({
                        'UID': auth_info['UID'],
                        'UIDSignature': auth_info['UIDSignature'],
                        'signatureTimestamp': auth_info['signatureTimestamp'],
                        '_csrf': self._get_cookies('https://login.vrt.be').get('OIDCXSRF').value,
                    }))
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                    retry.error = e
                    continue
                raise

        self._authenticated = True

    def _real_extract(self, url):
        display_id = self._match_id(url)
        parsed_url = urllib.parse.urlparse(url)
        details = self._download_json(
            f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path.rstrip("/")}.model.json',
            display_id, 'Downloading asset JSON', 'Unable to download asset JSON')['details']

        watch_info = traverse_obj(details, (
            'actions', lambda _, v: v['type'] == 'watch-episode', {dict}), get_all=False) or {}
        video_id = join_nonempty(
            'episodePublicationId', 'episodeVideoId', delim='$', from_dict=watch_info)
        if '$' not in video_id:
            raise ExtractorError('Unable to extract video ID')

        vrtnutoken = self._download_json(
            'https://token.vrt.be/refreshtoken', video_id, note='Retrieving vrtnutoken',
            errnote='Token refresh failed')['vrtnutoken'] if self._authenticated else None

        video_info = self._call_api(video_id, 'vrtnu-web@PROD', vrtnutoken)

        if 'title' not in video_info:
            code = video_info.get('code')
            if code in ('AUTHENTICATION_REQUIRED', 'CONTENT_IS_AGE_RESTRICTED'):
                self.raise_login_required(code, method='password')
            elif code in ('INVALID_LOCATION', 'CONTENT_AVAILABLE_ONLY_IN_BE'):
                self.raise_geo_restricted(countries=['BE'])
            elif code == 'CONTENT_AVAILABLE_ONLY_FOR_BE_RESIDENTS_AND_EXPATS':
                if not self._authenticated:
                    self.raise_login_required(code, method='password')
                self.raise_geo_restricted(countries=['BE'])
            raise ExtractorError(code, expected=True)

        formats, subtitles = self._extract_formats_and_subtitles(video_info, video_id)

        return {
            **traverse_obj(details, {
                'title': 'title',
                'description': ('description', {clean_html}),
                'timestamp': ('data', 'episode', 'onTime', 'raw', {parse_iso8601}),
                'release_timestamp': ('data', 'episode', 'onTime', 'raw', {parse_iso8601}),
                'series': ('data', 'program', 'title'),
                'season': ('data', 'season', 'title', 'value'),
                'season_number': ('data', 'season', 'title', 'raw', {int_or_none}),
                'season_id': ('data', 'season', 'id', {str_or_none}),
                'episode': ('data', 'episode', 'number', 'value', {str_or_none}),
                'episode_number': ('data', 'episode', 'number', 'raw', {int_or_none}),
                'episode_id': ('data', 'episode', 'id', {str_or_none}),
                'age_limit': ('data', 'episode', 'age', 'raw', {parse_age_limit}),
            }),
            'id': video_id,
            'display_id': display_id,
            'channel': 'VRT',
            'formats': formats,
            'duration': float_or_none(video_info.get('duration'), 1000),
            'thumbnail': url_or_none(video_info.get('posterImageUrl')),
            'subtitles': subtitles,
            '_old_archive_ids': [make_archive_id('Canvas', video_id)],
        }


class KetnetIE(VRTBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ketnet\.be/(?P<id>(?:[^/]+/)*[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.ketnet.be/kijken/m/meisjes/6/meisjes-s6a5',
        'info_dict': {
            'id': 'pbs-pub-39f8351c-a0a0-43e6-8394-205d597d6162$vid-5e306921-a9aa-4fa9-9f39-5b82c8f1028e',
            'ext': 'mp4',
            'title': 'Meisjes',
            'episode': 'Reeks 6: Week 5',
            'season': 'Reeks 6',
            'series': 'Meisjes',
            'timestamp': 1685251800,
            'upload_date': '20230528',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        video = self._download_json(
            'https://senior-bff.ketnet.be/graphql', display_id, query={
                'query': '''{
  video(id: "content/ketnet/nl/%s.model.json") {
    description
    episodeNr
    imageUrl
    mediaReference
    programTitle
    publicationDate
    seasonTitle
    subtitleVideodetail
    titleVideodetail
  }
}''' % display_id,  # noqa: UP031
            })['data']['video']

        video_id = urllib.parse.unquote(video['mediaReference'])
        data = self._call_api(video_id, 'ketnet@PROD', version='v1')
        formats, subtitles = self._extract_formats_and_subtitles(data, video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            '_old_archive_ids': [make_archive_id('Canvas', video_id)],
            **traverse_obj(video, {
                'title': ('titleVideodetail', {str}),
                'description': ('description', {str}),
                'thumbnail': ('thumbnail', {url_or_none}),
                'timestamp': ('publicationDate', {parse_iso8601}),
                'series': ('programTitle', {str}),
                'season': ('seasonTitle', {str}),
                'episode': ('subtitleVideodetail', {str}),
                'episode_number': ('episodeNr', {int_or_none}),
            }),
        }


class DagelijkseKostIE(VRTBaseIE):
    IE_DESC = 'dagelijksekost.een.be'
    _VALID_URL = r'https?://dagelijksekost\.een\.be/gerechten/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://dagelijksekost.een.be/gerechten/hachis-parmentier-met-witloof',
        'info_dict': {
            'id': 'md-ast-27a4d1ff-7d7b-425e-b84f-a4d227f592fa',
            'ext': 'mp4',
            'title': 'Hachis parmentier met witloof',
            'description': 'md5:9960478392d87f63567b5b117688cdc5',
            'display_id': 'hachis-parmentier-met-witloof',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._html_search_regex(
            r'data-url=(["\'])(?P<id>(?:(?!\1).)+)\1', webpage, 'video id', group='id')

        data = self._call_api(video_id, 'dako@prod', version='v1')
        formats, subtitles = self._extract_formats_and_subtitles(data, video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'display_id': display_id,
            'title': strip_or_none(get_element_by_class(
                'dish-metadata__title', webpage) or self._html_search_meta('twitter:title', webpage)),
            'description': clean_html(get_element_by_class(
                'dish-description', webpage)) or self._html_search_meta(
                ['description', 'twitter:description', 'og:description'], webpage),
            '_old_archive_ids': [make_archive_id('Canvas', video_id)],
        }


class Radio1BeIE(VRTBaseIE):
    _VALID_URL = r'https?://radio1\.be/(?:lees|luister/select)/(?P<id>[\w/-]+)'
    _TESTS = [{
        'url': 'https://radio1.be/luister/select/de-ochtend/komt-n-va-volgend-jaar-op-in-wallonie',
        'info_dict': {
            'id': 'eb6c22e9-544f-44f4-af39-cf8cccd29e22',
            'title': 'Komt N-VA volgend jaar op in Wallonië?',
            'display_id': 'de-ochtend/komt-n-va-volgend-jaar-op-in-wallonie',
            'description': 'md5:b374ea1c9302f38362df9dea1931468e',
            'thumbnail': r're:https?://cds\.vrt\.radio/[^/#\?&]+',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://radio1.be/lees/europese-unie-wil-onmiddellijke-humanitaire-pauze-en-duurzaam-staakt-het-vuren-in-gaza?view=web',
        'info_dict': {
            'id': '5d47f102-dbdb-4fa0-832b-26c1870311f2',
            'title': 'Europese Unie wil "onmiddellijke humanitaire pauze" en "duurzaam staakt-het-vuren" in Gaza',
            'description': 'md5:1aad1fae7d39edeffde5d3e67d276b64',
            'thumbnail': r're:https?://cds\.vrt\.radio/[^/#\?&]+',
            'display_id': 'europese-unie-wil-onmiddellijke-humanitaire-pauze-en-duurzaam-staakt-het-vuren-in-gaza',
        },
        'playlist_mincount': 1,
    }]

    def _extract_video_entries(self, next_js_data, display_id):
        video_data = traverse_obj(
            next_js_data, ((None, ('paragraphs', ...)), {lambda x: x if x['mediaReference'] else None}))
        for data in video_data:
            media_reference = data['mediaReference']
            formats, subtitles = self._extract_formats_and_subtitles(
                self._call_api(media_reference), display_id)

            yield {
                'id': media_reference,
                'formats': formats,
                'subtitles': subtitles,
                **traverse_obj(data, {
                    'title': ('title', {str}),
                    'description': ('body', {clean_html}),
                }),
            }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        next_js_data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['item']

        return self.playlist_result(
            self._extract_video_entries(next_js_data, display_id), **merge_dicts(traverse_obj(
                next_js_data, ({
                    'id': ('id', {str}),
                    'title': ('title', {str}),
                    'description': (('description', 'content'), {clean_html}),
                }), get_all=False), {
                    'display_id': display_id,
                    'title': self._html_search_meta(['name', 'og:title', 'twitter:title'], webpage),
                    'description': self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage),
                    'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage),
            }))

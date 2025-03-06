import json
import time
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    get_element_by_class,
    get_element_html_by_class,
    int_or_none,
    jwt_decode_hs256,
    jwt_encode_hs256,
    make_archive_id,
    merge_dicts,
    parse_age_limit,
    parse_duration,
    parse_iso8601,
    str_or_none,
    strip_or_none,
    traverse_obj,
    try_call,
    url_or_none,
)


class VRTBaseIE(InfoExtractor):
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
            'version': '10',
        },
        'player': {
            'name': 'VRT web player',
            'version': '5.1.1-prod-2025-02-14T08:44:16"',
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
        vrt_player_token = self._download_json(
            f'https://media-services-public.vrt.be/vualto-video-aggregator-web/rest/external/{version}/tokens',
            video_id, 'Downloading player token', 'Failed to download player token', headers={
                **self.geo_verification_headers(),
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'identityToken': id_token or '',
                'playerInfo': jwt_encode_hs256(player_info, self._JWT_SIGNING_KEY, headers={
                    'kid': self._JWT_KEY_ID,
                }).decode(),
            }, separators=(',', ':')).encode())['vrtPlayerToken']

        return self._download_json(
            f'https://media-services-public.vrt.be/media-aggregator/{version}/media-items/{video_id}',
            video_id, 'Downloading API JSON', 'Failed to download API JSON', query={
                'client': client,
                'vrtPlayerToken': vrt_player_token,
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


def jwt_is_expired(token):
    return jwt_decode_hs256(token)['exp'] - time.time() < 300


class VrtNUIE(VRTBaseIE):
    IE_DESC = 'VRT MAX'
    _VALID_URL = r'https?://(?:www\.)?vrt\.be/(?:vrtnu|vrtmax)/a-z/(?:[^/]+/){2}(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.vrt.be/vrtmax/a-z/ket---doc/trailer/ket---doc-trailer-s6/',
        'info_dict': {
            'channel': 'ketnet',
            'description': 'Neem een kijkje in de bijzondere wereld van deze Ketnetters.',
            'display_id': 'ket---doc-trailer-s6',
            'duration': 30.0,
            'episode': 'Reeks 6 volledig vanaf 3 maart',
            'episode_id': '1739450401467',
            'ext': 'mp4',
            'id': 'pbs-pub-c8a78645-5d3e-468a-89ec-6f3ed5534bd5$vid-242ddfe9-18f5-4e16-ab45-09b122a19251',
            'season': 'Trailer',
            'season_id': '1739450401467',
            'series': 'Ket & Doc',
            'thumbnail': 'https://images.vrt.be/orig/2025/02/21/63f07122-5bbd-4ca1-b42e-8565c6cd95df.jpg',
            'timestamp': 1740373200,
            'title': 'Reeks 6 volledig vanaf 3 maart',
            'upload_date': '20250224',
            '_old_archive_ids': ['canvas pbs-pub-c8a78645-5d3e-468a-89ec-6f3ed5534bd5$vid-242ddfe9-18f5-4e16-ab45-09b122a19251'],
        },
    }, {
        'url': 'https://www.vrt.be/vrtnu/a-z/taboe/3/taboe-s3a4/',
        'info_dict': {
            'channel': 'een',
            'description': 'md5:bf61345a95eca9393a95de4a7a54b5c6',
            'display_id': 'taboe-s3a4',
            'duration': 2882.02,
            'ext': 'mp4',
            'episode': 'Mensen met het syndroom van Gilles de la Tourette',
            'episode_id': '1739055911734',
            'episode_number': 4,
            'id': 'pbs-pub-f50faa3a-1778-46b6-9117-4ba85f197703$vid-547507fe-1c8b-4394-b361-21e627cbd0fd',
            'season': '3',
            'season_id': '1739055911734',
            'season_number': 3,
            'series': 'Taboe',
            'thumbnail': 'https://images.vrt.be/orig/2025/02/19/8198496c-d1ae-4bca-9a48-761cf3ea3ff2.jpg',
            'timestamp': 1740286800,
            'title': 'Mensen met het syndroom van Gilles de la Tourette',
            'upload_date': '20250223',
            '_old_archive_ids': ['canvas pbs-pub-f50faa3a-1778-46b6-9117-4ba85f197703$vid-547507fe-1c8b-4394-b361-21e627cbd0fd'],
        },
    }]
    _NETRC_MACHINE = 'vrtnu'

    _VIDEO_PAGE_QUERY = '''
    query VideoPage($pageId: ID!) {
        page(id: $pageId) {
            ... on EpisodePage {
                episode {
                    ageRaw
                    description
                    durationRaw
                    episodeNumberRaw
                    id
                    name
                    onTimeRaw
                    program {
                        title
                    }
                    season {
                        id
                        titleRaw
                    }
                    title
                }
                ldjson
                player {
                    image {
                        templateUrl
                    }
                    modes {
                        streamId
                    }
                }
            }
        }
    }
    '''

    def _fetch_refresh_token(self):
        refresh_token = self._get_refresh_token_from_cookie()
        if refresh_token and not jwt_is_expired(refresh_token):
            return refresh_token

        if not self._get_login_info()[0]:
            return

        refresh_token = self.cache.load(self._NETRC_MACHINE, 'refresh_token', default=None)
        if refresh_token and not jwt_is_expired(refresh_token):
            self.write_debug('Restored refresh token from cache')
            self._set_cookie('.www.vrt.be', 'vrtnu-site_profile_rt', refresh_token, path='/vrtmax/sso')
            return refresh_token

    def _fetch_video_token(self):
        video_token = self._get_video_token_from_cookie()
        if video_token and not jwt_is_expired(video_token):
            return video_token

        if self._get_login_info()[0]:
            video_token = self.cache.load(self._NETRC_MACHINE, 'video_token', default=None)
            if video_token and not jwt_is_expired(video_token):
                self.write_debug('Restored video token from cache')
                self._set_cookie('.www.vrt.be', 'vrtnu-site_profile_vt', video_token)
                return video_token

        refresh_token = self._fetch_refresh_token()
        if not refresh_token:
            return None

        self._download_webpage(
            'https://www.vrt.be/vrtmax/sso/login', None,
            'Refreshing video token', query={'scope': 'openid,mid'})

        video_token = self._get_video_token_from_cookie()
        if not video_token:
            self.cache.store(self._NETRC_MACHINE, 'refresh_token', None)
            self.report_warning('Refreshing of video token failed')
            return None
        if self._get_login_info()[0]:
            self.cache.store(self._NETRC_MACHINE, 'video_token', video_token)
        return video_token

    def _get_video_token_from_cookie(self):
        return try_call(lambda: self._get_cookies('https://www.vrt.be')['vrtnu-site_profile_vt'].value)

    def _get_refresh_token_from_cookie(self):
        return try_call(lambda: self._get_cookies('https://www.vrt.be/vrtmax/sso')['vrtnu-site_profile_rt'].value)

    def _perform_login(self, username, password):
        if self._fetch_refresh_token():
            self.write_debug('Refresh token already present, skipping login')
            return

        self._request_webpage(
            'https://www.vrt.be/vrtmax/sso/login', None,
            note='Getting session cookies', errnote='Failed to get session cookies')

        login_data = self._download_json(
            'https://login.vrt.be/perform_login', None, data=json.dumps({
                'clientId': 'vrtnu-site',
                'loginID': username,
                'password': password,
            }).encode(), headers={
                'Content-Type': 'application/json',
                'Oidcxsrf': self._get_cookies('https://login.vrt.be').get('OIDCXSRF').value,
            }, note='Logging in', errnote='Login failed', expected_status=403)
        if login_data.get('errorCode'):
            raise ExtractorError(f'Login failed: {login_data.get("errorMessage")}', expected=True)

        self._download_webpage(login_data['redirectUrl'], None, note='Getting access token', errnote='Failed to get access token')

        self.cache.store(self._NETRC_MACHINE, 'video_token', self._get_video_token_from_cookie())
        self.cache.store(self._NETRC_MACHINE, 'refresh_token', self._get_refresh_token_from_cookie())

    def _real_extract(self, url):
        display_id = self._match_id(url)

        metadata = self._download_json(
            'https://www.vrt.be/vrtnu-api/graphql/public/v1',
            display_id, 'Downloading asset JSON', 'Unable to download asset JSON',
            data=json.dumps({
                'operationName': 'VideoPage',
                'query': self._VIDEO_PAGE_QUERY,
                'variables': {'pageId': urllib.parse.urlparse(url).path},
            }).encode(),
            headers={
                'content-type': 'application/json',
                'x-vrt-client-name': 'WEB',
                'x-vrt-client-version': '1.5.9',
                'x-vrt-zone': 'default',
            })['data']['page']

        video_id = metadata['player']['modes'][0]['streamId']
        video_token = self._fetch_video_token()

        try:
            streaming_info = self._call_api(video_id, 'vrtnu-web@PROD', id_token=video_token)
        except ExtractorError as e:
            if not video_token and isinstance(e.cause, HTTPError) and e.cause.status == 404:
                self.raise_login_required()
            raise

        formats, subtitles = self._extract_formats_and_subtitles(streaming_info, video_id)

        code = traverse_obj(streaming_info, ('code', {str}))
        if not formats and code:
            if code in ('CONTENT_AVAILABLE_ONLY_FOR_BE_RESIDENTS', 'CONTENT_AVAILABLE_ONLY_IN_BE', 'CONTENT_UNAVAILABLE_VIA_PROXY'):
                self.raise_geo_restricted()
            elif code in ('CONTENT_AVAILABLE_ONLY_FOR_BE_RESIDENTS_AND_EXPATS', 'CONTENT_IS_AGE_RESTRICTED', 'CONTENT_REQUIRES_AUTHENTICATION'):
                self.raise_login_required()
            else:
                raise ExtractorError(f'Unable to extract formats: {code}')

        return {
            'id': video_id,
            **self._json_ld(traverse_obj(metadata, ('ldjson', ..., {json.loads})), video_id, fatal=False),
            **traverse_obj(metadata, ('episode', {
                'age_limit': ('ageRaw', {parse_age_limit}),
                'channel': ('brand', {str}),
                'description': ('description', {str}),
                'duration': ('durationRaw', {parse_duration}),
                'episode': ('title', {str}),
                'episode_id': ('id', {str_or_none}),
                'episode_number': ('episodeNumberRaw', {int_or_none}),
                'season': ('season', 'titleRaw', {str}),
                'season_id': ('id', {str_or_none}),
                'season_number': ('season', 'titleRaw', {int_or_none}),
                'series': ('program', 'title', {str}),
                'timestamp': ('onTimeRaw', {parse_iso8601}),
                'title': ('title', {str}),
            })),
            'display_id': display_id,
            'duration': float_or_none(streaming_info.get('duration'), 1000),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': url_or_none(streaming_info.get('posterImageUrl')),
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

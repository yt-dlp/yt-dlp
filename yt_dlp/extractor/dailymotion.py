import functools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    age_restricted,
    clean_html,
    extract_attributes,
    int_or_none,
    join_nonempty,
    make_archive_id,
    unescapeHTML,
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import find_elements, traverse_obj


class DailymotionBaseIE(InfoExtractor):
    _API_BASE = 'https://graphql.api.dailymotion.com'
    _BASE_URL = 'https://www.dailymotion.com'
    _FAMILY_FILTER = False
    _GEO_BYPASS = False
    _HEADERS = {
        'Content-Type': 'application/json',
        'Origin': _BASE_URL,
    }
    _NETRC_MACHINE = 'dailymotion'

    def _get_dailymotion_cookies(self):
        return self._get_cookies(self._BASE_URL)

    @staticmethod
    def _get_cookie_value(cookies, name):
        cookie = cookies.get(name)
        if cookie:
            return cookie.value

    def _set_dailymotion_cookie(self, name, value):
        self._set_cookie('www.dailymotion.com', name, value)

    def _real_initialize(self):
        cookies = self._get_dailymotion_cookies()
        ff = self._get_cookie_value(cookies, 'ff')
        self._FAMILY_FILTER = ff == 'on' if ff else age_restricted(18, self.get_param('age_limit'))
        self._set_dailymotion_cookie('ff', 'on' if self._FAMILY_FILTER else 'off')

    def _get_token(self, xid):
        cookies = self._get_dailymotion_cookies()
        token = self._get_cookie_value(cookies, 'access_token') or self._get_cookie_value(cookies, 'client_token')
        if token:
            return token

        data = {
            'client_id': 'f1a362d288c1b98099c7',
            'client_secret': 'eea605b96e01c796ff369935357eca920c5da4c5',
        }
        username, password = self._get_login_info()
        if username:
            data.update({
                'grant_type': 'password',
                'password': password,
                'username': username,
            })
        else:
            data['grant_type'] = 'client_credentials'
        try:
            token = self._download_json(
                f'{self._API_BASE}/oauth/token',
                None, 'Downloading Access Token',
                data=urlencode_postdata(data))['access_token']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError(self._parse_json(
                    e.cause.response.read().decode(), xid)['error_description'], expected=True)
            raise
        self._set_dailymotion_cookie('access_token' if username else 'client_token', token)
        return token

    def _call_api(self, object_type, xid, object_fields, note='Downloading JSON metadata', extra_params=None):
        if not self._HEADERS.get('Authorization'):
            self._HEADERS['Authorization'] = f'Bearer {self._get_token(xid)}'

        extra = f', {extra_params}' if extra_params else ''
        resp = self._download_json(
            self._API_BASE, xid, note,
            headers=self._HEADERS, data=json.dumps({
                'query': f'''{{
                  {object_type}(xid: "{xid}"{extra}) {{
                    {object_fields}
                  }}
                }}''',
            }).encode())

        obj = resp['data'][object_type]
        if not obj:
            raise ExtractorError(resp['errors'][0]['message'], expected=True)

        return obj


class DailymotionIE(DailymotionBaseIE):
    IE_NAME = 'dailymotion'
    _VALID_URL = r'''(?ix)
        (?:https?:)?//
        (?:
            dai\.ly/|
            (?:(?:www|touch|geo)\.)?dailymotion\.[a-z]{2,3}/
            (?:
                (?:(?:crawler|embed)/)?video/|
                player(?:/[\da-z]+)?\.html\?(?:video|(?P<is_playlist>playlist))=
            )
        )
        (?P<id>[^/?_&#"\']+)(?:[\w-]*\?playlist=(?P<playlist_id>x[0-9a-z]+))?
    '''
    _EMBED_REGEX = [rf'(?ix)<(?:(?:embed|iframe)[^>]+?src=|input[^>]+id=[\'"]dmcloudUrlEmissionSelect[\'"][^>]+value=)["\'](?P<url>{_VALID_URL[5:]})']
    _TESTS = [{
        'url': 'https://www.dailymotion.com/video/x5kesuj',
        'info_dict': {
            'id': 'x5kesuj',
            'ext': 'mp4',
            'title': 'Office Christmas Party Review – Jason Bateman, Olivia Munn, T.J. Miller',
            'categories': ['news'],
            'channel': 'Deadline',
            'channel_id': 'DeadlineHollywood',
            'channel_is_verified': True,
            'description': 'Office Christmas Party Review - Jason Bateman, Olivia Munn, T.J. Miller',
            'duration': 187,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1493651285,
            'upload_date': '20170501',
            'uploader': 'Deadline',
            'uploader_id': 'x1xm8ri',
        },
    }, {
        # Geo-restricted to France
        'url': 'https://www.dailymotion.com/video/xhza0o',
        'info_dict': {
            'id': 'xhza0o',
            'ext': 'mp4',
            'title': 'LISBOA : une minute avant le film',
            'categories': ['shortfilms'],
            'channel': 'FilmoTV France',
            'channel_id': 'FilmoTV',
            'channel_is_verified': True,
            'description': 'md5:8eb48604302cab2d045b88d9791b4a51',
            'duration': 68,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1302025395,
            'upload_date': '20110405',
            'uploader': 'FilmoTV France',
            'uploader_id': 'xfvuut',
        },
    }, {
        'url': 'https://www.dailymotion.com/video/x3z49k?playlist=xv4bw',
        'info_dict': {
            'id': 'x3z49k',
            'ext': 'mp4',
            'title': 'Squash (Rémi Gaillard)',
            'categories': ['fun'],
            'channel': 'Rémi Gaillard',
            'channel_id': 'nqtv',
            'channel_is_verified': True,
            'description': 'md5:abc361742376162ae3cfaba81dcf49df',
            'duration': 106,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1199661266,
            'upload_date': '20080106',
            'uploader': 'Rémi Gaillard',
            'uploader_id': 'x4r137',
        },
        'params': {'noplaylist': True},
    }, {
        'url': 'https://www.dailymotion.com/video/x3z49k?playlist=xv4bw',
        'info_dict': {
            'id': 'xv4bw',
        },
        'playlist_mincount': 23,
    }, {
        'url': 'https://geo.dailymotion.com/player.html?video=x3n92nf',
        'info_dict': {
            'id': 'x3n92nf',
            'ext': 'mp4',
            'title': 'Incendie au Ritz : Les images des pompiers de Paris',
            'categories': ['news'],
            'channel': '20Minutes',
            'channel_id': '20Minutes',
            'channel_is_verified': True,
            'description': 'md5:378bf86601da54142dc773597554cc42',
            'duration': 30,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1453203318,
            'upload_date': '20160119',
            'uploader': '20Minutes',
            'uploader_id': 'xtsy7',
        },
    }, {
        # Geo-restricted to France, Monaco, Andorra and Overseas France
        'url': 'https://geo.dailymotion.com/player/xakln.html?video=x8mjju4',
        'info_dict': {
            'id': 'x8mjju4',
            'ext': 'mp4',
            'title': 'Wimbledon : Marketa Vondrousova remporte son premier tournoi du Grand Chelem',
            'categories': ['sport'],
            'channel': 'Beinsports-FR',
            'channel_id': 'Beinsports-FR',
            'channel_is_verified': True,
            'duration': 763,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1689433092,
            'upload_date': '20230715',
            'uploader': 'Beinsports-FR',
            'uploader_id': 'x1jf2q2',
        },
    }, {
        # Private video, query: access_id
        'url': 'https://geo.dailymotion.com/player/x86gw.html?video=k46oCapRs4iikoz9DWy',
        'info_dict': {
            'id': 'x8la1te',
            'ext': 'mp4',
            'title': '2023-05-26_2023-05-26_étiennegénération',
            'categories': ['news'],
            'channel': 'Arrêt sur images',
            'channel_id': 'asi',
            'channel_is_verified': True,
            'duration': 97,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1685117572,
            'upload_date': '20230526',
            'uploader': 'Arrêt sur images',
            'uploader_id': 'x8t4yq',
            '_old_archive_ids': ['dailymotion k46oCapRs4iikoz9DWy'],
        },
    }, {
        # Playlist newest video
        'url': 'https://geo.dailymotion.com/player/xf7zn.html?playlist=x7wdsj',
        'only_matching': True,
    }, {
        'url': 'https://dai.ly/x94cnnk',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # https://geo.dailymotion.com/player/xmyye.html?video=x93blhi
        'url': 'https://www.financialounge.com/video/2024/08/01/borse-europee-in-rosso-dopo-la-fed-a-milano-volano-mediobanca-e-tim-edizione-del-1-agosto/',
        'info_dict': {
            'id': 'x93blhi',
            'ext': 'mp4',
            'title': 'OnAir - 01/08/24',
            'categories': ['news'],
            'channel': 'Financialounge',
            'channel_id': 'financialounge',
            'channel_is_verified': True,
            'duration': 217,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1722505658,
            'upload_date': '20240801',
            'uploader': 'Financialounge',
            'uploader_id': 'x2vtgmm',
        },
    }, {
        # https://geo.dailymotion.com/player/xf7zn.html?playlist=x7wdsj
        'url': 'https://www.cycleworld.com/blogs/ask-kevin/ducati-continues-to-evolve-with-v4/',
        'info_dict': {
            'id': 'x7wdsj',
        },
        'playlist_mincount': 50,
    }, {
        # https://github.com/yt-dlp/yt-dlp/pull/10843
        # https://www.dailymotion.com/crawler/video/x8u4owg
        'url': 'https://www.leparisien.fr/environnement/video-le-veloto-la-voiture-a-pedales-qui-aimerait-se-faire-une-place-sur-les-routes-09-03-2024-KCYMCPM4WFHJXMSKBUI66UNFPU.php',
        'info_dict': {
            'id': 'x8u4owg',
            'ext': 'mp4',
            'title': 'VIDÉO. Le «\xa0véloto\xa0», la voiture à pédales qui aimerait se faire une place sur les routes',
            'categories': ['news'],
            'channel': 'Le Parisien',
            'channel_id': 'leparisien',
            'channel_is_verified': True,
            'description': 'À bord du « véloto », l’alternative à la voiture pour la campagne',
            'duration': 428,
            'media_type': 'video',
            'thumbnail': r're:https?://www\.leparisien\.fr/.+\.jpg',
            'timestamp': 1709997866,
            'upload_date': '20240309',
            'uploader': 'Le Parisien',
            'uploader_id': 'x32f7b',
        },
    }, {
        # DM.player
        'url': 'https://forum.ionicframework.com/t/ionic-2-jw-player-dailymotion-player/83248',
        'info_dict': {
            'id': 'xwr14q',
            'ext': 'mp4',
            'title': 'Macklemore & Ryan Lewis - Thrift Shop (feat. Wanz)',
            'categories': ['music'],
            'channel': 'Macklemore Official',
            'channel_id': 'Macklemore-Official',
            'channel_is_verified': True,
            'description': 'md5:47fbe168b5a6ddc4a205e20dd6c841b2',
            'duration': 234,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1358177670,
            'upload_date': '20130114',
            'uploader': 'Macklemore Official',
            'uploader_id': 'x19qlwr',
        },
    }, {
        # dailymotion.createPlayer
        'url': 'https://www.cnnturk.com/tv-cnn-turk/programlar/ana-haber/ana-haber-18-kasim-2025-sali-2360418',
        'info_dict': {
            'id': 'x9u1750',
            'ext': 'mp4',
            'title': 'Ana Haber 18 Kasım 2025 Salı',
            'categories': ['news'],
            'channel': 'CNN TÜRK',
            'channel_id': 'cnnturk',
            'channel_is_verified': True,
            'description': 'md5:a5c5c78fa082852e129035ff56b4938b',
            'duration': 7342,
            'media_type': 'video',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1763509441,
            'upload_date': '20251118',
            'uploader': 'CNN TÜRK',
            'uploader_id': 'x2bu8h6',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _COMMON_MEDIA_FIELDS = '''description
      geoblockedCountries {
        allowed
      }
      xid'''

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)

        # https://developers.dailymotion.com/guides/migrate-player-embed/#web-sdk-mapping
        pattern = r'''(?sx)
            (?:DM\.player|dailymotion\.createPlayer)\(
            [^,]+,\s*{.*?video["\']?\s*:\s*["\']?(?P<id>[0-9A-Za-z]+).*?}\)\s*;
        '''
        for m in re.finditer(pattern, webpage):
            yield f'https://www.dailymotion.com/video/{m.group("id")}'

        # https://developers.dailymotion.com/guides/getting-started-with-web-sdk/#player-embed-script
        for id_type in ('playlist', 'video'):
            for item in traverse_obj(webpage, ({find_elements(
                tag='script', attr=f'data-{id_type}', value=r'x\w+', html=True, regex=True,
            )}, ..., {extract_attributes}, all, lambda _, v: url_or_none(v['src']))):
                if id_type == 'video' and item.get('data-playlist'):
                    continue
                if item_id := traverse_obj(item, (f'data-{id_type}', {str})):
                    yield update_url_query(
                        item['src'].replace('.js', '.html'), {id_type: item_id})

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url)
        video_id, is_playlist, playlist_id = self._match_valid_url(url).group('id', 'is_playlist', 'playlist_id')

        if is_playlist:  # We matched the playlist query param as video_id
            playlist_id = video_id
            video_id = None

        if playlist_id and not self.get_param('noplaylist'):
            return self.url_result(
                f'{self._BASE_URL}/playlist/{playlist_id}', DailymotionPlaylistIE)

        password = self.get_param('videopassword')
        media = self._call_api(
            'media', video_id, f'''... on Video {{
              {self._COMMON_MEDIA_FIELDS}
              hashtags {{
                edges {{
                  node {{
                    name
                  }}
                }}
              }}
            }}
            ... on Live {{
              {self._COMMON_MEDIA_FIELDS}
              isOnAir
            }}''', extra_params=f'password: "{password}"' if password else None)

        xid = media['xid']
        metadata = self._download_json(
            f'{self._BASE_URL}/player/metadata/video/{xid}', xid,
            query=traverse_obj(smuggled_data, 'query') or {'app': 'com.dailymotion.neon'})
        video_id = metadata['id']

        # https://developers.dailymotion.com/api/platform-api/errors/#access-error
        if error := metadata.get('error'):
            code = traverse_obj(error, ('code', {clean_html}, filter))
            message = traverse_obj(error, (('title', 'raw_message'), {clean_html}, any))
            if code == 'DM007':
                allowed_countries = traverse_obj(media, (
                    'geoblockedCountries', 'allowed', ..., {str}, filter, all, filter))
                self.raise_geo_restricted(msg=message, countries=allowed_countries)
            raise ExtractorError(join_nonempty(code, message, delim=': '), expected=True)

        m3u8_url = traverse_obj(metadata, ('qualities', 'auto', ..., 'url', {url_or_none}, any))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, xid, 'mp4')

        for f in formats:
            _, sep, suffix = f['format_id'].rpartition('@')
            if sep and suffix.isdigit():
                f['fps'] = int(suffix)

        for lang, subtitle in traverse_obj(metadata, (
            'subtitles', 'data', {dict.items}, ...,
        )):
            for subtitle_url in traverse_obj(subtitle, (
                'urls', ..., {url_or_none},
            )):
                subtitles.setdefault(lang, []).append({'url': subtitle_url})

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            '_old_archive_ids': [make_archive_id(self, xid)] if xid != video_id else None,
            **traverse_obj(media, {
                'description': ('description', {clean_html}, filter),
                'is_live': ('stream_type', {str}, {lambda x: x == 'live'}),
                'tags': ('hashtags', 'edges', ..., 'node', 'name', {str}, filter, all, filter),
            }),
            **traverse_obj(metadata, {
                'title': ('title', {clean_html}),
                'age_limit': ('explicit', {bool}, {lambda x: 18 if x else None}),
                'categories': ('channel', {str}, all),
                'channel_is_verified': ('partner', {bool}),
                'duration': ('duration', {int_or_none}),
                'media_type': ('media_type', {str}),
                'thumbnails': ('thumbnails', {dict.items}, lambda _, v: url_or_none(v[1]), {
                    'id': (0, {str}),
                    'height': (0, {int_or_none}),
                    'url': 1,
                }),
                'timestamp': ('created_time', {int_or_none}),
            }),
            **traverse_obj(metadata, ('owner', {
                'channel': ('screenname', {clean_html}),
                'channel_id': ('username', {str}),
                'uploader': ('screenname', {clean_html}),
                'uploader_id': ('id', {str}),
            })),
        }


class DailymotionPlaylistBaseIE(DailymotionBaseIE):
    _PAGE_SIZE = 100

    def _fetch_page(self, playlist_id, page):
        page += 1
        videos = self._call_api(
            self._OBJECT_TYPE, playlist_id,
            '''videos(allowExplicit: %s, first: %d, page: %d) {
      edges {
        node {
          xid
          url
        }
      }
    }''' % ('false' if self._FAMILY_FILTER else 'true', self._PAGE_SIZE, page),
            f'Downloading page {page}')['videos']
        for edge in videos['edges']:
            node = edge['node']
            yield self.url_result(
                node['url'], DailymotionIE.ie_key(), node['xid'])

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, playlist_id), self._PAGE_SIZE)
        return self.playlist_result(
            entries, playlist_id)


class DailymotionPlaylistIE(DailymotionPlaylistBaseIE):
    IE_NAME = 'dailymotion:playlist'
    _VALID_URL = r'(?:https?://)?(?:www\.)?dailymotion\.[a-z]{2,3}/playlist/(?P<id>x[0-9a-z]+)'
    _TESTS = [{
        'url': 'http://www.dailymotion.com/playlist/xv4bw_nqtv_sport/1#video=xl8v3q',
        'info_dict': {
            'id': 'xv4bw',
        },
        'playlist_mincount': 20,
    }]
    _OBJECT_TYPE = 'collection'

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # Look for embedded Dailymotion playlist player (#3822)
        for mobj in re.finditer(
                r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?dailymotion\.[a-z]{2,3}/widget/jukebox\?.+?)\1',
                webpage):
            for p in re.findall(r'list\[\]=/playlist/([^/]+)/', unescapeHTML(mobj.group('url'))):
                yield f'//dailymotion.com/playlist/{p}'


class DailymotionSearchIE(DailymotionPlaylistBaseIE):
    IE_NAME = 'dailymotion:search'
    _VALID_URL = r'https?://(?:www\.)?dailymotion\.[a-z]{2,3}/search/(?P<id>[^/?#]+)/videos'
    _PAGE_SIZE = 20
    _TESTS = [{
        'url': 'http://www.dailymotion.com/search/king of turtles/videos',
        'info_dict': {
            'id': 'king of turtles',
            'title': 'king of turtles',
        },
        'playlist_mincount': 0,
    }]
    _SEARCH_QUERY = 'query SEARCH_QUERY( $query: String! $page: Int $limit: Int ) { search { videos( query: $query first: $limit page: $page ) { edges { node { xid } } } } } '

    def _call_search_api(self, term, page, note):
        if not self._HEADERS.get('Authorization'):
            self._HEADERS['Authorization'] = f'Bearer {self._get_token(term)}'
        resp = self._download_json(
            self._API_BASE, None, note, data=json.dumps({
                'operationName': 'SEARCH_QUERY',
                'query': self._SEARCH_QUERY,
                'variables': {
                    'limit': 20,
                    'page': page,
                    'query': term,
                },
            }).encode(), headers=self._HEADERS)
        obj = traverse_obj(resp, ('data', 'search', {dict}))
        if not obj:
            raise ExtractorError(
                traverse_obj(resp, ('errors', 0, 'message', {str})) or 'Could not fetch search data')

        return obj

    def _fetch_page(self, term, page):
        page += 1
        response = self._call_search_api(term, page, f'Searching "{term}" page {page}')
        for xid in traverse_obj(response, ('videos', 'edges', ..., 'node', 'xid')):
            yield self.url_result(f'{self._BASE_URL}/video/{xid}', DailymotionIE, xid)

    def _real_extract(self, url):
        term = urllib.parse.unquote_plus(self._match_id(url))
        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, term), self._PAGE_SIZE), term, term)


class DailymotionUserIE(DailymotionPlaylistBaseIE):
    IE_NAME = 'dailymotion:user'
    _VALID_URL = r'https?://(?:www\.)?dailymotion\.[a-z]{2,3}/(?!(?:embed|swf|#|video|playlist|search|crawler)/)(?:(?:old/)?user/)?(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.dailymotion.com/user/nqtv',
        'info_dict': {
            'id': 'nqtv',
        },
        'playlist_mincount': 148,
    }, {
        'url': 'http://www.dailymotion.com/user/UnderProject',
        'info_dict': {
            'id': 'UnderProject',
        },
        'playlist_mincount': 1000,
        'skip': 'Takes too long time',
    }, {
        'url': 'https://www.dailymotion.com/user/nqtv',
        'info_dict': {
            'id': 'nqtv',
        },
        'playlist_mincount': 148,
        'params': {
            'age_limit': 0,
        },
    }]
    _OBJECT_TYPE = 'channel'

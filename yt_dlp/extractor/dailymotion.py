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
    traverse_obj,
    try_get,
    unescapeHTML,
    unsmuggle_url,
    update_url,
    url_or_none,
    urlencode_postdata,
)


class DailymotionBaseInfoExtractor(InfoExtractor):
    _FAMILY_FILTER = None
    _HEADERS = {
        'Content-Type': 'application/json',
        'Origin': 'https://www.dailymotion.com',
    }
    _NETRC_MACHINE = 'dailymotion'

    def _get_dailymotion_cookies(self):
        return self._get_cookies('https://www.dailymotion.com/')

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
                'https://graphql.api.dailymotion.com/oauth/token',
                None, 'Downloading Access Token',
                data=urlencode_postdata(data))['access_token']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError(self._parse_json(
                    e.cause.response.read().decode(), xid)['error_description'], expected=True)
            raise
        self._set_dailymotion_cookie('access_token' if username else 'client_token', token)
        return token

    def _call_api(self, object_type, xid, object_fields, note, filter_extra=None):
        if not self._HEADERS.get('Authorization'):
            self._HEADERS['Authorization'] = f'Bearer {self._get_token(xid)}'

        resp = self._download_json(
            'https://graphql.api.dailymotion.com/', xid, note, data=json.dumps({
                'query': '''{
  %s(xid: "%s"%s) {
    %s
  }
}''' % (object_type, xid, ', ' + filter_extra if filter_extra else '', object_fields),  # noqa: UP031
            }).encode(), headers=self._HEADERS)
        obj = resp['data'][object_type]
        if not obj:
            raise ExtractorError(resp['errors'][0]['message'], expected=True)
        return obj


class DailymotionIE(DailymotionBaseInfoExtractor):
    _VALID_URL = r'''(?ix)
                    (?:https?:)?//
                    (?:
                        dai\.ly/|
                        (?:
                            (?:(?:www|touch|geo)\.)?dailymotion\.[a-z]{2,3}|
                            (?:www\.)?lequipe\.fr
                        )/
                        (?:
                            swf/(?!video)|
                            (?:(?:crawler|embed|swf)/)?video/|
                            player(?:/[\da-z]+)?\.html\?(?:video|(?P<is_playlist>playlist))=
                        )
                    )
                    (?P<id>[^/?_&#]+)(?:[\w-]*\?playlist=(?P<playlist_id>x[0-9a-z]+))?
    '''
    IE_NAME = 'dailymotion'
    _EMBED_REGEX = [rf'(?ix)<(?:(?:embed|iframe)[^>]+?src=|input[^>]+id=[\'"]dmcloudUrlEmissionSelect[\'"][^>]+value=)["\'](?P<url>{_VALID_URL[5:]})']
    _TESTS = [{
        'url': 'http://www.dailymotion.com/video/x5kesuj_office-christmas-party-review-jason-bateman-olivia-munn-t-j-miller_news',
        'info_dict': {
            'id': 'x5kesuj',
            'ext': 'mp4',
            'title': 'Office Christmas Party Review –  Jason Bateman, Olivia Munn, T.J. Miller',
            'description': 'Office Christmas Party Review - Jason Bateman, Olivia Munn, T.J. Miller',
            'duration': 187,
            'tags': 'count:5',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1493651285,
            'upload_date': '20170501',
            'uploader': 'Deadline',
            'uploader_id': 'x1xm8ri',
            'age_limit': 0,
            'view_count': int,
            'like_count': int,
        },
    }, {
        'url': 'https://geo.dailymotion.com/player.html?video=x89eyek&mute=true',
        'info_dict': {
            'id': 'x89eyek',
            'ext': 'mp4',
            'title': 'En quête d\'esprit du 27/03/2022',
            'description': 'md5:66542b9f4df2eb23f314fc097488e553',
            'duration': 2756,
            'tags': 'count:1',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1648383669,
            'upload_date': '20220327',
            'uploader': 'CNEWS',
            'uploader_id': 'x24vth',
            'age_limit': 0,
            'view_count': int,
            'like_count': int,
        },
    }, {
        'url': 'https://www.dailymotion.com/video/x2iuewm_steam-machine-models-pricing-listed-on-steam-store-ign-news_videogames',
        'md5': '2137c41a8e78554bb09225b8eb322406',
        'info_dict': {
            'id': 'x2iuewm',
            'ext': 'mp4',
            'title': 'Steam Machine Models, Pricing Listed on Steam Store - IGN News',
            'description': 'Several come bundled with the Steam Controller.',
            'duration': 74,
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1425657362,
            'upload_date': '20150306',
            'uploader': 'IGN',
            'uploader_id': 'xijv66',
            'age_limit': 0,
            'view_count': int,
        },
        'skip': 'video gone',
    }, {
        # age-restricted video
        'url': 'http://www.dailymotion.com/video/xyh2zz_leanna-decker-cyber-girl-of-the-year-desires-nude-playboy-plus_redband',
        'md5': '0d667a7b9cebecc3c89ee93099c4159d',
        'info_dict': {
            'id': 'xyh2zz',
            'ext': 'mp4',
            'title': 'Leanna Decker - Cyber Girl Of The Year Desires Nude [Playboy Plus]',
            'uploader': 'HotWaves1012',
            'age_limit': 18,
        },
        'skip': 'video gone',
    }, {
        # geo-restricted, player v5
        'url': 'http://www.dailymotion.com/video/xhza0o',
        'only_matching': True,
    }, {
        # with subtitles
        'url': 'http://www.dailymotion.com/video/x20su5f_the-power-of-nightmares-1-the-rise-of-the-politics-of-fear-bbc-2004_news',
        'only_matching': True,
    }, {
        'url': 'http://www.dailymotion.com/swf/video/x3n92nf',
        'only_matching': True,
    }, {
        'url': 'http://www.dailymotion.com/swf/x3ss1m_funny-magic-trick-barry-and-stuart_fun',
        'only_matching': True,
    }, {
        'url': 'https://www.lequipe.fr/video/x791mem',
        'only_matching': True,
    }, {
        'url': 'https://www.lequipe.fr/video/k7MtHciueyTcrFtFKA2',
        'only_matching': True,
    }, {
        'url': 'https://www.dailymotion.com/video/x3z49k?playlist=xv4bw',
        'only_matching': True,
    }, {
        'url': 'https://geo.dailymotion.com/player/x86gw.html?video=k46oCapRs4iikoz9DWy',
        'only_matching': True,
    }, {
        'url': 'https://geo.dailymotion.com/player/xakln.html?video=x8mjju4&customConfig%5BcustomParams%5D=%2Ffr-fr%2Ftennis%2Fwimbledon-mens-singles%2Farticles-video',
        'only_matching': True,
    }, {  # playlist-only
        'url': 'https://geo.dailymotion.com/player/xf7zn.html?playlist=x7wdsj',
        'only_matching': True,
    }, {
        'url': 'https://geo.dailymotion.com/player/xmyye.html?video=x93blhi',
        'only_matching': True,
    }, {
        'url': 'https://www.dailymotion.com/crawler/video/x8u4owg',
        'only_matching': True,
    }, {
        'url': 'https://www.dailymotion.com/embed/video/x8u4owg',
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
            'description': '',
            'duration': 217,
            'timestamp': 1722505658,
            'upload_date': '20240801',
            'uploader': 'Financialounge',
            'uploader_id': 'x2vtgmm',
            'age_limit': 0,
            'tags': [],
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'view_count': int,
            'like_count': int,
        },
    }, {
        # https://geo.dailymotion.com/player/xf7zn.html?playlist=x7wdsj
        'url': 'https://www.cycleworld.com/blogs/ask-kevin/ducati-continues-to-evolve-with-v4/',
        'info_dict': {
            'id': 'x7wdsj',
        },
        'playlist_mincount': 50,
    }, {
        # https://www.dailymotion.com/crawler/video/x8u4owg
        'url': 'https://www.leparisien.fr/environnement/video-le-veloto-la-voiture-a-pedales-qui-aimerait-se-faire-une-place-sur-les-routes-09-03-2024-KCYMCPM4WFHJXMSKBUI66UNFPU.php',
        'info_dict': {
            'id': 'x8u4owg',
            'ext': 'mp4',
            'description': 'À bord du « véloto », l’alternative à la voiture pour la campagne',
            'like_count': int,
            'uploader': 'Le Parisien',
            'upload_date': '20240309',
            'view_count': int,
            'tags': 'count:7',
            'thumbnail': r're:https?://www\.leparisien\.fr/.+\.jpg',
            'timestamp': 1709997866,
            'age_limit': 0,
            'uploader_id': 'x32f7b',
            'title': 'VIDÉO. Le «\xa0véloto\xa0», la voiture à pédales qui aimerait se faire une place sur les routes',
            'duration': 428.0,
        },
    }, {
        # https://geo.dailymotion.com/player/xry80.html?video=x8vu47w
        'url': 'https://www.metatube.com/en/videos/546765/This-frogs-decorates-Christmas-tree/',
        'info_dict': {
            'id': 'x8vu47w',
            'ext': 'mp4',
            'like_count': int,
            'uploader': 'Metatube',
            'upload_date': '20240326',
            'view_count': int,
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1711496732,
            'age_limit': 0,
            'uploader_id': 'x2xpy74',
            'title': 'Está lindas ranitas ponen su arbolito',
            'duration': 28,
            'description': 'Que lindura',
            'tags': [],
        },
        'skip': 'Invalid URL',
    }, {
        # //geo.dailymotion.com/player/xysxq.html?video=k2Y4Mjp7krAF9iCuINM
        'url': 'https://lcp.fr/programmes/avant-la-catastrophe-la-naissance-de-la-dictature-nazie-1933-1936-346819',
        'info_dict': {
            'id': 'k2Y4Mjp7krAF9iCuINM',
            'ext': 'mp4',
            'title': 'Avant la catastrophe la naissance de la dictature nazie 1933 -1936',
            'description': 'md5:7b620d5e26edbe45f27bbddc1c0257c1',
            'uploader': 'LCP Assemblée nationale',
            'uploader_id': 'xbz33d',
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'duration': 3220,
            'tags': [],
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1739919947,
            'upload_date': '20250218',
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'https://forum.ionicframework.com/t/ionic-2-jw-player-dailymotion-player/83248',
        'info_dict': {
            'id': 'xwr14q',
            'ext': 'mp4',
            'title': 'Macklemore & Ryan Lewis - Thrift Shop (feat. Wanz)',
            'age_limit': 0,
            'description': 'md5:47fbe168b5a6ddc4a205e20dd6c841b2',
            'duration': 234,
            'like_count': int,
            'tags': 'count:5',
            'thumbnail': r're:https?://s[12]\.dmcdn\.net/v/.+',
            'timestamp': 1358177670,
            'upload_date': '20130114',
            'uploader': 'Macklemore Official',
            'uploader_id': 'x19qlwr',
            'view_count': int,
        },
    }]
    _GEO_BYPASS = False
    _COMMON_MEDIA_FIELDS = '''description
      geoblockedCountries {
        allowed
      }
      xid'''

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # https://developer.dailymotion.com/player#player-parameters
        yield from super()._extract_embed_urls(url, webpage)
        for mobj in re.finditer(
                r'(?s)DM\.player\([^,]+,\s*{.*?video[\'"]?\s*:\s*["\']?(?P<id>[0-9a-zA-Z]+).+?}\s*\);', webpage):
            yield 'https://www.dailymotion.com/embed/video/' + mobj.group('id')
        for mobj in re.finditer(
                r'(?s)<script [^>]*\bsrc=(["\'])(?:https?:)?//[\w-]+\.dailymotion\.com/player/(?:(?!\1).)+\1[^>]*>', webpage):
            attrs = extract_attributes(mobj.group(0))
            player_url = url_or_none(attrs.get('src'))
            if not player_url:
                continue
            player_url = player_url.replace('.js', '.html')
            if player_url.startswith('//'):
                player_url = f'https:{player_url}'
            if video_id := attrs.get('data-video'):
                query_string = f'video={video_id}'
            elif playlist_id := attrs.get('data-playlist'):
                query_string = f'playlist={playlist_id}'
            else:
                continue
            yield update_url(player_url, query=query_string)

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url)
        video_id, is_playlist, playlist_id = self._match_valid_url(url).group('id', 'is_playlist', 'playlist_id')

        if is_playlist:  # We matched the playlist query param as video_id
            playlist_id = video_id
            video_id = None

        if self._yes_playlist(playlist_id, video_id):
            return self.url_result(
                f'http://www.dailymotion.com/playlist/{playlist_id}',
                'DailymotionPlaylist', playlist_id)

        password = self.get_param('videopassword')
        media = self._call_api(
            'media', video_id, '''... on Video {
      %s
      stats {
        likes {
          total
        }
        views {
          total
        }
      }
    }
    ... on Live {
      %s
      audienceCount
      isOnAir
    }''' % (self._COMMON_MEDIA_FIELDS, self._COMMON_MEDIA_FIELDS), 'Downloading media JSON metadata',  # noqa: UP031
            'password: "{}"'.format(self.get_param('videopassword')) if password else None)
        xid = media['xid']

        metadata = self._download_json(
            'https://www.dailymotion.com/player/metadata/video/' + xid,
            xid, 'Downloading metadata JSON',
            query=traverse_obj(smuggled_data, 'query') or {'app': 'com.dailymotion.neon'})

        error = metadata.get('error')
        if error:
            title = error.get('title') or error['raw_message']
            # See https://developer.dailymotion.com/api#access-error
            if error.get('code') == 'DM007':
                allowed_countries = try_get(media, lambda x: x['geoblockedCountries']['allowed'], list)
                self.raise_geo_restricted(msg=title, countries=allowed_countries)
            raise ExtractorError(
                f'{self.IE_NAME} said: {title}', expected=True)

        title = metadata['title']
        is_live = media.get('isOnAir')
        formats = []
        subtitles = {}

        for quality, media_list in metadata['qualities'].items():
            for m in media_list:
                media_url = m.get('url')
                media_type = m.get('type')
                if not media_url or media_type == 'application/vnd.lumberjack.manifest':
                    continue
                if media_type == 'application/x-mpegURL':
                    fmt, subs = self._extract_m3u8_formats_and_subtitles(
                        media_url, video_id, 'mp4', live=is_live, m3u8_id='hls', fatal=False)
                    formats.extend(fmt)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    f = {
                        'url': media_url,
                        'format_id': 'http-' + quality,
                    }
                    m = re.search(r'/H264-(\d+)x(\d+)(?:-(60)/)?', media_url)
                    if m:
                        width, height, fps = map(int_or_none, m.groups())
                        f.update({
                            'fps': fps,
                            'height': height,
                            'width': width,
                        })
                    formats.append(f)
        for f in formats:
            f['url'] = f['url'].split('#')[0]
            if not f.get('fps') and f['format_id'].endswith('@60'):
                f['fps'] = 60

        subtitles_data = try_get(metadata, lambda x: x['subtitles']['data'], dict) or {}
        for subtitle_lang, subtitle in subtitles_data.items():
            subtitles[subtitle_lang] = [{
                'url': subtitle_url,
            } for subtitle_url in subtitle.get('urls', [])]

        thumbnails = traverse_obj(metadata, (
            ('posters', 'thumbnails'), {dict.items}, lambda _, v: url_or_none(v[1]), {
                'height': (0, {int_or_none}),
                'id': (0, {str}),
                'url': 1,
            }))

        owner = metadata.get('owner') or {}
        stats = media.get('stats') or {}
        get_count = lambda x: int_or_none(try_get(stats, lambda y: y[x + 's']['total']))

        return {
            'id': video_id,
            'title': title,
            'description': clean_html(media.get('description')),
            'thumbnails': thumbnails,
            'duration': int_or_none(metadata.get('duration')) or None,
            'timestamp': int_or_none(metadata.get('created_time')),
            'uploader': owner.get('screenname'),
            'uploader_id': owner.get('id') or metadata.get('screenname'),
            'age_limit': 18 if metadata.get('explicit') else 0,
            'tags': metadata.get('tags'),
            'view_count': get_count('view') or int_or_none(media.get('audienceCount')),
            'like_count': get_count('like'),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
        }


class DailymotionPlaylistBaseIE(DailymotionBaseInfoExtractor):
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
            'https://graphql.api.dailymotion.com/', None, note, data=json.dumps({
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
            yield self.url_result(f'https://www.dailymotion.com/video/{xid}', DailymotionIE, xid)

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

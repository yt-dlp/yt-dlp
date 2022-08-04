import functools
import json
import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    age_restricted,
    clean_html,
    int_or_none,
    traverse_obj,
    try_get,
    unescapeHTML,
    unsmuggle_url,
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

    def _call_api(self, object_type, xid, object_fields, note, filter_extra=None):
        if not self._HEADERS.get('Authorization'):
            cookies = self._get_dailymotion_cookies()
            token = self._get_cookie_value(cookies, 'access_token') or self._get_cookie_value(cookies, 'client_token')
            if not token:
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
                    if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                        raise ExtractorError(self._parse_json(
                            e.cause.read().decode(), xid)['error_description'], expected=True)
                    raise
                self._set_dailymotion_cookie('access_token' if username else 'client_token', token)
            self._HEADERS['Authorization'] = 'Bearer ' + token

        resp = self._download_json(
            'https://graphql.api.dailymotion.com/', xid, note, data=json.dumps({
                'query': '''{
  %s(xid: "%s"%s) {
    %s
  }
}''' % (object_type, xid, ', ' + filter_extra if filter_extra else '', object_fields),
            }).encode(), headers=self._HEADERS)
        obj = resp['data'][object_type]
        if not obj:
            raise ExtractorError(resp['errors'][0]['message'], expected=True)
        return obj


class DailymotionIE(DailymotionBaseInfoExtractor):
    _VALID_URL = r'''(?ix)
                    https?://
                        (?:
                            (?:(?:www|touch|geo)\.)?dailymotion\.[a-z]{2,3}/(?:(?:(?:(?:embed|swf|\#)/)|player\.html\?)?video|swf)|
                            (?:www\.)?lequipe\.fr/video
                        )
                        [/=](?P<id>[^/?_&]+)(?:.+?\bplaylist=(?P<playlist_id>x[0-9a-z]+))?
                    '''
    IE_NAME = 'dailymotion'
    _EMBED_REGEX = [r'<(?:(?:embed|iframe)[^>]+?src=|input[^>]+id=[\'"]dmcloudUrlEmissionSelect[\'"][^>]+value=)(["\'])(?P<url>(?:https?:)?//(?:www\.)?dailymotion\.com/(?:embed|swf)/video/.+?)\1']
    _TESTS = [{
        'url': 'http://www.dailymotion.com/video/x5kesuj_office-christmas-party-review-jason-bateman-olivia-munn-t-j-miller_news',
        'md5': '074b95bdee76b9e3654137aee9c79dfe',
        'info_dict': {
            'id': 'x5kesuj',
            'ext': 'mp4',
            'title': 'Office Christmas Party Review –  Jason Bateman, Olivia Munn, T.J. Miller',
            'description': 'Office Christmas Party Review -  Jason Bateman, Olivia Munn, T.J. Miller',
            'duration': 187,
            'timestamp': 1493651285,
            'upload_date': '20170501',
            'uploader': 'Deadline',
            'uploader_id': 'x1xm8ri',
            'age_limit': 0,
        },
    }, {
        'url': 'https://geo.dailymotion.com/player.html?video=x89eyek&mute=true',
        'md5': 'e2f9717c6604773f963f069ca53a07f8',
        'info_dict': {
            'id': 'x89eyek',
            'ext': 'mp4',
            'title': "En quête d'esprit du 27/03/2022",
            'description': 'md5:66542b9f4df2eb23f314fc097488e553',
            'duration': 2756,
            'timestamp': 1648383669,
            'upload_date': '20220327',
            'uploader': 'CNEWS',
            'uploader_id': 'x24vth',
            'age_limit': 0,
            'view_count': int,
            'like_count': int,
            'tags': ['en_quete_d_esprit'],
            'thumbnail': 'https://s2.dmcdn.net/v/Tncwi1YGKdvFbDuDY/x1080',
        }
    }, {
        'url': 'https://www.dailymotion.com/video/x2iuewm_steam-machine-models-pricing-listed-on-steam-store-ign-news_videogames',
        'md5': '2137c41a8e78554bb09225b8eb322406',
        'info_dict': {
            'id': 'x2iuewm',
            'ext': 'mp4',
            'title': 'Steam Machine Models, Pricing Listed on Steam Store - IGN News',
            'description': 'Several come bundled with the Steam Controller.',
            'thumbnail': r're:^https?:.*\.(?:jpg|png)$',
            'duration': 74,
            'timestamp': 1425657362,
            'upload_date': '20150306',
            'uploader': 'IGN',
            'uploader_id': 'xijv66',
            'age_limit': 0,
            'view_count': int,
        },
        'skip': 'video gone',
    }, {
        # Vevo video
        'url': 'http://www.dailymotion.com/video/x149uew_katy-perry-roar-official_musi',
        'info_dict': {
            'title': 'Roar (Official)',
            'id': 'USUV71301934',
            'ext': 'mp4',
            'uploader': 'Katy Perry',
            'upload_date': '20130905',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'VEVO is only available in some countries',
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
            yield from 'https://www.dailymotion.com/embed/video/' + mobj.group('id')

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url)
        video_id, playlist_id = self._match_valid_url(url).groups()

        if playlist_id:
            if self._yes_playlist(playlist_id, video_id):
                return self.url_result(
                    'http://www.dailymotion.com/playlist/' + playlist_id,
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
    }''' % (self._COMMON_MEDIA_FIELDS, self._COMMON_MEDIA_FIELDS), 'Downloading media JSON metadata',
            'password: "%s"' % self.get_param('videopassword') if password else None)
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
                '%s said: %s' % (self.IE_NAME, title), expected=True)

        title = metadata['title']
        is_live = media.get('isOnAir')
        formats = []
        for quality, media_list in metadata['qualities'].items():
            for m in media_list:
                media_url = m.get('url')
                media_type = m.get('type')
                if not media_url or media_type == 'application/vnd.lumberjack.manifest':
                    continue
                if media_type == 'application/x-mpegURL':
                    formats.extend(self._extract_m3u8_formats(
                        media_url, video_id, 'mp4', live=is_live, m3u8_id='hls', fatal=False))
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
        self._sort_formats(formats)

        subtitles = {}
        subtitles_data = try_get(metadata, lambda x: x['subtitles']['data'], dict) or {}
        for subtitle_lang, subtitle in subtitles_data.items():
            subtitles[subtitle_lang] = [{
                'url': subtitle_url,
            } for subtitle_url in subtitle.get('urls', [])]

        thumbnails = []
        for height, poster_url in metadata.get('posters', {}).items():
            thumbnails.append({
                'height': int_or_none(height),
                'id': height,
                'url': poster_url,
            })

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
            'Downloading page %d' % page)['videos']
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
                yield '//dailymotion.com/playlist/%s' % p


class DailymotionUserIE(DailymotionPlaylistBaseIE):
    IE_NAME = 'dailymotion:user'
    _VALID_URL = r'https?://(?:www\.)?dailymotion\.[a-z]{2,3}/(?!(?:embed|swf|#|video|playlist)/)(?:(?:old/)?user/)?(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.dailymotion.com/user/nqtv',
        'info_dict': {
            'id': 'nqtv',
        },
        'playlist_mincount': 152,
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

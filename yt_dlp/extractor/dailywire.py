import json
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    join_nonempty,
    jwt_decode_hs256,
    traverse_obj,
    url_or_none,
)


class DailyWireBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'dailywire'
    _GRAPHQL_API = 'https://v2server.dailywire.com/app/graphql'
    _GRAPHQL_QUERY = 'query currentPerson { currentPerson { id } }'
    _HEADERS = {
        'Content-Type': 'application/json',
        'apollographql-client-name': 'DW_WEBSITE',
        'Origin': 'https://www.dailywire.com',
    }

    def _perform_login(self, username, password):
        if 'Authorization' in self._HEADERS:
            return
        if username != 'access_token':
            raise ExtractorError(
                'Login using username and password is not currently supported. '
                'Use "--username access_token --password <access_token>" to login using an access token. '
                'To get your access_token: login to the website, go to Developer Tools > Storage tab > Local Storage > https://www.dailywire.com > find the Key named access_token > copy the corresponding Value', expected=True)
        try:
            # validate the token
            jwt = jwt_decode_hs256(password)
            if time.time() >= jwt['exp']:
                raise ValueError('jwt expired')
            self._HEADERS['Authorization'] = f'Bearer {password}'
            self.report_login()
        except ValueError as e:
            self.report_warning(f'Provided authorization token is invalid ({e!s}). Continuing as guest')


class DailyWireGraphQLIE(DailyWireBaseIE):
    def _get_json(self, url):
        sites_type, slug = self._match_valid_url(url).group('sites_type', 'id')
        result = self._download_json(
            self._GRAPHQL_API, slug, note='Downloading JSON from GraphQL API', fatal=False,
            data=json.dumps({'query': self._GRAPHQL_QUERY, 'variables': {'slug': slug}}, separators=(',', ':')).encode(),
            headers=self._HEADERS)
        return slug, traverse_obj(result, ('data', ('episode', 'video')))[0]

    def _real_extract(self, url):
        slug, episode_info = self._get_json(url)
        urls = traverse_obj(episode_info, [(['segments', ..., ('video', 'audio')], 'videoURL'), {url_or_none}])

        formats, subtitles = [], {}
        for url in urls:
            if determine_ext(url) != 'm3u8':
                formats.append({'url': url})
                continue
            format_, subs_ = self._extract_m3u8_formats_and_subtitles(url, slug)
            formats.extend(format_)
            self._merge_subtitles(subs_, target=subtitles)
        return {
            'id': episode_info['id'],
            'display_id': slug,
            'title': traverse_obj(episode_info, 'title', 'name'),
            'description': episode_info.get('description'),
            'creator': join_nonempty(('createdBy', 'firstName'), ('createdBy', 'lastName'), from_dict=episode_info, delim=' '),
            'duration': float_or_none(episode_info.get('duration')),
            'is_live': episode_info.get('isLive'),
            'thumbnail': traverse_obj(episode_info, 'thumbnail', 'image', expected_type=url_or_none),
            'formats': formats,
            'subtitles': subtitles,
            'series_id': traverse_obj(episode_info, ('show', 'id')),
            'series': traverse_obj(episode_info, ('show', 'name')),
        }


class DailyWireEpisodeIE(DailyWireGraphQLIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>episode)/(?P<id>[\w-]+)'
    _GRAPHQL_QUERY = '''
    query getEpisodeBySlug($slug: String!) {
      episode(where: {slug: $slug}) {
        id
        title
        slug
        description
        image
        isLive
        show {
          id
          name
        }
        segments {
          audio
          video
        }
        createdBy {
          firstName
          lastName
        }
      }
    }
    '''
    _TESTS = [{
        'url': 'https://www.dailywire.com/episode/1-fauci',
        'info_dict': {
            'id': 'ckzsl50xnqpy30850in3v4bu7',
            'ext': 'mp4',
            'display_id': '1-fauci',
            'title': '1. Fauci',
            'description': 'md5:9df630347ef85081b7e97dd30bc22853',
            'thumbnail': 'https://daily-wire-production.imgix.net/episodes/ckzsl50xnqpy30850in3v4bu7/ckzsl50xnqpy30850in3v4bu7-1648237399554.jpg',
            'creators': ['Caroline Roberts'],
            'series_id': 'ckzplm0a097fn0826r2vc3j7h',
            'series': 'China: The Enemy Within',
        },
    }, {
        'url': 'https://www.dailywire.com/episode/2-biden',
        'info_dict': {
            'id': 'ckzsldx8pqpr50a26qgy90f92',
            'ext': 'mp4',
            'display_id': '2-biden',
            'title': '2. Biden',
            'description': 'md5:23cbc63f41dc3f22d2651013ada70ce5',
            'thumbnail': 'https://daily-wire-production.imgix.net/episodes/ckzsldx8pqpr50a26qgy90f92/ckzsldx8pqpr50a26qgy90f92-1648237379060.jpg',
            'creators': ['Caroline Roberts'],
            'series_id': 'ckzplm0a097fn0826r2vc3j7h',
            'series': 'China: The Enemy Within',
        },
    }, {
        'url': 'https://www.dailywire.com/episode/ep-124-bill-maher',
        'info_dict': {
            'id': 'cl0ngbaalplc80894sfdo9edf',
            'ext': 'mp4',  # note: mp3 when anonymous user, mp4 when insider user (2025-02,)
            'display_id': 'ep-124-bill-maher',
            'title': 'Ep. 124 - Bill Maher',
            'thumbnail': 'https://daily-wire-production.imgix.net/episodes/cl0ngbaalplc80894sfdo9edf/cl0ngbaalplc80894sfdo9edf-1647065568518.jpg',
            'creators': ['Caroline Roberts'],
            'description': 'md5:adb0de584bcfa9c41374999d9e324e98',
            'series_id': 'cjzvep7270hp00786l9hwccob',
            'series': 'The Sunday Special',
        },
    }]


class DailyWireVideoIE(DailyWireGraphQLIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>videos)/(?P<id>[\w-]+)'
    _GRAPHQL_QUERY = '''
    query getVideoBySlug($slug: String!) {
      video(where: {slug: $slug}) {
        id
        name
        slug
        description
        image
        videoURL
        isLive
        createdBy {
          firstName
          lastName
        }
        captions {
          id
        }
      }
    }
    '''
    _TESTS = [{
        'url': 'https://www.dailywire.com/videos/am-i-racist',
        'info_dict': {
            'id': 'cm2owypdr2ku00970z0pl07yj',
            'ext': 'mp4',
            'display_id': 'am-i-racist',
            'thumbnail': 'https://daily-wire-production.imgix.net/videos/cm2owypdr2ku00970z0pl07yj/cm2owypdr2ku00970z0pl07yj-1732043421312.jpg',
            'description': 'md5:6c38b62c0c006aad8d01675d5a5d12b1',
            'title': 'Am I Racist?',
        },
    }, {
        'url': 'https://www.dailywire.com/videos/the-hyperions',
        'only_matching': True,
    }]


class DailyWirePodcastIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>podcasts)/(?P<podcaster>[\w-]+/(?P<id>[\w-]+))'
    _TESTS = [{
        'url': 'https://www.dailywire.com/podcasts/morning-wire/get-ready-for-recession-6-15-22',
        'info_dict': {
            'id': 'cl4f01d0w8pbe0a98ydd0cfn1',
            'ext': 'm4a',
            'display_id': 'get-ready-for-recession-6-15-22',
            'title': 'Get Ready for Recession | 6.15.22',
            'description': 'md5:c4afbadda4e1c38a4496f6d62be55634',
            'thumbnail': 'https://daily-wire-production.imgix.net/podcasts/ckx4otgd71jm508699tzb6hf4-1717620528520.png',
            'duration': 900.117667,
        },
    }]

    def _get_json(self, url):
        sites_type, slug = self._match_valid_url(url).group('sites_type', 'id')
        json_data = self._search_nextjs_data(self._download_webpage(url, slug), slug)
        return slug, traverse_obj(json_data, ('props', 'pageProps', 'episode'))

    def _real_extract(self, url):
        slug, episode_info = self._get_json(url)
        audio_id = traverse_obj(episode_info, 'audioMuxPlaybackId', 'VUsAipTrBVSgzw73SpC2DAJD401TYYwEp')

        return {
            'id': episode_info['id'],
            'url': f'https://stream.media.dailywire.com/{audio_id}/audio.m4a',
            'display_id': slug,
            'title': episode_info.get('title'),
            'duration': float_or_none(episode_info.get('duration')),
            'thumbnail': episode_info.get('thumbnail'),
            'description': episode_info.get('description'),
        }

import json
import re

from .turner import TurnerBaseIE
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    make_archive_id,
    merge_dicts,
    mimetype2ext,
    parse_duration,
    parse_qs,
    traverse_obj,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class TeamcocoBaseIE(TurnerBaseIE):
    _QUALITIES = {
        'low': (480, 272),
        'sd': (640, 360),
        'hd': (1280, 720),
        'uhd': (1920, 1080),
    }

    def _get_formats_and_subtitles(self, info, video_id):
        formats, subtitles = [], {}

        for src in traverse_obj(info, ('src', ..., {dict})):
            format_id = src.get('label')
            src_url = src.get('src')
            if re.match(r'https?:/[^/]', src_url):
                src_url = src_url.replace(':/', '://', 1)
            ext = determine_ext(src_url, mimetype2ext(src.get('type')))

            if not format_id or not src_url:
                continue
            elif format_id == 'hls' or ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    src_url, video_id, 'mp4', m3u8_id=format_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

            elif format_id in self._QUALITIES:
                if src_url.startswith('/mp4:protected/'):
                    # TODO: Correct extraction for these files
                    continue
                formats.append({
                    'url': src_url,
                    'ext': ext,
                    'format_id': format_id,
                    'width': self._QUALITIES[format_id][0],
                    'height': self._QUALITIES[format_id][1],
                })

        return formats, subtitles


class TeamcocoIE(TeamcocoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?teamcoco\.com/(?P<id>([^/]+/)*[^/?#]+)'
    _TESTS = [
        {
            'url': 'http://teamcoco.com/video/mary-kay-remote',
            'info_dict': {
                'id': '80187',
                'display_id': 'video_mary-kay-remote',
                'ext': 'mp4',
                'title': 'Conan Becomes A Mary Kay Beauty Consultant',
                'description': 'md5:9fb64e45b5aef6b2af1b67612b36c162',
                'thumbnail': 'https://teamcoco.com/image/thumb?id=80187',
                'upload_date': '20140402',
                'timestamp': 1396440000,
            },
            'params': {
                'skip_download': 'm3u8',
            },
        }, {
            'url': 'http://teamcoco.com/video/louis-ck-interview-george-w-bush',
            'info_dict': {
                'id': '19705',
                'display_id': 'video_louis-ck-interview-george-w-bush',
                'ext': 'mp4',
                'title': 'Louis C.K. Interview Pt. 1 11/3/11',
                'description': 'Louis C.K. got starstruck by George W. Bush, so what? Part one.',
                'thumbnail': 'https://teamcoco.com/image/thumb?id=19705',
                'upload_date': '20111104',
                'timestamp': 1320408000,
            },
            'params': {
                'skip_download': 'm3u8',
            },
        }, {
            'url': 'http://teamcoco.com/video/timothy-olyphant-drinking-whiskey',
            'info_dict': {
                'id': '88748',
                'display_id': 'video_timothy-olyphant-drinking-whiskey',
                'ext': 'mp4',
                'title': 'Timothy Olyphant Raises A Toast To “Justified”',
                'description': 'md5:15501f23f020e793aeca761205e42c24',
                'upload_date': '20150415',
                'timestamp': 1429099200,
                'thumbnail': 'https://teamcoco.com/image/thumb?id=88748',
            },
        }, {
            'url': 'http://teamcoco.com/video/full-episode-mon-6-1-joel-mchale-jake-tapper-and-musical-guest-courtney-barnett?playlist=x;eyJ0eXBlIjoidGFnIiwiaWQiOjl9',
            'info_dict': {
                'id': '89341',
                'ext': 'mp4',
                'title': 'Full Episode - Mon. 6/1 - Joel McHale, Jake Tapper, And Musical Guest Courtney Barnett',
                'description': 'Guests: Joel McHale, Jake Tapper, And Musical Guest Courtney Barnett',
            },
            'skip': 'This video is no longer available.',
        }, {
            'url': 'http://teamcoco.com/video/the-conan-audiencey-awards-for-04/25/18',
            'only_matching': True,
        }, {
            'url': 'http://teamcoco.com/italy/conan-jordan-schlansky-hit-the-streets-of-florence',
            'only_matching': True,
        }, {
            'url': 'http://teamcoco.com/haiti/conan-s-haitian-history-lesson',
            'only_matching': True,
        }, {
            'url': 'http://teamcoco.com/israel/conan-hits-the-streets-beaches-of-tel-aviv',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url).replace('/', '_')
        webpage = self._download_webpage(url, display_id)
        data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['pageData']
        info = merge_dicts(*traverse_obj(data, (
            'blocks', lambda _, v: v['name'] in ('meta-tags', 'video-player', 'video-info'), 'props', {dict})))

        thumbnail = traverse_obj(
            info, (('image', 'poster'), {urljoin('https://teamcoco.com/')}), get_all=False)
        video_id = traverse_obj(parse_qs(thumbnail), ('id', 0)) or display_id

        formats, subtitles = self._get_formats_and_subtitles(info, video_id)

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail,
            **traverse_obj(info, {
                'title': 'title',
                'description': (('descriptionHtml', 'description'), {clean_html}),
                'timestamp': ('publishedOn', {lambda x: f'{x} 12:00AM'}, {unified_timestamp}),
            }, get_all=False),
        }


class ConanClassicIE(TeamcocoBaseIE):
    _WORKING = False
    _VALID_URL = r'https?://(?:(?:www\.)?conanclassic|conan25\.teamcoco)\.com/(?P<id>([^/]+/)*[^/?#]+)'
    _TESTS = [{
        'url': 'https://conanclassic.com/video/ice-cube-kevin-hart-conan-share-lyft',
        'info_dict': {
            'id': '74709',
            'ext': 'mp4',
            'title': 'Ice Cube, Kevin Hart, & Conan Share A Lyft Car',
            'display_id': 'video/ice-cube-kevin-hart-conan-share-lyft',
            'description': 'The stars of "Ride Along" teach Conan how to roll around Hollywood.',
            'thumbnail': 'http://cdn.teamcococdn.com/image/640x360/lyft-5bd75f82b616c.png',
            'duration': 570.0,
            'upload_date': '20131211',
            'timestamp': 1386721620,
            '_old_archive_ids': ['teamcoco 74709'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://conan25.teamcoco.com/video/ice-cube-kevin-hart-conan-share-lyft',
        'only_matching': True,
    }]

    _GRAPHQL_QUERY = '''query find($id: ID!) {
  findRecord(id: $id) {

... on MetaInterface {
  id
  title
  teaser
  publishOn
  slug
  thumb {

... on FileInterface {
  id
  path
  preview
  mime
}

  }
}

... on Video {
  videoType
  duration
  isLive
  youtubeId
  turnerMediaId
  turnerMediaAuthToken
  airDate
}

... on Episode {
  airDate
  seasonNumber
  episodeNumber
  guestNames
}

  }
  findRecordVideoMetadata(id: $id) {
    turnerMediaId
    turnerMediaAuthToken
    duration
    src
  }
}'''

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['pageData']
        video_id = traverse_obj(
            data, ('blocks', ..., 'props', 'fieldDefs', lambda _, v: v['name'] == 'incomingVideoId', 'value'),
            ('blocks', ..., 'props', 'fields', 'incomingVideoRecord', 'id'), get_all=False)
        if not video_id:
            self.raise_no_formats('Unable to extract video ID from webpage', expected=True)

        response = self._download_json(
            'https://conanclassic.com/api/legacy/graphql', video_id, data=json.dumps({
                'query': self._GRAPHQL_QUERY,
                'variables': {'id': video_id},
            }, separators=(',', ':')).encode(), headers={
                'Content-Type': 'application/json',
            })

        info = traverse_obj(response, ('data', 'findRecord', {
            'title': 'title',
            'description': 'teaser',
            'thumbnail': ('thumb', 'preview', {url_or_none}),
            'duration': ('duration', {parse_duration}),
            'timestamp': ('publishOn', {unified_timestamp}),
        }))

        media_id = traverse_obj(
            response, ('data', ('findRecord', 'findRecordVideoMetadata'), 'turnerMediaId'), get_all=False)
        if media_id:
            token = traverse_obj(
                response, ('data', ('findRecord', 'findRecordVideoMetadata'), 'turnerMediaAuthToken'), get_all=False)
            if not token:
                raise ExtractorError('No Turner Media auth token found in API response')
            self._initialize_geo_bypass({
                'countries': ['US'],
            })
            info.update(self._extract_ngtv_info(media_id, {
                'accessToken': token,
                'accessTokenType': 'jws',
            }, None))  # TODO: the None arg needs to be the AdobePass software_statement
        else:
            formats, subtitles = self._get_formats_and_subtitles(
                traverse_obj(response, ('data', 'findRecordVideoMetadata')), video_id)
            info.update({
                'formats': formats,
                'subtitles': subtitles,
            })

        return {
            'id': video_id,
            'display_id': display_id,
            '_old_archive_ids': [make_archive_id('Teamcoco', video_id)],
            **info,
        }

# coding: utf-8
from __future__ import unicode_literals

import json

from .turner import TurnerBaseIE
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    mimetype2ext,
    parse_duration,
    parse_iso8601,
    qualities,
)


class TeamcocoIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?teamcoco\.com/(?P<id>([^/]+/)*[^/?#]+)'
    _TESTS = [
        {
            'url': 'http://teamcoco.com/video/mary-kay-remote',
            'md5': '55d532f81992f5c92046ad02fec34d7d',
            'info_dict': {
                'id': '80187',
                'ext': 'mp4',
                'title': 'Conan Becomes A Mary Kay Beauty Consultant',
                'description': 'Mary Kay is perhaps the most trusted name in female beauty, so of course Conan is a natural choice to sell their products.',
                'duration': 495.0,
                'upload_date': '20140402',
                'timestamp': 1396407600,
            }
        }, {
            'url': 'http://teamcoco.com/video/louis-ck-interview-george-w-bush',
            'md5': 'cde9ba0fa3506f5f017ce11ead928f9a',
            'info_dict': {
                'id': '19705',
                'ext': 'mp4',
                'description': 'Louis C.K. got starstruck by George W. Bush, so what? Part one.',
                'title': 'Louis C.K. Interview Pt. 1 11/3/11',
                'duration': 288,
                'upload_date': '20111104',
                'timestamp': 1320405840,
            }
        }, {
            'url': 'http://teamcoco.com/video/timothy-olyphant-drinking-whiskey',
            'info_dict': {
                'id': '88748',
                'ext': 'mp4',
                'title': 'Timothy Olyphant Raises A Toast To “Justified”',
                'description': 'md5:15501f23f020e793aeca761205e42c24',
                'upload_date': '20150415',
                'timestamp': 1429088400,
            },
            'params': {
                'skip_download': True,  # m3u8 downloads
            }
        }, {
            'url': 'http://teamcoco.com/video/full-episode-mon-6-1-joel-mchale-jake-tapper-and-musical-guest-courtney-barnett?playlist=x;eyJ0eXBlIjoidGFnIiwiaWQiOjl9',
            'info_dict': {
                'id': '89341',
                'ext': 'mp4',
                'title': 'Full Episode - Mon. 6/1 - Joel McHale, Jake Tapper, And Musical Guest Courtney Barnett',
                'description': 'Guests: Joel McHale, Jake Tapper, And Musical Guest Courtney Barnett',
            },
            'params': {
                'skip_download': True,  # m3u8 downloads
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
        }, {
            'url': 'https://conan25.teamcoco.com/video/ice-cube-kevin-hart-conan-share-lyft',
            'only_matching': True,
        }
    ]
    _RECORD_TEMPL = '''id
        title
        teaser
        publishOn
        thumb {
          preview
        }
        tags {
          name
        }
        duration
        turnerMediaId
        turnerMediaAuthToken'''

    def _graphql_call(self, query_template, object_type, object_id):
        find_object = 'find' + object_type
        return self._download_json(
            'https://teamcoco.com/graphql', object_id, data=json.dumps({
                'query': query_template % (find_object, object_id)
            }).encode(), headers={
                'Content-Type': 'application/json',
            })['data'][find_object]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        response = self._graphql_call('''{
  %%s(slug: "%%s") {
    ... on RecordSlug {
      record {
        %s
      }
    }
    ... on PageSlug {
      child {
        id
      }
    }
    ... on NotFoundSlug {
      status
    }
  }
}''' % self._RECORD_TEMPL, 'Slug', display_id)
        if response.get('status'):
            raise ExtractorError('This video is no longer available.', expected=True)

        child = response.get('child')
        if child:
            record = self._graphql_call('''{
  %%s(id: "%%s") {
    ... on Video {
      %s
    }
  }
}''' % self._RECORD_TEMPL, 'Record', child['id'])
        else:
            record = response['record']
        video_id = record['id']

        info = {
            'id': video_id,
            'display_id': display_id,
            'title': record['title'],
            'thumbnail': record.get('thumb', {}).get('preview'),
            'description': record.get('teaser'),
            'duration': parse_duration(record.get('duration')),
            'timestamp': parse_iso8601(record.get('publishOn')),
        }

        media_id = record.get('turnerMediaId')
        if media_id:
            self._initialize_geo_bypass({
                'countries': ['US'],
            })
            info.update(self._extract_ngtv_info(media_id, {
                'accessToken': record['turnerMediaAuthToken'],
                'accessTokenType': 'jws',
            }))
        else:
            video_sources = self._download_json(
                'https://teamcoco.com/_truman/d/' + video_id,
                video_id)['meta']['src']
            if isinstance(video_sources, dict):
                video_sources = video_sources.values()

            formats = []
            get_quality = qualities(['low', 'sd', 'hd', 'uhd'])
            for src in video_sources:
                if not isinstance(src, dict):
                    continue
                src_url = src.get('src')
                if not src_url:
                    continue
                format_id = src.get('label')
                ext = determine_ext(src_url, mimetype2ext(src.get('type')))
                if format_id == 'hls' or ext == 'm3u8':
                    # compat_urllib_parse.urljoin does not work here
                    if src_url.startswith('/'):
                        src_url = 'http://ht.cdn.turner.com/tbs/big/teamcoco' + src_url
                    formats.extend(self._extract_m3u8_formats(
                        src_url, video_id, 'mp4', m3u8_id=format_id, fatal=False))
                else:
                    if src_url.startswith('/mp4:protected/'):
                        # TODO Correct extraction for these files
                        continue
                    tbr = int_or_none(self._search_regex(
                        r'(\d+)k\.mp4', src_url, 'tbr', default=None))

                    formats.append({
                        'url': src_url,
                        'ext': ext,
                        'tbr': tbr,
                        'format_id': format_id,
                        'quality': get_quality(format_id),
                    })
            self._sort_formats(formats)
            info['formats'] = formats

        return info

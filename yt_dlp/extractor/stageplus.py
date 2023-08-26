import json
import uuid

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    traverse_obj,
    try_call,
    unified_timestamp,
    url_or_none,
)


class StagePlusVODConcertIE(InfoExtractor):
    _NETRC_MACHINE = 'stageplus'
    _VALID_URL = r'https?://(?:www\.)?stage-plus\.com/video/(?P<id>vod_concert_\w+)'
    _TESTS = [{
        'url': 'https://www.stage-plus.com/video/vod_concert_APNM8GRFDPHMASJKBSPJACG',
        'playlist_count': 6,
        'info_dict': {
            'id': 'vod_concert_APNM8GRFDPHMASJKBSPJACG',
            'title': 'Yuja Wang plays Rachmaninoff\'s Piano Concerto No. 2 – from Odeonsplatz',
            'description': 'md5:50f78ec180518c9bdb876bac550996fc',
            'artist': ['Yuja Wang', 'Lorenzo Viotti'],
            'upload_date': '20230331',
            'timestamp': 1680249600,
            'release_date': '20210709',
            'release_timestamp': 1625788800,
            'thumbnails': 'count:3',
        },
        'playlist': [{
            'info_dict': {
                'id': 'performance_work_A1IN4PJFE9MM2RJ3CLBMUSJBBSOJAD9O',
                'ext': 'mp4',
                'title': 'Piano Concerto No. 2 in C Minor, Op. 18',
                'description': 'md5:50f78ec180518c9bdb876bac550996fc',
                'upload_date': '20230331',
                'timestamp': 1680249600,
                'release_date': '20210709',
                'release_timestamp': 1625788800,
                'duration': 2207,
                'chapters': 'count:5',
                'artist': ['Yuja Wang'],
                'composer': ['Sergei Rachmaninoff'],
                'album': 'Yuja Wang plays Rachmaninoff\'s Piano Concerto No. 2 – from Odeonsplatz',
                'album_artist': ['Yuja Wang', 'Lorenzo Viotti'],
                'track': 'Piano Concerto No. 2 in C Minor, Op. 18',
                'track_number': 1,
                'genre': 'Instrumental Concerto',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }]

    # TODO: Prune this after livestream and/or album extractors are added
    _GRAPHQL_QUERY = '''query videoDetailPage($videoId: ID!, $sliderItemsFirst: Int = 24) {
  node(id: $videoId) {
    __typename
    ...LiveConcertFields
    ... on LiveConcert {
      artists {
        edges {
          role {
            ...RoleFields
          }
          node {
            id
            name
            sortName
          }
        }
      }
      isAtmos
      maxResolution
      groups {
        id
        name
        typeDisplayName
      }
      shortDescription
      performanceWorks {
        ...livePerformanceWorkFields
      }
      totalDuration
      sliders {
        ...contentContainerFields
      }
      vodConcert {
        __typename
        id
      }
    }
    ...VideoFields
    ... on Video {
      artists {
        edges {
          role {
            ...RoleFields
          }
          node {
            id
            name
            sortName
          }
        }
      }
      isAtmos
      maxResolution
      isLossless
      description
      productionDate
      takedownDate
      sliders {
        ...contentContainerFields
      }
    }
    ...VodConcertFields
    ... on VodConcert {
      artists {
        edges {
          role {
            ...RoleFields
          }
          node {
            id
            name
            sortName
          }
        }
      }
      isAtmos
      maxResolution
      groups {
        id
        name
        typeDisplayName
      }
      performanceWorks {
        ...PerformanceWorkFields
      }
      shortDescription
      productionDate
      takedownDate
      sliders {
        ...contentContainerFields
      }
    }
  }
}

fragment LiveConcertFields on LiveConcert {
  endTime
  id
  pictures {
    ...PictureFields
  }
  reruns {
    ...liveConcertRerunFields
  }
  publicationLevel
  startTime
  streamStartTime
  subtitle
  title
  typeDisplayName
  stream {
    ...liveStreamFields
  }
  trailerStream {
    ...streamFields
  }
  geoAccessCountries
  geoAccessMode
}

fragment PictureFields on Picture {
  id
  url
  type
}

fragment liveConcertRerunFields on LiveConcertRerun {
  streamStartTime
  endTime
  startTime
  stream {
    ...rerunStreamFields
  }
}

fragment rerunStreamFields on RerunStream {
  publicationLevel
  streamType
  url
}

fragment liveStreamFields on LiveStream {
  publicationLevel
  streamType
  url
}

fragment streamFields on Stream {
  publicationLevel
  streamType
  url
}

fragment RoleFields on Role {
  __typename
  id
  type
  displayName
}

fragment livePerformanceWorkFields on LivePerformanceWork {
  __typename
  id
  artists {
    ...artistWithRoleFields
  }
  groups {
    edges {
      node {
        id
        name
        typeDisplayName
      }
    }
  }
  work {
    ...workFields
  }
}

fragment artistWithRoleFields on ArtistWithRoleConnection {
  edges {
    role {
      ...RoleFields
    }
    node {
      id
      name
      sortName
    }
  }
}

fragment workFields on Work {
  id
  title
  movements {
    id
    title
  }
  composers {
    id
    name
  }
  genre {
    id
    title
  }
}

fragment contentContainerFields on CuratedContentContainer {
  __typename
  ...SliderFields
  ...BannerFields
}

fragment SliderFields on Slider {
  id
  headline
  items(first: $sliderItemsFirst) {
    edges {
      node {
        id
        __typename
        ...AlbumFields
        ...ArtistFields
        ...EpochFields
        ...GenreFields
        ...GroupFields
        ...LiveConcertFields
        ...PartnerFields
        ...PerformanceWorkFields
        ...VideoFields
        ...VodConcertFields
      }
    }
  }
}

fragment AlbumFields on Album {
  artistAndGroupDisplayInfo
  id
  pictures {
    ...PictureFields
  }
  title
}

fragment ArtistFields on Artist {
  id
  name
  roles {
    ...RoleFields
  }
  pictures {
    ...PictureFields
  }
}

fragment EpochFields on Epoch {
  id
  endYear
  pictures {
    ...PictureFields
  }
  startYear
  title
}

fragment GenreFields on Genre {
  id
  pictures {
    ...PictureFields
  }
  title
}

fragment GroupFields on Group {
  id
  name
  typeDisplayName
  pictures {
    ...PictureFields
  }
}

fragment PartnerFields on Partner {
  id
  name
  typeDisplayName
  subtypeDisplayName
  pictures {
    ...PictureFields
  }
}

fragment PerformanceWorkFields on PerformanceWork {
  __typename
  id
  artists {
    ...artistWithRoleFields
  }
  groups {
    edges {
      node {
        id
        name
        typeDisplayName
      }
    }
  }
  work {
    ...workFields
  }
  stream {
    ...streamFields
  }
  vodConcert {
    __typename
    id
  }
  duration
  cuePoints {
    mark
    title
  }
}

fragment VideoFields on Video {
  id
  archiveReleaseDate
  title
  subtitle
  pictures {
    ...PictureFields
  }
  stream {
    ...streamFields
  }
  trailerStream {
    ...streamFields
  }
  duration
  typeDisplayName
  duration
  geoAccessCountries
  geoAccessMode
  publicationLevel
  takedownDate
}

fragment VodConcertFields on VodConcert {
  id
  archiveReleaseDate
  pictures {
    ...PictureFields
  }
  subtitle
  title
  typeDisplayName
  totalDuration
  geoAccessCountries
  geoAccessMode
  trailerStream {
   ...streamFields
  }
  publicationLevel
  takedownDate
}

fragment BannerFields on Banner {
  description
  link
  pictures {
    ...PictureFields
  }
  title
}'''

    _TOKEN = None

    def _perform_login(self, username, password):
        auth = self._download_json('https://audience.api.stageplus.io/oauth/token', None, headers={
            'Content-Type': 'application/json',
            'Origin': 'https://www.stage-plus.com',
        }, data=json.dumps({
            'grant_type': 'password',
            'username': username,
            'password': password,
            'device_info': 'Chrome (Windows)',
            'client_device_id': str(uuid.uuid4()),
        }, separators=(',', ':')).encode(), note='Logging in')

        if auth.get('access_token'):
            self._TOKEN = auth['access_token']

    def _real_initialize(self):
        if self._TOKEN:
            return

        self._TOKEN = try_call(
            lambda: self._get_cookies('https://www.stage-plus.com/')['dgplus_access_token'].value)
        if not self._TOKEN:
            self.raise_login_required()

    def _real_extract(self, url):
        concert_id = self._match_id(url)

        data = self._download_json('https://audience.api.stageplus.io/graphql', concert_id, headers={
            'authorization': f'Bearer {self._TOKEN}',
            'content-type': 'application/json',
            'Origin': 'https://www.stage-plus.com',
        }, data=json.dumps({
            'query': self._GRAPHQL_QUERY,
            'variables': {'videoId': concert_id},
            'operationName': 'videoDetailPage'
        }, separators=(',', ':')).encode())['data']['node']

        metadata = traverse_obj(data, {
            'title': 'title',
            'description': ('shortDescription', {str}),
            'artist': ('artists', 'edges', ..., 'node', 'name'),
            'timestamp': ('archiveReleaseDate', {unified_timestamp}),
            'release_timestamp': ('productionDate', {unified_timestamp}),
        })

        thumbnails = traverse_obj(data, ('pictures', lambda _, v: url_or_none(v['url']), {
            'id': 'name',
            'url': 'url',
        })) or None

        m3u8_headers = {'jwt': self._TOKEN}

        entries = []
        for idx, video in enumerate(traverse_obj(data, (
                'performanceWorks', lambda _, v: v['id'] and url_or_none(v['stream']['url']))), 1):
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                video['stream']['url'], video['id'], 'mp4', m3u8_id='hls', headers=m3u8_headers)
            entries.append({
                'id': video['id'],
                'formats': formats,
                'subtitles': subtitles,
                'http_headers': m3u8_headers,
                'album': metadata.get('title'),
                'album_artist': metadata.get('artist'),
                'track_number': idx,
                **metadata,
                **traverse_obj(video, {
                    'title': ('work', 'title'),
                    'track': ('work', 'title'),
                    'duration': ('duration', {float_or_none}),
                    'chapters': (
                        'cuePoints', lambda _, v: float_or_none(v['mark']) is not None, {
                            'title': 'title',
                            'start_time': ('mark', {float_or_none}),
                        }),
                    'artist': ('artists', 'edges', ..., 'node', 'name'),
                    'composer': ('work', 'composers', ..., 'name'),
                    'genre': ('work', 'genre', 'title'),
                }),
            })

        return self.playlist_result(entries, concert_id, thumbnails=thumbnails, **metadata)

import re
import requests
import json
from .common import InfoExtractor
from ..utils import ExtractorError
from ..compat import compat_urlparse


class TuneInBaseIE(InfoExtractor):
    _API_BASE_URL = 'http://tunein.com/tuner/tune/'

    def _real_extract(self, url):

        content_id = self._match_id(url)

        # Use a try-except block to handle potential exceptions
        # when downloading the JSON metadata
        try:
            # Use the requests library to download the JSON metadata
            # from the TuneIn website.
            response = requests.get(
                self._API_BASE_URL + self._API_URL_QUERY % content_id
            )

            # Check the response status code to verify that the download
            # was successful
            if response.status_code == 200:
                # Use the response text as the JSON metadata
                content_info = response.text
            else:
                # If the status code is not 200, raise an ExtractorError
                # with an appropriate error message
                raise ExtractorError(
                    'Failed to download JSON metadata: HTTP %d' % response.status_code,
                    expected=True
                )
        except requests.exceptions.RequestException as e:
            # If there was an error with the request, raise an
            # ExtractorError with an appropriate error message
            raise ExtractorError(
                'Failed to download JSON metadata: %s' % str(e),
                expected=True
            )

        # Parse the JSON metadata to extract the information we need
        content_info = json.loads(content_info)
        title = content_info['Title']
        thumbnail = content_info.get('Logo')
        location = content_info.get('Location')
        streams_url = content_info.get('StreamUrl')
        content_id = self._match_id(url)

        if not streams_url:
            raise ExtractorError('No downloadable streams found', expected=True)
        if not streams_url.startswith('http://'):
            streams_url = compat_urlparse.urljoin(url, streams_url)

        streams = self._download_json(
            streams_url, content_id, note='Downloading stream data',
            transform_source=lambda s: re.sub(r'^\s*\((.*)\);\s*$', r'\1', s))['Streams']

        is_live = False

        formats = []

        for stream in streams:
            if stream.get('Type') == 'Live':
                is_live = True

            reliability = stream.get('Reliability')
            format_note = (
                f'Reliability: {reliability}%' if reliability is not None else None
            )
            formats.append({
                'preference': 0 if reliability is None or reliability > 90 else 1,
                'abr': stream.get('Bandwidth'),
                'ext': stream.get('MediaType').lower(),
                'acodec': stream.get('MediaType'),
                'vcodec': 'none',
                'url': stream.get('Url'),
                'source_preference': reliability,
                'format_note': format_note,
            })

        return {
            'id': content_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'location': location,
            'is_live': is_live,
        }


class TuneInClipIE(TuneInBaseIE):
    IE_NAME = 'tunein:clip'
    _VALID_URL = r'https?://(?:www\.)?tunein\.com/station/.*?audioClipId\=(?P<id>\d+)'
    _API_URL_QUERY = '?tuneType=AudioClip&audioclipId=%s'

    _TESTS = [{
        'url': 'http://tunein.com/station/?stationId=246119&audioClipId=816',
        'md5': '99f00d772db70efc804385c6b47f4e77',
        'info_dict': {
            'id': '816',
            'title': '32m',
            'ext': 'mp3',
        },
    }]


class TuneInStationIE(TuneInBaseIE):
    IE_NAME = 'tunein:station'
    _VALID_URL = r'https?://(?:www\.)?tunein\.com/(?:radio/.*?-s|station/.*?StationId=|embed/player/s)(?P<id>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>(?:https?://)?tunein\.com/embed/player/[pst]\d+)']
    _API_URL_QUERY = '?tuneType=Station&stationId=%s'

    @classmethod
    def suitable(cls, url):
        return False if TuneInClipIE.suitable(url) else super(TuneInStationIE, cls).suitable(url)

    _TESTS = [{
        'url': 'http://tunein.com/radio/Jazz24-885-s34682/',
        'info_dict': {
            'id': '34682',
            'title': 'Jazz 24 on 88.5 Jazz24 - KPLU-HD2',
            'ext': 'mp3',
            'location': 'Tacoma, WA',
        },
        'params': {
            'skip_download': True,  # live stream
        },
    }, {
        'url': 'http://tunein.com/embed/player/s6404/',
        'only_matching': True,
    },
        {
        'url': 'https://tunein.com/radio/BBC-World-Service-News-s24948/',
        'info_dict': {
            'id': '63219',
            'title': 'BBC World Service News',
            'ext': 'mp3',
        },
        'params': {
            'skip_download': False,
        },
    }, {
        'url': 'http://tunein.com/radio/BBC-World-Service-News-s24948/',
        'only_matching': False,
    },
        {
        'url': 'https://tunein.com/radio/979-WJLB-s29884/',
        'info_dict': {
            'id': '72932',
            'title': '97.9 WJLB',
            'ext': 'mp3',
        },
        'params': {
            'skip_download': False,
        },
    }
    ]


class TuneInProgramIE(TuneInBaseIE):
    IE_NAME = 'tunein:program'
    _VALID_URL = r'https?://(?:www\.)?tunein\.com/(?:radio/.*?-p|program/.*?ProgramId=|embed/player/p)(?P<id>\d+)'
    _API_URL_QUERY = '?tuneType=Program&programId=%s'

    _TESTS = [{
        'url': 'http://tunein.com/radio/Jazz-24-p2506/',
        'info_dict': {
            'id': '2506',
            'title': 'Jazz 24 on 91.3 WUKY-HD3',
            'ext': 'mp3',
            'location': 'Lexington, KY',
        },
        'params': {
            'skip_download': True,  # live stream
        },
    }, {
        'url': 'http://tunein.com/embed/player/p191660/',
        'only_matching': True,
    }]


class TuneInTopicIE(TuneInBaseIE):
    IE_NAME = 'tunein:topic'
    _VALID_URL = r'https?://(?:www\.)?tunein\.com/(?:topic/.*?TopicId=|embed/player/t)(?P<id>\d+)'
    _API_URL_QUERY = '?tuneType=Topic&topicId=%s'

    _TESTS = [{
        'url': 'http://tunein.com/topic/?TopicId=101830576',
        'md5': 'c31a39e6f988d188252eae7af0ef09c9',
        'info_dict': {
            'id': '101830576',
            'title': 'Votez pour moi du 29 octobre 2015 (29/10/15)',
            'ext': 'mp3',
            'location': 'Belgium',
        },
    }, {
        'url': 'http://tunein.com/embed/player/t101830576/',
        'only_matching': True,
    }]


class TuneInShortenerIE(InfoExtractor):
    IE_NAME = 'tunein:shortener'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://tun\.in/(?P<id>[A-Za-z0-9]+)'

    _TEST = {
        # test redirection
        'url': 'http://tun.in/ser7s',
        'info_dict': {
            'id': '34682',
            'title': 'Jazz 24 on 88.5 Jazz24 - KPLU-HD2',
            'ext': 'mp3',
            'location': 'Tacoma, WA',
        },
        'params': {
            'skip_download': True,  # live stream
        },
    }

    def _real_extract(self, url):
        redirect_id = self._match_id(url)
        # The server doesn't support HEAD requests
        urlh = self._request_webpage(
            url, redirect_id, note='Downloading redirect page')
        url = urlh.geturl()
        self.to_screen('Following redirect: %s' % url)
        return self.url_result(url)

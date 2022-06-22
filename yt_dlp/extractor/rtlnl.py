from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
)


class RtlNlIE(InfoExtractor):
    IE_NAME = 'rtl.nl'
    IE_DESC = 'rtl.nl and rtlxl.nl'
    _VALID_URL = r'''(?x)
        https?://(?:(?:www|static)\.)?
        (?:
            rtlxl\.nl/(?:[^\#]*\#!|programma)/[^/]+/|
            rtl\.nl/(?:(?:system/videoplayer/(?:[^/]+/)+(?:video_)?embed\.html|embed)\b.+?\buuid=|video/)|
            embed\.rtl\.nl/\#uuid=
        )
        (?P<id>[0-9a-f-]+)'''

    _TESTS = [{
        # new URL schema
        'url': 'https://www.rtlxl.nl/programma/rtl-nieuws/0bd1384d-d970-3086-98bb-5c104e10c26f',
        'md5': '490428f1187b60d714f34e1f2e3af0b6',
        'info_dict': {
            'id': '0bd1384d-d970-3086-98bb-5c104e10c26f',
            'ext': 'mp4',
            'title': 'RTL Nieuws',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'timestamp': 1593293400,
            'upload_date': '20200627',
            'duration': 661.08,
        },
    }, {
        # old URL schema
        'url': 'http://www.rtlxl.nl/#!/rtl-nieuws-132237/82b1aad1-4a14-3d7b-b554-b0aed1b2c416',
        'md5': '473d1946c1fdd050b2c0161a4b13c373',
        'info_dict': {
            'id': '82b1aad1-4a14-3d7b-b554-b0aed1b2c416',
            'ext': 'mp4',
            'title': 'RTL Nieuws',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'timestamp': 1461951000,
            'upload_date': '20160429',
            'duration': 1167.96,
        },
        'skip': '404',
    }, {
        # best format available a3t
        'url': 'http://www.rtl.nl/system/videoplayer/derden/rtlnieuws/video_embed.html#uuid=84ae5571-ac25-4225-ae0c-ef8d9efb2aed/autoplay=false',
        'md5': 'dea7474214af1271d91ef332fb8be7ea',
        'info_dict': {
            'id': '84ae5571-ac25-4225-ae0c-ef8d9efb2aed',
            'ext': 'mp4',
            'timestamp': 1424039400,
            'title': 'RTL Nieuws - Nieuwe beelden Kopenhagen: chaos direct na aanslag',
            'thumbnail': r're:^https?://screenshots\.rtl\.nl/(?:[^/]+/)*sz=[0-9]+x[0-9]+/uuid=84ae5571-ac25-4225-ae0c-ef8d9efb2aed$',
            'upload_date': '20150215',
            'description': 'Er zijn nieuwe beelden vrijgegeven die vlak na de aanslag in Kopenhagen zijn gemaakt. Op de video is goed te zien hoe omstanders zich bekommeren om één van de slachtoffers, terwijl de eerste agenten ter plaatse komen.',
        }
    }, {
        # empty synopsis and missing episodes (see https://github.com/ytdl-org/youtube-dl/issues/6275)
        # best format available nettv
        'url': 'http://www.rtl.nl/system/videoplayer/derden/rtlnieuws/video_embed.html#uuid=f536aac0-1dc3-4314-920e-3bd1c5b3811a/autoplay=false',
        'info_dict': {
            'id': 'f536aac0-1dc3-4314-920e-3bd1c5b3811a',
            'ext': 'mp4',
            'title': 'RTL Nieuws - Meer beelden van overval juwelier',
            'thumbnail': r're:^https?://screenshots\.rtl\.nl/(?:[^/]+/)*sz=[0-9]+x[0-9]+/uuid=f536aac0-1dc3-4314-920e-3bd1c5b3811a$',
            'timestamp': 1437233400,
            'upload_date': '20150718',
            'duration': 30.474,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # encrypted m3u8 streams, georestricted
        'url': 'http://www.rtlxl.nl/#!/afl-2-257632/52a74543-c504-4cde-8aa8-ec66fe8d68a7',
        'only_matching': True,
    }, {
        'url': 'http://www.rtl.nl/system/videoplayer/derden/embed.html#!/uuid=bb0353b0-d6a4-1dad-90e9-18fe75b8d1f0',
        'only_matching': True,
    }, {
        'url': 'http://rtlxl.nl/?_ga=1.204735956.572365465.1466978370#!/rtl-nieuws-132237/3c487912-023b-49ac-903e-2c5d79f8410f',
        'only_matching': True,
    }, {
        'url': 'https://www.rtl.nl/video/c603c9c2-601d-4b5e-8175-64f1e942dc7d/',
        'only_matching': True,
    }, {
        'url': 'https://static.rtl.nl/embed/?uuid=1a2970fc-5c0b-43ff-9fdc-927e39e6d1bc&autoplay=false&publicatiepunt=rtlnieuwsnl',
        'only_matching': True,
    }, {
        # new embed URL schema
        'url': 'https://embed.rtl.nl/#uuid=84ae5571-ac25-4225-ae0c-ef8d9efb2aed/autoplay=false',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        uuid = self._match_id(url)
        info = self._download_json(
            'http://www.rtl.nl/system/s4m/vfd/version=2/uuid=%s/fmt=adaptive/' % uuid,
            uuid)

        material = info['material'][0]
        title = info['abstracts'][0]['name']
        subtitle = material.get('title')
        if subtitle:
            title += ' - %s' % subtitle
        description = material.get('synopsis')

        meta = info.get('meta', {})

        videopath = material['videopath']
        m3u8_url = meta.get('videohost', 'http://manifest.us.rtl.nl') + videopath

        formats = self._extract_m3u8_formats(
            m3u8_url, uuid, 'mp4', m3u8_id='hls', fatal=False)
        self._sort_formats(formats)

        thumbnails = []

        for p in ('poster_base_url', '"thumb_base_url"'):
            if not meta.get(p):
                continue

            thumbnails.append({
                'url': self._proto_relative_url(meta[p] + uuid),
                'width': int_or_none(self._search_regex(
                    r'/sz=([0-9]+)', meta[p], 'thumbnail width', fatal=False)),
                'height': int_or_none(self._search_regex(
                    r'/sz=[0-9]+x([0-9]+)',
                    meta[p], 'thumbnail height', fatal=False))
            })

        return {
            'id': uuid,
            'title': title,
            'formats': formats,
            'timestamp': material['original_date'],
            'description': description,
            'duration': parse_duration(material.get('duration')),
            'thumbnails': thumbnails,
        }

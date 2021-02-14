# coding: utf-8
from __future__ import unicode_literals

import re
import json

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    mimetype2ext,
    str_or_none,
    try_get,
    unescapeHTML,
    unsmuggle_url,
    url_or_none,
    urljoin,
)


_ID_RE = r'(?:[0-9a-f]{32,34}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12,14})'


class MediasiteIE(InfoExtractor):
    _VALID_URL = r'(?xi)https?://[^/]+/Mediasite/(?:Play|Showcase/(?:default|livebroadcast)/Presentation)/(?P<id>%s)(?P<query>\?[^#]+|)' % _ID_RE
    _TESTS = [
        {
            'url': 'https://hitsmediaweb.h-its.org/mediasite/Play/2db6c271681e4f199af3c60d1f82869b1d',
            'info_dict': {
                'id': '2db6c271681e4f199af3c60d1f82869b1d',
                'ext': 'mp4',
                'title': 'Lecture: Tuesday, September 20, 2016 - Sir Andrew Wiles',
                'description': 'Sir Andrew Wiles: “Equations in arithmetic”\\n\\nI will describe some of the interactions between modern number theory and the problem of solving equations in rational numbers or integers\\u0027.',
                'timestamp': 1474268400.0,
                'upload_date': '20160919',
            },
        },
        {
            'url': 'http://mediasite.uib.no/Mediasite/Play/90bb363295d945d6b548c867d01181361d?catalog=a452b7df-9ae1-46b7-a3ba-aceeb285f3eb',
            'info_dict': {
                'id': '90bb363295d945d6b548c867d01181361d',
                'ext': 'mp4',
                'upload_date': '20150429',
                'title': '5) IT-forum 2015-Dag 1  - Dungbeetle -  How and why Rain created a tiny bug tracker for Unity',
                'timestamp': 1430311380.0,
            },
        },
        {
            'url': 'https://collegerama.tudelft.nl/Mediasite/Play/585a43626e544bdd97aeb71a0ec907a01d',
            'md5': '481fda1c11f67588c0d9d8fbdced4e39',
            'info_dict': {
                'id': '585a43626e544bdd97aeb71a0ec907a01d',
                'ext': 'mp4',
                'title': 'Een nieuwe wereld: waarden, bewustzijn en techniek van de mensheid 2.0.',
                'description': '',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'duration': 7713.088,
                'timestamp': 1413309600,
                'upload_date': '20141014',
            },
        },
        {
            'url': 'https://collegerama.tudelft.nl/Mediasite/Play/86a9ea9f53e149079fbdb4202b521ed21d?catalog=fd32fd35-6c99-466c-89d4-cd3c431bc8a4',
            'md5': 'ef1fdded95bdf19b12c5999949419c92',
            'info_dict': {
                'id': '86a9ea9f53e149079fbdb4202b521ed21d',
                'ext': 'wmv',
                'title': '64ste Vakantiecursus: Afvalwater',
                'description': 'md5:7fd774865cc69d972f542b157c328305',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*?)?$',
                'duration': 10853,
                'timestamp': 1326446400,
                'upload_date': '20120113',
            },
        },
        {
            'url': 'http://digitalops.sandia.gov/Mediasite/Play/24aace4429fc450fb5b38cdbf424a66e1d',
            'md5': '9422edc9b9a60151727e4b6d8bef393d',
            'info_dict': {
                'id': '24aace4429fc450fb5b38cdbf424a66e1d',
                'ext': 'mp4',
                'title': 'Xyce Software Training - Section 1',
                'description': r're:(?s)SAND Number: SAND 2013-7800.{200,}',
                'upload_date': '20120409',
                'timestamp': 1333983600,
                'duration': 7794,
            }
        },
        {
            'url': 'https://collegerama.tudelft.nl/Mediasite/Showcase/livebroadcast/Presentation/ada7020854f743c49fbb45c9ec7dbb351d',
            'only_matching': True,
        },
        {
            'url': 'https://mediasite.ntnu.no/Mediasite/Showcase/default/Presentation/7d8b913259334b688986e970fae6fcb31d',
            'only_matching': True,
        },
        {
            # dashed id
            'url': 'https://hitsmediaweb.h-its.org/mediasite/Play/2db6c271-681e-4f19-9af3-c60d1f82869b1d',
            'only_matching': True,
        }
    ]

    # look in Mediasite.Core.js (Mediasite.ContentStreamType[*])
    _STREAM_TYPES = {
        0: 'video1',  # the main video
        2: 'slide',
        3: 'presentation',
        4: 'video2',  # screencast?
        5: 'video3',
    }

    @staticmethod
    def _extract_urls(webpage):
        return [
            unescapeHTML(mobj.group('url'))
            for mobj in re.finditer(
                r'(?xi)<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:(?:https?:)?//[^/]+)?/Mediasite/Play/%s(?:\?.*?)?)\1' % _ID_RE,
                webpage)]

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})
        mobj = re.match(self._VALID_URL, url)
        resource_id = mobj.group('id')
        query = mobj.group('query')

        webpage, urlh = self._download_webpage_handle(url, resource_id)  # XXX: add UrlReferrer?
        redirect_url = urlh.geturl()

        # XXX: might have also extracted UrlReferrer and QueryString from the html
        service_path = compat_urlparse.urljoin(redirect_url, self._html_search_regex(
            r'<div[^>]+\bid=["\']ServicePath[^>]+>(.+?)</div>', webpage, resource_id,
            default='/Mediasite/PlayerService/PlayerService.svc/json'))

        player_options = self._download_json(
            '%s/GetPlayerOptions' % service_path, resource_id,
            headers={
                'Content-type': 'application/json; charset=utf-8',
                'X-Requested-With': 'XMLHttpRequest',
            },
            data=json.dumps({
                'getPlayerOptionsRequest': {
                    'ResourceId': resource_id,
                    'QueryString': query,
                    'UrlReferrer': data.get('UrlReferrer', ''),
                    'UseScreenReader': False,
                }
            }).encode('utf-8'))['d']

        presentation = player_options['Presentation']
        title = presentation['Title']

        if presentation is None:
            raise ExtractorError(
                'Mediasite says: %s' % player_options['PlayerPresentationStatusMessage'],
                expected=True)

        thumbnails = []
        formats = []
        for snum, Stream in enumerate(presentation['Streams']):
            stream_type = Stream.get('StreamType')
            if stream_type is None:
                continue

            video_urls = Stream.get('VideoUrls')
            if not isinstance(video_urls, list):
                video_urls = []

            stream_id = self._STREAM_TYPES.get(
                stream_type, 'type%u' % stream_type)

            stream_formats = []
            for unum, VideoUrl in enumerate(video_urls):
                video_url = url_or_none(VideoUrl.get('Location'))
                if not video_url:
                    continue
                # XXX: if Stream.get('CanChangeScheme', False), switch scheme to HTTP/HTTPS

                media_type = VideoUrl.get('MediaType')
                if media_type == 'SS':
                    stream_formats.extend(self._extract_ism_formats(
                        video_url, resource_id,
                        ism_id='%s-%u.%u' % (stream_id, snum, unum),
                        fatal=False))
                elif media_type == 'Dash':
                    stream_formats.extend(self._extract_mpd_formats(
                        video_url, resource_id,
                        mpd_id='%s-%u.%u' % (stream_id, snum, unum),
                        fatal=False))
                else:
                    stream_formats.append({
                        'format_id': '%s-%u.%u' % (stream_id, snum, unum),
                        'url': video_url,
                        'ext': mimetype2ext(VideoUrl.get('MimeType')),
                    })

            # TODO: if Stream['HasSlideContent']:
            # synthesise an MJPEG video stream '%s-%u.slides' % (stream_type, snum)
            # from Stream['Slides']
            # this will require writing a custom downloader...

            # disprefer 'secondary' streams
            if stream_type != 0:
                for fmt in stream_formats:
                    fmt['preference'] = -1

            thumbnail_url = Stream.get('ThumbnailUrl')
            if thumbnail_url:
                thumbnails.append({
                    'id': '%s-%u' % (stream_id, snum),
                    'url': urljoin(redirect_url, thumbnail_url),
                    'preference': -1 if stream_type != 0 else 0,
                })
            formats.extend(stream_formats)

        self._sort_formats(formats)

        # XXX: Presentation['Presenters']
        # XXX: Presentation['Transcript']

        return {
            'id': resource_id,
            'title': title,
            'description': presentation.get('Description'),
            'duration': float_or_none(presentation.get('Duration'), 1000),
            'timestamp': float_or_none(presentation.get('UnixTime'), 1000),
            'formats': formats,
            'thumbnails': thumbnails,
        }


class MediasiteCatalogIE(InfoExtractor):
    _VALID_URL = r'''(?xi)
                        (?P<url>https?://[^/]+/Mediasite)
                        /Catalog/Full/
                        (?P<catalog_id>{0})
                        (?:
                            /(?P<current_folder_id>{0})
                            /(?P<root_dynamic_folder_id>{0})
                        )?
                    '''.format(_ID_RE)
    _TESTS = [{
        'url': 'http://events7.mediasite.com/Mediasite/Catalog/Full/631f9e48530d454381549f955d08c75e21',
        'info_dict': {
            'id': '631f9e48530d454381549f955d08c75e21',
            'title': 'WCET Summit: Adaptive Learning in Higher Ed: Improving Outcomes Dynamically',
        },
        'playlist_count': 6,
        'expected_warnings': ['is not a supported codec'],
    }, {
        # with CurrentFolderId and RootDynamicFolderId
        'url': 'https://medaudio.medicine.iu.edu/Mediasite/Catalog/Full/9518c4a6c5cf4993b21cbd53e828a92521/97a9db45f7ab47428c77cd2ed74bb98f14/9518c4a6c5cf4993b21cbd53e828a92521',
        'info_dict': {
            'id': '9518c4a6c5cf4993b21cbd53e828a92521',
            'title': 'IUSM Family and Friends Sessions',
        },
        'playlist_count': 2,
    }, {
        'url': 'http://uipsyc.mediasite.com/mediasite/Catalog/Full/d5d79287c75243c58c50fef50174ec1b21',
        'only_matching': True,
    }, {
        # no AntiForgeryToken
        'url': 'https://live.libraries.psu.edu/Mediasite/Catalog/Full/8376d4b24dd1457ea3bfe4cf9163feda21',
        'only_matching': True,
    }, {
        'url': 'https://medaudio.medicine.iu.edu/Mediasite/Catalog/Full/9518c4a6c5cf4993b21cbd53e828a92521/97a9db45f7ab47428c77cd2ed74bb98f14/9518c4a6c5cf4993b21cbd53e828a92521',
        'only_matching': True,
    }, {
        # dashed id
        'url': 'http://events7.mediasite.com/Mediasite/Catalog/Full/631f9e48-530d-4543-8154-9f955d08c75e',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        mediasite_url = mobj.group('url')
        catalog_id = mobj.group('catalog_id')
        current_folder_id = mobj.group('current_folder_id') or catalog_id
        root_dynamic_folder_id = mobj.group('root_dynamic_folder_id')

        webpage = self._download_webpage(url, catalog_id)

        # AntiForgeryToken is optional (e.g. [1])
        # 1. https://live.libraries.psu.edu/Mediasite/Catalog/Full/8376d4b24dd1457ea3bfe4cf9163feda21
        anti_forgery_token = self._search_regex(
            r'AntiForgeryToken\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
            webpage, 'anti forgery token', default=None, group='value')
        if anti_forgery_token:
            anti_forgery_header = self._search_regex(
                r'AntiForgeryHeaderName\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, 'anti forgery header name',
                default='X-SOFO-AntiForgeryHeader', group='value')

        data = {
            'IsViewPage': True,
            'IsNewFolder': True,
            'AuthTicket': None,
            'CatalogId': catalog_id,
            'CurrentFolderId': current_folder_id,
            'RootDynamicFolderId': root_dynamic_folder_id,
            'ItemsPerPage': 1000,
            'PageIndex': 0,
            'PermissionMask': 'Execute',
            'CatalogSearchType': 'SearchInFolder',
            'SortBy': 'Date',
            'SortDirection': 'Descending',
            'StartDate': None,
            'EndDate': None,
            'StatusFilterList': None,
            'PreviewKey': None,
            'Tags': [],
        }

        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest',
        }
        if anti_forgery_token:
            headers[anti_forgery_header] = anti_forgery_token

        catalog = self._download_json(
            '%s/Catalog/Data/GetPresentationsForFolder' % mediasite_url,
            catalog_id, data=json.dumps(data).encode(), headers=headers)

        entries = []
        for video in catalog['PresentationDetailsList']:
            if not isinstance(video, dict):
                continue
            video_id = str_or_none(video.get('Id'))
            if not video_id:
                continue
            entries.append(self.url_result(
                '%s/Play/%s' % (mediasite_url, video_id),
                ie=MediasiteIE.ie_key(), video_id=video_id))

        title = try_get(
            catalog, lambda x: x['CurrentFolder']['Name'], compat_str)

        return self.playlist_result(entries, catalog_id, title,)


class MediasiteNamedCatalogIE(InfoExtractor):
    _VALID_URL = r'(?xi)(?P<url>https?://[^/]+/Mediasite)/Catalog/catalogs/(?P<catalog_name>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://msite.misis.ru/Mediasite/Catalog/catalogs/2016-industrial-management-skriabin-o-o',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        mediasite_url = mobj.group('url')
        catalog_name = mobj.group('catalog_name')

        webpage = self._download_webpage(url, catalog_name)

        catalog_id = self._search_regex(
            r'CatalogId\s*:\s*["\'](%s)' % _ID_RE, webpage, 'catalog id')

        return self.url_result(
            '%s/Catalog/Full/%s' % (mediasite_url, catalog_id),
            ie=MediasiteCatalogIE.ie_key(), video_id=catalog_id)

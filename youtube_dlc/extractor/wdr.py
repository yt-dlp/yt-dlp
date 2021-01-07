# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    js_to_json,
    strip_jsonp,
    try_get,
    unified_strdate,
    update_url_query,
    urlhandle_detect_ext,
    url_or_none,
)


class WDRIE(InfoExtractor):
    _VALID_URL = r'https?://deviceids-medp\.wdr\.de/ondemand/\d+/(?P<id>\d+)\.js'
    _GEO_COUNTRIES = ['DE']
    _TEST = {
        'url': 'http://deviceids-medp.wdr.de/ondemand/155/1557833.js',
        'info_dict': {
            'id': 'mdb-1557833',
            'ext': 'mp4',
            'title': 'Biathlon-Staffel verpasst Podest bei Olympia-Generalprobe',
            'upload_date': '20180112',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            url, video_id, transform_source=strip_jsonp)

        is_live = metadata.get('mediaType') == 'live'

        tracker_data = metadata['trackerData']
        title = tracker_data['trackerClipTitle']
        media_resource = metadata['mediaResource']

        formats = []
        subtitles = {}

        # check if the metadata contains a direct URL to a file
        for kind, media in media_resource.items():
            if kind == 'captionsHash':
                for ext, url in media.items():
                    subtitles.setdefault('de', []).append({
                        'url': url,
                        'ext': ext,
                    })
                continue

            if kind not in ('dflt', 'alt'):
                continue
            if not isinstance(media, dict):
                continue

            for tag_name, medium_url in media.items():
                if tag_name not in ('videoURL', 'audioURL'):
                    continue

                ext = determine_ext(medium_url)
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        medium_url, video_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls'))
                elif ext == 'f4m':
                    manifest_url = update_url_query(
                        medium_url, {'hdcore': '3.2.0', 'plugin': 'aasp-3.2.0.77.18'})
                    formats.extend(self._extract_f4m_formats(
                        manifest_url, video_id, f4m_id='hds', fatal=False))
                elif ext == 'smil':
                    formats.extend(self._extract_smil_formats(
                        medium_url, 'stream', fatal=False))
                else:
                    a_format = {
                        'url': medium_url
                    }
                    if ext == 'unknown_video':
                        urlh = self._request_webpage(
                            medium_url, video_id, note='Determining extension')
                        ext = urlhandle_detect_ext(urlh)
                        a_format['ext'] = ext
                    formats.append(a_format)

        self._sort_formats(formats)

        caption_url = media_resource.get('captionURL')
        if caption_url:
            subtitles['de'] = [{
                'url': caption_url,
                'ext': 'ttml',
            }]
        captions_hash = media_resource.get('captionsHash')
        if isinstance(captions_hash, dict):
            for ext, format_url in captions_hash.items():
                format_url = url_or_none(format_url)
                if not format_url:
                    continue
                subtitles.setdefault('de', []).append({
                    'url': format_url,
                    'ext': determine_ext(format_url, None) or ext,
                })

        return {
            'id': tracker_data.get('trackerClipId', video_id),
            'title': self._live_title(title) if is_live else title,
            'alt_title': tracker_data.get('trackerClipSubcategory'),
            'formats': formats,
            'subtitles': subtitles,
            'upload_date': unified_strdate(tracker_data.get('trackerClipAirTime')),
            'is_live': is_live,
        }


class WDRPageIE(InfoExtractor):
    _CURRENT_MAUS_URL = r'https?://(?:www\.)wdrmaus.de/(?:[^/]+/){1,2}[^/?#]+\.php5'
    _PAGE_REGEX = r'/(?:mediathek/)?(?:[^/]+/)*(?P<display_id>[^/]+)\.html'
    _VALID_URL = r'https?://(?:www\d?\.)?(?:(?:kinder\.)?wdr\d?|sportschau)\.de' + _PAGE_REGEX + '|' + _CURRENT_MAUS_URL

    _TESTS = [
        {
            'url': 'http://www1.wdr.de/mediathek/video/sendungen/doku-am-freitag/video-geheimnis-aachener-dom-100.html',
            # HDS download, MD5 is unstable
            'info_dict': {
                'id': 'mdb-1058683',
                'ext': 'flv',
                'display_id': 'doku-am-freitag/video-geheimnis-aachener-dom-100',
                'title': 'Geheimnis Aachener Dom',
                'alt_title': 'Doku am Freitag',
                'upload_date': '20160304',
                'description': 'md5:87be8ff14d8dfd7a7ee46f0299b52318',
                'is_live': False,
                'subtitles': {'de': [{
                    'url': 'http://ondemand-ww.wdr.de/medp/fsk0/105/1058683/1058683_12220974.xml',
                    'ext': 'ttml',
                }]},
            },
            'skip': 'HTTP Error 404: Not Found',
        },
        {
            'url': 'http://www1.wdr.de/mediathek/audio/wdr3/wdr3-gespraech-am-samstag/audio-schriftstellerin-juli-zeh-100.html',
            'md5': 'f4c1f96d01cf285240f53ea4309663d8',
            'info_dict': {
                'id': 'mdb-1072000',
                'ext': 'mp3',
                'display_id': 'wdr3-gespraech-am-samstag/audio-schriftstellerin-juli-zeh-100',
                'title': 'Schriftstellerin Juli Zeh',
                'alt_title': 'WDR 3 Gespräch am Samstag',
                'upload_date': '20160312',
                'description': 'md5:e127d320bc2b1f149be697ce044a3dd7',
                'is_live': False,
                'subtitles': {}
            },
            'skip': 'HTTP Error 404: Not Found',
        },
        {
            'url': 'http://www1.wdr.de/mediathek/video/live/index.html',
            'info_dict': {
                'id': 'mdb-1406149',
                'ext': 'mp4',
                'title': r're:^WDR Fernsehen im Livestream \(nur in Deutschland erreichbar\) [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
                'alt_title': 'WDR Fernsehen Live',
                'upload_date': '20150101',
                'is_live': True,
            },
            'params': {
                'skip_download': True,  # m3u8 download
            },
        },
        {
            'url': 'http://www1.wdr.de/mediathek/video/sendungen/aktuelle-stunde/aktuelle-stunde-120.html',
            'playlist_mincount': 7,
            'info_dict': {
                'id': 'aktuelle-stunde-120',
            },
        },
        {
            'url': 'http://www.wdrmaus.de/aktuelle-sendung/index.php5',
            'info_dict': {
                'id': 'mdb-1552552',
                'ext': 'mp4',
                'upload_date': 're:^[0-9]{8}$',
                'title': 're:^Die Sendung mit der Maus vom [0-9.]{10}$',
            },
            'skip': 'The id changes from week to week because of the new episode'
        },
        {
            'url': 'http://www.wdrmaus.de/filme/sachgeschichten/achterbahn.php5',
            'md5': '803138901f6368ee497b4d195bb164f2',
            'info_dict': {
                'id': 'mdb-186083',
                'ext': 'mp4',
                'upload_date': '20130919',
                'title': 'Sachgeschichte - Achterbahn ',
            },
        },
        {
            'url': 'http://www1.wdr.de/radio/player/radioplayer116~_layout-popupVersion.html',
            # Live stream, MD5 unstable
            'info_dict': {
                'id': 'mdb-869971',
                'ext': 'mp4',
                'title': r're:^COSMO Livestream [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
                'upload_date': '20160101',
            },
            'params': {
                'skip_download': True,  # m3u8 download
            }
        },
        {
            'url': 'http://www.sportschau.de/handballem2018/handball-nationalmannschaft-em-stolperstein-vorrunde-100.html',
            'info_dict': {
                'id': 'mdb-1556012',
                'ext': 'mp4',
                'title': 'DHB-Vizepräsident Bob Hanning - "Die Weltspitze ist extrem breit"',
                'upload_date': '20180111',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.sportschau.de/handballem2018/audio-vorschau---die-handball-em-startet-mit-grossem-favoritenfeld-100.html',
            'only_matching': True,
        },
        {
            'url': 'https://kinder.wdr.de/tv/die-sendung-mit-dem-elefanten/av/video-folge---astronaut-100.html',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('display_id')
        webpage = self._download_webpage(url, display_id)

        entries = []

        # Article with several videos

        # for wdr.de the data-extension is in a tag with the class "mediaLink"
        # for wdr.de radio players, in a tag with the class "wdrrPlayerPlayBtn"
        # for wdrmaus, in a tag with the class "videoButton" (previously a link
        # to the page in a multiline "videoLink"-tag)
        for mobj in re.finditer(
            r'''(?sx)class=
                    (?:
                        (["\'])(?:mediaLink|wdrrPlayerPlayBtn|videoButton)\b.*?\1[^>]+|
                        (["\'])videoLink\b.*?\2[\s]*>\n[^\n]*
                    )data-extension=(["\'])(?P<data>(?:(?!\3).)+)\3
                    ''', webpage):
            media_link_obj = self._parse_json(
                mobj.group('data'), display_id, transform_source=js_to_json,
                fatal=False)
            if not media_link_obj:
                continue
            jsonp_url = try_get(
                media_link_obj, lambda x: x['mediaObj']['url'], compat_str)
            if jsonp_url:
                entries.append(self.url_result(jsonp_url, ie=WDRIE.ie_key()))

        # Playlist (e.g. https://www1.wdr.de/mediathek/video/sendungen/aktuelle-stunde/aktuelle-stunde-120.html)
        if not entries:
            entries = [
                self.url_result(
                    compat_urlparse.urljoin(url, mobj.group('href')),
                    ie=WDRPageIE.ie_key())
                for mobj in re.finditer(
                    r'<a[^>]+\bhref=(["\'])(?P<href>(?:(?!\1).)+)\1[^>]+\bdata-extension=',
                    webpage) if re.match(self._PAGE_REGEX, mobj.group('href'))
            ]

        return self.playlist_result(entries, playlist_id=display_id)


class WDRElefantIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)wdrmaus\.de/elefantenseite/#(?P<id>.+)'
    _TEST = {
        'url': 'http://www.wdrmaus.de/elefantenseite/#folge_ostern_2015',
        'info_dict': {
            'title': 'Folge Oster-Spezial 2015',
            'id': 'mdb-1088195',
            'ext': 'mp4',
            'age_limit': None,
            'upload_date': '20150406'
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        # Table of Contents seems to always be at this address, so fetch it directly.
        # The website fetches configurationJS.php5, which links to tableOfContentsJS.php5.
        table_of_contents = self._download_json(
            'https://www.wdrmaus.de/elefantenseite/data/tableOfContentsJS.php5',
            display_id)
        if display_id not in table_of_contents:
            raise ExtractorError(
                'No entry in site\'s table of contents for this URL. '
                'Is the fragment part of the URL (after the #) correct?',
                expected=True)
        xml_metadata_path = table_of_contents[display_id]['xmlPath']
        xml_metadata = self._download_xml(
            'https://www.wdrmaus.de/elefantenseite/' + xml_metadata_path,
            display_id)
        zmdb_url_element = xml_metadata.find('./movie/zmdb_url')
        if zmdb_url_element is None:
            raise ExtractorError(
                '%s is not a video' % display_id, expected=True)
        return self.url_result(zmdb_url_element.text, ie=WDRIE.ie_key())


class WDRMobileIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://mobile-ondemand\.wdr\.de/
        .*?/fsk(?P<age_limit>[0-9]+)
        /[0-9]+/[0-9]+/
        (?P<id>[0-9]+)_(?P<title>[0-9]+)'''
    IE_NAME = 'wdr:mobile'
    _TEST = {
        'url': 'http://mobile-ondemand.wdr.de/CMS2010/mdb/ondemand/weltweit/fsk0/42/421735/421735_4283021.mp4',
        'info_dict': {
            'title': '4283021',
            'id': '421735',
            'ext': 'mp4',
            'age_limit': 0,
        },
        'skip': 'Problems with loading data.'
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        return {
            'id': mobj.group('id'),
            'title': mobj.group('title'),
            'age_limit': int(mobj.group('age_limit')),
            'url': url,
            'http_headers': {
                'User-Agent': 'mobile',
            },
        }

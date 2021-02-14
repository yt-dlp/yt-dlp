# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    js_to_json,
    parse_iso8601,
    parse_filesize,
)


class TagesschauPlayerIE(InfoExtractor):
    IE_NAME = 'tagesschau:player'
    _VALID_URL = r'https?://(?:www\.)?tagesschau\.de/multimedia/(?P<kind>audio|video)/(?P=kind)-(?P<id>\d+)~player(?:_[^/?#&]+)?\.html'

    _TESTS = [{
        'url': 'http://www.tagesschau.de/multimedia/video/video-179517~player.html',
        'md5': '8d09548d5c15debad38bee3a4d15ca21',
        'info_dict': {
            'id': '179517',
            'ext': 'mp4',
            'title': 'Marie Kristin Boese, ARD Berlin, über den zukünftigen Kurs der AfD',
            'thumbnail': r're:^https?:.*\.jpg$',
            'formats': 'mincount:6',
        },
    }, {
        'url': 'https://www.tagesschau.de/multimedia/audio/audio-29417~player.html',
        'md5': '76e6eec6ebd40740671cf0a2c88617e5',
        'info_dict': {
            'id': '29417',
            'ext': 'mp3',
            'title': 'Trabi - Bye, bye Rennpappe',
            'thumbnail': r're:^https?:.*\.jpg$',
            'formats': 'mincount:2',
        },
    }, {
        'url': 'http://www.tagesschau.de/multimedia/audio/audio-29417~player_autoplay-true.html',
        'only_matching': True,
    }]

    _FORMATS = {
        'xs': {'quality': 0},
        's': {'width': 320, 'height': 180, 'quality': 1},
        'm': {'width': 512, 'height': 288, 'quality': 2},
        'l': {'width': 960, 'height': 540, 'quality': 3},
        'xl': {'width': 1280, 'height': 720, 'quality': 4},
        'xxl': {'quality': 5},
    }

    def _extract_via_api(self, kind, video_id):
        info = self._download_json(
            'https://www.tagesschau.de/api/multimedia/{0}/{0}-{1}.json'.format(kind, video_id),
            video_id)
        title = info['headline']
        formats = []
        for media in info['mediadata']:
            for format_id, format_url in media.items():
                if determine_ext(format_url) == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, video_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id='hls'))
                else:
                    formats.append({
                        'url': format_url,
                        'format_id': format_id,
                        'vcodec': 'none' if kind == 'audio' else None,
                    })
        self._sort_formats(formats)
        timestamp = parse_iso8601(info.get('date'))
        return {
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'formats': formats,
        }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        # kind = mobj.group('kind').lower()
        # if kind == 'video':
        #     return self._extract_via_api(kind, video_id)

        # JSON api does not provide some audio formats (e.g. ogg) thus
        # extracting audio via webpage

        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage).strip()
        formats = []

        for media_json in re.findall(r'({src\s*:\s*["\']http[^}]+type\s*:[^}]+})', webpage):
            media = self._parse_json(js_to_json(media_json), video_id, fatal=False)
            if not media:
                continue
            src = media.get('src')
            if not src:
                return
            quality = media.get('quality')
            kind = media.get('type', '').split('/')[0]
            ext = determine_ext(src)
            f = {
                'url': src,
                'format_id': '%s_%s' % (quality, ext) if quality else ext,
                'ext': ext,
                'vcodec': 'none' if kind == 'audio' else None,
            }
            f.update(self._FORMATS.get(quality, {}))
            formats.append(f)

        self._sort_formats(formats)

        thumbnail = self._og_search_thumbnail(webpage)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }


class TagesschauIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tagesschau\.de/(?P<path>[^/]+/(?:[^/]+/)*?(?P<id>[^/#?]+?(?:-?[0-9]+)?))(?:~_?[^/#?]+?)?\.html'

    _TESTS = [{
        'url': 'http://www.tagesschau.de/multimedia/video/video-102143.html',
        'md5': 'f7c27a0eff3bfe8c7727e65f8fe1b1e6',
        'info_dict': {
            'id': 'video-102143',
            'ext': 'mp4',
            'title': 'Regierungsumbildung in Athen: Neue Minister in Griechenland vereidigt',
            'description': '18.07.2015 20:10 Uhr',
            'thumbnail': r're:^https?:.*\.jpg$',
        },
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/ts-5727.html',
        'md5': '3c54c1f6243d279b706bde660ceec633',
        'info_dict': {
            'id': 'ts-5727',
            'ext': 'mp4',
            'title': 'Sendung: tagesschau \t04.12.2014 20:00 Uhr',
            'description': 'md5:695c01bfd98b7e313c501386327aea59',
            'thumbnail': r're:^https?:.*\.jpg$',
        },
    }, {
        # exclusive audio
        'url': 'http://www.tagesschau.de/multimedia/audio/audio-29417.html',
        'md5': '76e6eec6ebd40740671cf0a2c88617e5',
        'info_dict': {
            'id': 'audio-29417',
            'ext': 'mp3',
            'title': 'Trabi - Bye, bye Rennpappe',
            'description': 'md5:8687dda862cbbe2cfb2df09b56341317',
            'thumbnail': r're:^https?:.*\.jpg$',
        },
    }, {
        # audio in article
        'url': 'http://www.tagesschau.de/inland/bnd-303.html',
        'md5': 'e0916c623e85fc1d2b26b78f299d3958',
        'info_dict': {
            'id': 'bnd-303',
            'ext': 'mp3',
            'title': 'Viele Baustellen für neuen BND-Chef',
            'description': 'md5:1e69a54be3e1255b2b07cdbce5bcd8b4',
            'thumbnail': r're:^https?:.*\.jpg$',
        },
    }, {
        'url': 'http://www.tagesschau.de/inland/afd-parteitag-135.html',
        'info_dict': {
            'id': 'afd-parteitag-135',
            'title': 'Möchtegern-Underdog mit Machtanspruch',
        },
        'playlist_count': 2,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/tsg-3771.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/tt-3827.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/nm-3475.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/weltspiegel-3167.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/tsvorzwanzig-959.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/bab/bab-3299~_bab-sendung-209.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/multimedia/video/video-102303~_bab-sendung-211.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tagesschau.de/100sekunden/index.html',
        'only_matching': True,
    }, {
        # playlist article with collapsing sections
        'url': 'http://www.tagesschau.de/wirtschaft/faq-freihandelszone-eu-usa-101.html',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if TagesschauPlayerIE.suitable(url) else super(TagesschauIE, cls).suitable(url)

    def _extract_formats(self, download_text, media_kind):
        links = re.finditer(
            r'<div class="button" title="(?P<title>[^"]*)"><a href="(?P<url>[^"]+)">(?P<name>.+?)</a></div>',
            download_text)
        formats = []
        for l in links:
            link_url = l.group('url')
            if not link_url:
                continue
            format_id = self._search_regex(
                r'.*/[^/.]+\.([^/]+)\.[^/.]+$', link_url, 'format ID',
                default=determine_ext(link_url))
            format = {
                'format_id': format_id,
                'url': l.group('url'),
                'format_name': l.group('name'),
            }
            title = l.group('title')
            if title:
                if media_kind.lower() == 'video':
                    m = re.match(
                        r'''(?x)
                            Video:\s*(?P<vcodec>[a-zA-Z0-9/._-]+)\s*&\#10;
                            (?P<width>[0-9]+)x(?P<height>[0-9]+)px&\#10;
                            (?P<vbr>[0-9]+)kbps&\#10;
                            Audio:\s*(?P<abr>[0-9]+)kbps,\s*(?P<audio_desc>[A-Za-z\.0-9]+)&\#10;
                            Gr&ouml;&szlig;e:\s*(?P<filesize_approx>[0-9.,]+\s+[a-zA-Z]*B)''',
                        title)
                    if m:
                        format.update({
                            'format_note': m.group('audio_desc'),
                            'vcodec': m.group('vcodec'),
                            'width': int(m.group('width')),
                            'height': int(m.group('height')),
                            'abr': int(m.group('abr')),
                            'vbr': int(m.group('vbr')),
                            'filesize_approx': parse_filesize(m.group('filesize_approx')),
                        })
                else:
                    m = re.match(
                        r'(?P<format>.+?)-Format\s*:\s*(?P<abr>\d+)kbps\s*,\s*(?P<note>.+)',
                        title)
                    if m:
                        format.update({
                            'format_note': '%s, %s' % (m.group('format'), m.group('note')),
                            'vcodec': 'none',
                            'abr': int(m.group('abr')),
                        })
            formats.append(format)
        self._sort_formats(formats)
        return formats

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id') or mobj.group('path')
        display_id = video_id.lstrip('-')

        webpage = self._download_webpage(url, display_id)

        title = self._html_search_regex(
            r'<span[^>]*class="headline"[^>]*>(.+?)</span>',
            webpage, 'title', default=None) or self._og_search_title(webpage)

        DOWNLOAD_REGEX = r'(?s)<p>Wir bieten dieses (?P<kind>Video|Audio) in folgenden Formaten zum Download an:</p>\s*<div class="controls">(?P<links>.*?)</div>\s*<p>'

        webpage_type = self._og_search_property('type', webpage, default=None)
        if webpage_type == 'website':  # Article
            entries = []
            for num, (entry_title, media_kind, download_text) in enumerate(re.findall(
                    r'(?s)<p[^>]+class="infotext"[^>]*>\s*(?:<a[^>]+>)?\s*<strong>(.+?)</strong>.*?</p>.*?%s' % DOWNLOAD_REGEX,
                    webpage), 1):
                entries.append({
                    'id': '%s-%d' % (display_id, num),
                    'title': '%s' % entry_title,
                    'formats': self._extract_formats(download_text, media_kind),
                })
            if len(entries) > 1:
                return self.playlist_result(entries, display_id, title)
            formats = entries[0]['formats']
        else:  # Assume single video
            download_text = self._search_regex(
                DOWNLOAD_REGEX, webpage, 'download links', group='links')
            media_kind = self._search_regex(
                DOWNLOAD_REGEX, webpage, 'media kind', default='Video', group='kind')
            formats = self._extract_formats(download_text, media_kind)
        thumbnail = self._og_search_thumbnail(webpage)
        description = self._html_search_regex(
            r'(?s)<p class="teasertext">(.*?)</p>',
            webpage, 'description', default=None)

        self._sort_formats(formats)

        return {
            'id': display_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'description': description,
        }

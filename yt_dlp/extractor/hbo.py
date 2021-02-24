# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    xpath_text,
    xpath_element,
    int_or_none,
    parse_duration,
    urljoin,
)


class HBOBaseIE(InfoExtractor):
    _FORMATS_INFO = {
        'pro7': {
            'width': 1280,
            'height': 720,
        },
        '1920': {
            'width': 1280,
            'height': 720,
        },
        'pro6': {
            'width': 768,
            'height': 432,
        },
        '640': {
            'width': 768,
            'height': 432,
        },
        'pro5': {
            'width': 640,
            'height': 360,
        },
        'highwifi': {
            'width': 640,
            'height': 360,
        },
        'high3g': {
            'width': 640,
            'height': 360,
        },
        'medwifi': {
            'width': 400,
            'height': 224,
        },
        'med3g': {
            'width': 400,
            'height': 224,
        },
    }

    def _extract_info(self, url, display_id):
        video_data = self._download_xml(url, display_id)
        video_id = xpath_text(video_data, 'id', fatal=True)
        episode_title = title = xpath_text(video_data, 'title', fatal=True)
        series = xpath_text(video_data, 'program')
        if series:
            title = '%s - %s' % (series, title)

        formats = []
        for source in xpath_element(video_data, 'videos', 'sources', True):
            if source.tag == 'size':
                path = xpath_text(source, './/path')
                if not path:
                    continue
                width = source.attrib.get('width')
                format_info = self._FORMATS_INFO.get(width, {})
                height = format_info.get('height')
                fmt = {
                    'url': path,
                    'format_id': 'http%s' % ('-%dp' % height if height else ''),
                    'width': format_info.get('width'),
                    'height': height,
                }
                rtmp = re.search(r'^(?P<url>rtmpe?://[^/]+/(?P<app>.+))/(?P<playpath>mp4:.+)$', path)
                if rtmp:
                    fmt.update({
                        'url': rtmp.group('url'),
                        'play_path': rtmp.group('playpath'),
                        'app': rtmp.group('app'),
                        'ext': 'flv',
                        'format_id': fmt['format_id'].replace('http', 'rtmp'),
                    })
                formats.append(fmt)
            else:
                video_url = source.text
                if not video_url:
                    continue
                if source.tag == 'tarball':
                    formats.extend(self._extract_m3u8_formats(
                        video_url.replace('.tar', '/base_index_w8.m3u8'),
                        video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))
                elif source.tag == 'hls':
                    m3u8_formats = self._extract_m3u8_formats(
                        video_url.replace('.tar', '/base_index.m3u8'),
                        video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
                    for f in m3u8_formats:
                        if f.get('vcodec') == 'none' and not f.get('tbr'):
                            f['tbr'] = int_or_none(self._search_regex(
                                r'-(\d+)k/', f['url'], 'tbr', default=None))
                    formats.extend(m3u8_formats)
                elif source.tag == 'dash':
                    formats.extend(self._extract_mpd_formats(
                        video_url.replace('.tar', '/manifest.mpd'),
                        video_id, mpd_id='dash', fatal=False))
                else:
                    format_info = self._FORMATS_INFO.get(source.tag, {})
                    formats.append({
                        'format_id': 'http-%s' % source.tag,
                        'url': video_url,
                        'width': format_info.get('width'),
                        'height': format_info.get('height'),
                    })
        self._sort_formats(formats)

        thumbnails = []
        card_sizes = xpath_element(video_data, 'titleCardSizes')
        if card_sizes is not None:
            for size in card_sizes:
                path = xpath_text(size, 'path')
                if not path:
                    continue
                width = int_or_none(size.get('width'))
                thumbnails.append({
                    'id': width,
                    'url': path,
                    'width': width,
                })

        subtitles = None
        caption_url = xpath_text(video_data, 'captionUrl')
        if caption_url:
            subtitles = {
                'en': [{
                    'url': caption_url,
                    'ext': 'ttml'
                }],
            }

        return {
            'id': video_id,
            'title': title,
            'duration': parse_duration(xpath_text(video_data, 'duration/tv14')),
            'series': series,
            'episode': episode_title,
            'formats': formats,
            'thumbnails': thumbnails,
            'subtitles': subtitles,
        }


class HBOIE(HBOBaseIE):
    IE_NAME = 'hbo'
    _VALID_URL = r'https?://(?:www\.)?hbo\.com/(?:video|embed)(?:/[^/]+)*/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'https://www.hbo.com/video/game-of-thrones/seasons/season-8/videos/trailer',
        'md5': '8126210656f433c452a21367f9ad85b3',
        'info_dict': {
            'id': '22113301',
            'ext': 'mp4',
            'title': 'Game of Thrones - Trailer',
        },
        'expected_warnings': ['Unknown MIME type application/mp4 in DASH manifest'],
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        location_path = self._parse_json(self._html_search_regex(
            r'data-state="({.+?})"', webpage, 'state'), display_id)['video']['locationUrl']
        return self._extract_info(urljoin(url, location_path), display_id)

# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    dict_get,
    ExtractorError,
    int_or_none,
    js_to_json,
    parse_iso8601,
)


class ZypeIE(InfoExtractor):
    _ID_RE = r'[\da-fA-F]+'
    _COMMON_RE = r'//player\.zype\.com/embed/%s\.(?:js|json|html)\?.*?(?:access_token|(?:ap[ip]|player)_key)='
    _VALID_URL = r'https?:%s[^&]+' % (_COMMON_RE % ('(?P<id>%s)' % _ID_RE))
    _TEST = {
        'url': 'https://player.zype.com/embed/5b400b834b32992a310622b9.js?api_key=jZ9GUhRmxcPvX7M3SlfejB6Hle9jyHTdk2jVxG7wOHPLODgncEKVdPYBhuz9iWXQ&autoplay=false&controls=true&da=false',
        'md5': 'eaee31d474c76a955bdaba02a505c595',
        'info_dict': {
            'id': '5b400b834b32992a310622b9',
            'ext': 'mp4',
            'title': 'Smoky Barbecue Favorites',
            'thumbnail': r're:^https?://.*\.jpe?g',
            'description': 'md5:5ff01e76316bd8d46508af26dc86023b',
            'timestamp': 1504915200,
            'upload_date': '20170909',
        },
    }

    @staticmethod
    def _extract_urls(webpage):
        return [
            mobj.group('url')
            for mobj in re.finditer(
                r'<script[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?%s.+?)\1' % (ZypeIE._COMMON_RE % ZypeIE._ID_RE),
                webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            response = self._download_json(re.sub(
                r'\.(?:js|html)\?', '.json?', url), video_id)['response']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code in (400, 401, 403):
                raise ExtractorError(self._parse_json(
                    e.cause.read().decode(), video_id)['message'], expected=True)
            raise

        body = response['body']
        video = response['video']
        title = video['title']

        if isinstance(body, dict):
            formats = []
            for output in body.get('outputs', []):
                output_url = output.get('url')
                if not output_url:
                    continue
                name = output.get('name')
                if name == 'm3u8':
                    formats = self._extract_m3u8_formats(
                        output_url, video_id, 'mp4',
                        'm3u8_native', m3u8_id='hls', fatal=False)
                else:
                    f = {
                        'format_id': name,
                        'tbr': int_or_none(output.get('bitrate')),
                        'url': output_url,
                    }
                    if name in ('m4a', 'mp3'):
                        f['vcodec'] = 'none'
                    else:
                        f.update({
                            'height': int_or_none(output.get('height')),
                            'width': int_or_none(output.get('width')),
                        })
                    formats.append(f)
            text_tracks = body.get('subtitles') or []
        else:
            m3u8_url = self._search_regex(
                r'(["\'])(?P<url>(?:(?!\1).)+\.m3u8(?:(?!\1).)*)\1',
                body, 'm3u8 url', group='url', default=None)
            if not m3u8_url:
                source = self._parse_json(self._search_regex(
                    r'(?s)sources\s*:\s*\[\s*({.+?})\s*\]', body,
                    'source'), video_id, js_to_json)
                if source.get('integration') == 'verizon-media':
                    m3u8_url = 'https://content.uplynk.com/%s.m3u8' % source['id']
            formats = self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls')
            text_tracks = self._search_regex(
                r'textTracks\s*:\s*(\[[^]]+\])',
                body, 'text tracks', default=None)
            if text_tracks:
                text_tracks = self._parse_json(
                    text_tracks, video_id, js_to_json, False)
        self._sort_formats(formats)

        subtitles = {}
        if text_tracks:
            for text_track in text_tracks:
                tt_url = dict_get(text_track, ('file', 'src'))
                if not tt_url:
                    continue
                subtitles.setdefault(text_track.get('label') or 'English', []).append({
                    'url': tt_url,
                })

        thumbnails = []
        for thumbnail in video.get('thumbnails', []):
            thumbnail_url = thumbnail.get('url')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(thumbnail.get('width')),
                'height': int_or_none(thumbnail.get('height')),
            })

        return {
            'id': video_id,
            'display_id': video.get('friendly_title'),
            'title': title,
            'thumbnails': thumbnails,
            'description': dict_get(video, ('description', 'ott_description', 'short_description')),
            'timestamp': parse_iso8601(video.get('published_at')),
            'duration': int_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('request_count')),
            'average_rating': int_or_none(video.get('rating')),
            'season_number': int_or_none(video.get('season')),
            'episode_number': int_or_none(video.get('episode')),
            'formats': formats,
            'subtitles': subtitles,
        }

from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
    qualities,
    try_get,
    url_or_none,
    urljoin,
)


class MxplayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?:show|movie)/(?:(?P<display_id>[-/a-z0-9]+)-)?(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/movie/watch-knock-knock-hindi-dubbed-movie-online-b9fa28df3bfb8758874735bbd7d2655a?watch=true',
        'info_dict': {
            'id': 'b9fa28df3bfb8758874735bbd7d2655a',
            'ext': 'mp4',
            'title': 'Knock Knock (Hindi Dubbed)',
            'description': 'md5:b195ba93ff1987309cfa58e2839d2a5b'
        },
        'params': {
            'skip_download': True,
            'format': 'bestvideo'
        }
    }, {
        'url': 'https://www.mxplayer.in/show/watch-shaitaan/season-1/the-infamous-taxi-gang-of-meerut-online-45055d5bcff169ad48f2ad7552a83d6c',
        'info_dict': {
            'id': '45055d5bcff169ad48f2ad7552a83d6c',
            'ext': 'm3u8',
            'title': 'The infamous taxi gang of Meerut',
            'description': 'md5:033a0a7e3fd147be4fb7e07a01a3dc28',
            'season': 'Season 1',
            'series': 'Shaitaan'
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://www.mxplayer.in/show/watch-aashram/chapter-1/duh-swapna-online-d445579792b0135598ba1bc9088a84cb',
        'info_dict': {
            'id': 'd445579792b0135598ba1bc9088a84cb',
            'ext': 'mp4',
            'title': 'Duh Swapna',
            'description': 'md5:35ff39c4bdac403c53be1e16a04192d8',
            'season': 'Chapter 1',
            'series': 'Aashram'
        },
        'expected_warnings': ['Unknown MIME type application/mp4 in DASH manifest'],
        'params': {
            'skip_download': True,
            'format': 'bestvideo'
        }
    }]

    def _get_stream_urls(self, video_dict):
        stream_provider_dict = try_get(
            video_dict,
            lambda x: x['stream'][x['stream']['provider']])
        if not stream_provider_dict:
            raise ExtractorError('No stream provider found', expected=True)

        for stream_name, stream in stream_provider_dict.items():
            if stream_name in ('hls', 'dash', 'hlsUrl', 'dashUrl'):
                stream_type = stream_name.replace('Url', '')
                if isinstance(stream, dict):
                    for quality, stream_url in stream.items():
                        if stream_url:
                            yield stream_type, quality, stream_url
                else:
                    yield stream_type, 'base', stream

    def _real_extract(self, url):
        display_id, video_id = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, video_id)

        source = self._parse_json(
            js_to_json(self._html_search_regex(
                r'(?s)<script>window\.state\s*[:=]\s(\{.+\})\n(\w+).*(</script>).*',
                webpage, 'WindowState')),
            video_id)
        if not source:
            raise ExtractorError('Cannot find source', expected=True)

        config_dict = source['config']
        video_dict = source['entities'][video_id]

        thumbnails = []
        for i in video_dict.get('imageInfo') or []:
            thumbnails.append({
                'url': urljoin(config_dict['imageBaseUrl'], i['url']),
                'width': i['width'],
                'height': i['height'],
            })

        formats = []
        get_quality = qualities(['main', 'base', 'high'])
        for stream_type, quality, stream_url in self._get_stream_urls(video_dict):
            format_url = url_or_none(urljoin(config_dict['videoCdnBaseUrl'], stream_url))
            if not format_url:
                continue
            if stream_type == 'dash':
                dash_formats = self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash-%s' % quality, headers={'Referer': url})
                for frmt in dash_formats:
                    frmt['quality'] = get_quality(quality)
                formats.extend(dash_formats)
            elif stream_type == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, fatal=False,
                    m3u8_id='hls-%s' % quality, quality=get_quality(quality)))

        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id.replace('/', '-'),
            'title': video_dict['title'] or self._og_search_title(webpage),
            'formats': formats,
            'description': video_dict.get('description'),
            'season': try_get(video_dict, lambda x: x['container']['title']),
            'series': try_get(video_dict, lambda x: x['container']['container']['title']),
            'thumbnails': thumbnails,
        }

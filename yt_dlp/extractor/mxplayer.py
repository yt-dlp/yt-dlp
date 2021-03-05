from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
    url_or_none,
    urljoin,
)


VALID_STREAMS = ('dash', 'hls')


class MxplayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?P<type>show/.*/|movie/)(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/movie/watch-knock-knock-hindi-dubbed-movie-online-b9fa28df3bfb8758874735bbd7d2655a?watch=true',
        'info_dict': {
            'id': 'b9fa28df3bfb8758874735bbd7d2655a',
            'ext': 'mp4',
            'title': 'Knock Knock Movie | Watch 2015 Knock Knock Full Movie Online- MX Player',
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

    }]

    def _get_best_stream_url(self, stream):
        best_stream = list(filter(None, [v for k, v in stream.items()]))
        return best_stream.pop(0) if len(best_stream) else None

    def _get_stream_urls_shows(self, video_dict):
        stream_dict = video_dict.get('stream', {'provider': {}})
        stream_provider = stream_dict.get('provider')
        stream_provider_dict = stream_dict.get(stream_provider)
        if not stream_dict[stream_provider]:
            message = 'No stream provider found'
            raise ExtractorError('%s said: %s' % (self.IE_NAME, message), expected=True)

        streams = []
        if stream_provider_dict['dashUrl']:
            streams.append(('dash', stream_provider_dict['dashUrl']))
        if stream_provider_dict['hlsUrl']:
            streams.append(('hls', stream_provider_dict['hlsUrl']))
        return streams

    def _get_stream_urls(self, video_dict):
        stream_dict = video_dict.get('stream', {'provider': {}})
        stream_provider = stream_dict.get('provider')

        if not stream_dict[stream_provider]:
            message = 'No stream provider found'
            raise ExtractorError('%s said: %s' % (self.IE_NAME, message), expected=True)

        streams = []
        for stream_name, v in stream_dict[stream_provider].items():
            if stream_name in VALID_STREAMS:
                stream_url = self._get_best_stream_url(v)
                if stream_url is None:
                    continue
                streams.append((stream_name, stream_url))
        return streams

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_slug = mobj.group('slug')
        video_type = mobj.group('type').split('/')[0]
        video_id = video_slug.split('-')[-1]

        webpage = self._download_webpage(url, video_id)

        window_state_json = self._html_search_regex(
            r'(?s)<script>window\.state\s*[:=]\s(\{.+\})\n(\w+).*(</script>).*',
            webpage, 'WindowState')

        source = self._parse_json(js_to_json(window_state_json), video_id)
        if not source:
            raise ExtractorError('Cannot find source', expected=True)

        config_dict = source['config']
        video_dict = source['entities'][video_id]

        if video_type == 'movie':
            title = self._og_search_title(webpage, fatal=True, default=video_dict['title'])
            stream_urls = self._get_stream_urls(video_dict)
            formats = []
            headers = {'Referer': url}
            for stream_name, stream_url in stream_urls:
                if stream_name == 'dash':
                    format_url = url_or_none(urljoin(config_dict['videoCdnBaseUrl'], stream_url))
                    if format_url:
                        formats.extend(self._extract_mpd_formats(
                            format_url, video_id, mpd_id='dash', headers=headers))
                elif stream_name == 'hls':
                    format_url = url_or_none(urljoin(config_dict['videoCdnBaseUrl'], stream_url))
                    if not format_url:
                        continue
                    formats.extend(self._extract_m3u8_formats(format_url, video_id, fatal=False))
                self._sort_formats(formats)
            info = {
                'id': video_id,
                'title': title,
                'description': video_dict.get('description'),
                'formats': formats
            }

        elif video_type == 'show':
            title = video_dict['title']
            season = video_dict['container']['title']
            series = video_dict['container']['container']['title']
            stream_urls = self._get_stream_urls_shows(video_dict)
            formats = []
            headers = {'Referer': url}
            for stream_name, stream_url in stream_urls:
                if stream_name == 'dash':
                    formats.extend(self._extract_mpd_formats(
                        stream_url, video_id, mpd_id='dash', headers=headers))
                elif stream_name == 'hls':
                    formats.extend(self._extract_m3u8_formats(stream_url, video_id, fatal=False))
            info = {
                'id': video_id,
                'title': title,
                'description': video_dict.get('description'),
                'formats': formats,
                'season': season,
                'series': series
            }

        if video_dict.get('imageInfo'):
            info['thumbnails'] = list(map(lambda i: dict(i, **{
                'url': urljoin(config_dict['imageBaseUrl'], i['url'])
            }), video_dict['imageInfo']))

        if video_dict.get('webUrl'):
            last_part = video_dict['webUrl'].split("/")[-1]
            info['display_id'] = last_part.replace(video_id, "").rstrip("-")

        return info

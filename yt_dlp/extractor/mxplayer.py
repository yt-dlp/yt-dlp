from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    js_to_json,
    qualities,
    try_get,
    url_or_none,
    urljoin,
)


class MxplayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?:movie|show/[-\w]+/[-\w]+)/(?P<display_id>[-\w]+)-(?P<id>\w+)'
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
                dash_formats_h265 = self._extract_mpd_formats(
                    format_url.replace('h264_high', 'h265_main'), video_id, mpd_id='dash-%s' % quality, headers={'Referer': url}, fatal=False)
                for frmt in dash_formats_h265:
                    frmt['quality'] = get_quality(quality)
                formats.extend(dash_formats_h265)
            elif stream_type == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, fatal=False,
                    m3u8_id='hls-%s' % quality, quality=get_quality(quality), ext='mp4'))

        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': video_dict['title'] or self._og_search_title(webpage),
            'formats': formats,
            'description': video_dict.get('description'),
            'season': try_get(video_dict, lambda x: x['container']['title']),
            'series': try_get(video_dict, lambda x: x['container']['container']['title']),
            'thumbnails': thumbnails,
        }


class MxplayerShowIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?mxplayer\.in/show/(?P<display_id>[-\w]+)-(?P<id>\w+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-chakravartin-ashoka-samrat-series-online-a8f44e3cc0814b5601d17772cedf5417',
        'playlist_mincount': 440,
        'info_dict': {
            'id': 'a8f44e3cc0814b5601d17772cedf5417',
            'title': 'Watch Chakravartin Ashoka Samrat Series Online',
        }
    }]

    _API_SHOW_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowseasons?type=tv_show&id={}&device-density=2&platform=com.mxplay.desktop&content-languages=hi,en"
    _API_EPISODES_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowepisodes?type=season&id={}&device-density=1&platform=com.mxplay.desktop&content-languages=hi,en&{}"

    def _entries(self, show_id):
        show_json = self._download_json(
            self._API_SHOW_URL.format(show_id),
            video_id=show_id, headers={'Referer': 'https://mxplayer.in'})
        page_num = 0
        for season in show_json.get('items') or []:
            season_id = try_get(season, lambda x: x['id'], compat_str)
            next_url = ''
            while next_url is not None:
                page_num += 1
                season_json = self._download_json(
                    self._API_EPISODES_URL.format(season_id, next_url),
                    video_id=season_id,
                    headers={'Referer': 'https://mxplayer.in'},
                    note='Downloading JSON metadata page %d' % page_num)
                for episode in season_json.get('items') or []:
                    video_url = episode['webUrl']
                    yield self.url_result(
                        'https://mxplayer.in%s' % video_url,
                        ie=MxplayerIE.ie_key(), video_id=video_url.split('-')[-1])
                next_url = season_json.get('next')

    def _real_extract(self, url):
        display_id, show_id = re.match(self._VALID_URL, url).groups()
        return self.playlist_result(
            self._entries(show_id), playlist_id=show_id,
            playlist_title=display_id.replace('-', ' ').title())

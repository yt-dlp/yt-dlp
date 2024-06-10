import itertools
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    str_to_int,
    try_get,
    unified_strdate,
    url_or_none,
)


class TedBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://www\.ted\.com/(?:{type})(?:/lang/[^/#?]+)?/(?P<id>[\w-]+)'

    def _parse_playlist(self, playlist):
        for entry in try_get(playlist, lambda x: x['videos']['nodes'], list):
            if entry.get('__typename') == 'Video' and entry.get('canonicalUrl'):
                yield self.url_result(entry['canonicalUrl'], TedTalkIE.ie_key())


class TedTalkIE(TedBaseIE):
    _VALID_URL = TedBaseIE._VALID_URL_BASE.format(type='talks')
    _TESTS = [{
        'url': 'https://www.ted.com/talks/candace_parker_how_to_break_down_barriers_and_not_accept_limits',
        'md5': '47e82c666d9c3261d4fe74748a90aada',
        'info_dict': {
            'id': '86532',
            'ext': 'mp4',
            'title': 'How to break down barriers and not accept limits',
            'description': 'md5:000707cece219d1e165b11550d612331',
            'view_count': int,
            'tags': ['personal growth', 'equality', 'activism', 'motivation', 'social change', 'sports'],
            'uploader': 'Candace Parker',
            'duration': 676.0,
            'upload_date': '20220114',
            'release_date': '20211201',
            'thumbnail': r're:http.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        talk_info = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['videoData']
        video_id = talk_info['id']
        player_data = self._parse_json(talk_info.get('playerData'), video_id)

        http_url = None
        formats, subtitles = [], {}
        for format_id, resources in (player_data.get('resources') or {}).items():
            if format_id == 'hls':
                stream_url = url_or_none(try_get(resources, lambda x: x['stream']))
                if not stream_url:
                    continue
                m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    stream_url, video_id, 'mp4', m3u8_id=format_id, fatal=False)
                formats.extend(m3u8_formats)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
                continue

            if not isinstance(resources, list):
                continue
            if format_id == 'h264':
                for resource in resources:
                    h264_url = resource.get('file')
                    if not h264_url:
                        continue
                    bitrate = int_or_none(resource.get('bitrate'))
                    formats.append({
                        'url': h264_url,
                        'format_id': f'{format_id}-{bitrate}k',
                        'tbr': bitrate,
                    })
                    if re.search(r'\d+k', h264_url):
                        http_url = h264_url
            elif format_id == 'rtmp':
                streamer = talk_info.get('streamer')
                if not streamer:
                    continue
                formats.extend({
                    'format_id': '{}-{}'.format(format_id, resource.get('name')),
                    'url': streamer,
                    'play_path': resource['file'],
                    'ext': 'flv',
                    'width': int_or_none(resource.get('width')),
                    'height': int_or_none(resource.get('height')),
                    'tbr': int_or_none(resource.get('bitrate')),
                } for resource in resources if resource.get('file'))

        if http_url:
            m3u8_formats = [f for f in formats if f.get('protocol') == 'm3u8' and f.get('vcodec') != 'none']
            for m3u8_format in m3u8_formats:
                bitrate = self._search_regex(r'(\d+k)', m3u8_format['url'], 'bitrate', default=None)
                if not bitrate:
                    continue
                bitrate_url = re.sub(r'\d+k', bitrate, http_url)
                if not self._is_valid_url(
                        bitrate_url, video_id, f'{bitrate} bitrate'):
                    continue
                f = m3u8_format.copy()
                f.update({
                    'url': bitrate_url,
                    'format_id': m3u8_format['format_id'].replace('hls', 'http'),
                    'protocol': 'http',
                })
                if f.get('acodec') == 'none':
                    del f['acodec']
                formats.append(f)

        audio_download = talk_info.get('audioDownload')
        if audio_download:
            formats.append({
                'url': audio_download,
                'format_id': 'audio',
                'vcodec': 'none',
            })

        if not formats:
            external = player_data.get('external') or {}
            service = external.get('service') or ''
            ext_url = external.get('code') if service.lower() == 'youtube' else None
            return self.url_result(ext_url or external['uri'])

        thumbnail = player_data.get('thumb') or self._og_search_property('image', webpage)
        if thumbnail:
            # trim thumbnail resize parameters
            thumbnail = thumbnail.split('?')[0]

        return {
            'id': video_id,
            'title': talk_info.get('title') or self._og_search_title(webpage),
            'uploader': talk_info.get('presenterDisplayName'),
            'thumbnail': thumbnail,
            'description': talk_info.get('description') or self._og_search_description(webpage),
            'subtitles': subtitles,
            'formats': formats,
            'duration': talk_info.get('duration') or parse_duration(self._og_search_property('video:duration', webpage)),
            'view_count': str_to_int(talk_info.get('viewedCount')),
            'upload_date': unified_strdate(talk_info.get('publishedAt')),
            'release_date': unified_strdate(talk_info.get('recordedOn')),
            'tags': try_get(player_data, lambda x: x['targeting']['tag'].split(',')),
        }


class TedSeriesIE(TedBaseIE):
    _VALID_URL = fr'{TedBaseIE._VALID_URL_BASE.format(type=r"series")}(?:#season_(?P<season>\d+))?'
    _TESTS = [{
        'url': 'https://www.ted.com/series/small_thing_big_idea',
        'info_dict': {
            'id': '3',
            'title': 'Small Thing Big Idea',
            'series': 'Small Thing Big Idea',
            'description': 'md5:6869ca52cec661aef72b3e9f7441c55c',
        },
        'playlist_mincount': 16,
    }, {
        'url': 'https://www.ted.com/series/the_way_we_work#season_2',
        'info_dict': {
            'id': '8_2',
            'title': 'The Way We Work Season 2',
            'series': 'The Way We Work',
            'description': 'md5:59469256e533e1a48c4aa926a382234c',
            'season_number': 2,
        },
        'playlist_mincount': 8,
    }]

    def _real_extract(self, url):
        display_id, season = self._match_valid_url(url).group('id', 'season')
        webpage = self._download_webpage(url, display_id, 'Downloading series webpage')
        info = self._search_nextjs_data(webpage, display_id)['props']['pageProps']

        entries = itertools.chain.from_iterable(
            self._parse_playlist(s) for s in info['seasons'] if season in [None, s.get('seasonNumber')])

        series_id = try_get(info, lambda x: x['series']['id'])
        series_name = try_get(info, lambda x: x['series']['name']) or self._og_search_title(webpage, fatal=False)

        return self.playlist_result(
            entries,
            f'{series_id}_{season}' if season and series_id else series_id,
            f'{series_name} Season {season}' if season else series_name,
            self._og_search_description(webpage),
            series=series_name, season_number=int_or_none(season))


class TedPlaylistIE(TedBaseIE):
    _VALID_URL = TedBaseIE._VALID_URL_BASE.format(type=r'playlists(?:/\d+)?')
    _TESTS = [{
        'url': 'https://www.ted.com/playlists/171/the_most_popular_talks_of_all',
        'info_dict': {
            'id': '171',
            'title': 'The most popular talks of all time',
            'description': 'md5:d2f22831dc86c7040e733a3cb3993d78',
        },
        'playlist_mincount': 25,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        playlist = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['playlist']

        return self.playlist_result(
            self._parse_playlist(playlist), playlist.get('id'),
            playlist.get('title') or self._og_search_title(webpage, default='').replace(' | TED Talks', '') or None,
            self._og_search_description(webpage))


class TedEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://embed(?:-ssl)?\.ted\.com/'
    _EMBED_REGEX = [rf'<iframe[^>]+?src=(["\'])(?P<url>{_VALID_URL}.+?)\1']

    _TESTS = [{
        'url': 'https://embed.ted.com/talks/janet_stovall_how_to_get_serious_about_diversity_and_inclusion_in_the_workplace',
        'info_dict': {
            'id': '21802',
            'ext': 'mp4',
            'title': 'How to get serious about diversity and inclusion in the workplace',
            'description': 'md5:0978aafe396e05341f8ecc795d22189d',
            'view_count': int,
            'tags': list,
            'uploader': 'Janet Stovall',
            'duration': 664.0,
            'upload_date': '20180822',
            'release_date': '20180719',
            'thumbnail': r're:http.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        return self.url_result(re.sub(r'://embed(-ssl)?', '://www', url), TedTalkIE.ie_key())

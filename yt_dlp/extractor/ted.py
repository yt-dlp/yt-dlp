from __future__ import unicode_literals
import re

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    str_to_int,
    try_get,
    url_or_none,
    unified_strdate,
    parse_duration,
)


class TEDIE(InfoExtractor):
    IE_NAME = 'ted'
    _VALID_URL = r'''(?x)
        (?P<proto>https?://)
        (?P<type>www|embed(?:-ssl)?)(?P<urlmain>\.ted\.com/
        (
            (?P<type_playlist>playlists(?:/(?P<playlist_id>\d+))?)
            |
            (?P<type_series>series)
            |
            (?P<type_talk>talks)
        )
        (/lang/(.*?))?
        /(?P<name>[\w-]+)(?:\#season_(?P<season>\d))?
        .*)$
        '''
    _TESTS = [{
        # talk
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
    },
        {
        # talk
        'url': 'https://www.ted.com/talks/janet_stovall_how_to_get_serious_about_diversity_and_inclusion_in_the_workplace',
        'info_dict': {
            'id': '21802',
            'ext': 'mp4',
            'title': 'How to get serious about diversity and inclusion in the workplace',
            'description': 'md5:0978aafe396e05341f8ecc795d22189d',
            'view_count': int,
            'tags': ['communication', 'community', 'work', 'humanity', 'race', 'social change', 'leadership', 'society', 'United States', 'equality'],
            'uploader': 'Janet Stovall',
            'duration': 664.0,
            'upload_date': '20180822',
            'release_date': '20180719',
            'thumbnail': r're:http.*\.jpg',
        },
    },
        {
        # playlist
        'url': 'https://www.ted.com/playlists/171/the_most_popular_talks_of_all',
        'info_dict': {
            'id': '171',
            'title': 'The most popular talks of all time',
            'description': 'md5:d2f22831dc86c7040e733a3cb3993d78'
        },
        'playlist_mincount': 25,
    },
        {
        # series
        'url': 'https://www.ted.com/series/small_thing_big_idea',
        'info_dict': {
            'id': '3',
            'series': 'Small Thing Big Idea',
            'description': 'md5:6869ca52cec661aef72b3e9f7441c55c'
        },
        'playlist_mincount': 16,
    },
        {
        # series
        'url': 'https://www.ted.com/series/the_way_we_work',
        'info_dict': {
            'id': '8',
            'series': 'The Way We Work',
            'description': 'md5:59469256e533e1a48c4aa926a382234c'
        },
        'playlist_mincount': 33,
    },
        {
        # series with season
        'url': 'https://www.ted.com/series/small_thing_big_idea#season_1',
        'info_dict': {
            'id': '3',
            'series': 'Small Thing Big Idea',
            'description': 'md5:6869ca52cec661aef72b3e9f7441c55c',
            'season_number': 1
        },
        'playlist_mincount': 8,
    },
        {
        # series with season
        'url': 'https://www.ted.com/series/the_way_we_work#season_2',
        'info_dict': {
            'id': '8',
            'series': 'The Way We Work',
            'description': 'md5:59469256e533e1a48c4aa926a382234c',
            'season_number': 2
        },
        'playlist_mincount': 8,
    },
    ]

    def _extract_info(self, webpage, video_name):
        return self._parse_json(self._html_search_regex('<script[^>]+id="__NEXT_DATA__"[^>]*>(.+?)</script>', webpage, 'json'), video_name)

    def _parse_playlist(self, playlist):
        playlist_entries = []

        for entry in try_get(playlist, lambda x: x['videos']['nodes'], list) or []:
            if entry.get('__typename') == 'Video' and entry.get('canonicalUrl'):
                playlist_entries.append(self.url_result(entry.get('canonicalUrl'), self.ie_key()))

        return playlist_entries

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url, re.VERBOSE)
        if m.group('type').startswith('embed'):
            desktop_url = m.group('proto') + 'www' + m.group('urlmain')
            return self.url_result(desktop_url, 'TED')
        name = m.group('name')
        if m.group('type_talk'):
            return self._talk_info(url, name)
        elif m.group('type_playlist'):
            return self._playlist_videos_info(url, name)
        elif m.group('type_series'):
            return self._series_videos_info(url, name, m.group('season'))

    def _playlist_videos_info(self, url, name):
        webpage = self._download_webpage(url, name, 'Downloading playlist webpage')
        info = self._extract_info(webpage, 'json')

        playlist = try_get(info, lambda x: x['props']['pageProps']['playlist'], dict) or {}
        playlist_id = playlist.get('id')
        playlist_entries = self._parse_playlist(playlist)

        return self.playlist_result(
            playlist_entries, playlist_id=playlist_id,
            playlist_title=playlist.get('title') or self._og_search_title(webpage, fatal=False).replace(' | TED Talks', ''),
            playlist_description=self._og_search_description(webpage))

    def _series_videos_info(self, url, name, season):
        webpage = self._download_webpage(url, name, 'Downloading series webpage')
        info = self._extract_info(webpage, 'json')
        series = try_get(info, lambda x: x['props']['pageProps']['series']) or {}
        series_id = series.get('id')

        seasonlist = try_get(info, lambda x: x['props']['pageProps']['seasons'], list)

        playlist_entries = []
        if season:
            [playlist_entries.extend(self._parse_playlist(s)) for s in seasonlist if s.get('seasonNumber') == season]
        else:
            [playlist_entries.extend(self._parse_playlist(s)) for s in seasonlist]

        return self.playlist_result(
            playlist_entries, playlist_id=series_id,
            series=series.get('name') or self._og_search_title(webpage, fatal=False),
            playlist_description=self._og_search_description(webpage),
            season_number=str_to_int(season))

    def _talk_info(self, url, video_name):
        webpage = self._download_webpage(url, video_name)
        info = self._extract_info(webpage, video_name)
        talk_info = try_get(info, lambda x: x['props']['pageProps']['videoData'], dict)

        video_id = talk_info.get('id')

        playerData = self._parse_json(talk_info.get('playerData'), video_id)
        resources_ = playerData.get('resources')
        http_url = None
        formats = []
        subtitles = {}
        for format_id, resources in resources_.items():
            if format_id == 'hls':
                if not isinstance(resources, dict):
                    continue
                stream_url = url_or_none(resources.get('stream'))
                if not stream_url:
                    continue
                m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    stream_url, video_name, 'mp4', m3u8_id=format_id,
                    fatal=False)
                formats.extend(m3u8_formats)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            else:
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
                            'format_id': '%s-%sk' % (format_id, bitrate),
                            'tbr': bitrate,
                        })
                        if re.search(r'\d+k', h264_url):
                            http_url = h264_url
                elif format_id == 'rtmp':
                    streamer = talk_info.get('streamer')
                    if not streamer:
                        continue
                    for resource in resources:
                        formats.append({
                            'format_id': '%s-%s' % (format_id, resource.get('name')),
                            'url': streamer,
                            'play_path': resource['file'],
                            'ext': 'flv',
                            'width': int_or_none(resource.get('width')),
                            'height': int_or_none(resource.get('height')),
                            'tbr': int_or_none(resource.get('bitrate')),
                        })

        m3u8_formats = list(filter(
            lambda f: f.get('protocol') == 'm3u8' and f.get('vcodec') != 'none',
            formats))
        if http_url:
            for m3u8_format in m3u8_formats:
                bitrate = self._search_regex(r'(\d+k)', m3u8_format['url'], 'bitrate', default=None)
                if not bitrate:
                    continue
                bitrate_url = re.sub(r'\d+k', bitrate, http_url)
                if not self._is_valid_url(
                        bitrate_url, video_name, '%s bitrate' % bitrate):
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
            external = playerData.get('external')
            if isinstance(external, dict):
                service = external.get('service')
                if isinstance(service, str):
                    ext_url = None
                    if service.lower() == 'youtube':
                        ext_url = external.get('code')
                    return self.url_result(ext_url or external['uri'])

        self._sort_formats(formats)

        thumbnail = playerData.get('thumb') or self._og_search_property('image', webpage)
        if thumbnail:
            # trim thumbnail resize parameters
            thumbnail = thumbnail.split('?')[0]

        return {
            'id': video_id,
            'title': talk_info.get('title') or self._og_search_title(webpage),
            'uploader': talk_info.get('presenterDisplayName'),
            'thumbnail': thumbnail,
            'description': parse_duration(talk_info.get('description')) or self._og_search_description(webpage),
            'subtitles': subtitles,
            'formats': formats,
            'duration': parse_duration(talk_info.get('duration')) or parse_duration(self._og_search_property('video:duration', webpage)),
            'view_count': str_to_int(talk_info.get('viewedCount')),
            'upload_date': unified_strdate(talk_info.get('publishedAt')),
            'release_date': unified_strdate(talk_info.get('recordedOn')),
            'tags': try_get(playerData, lambda x: x['targeting']['tag'].split(',')),
        }

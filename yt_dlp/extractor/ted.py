from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor

from ..compat import (
    compat_str,
    compat_urlparse
)
from ..utils import (
    extract_attributes,
    int_or_none,
    str_to_int,
    try_get,
    url_or_none,
    unified_strdate,
    parse_duration
)


class TEDIE(InfoExtractor):
    IE_NAME = 'ted'
    _VALID_URL = r'''(?x)
        (?P<proto>https?://)
        (?P<type>www|embed(?:-ssl)?)(?P<urlmain>\.ted\.com/
        (
            (?P<type_playlist>playlists(?:/(?P<playlist_id>\d+))?) # We have a playlist
            |
            ((?P<type_talk>talks)) # We have a simple talk
            |
            (?P<type_watch>watch)/[^/]+/[^/]+
        )
        (/lang/(.*?))? # The url may contain the language
        /(?P<name>[\w-]+) # Here goes the name and then ".html"
        .*)$
        '''
    _TESTS = [{
        'url': 'https://www.ted.com/talks/candace_parker_how_to_break_down_barriers_and_not_accept_limits',
        'md5': '47e82c666d9c3261d4fe74748a90aada',
        'info_dict': {
            'id': '86532',
            'ext': 'mp4',
            'title': 'How to break down barriers and not accept limits',
            'description': 'What can\'t Candace Parker do? A two-time NCAA champion, two-time Olympic gold medalist and two-time WNBA champion, Parker knows what it takes to fight for your dreams. In this inspiring talk, she shares what she\'s learned during a career spent not accepting limits -- and how her daughter taught her the best lesson of all. "Barrier breaking is about not staying in your lane and not being something that the world expects you to be," she says. "It\'s about not accepting limitations."',
            'view_count': int,
            'tags': ['personal growth', 'equality', 'activism', 'motivation', 'social change', 'sports'],
            'uploader': 'Candace Parker',
            'duration': 676.0,
            'upload_date': '20220114',
            'release_date': '20211201',
            'thumbnail': 'https://pi.tedcdn.com/r/talkstar-photos.s3.amazonaws.com/uploads/fd2ff863-26bb-4a72-8fd4-8380a4a8c0b4/CandaceParker_2021W-embed.jpg',
        },
    },
        {
        'url': 'https://www.ted.com/talks/janet_stovall_how_to_get_serious_about_diversity_and_inclusion_in_the_workplace',
        'info_dict': {
            'id': '21802',
            'ext': 'mp4',
            'title': 'How to get serious about diversity and inclusion in the workplace',
            'description': 'Imagine a workplace where people of all colors and races are able to climb every rung of the corporate ladder -- and where the lessons we learn about diversity at work actually transform the things we do, think and say outside the office. How do we get there? In this candid talk, inclusion advocate Janet Stovall shares a three-part action plan for creating workplaces where people feel safe and expected to be their unassimilated, authentic selves.',
            'view_count': int,
            'tags': ['communication', 'community', 'work', 'humanity', 'race', 'social change', 'leadership', 'society', 'United States', 'equality'],
            'uploader': 'Janet Stovall',
            'duration': 664.0,
            'upload_date': '20180822',
            'release_date': '20180719',
            'thumbnail': 'https://pi.tedcdn.com/r/talkstar-photos.s3.amazonaws.com/uploads/6a3549fa-2640-4ab4-892b-2491af834816/JanetStovall_2018S-embed.jpg',
        },
    }]

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url, re.VERBOSE)
        if m.group('type').startswith('embed'):
            desktop_url = m.group('proto') + 'www' + m.group('urlmain')
            return self.url_result(desktop_url, 'TED')
        name = m.group('name')
        if m.group('type_talk'):
            return self._talk_info(url, name)
        elif m.group('type_watch'):
            return self._watch_info(url, name)
        else:
            return self._playlist_videos_info(url, name)

    def _playlist_videos_info(self, url, name):
        '''Returns the videos of the playlist'''

        webpage = self._download_webpage(url, name,
                                         'Downloading playlist webpage')

        playlist_entries = []
        for entry in re.findall(r'(?s)<[^>]+data-ga-context=["\']playlist["\'][^>]*>', webpage):
            attrs = extract_attributes(entry)
            entry_url = compat_urlparse.urljoin(url, attrs['href'])
            playlist_entries.append(self.url_result(entry_url, self.ie_key()))

        final_url = self._og_search_url(webpage, fatal=False)
        playlist_id = (
            re.match(self._VALID_URL, final_url).group('playlist_id')
            if final_url else None)

        return self.playlist_result(
            playlist_entries, playlist_id=playlist_id,
            playlist_title=self._og_search_title(webpage, fatal=False),
            playlist_description=self._og_search_description(webpage))

    def _talk_info(self, url, video_name):
        webpage = self._download_webpage(url, video_name)
        print(url)
        json = self._parse_json(self._html_search_regex('<script[^>]+id="__NEXT_DATA__"[^>]*>(.+?)</script>', webpage, 'json'), video_name)
        talk_info = try_get(json, lambda x: x['props']['pageProps']['videoData'], dict)

        video_id = talk_info.get('id')
        title = talk_info.get('title') or self._og_search_title(webpage)
        uploader = talk_info.get('presenterDisplayName')
        release_date = unified_strdate(talk_info.get('recordedOn'))
        upload_date = unified_strdate(talk_info.get('publishedAt'))
        view_count = str_to_int(talk_info.get('viewedCount'))
        duration = parse_duration(talk_info.get('duration')) or parse_duration(self._og_search_property('video:duration', webpage))
        description = parse_duration(talk_info.get('description')) or self._og_search_description(webpage)

        playerData = self._parse_json(talk_info.get('playerData'), video_id)
        resources_ = playerData.get('resources')
        http_url = None
        formats = []
        subtitles = None
        for format_id, resources in resources_.items():
            if format_id == 'hls':
                if not isinstance(resources, dict):
                    continue
                stream_url = url_or_none(resources.get('stream'))
                if not stream_url:
                    continue
                m3u8, subtitles = self._extract_m3u8_formats_and_subtitles(
                    stream_url, video_name, 'mp4', m3u8_id=format_id,
                    fatal=False)
                formats.extend(m3u8)
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

        # not sure if this is still relevant
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
                if isinstance(service, compat_str):
                    ext_url = None
                    if service.lower() == 'youtube':
                        ext_url = external.get('code')
                    return self.url_result(ext_url or external['uri'])

        self._sort_formats(formats)

        # trim thumbnail resize parameters
        thumbnail = self._search_regex(r'^(http[^?]*)', playerData.get('thumb'), 'thumbnail', default=None) or self._search_regex(r'^(http[^?]*)', self._og_search_property('image', webpage), 'thumbnail', default=None)

        # tags
        tags = try_get(playerData, lambda x: x['targeting']['tag'], str)
        if tags:
            tags = tags.split(',')

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'thumbnail': thumbnail,
            'description': description,
            'subtitles': subtitles,
            'formats': formats,
            'duration': duration,
            'view_count': view_count,
            'upload_date': upload_date,
            'release_date': release_date,
            'tags': tags,
        }

    def _get_subtitles(self, video_id, talk_info):
        sub_lang_list = {}
        for language in try_get(
                talk_info,
                (lambda x: x['downloads']['languages'],
                 lambda x: x['languages']), list):
            lang_code = language.get('languageCode') or language.get('ianaCode')
            if not lang_code:
                continue
            sub_lang_list[lang_code] = [
                {
                    'url': 'http://www.ted.com/talks/subtitles/id/%s/lang/%s/format/%s' % (video_id, lang_code, ext),
                    'ext': ext,
                }
                for ext in ['ted', 'srt']
            ]
        return sub_lang_list

    def _watch_info(self, url, name):
        webpage = self._download_webpage(url, name)

        config_json = self._html_search_regex(
            r'"pages\.jwplayer"\s*,\s*({.+?})\s*\)\s*</script>',
            webpage, 'config', default=None)
        if not config_json:
            embed_url = self._search_regex(
                r"<iframe[^>]+class='pages-video-embed__video__object'[^>]+src='([^']+)'", webpage, 'embed url')
            return self.url_result(self._proto_relative_url(embed_url))
        config = json.loads(config_json)['config']
        video_url = config['video']['url']
        thumbnail = config.get('image', {}).get('url')

        title = self._html_search_regex(
            r"(?s)<h1(?:\s+class='[^']+')?>(.+?)</h1>", webpage, 'title')
        description = self._html_search_regex(
            [
                r'(?s)<h4 class="[^"]+" id="h3--about-this-talk">.*?</h4>(.*?)</div>',
                r'(?s)<p><strong>About this talk:</strong>\s+(.*?)</p>',
            ],
            webpage, 'description', fatal=False)

        return {
            'id': name,
            'url': video_url,
            'title': title,
            'thumbnail': thumbnail,
            'description': description,
        }

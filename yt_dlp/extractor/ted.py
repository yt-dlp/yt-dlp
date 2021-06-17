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
    float_or_none,
    int_or_none,
    try_get,
    url_or_none,
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
        'url': 'http://www.ted.com/talks/dan_dennett_on_our_consciousness.html',
        'md5': 'b0ce2b05ca215042124fbc9e3886493a',
        'info_dict': {
            'id': '102',
            'ext': 'mp4',
            'title': 'The illusion of consciousness',
            'description': ('Philosopher Dan Dennett makes a compelling '
                            'argument that not only don\'t we understand our own '
                            'consciousness, but that half the time our brains are '
                            'actively fooling us.'),
            'uploader': 'Dan Dennett',
            'width': 853,
            'duration': 1308,
            'view_count': int,
            'comment_count': int,
            'tags': list,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # missing HTTP bitrates
        'url': 'https://www.ted.com/talks/vishal_sikka_the_beauty_and_power_of_algorithms',
        'info_dict': {
            'id': '6069',
            'ext': 'mp4',
            'title': 'The beauty and power of algorithms',
            'thumbnail': r're:^https?://.+\.jpg',
            'description': 'md5:734e352710fb00d840ab87ae31aaf688',
            'uploader': 'Vishal Sikka',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.ted.com/talks/gabby_giffords_and_mark_kelly_be_passionate_be_courageous_be_your_best',
        'md5': 'e6b9617c01a7970ceac8bb2c92c346c0',
        'info_dict': {
            'id': '1972',
            'ext': 'mp4',
            'title': 'Be passionate. Be courageous. Be your best.',
            'uploader': 'Gabby Giffords and Mark Kelly',
            'description': 'md5:5174aed4d0f16021b704120360f72b92',
            'duration': 1128,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.ted.com/playlists/who_are_the_hackers',
        'info_dict': {
            'id': '10',
            'title': 'Who are the hackers?',
            'description': 'md5:49a0dbe8fb76d81a0e64b4a80af7f15a'
        },
        'playlist_mincount': 6,
    }, {
        # contains a youtube video
        'url': 'https://www.ted.com/talks/douglas_adams_parrots_the_universe_and_everything',
        'add_ie': ['Youtube'],
        'info_dict': {
            'id': '_ZG8HBuDjgc',
            'ext': 'webm',
            'title': 'Douglas Adams: Parrots the Universe and Everything',
            'description': 'md5:01ad1e199c49ac640cb1196c0e9016af',
            'uploader': 'University of California Television (UCTV)',
            'uploader_id': 'UCtelevision',
            'upload_date': '20080522',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # no nativeDownloads
        'url': 'https://www.ted.com/talks/tom_thum_the_orchestra_in_my_mouth',
        'info_dict': {
            'id': '1792',
            'ext': 'mp4',
            'title': 'The orchestra in my mouth',
            'description': 'md5:5d1d78650e2f8dfcbb8ebee2951ac29a',
            'uploader': 'Tom Thum',
            'view_count': int,
            'comment_count': int,
            'tags': list,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # with own formats and private Youtube external
        'url': 'https://www.ted.com/talks/spencer_wells_a_family_tree_for_humanity',
        'only_matching': True,
    }]

    _NATIVE_FORMATS = {
        'low': {'width': 320, 'height': 180},
        'medium': {'width': 512, 'height': 288},
        'high': {'width': 854, 'height': 480},
    }

    def _extract_info(self, webpage):
        info_json = self._search_regex(
            r'(?s)q\(\s*"\w+.init"\s*,\s*({.+?})\)\s*</script>',
            webpage, 'info json')
        return json.loads(info_json)

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

        info = self._extract_info(webpage)

        data = try_get(info, lambda x: x['__INITIAL_DATA__'], dict) or info
        talk_info = data['talks'][0]

        title = talk_info['title'].strip()

        downloads = talk_info.get('downloads') or {}
        native_downloads = downloads.get('nativeDownloads') or talk_info.get('nativeDownloads') or {}

        formats = [{
            'url': format_url,
            'format_id': format_id,
        } for (format_id, format_url) in native_downloads.items() if format_url is not None]

        subtitled_downloads = downloads.get('subtitledDownloads') or {}
        for lang, subtitled_download in subtitled_downloads.items():
            for q in self._NATIVE_FORMATS:
                q_url = subtitled_download.get(q)
                if not q_url:
                    continue
                formats.append({
                    'url': q_url,
                    'format_id': '%s-%s' % (q, lang),
                    'language': lang,
                })

        if formats:
            for f in formats:
                finfo = self._NATIVE_FORMATS.get(f['format_id'].split('-')[0])
                if finfo:
                    f.update(finfo)

        player_talk = talk_info['player_talks'][0]

        resources_ = player_talk.get('resources') or talk_info.get('resources')

        http_url = None
        for format_id, resources in resources_.items():
            if format_id == 'hls':
                if not isinstance(resources, dict):
                    continue
                stream_url = url_or_none(resources.get('stream'))
                if not stream_url:
                    continue
                formats.extend(self._extract_m3u8_formats(
                    stream_url, video_name, 'mp4', m3u8_id=format_id,
                    fatal=False))
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
            external = player_talk.get('external')
            if isinstance(external, dict):
                service = external.get('service')
                if isinstance(service, compat_str):
                    ext_url = None
                    if service.lower() == 'youtube':
                        ext_url = external.get('code')
                    return self.url_result(ext_url or external['uri'])

        self._sort_formats(formats)

        video_id = compat_str(talk_info['id'])

        return {
            'id': video_id,
            'title': title,
            'uploader': player_talk.get('speaker') or talk_info.get('speaker'),
            'thumbnail': player_talk.get('thumb') or talk_info.get('thumb'),
            'description': self._og_search_description(webpage),
            'subtitles': self._get_subtitles(video_id, talk_info),
            'formats': formats,
            'duration': float_or_none(talk_info.get('duration')),
            'view_count': int_or_none(data.get('viewed_count')),
            'comment_count': int_or_none(
                try_get(data, lambda x: x['comments']['count'])),
            'tags': try_get(talk_info, lambda x: x['tags'], list),
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

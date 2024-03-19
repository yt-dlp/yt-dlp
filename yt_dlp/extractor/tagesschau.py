import re

from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    extract_attributes,
    int_or_none,
    js_to_json,
    parse_iso8601,
    try_get,
)


class TagesschauIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?tagesschau\.de/(?P<path>[^/]+/(?:[^/]+/)*?(?P<id>[^/#?]+?(?:-?[0-9]+)?))(?:~_?[^/#?]+?)?\.html'

    _TESTS = [{
        'url': 'http://www.tagesschau.de/multimedia/video/video-102143.html',
        'md5': 'ccb9359bf8c4795836e43759f3408a93',
        'info_dict': {
            'id': 'video-102143-1',
            'ext': 'mp4',
            'title': 'Regierungsumbildung in Athen: Neue Minister in Griechenland vereidigt',
            'duration': 138,
        },
    }, {
        'url': 'http://www.tagesschau.de/multimedia/sendung/ts-5727.html',
        'md5': '5c15e8f3da049e48829ec9786d835536',
        'info_dict': {
            'id': 'ts-5727-1',
            'ext': 'mp4',
            'title': 'Ganze Sendung',
            'duration': 932,
        },
    }, {
        # exclusive audio
        'url': 'http://www.tagesschau.de/multimedia/audio/audio-29417.html',
        'md5': '4bff8f23504df56a0d86ed312d654182',
        'info_dict': {
            'id': 'audio-29417-1',
            'ext': 'mp3',
            'title': 'EU-Gipfel: Im Verbrennerstreit hat Deutschland maximalen Schaden angerichtet',
        },
    }, {
        'url': 'http://www.tagesschau.de/inland/bnd-303.html',
        'md5': 'f049fa1698d7564e9ca4c3325108f034',
        'info_dict': {
            'id': 'bnd-303-1',
            'ext': 'mp3',
            'title': 'Das Siegel des Bundesnachrichtendienstes | dpa',
        },
    }, {
        'url': 'http://www.tagesschau.de/inland/afd-parteitag-135.html',
        'info_dict': {
            'id': 'afd-parteitag-135',
            'title': 'AfD',
        },
        'playlist_mincount': 15,
    }, {
        'url': 'https://www.tagesschau.de/multimedia/audio/audio-29417~player.html',
        'info_dict': {
            'id': 'audio-29417-1',
            'ext': 'mp3',
            'title': 'EU-Gipfel: Im Verbrennerstreit hat Deutschland maximalen Schaden angerichtet',
        },
    }, {
        'url': 'https://www.tagesschau.de/multimedia/audio/podcast-11km-327.html',
        'info_dict': {
            'id': 'podcast-11km-327',
            'ext': 'mp3',
            'title': 'Gewalt in der Kita – Wenn Erzieher:innen schweigen',
            'upload_date': '20230322',
            'timestamp': 1679482808,
            'thumbnail': 'https://www.tagesschau.de/multimedia/audio/podcast-11km-329~_v-original.jpg',
            'description': 'md5:dad059931fe4b3693e3656e93a249848',
        },
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

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('path')
        display_id = video_id.lstrip('-')

        webpage = self._download_webpage(url, display_id)

        title = self._html_search_regex(
            r'<span[^>]*class="headline"[^>]*>(.+?)</span>',
            webpage, 'title', default=None) or self._og_search_title(webpage, fatal=False)

        entries = []
        videos = re.findall(r'<div[^>]+>', webpage)
        num = 0
        for video in videos:
            video = extract_attributes(video).get('data-config')
            if not video:
                continue
            video = self._parse_json(video, video_id, transform_source=js_to_json, fatal=False)
            video_formats = try_get(video, lambda x: x['mc']['_mediaArray'][0]['_mediaStreamArray'])
            if not video_formats:
                continue
            num += 1
            for video_format in video_formats:
                media_url = video_format.get('_stream') or ''
                formats = []
                if media_url.endswith('master.m3u8'):
                    formats = self._extract_m3u8_formats(media_url, video_id, 'mp4', m3u8_id='hls')
                elif media_url.endswith('.mp3'):
                    formats = [{
                        'url': media_url,
                        'vcodec': 'none',
                    }]
                if not formats:
                    continue
                entries.append({
                    'id': '%s-%d' % (display_id, num),
                    'title': try_get(video, lambda x: x['mc']['_title']),
                    'duration': int_or_none(try_get(video, lambda x: x['mc']['_duration'])),
                    'formats': formats
                })

        if not entries:
            raise UnsupportedError(url)

        if len(entries) > 1:
            return self.playlist_result(entries, display_id, title)

        return {
            'id': display_id,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': entries[0]['formats'],
            'timestamp': parse_iso8601(self._html_search_meta('date', webpage)),
            'description': self._og_search_description(webpage),
            'duration': entries[0]['duration'],
        }

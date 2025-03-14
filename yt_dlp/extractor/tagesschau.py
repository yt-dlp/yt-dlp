from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    extract_attributes,
    get_elements_html_by_attribute,
    int_or_none,
    parse_iso8601,
    try_get,
)


class TagesschauIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:www\.)?tagesschau\.de(?:/[^/#?]+)*/(?P<id>[^/#?\.]+)',
        r'https?://(?:www\.)?(?P<id>tagesschau\.de)/?',
    ]

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
        webpage_id = self._match_id(url)
        webpage = self._download_webpage(url, webpage_id)

        title = self._html_search_regex(
            r'<span[^>]*class="headline"[^>]*>(.+?)</span>',
            webpage, 'title', default=None) or self._og_search_title(webpage, fatal=False)

        entries = []
        media_players = get_elements_html_by_attribute(
            'data-v-type', 'MediaPlayer(?:InlinePlay)?', webpage, escape_value=False)

        for player in media_players:
            data = self._parse_json(extract_attributes(player)['data-v'], webpage_id)
            media_id = data['mc']['pluginData']['trackingSAND@all']['av_content_id']
            video_formats = try_get(data, lambda x: x['mc']['streams'][0]['media'])
            if not video_formats:
                continue
            formats = []
            for video_format in video_formats:
                media_url = video_format.get('url') or ''
                if media_url.endswith('master.m3u8'):
                    formats += self._extract_m3u8_formats(media_url, media_id, 'mp4', m3u8_id='hls')
                elif media_url.endswith('.mp3'):
                    formats.append({
                        'url': media_url,
                        'vcodec': 'none',
                        'format_note': video_format.get('forcedLabel'),
                    })
            if not formats:
                continue
            entries.append({
                'id': media_id,
                'title': try_get(data, lambda x: x['mc']['meta']['title']),
                'duration': int_or_none(try_get(data, lambda x: x['mc']['meta']['durationSeconds'])),
                'formats': formats,
            })

        if not entries:
            raise UnsupportedError(url)

        if len(entries) > 1 and self._yes_playlist(
                webpage_id, entries[0]['id'], playlist_label='all media on', video_label='file'):
            return self.playlist_result(entries, webpage_id, title)

        return {
            'id': entries[0]['id'],
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': entries[0]['formats'],
            'timestamp': parse_iso8601(self._html_search_meta('date', webpage)),
            'description': self._og_search_description(webpage),
            'duration': entries[0]['duration'],
        }

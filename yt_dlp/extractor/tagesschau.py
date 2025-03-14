from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    extract_attributes,
    get_elements_html_by_attribute,
    int_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


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
        media_players = get_elements_html_by_attribute(
            'data-v-type', 'MediaPlayer(?:InlinePlay)?', webpage, escape_value=False)

        entries = []
        for player in media_players:
            data = self._parse_json(extract_attributes(player)['data-v'], webpage_id)
            media_id = traverse_obj(data, ('mc', 'pluginData', (
                ('trackingSAND@all', 'av_content_id'),
                ('trackingPiano@all', 'avContent', 'av_content_id'),
                ('trackingAgf@all', 'playerID')), any))
            if not media_id:
                self.report_warning('Skipping unrecognized media file')
                continue

            entry = {
                'id': media_id,
                **traverse_obj(data, {
                    'title': ('mc', (
                        ('pluginData', 'trackingPiano@all', 'avContent', 'av_content'),
                        ('meta', 'title')), any),
                    'duration': ('mc', 'meta', 'durationSeconds', {int_or_none}),
                    'thumbnail': (
                        'pc', 'generic', 'imageTemplateConfig', 'size', -1,
                        'value', {lambda v: (v + '.webp') if v else None}),
                    'timestamp': (
                        'mc', 'pluginData', 'trackingPiano@all', 'avContent',
                        'd:av_publication_date', {parse_iso8601}),
                }),
            }
            input_formats = traverse_obj(data, (
                'mc', 'streams', 0, 'media', lambda _, v: url_or_none(v.get('url'))), default=[])

            formats = []
            for input_format in input_formats:
                file_url = input_format['url']
                if file_url.endswith('master.m3u8'):
                    formats = self._extract_m3u8_formats(file_url, media_id, 'mp4', m3u8_id='hls')
                    break
                if file_url.endswith('.mp3'):
                    formats.append(traverse_obj(input_format, {
                        'url': 'url',
                        'vcodec': {lambda _: 'none'},
                        'format_note': ('forcedLabel', {str}),
                    }))
            if not formats:
                self.report_warning(f'Skipping file {media_id} because it has no formats')
                continue
            entry['formats'] = formats
            entries.append(entry)

        if not entries:
            raise UnsupportedError(url)

        if len(entries) > 1 and self._yes_playlist(
                webpage_id, entries[0]['id'], playlist_label='all media on', video_label='file'):
            title = self._html_search_regex(
                r'<span[^>]*class="headline"[^>]*>(.+?)</span>',
                webpage, 'title', default=None) or self._og_search_title(webpage, fatal=False)
            return self.playlist_result(entries, webpage_id, title)

        return entries[0]

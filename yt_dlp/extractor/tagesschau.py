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
        # Single video without recommendations
        'url': 'http://www.tagesschau.de/multimedia/video/video-102143.html',
        'md5': 'ccb9359bf8c4795836e43759f3408a93',
        'info_dict': {
            'id': 'video-102143',
            'ext': 'mp4',
            'title': 'Regierungsumbildung in Athen: Neue Minister in Griechenland vereidigt',
            'duration': 138,
            'thumbnail': 'https://images.tagesschau.de/image/eb0b0d74-03ac-45ec-9300-0851fd6823d3/AAABj-POS-g/AAABkZLhkrw/16x9-1280/sendungslogo-tagesschau-100.webp',
            'timestamp': 1437250200,
            'upload_date': '20150718',
        },
    }, {
        # Single video embedded
        'url': 'https://www.tagesschau.de/multimedia/sendung/tagesschau_20_uhr/video-102143~player.html',
        'md5': 'ccb9359bf8c4795836e43759f3408a93',
        'info_dict': {
            'id': 'video-102143',
            'ext': 'mp4',
            'title': 'Regierungsumbildung in Athen: Neue Minister in Griechenland vereidigt',
            'duration': 138,
            'thumbnail': 'https://images.tagesschau.de/image/eb0b0d74-03ac-45ec-9300-0851fd6823d3/AAABj-POS-g/AAABkZLhkrw/16x9-1280/sendungslogo-tagesschau-100.webp',
            'timestamp': 1437250200,
            'upload_date': '20150718',
        },
    }, {
        # Single video with recommendations, `--no-playlist`
        'url': 'http://www.tagesschau.de/multimedia/sendung/ts-5727.html',
        'md5': '5c15e8f3da049e48829ec9786d835536',
        'info_dict': {
            'id': 'video-45741',
            'ext': 'mp4',
            'title': 'tagesschau 20:00 Uhr',
            'duration': 932,
            'thumbnail': 'https://images.tagesschau.de/image/eb0b0d74-03ac-45ec-9300-0851fd6823d3/AAABj-POS-g/AAABkZLhkrw/16x9-1280/sendungslogo-tagesschau-100.webp',
            'timestamp': 1417723200,
            'upload_date': '20141204',
        },
        'params': {'noplaylist': True},
    }, {
        # Single audio embedded
        'url': 'https://www.tagesschau.de/multimedia/audio/audio-157831~player.html',
        'md5': '4bff8f23504df56a0d86ed312d654182',
        'info_dict': {
            'id': 'audio-157831',
            'ext': 'mp3',
            'title': 'EU-Gipfel: Im Verbrennerstreit hat Deutschland maximalen Schaden angerichtet',
            'duration': 200,
            'thumbnail': 'https://images.tagesschau.de/image/197a5977-3f5f-4c21-8c08-fad6ecb4b493/AAABj864C3w/AAABkZLhkrw/16x9-1280/default-audioplayer-100.webp',
            'timestamp': 1679687280,
            'upload_date': '20230324',
        },
    }, {
        # Single audio with recommendations, `--no-playlist`
        'url': 'https://www.tagesschau.de/multimedia/audio/audio-157831.html',
        'md5': '4bff8f23504df56a0d86ed312d654182',
        'info_dict': {
            'id': 'audio-157831',
            'ext': 'mp3',
            'title': 'EU-Gipfel: Im Verbrennerstreit hat Deutschland maximalen Schaden angerichtet',
            'duration': 200,
            'thumbnail': 'https://images.tagesschau.de/image/197a5977-3f5f-4c21-8c08-fad6ecb4b493/AAABj864C3w/AAABkZLhkrw/16x9-1280/default-audioplayer-100.webp',
            'timestamp': 1679687280,
            'upload_date': '20230324',
        },
        'params': {'noplaylist': True},
    }, {
        # Article with multimedia content, `--no-playlist`
        'url': 'https://www.tagesschau.de/inland/bundestagswahl/bundestagswahl-ergebnisse-104.html',
        'md5': 'f72b42f213f632dbbe76551fabebcaef',
        'info_dict': {
            'id': 'video-1437570',
            'ext': 'mp4',
            'title': 'Union mit Kanzlerkandidat Merz gewinnt Bundestagswahl: Parteienlandschaft im Umbruch',
            'duration': 181,
            'thumbnail': 'https://images.tagesschau.de/image/ab8aa6ce-4fd5-4c1e-921d-807b07848a80/AAABlTZ3CAQ/AAABkZLpihI/20x9-1280/union-wahl-siegesfeier-100.webp',
            'timestamp': 1740401379,
            'upload_date': '20250224',
        },
        'params': {'noplaylist': True},
    }, {
        # Topic page with multimedia content, `--no-playlist`
        'url': 'https://www.tagesschau.de/thema/em_2024',
        'md5': '07be4d381753e8411b527c8f0a36229f',
        'info_dict': {
            'id': 'audio-195242',
            'ext': 'mp3',
            'title': 'Optimistische Verbraucherstimmung kommt an der Börse nicht an ',
            'thumbnail': 'https://images.tagesschau.de/image/490fbbe9-1718-4fe0-8f51-538a3182d28e/AAABkOOc5Z0/AAABkZLpihI/20x9-1280/em-2024-fans-100.webp',
            'timestamp': 1721825201,
            'upload_date': '20240724',
        },
        'params': {'noplaylist': True},
    }, {
        # Playlist, single video with recommendations
        'url': 'http://www.tagesschau.de/multimedia/sendung/ts-5727.html',
        'info_dict': {
            'id': 'ts-5727',
            'title': 'tagesschau',
        },
        'playlist_mincount': 8,
    }, {
        # Playlist, single audio with recommendations
        'url': 'https://www.tagesschau.de/multimedia/audio/audio-157831.html',
        'info_dict': {
            'id': 'audio-157831',
            'title': 'EU-Gipfel: Im Verbrennerstreit hat Deutschland maximalen Schaden angerichtet',
        },
        'playlist_mincount': 5,
    }, {
        # Playlist, article with multimedia content
        'url': 'https://www.tagesschau.de/inland/bundestagswahl/bundestagswahl-ergebnisse-104.html',
        'info_dict': {
            'id': 'bundestagswahl-ergebnisse-104',
            'title': 'Vorläufiges Ergebnis der Bundestagswahl: Union stärkste Kraft, FDP und BSW draußen',
        },
        'playlist_mincount': 20,
    }, {
        # Playlist, topic page with multimedia content
        'url': 'https://www.tagesschau.de/thema/em_2024',
        'info_dict': {
            'id': 'em_2024',
            'title': 'EM 2024',
        },
        'playlist_mincount': 10,
    }, {
        # Podcast feed
        'url': 'https://www.tagesschau.de/multimedia/podcast/11km/11km-feed-100.html',
        'info_dict': {
            'id': '11km-feed-100',
            'title': '11KM: der tagesschau-Podcast',
        },
        'playlist_mincount': 250,
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
        'url': 'http://www.tagesschau.de/wirtschaft/faq-freihandelszone-eu-usa-101.html',
        'only_matching': True,
    }, {
        'url': 'https://www.tagesschau.de',
        'only_matching': True,
    }, {
        'url': 'https://www.tagesschau.de/',
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
            title = self._html_search_meta(
                ['og:title', 'title', 'twitter:title'], webpage, 'title', fatal=False)
            return self.playlist_result(entries, webpage_id, title)

        return entries[0]

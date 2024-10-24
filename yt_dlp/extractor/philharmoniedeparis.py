from .common import InfoExtractor
from ..utils import try_get


class PhilharmonieDeParisIE(InfoExtractor):
    IE_DESC = 'Philharmonie de Paris'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            live\.philharmoniedeparis\.fr/(?:[Cc]oncert/|embed(?:app)?/|misc/Playlist\.ashx\?id=)|
                            pad\.philharmoniedeparis\.fr/(?:doc/CIMU/|player\.aspx\?id=)|
                            philharmoniedeparis\.fr/fr/live/concert/|
                            otoplayer\.philharmoniedeparis\.fr/fr/embed/
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://philharmoniedeparis.fr/fr/live/concert/1129666-danses-symphoniques',
        'md5': '24bdb7e86c200c107680e1f7770330ae',
        'info_dict': {
            'id': '1129666',
            'ext': 'mp4',
            'title': 'Danses symphoniques. Orchestre symphonique Divertimento - Zahia Ziouani. Bizet, de Falla, Stravinski, Moussorgski, Saint-Saëns',
        },
    }, {
        'url': 'https://philharmoniedeparis.fr/fr/live/concert/1032066-akademie-fur-alte-musik-berlin-rias-kammerchor-rene-jacobs-passion-selon-saint-jean-de-johann',
        'info_dict': {
            'id': '1032066',
            'title': 'Akademie für alte Musik Berlin, Rias Kammerchor, René Jacobs : Passion selon saint Jean de Johann Sebastian Bach',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://philharmoniedeparis.fr/fr/live/concert/1030324-orchestre-philharmonique-de-radio-france-myung-whun-chung-renaud-capucon-pascal-dusapin-johannes',
        'only_matching': True,
    }, {
        'url': 'http://live.philharmoniedeparis.fr/misc/Playlist.ashx?id=1030324&track=&lang=fr',
        'only_matching': True,
    }, {
        'url': 'https://live.philharmoniedeparis.fr/embedapp/1098406/berlioz-fantastique-lelio-les-siecles-national-youth-choir-of.html?lang=fr-FR',
        'only_matching': True,
    }, {
        'url': 'https://otoplayer.philharmoniedeparis.fr/fr/embed/1098406?lang=fr-FR',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        config = self._download_json(
            f'https://otoplayer.philharmoniedeparis.fr/fr/config/{video_id}.json', video_id, query={
                'id': video_id,
                'lang': 'fr-FR',
            })

        def extract_entry(source):
            if not isinstance(source, dict):
                return
            title = source.get('title')
            if not title:
                return
            files = source.get('files')
            if not isinstance(files, dict):
                return
            format_urls = set()
            formats = []
            for format_id in ('mobile', 'desktop'):
                format_url = try_get(
                    files, lambda x: x[format_id]['file'], str)
                if not format_url or format_url in format_urls:
                    continue
                format_urls.add(format_url)
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            if not formats and not self.get_param('ignore_no_formats'):
                return
            return {
                'title': title,
                'formats': formats,
                'thumbnail': files.get('thumbnail'),
            }
        info = extract_entry(config)
        if info:
            info.update({
                'id': video_id,
            })
            return info
        entries = []
        for num, chapter in enumerate(config['chapters'], start=1):
            entry = extract_entry(chapter)
            if entry is None:
                continue
            entry['id'] = f'{video_id}-{num}'
            entries.append(entry)

        return self.playlist_result(entries, video_id, config.get('title'))

from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj, parse_duration, unified_timestamp


class RTVSLOIE(InfoExtractor):
    IE_NAME = 'rtvslo.si'
    _VALID_URL = r'https?://(?:(?:365|4d)\.rtvslo.si/arhiv/[^/?#&;]+|(?:www\.)?rtvslo\.si/rtv365/arhiv)/(?P<id>(\d+))'
    _API_BASE = 'https://api.rtvslo.si/ava/{}/{}?client_id=82013fb3a531d5414f478747c1aca622'
    _GEO_COUNTRIES = ['SI']
    _TESTS = [
        {
            'url': 'https://www.rtvslo.si/rtv365/arhiv/174842550?s=tv',
            'info_dict': {
                'id': '174842550',
                'ext': 'mp4',
                'release_timestamp': 1643140032,
                'upload_date': '20220125',
                'series': 'Dnevnik',
                'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/92/dnevnik_3_wide2.jpg',
                'description': 'md5:76a18692757aeb8f0f51221106277dd2',
                'timestamp': 1643137046,
                'title': 'Dnevnik',
                'series_id': '92',
                'release_date': '20220125',
                'duration': 1789,
            },
        }, {
            'url': 'https://365.rtvslo.si/arhiv/utrip/174843754',
            'info_dict': {
                'id': '174843754',
                'ext': 'mp4',
                'series_id': '94',
                'release_date': '20220129',
                'timestamp': 1643484455,
                'title': 'Utrip',
                'duration': 813,
                'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/94/utrip_1_wide2.jpg',
                'description': 'md5:77f2892630c7b17bb7a5bb84319020c9',
                'release_timestamp': 1643485825,
                'upload_date': '20220129',
                'series': 'Utrip',
            },
        }, {
            'url': 'https://365.rtvslo.si/arhiv/il-giornale-della-sera/174844609',
            'info_dict': {
                'id': '174844609',
                'ext': 'mp3',
                'series_id': '106615841',
                'title': 'Il giornale della sera',
                'duration': 1328,
                'series': 'Il giornale della sera',
                'timestamp': 1643743800,
                'release_timestamp': 1643745424,
                'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/il-giornale-della-sera_wide2.jpg',
                'upload_date': '20220201',
                'bitrate': 128000,
                'release_date': '20220201',
            },

        }, {
            'url': 'https://4d.rtvslo.si/arhiv/dnevnik/174842550',
            'only_matching': True
        }
    ]

    def _real_extract(self, url):
        v_id = self._match_id(url)
        meta = self._download_json(self._API_BASE.format('getRecordingDrm', v_id), v_id).get('response')
        date = unified_timestamp(meta.get('broadcastDate') or meta.get('broadcastDates')[0])

        thumbs = [{'id': k, 'url': v} for (k, v) in meta.get('images').items()]
        SUB_LANGS_MAP = {'Slovenski': 'sl', }

        subs = {}
        for s in traverse_obj(meta, 'subs', 'subtitles', default={}):
            if s.get('language') in SUB_LANGS_MAP.keys():
                s['language'] = SUB_LANGS_MAP[s['language']]
            if not subs.get(s.get('language'), False):
                subs[s.get('language')] = []
            subs[s.get('language')].append({'url': s.get('file'), 'format': s.get('format').lower()})

        jwt = meta.get('jwt')
        if not jwt:
            raise ExtractorError('Site did not provide an authentication token, cannot proceed.')

        media = self._download_json(self._API_BASE.format('getMedia', v_id) + f'&jwt={jwt}', v_id).get('response')

        formats = []
        if media.get('addaptiveMedia', False):
            formats = self._extract_wowza_formats(
                traverse_obj(media, ('addaptiveMedia', 'hls_sec'), expected_type=str),
                v_id, skip_protocols=['smil'])
        for strm in ('http', 'https'):
            for f in media.get('mediaFiles'):
                if traverse_obj(f, ('streams', strm)):
                    formats.append({
                        'bitrate': f.get('bitrate'),
                        'url': traverse_obj(f, ('streams', strm)),
                        'filesize': f.get('filesize'),
                        'width': f.get('width'),
                        'height': f.get('height'),
                        'ext': f.get('mediaType').lower(),
                        'format_id': f'files_{strm}_{f.get("mediaType").lower()}_{f.get("bitrate")}'
                    })

        if media.get('addaptiveMedia_sl', False):
            for f in self._extract_wowza_formats(
                traverse_obj(media, ('addaptiveMedia_sl', 'hls_sec')), v_id, skip_protocols=['smil']
            ):
                f.update({'format_note': 'Sign language interpretation', 'preference': -10})
                formats.append(f)
        for strm in ('http', 'https'):
            for f in media.get('mediaFiles_sl'):
                if traverse_obj(f, ('streams', strm)):
                    formats.append({
                        'bitrate': f.get('bitrate'),
                        'url': traverse_obj(f, ('streams', strm)),
                        'filesize': f.get('filesize'),
                        'width': f.get('width'),
                        'height': f.get('height'),
                        'ext': f.get('mediaType').lower(),
                        'format_id': f'files-sl_{strm}_{f.get("mediaType").lower()}_{f.get("bitrate")}',
                        'format_note': 'Sign language interpretation',
                        'preference': -10
                    })

        self._sort_formats(formats)

        if any('intermission.mp4' in x.get('url', '') for x in formats):
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
        if any('dummy_720p.mp4' in x.get('manifest_url', '') for x in formats) and meta.get('stub', '') == 'error':
            raise ExtractorError(f'{self.IE_NAME} said: Clip not available', expected=True)

        return {
            'thumbnails': thumbs,
            'subtitles': subs,
            'title': meta.get('title'),
            'id': v_id,
            'description': meta.get('description'),
            'formats': formats,
            'timestamp': date,
            'release_timestamp': unified_timestamp(meta.get('recordingDate')),
            'duration': meta.get('duration') or parse_duration(meta.get('length')),
            'webpage_url': ''.join(traverse_obj(meta, ('canonical', ('domain', 'path')))),
            'tags': meta.get('genre'),
            'series': meta.get('showName'),
            'series_id': meta.get('showId'),
        }

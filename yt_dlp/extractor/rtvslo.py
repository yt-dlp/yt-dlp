from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj, parse_duration, unified_timestamp


class RTVSLOIE(InfoExtractor):
    IE_NAME = 'rtvslo.si'
    _VALID_URL = r'https?://((365|4d)\.rtvslo.si/arhiv/[^/?#&;]+|(www\.)?rtvslo\.si/rtv365/arhiv)/(?P<id>([0-9]+))'
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

        thumbs = [{'url': v, 'id': k} for (k, v) in meta.get('images').items()]
        subs = {}
        SUB_LANGS_MAP = {'Slovenski': 'sl', }

        for s in meta.get('subtitles', []):
            if s.get('language') in SUB_LANGS_MAP.keys():
                s['language'] = SUB_LANGS_MAP[s['language']]
            if not subs.get(s.get('language'), False):
                subs[s.get('language')] = []
            subs[s.get('language')].append({'url': s.get('file'), 'format': s.get('format').lower()})

        jwt = meta.get('jwt')

        def _determine_extract_func(name):
            if name in ('hls', 'hls_sec'):
                return self._extract_m3u8_formats
            elif name == 'mpeg-dash':
                return self._extract_mpd_formats
            elif name == 'jwplayer':
                return self._extract_smil_formats
            else:
                return lambda x, y: {}

        def _extract_media_file_formats(formats, media_source_key):
            return [[_determine_extract_func(src)(url, v_id) or [{
                'bitrate': f.get('bitrate'),
                'url': url,
                'filesize': f.get('filesize'),
                'width': f.get('width'),
                'height': f.get('height'),
                'ext': f.get('mediaType').lower(),
                'format_id': f'{media_source_key}_{f.get("mediaType").lower()}_{f.get("bitrate")}_{src}'
            }] for src, url in f.get('streams', {}).items()] for f in formats]

        media = self._download_json(self._API_BASE.format('getMedia', v_id) + f'&jwt={jwt}', v_id).get('response')

        formats = []
        [[formats.extend(g) for g in f] for f in _extract_media_file_formats(media.get('mediaFiles_sl', {}), 'files_sl')]
        [[formats.extend(g) for g in f] for f in _extract_media_file_formats(media.get('mediaFiles', {}), 'files')]

        def _extract_adaptive(data):
            return [_determine_extract_func(name)(url, v_id) for name, url in data.items()]
        [formats.extend(g) for g in _extract_adaptive(media.get('addaptiveMedia', {}))]
        [formats.extend(g) for g in _extract_adaptive(media.get('addaptiveMedia_sl', {}))]
        self._sort_formats(formats)

        if any('intermission.mp4' in x.get('url', '') for x in formats):
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
        if any('dummy_720p.mp4' in x.get('manifest_url', '') for x in formats) and meta.get('stub', '') == 'error':
            raise ExtractorError(f'{self.IE_NAME} said: Clip not available')

        info = {
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

        return info

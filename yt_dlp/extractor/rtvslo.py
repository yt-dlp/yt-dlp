from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_duration,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class RTVSLOIE(InfoExtractor):
    IE_NAME = 'rtvslo.si'
    _VALID_URL = r'''(?x)
        https?://(?:
            (?:365|4d)\.rtvslo.si/arhiv/[^/?#&;]+|
            (?:www\.)?rtvslo\.si/rtv365/arhiv
        )/(?P<id>\d+)'''
    _GEO_COUNTRIES = ['SI']

    _API_BASE = 'https://api.rtvslo.si/ava/{}/{}?client_id=82013fb3a531d5414f478747c1aca622'
    SUB_LANGS_MAP = {'Slovenski': 'sl'}

    _TESTS = [
        {
            'url': 'https://www.rtvslo.si/rtv365/arhiv/174842550?s=tv',
            'info_dict': {
                'id': '174842550',
                'ext': 'flv',
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
                'tbr': 128000,
                'release_date': '20220201',
            },

        }, {
            'url': 'https://4d.rtvslo.si/arhiv/dnevnik/174842550',
            'only_matching': True
        }
    ]

    def _real_extract(self, url):
        v_id = self._match_id(url)
        meta = self._download_json(self._API_BASE.format('getRecordingDrm', v_id), v_id)['response']

        thumbs = [{'id': k, 'url': v, 'http_headers': {'Accept': 'image/jpeg'}}
                  for k, v in (meta.get('images') or {}).items()]

        subs = {}
        for s in traverse_obj(meta, 'subs', 'subtitles', default=[]):
            lang = self.SUB_LANGS_MAP.get(s.get('language'), s.get('language') or 'und')
            subs.setdefault(lang, []).append({
                'url': s.get('file'),
                'ext': traverse_obj(s, 'format', expected_type=str.lower),
            })

        jwt = meta.get('jwt')
        if not jwt:
            raise ExtractorError('Site did not provide an authentication token, cannot proceed.')

        media = self._download_json(self._API_BASE.format('getMedia', v_id), v_id, query={'jwt': jwt})['response']

        formats = []
        adaptive_url = traverse_obj(media, ('addaptiveMedia', 'hls_sec'), expected_type=url_or_none)
        if adaptive_url:
            formats = self._extract_wowza_formats(adaptive_url, v_id, skip_protocols=['smil'])

        adaptive_url = traverse_obj(media, ('addaptiveMedia_sl', 'hls_sec'), expected_type=url_or_none)
        if adaptive_url:
            for f in self._extract_wowza_formats(adaptive_url, v_id, skip_protocols=['smil']):
                formats.append({
                    **f,
                    'format_id': 'sign-' + f['format_id'],
                    'format_note': 'Sign language interpretation', 'preference': -10,
                    'language': (
                        'slv' if f.get('language') == 'eng' and f.get('acodec') != 'none'
                        else f.get('language'))
                })

        formats.extend(
            {
                'url': f['streams'][strm],
                'ext': traverse_obj(f, 'mediaType', expected_type=str.lower),
                'width': f.get('width'),
                'height': f.get('height'),
                'tbr': f.get('bitrate'),
                'filesize': f.get('filesize'),
            }
            for strm in ('http', 'https')
            for f in media.get('mediaFiles') or []
            if traverse_obj(f, ('streams', strm))
        )

        if any('intermission.mp4' in x['url'] for x in formats):
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
        if any('dummy_720p.mp4' in x.get('manifest_url', '') for x in formats) and meta.get('stub') == 'error':
            raise ExtractorError(f'{self.IE_NAME} said: Clip not available', expected=True)

        return {
            'id': v_id,
            'webpage_url': ''.join(traverse_obj(meta, ('canonical', ('domain', 'path')))),
            'title': meta.get('title'),
            'formats': formats,
            'subtitles': subs,
            'thumbnails': thumbs,
            'description': meta.get('description'),
            'timestamp': unified_timestamp(traverse_obj(meta, 'broadcastDate', ('broadcastDates', 0))),
            'release_timestamp': unified_timestamp(meta.get('recordingDate')),
            'duration': meta.get('duration') or parse_duration(meta.get('length')),
            'tags': meta.get('genre'),
            'series': meta.get('showName'),
            'series_id': meta.get('showId'),
        }

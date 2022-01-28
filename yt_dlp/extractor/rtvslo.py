from .common import InfoExtractor
from ..utils import traverse_obj, parse_duration, unified_timestamp


class RTVSLOIE(InfoExtractor):
    IE_NAME = 'rtvslo.si'
    _VALID_URL = r'https?://(www\.)?rtvslo\.si\/rtv365\/arhiv\/(?P<id>[0-9]+)'
    'https://(4d|365).rtvslo.si/arhiv/dnevnik/(?P<id>[0-9]+)'
    _API_BASE = 'https://api.rtvslo.si/ava/{}/{}?client_id=82013fb3a531d5414f478747c1aca622'
    _GEO_COUNTRIES = ['SI']
    _TESTS = [{
        'url': 'https://www.rtvslo.si/rtv365/arhiv/174842550?s=tv',
        'only_matching': True
    }]

    def _real_extract(self, url):
        v_id = self._match_id(url)
        meta = self._download_json(self._API_BASE.format('getRecordingDrm', v_id), v_id).get('response')
        date = unified_timestamp(meta.get('broadcastDate') or meta.get('broadcastDates')[0])

        thumbs = [{'url': v, 'id': k} for (k, v) in meta.get('images').items()]
        subs = {}
        SUB_LANGS_MAP = {'Slovenski': 'sl', }

        for s in meta.get('subtitles'):
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
        [formats.extend(g) for g in _extract_adaptive(media.get('addaptiveMedia'))]
        [formats.extend(g) for g in _extract_adaptive(media.get('addaptiveMedia_sl'))]
        self._sort_formats(formats)

        geoblocked = meta.get('geoblocked', 0) == 1
        must_circumvent_geoblock = None  # TODO check whether playlist redirects to https://vodstr.rtvslo.si/encrypted11/intermission.mp4/playlist.m3u8
        paywall = bool(meta.get('payTv')) or meta.get('source') == 'ZKP'
        must_circumvent_paywall = None  # TODO check whether media data returns mediaFiles[0][stream] elements contain: http://progressive.rtvslo.si/encrypted06/preroll/payable.mp4
        

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

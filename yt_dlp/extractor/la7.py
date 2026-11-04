import base64
import json

from .common import (
    ExtractorError,
    InfoExtractor,
)
from ..utils import (
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class LA7IE(InfoExtractor):
    IE_NAME = 'la7play.it'
    _VALID_URL = r'https?://(?:www\.)?la7play\.it(?P<path>/(?:[^/?#]+/)*(?P<id>[^/?#]+))'

    _TESTS = [{
        # Full episode, "rivedila7" path segment (entity type NodeReplica)
        'url': 'https://www.la7play.it/bellidentrobellifuori/rivedila7/belli-dentro-belli-fuori-puntata-del-932024-09-03-2024-530432',
        'md5': '67bf76fb2eb52386137cae68e8687edf',
        'info_dict': {
            'id': 'belli-dentro-belli-fuori-puntata-del-932024-09-03-2024-530432',
            'ext': 'mp4',
            'title': 'Belli dentro belli fuori - Puntata del  9/3/2024',
            'duration': 1796,
            'thumbnail': 'https://images.la7play.it/video/111/0_po1fdrop/belli-dentro-belli-fuori-puntata-del-9-3-2024/scena-854x480.webp',
            'timestamp': 1709981573,
            'upload_date': '20240309',
            'modified_timestamp': 1710144374,
            'modified_date': '20240311',
        },
    }, {
        # Full episode, "episodi" path segment (entity type NodeReplica)
        'url': 'https://www.la7play.it/mercanti-dellanima-lai-e-il-nostro-futuro/episodi/st-1-episodio-2-395896',
        'md5': 'bbb51a9313f8bdaa1ee777edfedb1207',
        'info_dict': {
            'id': 'st-1-episodio-2-395896',
            'ext': 'mp4',
            'title': 'St. 1 Episodio 2',
            'description': 'md5:196f0586d0bc174addda6af1d3d1e574',
            'duration': 3946,
            'thumbnail': 'https://images.la7play.it/video/0/400/0_0usrx8nr_0_wwaki72o_2/st-1-episodio-2/scena-854x480.webp',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1791845946,
            'upload_date': '20261012',
            'modified_timestamp': 1792070405,
            'modified_date': '20261015',
        },
    }, {
        # Full episode, "puntate" path segment (entity type NodeReplica)
        'url': 'https://www.la7play.it/in-onda/puntate/puntata-del-1-11-2026-398431',
        'md5': 'd67876ec61b92393fdf09e2dc2575982',
        'info_dict': {
            'id': 'puntata-del-1-11-2026-398431',
            'ext': 'mp4',
            'title': 'D\'Alema, un ex comunista tra il \'68 e Meloni - Puntata del 1/11/2026',
            'description': 'md5:cd6bf6963b1de91d4c7ac62b26dc1c31',
            'duration': 4406,
            'thumbnail': 'https://images.la7play.it/video/0/406/0_h6jds5l2_0_fh960gys_2/d-alema-un-ex-comunista-tra-il-68-e-meloni-puntata-del-1-11/scena-854x480.webp',
            'season': 'Season 29',
            'season_number': 29,
            'episode': 'Episode 7',
            'episode_number': 7,
            'timestamp': 1793570167,
            'upload_date': '20261101',
            'modified_timestamp': 1793604614,
            'modified_date': '20261102',
        },
    }, {
        # Clip/video (entity type NodeVideo)
        'url': 'https://www.la7play.it/in-onda/video/crisi-in-venezuela-lintervista-a-luciana-castellina-05-01-2026-626950',
        'md5': 'b76230799cbaf16a9550adf0a1859cef',
        'info_dict': {
            'id': 'crisi-in-venezuela-lintervista-a-luciana-castellina-05-01-2026-626950',
            'ext': 'mp4',
            'title': 'Crisi in Venezuela, l\'intervista a Luciana Castellina',
            'duration': 102,
            'description': 'md5:e5b7a733dffc04a24249afd0278b769f',
            'thumbnail': 'https://images.la7play.it/video/111/0_2544fg79/crisi-in-venezuela-l-intervista-a-luciana-castellina/scena-854x480.webp',
            'timestamp': 1767647390,
            'upload_date': '20260105',
            'modified_timestamp': 1767647725,
            'modified_date': '20260105',
        },
    }, {
        # Single path segment
        'url': 'https://www.la7play.it/dream-bike-20-09-2026-393369',
        'md5': '29a2adcda6d8b5b626b9aef19421996e',
        'info_dict': {
            'id': 'dream-bike-20-09-2026-393369',
            'ext': 'mp4',
            'title': 'Puntata del 23/9/2026',
            'thumbnail': 'https://images.la7play.it/video/0/397/0_c4lgs673_0_zzscdbmp_2/puntata-del-23-9-2026/scena-854x480.webp',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1789858785,
            'upload_date': '20260919',
            'modified_timestamp': 1793618784,
            'modified_date': '20261102',
        },
    }, {
        # Video with reconstructed direct HTTPS URL
        'url': 'https://www.la7play.it/otto-e-mezzo/rivedila7/otto-e-mezzo-26-06-2026-650566',
        'md5': 'eeca111e2b4f97e46d693f565fcafef9',
        'info_dict': {
            'id': 'otto-e-mezzo-26-06-2026-650566',
            'ext': 'mp4',
            'title': 'La regola del caos - Otto e Mezzo - Puntata del 26/6/2026',
            'duration': 2197,
            'thumbnail': 'https://images.la7play.it/video/111/0_bbomr2tk/la-regola-del-caos-otto-e-mezzo-puntata-del-26-6-2026/scena-854x480.webp',
            'timestamp': 1782503632,
            'upload_date': '20260626',
            'modified_timestamp': 1782540689,
            'modified_date': '20260627',
        },
        'params': {
            'format': 'b[protocol=https]',
        },
    }, {
        # Video with subtitiles
        'url': 'https://www.la7play.it/piazzapulita/video/dal-dibattito/bortone-aboliamo-la-parola-maranza-e-classista-e-razzista-30-10-2026-398286',
        'md5': '5b3a510d617e77b0ec890fbb31378136',
        'info_dict': {
            'id': 'bortone-aboliamo-la-parola-maranza-e-classista-e-razzista-30-10-2026-398286',
            'ext': 'mp4',
            'title': 'Bortone: "Aboliamo la parola maranza, è classista e razzista"',
            'description': 'md5:f626210b971efed522d6baf348704209',
            'duration': 82,
            'thumbnail': 'https://images.la7play.it/video/111/0_r2k05j89/bortone-aboliamo-la-parola-maranza-e-classista-e-razzista/scena-854x480.webp',
            'timestamp': 1793348588,
            'upload_date': '20261030',
            'modified_timestamp': 1793348708,
            'modified_date': '20261030',
            'subtitles': 'count:2',
        },
    }]
    _HOST = 'https://awsvodpkg.iltrovatore.it'

    # Endpoints IDs are hardcoded in the JS bundle,
    # but may never be called because of Next.js hydration.
    # Actual call parameters can be extracted via the mobile app:
    # https://play.google.com/store/apps/details?id=it.la7.it
    def _call_api(self, video_id, endpoint_desc, endpoint_id, payload):
        serialized = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        return self._download_json(
            f'https://www.la7play.it/api/gql/{endpoint_id}/{serialized}', video_id,
            note=f'Downloading {endpoint_desc}',
            errnote=f'Failed to download {endpoint_desc}')['data']['route']

    def _generate_mp4_url(self, quality, m3u8_formats):
        for f in m3u8_formats:
            if quality.startswith('//'):
                quality = quality[1:]
            if f['vcodec'] == 'none' or quality not in f['url']:
                continue

            http_f = f.copy()
            del http_f['manifest_url']
            http_f.update({
                'format_id': http_f['format_id'].replace('hls-', 'https-'),
                'url': f'{self._HOST}{quality}.mp4',
                'protocol': 'https',
            })
            return http_f
        return None

    def _real_extract(self, url):
        video_id, path = self._match_valid_url(url).group('id', 'path')
        type_info = self._call_api(
            video_id, 'entity type info', 'cf87a75d078158e9', {'path': path})

        type_name = traverse_obj(type_info, ('entity', '__typename', {str}))
        self.write_debug(f'Entity type: {type_name}')
        match (type_name):
            case 'NodeVideo':
                endpoint_id = '9e6877beb0b950cb'
            case 'NodeReplica':
                endpoint_id = 'a9448166e3cd0b3d'
            case 'NodeEventoSingolo':
                endpoint_id = '150c651a74b13c6d'
            case 'NodeLiveStreaming':
                self.report_drm(video_id)
            case 'NodePaginaHub' | 'NodeGuidaTv' | 'NodeAggregatoreTassonomie' | None:
                raise ExtractorError('There is no video for this URL', expected=True)
            case _:
                raise ExtractorError(f'Unsupported entity type "{type_name}"')

        data = self._call_api(video_id, 'video data', endpoint_id, {
            'path': traverse_obj(type_info, ('entity', 'path', {str})) or path,
        })['entity']

        video_path = data['uploadVideo']['cf_remote_url'].replace('.mp4', '')

        formats = self._extract_mpd_formats(
            f'{self._HOST}/local/dash/,{video_path},.mp4.urlset/manifest.mpd',
            video_id, mpd_id='dash', fatal=False)
        m3u8_formats = self._extract_m3u8_formats(
            f'{self._HOST}/local/hls/,{video_path},.mp4.urlset/master.m3u8',
            video_id, 'mp4', m3u8_id='hls', fatal=False)
        formats.extend(m3u8_formats)

        # Only older videos have direct HTTP links
        if traverse_obj(data, ('uploadVideo', 'cf_old_entry_id', {str})):
            for q in filter(None, video_path.split(',')):
                if http_f := self._generate_mp4_url(q, m3u8_formats):
                    formats.append(http_f)

        subtitles = {}
        for sub in traverse_obj(data, ('uploadVideo', 'subtitles', {list})) or []:
            if lang := traverse_obj(sub, ('lang', {str})):
                if url := traverse_obj(sub, ('url', {url_or_none})):
                    subtitles.setdefault(lang, []).append({'url': url})

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('body', 'plainValue', {str}),
                'duration': ('uploadVideo', 'cf_duration', {int_or_none}),
                'season_number': ('uploadVideo', 'stagione', {int_or_none}),
                'episode_number': ('uploadVideo', 'episodio', {int_or_none}),
                'timestamp': ('created', 'timestamp', {int_or_none}),
                'modified_timestamp': ('changed', 'timestamp', {int_or_none}),
                'thumbnail': ('uploadVideo', 'cf_thumbnail_url', {url_or_none}),
            }),
        }

import json

from .common import InfoExtractor
from ..utils import int_or_none, js_to_json


class GediDigitalIE(InfoExtractor):
    _VALID_URL = r'''(?x:(?:https?:)//(?:\w+\.)?
        (?:
            repubblica
            |lastampa
            |ilsecoloxix
            |huffingtonpost
        )\.it/[^?]+(?:/video/(?P<slug>[a-z0-9_-]+)-|/)(?P<id>\d+))'''
    _TESTS = [{
        'url': 'https://video.lastampa.it/politica/il-paradosso-delle-regionali-la-lega-vince-ma-sembra-aver-perso/121559/121683',
        'md5': '6d1238ab5f4753b6f3d9eb396bff8ea3',
        'info_dict': {
            'id': '121683',
            'ext': 'mp4',
            'title': 'Il paradosso delle Regionali: ecco perché la Lega vince ma sembra aver perso',
            'description': 'md5:fad65b086b8b23fd4db66dc1f7a530f9',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-full-.+?\.jpg$',
            'duration': 125,
            'uploader_id': '6210505280001',
        },
    }, {
        'url': 'https://www.repubblica.it/video/tv/2023/10/25/video/maurizio_molinari_israele_sotto_shock_per_le_parole_del_segretario_generale_dellonu-422547542',
        'md5': '3cdb25ee59373cb326dd402c7e18490f',
        'info_dict': {
            'id': '422547542',
            'ext': 'mp4',
            'display_id': 'maurizio_molinari_israele_sotto_shock_per_le_parole_del_segretario_generale_dellonu',
            'title': 'Maurizio Molinari: "Israele sotto shock per le parole del segretario generale dell\'Onu"',
            'uploader_id': '6210505280001',
            'duration': 89,
            'thumbnail': 'https://www.repstatic.it/video/photo/2023/10/25/918897/918897-thumb-full-720-molinari_porta_a_porta_24_10_23.jpg',
        },
    }, {
        'url': 'https://roma.repubblica.it/cronaca/2025/05/22/video/giornata_biodiversita_mattarella_si_improvvisa_giardiniere_annaffia_una_piantina_a_castelporziano-424598388/',
        'only_matching': True,
    }, {
        'url': 'https://video.huffingtonpost.it/embed/politica/cotticelli-non-so-cosa-mi-sia-successo-sto-cercando-di-capire-se-ho-avuto-un-malore/29312/29276?responsive=true&el=video971040871621586700',
        'only_matching': True,
    }, {
        'url': 'https://video.repubblica.it/motori/record-della-pista-a-spa-francorchamps-la-pagani-huayra-roadster-bc-stupisce/367415/367963',
        'only_matching': True,
    }, {
        'url': 'https://video.ilsecoloxix.it/sport/cassani-e-i-brividi-azzurri-ai-mondiali-di-imola-qui-mi-sono-innamorato-del-ciclismo-da-ragazzino-incredibile-tornarci-da-ct/66184/66267',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, slug = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, video_id)
        data = self._search_json(
            r'BrightcoveVideoPlayerOptions\s*=', webpage, 'Brightcove video player options', video_id, transform_source=js_to_json,
        )
        streams = json.loads(data['videoSrc'])
        formats = []
        for stream in streams:
            if isinstance(stream, str):
                continue
            if stream['type'] == 'video/mp4':
                bitrate = self._search_regex(r'video-rrtv-(\d+)', stream['src'], 'vbr', None)
                formats.append({
                    'format_id': f'mp4-{bitrate}' if bitrate else 'mp4',
                    'url': stream['src'],
                    'ext': 'mp4',
                    'vcodec': 'avc1',
                    'acodec': 'mp4a',
                    'vbr': int_or_none(bitrate),
                })
            elif stream['type'] == 'application/x-mpegURL':
                new_formats = self._extract_m3u8_formats(stream['src'], video_id)
                for fmt in new_formats:
                    fmt.setdefault('vbr', int_or_none(self._search_regex(r'/hls/_(\d+)/', fmt['url'], 'vbr', None)))
                formats.extend(new_formats)
            elif stream['type'] == 'audio/mp3':
                bitrate = self._search_regex(r'mp3-audio-(\d+)', stream['src'], 'vbr', None)
                formats.append({
                    'format_id': f'mp3-{bitrate}' if bitrate else 'mp3',
                    'url': stream['src'],
                    'ext': 'mp3',
                    'acodec': 'mp3',
                    'abr': int_or_none(bitrate),
                    'tbr': int_or_none(bitrate),
                })
            else:
                formats.append({
                    'format_id': stream['type'],
                    'url': stream['src'],
                })

        return {
            'id': video_id,
            'display_id': slug,
            'title': data.get('videoTitle') or self._html_search_meta(['twitter:title', 'og:title'], webpage),
            'description': self._html_search_meta(['twitter:description', 'og:description', 'description'], webpage, default=None),
            'formats': formats,
            'thumbnail': data.get('posterSrc') or self._og_search_thumbnail(webpage),
            'uploader_id': data.get('accountId'),
            'duration': int_or_none(data.get('videoLenght')),
        }

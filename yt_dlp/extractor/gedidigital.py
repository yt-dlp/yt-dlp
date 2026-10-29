from .common import InfoExtractor
from ..utils import (
    base_url,
    int_or_none,
    join_nonempty,
    js_to_json,
    mimetype2ext,
    url_basename,
    urljoin,
)


class GediDigitalIE(InfoExtractor):
    _VALID_URL = r'''(?x:(?:https?:)//(?:\w+\.)?
        (?:
            repubblica
            |lastampa
            |ilsecoloxix
            |huffingtonpost
        )\.it/[^?]+(?:/video/(?P<slug>[a-z0-9_-]+)-|/)(?P<id>\d+)[?&]?.*)'''
    _EMBED_REGEX = [rf'''(?x)
            (?:
                data-frame-src=|
                <iframe[^\n]+src=
            )
            (["'])(?P<url>{_VALID_URL})\1''']
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

    @staticmethod
    def _sanitize_urls(urls):
        # add protocol if missing
        for i, e in enumerate(urls):
            if e.startswith('//'):
                urls[i] = f'https:{e}'
        # clean iframes urls
        for i, e in enumerate(urls):
            urls[i] = urljoin(base_url(e), url_basename(e))
        return urls

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        return cls._sanitize_urls(tuple(super()._extract_embed_urls(url, webpage)))

    def _real_extract(self, url):
        video_id, slug = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, video_id)
        data = self._search_json(
            r'BrightcoveVideoPlayerOptions\s*=', webpage, 'Brightcove params',
            video_id, transform_source=js_to_json)
        streams = self._parse_json(data['videoSrc'], video_id)
        formats = []
        for stream in streams:
            if isinstance(stream, str):
                continue
            ext = mimetype2ext(stream.get('type'))
            if ext == 'mp4':
                bitrate = self._search_regex(r'video-rrtv-(\d+)', stream['src'], 'vbr', None)
                formats.append({
                    'format_id': join_nonempty('http', ext, bitrate),
                    'url': stream['src'],
                    'ext': ext,
                    'vcodec': 'avc1',
                    'acodec': 'mp4a',
                    'vbr': int_or_none(bitrate),
                })
            elif ext == 'm3u8':
                fmts = self._extract_m3u8_formats(stream['src'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                for fmt in fmts:
                    fmt.setdefault('vbr', int_or_none(
                        self._search_regex(r'/hls/_(\d+)/', fmt['url'], 'vbr', default=None)))
                formats.extend(fmts)
            elif ext == 'mp3':
                bitrate = self._search_regex(r'mp3-audio-(\d+)', stream['src'], 'vbr', None)
                formats.append({
                    'format_id': join_nonempty('http', ext, bitrate),
                    'url': stream['src'],
                    'ext': ext,
                    'acodec': ext,
                    'vcodec': 'none',
                    'abr': int_or_none(bitrate),
                    'tbr': int_or_none(bitrate),
                })
            else:
                formats.append({
                    'format_id': ext,
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

# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    base_url,
    determine_ext,
    int_or_none,
    url_basename,
    urljoin,
)


class GediDigitalIE(InfoExtractor):
    _VALID_URL = r'''(?x)(?P<url>(?:https?:)//video\.
        (?:
            (?:
                (?:espresso\.)?repubblica
                |lastampa
                |ilsecoloxix
                |huffingtonpost
            )|
            (?:
                iltirreno
                |messaggeroveneto
                |ilpiccolo
                |gazzettadimantova
                |mattinopadova
                |laprovinciapavese
                |tribunatreviso
                |nuovavenezia
                |gazzettadimodena
                |lanuovaferrara
                |corrierealpi
                |lasentinella
            )\.gelocal
        )\.it(?:/[^/]+){2,4}/(?P<id>\d+))(?:$|[?&].*)'''
    _TESTS = [{
        'url': 'https://video.lastampa.it/politica/il-paradosso-delle-regionali-la-lega-vince-ma-sembra-aver-perso/121559/121683',
        'md5': '84658d7fb9e55a6e57ecc77b73137494',
        'info_dict': {
            'id': '121683',
            'ext': 'mp4',
            'title': 'Il paradosso delle Regionali: ecco perché la Lega vince ma sembra aver perso',
            'description': 'md5:de7f4d6eaaaf36c153b599b10f8ce7ca',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-full-.+?\.jpg$',
            'duration': 125,
        },
    }, {
        'url': 'https://video.huffingtonpost.it/embed/politica/cotticelli-non-so-cosa-mi-sia-successo-sto-cercando-di-capire-se-ho-avuto-un-malore/29312/29276?responsive=true&el=video971040871621586700',
        'only_matching': True,
    }, {
        'url': 'https://video.espresso.repubblica.it/embed/tutti-i-video/01-ted-villa/14772/14870&width=640&height=360',
        'only_matching': True,
    }, {
        'url': 'https://video.repubblica.it/motori/record-della-pista-a-spa-francorchamps-la-pagani-huayra-roadster-bc-stupisce/367415/367963',
        'only_matching': True,
    }, {
        'url': 'https://video.ilsecoloxix.it/sport/cassani-e-i-brividi-azzurri-ai-mondiali-di-imola-qui-mi-sono-innamorato-del-ciclismo-da-ragazzino-incredibile-tornarci-da-ct/66184/66267',
        'only_matching': True,
    }, {
        'url': 'https://video.iltirreno.gelocal.it/sport/dentro-la-notizia-ferrari-cosa-succede-a-maranello/141059/142723',
        'only_matching': True,
    }, {
        'url': 'https://video.messaggeroveneto.gelocal.it/locale/maria-giovanna-elmi-covid-vaccino/138155/139268',
        'only_matching': True,
    }, {
        'url': 'https://video.ilpiccolo.gelocal.it/dossier/big-john/dinosauro-big-john-al-via-le-visite-guidate-a-trieste/135226/135751',
        'only_matching': True,
    }, {
        'url': 'https://video.gazzettadimantova.gelocal.it/locale/dal-ponte-visconteo-di-valeggio-l-and-8217sos-dei-ristoratori-aprire-anche-a-cena/137310/137818',
        'only_matching': True,
    }, {
        'url': 'https://video.mattinopadova.gelocal.it/dossier/coronavirus-in-veneto/covid-a-vo-un-anno-dopo-un-cuore-tricolore-per-non-dimenticare/138402/138964',
        'only_matching': True,
    }, {
        'url': 'https://video.laprovinciapavese.gelocal.it/locale/mede-zona-rossa-via-alle-vaccinazioni-per-gli-over-80/137545/138120',
        'only_matching': True,
    }, {
        'url': 'https://video.tribunatreviso.gelocal.it/dossier/coronavirus-in-veneto/ecco-le-prima-vaccinazioni-di-massa-nella-marca/134485/135024',
        'only_matching': True,
    }, {
        'url': 'https://video.nuovavenezia.gelocal.it/locale/camion-troppo-alto-per-il-ponte-ferroviario-perde-il-carico/135734/136266',
        'only_matching': True,
    }, {
        'url': 'https://video.gazzettadimodena.gelocal.it/locale/modena-scoperta-la-proteina-che-predice-il-livello-di-gravita-del-covid/139109/139796',
        'only_matching': True,
    }, {
        'url': 'https://video.lanuovaferrara.gelocal.it/locale/due-bombole-di-gpl-aperte-e-abbandonate-i-vigili-bruciano-il-gas/134391/134957',
        'only_matching': True,
    }, {
        'url': 'https://video.corrierealpi.gelocal.it/dossier/cortina-2021-i-mondiali-di-sci-alpino/mondiali-di-sci-il-timelapse-sulla-splendida-olympia/133760/134331',
        'only_matching': True,
    }, {
        'url': 'https://video.lasentinella.gelocal.it/locale/vestigne-centra-un-auto-e-si-ribalta/138931/139466',
        'only_matching': True,
    }, {
        'url': 'https://video.espresso.repubblica.it/tutti-i-video/01-ted-villa/14772',
        'only_matching': True,
    }]

    @staticmethod
    def _sanitize_urls(urls):
        # add protocol if missing
        for i, e in enumerate(urls):
            if e.startswith('//'):
                urls[i] = 'https:%s' % e
        # clean iframes urls
        for i, e in enumerate(urls):
            urls[i] = urljoin(base_url(e), url_basename(e))
        return urls

    @staticmethod
    def _extract_urls(webpage):
        entries = [
            mobj.group('eurl')
            for mobj in re.finditer(r'''(?x)
            (?:
                data-frame-src=|
                <iframe[^\n]+src=
            )
            (["'])(?P<eurl>%s)\1''' % GediDigitalIE._VALID_URL, webpage)]
        return GediDigitalIE._sanitize_urls(entries)

    @staticmethod
    def _extract_url(webpage):
        urls = GediDigitalIE._extract_urls(webpage)
        return urls[0] if urls else None

    @staticmethod
    def _clean_formats(formats):
        format_urls = set()
        clean_formats = []
        for f in formats:
            if f['url'] not in format_urls:
                if f.get('audio_ext') != 'none' and not f.get('acodec'):
                    continue
                format_urls.add(f['url'])
                clean_formats.append(f)
        formats[:] = clean_formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = self._match_valid_url(url).group('url')
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta(
            ['twitter:title', 'og:title'], webpage, fatal=True)
        player_data = re.findall(
            r"PlayerFactory\.setParam\('(?P<type>format|param)',\s*'(?P<name>[^']+)',\s*'(?P<val>[^']+)'\);",
            webpage)

        formats = []
        duration = thumb = None
        for t, n, v in player_data:
            if t == 'format':
                if n in ('video-hds-vod-ec', 'video-hls-vod-ec', 'video-viralize', 'video-youtube-pfp'):
                    continue
                elif n.endswith('-vod-ak'):
                    formats.extend(self._extract_akamai_formats(
                        v, video_id, {'http': 'media.gedidigital.it'}))
                else:
                    ext = determine_ext(v)
                    if ext == 'm3u8':
                        formats.extend(self._extract_m3u8_formats(
                            v, video_id, 'mp4', 'm3u8_native', m3u8_id=n, fatal=False))
                        continue
                    f = {
                        'format_id': n,
                        'url': v,
                    }
                    if ext == 'mp3':
                        abr = int_or_none(self._search_regex(
                            r'-mp3-audio-(\d+)', v, 'abr', default=None))
                        f.update({
                            'abr': abr,
                            'tbr': abr,
                            'acodec': ext,
                            'vcodec': 'none'
                        })
                    else:
                        mobj = re.match(r'^video-rrtv-(\d+)(?:-(\d+))?$', n)
                        if mobj:
                            f.update({
                                'height': int(mobj.group(1)),
                                'vbr': int_or_none(mobj.group(2)),
                            })
                        if not f.get('vbr'):
                            f['vbr'] = int_or_none(self._search_regex(
                                r'-video-rrtv-(\d+)', v, 'abr', default=None))
                    formats.append(f)
            elif t == 'param':
                if n in ['image_full', 'image']:
                    thumb = v
                elif n == 'videoDuration':
                    duration = int_or_none(v)

        self._clean_formats(formats)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_meta(
                ['twitter:description', 'og:description', 'description'], webpage),
            'thumbnail': thumb or self._og_search_thumbnail(webpage),
            'formats': formats,
            'duration': duration,
        }

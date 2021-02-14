# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    base_url,
    url_basename,
    urljoin,
)


class GediBaseIE(InfoExtractor):
    @staticmethod
    def _clean_audio_fmts(formats):
        unique_formats = []
        for f in formats:
            if 'acodec' in f:
                unique_formats.append(f)
        formats[:] = unique_formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        player_data = re.findall(
            r'PlayerFactory\.setParam\(\'(?P<type>.+?)\',\s*\'(?P<name>.+?)\',\s*\'(?P<val>.+?)\'\);',
            webpage)

        formats = []
        audio_fmts = []
        hls_fmts = []
        http_fmts = []
        title = ''
        thumb = ''

        fmt_reg = r'(?P<t>video|audio)-(?P<p>rrtv|hls)-(?P<h>[\w\d]+)(?:-(?P<br>[\w\d]+))?$'
        br_reg = r'video-rrtv-(?P<br>\d+)-'

        for t, n, v in player_data:
            if t == 'format':
                m = re.match(fmt_reg, n)
                if m:
                    # audio formats
                    if m.group('t') == 'audio':
                        if m.group('p') == 'hls':
                            audio_fmts.extend(self._extract_m3u8_formats(
                                v, video_id, 'm4a', m3u8_id='hls', fatal=False))
                        elif m.group('p') == 'rrtv':
                            audio_fmts.append({
                                'format_id': 'mp3',
                                'url': v,
                                'tbr': 128,
                                'ext': 'mp3',
                                'vcodec': 'none',
                                'acodec': 'mp3',
                            })

                    # video formats
                    elif m.group('t') == 'video':
                        # hls manifest video
                        if m.group('p') == 'hls':
                            hls_fmts.extend(self._extract_m3u8_formats(
                                v, video_id, 'mp4', m3u8_id='hls', fatal=False))
                        # direct mp4 video
                        elif m.group('p') == 'rrtv':
                            if not m.group('br'):
                                mm = re.search(br_reg, v)
                            http_fmts.append({
                                'format_id': 'https-' + m.group('h'),
                                'protocol': 'https',
                                'url': v,
                                'tbr': int(m.group('br')) if m.group('br') else
                                (int(mm.group('br')) if mm.group('br') else 0),
                                'height': int(m.group('h'))
                            })

            elif t == 'param':
                if n == 'videotitle':
                    title = v
                if n == 'image_full_play':
                    thumb = v

        title = self._og_search_title(webpage) if title == '' else title

        # clean weird char
        title = compat_str(title).encode('utf8', 'replace').replace(b'\xc3\x82', b'').decode('utf8', 'replace')

        if audio_fmts:
            self._clean_audio_fmts(audio_fmts)
            self._sort_formats(audio_fmts)
        if hls_fmts:
            self._sort_formats(hls_fmts)
        if http_fmts:
            self._sort_formats(http_fmts)

        formats.extend(audio_fmts)
        formats.extend(hls_fmts)
        formats.extend(http_fmts)

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_meta('twitter:description', webpage),
            'thumbnail': thumb,
            'formats': formats,
        }


class GediIE(GediBaseIE):
    _VALID_URL = r'''(?x)https?://video\.
                    (?:
                        (?:espresso\.)?repubblica
                        |lastampa
                        |huffingtonpost
                        |ilsecoloxix
                        |iltirreno
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
                    )
                    (?:\.gelocal)?\.it/(?!embed/).+?/(?P<id>[\d/]+)(?:\?|\&|$)'''
    _TESTS = [{
        'url': 'https://video.lastampa.it/politica/il-paradosso-delle-regionali-la-lega-vince-ma-sembra-aver-perso/121559/121683',
        'md5': '84658d7fb9e55a6e57ecc77b73137494',
        'info_dict': {
            'id': '121559/121683',
            'ext': 'mp4',
            'title': 'Il paradosso delle Regionali: ecco perché la Lega vince ma sembra aver perso',
            'description': 'md5:de7f4d6eaaaf36c153b599b10f8ce7ca',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-social-play\.jpg$',
        },
    }, {
        'url': 'https://video.repubblica.it/motori/record-della-pista-a-spa-francorchamps-la-pagani-huayra-roadster-bc-stupisce/367415/367963',
        'md5': 'e763b94b7920799a0e0e23ffefa2d157',
        'info_dict': {
            'id': '367415/367963',
            'ext': 'mp4',
            'title': 'Record della pista a Spa Francorchamps, la Pagani Huayra Roadster BC stupisce',
            'description': 'md5:5deb503cefe734a3eb3f07ed74303920',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-social-play\.jpg$',
        },
    }, {
        'url': 'https://video.ilsecoloxix.it/sport/cassani-e-i-brividi-azzurri-ai-mondiali-di-imola-qui-mi-sono-innamorato-del-ciclismo-da-ragazzino-incredibile-tornarci-da-ct/66184/66267',
        'md5': 'e48108e97b1af137d22a8469f2019057',
        'info_dict': {
            'id': '66184/66267',
            'ext': 'mp4',
            'title': 'Cassani e i brividi azzurri ai Mondiali di Imola: \\"Qui mi sono innamorato del ciclismo da ragazzino, incredibile tornarci da ct\\"',
            'description': 'md5:fc9c50894f70a2469bb9b54d3d0a3d3b',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-social-play\.jpg$',
        },
    }, {
        'url': 'https://video.iltirreno.gelocal.it/sport/dentro-la-notizia-ferrari-cosa-succede-a-maranello/141059/142723',
        'md5': 'a6e39f3bdc1842bbd92abbbbef230817',
        'info_dict': {
            'id': '141059/142723',
            'ext': 'mp4',
            'title': 'Dentro la notizia - Ferrari, cosa succede a Maranello',
            'description': 'md5:9907d65b53765681fa3a0b3122617c1f',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-social-play\.jpg$',
        },
    }]


class GediEmbedsIE(GediBaseIE):
    _VALID_URL = r'''(?x)https?://video\.
                    (?:
                        (?:espresso\.)?repubblica
                        |lastampa
                        |huffingtonpost
                        |ilsecoloxix
                        |iltirreno
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
                    )
                    (?:\.gelocal)?\.it/embed/.+?/(?P<id>[\d/]+)(?:\?|\&|$)'''
    _TESTS = [{
        'url': 'https://video.huffingtonpost.it/embed/politica/cotticelli-non-so-cosa-mi-sia-successo-sto-cercando-di-capire-se-ho-avuto-un-malore/29312/29276?responsive=true&el=video971040871621586700',
        'md5': 'f4ac23cadfea7fef89bea536583fa7ed',
        'info_dict': {
            'id': '29312/29276',
            'ext': 'mp4',
            'title': 'Cotticelli: \\"Non so cosa mi sia successo. Sto cercando di capire se ho avuto un malore\\"',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-social-play\.jpg$',
        },
    }, {
        'url': 'https://video.espresso.repubblica.it/embed/tutti-i-video/01-ted-villa/14772/14870&width=640&height=360',
        'md5': '0391c2c83c6506581003aaf0255889c0',
        'info_dict': {
            'id': '14772/14870',
            'ext': 'mp4',
            'title': 'Festival EMERGENCY, Villa: «La buona informazione aiuta la salute» (14772-14870)',
            'description': 'md5:2bce954d278248f3c950be355b7c2226',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-social-play\.jpg$',
        },
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
            mobj.group('url')
            for mobj in re.finditer(r'''(?x)
            (?:
                data-frame-src=|
                <iframe[^\n]+src=
            )
            (["'])
                (?P<url>https?://video\.
                    (?:
                        (?:espresso\.)?repubblica
                        |lastampa
                        |huffingtonpost
                        |ilsecoloxix
                        |iltirreno
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
                    )
                    (?:\.gelocal)?\.it/embed/.+?)
            \1''', webpage)]
        return GediEmbedsIE._sanitize_urls(entries)

    @staticmethod
    def _extract_url(webpage):
        urls = GediEmbedsIE._extract_urls(webpage)
        return urls[0] if urls else None

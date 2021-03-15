# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    ExtractorError,
    js_to_json,
    base_url,
    url_basename,
    urljoin,
)


class RCSBaseIE(InfoExtractor):
    # based on VideoPlayerLoader.prototype.getVideoSrc
    # and VideoPlayerLoader.prototype.transformSrc from
    # https://js2.corriereobjects.it/includes2013/LIBS/js/corriere_video.sjs
    _ALL_REPLACE = {
        'media2vam.corriere.it.edgesuite.net':
            'media2vam-corriere-it.akamaized.net',
        'media.youreporter.it.edgesuite.net':
            'media-youreporter-it.akamaized.net',
        'corrierepmd.corriere.it.edgesuite.net':
            'corrierepmd-corriere-it.akamaized.net',
        'media2vam-corriere-it.akamaized.net/fcs.quotidiani/vr/videos/':
            'video.corriere.it/vr360/videos/',
        '.net//': '.net/',
    }
    _MP4_REPLACE = {
        'media2vam.corbologna.corriere.it.edgesuite.net':
            'media2vam-bologna-corriere-it.akamaized.net',
        'media2vam.corfiorentino.corriere.it.edgesuite.net':
            'media2vam-fiorentino-corriere-it.akamaized.net',
        'media2vam.cormezzogiorno.corriere.it.edgesuite.net':
            'media2vam-mezzogiorno-corriere-it.akamaized.net',
        'media2vam.corveneto.corriere.it.edgesuite.net':
            'media2vam-veneto-corriere-it.akamaized.net',
        'media2.oggi.it.edgesuite.net':
            'media2-oggi-it.akamaized.net',
        'media2.quimamme.it.edgesuite.net':
            'media2-quimamme-it.akamaized.net',
        'media2.amica.it.edgesuite.net':
            'media2-amica-it.akamaized.net',
        'media2.living.corriere.it.edgesuite.net':
            'media2-living-corriere-it.akamaized.net',
        'media2.style.corriere.it.edgesuite.net':
            'media2-style-corriere-it.akamaized.net',
        'media2.iodonna.it.edgesuite.net':
            'media2-iodonna-it.akamaized.net',
        'media2.leitv.it.edgesuite.net':
            'media2-leitv-it.akamaized.net',
    }
    _MIGRATION_MAP = {
        'videoamica-vh.akamaihd': 'amica',
        'media2-amica-it.akamaized': 'amica',
        'corrierevam-vh.akamaihd': 'corriere',
        'media2vam-corriere-it.akamaized': 'corriere',
        'cormezzogiorno-vh.akamaihd': 'corrieredelmezzogiorno',
        'media2vam-mezzogiorno-corriere-it.akamaized': 'corrieredelmezzogiorno',
        'corveneto-vh.akamaihd': 'corrieredelveneto',
        'media2vam-veneto-corriere-it.akamaized': 'corrieredelveneto',
        'corbologna-vh.akamaihd': 'corrieredibologna',
        'media2vam-bologna-corriere-it.akamaized': 'corrieredibologna',
        'corfiorentino-vh.akamaihd': 'corrierefiorentino',
        'media2vam-fiorentino-corriere-it.akamaized': 'corrierefiorentino',
        'corinnovazione-vh.akamaihd': 'corriereinnovazione',
        'media2-gazzanet-gazzetta-it.akamaized': 'gazzanet',
        'videogazzanet-vh.akamaihd': 'gazzanet',
        'videogazzaworld-vh.akamaihd': 'gazzaworld',
        'gazzettavam-vh.akamaihd': 'gazzetta',
        'media2vam-gazzetta-it.akamaized': 'gazzetta',
        'videoiodonna-vh.akamaihd': 'iodonna',
        'media2-leitv-it.akamaized': 'leitv',
        'videoleitv-vh.akamaihd': 'leitv',
        'videoliving-vh.akamaihd': 'living',
        'media2-living-corriere-it.akamaized': 'living',
        'media2-oggi-it.akamaized': 'oggi',
        'videooggi-vh.akamaihd': 'oggi',
        'media2-quimamme-it.akamaized': 'quimamme',
        'quimamme-vh.akamaihd': 'quimamme',
        'videorunning-vh.akamaihd': 'running',
        'media2-style-corriere-it.akamaized': 'style',
        'style-vh.akamaihd': 'style',
        'videostyle-vh.akamaihd': 'style',
        'media2-stylepiccoli-it.akamaized': 'stylepiccoli',
        'stylepiccoli-vh.akamaihd': 'stylepiccoli',
        'doveviaggi-vh.akamaihd': 'viaggi',
        'media2-doveviaggi-it.akamaized': 'viaggi',
        'media2-vivimilano-corriere-it.akamaized': 'vivimilano',
        'vivimilano-vh.akamaihd': 'vivimilano',
        'media2-youreporter-it.akamaized': 'youreporter'
    }
    _MIGRATION_MEDIA = {
        'advrcs-vh.akamaihd': '',
        'corriere-f.akamaihd': '',
        'corrierepmd-corriere-it.akamaized': '',
        'corrprotetto-vh.akamaihd': '',
        'gazzetta-f.akamaihd': '',
        'gazzettapmd-gazzetta-it.akamaized': '',
        'gazzprotetto-vh.akamaihd': '',
        'periodici-f.akamaihd': '',
        'periodicisecure-vh.akamaihd': '',
        'videocoracademy-vh.akamaihd': ''
    }

    def _get_video_src(self, video):
        mediaFiles = video.get('mediaProfile').get('mediaFile')
        src = {}
        # audio
        if video.get('mediaType') == 'AUDIO':
            for aud in mediaFiles:
                # todo: check
                src['mp3'] = aud.get('value')
        # video
        else:
            for vid in mediaFiles:
                if vid.get('mimeType') == 'application/vnd.apple.mpegurl':
                    src['m3u8'] = vid.get('value')
                if vid.get('mimeType') == 'video/mp4':
                    src['mp4'] = vid.get('value')

        # replace host
        for t in src:
            for s, r in self._ALL_REPLACE.items():
                src[t] = src[t].replace(s, r)
            for s, r in self._MP4_REPLACE.items():
                src[t] = src[t].replace(s, r)

        # switch cdn
        if 'mp4' in src and 'm3u8' in src:
            if ('-lh.akamaihd' not in src.get('m3u8')
                    and 'akamai' in src.get('mp4')):
                if 'm3u8' in src:
                    matches = re.search(r'(?:https*:)?\/\/(?P<host>.*)\.net\/i(?P<path>.*)$', src.get('m3u8'))
                    src['m3u8'] = 'https://vod.rcsobjects.it/hls/%s%s' % (
                        self._MIGRATION_MAP[matches.group('host')],
                        matches.group('path').replace(
                            '///', '/').replace(
                            '//', '/').replace(
                            '.csmil', '.urlset'
                        )
                    )
                if 'mp4' in src:
                    matches = re.search(r'(?:https*:)?\/\/(?P<host>.*)\.net\/i(?P<path>.*)$', src.get('mp4'))
                    if matches:
                        if matches.group('host') in self._MIGRATION_MEDIA:
                            vh_stream = 'https://media2.corriereobjects.it'
                            if src.get('mp4').find('fcs.quotidiani_!'):
                                vh_stream = 'https://media2-it.corriereobjects.it'
                            src['mp4'] = '%s%s' % (
                                vh_stream,
                                matches.group('path').replace(
                                    '///', '/').replace(
                                    '//', '/').replace(
                                    '/fcs.quotidiani/mediacenter', '').replace(
                                    '/fcs.quotidiani_!/mediacenter', '').replace(
                                    'corriere/content/mediacenter/', '').replace(
                                    'gazzetta/content/mediacenter/', '')
                            )
                        else:
                            src['mp4'] = 'https://vod.rcsobjects.it/%s%s' % (
                                self._MIGRATION_MAP[matches.group('host')],
                                matches.group('path').replace('///', '/').replace('//', '/')
                            )

        if 'mp3' in src:
            src['mp3'] = src.get('mp3').replace(
                'media2vam-corriere-it.akamaized.net',
                'vod.rcsobjects.it/corriere')
        if 'mp4' in src:
            if src.get('mp4').find('fcs.quotidiani_!'):
                src['mp4'] = src.get('mp4').replace('vod.rcsobjects', 'vod-it.rcsobjects')
        if 'm3u8' in src:
            if src.get('m3u8').find('fcs.quotidiani_!'):
                src['m3u8'] = src.get('m3u8').replace('vod.rcsobjects', 'vod-it.rcsobjects')

        if 'geoblocking' in video.get('mediaProfile'):
            if 'm3u8' in src:
                src['m3u8'] = src.get('m3u8').replace('vod.rcsobjects', 'vod-it.rcsobjects')
            if 'mp4' in src:
                src['mp4'] = src.get('mp4').replace('vod.rcsobjects', 'vod-it.rcsobjects')
        if 'm3u8' in src:
            if src.get('m3u8').find('csmil') and src.get('m3u8').find('vod'):
                src['m3u8'] = src.get('m3u8').replace('.csmil', '.urlset')

        return src

    def _create_formats(self, urls, video_id):
        formats = []
        formats = self._extract_m3u8_formats(
            urls.get('m3u8'), video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls', fatal=False)

        if urls.get('mp4'):
            formats.append({
                'format_id': 'http-mp4',
                'url': urls['mp4']
            })
        self._sort_formats(formats)
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        mobj = re.search(self._VALID_URL, url)

        if 'cdn' not in mobj.groupdict():
            raise ExtractorError('CDN not found in url: %s' % url)

        # for leitv/youreporter/viaggi don't use the embed page
        if ((mobj.group('cdn') not in ['leitv.it', 'youreporter.it'])
                and (mobj.group('vid') == 'video')):
            url = 'https://video.%s/video-embed/%s' % (mobj.group('cdn'), video_id)

        page = self._download_webpage(url, video_id)

        video_data = None
        # look for json video data url
        json = self._search_regex(
            r'''(?x)url\s*=\s*(["'])
            (?P<url>
                (?:https?:)?//video\.rcs\.it
                /fragment-includes/video-includes/.+?\.json
            )\1;''',
            page, video_id, group='url', default=None)
        if json:
            if json.startswith('//'):
                json = 'https:%s' % json
            video_data = self._download_json(json, video_id)

        # if json url not found, look for json video data directly in the page
        else:
            # RCS normal pages and most of the embeds
            json = self._search_regex(
                r'[\s;]video\s*=\s*({[\s\S]+?})(?:;|,playlist=)',
                page, video_id, default=None)
            if not json and 'video-embed' in url:
                page = self._download_webpage(url.replace('video-embed', 'video-json'), video_id)
                json = self._search_regex(
                    r'##start-video##({[\s\S]+?})##end-video##',
                    page, video_id, default=None)
            if not json:
                # if no video data found try search for iframes
                emb = RCSEmbedsIE._extract_url(page)
                if emb:
                    return {
                        '_type': 'url_transparent',
                        'url': emb,
                        'ie_key': RCSEmbedsIE.ie_key()
                    }
            if json:
                video_data = self._parse_json(
                    json, video_id, transform_source=js_to_json)

        if not video_data:
            raise ExtractorError('Video data not found in the page')

        formats = self._create_formats(
            self._get_video_src(video_data), video_id)

        description = (video_data.get('description')
                       or clean_html(video_data.get('htmlDescription'))
                       or self._html_search_meta('description', page))
        uploader = video_data.get('provider') or mobj.group('cdn')

        return {
            'id': video_id,
            'title': video_data.get('title'),
            'description': description,
            'uploader': uploader,
            'formats': formats
        }


class RCSEmbedsIE(RCSBaseIE):
    _VALID_URL = r'''(?x)
                    https?://(?P<vid>video)\.
                    (?P<cdn>
                    (?:
                        rcs|
                        (?:corriere\w+\.)?corriere|
                        (?:gazzanet\.)?gazzetta
                    )\.it)
                    /video-embed/(?P<id>[^/=&\?]+?)(?:$|\?)'''
    _TESTS = [{
        'url': 'https://video.rcs.it/video-embed/iodonna-0001585037',
        'md5': '623ecc8ffe7299b2d0c1046d8331a9df',
        'info_dict': {
            'id': 'iodonna-0001585037',
            'ext': 'mp4',
            'title': 'Sky Arte racconta Madonna nella serie "Artist to icon"',
            'description': 'md5:65b09633df9ffee57f48b39e34c9e067',
            'uploader': 'rcs.it',
        }
    }, {
        # redownload the page changing 'video-embed' in 'video-json'
        'url': 'https://video.gazzanet.gazzetta.it/video-embed/gazzanet-mo05-0000260789',
        'md5': 'a043e3fecbe4d9ed7fc5d888652a5440',
        'info_dict': {
            'id': 'gazzanet-mo05-0000260789',
            'ext': 'mp4',
            'title': 'Valentino Rossi e papà Graziano si divertono col drifting',
            'description': 'md5:a8bf90d6adafd9815f70fc74c0fc370a',
            'uploader': 'rcd',
        }
    }, {
        'url': 'https://video.corriere.it/video-embed/b727632a-f9d0-11ea-91b0-38d50a849abb?player',
        'match_only': True
    }, {
        'url': 'https://video.gazzetta.it/video-embed/49612410-00ca-11eb-bcd8-30d4253e0140',
        'match_only': True
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
                (?P<url>(?:https?:)?//video\.
                    (?:
                        rcs|
                        (?:corriere\w+\.)?corriere|
                        (?:gazzanet\.)?gazzetta
                    )
                \.it/video-embed/.+?)
            \1''', webpage)]
        return RCSEmbedsIE._sanitize_urls(entries)

    @staticmethod
    def _extract_url(webpage):
        urls = RCSEmbedsIE._extract_urls(webpage)
        return urls[0] if urls else None


class RCSIE(RCSBaseIE):
    _VALID_URL = r'''(?x)https?://(?P<vid>video|viaggi)\.
                    (?P<cdn>
                    (?:
                        corrieredelmezzogiorno\.
                        |corrieredelveneto\.
                        |corrieredibologna\.
                        |corrierefiorentino\.
                    )?corriere\.it
                    |(?:gazzanet\.)?gazzetta\.it)
                    /(?!video-embed/).+?/(?P<id>[^/\?]+)(?=\?|/$|$)'''
    _TESTS = [{
        'url': 'https://video.corriere.it/sport/formula-1/vettel-guida-ferrari-sf90-mugello-suo-fianco-c-elecrerc-bendato-video-esilarante/b727632a-f9d0-11ea-91b0-38d50a849abb',
        'md5': '0f4ededc202b0f00b6e509d831e2dcda',
        'info_dict': {
            'id': 'b727632a-f9d0-11ea-91b0-38d50a849abb',
            'ext': 'mp4',
            'title': 'Vettel guida la Ferrari SF90 al Mugello e al suo fianco c\'è Leclerc (bendato): il video è esilarante',
            'description': 'md5:93b51c9161ac8a64fb2f997b054d0152',
            'uploader': 'Corriere Tv',
        }
    }, {
        # video data inside iframe
        'url': 'https://viaggi.corriere.it/video/norvegia-il-nuovo-ponte-spettacolare-sopra-la-cascata-di-voringsfossen/',
        'md5': 'da378e4918d2afbf7d61c35abb948d4c',
        'info_dict': {
            'id': '5b7cd134-e2c1-11ea-89b3-b56dd0df2aa2',
            'ext': 'mp4',
            'title': 'La nuova spettacolare attrazione in Norvegia: il ponte sopra Vøringsfossen',
            'description': 'md5:18b35a291f6746c0c8dacd16e5f5f4f8',
            'uploader': 'DOVE Viaggi',
        }
    }, {
        'url': 'https://video.gazzetta.it/video-motogp-catalogna-cadute-dovizioso-vale-rossi/49612410-00ca-11eb-bcd8-30d4253e0140?vclk=Videobar',
        'md5': 'eedc1b5defd18e67383afef51ff7bdf9',
        'info_dict': {
            'id': '49612410-00ca-11eb-bcd8-30d4253e0140',
            'ext': 'mp4',
            'title': 'Dovizioso, il contatto con Zarco e la caduta. E anche Vale finisce a terra',
            'description': 'md5:8c6e905dc3b9413218beca11ebd69778',
            'uploader': 'AMorici',
        }
    }, {
        'url': 'https://video.corriere.it/video-360/metro-copenaghen-tutta-italiana/a248a7f0-e2db-11e9-9830-af2de6b1f945',
        'match_only': True
    }]


class RCSVariousIE(RCSBaseIE):
    _VALID_URL = r'''(?x)https?://www\.
                    (?P<cdn>
                        leitv\.it|
                        youreporter\.it
                    )/(?:[^/]+/)?(?P<id>[^/]+?)(?:$|\?|/)'''
    _TESTS = [{
        'url': 'https://www.leitv.it/benessere/mal-di-testa-come-combatterlo-ed-evitarne-la-comparsa/',
        'md5': '92b4e63667b8f95acb0a04da25ae28a1',
        'info_dict': {
            'id': 'mal-di-testa-come-combatterlo-ed-evitarne-la-comparsa',
            'ext': 'mp4',
            'title': 'Cervicalgia e mal di testa, il video con i suggerimenti dell\'esperto',
            'description': 'md5:ae21418f34cee0b8d02a487f55bcabb5',
            'uploader': 'leitv.it',
        }
    }, {
        'url': 'https://www.youreporter.it/fiume-sesia-3-ottobre-2020/',
        'md5': '8dccd436b47a830bab5b4a88232f391a',
        'info_dict': {
            'id': 'fiume-sesia-3-ottobre-2020',
            'ext': 'mp4',
            'title': 'Fiume Sesia 3 ottobre 2020',
            'description': 'md5:0070eef1cc884d13c970a4125063de55',
            'uploader': 'youreporter.it',
        }
    }]

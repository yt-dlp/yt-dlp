import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    base_url,
    clean_html,
    HEADRequest,
    int_or_none,
    js_to_json,
    sanitize_url,
    traverse_obj,
    url_basename,
    urljoin,
)


class RCSBaseIE(InfoExtractor):
    # based on VideoPlayerLoader.prototype.getVideoSrc
    # and VideoPlayerLoader.prototype.transformSrc from
    # https://js2.corriereobjects.it/includes2013/LIBS/js/corriere_video.sjs
    _UUID_RE = r'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}'
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
        'http://': 'https://',
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
    _MIME_TYPE = {
        'application/vnd.apple.mpegurl': 'm3u8',
        'audio/mpeg': 'mp3',
        'video/mp4': 'mp4',  # unreliable: use _create_http_formats instead
        'application/f4m': 'dash',  # TODO
    }

    def _get_video_src(self, video):
        mediaFiles = traverse_obj(video, ('mediaProfile', 'mediaFile'))
        sources = []

        for source in mediaFiles:
            if self._MIME_TYPE.get(source.get('mimeType')):
                sources.append({
                    'type': self._MIME_TYPE[source['mimeType']],
                    'url': source.get('value'),
                    'bitrate': source.get('bitrate')})

        for source in sources:
            for s, r in self._ALL_REPLACE.items():
                source['url'] = source['url'].replace(s, r)

            if source['type'] == 'm3u8' and '-lh.akamaihd' in source['url']:
                matches = re.search(r'(?:https*:)?\/\/(?P<host>.*)\.net\/i(?P<path>.*)$', source['url'])
                source['url'] = 'https://vod.rcsobjects.it/hls/%s%s' % (
                    self._MIGRATION_MAP[matches.group('host')],
                    matches.group('path').replace('///', '/').replace('//', '/').replace('.csmil', '.urlset')
                )
            if (source['type'] == 'm3u8' and 'fcs.quotidiani_!' in source['url']) or (
                    'geoblocking' in video['mediaProfile']):
                source['url'] = source['url'].replace(
                    'vod.rcsobjects', 'vod-it.rcsobjects')
            if source['type'] == 'm3u8' and 'vod' in source['url']:
                source['url'] = source['url'].replace(
                    '.csmil', '.urlset')
            if source['type'] == 'mp3':
                source['url'] = source['url'].replace(
                    'media2vam-corriere-it.akamaized.net',
                    'vod.rcsobjects.it/corriere')

        return sources

    def _create_http_formats(self, m3u8_url, m3u8_formats, video_id):
        http_formats = []
        REPL_REGEX = r'(https?://[^/]+)/hls/(\S+?\.mp4).+'
        for f in m3u8_formats:
            if f['vcodec'] != 'none' and re.match(REPL_REGEX, f['url']):
                http_f = f.copy()
                del http_f['manifest_url']
                http_url = re.sub(REPL_REGEX, r'\g<1>/\g<2>', f['url'])
                format_id = http_f['format_id'].replace('hls-', 'https-')
                urlh = self._request_webpage(
                    HEADRequest(http_url), video_id,
                    note=f'Check filesize for {format_id}', fatal=False)
                if urlh:
                    http_f.update({
                        'format_id': format_id,
                        'url': http_url,
                        'protocol': 'https',
                        'filesize_approx': int_or_none(urlh.headers.get('Content-Length', None)),
                    })
                    http_formats.append(http_f)

        return http_formats

    def _create_formats(self, sources, video_id):
        formats = []

        for source in sources:
            if source['type'] == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    source['url'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(m3u8_formats)
                http_formats = self._create_http_formats(source['url'], m3u8_formats or [], video_id)
                formats.extend(http_formats)
            if source['type'] == 'mp3':
                formats.append({
                    'format_id': 'https-mp3',
                    'ext': 'mp3',
                    'acodec': 'mp3',
                    'vcodec': 'none',
                    'abr': source.get('bitrate'),
                    'url': source['url'],
                })

        return formats

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        if 'cdn' not in mobj.groupdict():
            raise ExtractorError('CDN not found in url: %s' % url)

        # for leitv/youreporter don't use the embed page
        if mobj.group('cdn') not in ['leitv.it', 'youreporter.it']:
            if 'video-embed' not in url and not re.match(self._UUID_RE, video_id):
                page = self._download_webpage(url, video_id)
                video_id = self._search_regex(fr'"uuid"\s*:\s*"({self._UUID_RE})"', page, video_id, fatal=False) or video_id
            url = 'https://video.%s/video-embed/%s' % (mobj.group('cdn'), video_id)

        page = self._download_webpage(url, video_id)
        video_data = None
        # look for json video data url
        json = self._search_regex(
            r'''(?x)url\s*=\s*(["'])
            (?P<url>
                (?:https?:)?//video\.rcs\.it
                /fragment-includes/video-includes/\S+?\.json
            )\1;''',
            page, video_id, group='url', default=None)

        if json:
            video_data = self._download_json(sanitize_url(json, scheme='https'), video_id)
            video_id = video_data.get('id') or video_id

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

        description = (clean_html(video_data.get('description'))
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
    _EMBED_REGEX = [r'''(?x)
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
            \1''']
    _TESTS = [{
        'url': 'https://video.rcs.it/video-embed/iodonna-0001585037',
        'md5': '0faca97df525032bb9847f690bc3720c',
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
        'md5': '03c81ad0c965b717596aee17028bcd78',
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
        # add protocol if missing and clean iframes urls
        for url in urls:
            url = sanitize_url(url, scheme='https')
            url = urljoin(base_url(url), url_basename(url))
        return urls

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        return cls._sanitize_urls(list(super()._extract_embed_urls(url, webpage)))


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
                    /(?!video-embed/)\S+?/(?P<id>[^/\?]+)(?=\?|/$|$)'''
    _TESTS = [{
        'url': 'https://video.corriere.it/sport/formula-1/vettel-guida-ferrari-sf90-mugello-suo-fianco-c-elecrerc-bendato-video-esilarante/b727632a-f9d0-11ea-91b0-38d50a849abb',
        'md5': '14946840dec46ecfddf66ba4eea7d2b2',
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
        'md5': 'f22a92d9e666e80f2fffbf2825359c81',
        'info_dict': {
            'id': '5b7cd134-e2c1-11ea-89b3-b56dd0df2aa2',
            'ext': 'mp4',
            'title': 'La nuova spettacolare attrazione in Norvegia: il ponte sopra Vøringsfossen',
            'description': 'md5:18b35a291f6746c0c8dacd16e5f5f4f8',
            'uploader': 'DOVE Viaggi',
        }
    }, {
        'url': 'https://video.gazzetta.it/video-motogp-catalogna-cadute-dovizioso-vale-rossi/49612410-00ca-11eb-bcd8-30d4253e0140?vclk=Videobar',
        'md5': 'c8cb6f99bf0d803d5c630ec5f9a401eb',
        'info_dict': {
            'id': '49612410-00ca-11eb-bcd8-30d4253e0140',
            'ext': 'mp4',
            'title': 'Dovizioso, il contatto con Zarco e la caduta. E anche Vale finisce a terra',
            'description': 'md5:8c6e905dc3b9413218beca11ebd69778',
            'uploader': 'AMorici',
        }
    }, {
        # only audio format https://github.com/yt-dlp/yt-dlp/issues/5683
        'url': 'https://video.corriere.it/cronaca/audio-telefonata-il-papa-becciu-santita-lettera-che-mi-ha-inviato-condanna/b94c0d20-70c2-11ed-9572-e4b947a0ebd2',
        'md5': 'aaffb08d02f2ce4292a4654694c78150',
        'info_dict': {
            'id': 'b94c0d20-70c2-11ed-9572-e4b947a0ebd2',
            'ext': 'mp3',
            'title': 'L\'audio della telefonata tra il Papa e Becciu: «Santità, la lettera che mi ha inviato è una condanna»',
            'description': 'md5:c0ddb61bd94a8d4e0d4bb9cda50a689b',
            'uploader': 'Corriere Tv',
            'formats': [{'format_id': 'https-mp3', 'ext': 'mp3'}],
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
        'url': 'https://www.leitv.it/benessere/mal-di-testa/',
        'md5': '3b7a683d105a7313ec7513b014443631',
        'info_dict': {
            'id': 'leitv-0000125151',
            'ext': 'mp4',
            'title': 'Cervicalgia e mal di testa, il video con i suggerimenti dell\'esperto',
            'description': 'md5:ae21418f34cee0b8d02a487f55bcabb5',
            'uploader': 'leitv.it',
        }
    }, {
        'url': 'https://www.youreporter.it/fiume-sesia-3-ottobre-2020/',
        'md5': '3989b6d603482611a2abd2f32b79f739',
        'info_dict': {
            'id': 'youreporter-0000332574',
            'ext': 'mp4',
            'title': 'Fiume Sesia 3 ottobre 2020',
            'description': 'md5:0070eef1cc884d13c970a4125063de55',
            'uploader': 'youreporter.it',
        }
    }]

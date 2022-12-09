import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    base_url,
    clean_html,
    extract_attributes,
    get_element_html_by_class,
    get_element_html_by_id,
    HEADRequest,
    int_or_none,
    js_to_json,
    mimetype2ext,
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
    _RCS_ID_RE = r'[\w-]+-\d{10}'
    _ALL_REPLACE = {
        'media2vam.corriere.it.edgesuite.net':
            'media2vam-corriere-it.akamaized.net',
        'media.youreporter.it.edgesuite.net':
            'media-youreporter-it.akamaized.net',
        'corrierepmd.corriere.it.edgesuite.net':
            'corrierepmd-corriere-it.akamaized.net',
        'media2vam-corriere-it.akamaized.net/fcs.quotidiani/vr/videos/':
            'video.corriere.it/vr360/videos/',
        'http://': 'https://',
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

    def _get_video_src(self, video):
        mediaFiles = traverse_obj(video, ('mediaProfile', 'mediaFile'))
        sources = []

        for source in mediaFiles:
            if source.get('mimeType'):
                sources.append({
                    'type': mimetype2ext(source['mimeType']),
                    'url': source.get('value'),
                    'bitrate': source.get('bitrate')})

        for source in sources:
            for s, r in self._ALL_REPLACE.items():
                source['url'] = source['url'].replace(s, r)

            if source['type'] == 'm3u8' and '-vh.akamaihd' in source['url']:
                # still needed for some old content: see _TESTS #3
                matches = re.search(r'(?:https*:)?//(?P<host>.*)\.net/i(?P<path>.*)$', source['url'])
                if matches:
                    source['url'] = f'https://vod.rcsobjects.it/hls/{self._MIGRATION_MAP[matches.group("host")]}{matches.group("path")}'
            if (source['type'] == 'm3u8' and 'fcs.quotidiani_!' in source['url']) or (
                    video['mediaProfile'].get('geoblocking')):
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
        REPL_REGEX = r'(https?://[^/]+)/hls/([^?#]+?\.mp4).+'
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
                formats.extend(self._create_http_formats(
                    source['url'], m3u8_formats or [], video_id))
            elif source['type'] == 'mp3':
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
        cdn, video_id = self._match_valid_url(url).group('cdn', 'id')
        video_data = None

        if re.match(self._UUID_RE, video_id) or re.match(self._RCS_ID_RE, video_id):
            url = f'https://video.{cdn}/video-json/{video_id}'
        else:
            webpage = self._download_webpage(url, video_id)
            data_config = get_element_html_by_id('divVideoPlayer', webpage) or get_element_html_by_class('divVideoPlayer', webpage)

            if data_config:
                data_config = self._parse_json(
                    extract_attributes(data_config).get('data-config'),
                    video_id, fatal=False) or {}
                cdn = f'{data_config["newspaper"]}.it' if data_config.get('newspaper') else cdn
                video_id = data_config.get('uuid') or video_id
                url = f'https://video.{cdn}/video-json/{video_id}'
            else:
                json_url = self._search_regex(
                    r'''(?x)url\s*=\s*(["'])
                    (?P<url>
                        (?:https?:)?//video\.rcs\.it
                        /fragment-includes/video-includes/[^"']+?\.json
                    )\1;''',
                    webpage, video_id, group='url', default=None)
                if json_url:
                    video_data = self._download_json(sanitize_url(json_url, scheme='https'), video_id)
                    video_id = video_data.get('id') or video_id

        if not video_data:
            webpage = self._download_webpage(url, video_id)
            json_data = self._search_regex(
                r'##start-video##({[\s\S]+?})##end-video##',
                webpage, video_id, default=None, fatal=False)
            if json_data:
                video_data = self._parse_json(
                    json_data, video_id, transform_source=js_to_json)
            else:
                # try search for iframes
                emb = RCSEmbedsIE._extract_url(webpage)
                if emb:
                    return {
                        '_type': 'url_transparent',
                        'url': emb,
                        'ie_key': RCSEmbedsIE.ie_key()
                    }

        if not video_data:
            raise ExtractorError('Video data not found in the page')

        return {
            'id': video_id,
            'title': video_data.get('title'),
            'description': (clean_html(video_data.get('description'))
                            or clean_html(video_data.get('htmlDescription'))
                            or self._html_search_meta('description', webpage)),
            'uploader': video_data.get('provider') or cdn,
            'formats': self._create_formats(self._get_video_src(video_data), video_id),
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
        'url': 'https://video.gazzanet.gazzetta.it/video-embed/gazzanet-mo05-0000260789',
        'match_only': True
    }, {
        'url': 'https://video.gazzetta.it/video-embed/49612410-00ca-11eb-bcd8-30d4253e0140',
        'match_only': True
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.iodonna.it/video-iodonna/personaggi-video/monica-bellucci-piu-del-lavoro-oggi-per-me-sono-importanti-lamicizia-e-la-famiglia/',
        'info_dict': {
            'id': 'iodonna-0002033648',
            'ext': 'mp4',
            'title': 'Monica Bellucci: «Più del lavoro, oggi per me sono importanti l\'amicizia e la famiglia»',
            'description': 'md5:daea6d9837351e56b1ab615c06bebac1',
            'uploader': 'rcs.it',
        }
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
                    /(?!video-embed/)[^?#]+?/(?P<id>[^/\?]+)(?=\?|/$|$)'''
    _TESTS = [{
        # json iframe from directly from id
        'url': 'https://video.corriere.it/sport/formula-1/vettel-guida-ferrari-sf90-mugello-suo-fianco-c-elecrerc-bendato-video-esilarante/b727632a-f9d0-11ea-91b0-38d50a849abb',
        'md5': '14946840dec46ecfddf66ba4eea7d2b2',
        'info_dict': {
            'id': 'b727632a-f9d0-11ea-91b0-38d50a849abb',
            'ext': 'mp4',
            'title': 'Vettel guida la Ferrari SF90 al Mugello e al suo fianco c\'è Leclerc (bendato): il video è esilarante',
            'description': 'md5:3915ce5ebb3d2571deb69a5eb85ac9b5',
            'uploader': 'Corriere Tv',
        }
    }, {
        # search for video id inside the page
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
        # old content still needs cdn migration
        'url': 'https://viaggi.corriere.it/video/milano-varallo-sesia-sul-treno-a-vapore/',
        'md5': '2dfdce7af249654ad27eeba03fe1e08d',
        'info_dict': {
            'id': 'd8f6c8d0-f7d7-11e8-bfca-f74cf4634191',
            'ext': 'mp4',
            'title': 'Milano-Varallo Sesia sul treno a vapore',
            'description': 'md5:6348f47aac230397fe341a74f7678d53',
            'uploader': 'DOVE Viaggi',
        }
    }, {
        'url': 'https://video.corriere.it/video-360/metro-copenaghen-tutta-italiana/a248a7f0-e2db-11e9-9830-af2de6b1f945',
        'match_only': True
    }]


class RCSVariousIE(RCSBaseIE):
    _VALID_URL = r'''(?x)https?://www\.
                    (?P<cdn>
                        leitv\.it|
                        youreporter\.it|
                        amica\.it
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
    }, {
        'url': 'https://www.amica.it/video-post/saint-omer-al-cinema-il-film-leone-dargento-che-ribalta-gli-stereotipi/',
        'md5': '187cce524dfd0343c95646c047375fc4',
        'info_dict': {
            'id': 'amica-0001225365',
            'ext': 'mp4',
            'title': '"Saint Omer": al cinema il film Leone d\'argento che ribalta gli stereotipi',
            'description': 'md5:b1c8869c2dcfd6073a2a311ba0008aa8',
            'uploader': 'rcs.it',
        }
    }]

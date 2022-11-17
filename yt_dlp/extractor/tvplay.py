import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_urlparse,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_iso8601,
    qualities,
    traverse_obj,
    try_get,
    update_url_query,
    url_or_none,
    urljoin,
)


class TVPlayIE(InfoExtractor):
    IE_NAME = 'mtg'
    IE_DESC = 'MTG services'
    _VALID_URL = r'''(?x)
                    (?:
                        mtg:|
                        https?://
                            (?:www\.)?
                            (?:
                                tvplay(?:\.skaties)?\.lv(?:/parraides)?|
                                (?:tv3play|play\.tv3)\.lt(?:/programos)?|
                                tv3play(?:\.tv3)?\.ee/sisu|
                                (?:tv(?:3|6|8|10)play)\.se/program|
                                (?:(?:tv3play|viasat4play|tv6play)\.no|(?:tv3play)\.dk)/programmer|
                                play\.nova(?:tv)?\.bg/programi
                            )
                            /(?:[^/]+/)+
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [
        {
            'url': 'http://www.tvplay.lv/parraides/vinas-melo-labak/418113?autostart=true',
            'md5': 'a1612fe0849455423ad8718fe049be21',
            'info_dict': {
                'id': '418113',
                'ext': 'mp4',
                'title': 'Kādi ir īri? - Viņas melo labāk',
                'description': 'Baiba apsmej īrus, kādi tie ir un ko viņi dara.',
                'series': 'Viņas melo labāk',
                'season': '2.sezona',
                'season_number': 2,
                'duration': 25,
                'timestamp': 1406097056,
                'upload_date': '20140723',
            },
        },
        {
            'url': 'http://play.tv3.lt/programos/moterys-meluoja-geriau/409229?autostart=true',
            'info_dict': {
                'id': '409229',
                'ext': 'flv',
                'title': 'Moterys meluoja geriau',
                'description': 'md5:9aec0fc68e2cbc992d2a140bd41fa89e',
                'series': 'Moterys meluoja geriau',
                'episode_number': 47,
                'season': '1 sezonas',
                'season_number': 1,
                'duration': 1330,
                'timestamp': 1403769181,
                'upload_date': '20140626',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv3play.ee/sisu/kodu-keset-linna/238551?autostart=true',
            'info_dict': {
                'id': '238551',
                'ext': 'flv',
                'title': 'Kodu keset linna 398537',
                'description': 'md5:7df175e3c94db9e47c0d81ffa5d68701',
                'duration': 1257,
                'timestamp': 1292449761,
                'upload_date': '20101215',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv3play.se/program/husraddarna/395385?autostart=true',
            'info_dict': {
                'id': '395385',
                'ext': 'mp4',
                'title': 'Husräddarna S02E07',
                'description': 'md5:f210c6c89f42d4fc39faa551be813777',
                'duration': 2574,
                'timestamp': 1400596321,
                'upload_date': '20140520',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv6play.se/program/den-sista-dokusapan/266636?autostart=true',
            'info_dict': {
                'id': '266636',
                'ext': 'mp4',
                'title': 'Den sista dokusåpan S01E08',
                'description': 'md5:295be39c872520221b933830f660b110',
                'duration': 1492,
                'timestamp': 1330522854,
                'upload_date': '20120229',
                'age_limit': 18,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv8play.se/program/antikjakten/282756?autostart=true',
            'info_dict': {
                'id': '282756',
                'ext': 'mp4',
                'title': 'Antikjakten S01E10',
                'description': 'md5:1b201169beabd97e20c5ad0ad67b13b8',
                'duration': 2646,
                'timestamp': 1348575868,
                'upload_date': '20120925',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv3play.no/programmer/anna-anka-soker-assistent/230898?autostart=true',
            'info_dict': {
                'id': '230898',
                'ext': 'mp4',
                'title': 'Anna Anka søker assistent - Ep. 8',
                'description': 'md5:f80916bf5bbe1c5f760d127f8dd71474',
                'duration': 2656,
                'timestamp': 1277720005,
                'upload_date': '20100628',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.viasat4play.no/programmer/budbringerne/21873?autostart=true',
            'info_dict': {
                'id': '21873',
                'ext': 'mp4',
                'title': 'Budbringerne program 10',
                'description': 'md5:4db78dc4ec8a85bb04fd322a3ee5092d',
                'duration': 1297,
                'timestamp': 1254205102,
                'upload_date': '20090929',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv6play.no/programmer/hotelinspektor-alex-polizzi/361883?autostart=true',
            'info_dict': {
                'id': '361883',
                'ext': 'mp4',
                'title': 'Hotelinspektør Alex Polizzi - Ep. 10',
                'description': 'md5:3ecf808db9ec96c862c8ecb3a7fdaf81',
                'duration': 2594,
                'timestamp': 1393236292,
                'upload_date': '20140224',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://play.novatv.bg/programi/zdravei-bulgariya/624952?autostart=true',
            'info_dict': {
                'id': '624952',
                'ext': 'flv',
                'title': 'Здравей, България (12.06.2015 г.) ',
                'description': 'md5:99f3700451ac5bb71a260268b8daefd7',
                'duration': 8838,
                'timestamp': 1434100372,
                'upload_date': '20150612',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'https://play.nova.bg/programi/zdravei-bulgariya/764300?autostart=true',
            'only_matching': True,
        },
        {
            'url': 'http://tvplay.skaties.lv/parraides/vinas-melo-labak/418113?autostart=true',
            'only_matching': True,
        },
        {
            'url': 'https://tvplay.skaties.lv/vinas-melo-labak/418113/?autostart=true',
            'only_matching': True,
        },
        {
            # views is null
            'url': 'http://tvplay.skaties.lv/parraides/tv3-zinas/760183',
            'only_matching': True,
        },
        {
            'url': 'http://tv3play.tv3.ee/sisu/kodu-keset-linna/238551?autostart=true',
            'only_matching': True,
        },
        {
            'url': 'mtg:418113',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        geo_country = self._search_regex(
            r'https?://[^/]+\.([a-z]{2})', url,
            'geo country', default=None)
        if geo_country:
            self._initialize_geo_bypass({'countries': [geo_country.upper()]})
        video = self._download_json(
            'http://playapi.mtgx.tv/v3/videos/%s' % video_id, video_id, 'Downloading video JSON')

        title = video['title']

        try:
            streams = self._download_json(
                'http://playapi.mtgx.tv/v3/videos/stream/%s' % video_id,
                video_id, 'Downloading streams JSON')
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                msg = self._parse_json(e.cause.read().decode('utf-8'), video_id)
                raise ExtractorError(msg['msg'], expected=True)
            raise

        quality = qualities(['hls', 'medium', 'high'])
        formats = []
        for format_id, video_url in streams.get('streams', {}).items():
            video_url = url_or_none(video_url)
            if not video_url:
                continue
            ext = determine_ext(video_url)
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    update_url_query(video_url, {
                        'hdcore': '3.5.0',
                        'plugin': 'aasp-3.5.0.151.81'
                    }), video_id, f4m_id='hds', fatal=False))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    video_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                fmt = {
                    'format_id': format_id,
                    'quality': quality(format_id),
                    'ext': ext,
                }
                if video_url.startswith('rtmp'):
                    m = re.search(
                        r'^(?P<url>rtmp://[^/]+/(?P<app>[^/]+))/(?P<playpath>.+)$', video_url)
                    if not m:
                        continue
                    fmt.update({
                        'ext': 'flv',
                        'url': m.group('url'),
                        'app': m.group('app'),
                        'play_path': m.group('playpath'),
                        'preference': -1,
                    })
                else:
                    fmt.update({
                        'url': video_url,
                    })
                formats.append(fmt)

        if not formats and video.get('is_geo_blocked'):
            self.raise_geo_restricted(
                'This content might not be available in your country due to copyright reasons',
                metadata_available=True)

        # TODO: webvtt in m3u8
        subtitles = {}
        sami_path = video.get('sami_path')
        if sami_path:
            lang = self._search_regex(
                r'_([a-z]{2})\.xml', sami_path, 'lang',
                default=compat_urlparse.urlparse(url).netloc.rsplit('.', 1)[-1])
            subtitles[lang] = [{
                'url': sami_path,
            }]

        series = video.get('format_title')
        episode_number = int_or_none(video.get('format_position', {}).get('episode'))
        season = video.get('_embedded', {}).get('season', {}).get('title')
        season_number = int_or_none(video.get('format_position', {}).get('season'))

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'series': series,
            'episode_number': episode_number,
            'season': season,
            'season_number': season_number,
            'duration': int_or_none(video.get('duration')),
            'timestamp': parse_iso8601(video.get('created_at')),
            'view_count': try_get(video, lambda x: x['views']['total'], int),
            'age_limit': int_or_none(video.get('age_limit', 0)),
            'formats': formats,
            'subtitles': subtitles,
        }


class ViafreeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        viafree\.(?P<country>dk|no|se|fi)
                        /(?P<id>(?:program(?:mer)?|ohjelmat)?/(?:[^/]+/)+[^/?#&]+)
                    '''
    _TESTS = [{
        'url': 'http://www.viafree.no/programmer/underholdning/det-beste-vorspielet/sesong-2/episode-1',
        'info_dict': {
            'id': '757786',
            'ext': 'mp4',
            'title': 'Det beste vorspielet - Sesong 2 - Episode 1',
            'description': 'md5:b632cb848331404ccacd8cd03e83b4c3',
            'series': 'Det beste vorspielet',
            'season_number': 2,
            'duration': 1116,
            'timestamp': 1471200600,
            'upload_date': '20160814',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.viafree.dk/programmer/humor/comedy-central-roast-of-charlie-sheen/film/1047660',
        'info_dict': {
            'id': '1047660',
            'ext': 'mp4',
            'title': 'Comedy Central Roast of Charlie Sheen - Comedy Central Roast of Charlie Sheen',
            'description': 'md5:ec956d941ae9fd7c65a48fd64951dc6d',
            'series': 'Comedy Central Roast of Charlie Sheen',
            'season_number': 1,
            'duration': 3747,
            'timestamp': 1608246060,
            'upload_date': '20201217'
        },
        'params': {
            'skip_download': True
        }
    }, {
        # with relatedClips
        'url': 'http://www.viafree.se/program/reality/sommaren-med-youtube-stjarnorna/sasong-1/avsnitt-1',
        'only_matching': True,
    }, {
        # Different og:image URL schema
        'url': 'http://www.viafree.se/program/reality/sommaren-med-youtube-stjarnorna/sasong-1/avsnitt-2',
        'only_matching': True,
    }, {
        'url': 'http://www.viafree.se/program/livsstil/husraddarna/sasong-2/avsnitt-2',
        'only_matching': True,
    }, {
        'url': 'http://www.viafree.dk/programmer/reality/paradise-hotel/saeson-7/episode-5',
        'only_matching': True,
    }, {
        'url': 'http://www.viafree.se/program/underhallning/i-like-radio-live/sasong-1/676869',
        'only_matching': True,
    }, {
        'url': 'https://www.viafree.fi/ohjelmat/entertainment/amazing-makeovers/kausi-7/jakso-2',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    def _real_extract(self, url):
        country, path = self._match_valid_url(url).groups()
        content = self._download_json(
            'https://viafree-content.mtg-api.com/viafree-content/v1/%s/path/%s' % (country, path), path)
        program = content['_embedded']['viafreeBlocks'][0]['_embedded']['program']
        guid = program['guid']
        meta = content['meta']
        title = meta['title']

        try:
            stream_href = self._download_json(
                program['_links']['streamLink']['href'], guid,
                headers=self.geo_verification_headers())['embedded']['prioritizedStreams'][0]['links']['stream']['href']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_geo_restricted(countries=[country])
            raise

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream_href, guid, 'mp4')
        episode = program.get('episode') or {}
        return {
            'id': guid,
            'title': title,
            'thumbnail': meta.get('image'),
            'description': meta.get('description'),
            'series': episode.get('seriesTitle'),
            'subtitles': subtitles,
            'episode_number': int_or_none(episode.get('episodeNumber')),
            'season_number': int_or_none(episode.get('seasonNumber')),
            'duration': int_or_none(try_get(program, lambda x: x['video']['duration']['milliseconds']), 1000),
            'timestamp': parse_iso8601(try_get(program, lambda x: x['availability']['start'])),
            'formats': formats,
        }


class TVPlayHomeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
            https?://
            (?:tv3?)?
            play\.(?:tv3|skaties)\.(?P<country>lv|lt|ee)/
            (?P<live>lives/)?
            [^?#&]+(?:episode|programme|clip)-(?P<id>\d+)
    '''
    _TESTS = [{
        'url': 'https://play.tv3.lt/series/gauju-karai-karveliai,serial-2343791/serija-8,episode-2343828',
        'info_dict': {
            'id': '2343828',
            'ext': 'mp4',
            'title': 'Gaujų karai. Karveliai (2021) | S01E08: Serija 8',
            'description': 'md5:f6fcfbb236429f05531131640dfa7c81',
            'duration': 2710,
            'season': 'Gaujų karai. Karveliai',
            'season_number': 1,
            'release_year': 2021,
            'episode': 'Serija 8',
            'episode_number': 8,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://play.tv3.lt/series/moterys-meluoja-geriau-n-7,serial-2574652/serija-25,episode-3284937',
        'info_dict': {
            'id': '3284937',
            'ext': 'mp4',
            'season': 'Moterys meluoja geriau [N-7]',
            'season_number': 14,
            'release_year': 2021,
            'episode': 'Serija 25',
            'episode_number': 25,
            'title': 'Moterys meluoja geriau [N-7] (2021) | S14|E25: Serija 25',
            'description': 'md5:c6926e9710f1a126f028fbe121eddb79',
            'duration': 2440,
        },
        'skip': '404'
    }, {
        'url': 'https://play.tv3.lt/lives/tv6-lt,live-2838694/optibet-a-lygos-rungtynes-marijampoles-suduva--vilniaus-riteriai,programme-3422014',
        'only_matching': True,
    }, {
        'url': 'https://tv3play.skaties.lv/series/women-lie-better-lv,serial-1024464/women-lie-better-lv,episode-1038762',
        'only_matching': True,
    }, {
        'url': 'https://play.tv3.ee/series/_,serial-2654462/_,episode-2654474',
        'only_matching': True,
    }, {
        'url': 'https://tv3play.skaties.lv/clips/tv3-zinas-valsti-lidz-15novembrim-bus-majsede,clip-3464509',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        country, is_live, video_id = self._match_valid_url(url).groups()

        api_path = 'lives/programmes' if is_live else 'vods'
        data = self._download_json(
            urljoin(url, f'/api/products/{api_path}/{video_id}?platform=BROWSER&lang={country.upper()}'),
            video_id)

        video_type = 'CATCHUP' if is_live else 'MOVIE'
        stream_id = data['programRecordingId'] if is_live else video_id
        stream = self._download_json(
            urljoin(url, f'/api/products/{stream_id}/videos/playlist?videoType={video_type}&platform=BROWSER'), video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            stream['sources']['HLS'][0]['src'], video_id, 'mp4', 'm3u8_native', m3u8_id='hls')

        thumbnails = set(traverse_obj(
            data, (('galary', 'images', 'artworks'), ..., ..., ('miniUrl', 'mainUrl')), expected_type=url_or_none))

        return {
            'id': video_id,
            'title': self._resolve_title(data),
            'description': traverse_obj(data, 'description', 'lead'),
            'duration': int_or_none(data.get('duration')),
            'season': traverse_obj(data, ('season', 'serial', 'title')),
            'season_number': int_or_none(traverse_obj(data, ('season', 'number'))),
            'episode': data.get('title'),
            'episode_number': int_or_none(data.get('episode')),
            'release_year': int_or_none(traverse_obj(data, ('season', 'serial', 'year'))),
            'thumbnails': [{'url': url, 'ext': 'jpg'} for url in thumbnails],
            'formats': formats,
            'subtitles': subtitles,
        }

    @staticmethod
    def _resolve_title(data):
        return try_get(data, lambda x: (
            f'{data["season"]["serial"]["title"]} ({data["season"]["serial"]["year"]}) | '
            f'S{data["season"]["number"]:02d}E{data["episode"]:02d}: {data["title"]}'
        )) or data.get('title')

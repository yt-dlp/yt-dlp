import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlparse
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    merge_dicts,
    parse_iso8601,
    qualities,
    try_get,
    urljoin,
)


class NDRBaseIE(InfoExtractor):
    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = next(group for group in mobj.groups() if group)
        webpage = self._download_webpage(url, display_id)
        return self._extract_embed(webpage, display_id, url)


class NDRIE(NDRBaseIE):
    IE_NAME = 'ndr'
    IE_DESC = 'NDR.de - Norddeutscher Rundfunk'
    _VALID_URL = r'https?://(?:\w+\.)*ndr\.de/(?:[^/]+/)*(?P<id>[^/?#]+),[\da-z]+\.html'
    _TESTS = [{
        # httpVideo, same content id
        'url': 'http://www.ndr.de/fernsehen/Party-Poette-und-Parade,hafengeburtstag988.html',
        'md5': '6515bc255dc5c5f8c85bbc38e035a659',
        'info_dict': {
            'id': 'hafengeburtstag988',
            'display_id': 'Party-Poette-und-Parade',
            'ext': 'mp4',
            'title': 'Party, Pötte und Parade',
            'description': 'md5:ad14f9d2f91d3040b6930c697e5f6b4c',
            'uploader': 'ndrtv',
            'timestamp': 1431255671,
            'upload_date': '20150510',
            'duration': 3498,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        # httpVideo, different content id
        'url': 'http://www.ndr.de/sport/fussball/40-Osnabrueck-spielt-sich-in-einen-Rausch,osna270.html',
        'md5': '1043ff203eab307f0c51702ec49e9a71',
        'info_dict': {
            'id': 'osna272',
            'display_id': '40-Osnabrueck-spielt-sich-in-einen-Rausch',
            'ext': 'mp4',
            'title': 'Osnabrück - Wehen Wiesbaden: Die Highlights',
            'description': 'md5:32e9b800b3d2d4008103752682d5dc01',
            'uploader': 'ndrtv',
            'timestamp': 1442059200,
            'upload_date': '20150912',
            'duration': 510,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        # httpAudio, same content id
        'url': 'http://www.ndr.de/info/La-Valette-entgeht-der-Hinrichtung,audio51535.html',
        'md5': 'bb3cd38e24fbcc866d13b50ca59307b8',
        'info_dict': {
            'id': 'audio51535',
            'display_id': 'La-Valette-entgeht-der-Hinrichtung',
            'ext': 'mp3',
            'title': 'La Valette entgeht der Hinrichtung',
            'description': 'md5:22f9541913a40fe50091d5cdd7c9f536',
            'uploader': 'ndrinfo',
            'timestamp': 1631711863,
            'upload_date': '20210915',
            'duration': 884,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # with subtitles
        'url': 'https://www.ndr.de/fernsehen/sendungen/extra_3/extra-3-Satiremagazin-mit-Christian-Ehring,sendung1091858.html',
        'info_dict': {
            'id': 'extra18674',
            'display_id': 'extra-3-Satiremagazin-mit-Christian-Ehring',
            'ext': 'mp4',
            'title': 'Extra 3 vom 11.11.2020 mit Christian Ehring',
            'description': 'md5:700f6de264010585012a72f97b0ac0c9',
            'uploader': 'ndrtv',
            'upload_date': '20201207',
            'timestamp': 1614349457,
            'duration': 1749,
            'subtitles': {
                'de': [{
                    'ext': 'ttml',
                    'url': r're:^https://www\.ndr\.de.+',
                }],
            },
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'https://www.ndr.de/Fettes-Brot-Ferris-MC-und-Thees-Uhlmann-live-on-stage,festivalsommer116.html',
        'only_matching': True,
    }]

    def _extract_embed(self, webpage, display_id, url):
        embed_url = (
            self._html_search_meta(
                'embedURL', webpage, 'embed URL',
                default=None)
            or self._search_regex(
                r'\bembedUrl["\']\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
                'embed URL', group='url', default=None)
            or self._search_regex(
                r'\bvar\s*sophoraID\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
                'embed URL', group='url', default=''))
        # some more work needed if we only found sophoraID
        if re.match(r'^[a-z]+\d+$', embed_url):
            # get the initial part of the url path,. eg /panorama/archiv/2022/
            parsed_url = compat_urllib_parse_urlparse(url)
            path = self._search_regex(r'(.+/)%s' % display_id, parsed_url.path or '', 'embed URL', default='')
            # find tell-tale image with the actual ID
            ndr_id = self._search_regex(r'%s([a-z]+\d+)(?!\.)\b' % (path, ), webpage, 'embed URL', default=None)
            # or try to use special knowledge!
            NDR_INFO_URL_TPL = 'https://www.ndr.de/info/%s-player.html'
            embed_url = 'ndr:%s' % (ndr_id, ) if ndr_id else NDR_INFO_URL_TPL % (embed_url, )
        if not embed_url:
            raise ExtractorError('Unable to extract embedUrl')

        description = self._search_regex(
            r'<p[^>]+itemprop="description">([^<]+)</p>',
            webpage, 'description', default=None) or self._og_search_description(webpage)
        timestamp = parse_iso8601(
            self._search_regex(
                (r'<span[^>]+itemprop="(?:datePublished|uploadDate)"[^>]+content="(?P<cont>[^"]+)"',
                 r'\bvar\s*pdt\s*=\s*(?P<q>["\'])(?P<cont>(?:(?!(?P=q)).)+)(?P=q)', ),
                webpage, 'upload date', group='cont', default=None))
        info = self._search_json_ld(webpage, display_id, default={})
        return merge_dicts({
            '_type': 'url_transparent',
            'url': embed_url,
            'display_id': display_id,
            'description': description,
            'timestamp': timestamp,
        }, info)


class NJoyIE(NDRBaseIE):
    IE_NAME = 'njoy'
    IE_DESC = 'N-JOY'
    _VALID_URL = r'https?://(?:www\.)?n-joy\.de/(?:[^/]+/)*(?:(?P<display_id>[^/?#]+),)?(?P<id>[\da-z]+)\.html'
    _TESTS = [{
        # httpVideo, same content id
        'url': 'http://www.n-joy.de/entertainment/comedy/comedy_contest/Benaissa-beim-NDR-Comedy-Contest,comedycontest2480.html',
        'md5': 'cb63be60cd6f9dd75218803146d8dc67',
        'info_dict': {
            'id': 'comedycontest2480',
            'display_id': 'Benaissa-beim-NDR-Comedy-Contest',
            'ext': 'mp4',
            'title': 'Benaissa beim NDR Comedy Contest',
            'description': 'md5:f057a6c4e1c728b10d33b5ffd36ddc39',
            'uploader': 'ndrtv',
            'upload_date': '20141129',
            'duration': 654,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        # httpVideo, different content id
        'url': 'http://www.n-joy.de/musik/Das-frueheste-DJ-Set-des-Nordens-live-mit-Felix-Jaehn-,felixjaehn168.html',
        'md5': '417660fffa90e6df2fda19f1b40a64d8',
        'info_dict': {
            'id': 'livestream283',
            'display_id': 'Das-frueheste-DJ-Set-des-Nordens-live-mit-Felix-Jaehn-',
            'ext': 'mp3',
            'title': 'Das frueheste DJ Set des Nordens live mit Felix Jaehn',
            'description': 'md5:681698f527b8601e511e7b79edde7d2c',
            'uploader': 'njoy',
            'upload_date': '20210830',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.n-joy.de/radio/webradio/morningshow209.html',
        'only_matching': True,
    }]

    def _extract_embed(self, webpage, display_id, url=None):
        # find tell-tale URL with the actual ID, or ...
        video_id = self._search_regex(
            (r'''\bsrc\s*=\s*["']?(?:/\w+)+/([a-z]+\d+)(?!\.)\b''',
             r'<iframe[^>]+id="pp_([\da-z]+)"', ),
            webpage, 'NDR id', default=None)

        description = (
            self._html_search_meta('description', webpage)
            or self._search_regex(
                r'<div[^>]+class="subline"[^>]*>[^<]+</div>\s*<p>([^<]+)</p>',
                webpage, 'description', fatal=False))
        return {
            '_type': 'url_transparent',
            'ie_key': 'NDREmbedBase',
            'url': 'ndr:%s' % video_id,
            'display_id': display_id,
            'description': description,
            'title': display_id.replace('-', ' ').strip(),
        }


class NDREmbedBaseIE(InfoExtractor):
    IE_NAME = 'ndr:embed:base'
    _VALID_URL = r'(?:ndr:(?P<id_s>[\da-z]+)|https?://www\.ndr\.de/(?P<id>[\da-z]+)-ppjson\.json)'
    _TESTS = [{
        'url': 'ndr:soundcheck3366',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/soundcheck3366-ppjson.json',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('id_s')

        ppjson = self._download_json(
            'http://www.ndr.de/%s-ppjson.json' % video_id, video_id)

        playlist = ppjson['playlist']

        formats = []
        quality_key = qualities(('xs', 's', 'm', 'l', 'xl'))

        for format_id, f in playlist.items():
            src = f.get('src')
            if not src:
                continue
            ext = determine_ext(src, None)
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    src + '?hdcore=3.7.0&plugin=aasp-3.7.0.39.44', video_id,
                    f4m_id='hds', fatal=False))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, video_id, 'mp4', m3u8_id='hls',
                    entry_protocol='m3u8_native', fatal=False))
            else:
                quality = f.get('quality')
                ff = {
                    'url': src,
                    'format_id': quality or format_id,
                    'quality': quality_key(quality),
                }
                type_ = f.get('type')
                if type_ and type_.split('/')[0] == 'audio':
                    ff['vcodec'] = 'none'
                    ff['ext'] = ext or 'mp3'
                formats.append(ff)
        self._sort_formats(formats)

        config = playlist['config']

        live = playlist.get('config', {}).get('streamType') in ['httpVideoLive', 'httpAudioLive']
        title = config['title']
        uploader = ppjson.get('config', {}).get('branding')
        upload_date = ppjson.get('config', {}).get('publicationDate')
        duration = int_or_none(config.get('duration'))

        thumbnails = []
        poster = try_get(config, lambda x: x['poster'], dict) or {}
        for thumbnail_id, thumbnail in poster.items():
            thumbnail_url = urljoin(url, thumbnail.get('src'))
            if not thumbnail_url:
                continue
            thumbnails.append({
                'id': thumbnail.get('quality') or thumbnail_id,
                'url': thumbnail_url,
                'preference': quality_key(thumbnail.get('quality')),
            })

        subtitles = {}
        tracks = config.get('tracks')
        if tracks and isinstance(tracks, list):
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                track_url = urljoin(url, track.get('src'))
                if not track_url:
                    continue
                subtitles.setdefault(track.get('srclang') or 'de', []).append({
                    'url': track_url,
                    'ext': 'ttml',
                })

        return {
            'id': video_id,
            'title': title,
            'is_live': live,
            'uploader': uploader if uploader != '-' else None,
            'upload_date': upload_date[0:8] if upload_date else None,
            'duration': duration,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }


class NDREmbedIE(NDREmbedBaseIE):
    IE_NAME = 'ndr:embed'
    _VALID_URL = r'https?://(?:\w+\.)*ndr\.de/(?:[^/]+/)*(?P<id>[\da-z]+)-(?:(?:ard)?player|externalPlayer)\.html'
    _TESTS = [{
        'url': 'http://www.ndr.de/fernsehen/sendungen/ndr_aktuell/ndraktuell28488-player.html',
        'md5': '8b9306142fe65bbdefb5ce24edb6b0a9',
        'info_dict': {
            'id': 'ndraktuell28488',
            'ext': 'mp4',
            'title': 'Norddeutschland begrüßt Flüchtlinge',
            'is_live': False,
            'uploader': 'ndrtv',
            'upload_date': '20150907',
            'duration': 132,
        },
        'skip': 'No longer available',
    }, {
        'url': 'http://www.ndr.de/ndr2/events/soundcheck/soundcheck3366-player.html',
        'md5': '002085c44bae38802d94ae5802a36e78',
        'info_dict': {
            'id': 'soundcheck3366',
            'ext': 'mp4',
            'title': 'Ella Henderson braucht Vergleiche nicht zu scheuen',
            'is_live': False,
            'uploader': 'ndr2',
            'upload_date': '20150912',
            'duration': 3554,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        'url': 'http://www.ndr.de/info/audio51535-player.html',
        'md5': 'bb3cd38e24fbcc866d13b50ca59307b8',
        'info_dict': {
            'id': 'audio51535',
            'ext': 'mp3',
            'title': 'La Valette entgeht der Hinrichtung',
            'is_live': False,
            'uploader': 'ndrinfo',
            'upload_date': '20210915',
            'duration': 884,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/visite/visite11010-externalPlayer.html',
        'md5': 'ae57f80511c1e1f2fd0d0d3d31aeae7c',
        'info_dict': {
            'id': 'visite11010',
            'ext': 'mp4',
            'title': 'Visite - die ganze Sendung',
            'is_live': False,
            'uploader': 'ndrtv',
            'upload_date': '20150902',
            'duration': 3525,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        # httpVideoLive
        'url': 'http://www.ndr.de/fernsehen/livestream/livestream217-externalPlayer.html',
        'info_dict': {
            'id': 'livestream217',
            'ext': 'mp4',
            'title': r're:^NDR Fernsehen Niedersachsen \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'is_live': True,
            'upload_date': '20210409',
            'uploader': 'ndrtv',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.ndr.de/ndrkultur/audio255020-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/nordtour/nordtour7124-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/kultur/film/videos/videoimport10424-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/hamburg_journal/hamj43006-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/weltbilder/weltbilder4518-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/doku952-player.html',
        'only_matching': True,
    }]


class NJoyEmbedIE(NDREmbedBaseIE):
    IE_NAME = 'njoy:embed'
    _VALID_URL = r'https?://(?:www\.)?n-joy\.de/(?:[^/]+/)*(?P<id>[\da-z]+)-(?:player|externalPlayer)_[^/]+\.html'
    _TESTS = [{
        # httpVideo
        'url': 'http://www.n-joy.de/events/reeperbahnfestival/doku948-player_image-bc168e87-5263-4d6d-bd27-bb643005a6de_theme-n-joy.html',
        'md5': '8483cbfe2320bd4d28a349d62d88bd74',
        'info_dict': {
            'id': 'doku948',
            'ext': 'mp4',
            'title': 'Zehn Jahre Reeperbahn Festival - die Doku',
            'is_live': False,
            'upload_date': '20200826',
            'duration': 1011,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        # httpAudio
        'url': 'http://www.n-joy.de/news_wissen/stefanrichter100-player_image-d5e938b1-f21a-4b9a-86b8-aaba8bca3a13_theme-n-joy.html',
        'md5': 'd989f80f28ac954430f7b8a48197188a',
        'info_dict': {
            'id': 'stefanrichter100',
            'ext': 'mp3',
            'title': 'Interview mit einem Augenzeugen',
            'is_live': False,
            'uploader': 'njoy',
            'upload_date': '20150909',
            'duration': 140,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        # httpAudioLive, no explicit ext
        'url': 'http://www.n-joy.de/news_wissen/webradioweltweit100-player_image-3fec0484-2244-4565-8fb8-ed25fd28b173_theme-n-joy.html',
        'info_dict': {
            'id': 'webradioweltweit100',
            'ext': 'mp3',
            'title': r're:^N-JOY Weltweit \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'is_live': True,
            'uploader': 'njoy',
            'upload_date': '20210830',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.n-joy.de/musik/dockville882-player_image-3905259e-0803-4764-ac72-8b7de077d80a_theme-n-joy.html',
        'only_matching': True,
    }, {
        'url': 'http://www.n-joy.de/radio/sendungen/morningshow/urlaubsfotos190-player_image-066a5df1-5c95-49ec-a323-941d848718db_theme-n-joy.html',
        'only_matching': True,
    }, {
        'url': 'http://www.n-joy.de/entertainment/comedy/krudetv290-player_image-ab261bfe-51bf-4bf3-87ba-c5122ee35b3d_theme-n-joy.html',
        'only_matching': True,
    }]

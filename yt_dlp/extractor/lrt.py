from .common import InfoExtractor
from ..utils import (
    clean_html,
    unified_timestamp,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class LRTStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lrt\.lt/mediateka/tiesiogiai/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.lrt.lt/mediateka/tiesiogiai/lrt-opus',
        'info_dict': {
            'id': 'lrt-opus',
            'live_status': 'is_live',
            'title': 're:^LRT Opus.+$',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # TODO: Use _search_nextjs_v13_data once fixed
        get_stream_url = self._search_regex(
            r'\\"get_streams_url\\":\\"([^"]+)\\"', webpage, 'stream URL')
        streams_data = self._download_json(get_stream_url, video_id)

        formats, subtitles = [], {}
        for stream_url in traverse_obj(streams_data, (
                'response', 'data', lambda k, _: k.startswith('content'), {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                stream_url, video_id, 'mp4', m3u8_id='hls', live=True)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            'title': self._og_search_title(webpage),
        }


class LRTVODIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:(?:www|archyvai)\.)?lrt\.lt/mediateka/irasas/(?P<id>[0-9]+)',
        r'https?://(?:(?:www|archyvai)\.)?lrt\.lt/mediateka/video/[^?#]+\?(?:[^#]*&)?episode=(?P<id>[0-9]+)',
    ]
    _TESTS = [{
        # m3u8 download
        'url': 'https://www.lrt.lt/mediateka/irasas/2000127261/greita-ir-gardu-sicilijos-ikvepta-klasikiniu-makaronu-su-baklazanais-vakariene',
        'info_dict': {
            'id': '2000127261',
            'ext': 'mp4',
            'title': 'Nustebinkite svečius klasikiniu makaronų su baklažanais receptu',
            'description': 'md5:ad7d985f51b0dc1489ba2d76d7ed47fa',
            'timestamp': 1604086200,
            'upload_date': '20201030',
            'tags': ['LRT TELEVIZIJA', 'Beatos virtuvė', 'Beata Nicholson', 'Makaronai', 'Baklažanai', 'Vakarienė', 'Receptas'],
            'thumbnail': 'https://www.lrt.lt/img/2020/10/30/764041-126478-1287x836.jpg',
            'channel': 'Beatos virtuvė',
        },
    }, {
        # audio download
        'url': 'https://www.lrt.lt/mediateka/irasas/1013074524/kita-tema',
        'md5': 'fc982f10274929c66fdff65f75615cb0',
        'info_dict': {
            'id': '1013074524',
            'ext': 'mp4',
            'title': 'Kita tema',
            'description': 'md5:1b295a8fc7219ed0d543fc228c931fb5',
            'channel': 'Kita tema',
            'timestamp': 1473087900,
            'upload_date': '20160905',
        },
    }, {
        'url': 'https://www.lrt.lt/mediateka/video/auksinis-protas-vasara?episode=2000420320&season=%2Fmediateka%2Fvideo%2Fauksinis-protas-vasara%2F2025',
        'info_dict': {
            'id': '2000420320',
            'ext': 'mp4',
            'title': 'Kuris senovės romėnų poetas aprašė Narcizo mitą?',
            'description': 'Intelektinė viktorina. Ved. Arūnas Valinskas ir Andrius Tapinas.',
            'channel': 'Auksinis protas. Vasara',
            'thumbnail': 'https://www.lrt.lt/img/2025/06/09/2094343-987905-1287x836.jpg',
            'tags': ['LRT TELEVIZIJA', 'Auksinis protas'],
            'timestamp': 1749851040,
            'upload_date': '20250613',
        },
    }, {
        'url': 'https://archyvai.lrt.lt/mediateka/video/ziniu-riteriai-ir-damos?episode=49685&season=%2Fmediateka%2Fvideo%2Fziniu-riteriai-ir-damos%2F2013',
        'only_matching': True,
    }, {
        'url': 'https://archyvai.lrt.lt/mediateka/irasas/2000077058/panorama-1989-baltijos-kelias',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # TODO: Use _search_nextjs_v13_data once fixed
        canonical_url = (
            self._search_regex(r'\\"(?:article|data)\\":{[^}]*\\"url\\":\\"(/[^"]+)\\"', webpage, 'content URL', fatal=False)
            or self._search_regex(r'<link\s+rel="canonical"\s*href="(/[^"]+)"', webpage, 'canonical URL'))

        media = self._download_json(
            'https://www.lrt.lt/servisai/stream_url/vod/media_info/',
            video_id, query={'url': canonical_url})
        jw_data = self._parse_jwplayer_data(
            media['playlist_item'], video_id, base_url=url)

        return {
            **jw_data,
            **traverse_obj(media, {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'description': ('content', {clean_html}),
                'timestamp': ('date', {lambda x: x.replace('.', '/')}, {unified_timestamp}),
                'tags': ('tags', ..., 'name', {str}),
            }),
        }


class LRTRadioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lrt\.lt/radioteka/irasas/(?P<id>\d+)/(?P<path>[^?#/]+)'
    _TESTS = [{
        # m3u8 download
        'url': 'https://www.lrt.lt/radioteka/irasas/2000359728/nemarios-eiles-apie-pragarus-ir-skaistyklas-su-aiste-kiltinaviciute',
        'info_dict': {
            'id': '2000359728',
            'ext': 'm4a',
            'title': 'Nemarios eilės: apie pragarus ir skaistyklas su Aiste Kiltinavičiūte',
            'description': 'md5:5eee9a0e86a55bf547bd67596204625d',
            'timestamp': 1726143120,
            'upload_date': '20240912',
            'tags': 'count:5',
            'thumbnail': r're:https?://.+/.+\.jpe?g',
            'categories': ['Daiktiniai įrodymai'],
        },
    }, {
        'url': 'https://www.lrt.lt/radioteka/irasas/2000304654/vakaras-su-knyga-svetlana-aleksijevic-cernobylio-malda-v-dalis?season=%2Fmediateka%2Faudio%2Fvakaras-su-knyga%2F2023',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, path = self._match_valid_url(url).group('id', 'path')
        media = self._download_json(
            'https://www.lrt.lt/rest-api/media', video_id,
            query={'url': f'/mediateka/irasas/{video_id}/{path}'})

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(media['playlist_item']['file'], video_id),
            **traverse_obj(media, {
                'title': ('title', {str}),
                'tags': ('tags', ..., 'name', {str}),
                'categories': ('playlist_item', 'category', {str}, filter, all, filter),
                'description': ('content', {clean_html}, {str}),
                'timestamp': ('date', {lambda x: x.replace('.', '/')}, {unified_timestamp}),
                'thumbnail': ('playlist_item', 'image', {urljoin('https://www.lrt.lt')}),
            }),
        }

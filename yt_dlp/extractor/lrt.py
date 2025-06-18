from .common import InfoExtractor
from ..utils import (
    clean_html,
    merge_dicts,
    traverse_obj,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class LRTBaseIE(InfoExtractor):
    def _extract_js_var(self, webpage, var_name, default=None):
        return self._search_regex(
            fr'{var_name}\s*=\s*(["\'])((?:(?!\1).)+)\1',
            webpage, var_name.replace('_', ' '), default, group=2)


class LRTStreamIE(LRTBaseIE):
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
        streams_data = self._download_json(self._extract_js_var(webpage, 'tokenURL'), video_id)

        formats, subtitles = [], {}
        for stream_url in traverse_obj(streams_data, (
                'response', 'data', lambda k, _: k.startswith('content')), expected_type=url_or_none):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(stream_url, video_id, 'mp4', m3u8_id='hls', live=True)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        stream_title = self._extract_js_var(webpage, 'video_title', 'LRT')
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            'title': f'{self._og_search_title(webpage)} - {stream_title}',
        }


class LRTVODIE(LRTBaseIE):
    _VALID_URL = r'https?://(?:www\.)?lrt\.lt(?P<path>/mediateka/irasas/(?P<id>[0-9]+))'
    _TESTS = [{
        # m3u8 download
        'url': 'https://www.lrt.lt/mediateka/irasas/2000127261/greita-ir-gardu-sicilijos-ikvepta-klasikiniu-makaronu-su-baklazanais-vakariene',
        'info_dict': {
            'id': '2000127261',
            'ext': 'mp4',
            'title': 'Greita ir gardu: Sicilijos įkvėpta klasikinių makaronų su baklažanais vakarienė',
            'description': 'md5:ad7d985f51b0dc1489ba2d76d7ed47fa',
            'duration': 3035,
            'timestamp': 1604079000,
            'upload_date': '20201030',
            'tags': ['LRT TELEVIZIJA', 'Beatos virtuvė', 'Beata Nicholson', 'Makaronai', 'Baklažanai', 'Vakarienė', 'Receptas'],
            'thumbnail': 'https://www.lrt.lt/img/2020/10/30/764041-126478-1287x836.jpg',
        },
    }, {
        # direct mp3 download
        'url': 'http://www.lrt.lt/mediateka/irasas/1013074524/',
        'md5': '389da8ca3cad0f51d12bed0c844f6a0a',
        'info_dict': {
            'id': '1013074524',
            'ext': 'mp3',
            'title': 'Kita tema 2016-09-05 15:05',
            'description': 'md5:1b295a8fc7219ed0d543fc228c931fb5',
            'duration': 3008,
            'view_count': int,
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        path, video_id = self._match_valid_url(url).group('path', 'id')
        webpage = self._download_webpage(url, video_id)

        media_url = self._extract_js_var(webpage, 'main_url', path)
        media = self._download_json(self._extract_js_var(
            webpage, 'media_info_url',
            'https://www.lrt.lt/servisai/stream_url/vod/media_info/'),
            video_id, query={'url': media_url})
        jw_data = self._parse_jwplayer_data(
            media['playlist_item'], video_id, base_url=url)

        json_ld_data = self._search_json_ld(webpage, video_id)

        tags = []
        for tag in (media.get('tags') or []):
            tag_name = tag.get('name')
            if not tag_name:
                continue
            tags.append(tag_name)

        clean_info = {
            'description': clean_html(media.get('content')),
            'tags': tags,
        }

        return merge_dicts(clean_info, jw_data, json_ld_data)


class LRTRadioIE(LRTBaseIE):
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
            'https://www.lrt.lt/radioteka/api/media', video_id,
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

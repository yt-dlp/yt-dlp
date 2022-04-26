from .common import InfoExtractor
from ..utils import (
    clean_html,
    merge_dicts,
    try_get
)


class LRTStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lrt\.lt/mediateka/tiesiogiai/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.lrt.lt/mediateka/tiesiogiai/lrt-opus',
        'info_dict': {
            'id': 'lrt-opus',
            'live_status': 'is_live',
            'title': 're:^LRT Opus.+$',
            'ext': 'mp4'
        }
    }]

    def _extract_js_var(self, webpage, var_name, default):
        return self._search_regex(
            r'%s\s*=\s*(["\'])((?:(?!\1).)+)\1' % var_name,
            webpage, var_name.replace('_', ' '), default, group=2)

    def _real_extract(self, url):
        matches = self._match_valid_url(url).groupdict()
        video_id = matches['id']

        webpage = self._download_webpage(url, video_id)
        token_url = self._extract_js_var(webpage, 'tokenURL', None)
        stream_title = self._extract_js_var(webpage, 'video_title', 'LRT')
        title = self._og_search_title(webpage)

        streams_data = self._download_json(token_url, video_id)

        formats = []
        for key in ['content', 'content2', 'content3']:
            stream_url = try_get(streams_data, lambda x: x['response']['data'][key])
            if stream_url == '':
                continue
            formats.extend(self._extract_m3u8_formats(stream_url, video_id, m3u8_id='hls', live=True))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'is_live': True,
            'title': '{0} - {1}'.format(title, stream_title)
        }


class LRTVODIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lrt\.lt(?P<path>/mediateka/irasas/(?P<id>[0-9]+))'
    _TESTS = [{
        # m3u8 download
        'url': 'https://www.lrt.lt/mediateka/irasas/2000127261/greita-ir-gardu-sicilijos-ikvepta-klasikiniu-makaronu-su-baklazanais-vakariene',
        'md5': 'cb4b239351697e985ca3177dcc1ced8d',
        'info_dict': {
            'id': '2000127261',
            'ext': 'mp4',
            'title': 'Greita ir gardu: Sicilijos įkvėpta klasikinių makaronų su baklažanais vakarienė',
            'description': 'md5:ad7d985f51b0dc1489ba2d76d7ed47fa',
            'duration': 3035,
            'timestamp': 1604079000,
            'upload_date': '20201030',
            'tags': ['LRT TELEVIZIJA', 'Beatos virtuvė', 'Beata Nicholson', 'Makaronai', 'Baklažanai', 'Vakarienė', 'Receptas'],
            'thumbnail': 'https://www.lrt.lt/img/2020/10/30/764041-126478-1287x836.jpg'
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

    def _extract_js_var(self, webpage, var_name, default):
        return self._search_regex(
            r'%s\s*=\s*(["\'])((?:(?!\1).)+)\1' % var_name,
            webpage, var_name.replace('_', ' '), default, group=2)

    def _real_extract(self, url):
        path, video_id = self._match_valid_url(url).groups()
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

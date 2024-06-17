from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class CloudyCDNIE(InfoExtractor):
    _VALID_URL = r'(?:https?:)?//embed\.cloudycdn\.services/(?P<site_id>[^/?#]+)/media/(?P<id>[\w-]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://embed.cloudycdn.services/ltv/media/46k_d23-6000-105?',
        'md5': '64f72a360ca530d5ed89c77646c9eee5',
        'info_dict': {
            'id': '46k_d23-6000-105',
            'ext': 'mp4',
            'timestamp': 1700589151,
            'duration': 1442,
            'upload_date': '20231121',
            'title': 'D23-6000-105_cetstud',
            'thumbnail': 'https://store.cloudycdn.services/tmsp00060/assets/media/660858/placeholder1700589200.jpg',
        },
    }, {
        'url': 'https://embed.cloudycdn.services/izm/media/26e_lv-8-5-1',
        'md5': '798828a479151e2444d8dcfbec76e482',
        'info_dict': {
            'id': '26e_lv-8-5-1',
            'ext': 'mp4',
            'title': 'LV-8-5-1',
            'timestamp': 1669767167,
            'thumbnail': 'https://store.cloudycdn.services/tmsp00120/assets/media/488306/placeholder1679423604.jpg',
            'duration': 1205,
            'upload_date': '20221130',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.tavaklase.lv/video/es-esmu-mina-um-2/',
        'md5': '63074e8e6c84ac2a01f2fb8bf03b8f43',
        'info_dict': {
            'id': 'cqd_lib-2',
            'ext': 'mp4',
            'upload_date': '20230223',
            'duration': 629,
            'thumbnail': 'https://store.cloudycdn.services/tmsp00120/assets/media/518407/placeholder1678748124.jpg',
            'timestamp': 1677181513,
            'title': 'LIB-2',
        },
    }]

    def _real_extract(self, url):
        site_id, video_id = self._match_valid_url(url).group('site_id', 'id')

        data = self._download_json(
            f'https://player.cloudycdn.services/player/{site_id}/media/{video_id}/',
            video_id, data=urlencode_postdata({
                'version': '6.4.0',
                'referer': url,
            }))

        formats, subtitles = [], {}
        for m3u8_url in traverse_obj(data, ('source', 'sources', ..., 'src', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('name', {str}),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('upload_date', {parse_iso8601}),
                'thumbnail': ('source', 'poster', {url_or_none}),
            }),
        }

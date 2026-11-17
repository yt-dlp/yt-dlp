from .common import InfoExtractor
from ..utils import (
    bug_reports_message,
    clean_html,
    get_element_by_class,
    js_to_json,
    mimetype2ext,
    strip_or_none,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class BTVPlusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?btvplus\.bg/produkt/(?:predavaniya|seriali|novini)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://btvplus.bg/produkt/predavaniya/67271/btv-reporterite/btv-reporterite-12-07-2025-g',
        'info_dict': {
            'ext': 'mp4',
            'id': '67271',
            'title': 'bTV Репортерите - 12.07.2025 г.',
            'thumbnail': 'https://cdn.btv.bg/media/images/940x529/Jul2025/2113606319.jpg',
        },
    }, {
        'url': 'https://btvplus.bg/produkt/seriali/66942/sezon-2/plen-sezon-2-epizod-55',
        'info_dict': {
            'ext': 'mp4',
            'id': '66942',
            'title': 'Плен - сезон 2, епизод 55',
            'thumbnail': 'https://cdn.btv.bg/media/images/940x529/Jun2025/2113595104.jpg',
        },
    }, {
        'url': 'https://btvplus.bg/produkt/novini/67270/btv-novinite-centralna-emisija-12-07-2025',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        player_url = self._search_regex(
            r'var\s+videoUrl\s*=\s*[\'"]([^\'"]+)[\'"]',
            webpage, 'player URL')

        player_config = self._download_json(
            urljoin('https://btvplus.bg', player_url), video_id)['config']

        videojs_data = self._search_json(
            r'videojs\(["\'][^"\']+["\'],', player_config, 'videojs data',
            video_id, transform_source=js_to_json)
        formats = []
        subtitles = {}
        for src in traverse_obj(videojs_data, ('sources', lambda _, v: url_or_none(v['src']))):
            ext = mimetype2ext(src.get('type'))
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    src['src'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                self.report_warning(f'Unknown format type {ext}{bug_reports_message()}')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': (
                strip_or_none(self._og_search_title(webpage, default=None))
                or clean_html(get_element_by_class('product-title', webpage))),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
        }

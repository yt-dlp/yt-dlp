from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    get_elements_by_class,
    int_or_none,
    smuggle_url,
    traverse_obj,
    urljoin,
)


class TvbAnywhereNaIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?tvbanywherena\.com/(?P<lang>[^/]+)/videos/[^/]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.tvbanywherena.com/cantonese/videos/437-SuperTrioShow/6007674088001',
        'info_dict': {
            'id': '6007674088001',
            'ext': 'mp4',
            'title': '天下無敵獎門人 第02集',
            'upload_date': '20190227',
            'timestamp': 1551252441,
            'description': '',
            'uploader_id': '5324042807001',
            'series': '天下無敵獎門人',
            'duration': 2669.436,
            'tags': ['supertrioshow'],
            'genres': ['遊戲'],
            'cast': 'count:3',
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_year': None,
        },
    }, {
        'url': 'https://tvbanywherena.com/english/videos/362-ForensicHeroesV/1749048584749039545',
        'info_dict': {
            'id': '1749048584749039545',
            'ext': 'mp4',
            'title': 'Forensic Heroes V Episode 02',
            'upload_date': '20221111',
            'timestamp': 1668193134,
            'uploader_id': '5324042807001',
            'series': 'Forensic Heroes V',
            'duration': 2579.264,
            'tags': ['forensicheroesven'],
            'genres': ['Crime', 'Action'],
            'cast': [''],
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_year': 2022,
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _real_extract(self, url):
        lang, content_id = self._match_valid_url(url).group('lang', 'id')
        webpage = self._download_webpage(url, content_id)

        attrs = extract_attributes(get_element_html_by_id('videoPlayerID', webpage))
        brightcove = self.BRIGHTCOVE_URL_TEMPLATE % (
            attrs.get('data-account'), attrs.get('data-player'), attrs.get('data-video-id'))

        metainfo = self._search_json(r'<script[^>]+type="application/ld\+json"[^>]*>', webpage, 'info', content_id)
        seriesname = metainfo.get('alternateName' if lang == 'cantonese' else 'name')
        episodeinfo = get_element_html_by_id(content_id, webpage)
        episodename = get_element_by_class('episodeName', episodeinfo)

        return {
            '_type': 'url_transparent',
            'id': content_id,
            'url': smuggle_url(brightcove, {
                'geo_countries': ['US'],
                'referrer': 'https://tvbanywherena.com',
            }),
            'ie_key': 'BrightcoveNew',
            'title': f'{seriesname} {episodename}',
            'description': get_element_by_class(episodeinfo, 'episodeDescription'),
            'series': seriesname,
            'genres': metainfo.get('genre', []),
            'cast': traverse_obj(metainfo, ('actor', ..., 'name')),
            'release_year': int_or_none(metainfo.get('datePublished')),
        }


class TvbAnywhereNaSeriesIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?tvbanywherena\.com/(?P<lang>[^/]+)/series/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://tvbanywherena.com/cantonese/series/2594-ForensicHeroesV',
        'info_dict': {
            'id': '2594-ForensicHeroesV',
            'title': '法證先鋒V',
            'description': 'md5:ada77595c0b4bfe9fbc859087fc659b6',
            'genres': ['警匪', '動作', '劇情'],
            'cast': ['黃宗澤', '袁偉豪', '蔡思貝', '洪永城', '蔡潔', '王敏奕'],
            'release_year': 2022,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'playlist_count': 30,
    }, {
        'url': 'https://www.tvbanywherena.com/viet/series/1034-Ngh%E1%BB%8BchThi%C3%AAnK%E1%BB%B3%C3%81n2',
        'info_dict': {
            'id': '1034-Ngh%E1%BB%8BchThi%C3%AAnK%E1%BB%B3%C3%81n2',
            'title': 'Nghịch Thiên Kỳ Án 2',
            'description': 'md5:9cb8cc2aa86e97b040e805c3b1eff1be',
            'genres': ['Phim Hình Sự'],
            'cast': ['Trần Triển Bàng', 'Lâm Hạ Vi', 'Phương Lực Thân'],
            'release_year': 2024,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'playlist_count': 30,
    }]

    def _real_extract(self, url):
        lang, content_id = self._match_valid_url(url).group('lang', 'id')
        webpage = self._download_webpage(url, content_id)
        metainfo = self._search_json(r'<script[^>]+type="application/ld\+json"[^>]*>', webpage, 'info', content_id)

        def get_entries(page_data):
            for episode in get_elements_by_class('item', page_data):
                yield self.url_result(urljoin(url, extract_attributes(episode).get('href')))

        return {
            '_type': 'playlist',
            'id': content_id,
            'title': metainfo.get('alternateName' if lang == 'cantonese' else 'name'),
            'description': metainfo.get('description'),
            'genres': metainfo.get('genre', []),
            'cast': traverse_obj(metainfo, ('actor', ..., 'name')),
            'release_year': int_or_none(metainfo.get('datePublished')),
            'thumbnail': metainfo.get('image'),
            'entries': get_entries(webpage),
        }

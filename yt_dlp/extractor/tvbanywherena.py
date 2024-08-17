from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    get_elements_by_class,
    int_or_none,
    smuggle_url,
    urljoin,
)


def _get_program_url(lang, pid):
    if lang == 'english':
        return f'https://api.tvbaw.com/EN/getProgramByPid?value={pid}'
    if lang == 'viet':
        return f'https://api.tvbaw.com/VN/getProgramByPid?value={pid}'

    return f'https://api.tvbaw.com/getProgramByPid?value={pid}'


class TvbAnywhereNaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvbanywherena\.com/(?P<lang>cantonese|english|viet)/videos/[^/]+/(?P<id>\d+)'
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
        'url': 'https://tvbanywherena.com/english/videos/221-BirthOfAHero/5998951339001',
        'info_dict': {
            'id': '5998951339001',
            'ext': 'mp4',
            'title': 'Birth Of A Hero Episode 04',
            'description': 'WAN-LUNG is severely beaten up and lapses into a coma. After regaining his consciousness, he pretends lunacy on purpose...',
            'upload_date': '20190206',
            'timestamp': 1549419051,
            'uploader_id': '5324042807001',
            'series': 'Birth Of A Hero',
            'duration': 2593.984,
            'tags': ['en_birthofahero'],
            'genres': ['Historical'],
            'cast': ['Edwin Siu', 'Ben Wong', 'Grace Chan', 'David Chiang '],
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_year': 2018,
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _real_extract(self, url):
        lang, content_id = self._match_valid_url(url).group('lang', 'id')
        webpage = self._download_webpage(url, content_id)

        attrs = extract_attributes(get_element_html_by_id('videoPlayerID', webpage))
        brightcove = self.BRIGHTCOVE_URL_TEMPLATE % (
            attrs.get('data-account'), attrs.get('data-player'), attrs.get('data-video-id'))

        pid = self._search_regex(r'\'pid\':\s*\'(\d+)\'', webpage, 'pid')
        program = self._download_json(_get_program_url(lang, pid), content_id)
        seriesname = program.get('title' if lang == 'cantonese' else 'subtitle')
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
            'description': get_element_by_class('episodeDescription', episodeinfo),
            'series': seriesname,
            'genres': program.get('genres', []),
            'cast': program.get('char', []),
            'release_year': int_or_none(program.get('year')),
        }


class TvbAnywhereNaSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvbanywherena\.com/(?P<lang>cantonese|english|viet)/series/(?P<id>\d+)-'
    _TESTS = [{
        'url': 'https://tvbanywherena.com/cantonese/series/2594-ForensicHeroesV',
        'info_dict': {
            'id': '2594',
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
            'id': '1034',
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
        program = self._download_json(_get_program_url(lang, content_id), content_id)
        # brightcove_playlist_id = program.get('bcov')

        def get_entries(page_data):
            for episode in get_elements_by_class('item', page_data):
                yield self.url_result(urljoin(url, extract_attributes(episode).get('href')))

        return {
            '_type': 'playlist',
            'id': content_id,
            'title': program.get('title' if lang == 'cantonese' else 'subtitle'),
            'description': program.get('synopsis'),
            'genres': program.get('genres', []),
            'cast': program.get('char', []),
            'release_year': int_or_none(program.get('year')),
            'thumbnail': program.get('large'),
            'entries': get_entries(webpage),
        }

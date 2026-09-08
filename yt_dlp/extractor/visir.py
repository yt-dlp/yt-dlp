import re

from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    clean_html,
    int_or_none,
    js_to_json,
    month_by_name,
    url_or_none,
    urljoin,
)
from ..utils.traversal import find_element, traverse_obj


class VisirIE(InfoExtractor):
    IE_DESC = 'Vísir'

    _VALID_URL = r'https?://(?:www\.)?visir\.is/(?P<type>k|player)/(?P<id>[\da-f-]+)(?:/(?P<slug>[\w.-]+))?'
    _EMBED_REGEX = [rf'<iframe[^>]+src=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://www.visir.is/k/eabb8f7f-ad87-46fb-9469-a0f1dc0fc4bc-1769022963988',
        'info_dict': {
            'id': 'eabb8f7f-ad87-46fb-9469-a0f1dc0fc4bc-1769022963988',
            'ext': 'mp4',
            'title': 'Sveppi og Siggi Þór mestu skaphundarnir',
            'categories': ['island-i-dag'],
            'description': 'md5:e06bd6a0cd8bdde328ad8cf00d3d4df6',
            'duration': 792,
            'thumbnail': r're:https?://www\.visir\.is/.+',
            'upload_date': '20260121',
            'view_count': int,
        },
    }, {
        'url': 'https://www.visir.is/k/b0a88e02-eceb-4270-855c-8328b76b9d81-1763979306704/tonlistarborgin-reykjavik',
        'info_dict': {
            'id': 'b0a88e02-eceb-4270-855c-8328b76b9d81-1763979306704',
            'ext': 'mp4',
            'title': 'Tónlistarborgin Reykjavík',
            'categories': ['tonlist'],
            'description': 'md5:47237589dc95dbde55dfbb163396f88a',
            'display_id': 'tonlistarborgin-reykjavik',
            'duration': 81,
            'thumbnail': r're:https?://www\.visir\.is/.+',
            'upload_date': '20251124',
            'view_count': int,
        },
    }, {
        'url': 'https://www.visir.is/player/0cd5709e-6870-46d0-aaaf-0ae637de94f1-1770060083580',
        'info_dict': {
            'id': '0cd5709e-6870-46d0-aaaf-0ae637de94f1-1770060083580',
            'ext': 'mp4',
            'title': 'Sportpakkinn 2. febrúar 2026',
            'categories': ['sportpakkinn'],
            'display_id': 'sportpakkinn-2.-februar-2026',
            'duration': 293,
            'thumbnail': r're:https?://www\.visir\.is/.+',
            'upload_date': '20260202',
            'view_count': int,
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.visir.is/g/20262837896d/segir-von-brigdin-med-prinsessuna-rista-djupt',
        'info_dict': {
            'id': '9ad5e58a-f26f-49f7-8b1d-68f0629485b7-1770059257365',
            'ext': 'mp4',
            'title': 'Norðmenn tala ekki um annað en prinsessuna',
            'categories': ['frettir'],
            'description': 'md5:53e2623ae79e1355778c14f5b557a0cd',
            'display_id': 'nordmenn-tala-ekki-um-annad-en-prinsessuna',
            'duration': 138,
            'thumbnail': r're:https?://www\.visir\.is/.+',
            'upload_date': '20260202',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_type, video_id, display_id = self._match_valid_url(url).group('type', 'id', 'slug')
        webpage = self._download_webpage(url, video_id)
        if video_type == 'player':
            real_url = self._og_search_url(webpage)
            if not self.suitable(real_url) or self._match_valid_url(real_url).group('type') == 'player':
                raise UnsupportedError(real_url)
            return self.url_result(real_url, self.ie_key())

        upload_date = None
        date_elements = traverse_obj(webpage, (
            {find_element(cls='article-item__date')}, {clean_html}, filter, {str.split}))
        if date_elements and len(date_elements) == 3:
            day, month, year = date_elements
            day = int_or_none(day.rstrip('.'))
            month = month_by_name(month, 'is')
            if day and month and re.fullmatch(r'[0-9]{4}', year):
                upload_date = f'{year}{month:02d}{day:02d}'

        player = self._search_json(
            r'App\.Player\.Init\(', webpage, video_id, 'player', transform_source=js_to_json)
        m3u8_url = traverse_obj(player, ('File', {urljoin('https://vod.visir.is/')}))

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
            'upload_date': upload_date,
            **traverse_obj(webpage, ({find_element(cls='article-item press-ads')}, {
                'description': ({find_element(cls='-large')}, {clean_html}, filter),
                'view_count': ({find_element(cls='article-item__viewcount')}, {clean_html}, {int_or_none}),
            })),
            **traverse_obj(player, {
                'title': ('Title', {clean_html}),
                'categories': ('Categoryname', {clean_html}, filter, all, filter),
                'duration': ('MediaDuration', {int_or_none}),
                'thumbnail': ('Image', {url_or_none}),
            }),
        }

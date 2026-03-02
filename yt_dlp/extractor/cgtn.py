from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    get_element_html_by_id,
    try_get,
    unescapeHTML,
    unified_strdate,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class CGTNIE(InfoExtractor):
    _VALID_URL = r'https?://news\.cgtn\.com/news/[0-9]{4}-[0-9]{2}-[0-9]{2}/[a-zA-Z0-9-]+-(?P<id>[a-zA-Z0-9-]+)/index\.html'
    _TESTS = [
        {
            'url': 'https://news.cgtn.com/news/2021-03-09/Up-and-Out-of-Poverty-Ep-1-A-solemn-promise-YuOUaOzGQU/index.html',
            'info_dict': {
                'id': 'YuOUaOzGQU',
                'ext': 'mp4',
                'title': 'Up and Out of Poverty Ep. 1: A solemn promise',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1615295940,
                'upload_date': '20210309',
                'categories': ['Video'],
            },
            'params': {
                'skip_download': True,
            },
        }, {
            'url': 'https://news.cgtn.com/news/2021-06-06/China-Indonesia-vow-to-further-deepen-maritime-cooperation-10REvJCewCY/index.html',
            'info_dict': {
                'id': '10REvJCewCY',
                'ext': 'mp4',
                'title': 'China, Indonesia vow to further deepen maritime cooperation',
                'thumbnail': r're:^https?://.*\.png$',
                'description': 'China and Indonesia vowed to upgrade their cooperation into the maritime sector and also for political security, economy, and cultural and people-to-people exchanges.',
                'creators': ['CGTN'],
                'categories': ['China'],
                'timestamp': 1622950200,
                'upload_date': '20210606',
            },
            'params': {
                'skip_download': False,
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        download_url = self._html_search_regex(r'data-video ="(?P<url>.+m3u8)"', webpage, 'download_url')
        datetime_str = self._html_search_regex(
            r'<span class="date">\s*(.+?)\s*</span>', webpage, 'datetime_str', fatal=False)
        category = self._html_search_regex(
            r'<span class="section">\s*(.+?)\s*</span>', webpage, 'category', fatal=False)
        author = self._search_regex(
            r'<div class="news-author-name">\s*(.+?)\s*</div>', webpage, 'author', default=None)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': self._extract_m3u8_formats(download_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'),
            'categories': [category] if category else None,
            'creators': [author] if author else None,
            'timestamp': try_get(unified_timestamp(datetime_str), lambda x: x - 8 * 3600),
        }

class CGTNRUSSIANIE(InfoExtractor):
    _VALID_URL = r'https?://russian\.cgtn\.com/news/(?P<date>\d{4}-\d{2}-\d{2})/(?P<id>\d+)/.*$'
    _TESTS = [
        {
            'url': 'https://russian.cgtn.com/news/2026-03-02/2028389396766744578/index.html',
            'info_dict': {
                'id': '2028389396766744578',
                'title': 'Министр культуры РФ о сотрудничестве России и КНР в сфере кинопроизводства',
                'description': 'Москва и Пекин продолжают развивать сотрудничество в гуманитарной сфере. В 2024 и 2025 в Китае и России прошло более 430 мероприятий в рамках перекрестных Годов культуры. Подписанный в прошлом году Документ о совместном кинопроизводстве РФ и КНР до 2030 года открывает новые возможности. Интересные перспективы открываются и у студентов двух стран, которые обучаются творческим профессиям. Об этом в эксклюзивном интервью нашему телеканалу рассказала министр культуры России Ольга Любимова. Министр культуры России Ольга Любимова: "Очень важно, что между нашими ведомствами подписан очень такой значимый для нас стратегический документ о совместном сотрудничестве в области кинематографии до 2030 года. И нам очень важно и дорого участие китайских кинематографистов в важнейших наших международных кинофестивалях. Вы знаете, что китайская кинематография первые в мире – 120 000 кинозалов. Это невероятный совершенно объем. И невероятное совершенно количество зрителей, которые ежегодно посещают кинотеатры с большим удовольствием. В России российские продюсеры борются за честь обрести печать дракона, прокатное удостоверение и возможность прокатать российское кино. И мы очень рады, что российское кино получает эту печать дракона. Это такой, мне кажется, знак качества для любой картины, из какой бы страны она не пожаловала в Китай. Я хочу упомянуть еще одно ключевое для нас направление в нашей деятельности - это образование. Мы очень любим китайских студентов, но это невероятно талантливые художники, невероятно талантливые артисты балета. Поэтому впереди, мне кажется, у нас много и совместных постановок, и мы ждем премьер, и гастролей, и с огромным интересом.',
                'thumbnail': r're:https?://russian\.cgtn\.com/.+\.(?:jpg|png)',
                'duration': 123.48,
            },
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        date = unified_strdate(mobj.group('date'))
        video_id = mobj.group('id')
        description = ''
        webpage = self._download_webpage(url, video_id)
        # Extracting data-json from the tag with id='cmsMainContent'
        target_element = get_element_html_by_id('cmsMainContent', webpage)
        if not target_element:
            raise ExtractorError('Cannot get html element with data')
        json_data = extract_attributes(target_element).get('data-json')
        if not json_data:
            raise ExtractorError('Cannot extract data from html element')
        json_data = unescapeHTML(json_data)
        if not json_data:
            raise ExtractorError('Cannot unescape html data')
        json_data = self._parse_json(json_data, video_id)
        for d in json_data:
            if d.get('type') == 3:
                content_data = d.get('content')
            if d.get('type') == 0:
                description += d.get('content', '')
        if not content_data:
            raise ExtractorError('Cannot get content data')
        content_data = traverse_obj(
            self._parse_json(content_data, video_id),
            (
                {
                    'thumbnail': ('poster', 'url', {url_or_none}),
                    'm3u8_url': ('url', {url_or_none}),
                    'duration': ('duration', {float_or_none}),
                }
            ),
        )
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            content_data['m3u8_url'],
            video_id,
            'mp4',
            m3u8_id='hls',
        )

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'release_date': date,
            'title': self._og_search_title(webpage)
            or self._html_extract_title(webpage),
            'description': clean_html(description),
            **content_data,
        }

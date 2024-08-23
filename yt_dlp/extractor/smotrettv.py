import urllib.parse

from .common import InfoExtractor
from ..utils import (
    base_url,
    clean_html,
    extract_attributes,
    get_domain,
    get_element_by_class,
    traverse_obj,
    url_or_none,
)


class SmotretTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?smotret\.tv/(?P<id>[^/#?]+)'

    _TESTS = [{
        # direct streams
        'url': 'https://smotret.tv/rossiya-1',
        'info_dict': {
            'id': 'rossiya-1',
            'ext': 'mp4',
            'title': 're:Россия 1 — смотреть онлайн прямой эфир [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': str,
            'thumbnail': 'https://smotret.tv/images/rossiya-1.jpg',
            'live_status': 'is_live',
            'subtitles': dict,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # RutubeEmbed in iframe
        'url': 'https://smotret.tv/otr',
        'info_dict': {
            'id': 'faa934385b83f9e8a92f5484defae5fa',  # TODO: use "otr"
            'ext': 'mp4',
            'title': 're:ОТР — смотреть онлайн прямой эфир [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'live_status': 'is_live',
            'timestamp': 1713523453,
            'uploader': 'Общественное Телевидение России - ОТР',
            'uploader_id': '23460694',
            'upload_date': '20240419',
            'categories': ['Телепередачи'],
            'age_limit': 0,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://smotret.tv/rbk',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, impersonate=True)
        title = self._og_search_title(webpage)

        video_page_url = urllib.parse.urljoin(base_url(url), extract_attributes(
            get_element_by_class('video-content', webpage))['src'])
        video_page = self._download_webpage(
            video_page_url, video_id, impersonate=True,
            note='Downloading video page', errnote='Unable to download video page')

        if m3u8_urls := self._search_json(
                r'var\s+streams\s*=', video_page, 'stream urls', video_id,
                contains_pattern=r'(\[.+\])', default=[]):
            formats, subtitles = [], {}
            for m3u8_url in traverse_obj(m3u8_urls, (..., {url_or_none})):  # filter out "/error.m3u8"
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    m3u8_url, video_id, m3u8_id=get_domain(m3u8_url), ext='mp4')
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            return {
                'id': video_id,
                'title': title,
                'description': self._og_search_description(webpage),
                'thumbnail': self._og_search_thumbnail(webpage),
                'formats': formats,
                'subtitles': subtitles,
                'is_live': True,
            }

        if player_url := self._html_search_regex(
                r'<iframe src="([^"]+)"', video_page, 'embedded player url', default=None):
            return self.url_result(player_url, None, video_id, title, url_transparent=True)


class SmotretTVLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?smotret-tv\.live/(?P<id>[^/#?.]+)'

    _TESTS = [{
        'url': 'http://smotret-tv.live/8-kanal.html',
        'info_dict': {
            'id': '8-kanal',
            'ext': 'mp4',
            'title': 're:8 канал смотреть онлайн бесплатно прямой эфир [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': str,
            'thumbnail': 'http://smotret-tv.live/images/8-kanal.png',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://smotret-tv.live/zvezda',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        base = base_url(url)

        logo_url = None
        if postopis := get_element_by_class('postopis', webpage):
            if logo_path := self._search_regex(
                    r'<img\s+src\s*=\s*"(?P<path>[^"]+)".+?/>', postopis, 'logo path', group='path', default=None):
                logo_url = urllib.parse.urljoin(base, logo_path)

        player = self._download_webpage(f'http://cdntvmedia.com/{video_id}.php', video_id, headers={'Referer': base})
        m3u8_urls = self._search_regex(
            r'Playerjs\s*\(\s*{.+?\s*file:\s*(["\'])(?P<url>https://[^"\']+)\1', player, 'player', group='url')

        return {
            'id': video_id,
            'title': self._html_extract_title(webpage),
            'description': clean_html(postopis),
            'thumbnail': logo_url,
            'formats': traverse_obj(m3u8_urls, (
                {lambda x: x.split('or')}, ..., {url_or_none},
                {lambda x: self._extract_m3u8_formats(x, video_id, m3u8_id=get_domain(x))}, ...)),
            'is_live': True,
        }

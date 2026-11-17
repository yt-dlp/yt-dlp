from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
)


class TVCIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvc\.ru/video/iframe/id/(?P<id>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:http:)?//(?:www\.)?tvc\.ru/video/iframe/id/[^"]+)\1']
    _TESTS = [{
        'url': 'http://www.tvc.ru/video/iframe/id/74622/isPlay/false/id_stat/channel/?acc_video_id=/channel/brand/id/17/show/episodes/episode_id/39702',
        'md5': 'aa6fb3cf384e18a0ad3b30ee2898beba',
        'info_dict': {
            'id': '74622',
            'ext': 'mp4',
            'title': 'TVC video #74622',
            'duration': 1122,
            'thumbnail': r're:https?://cdn\.tvc\.ru/pictures/.+\.jpg',
        },
    }]
    _WEBPAGE_TESTS = [{
        # FIXME: Embed detection
        'url': 'https://krizis-centr.ru/informatsiya/smi-o-tsentre/liniya-zashchity-bitye-zhjony-tv-tsentr',
        'md5': '43b8eee579a5cd2b85c9ed5b73d1c671',
        'info_dict': {
            'id': '123378',
            'ext': 'mp4',
            'title': 'TVC video #123378',
            'duration': 1526,
            'thumbnail': r're:https?://cdn\.tvc\.ru/pictures/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            f'http://www.tvc.ru/video/json/id/{video_id}', video_id)

        formats = []
        for info in video.get('path', {}).get('quality', []):
            video_url = info.get('url')
            if not video_url:
                continue
            format_id = self._search_regex(
                r'cdnvideo/([^/]+?)(?:-[^/]+?)?/', video_url,
                'format id', default=None)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': int_or_none(info.get('width')),
                'height': int_or_none(info.get('height')),
                'tbr': int_or_none(info.get('bitrate')),
            })

        return {
            'id': video_id,
            'title': video['title'],
            'thumbnail': video.get('picture'),
            'duration': int_or_none(video.get('duration')),
            'formats': formats,
        }


class TVCArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvc\.ru/(?!video/iframe/id/)(?P<id>[^?#]+)'
    _TESTS = [{
        'url': 'http://www.tvc.ru/channel/brand/id/29/show/episodes/episode_id/39702/',
        'info_dict': {
            'id': '74622',
            'ext': 'mp4',
            'title': 'События. "События". Эфир от 22.05.2015 14:30',
            'description': 'md5:ad7aa7db22903f983e687b8a3e98c6dd',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1122,
        },
    }, {
        'url': 'http://www.tvc.ru/news/show/id/69944',
        'info_dict': {
            'id': '75399',
            'ext': 'mp4',
            'title': 'Эксперты: в столице встал вопрос о максимально безопасных остановках',
            'description': 'md5:f2098f71e21f309e89f69b525fd9846e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 278,
        },
    }, {
        'url': 'http://www.tvc.ru/channel/brand/id/47/show/episodes#',
        'info_dict': {
            'id': '2185',
            'ext': 'mp4',
            'title': 'Ещё не поздно. Эфир от 03.08.2013',
            'description': 'md5:51fae9f3f8cfe67abce014e428e5b027',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 3316,
        },
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, self._match_id(url))
        return {
            '_type': 'url_transparent',
            'ie_key': 'TVC',
            'url': self._og_search_video_url(webpage),
            'title': clean_html(self._og_search_title(webpage)),
            'description': clean_html(self._og_search_description(webpage)),
            'thumbnail': self._og_search_thumbnail(webpage),
        }

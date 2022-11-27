from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_qs,
    xpath_text,
    qualities,
)


class PladformIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:
                                out\.pladform\.ru/player|
                                static\.pladform\.ru/player\.swf
                            )
                            \?.*\bvideoid=|
                            video\.pladform\.ru/catalog/video/videoid/
                        )
                        (?P<id>\d+)
                    '''
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//out\.pladform\.ru/player\?.+?)\1']
    _TESTS = [{
        'url': 'http://out.pladform.ru/player?pl=18079&type=html5&videoid=100231282',
        'info_dict': {
            'id': '6216d548e755edae6e8280667d774791',
            'ext': 'mp4',
            'timestamp': 1406117012,
            'title': 'Гарик Мартиросян и Гарик Харламов - Кастинг на концерт ко Дню милиции',
            'age_limit': 0,
            'upload_date': '20140723',
            'thumbnail': str,
            'view_count': int,
            'description': str,
            'category': list,
            'uploader_id': '12082',
            'uploader': 'Comedy Club',
            'duration': 367,
        },
        'expected_warnings': ['HTTP Error 404: Not Found']
    }, {
        'url': 'https://out.pladform.ru/player?pl=64471&videoid=3777899&vk_puid15=0&vk_puid34=0',
        'md5': '53362fac3a27352da20fa2803cc5cd6f',
        'info_dict': {
            'id': '3777899',
            'ext': 'mp4',
            'title': 'СТУДИЯ СОЮЗ • Шоу Студия Союз, 24 выпуск (01.02.2018) Нурлан Сабуров и Слава Комиссаренко',
            'description': 'md5:05140e8bf1b7e2d46e7ba140be57fd95',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 3190,
        },
    }, {
        'url': 'http://static.pladform.ru/player.swf?pl=21469&videoid=100183293&vkcid=0',
        'only_matching': True,
    }, {
        'url': 'http://video.pladform.ru/catalog/video/videoid/100183293/vkcid/0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        qs = parse_qs(url)
        pl = qs.get('pl', ['1'])[0]

        video = self._download_xml(
            'http://out.pladform.ru/getVideo', video_id, query={
                'pl': pl,
                'videoid': video_id,
            }, fatal=False)

        def fail(text):
            raise ExtractorError(
                '%s returned error: %s' % (self.IE_NAME, text),
                expected=True)

        if not video:
            targetUrl = self._request_webpage(url, video_id, note='Resolving final URL').geturl()
            if targetUrl == url:
                raise ExtractorError('Can\'t parse page')
            return self.url_result(targetUrl)

        if video.tag == 'error':
            fail(video.text)

        quality = qualities(('ld', 'sd', 'hd'))

        formats = []
        for src in video.findall('./src'):
            if src is None:
                continue
            format_url = src.text
            if not format_url:
                continue
            if src.get('type') == 'hls' or determine_ext(format_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': src.text,
                    'format_id': src.get('quality'),
                    'quality': quality(src.get('quality')),
                })

        if not formats:
            error = xpath_text(video, './cap', 'error', default=None)
            if error:
                fail(error)

        webpage = self._download_webpage(
            'http://video.pladform.ru/catalog/video/videoid/%s' % video_id,
            video_id)

        title = self._og_search_title(webpage, fatal=False) or xpath_text(
            video, './/title', 'title', fatal=True)
        description = self._search_regex(
            r'</h3>\s*<p>([^<]+)</p>', webpage, 'description', fatal=False)
        thumbnail = self._og_search_thumbnail(webpage) or xpath_text(
            video, './/cover', 'cover')

        duration = int_or_none(xpath_text(video, './/time', 'duration'))
        age_limit = int_or_none(xpath_text(video, './/age18', 'age limit'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': age_limit,
            'formats': formats,
        }

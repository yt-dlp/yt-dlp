import urllib.parse

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    qualities,
    unified_strdate,
    url_or_none,
)


class FirstTVIE(InfoExtractor):
    IE_NAME = '1tv'
    IE_DESC = 'Первый канал'
    _VALID_URL = r'https?://(?:www\.)?1tv\.ru/(?:[^/]+/)+(?P<id>[^/?#]+)'

    _TESTS = [{
        # single format
        'url': 'http://www.1tv.ru/shows/naedine-so-vsemi/vypuski/gost-lyudmila-senchina-naedine-so-vsemi-vypusk-ot-12-02-2015',
        'md5': 'a1b6b60d530ebcf8daacf4565762bbaf',
        'info_dict': {
            'id': '40049',
            'ext': 'mp4',
            'title': 'Гость Людмила Сенчина. Наедине со всеми. Выпуск от 12.02.2015',
            'thumbnail': r're:^https?://.*\.(?:jpg|JPG)$',
            'upload_date': '20150212',
            'duration': 2694,
        },
    }, {
        # multiple formats
        'url': 'http://www.1tv.ru/shows/dobroe-utro/pro-zdorove/vesennyaya-allergiya-dobroe-utro-fragment-vypuska-ot-07042016',
        'info_dict': {
            'id': '364746',
            'ext': 'mp4',
            'title': 'Весенняя аллергия. Доброе утро. Фрагмент выпуска от 07.04.2016',
            'thumbnail': r're:^https?://.*\.(?:jpg|JPG)$',
            'upload_date': '20160407',
            'duration': 179,
            'formats': 'mincount:3',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.1tv.ru/news/issue/2016-12-01/14:00',
        'info_dict': {
            'id': '14:00',
            'title': 'Выпуск новостей в 14:00   1 декабря 2016 года. Новости. Первый канал',
            'description': 'md5:2e921b948f8c1ff93901da78ebdb1dfd',
        },
        'playlist_count': 13,
    }, {
        'url': 'http://www.1tv.ru/shows/tochvtoch-supersezon/vystupleniya/evgeniy-dyatlov-vladimir-vysockiy-koni-priveredlivye-toch-v-toch-supersezon-fragment-vypuska-ot-06-11-2016',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)
        playlist_url = urllib.parse.urljoin(url, self._search_regex(
            r'data-playlist-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
            webpage, 'playlist url', group='url'))

        parsed_url = urllib.parse.urlparse(playlist_url)
        qs = urllib.parse.parse_qs(parsed_url.query)
        item_ids = qs.get('videos_ids[]') or qs.get('news_ids[]')

        items = self._download_json(playlist_url, display_id)

        if item_ids:
            items = [
                item for item in items
                if item.get('uid') and str(item['uid']) in item_ids]
        else:
            items = [items[0]]

        entries = []
        QUALITIES = ('ld', 'sd', 'hd')

        for item in items:
            title = item['title']
            quality = qualities(QUALITIES)
            formats = []
            path = None
            for f in item.get('mbr', []):
                src = url_or_none(f.get('src'))
                if not src:
                    continue
                tbr = int_or_none(self._search_regex(
                    r'_(\d{3,})\.mp4', src, 'tbr', default=None))
                if not path:
                    path = self._search_regex(
                        r'//[^/]+/(.+?)_\d+\.mp4', src,
                        'm3u8 path', default=None)
                formats.append({
                    'url': src,
                    'format_id': f.get('name'),
                    'tbr': tbr,
                    'source_preference': quality(f.get('name')),
                    # quality metadata of http formats may be incorrect
                    'preference': -10,
                })
            # m3u8 URL format is reverse engineered from [1] (search for
            # master.m3u8). dashEdges (that is currently balancer-vod.1tv.ru)
            # is taken from [2].
            # 1. http://static.1tv.ru/player/eump1tv-current/eump-1tv.all.min.js?rnd=9097422834:formatted
            # 2. http://static.1tv.ru/player/eump1tv-config/config-main.js?rnd=9097422834
            if not path and len(formats) == 1:
                path = self._search_regex(
                    r'//[^/]+/(.+?$)', formats[0]['url'],
                    'm3u8 path', default=None)
            if path:
                if len(formats) == 1:
                    m3u8_path = ','
                else:
                    tbrs = [str(t) for t in sorted(f['tbr'] for f in formats)]
                    m3u8_path = '_,{},{}'.format(','.join(tbrs), '.mp4')
                formats.extend(self._extract_m3u8_formats(
                    f'http://balancer-vod.1tv.ru/{path}{m3u8_path}.urlset/master.m3u8',
                    display_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', fatal=False))

            thumbnail = item.get('poster') or self._og_search_thumbnail(webpage)
            duration = int_or_none(item.get('duration') or self._html_search_meta(
                'video:duration', webpage, 'video duration', fatal=False))
            upload_date = unified_strdate(self._html_search_meta(
                'ya:ovs:upload_date', webpage, 'upload date', default=None))

            entries.append({
                'id': str(item.get('id') or item['uid']),
                'thumbnail': thumbnail,
                'title': title,
                'upload_date': upload_date,
                'duration': int_or_none(duration),
                'formats': formats,
            })

        title = self._html_search_regex(
            (r'<div class="tv_translation">\s*<h1><a href="[^"]+">([^<]*)</a>',
             r"'title'\s*:\s*'([^']+)'"),
            webpage, 'title', default=None) or self._og_search_title(
            webpage, default=None)
        description = self._html_search_regex(
            r'<div class="descr">\s*<div>&nbsp;</div>\s*<p>([^<]*)</p></div>',
            webpage, 'description', default=None) or self._html_search_meta(
            'description', webpage, 'description', default=None)

        return self.playlist_result(entries, display_id, title, description)

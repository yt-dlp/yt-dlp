import urllib.parse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    join_nonempty,
    mimetype2ext,
    parse_qs,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class FirstTVIE(InfoExtractor):
    IE_NAME = '1tv'
    IE_DESC = 'Первый канал'
    _VALID_URL = r'https?://(?:www\.)?(?:sport)?1tv\.ru/(?:[^/?#]+/)+(?P<id>[^/?#]+)'

    _TESTS = [{
        # single format; has item.id
        'url': 'https://www.1tv.ru/shows/naedine-so-vsemi/vypuski/gost-lyudmila-senchina-naedine-so-vsemi-vypusk-ot-12-02-2015',
        'md5': '8011ae8e88ff4150107ab9c5a8f5b659',
        'info_dict': {
            'id': '40049',
            'ext': 'mp4',
            'title': 'Гость Людмила Сенчина. Наедине со всеми. Выпуск от 12.02.2015',
            'thumbnail': r're:https?://.+/.+\.jpg',
            'upload_date': '20150212',
            'duration': 2694,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # multiple formats; has item.id
        'url': 'https://www.1tv.ru/shows/dobroe-utro/pro-zdorove/vesennyaya-allergiya-dobroe-utro-fragment-vypuska-ot-07042016',
        'info_dict': {
            'id': '364746',
            'ext': 'mp4',
            'title': 'Весенняя аллергия. Доброе утро. Фрагмент выпуска от 07.04.2016',
            'thumbnail': r're:https?://.+/.+\.jpg',
            'upload_date': '20160407',
            'duration': 179,
            'formats': 'mincount:3',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.1tv.ru/news/issue/2016-12-01/14:00',
        'info_dict': {
            'id': '14:00',
            'title': 'Выпуск программы «Время» в 20:00   1 декабря 2016 года. Новости. Первый канал',
            'thumbnail': 'https://static.1tv.ru/uploads/photo/image/8/big/338448_big_8fc7eb236f.jpg',
        },
        'playlist_count': 13,
    }, {
        # has timestamp; has item.uid but not item.id
        'url': 'https://www.1tv.ru/shows/segodnya-vecherom/vypuski/avtory-odnogo-hita-segodnya-vecherom-vypusk-ot-03-05-2025',
        'info_dict': {
            'id': '270411',
            'ext': 'mp4',
            'title': 'Авторы одного хита. Сегодня вечером. Выпуск от 03.05.2025',
            'thumbnail': r're:https?://.+/.+\.jpg',
            'timestamp': 1746286020,
            'upload_date': '20250503',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://www.1tv.ru/shows/tochvtoch-supersezon/vystupleniya/evgeniy-dyatlov-vladimir-vysockiy-koni-priveredlivye-toch-v-toch-supersezon-fragment-vypuska-ot-06-11-2016',
        'only_matching': True,
    }, {
        'url': 'https://www.sport1tv.ru/sport/chempionat-rossii-po-figurnomu-kataniyu-2025',
        'only_matching': True,
    }]

    def _entries(self, items):
        for item in items:
            video_id = str(item.get('id') or item['uid'])

            formats, subtitles = [], {}
            for f in traverse_obj(item, ('sources', lambda _, v: url_or_none(v['src']))):
                src = f['src']
                ext = mimetype2ext(f.get('type'), default=determine_ext(src))
                if ext == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        src, video_id, 'mp4', m3u8_id='hls', fatal=False)
                elif ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        src, video_id, mpd_id='dash', fatal=False)
                else:
                    tbr = self._search_regex(fr'_(\d{{3,}})\.{ext}', src, 'tbr', default=None)
                    formats.append({
                        'url': src,
                        'ext': ext,
                        'format_id': join_nonempty('http', ext, tbr),
                        'tbr': int_or_none(tbr),
                        # quality metadata of http formats may be incorrect
                        'quality': -10,
                    })
                    continue
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

            yield {
                **traverse_obj(item, {
                    'title': ('title', {str}),
                    'thumbnail': ('poster', {url_or_none}),
                    'timestamp': ('dvr_begin_at', {int_or_none}),
                    'upload_date': ('date_air', {unified_strdate}),
                    'duration': ('duration', {int_or_none}),
                }),
                'id': video_id,
                'formats': formats,
                'subtitles': subtitles,
            }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)
        playlist_url = urllib.parse.urljoin(url, self._html_search_regex(
            r'data-playlist-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
            webpage, 'playlist url', group='url'))

        item_ids = traverse_obj(parse_qs(playlist_url), 'video_id', 'videos_ids[]', 'news_ids[]')
        items = traverse_obj(
            self._download_json(playlist_url, display_id),
            lambda _, v: v['uid'] and (str(v['uid']) in item_ids if item_ids else True))

        return self.playlist_result(
            self._entries(items), display_id, self._og_search_title(webpage, default=None),
            thumbnail=self._og_search_thumbnail(webpage, default=None))


class FirstTVLiveIE(InfoExtractor):
    IE_NAME = '1tv:live'
    IE_DESC = 'Первый канал (прямой эфир)'
    _VALID_URL = r'https?://(?:www\.)?1tv\.ru/live'

    _TESTS = [{
        'url': 'https://www.1tv.ru/live',
        'info_dict': {
            'id': 'live',
            'ext': 'mp4',
            'title': r're:ПЕРВЫЙ КАНАЛ ПРЯМОЙ ЭФИР СМОТРЕТЬ ОНЛАЙН \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'livestream'},
    }]

    def _real_extract(self, url):
        display_id = 'live'
        webpage = self._download_webpage(url, display_id, fatal=False)

        streams_list = self._download_json('https://stream.1tv.ru/api/playlist/1tvch-v1_as_array.json', display_id)
        mpd_url = traverse_obj(streams_list, ('mpd', ..., {url_or_none}, any, {require('mpd url')}))
        # FFmpeg needs to be passed -re to not seek past live window. This is handled by core
        formats, _ = self._extract_mpd_formats_and_subtitles(mpd_url, display_id, mpd_id='dash')

        return {
            'id': display_id,
            'title': self._html_extract_title(webpage),
            'formats': formats,
            'is_live': True,
        }

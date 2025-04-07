import itertools

from .common import InfoExtractor
from ..utils import (
    bug_reports_message,
    determine_ext,
    int_or_none,
    lowercase_escape,
    parse_qs,
    qualities,
    try_get,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class YandexVideoIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            yandex\.ru(?:/(?:portal/(?:video|efir)|efir))?/?\?.*?stream_id=|
                            frontend\.vh\.yandex\.ru/player/
                        )
                        (?P<id>(?:[\da-f]{32}|[\w-]{12}))
                    '''
    _TESTS = [{
        'url': 'https://yandex.ru/portal/video?stream_id=4dbb36ec4e0526d58f9f2dc8f0ecf374',
        'info_dict': {
            'id': '4dbb36ec4e0526d58f9f2dc8f0ecf374',
            'ext': 'mp4',
            'title': 'Русский Вудсток - главный рок-фест в истории СССР / вДудь',
            'description': 'md5:7d6b8d4bc4a3b9a56499916c1ea5b5fa',
            'thumbnail': r're:^https?://',
            'timestamp': 1549972939,
            'duration': 5575,
            'age_limit': 18,
            'upload_date': '20190212',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://yandex.ru/portal/efir?stream_id=4dbb262b4fe5cf15a215de4f34eee34d&from=morda',
        'only_matching': True,
    }, {
        'url': 'https://yandex.ru/?stream_id=4dbb262b4fe5cf15a215de4f34eee34d',
        'only_matching': True,
    }, {
        'url': 'https://frontend.vh.yandex.ru/player/4dbb262b4fe5cf15a215de4f34eee34d?from=morda',
        'only_matching': True,
    }, {
        # vod-episode, series episode
        'url': 'https://yandex.ru/portal/video?stream_id=45b11db6e4b68797919c93751a938cee',
        'only_matching': True,
    }, {
        # episode, sports
        'url': 'https://yandex.ru/?stream_channel=1538487871&stream_id=4132a07f71fb0396be93d74b3477131d',
        'only_matching': True,
    }, {
        # DASH with DRM
        'url': 'https://yandex.ru/portal/video?from=morda&stream_id=485a92d94518d73a9d0ff778e13505f8',
        'only_matching': True,
    }, {
        'url': 'https://yandex.ru/efir?stream_active=watching&stream_id=v7a2dZ-v5mSI&from_block=efir_newtab',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player = try_get((self._download_json(
            'https://frontend.vh.yandex.ru/graphql', video_id, data=('''{
  player(content_id: "%s") {
    computed_title
    content_url
    description
    dislikes
    duration
    likes
    program_title
    release_date
    release_date_ut
    release_year
    restriction_age
    season
    start_time
    streams
    thumbnail
    title
    views_count
  }
}''' % video_id).encode(), fatal=False)), lambda x: x['player']['content'])  # noqa: UP031
        if not player or player.get('error'):
            player = self._download_json(
                f'https://frontend.vh.yandex.ru/v23/player/{video_id}.json',
                video_id, query={
                    'stream_options': 'hires',
                    'disable_trackings': 1,
                })
        content = player['content']

        title = content.get('title') or content['computed_title']

        formats = []
        streams = content.get('streams') or []
        streams.append({'url': content.get('content_url')})
        for stream in streams:
            content_url = url_or_none(stream.get('url'))
            if not content_url:
                continue
            ext = determine_ext(content_url)
            if ext == 'ismc':
                continue
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    content_url, video_id, 'mp4',
                    'm3u8_native', m3u8_id='hls', fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    content_url, video_id, mpd_id='dash', fatal=False))
            else:
                formats.append({'url': content_url})

        timestamp = (int_or_none(content.get('release_date'))
                     or int_or_none(content.get('release_date_ut'))
                     or int_or_none(content.get('start_time')))
        season = content.get('season') or {}

        return {
            'id': video_id,
            'title': title,
            'description': content.get('description'),
            'thumbnail': content.get('thumbnail'),
            'timestamp': timestamp,
            'duration': int_or_none(content.get('duration')),
            'series': content.get('program_title'),
            'age_limit': int_or_none(content.get('restriction_age')),
            'view_count': int_or_none(content.get('views_count')),
            'like_count': int_or_none(content.get('likes')),
            'dislike_count': int_or_none(content.get('dislikes')),
            'season_number': int_or_none(season.get('season_number')),
            'season_id': season.get('id'),
            'release_year': int_or_none(content.get('release_year')),
            'formats': formats,
        }


class YandexVideoPreviewIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?yandex\.\w{2,3}(?:\.(?:am|ge|il|tr))?/video/preview(?:/?\?.*?filmId=|/)(?P<id>\d+)'
    _TESTS = [{  # Odnoklassniki
        'url': 'https://yandex.ru/video/preview/?filmId=10682852472978372885&text=summer',
        'info_dict': {
            'id': '1352565459459',
            'ext': 'mp4',
            'like_count': int,
            'upload_date': '20191202',
            'age_limit': 0,
            'duration': 196,
            'thumbnail': 'https://i.mycdn.me/videoPreview?id=544866765315&type=37&idx=13&tkn=TY5qjLYZHxpmcnK8U2LgzYkgmaU&fn=external_8',
            'uploader_id': '481054701571',
            'title': 'LOFT - summer, summer, summer HD',
            'uploader': 'АРТЁМ КУДРОВ',
        },
    }, {  # youtube
        'url': 'https://yandex.ru/video/preview/?filmId=4479424425337895262&source=main_redirect&text=видео&utm_source=main_stripe_big',
        'only_matching': True,
    }, {  # YandexVideo
        'url': 'https://yandex.ru/video/preview/5275069442094787341',
        'only_matching': True,
    }, {  # youtube
        'url': 'https://yandex.ru/video/preview/?filmId=16658118429797832897&from=tabbar&p=1&text=%D0%BF%D1%80%D0%BE%D1%81%D0%BC%D0%BE%D1%82%D1%80+%D1%84%D1%80%D0%B0%D0%B3%D0%BC%D0%B5%D0%BD%D1%82%D0%B0+%D0%BC%D0%B0%D0%BB%D0%B5%D0%BD%D1%8C%D0%BA%D0%B8%D0%B9+%D0%BF%D1%80%D0%B8%D0%BD%D1%86+%D0%BC%D1%8B+%D0%B2+%D0%BE%D1%82%D0%B2%D0%B5%D1%82%D0%B5+%D0%B7%D0%B0+%D1%82%D0%B5%D1%85+%D0%BA%D0%BE%D0%B3%D0%BE+%D0%BF%D1%80%D0%B8%D1%80%D1%83%D1%87%D0%B8%D0%BB%D0%B8',
        'only_matching': True,
    }, {  # Odnoklassniki
        'url': 'https://yandex.ru/video/preview/?text=Francis%20Lai%20-%20Le%20Bon%20Et%20Les%20MC)chants&path=wizard&parent-reqid=1643208087979310-1481782809207673478-sas3-0931-2f9-sas-l7-balancer-8080-BAL-9380&wiz_type=vital&filmId=12508152936505397283',
        'only_matching': True,
    }, {  # Odnoklassniki
        'url': 'https://yandex.com/video/preview/?text=dossier%2051%20film%201978&path=yandex_search&parent-reqid=1664361087754492-8727541069609384458-sas2-0340-sas-l7-balancer-8080-BAL-8045&noreask=1&from_type=vast&filmId=5794987234584444632',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data_raw = self._search_regex(r'window.Ya.__inline_params__\s*=\s*JSON.parse\(\'([^"]+?\\u0022video\\u0022:[^"]+?})\'\);', webpage, 'data_raw')
        data_json = self._parse_json(data_raw, video_id, transform_source=lowercase_escape)
        return self.url_result(data_json['video']['url'])


class ZenYandexBaseIE(InfoExtractor):
    def _fetch_ssr_data(self, url, video_id):
        webpage = self._download_webpage(url, video_id)
        redirect = self._search_json(
            r'(?:var|let|const)\s+it\s*=', webpage, 'redirect', video_id, default={}).get('retpath')
        if redirect:
            video_id = self._match_id(redirect)
            webpage = self._download_webpage(redirect, video_id, note='Redirecting')
        return video_id, self._search_json(
            r'(?:var|let|const)\s+_params\s*=\s*\(', webpage, 'metadata', video_id,
            contains_pattern=r'{["\']ssrData.+}')['ssrData']


class ZenYandexIE(ZenYandexBaseIE):
    IE_NAME = 'dzen.ru'
    IE_DESC = 'Дзен (dzen) formerly Яндекс.Дзен (Yandex Zen)'
    _VALID_URL = r'https?://(zen\.yandex|dzen)\.ru(?:/video)?/(media|watch)/(?:(?:id/[^/]+/|[^/]+/)(?:[a-z0-9-]+)-)?(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://zen.yandex.ru/media/id/606fd806cc13cb3c58c05cf5/vot-eto-focus-dedy-morozy-na-gidrociklah-60c7c443da18892ebfe85ed7',
        'info_dict': {
            'id': '60c7c443da18892ebfe85ed7',
            'ext': 'mp4',
            'title': 'ВОТ ЭТО Focus. Деды Морозы на гидроциклах',
            'description': 'md5:8684912f6086f298f8078d4af0e8a600',
            'thumbnail': 're:^https://avatars.dzeninfra.ru/',
            'uploader': 'AcademeG DailyStream',
        },
        'params': {
            'skip_download': 'm3u8',
            'format': 'bestvideo',
        },
        'skip': 'The page does not exist',
    }, {
        'url': 'https://dzen.ru/media/id/606fd806cc13cb3c58c05cf5/vot-eto-focus-dedy-morozy-na-gidrociklah-60c7c443da18892ebfe85ed7',
        'info_dict': {
            'id': '60c7c443da18892ebfe85ed7',
            'ext': 'mp4',
            'title': 'ВОТ ЭТО Focus. Деды Морозы на гидроциклах',
            'description': 'md5:8684912f6086f298f8078d4af0e8a600',
            'thumbnail': r're:^https://avatars\.dzeninfra\.ru/',
            'uploader': 'AcademeG DailyStream',
            'upload_date': '20191111',
            'timestamp': 1573465585,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'The page does not exist',
    }, {
        'url': 'https://zen.yandex.ru/video/watch/6002240ff8b1af50bb2da5e3',
        'info_dict': {
            'id': '6002240ff8b1af50bb2da5e3',
            'ext': 'mp4',
            'title': 'Извержение вулкана из спичек: зрелищный опыт',
            'description': 'md5:053ad3c61b5596d510c9a199dc8ee633',
            'thumbnail': r're:^https://avatars\.dzeninfra\.ru/',
            'uploader': 'TechInsider',
            'timestamp': 1611378221,
            'upload_date': '20210123',
            'view_count': int,
            'duration': 243,
            'tags': ['опыт', 'эксперимент', 'огонь'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://dzen.ru/video/watch/6002240ff8b1af50bb2da5e3',
        'info_dict': {
            'id': '6002240ff8b1af50bb2da5e3',
            'ext': 'mp4',
            'title': 'Извержение вулкана из спичек: зрелищный опыт',
            'description': 'md5:053ad3c61b5596d510c9a199dc8ee633',
            'thumbnail': 're:^https://avatars.dzeninfra.ru/',
            'uploader': 'TechInsider',
            'upload_date': '20210123',
            'timestamp': 1611378221,
            'view_count': int,
            'duration': 243,
            'tags': ['опыт', 'эксперимент', 'огонь'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://zen.yandex.ru/media/id/606fd806cc13cb3c58c05cf5/novyi-samsung-fold-3-moskvich-barahlit-612f93b7f8d48e7e945792a2?from=channel&rid=2286618386.482.1630817595976.42360',
        'only_matching': True,
    }, {
        'url': 'https://dzen.ru/media/id/606fd806cc13cb3c58c05cf5/novyi-samsung-fold-3-moskvich-barahlit-612f93b7f8d48e7e945792a2?from=channel&rid=2286618386.482.1630817595976.42360',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_id, ssr_data = self._fetch_ssr_data(url, video_id)
        video_data = ssr_data['videoMetaResponse']

        formats, subtitles = [], {}
        quality = qualities(('4', '0', '1', '2', '3', '5', '6', '7'))
        # Deduplicate stream URLs. The "dzen_dash" query parameter is present in some URLs but can be omitted
        stream_urls = set(traverse_obj(video_data, (
            'video', ('id', ('streams', ...), ('mp4Streams', ..., 'url'), ('oneVideoStreams', ..., 'url')),
            {url_or_none}, {update_url_query(query={'dzen_dash': []})})))
        for s_url in stream_urls:
            ext = determine_ext(s_url)
            content_type = traverse_obj(parse_qs(s_url), ('ct', 0))
            if ext == 'mpd' or content_type == '6':
                fmts, subs = self._extract_mpd_formats_and_subtitles(s_url, video_id, mpd_id='dash', fatal=False)
            elif ext == 'm3u8' or content_type == '8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(s_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            elif content_type == '0':
                format_type = traverse_obj(parse_qs(s_url), ('type', 0))
                formats.append({
                    'url': s_url,
                    'format_id': format_type,
                    'ext': 'mp4',
                    'quality': quality(format_type),
                })
                continue
            else:
                self.report_warning(f'Unsupported stream URL: {s_url}{bug_reports_message()}')
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('video', 'duration', {int_or_none}),
                'view_count': ('video', 'views', {int_or_none}),
                'timestamp': ('publicationDate', {int_or_none}),
                'tags': ('tags', ..., {str}),
                'uploader': ('source', 'title', {str}),
            }),
        }


class ZenYandexChannelIE(ZenYandexBaseIE):
    IE_NAME = 'dzen.ru:channel'
    _VALID_URL = r'https?://(zen\.yandex|dzen)\.ru/(?!media|video)(?:id/)?(?P<id>[a-z0-9-_]+)'
    _TESTS = [{
        'url': 'https://zen.yandex.ru/tok_media',
        'info_dict': {
            'id': 'tok_media',
            'title': 'СПЕКТР',
            'description': 'md5:a9e5b3c247b7fe29fd21371a428bcf56',
        },
        'playlist_mincount': 169,
        'skip': 'The page does not exist',
    }, {
        'url': 'https://dzen.ru/tok_media',
        'info_dict': {
            'id': 'tok_media',
            'title': 'СПЕКТР',
            'description': 'md5:a9e5b3c247b7fe29fd21371a428bcf56',
        },
        'playlist_mincount': 169,
        'skip': 'The page does not exist',
    }, {
        'url': 'https://zen.yandex.ru/id/606fd806cc13cb3c58c05cf5',
        'info_dict': {
            'id': '606fd806cc13cb3c58c05cf5',
            'description': 'md5:517b7c97d8ca92e940f5af65448fd928',
            'title': 'AcademeG DailyStream',
        },
        'playlist_mincount': 657,
    }, {
        # Test that the playlist extractor finishes extracting when the
        # channel has less than one page
        'url': 'https://zen.yandex.ru/jony_me',
        'info_dict': {
            'id': 'jony_me',
            'description': 'md5:7c30d11dc005faba8826feae99da3113',
            'title': 'JONY',
        },
        'playlist_count': 18,
    }, {
        # Test that the playlist extractor finishes extracting when the
        # channel has more than one page of entries
        'url': 'https://zen.yandex.ru/tatyanareva',
        'info_dict': {
            'id': 'tatyanareva',
            'description': 'md5:92e56fa730a932ca2483ba5c2186ad96',
            'title': 'Татьяна Рева',
        },
        'playlist_mincount': 46,
    }, {
        'url': 'https://dzen.ru/id/606fd806cc13cb3c58c05cf5',
        'info_dict': {
            'id': '606fd806cc13cb3c58c05cf5',
            'title': 'AcademeG DailyStream',
            'description': 'md5:517b7c97d8ca92e940f5af65448fd928',
        },
        'playlist_mincount': 657,
    }]

    def _entries(self, feed_data, channel_id):
        next_page_id = None
        for page in itertools.count(1):
            for item in traverse_obj(feed_data, (
                (None, ('items', lambda _, v: v['tab'] in ('shorts', 'longs'))),
                'items', lambda _, v: url_or_none(v['link']),
            )):
                yield self.url_result(item['link'], ZenYandexIE, item.get('id'), title=item.get('title'))

            more = traverse_obj(feed_data, ('more', 'link', {url_or_none}))
            current_page_id = next_page_id
            next_page_id = traverse_obj(parse_qs(more), ('next_page_id', -1))
            if not all((more, next_page_id, next_page_id != current_page_id)):
                break

            feed_data = self._download_json(more, channel_id, note=f'Downloading Page {page}')

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel_id, ssr_data = self._fetch_ssr_data(url, channel_id)
        channel_data = ssr_data['exportResponse']

        return self.playlist_result(
            self._entries(channel_data['feedData'], channel_id),
            channel_id, **traverse_obj(channel_data, ('channel', 'source', {
                'title': ('title', {str}),
                'description': ('description', {str}),
            })))

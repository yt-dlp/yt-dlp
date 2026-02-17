import itertools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    determine_ext,
    extract_attributes,
    int_or_none,
    js_to_json,
    parse_iso8601,
    strip_or_none,
    traverse_obj,
    unescapeHTML,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class PolskieRadioBaseIE(InfoExtractor):
    def _extract_webpage_player_entries(self, webpage, playlist_id, base_data):
        media_urls = set()

        for data_media in re.findall(r'<[^>]+data-media="?({[^>]+})"?', webpage):
            media = self._parse_json(data_media, playlist_id, transform_source=unescapeHTML, fatal=False)
            if not media.get('file') or not media.get('desc'):
                continue
            media_url = self._proto_relative_url(media['file'])
            if media_url in media_urls:
                continue
            media_urls.add(media_url)
            entry = base_data.copy()
            entry.update({
                'id': str(media['id']),
                'url': media_url,
                'duration': int_or_none(media.get('length')),
                'vcodec': 'none' if media.get('provider') == 'audio' else None,
            })
            entry_title = urllib.parse.unquote(media['desc'])
            if entry_title:
                entry['title'] = entry_title
            yield entry


class PolskieRadioLegacyIE(PolskieRadioBaseIE):
    # legacy sites
    IE_NAME = 'polskieradio:legacy'
    _VALID_URL = r'https?://(?:www\.)?polskieradio(?:24)?\.pl/\d+/\d+/[Aa]rtykul/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.polskieradio.pl/8/2382/Artykul/2534482,Zagarysci-Poezja-jak-spoiwo',
        'info_dict': {
            'id': '2534482',
            'title': 'Żagaryści. Poezja jak spoiwo',
            'description': 'md5:f18d95d5dcba747a09b635e21a4c0695',
        },
        'playlist': [{
            'md5': 'd07559829f61d5a93a75755987ded760',
            'info_dict': {
                'id': '2516679',
                'ext': 'mp3',
                'title': 'md5:c6e1234e0b747ad883cb91b7ad06b98c',
                'timestamp': 1592654400,
                'upload_date': '20200620',
                'duration': 1430,
                'thumbnail': r're:^https?://static\.prsa\.pl/images/.*\.jpg$',
            },
        }],
    }, {
        # PR4 audition - other frontend
        'url': 'https://www.polskieradio.pl/10/6071/Artykul/2610977,Poglos-29-pazdziernika-godz-2301',
        'info_dict': {
            'id': '2610977',
            'ext': 'mp3',
            'title': 'Pogłos 29 października godz. 23:01',
        },
    }, {
        'url': 'https://polskieradio24.pl/130/4503/Artykul/2621876,Narusza-nasza-suwerennosc-Publicysci-o-uzaleznieniu-funduszy-UE-od-praworzadnosci',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, playlist_id)
        if PolskieRadioIE.suitable(urlh.url):
            return self.url_result(urlh.url, PolskieRadioIE, playlist_id)

        content = self._search_regex(
            r'(?s)<div[^>]+class="\s*this-article\s*"[^>]*>(.+?)<div[^>]+class="tags"[^>]*>',
            webpage, 'content', default=None)

        timestamp = unified_timestamp(self._html_search_regex(
            r'(?s)<span[^>]+id="datetime2"[^>]*>(.+?)</span>',
            webpage, 'timestamp', default=None))

        thumbnail_url = self._og_search_thumbnail(webpage, default=None)

        title = self._og_search_title(webpage).strip()

        description = strip_or_none(self._og_search_description(webpage, default=None))
        description = description.replace('\xa0', ' ') if description is not None else None

        if not content:
            return {
                'id': playlist_id,
                'url': self._proto_relative_url(
                    self._search_regex(
                        r"source:\s*'(//static\.prsa\.pl/[^']+)'",
                        webpage, 'audition record url')),
                'title': title,
                'description': description,
                'timestamp': timestamp,
                'thumbnail': thumbnail_url,
            }

        entries = self._extract_webpage_player_entries(content, playlist_id, {
            'title': title,
            'timestamp': timestamp,
            'thumbnail': thumbnail_url,
        })

        return self.playlist_result(entries, playlist_id, title, description)


class PolskieRadioIE(PolskieRadioBaseIE):
    # new next.js sites
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:polskieradio(?:24)?|radiokierowcow)\.pl/artykul/(?P<id>\d+)'
    _TESTS = [{
        # articleData, attachments
        'url': 'https://jedynka.polskieradio.pl/artykul/1587943',
        'info_dict': {
            'id': '1587943',
            'title': 'Prof. Andrzej Nowak: o historii nie da się myśleć beznamiętnie',
            'description': 'md5:12f954edbf3120c5e7075e17bf9fc5c5',
        },
        'playlist': [{
            'md5': '2984ee6ce9046d91fc233bc1a864a09a',
            'info_dict': {
                'id': '7a85d429-5356-4def-a347-925e4ae7406b',
                'ext': 'mp3',
                'title': 'md5:d4623290d4ac983bf924061c75c23a0d',
            },
        }],
    }, {
        # post, legacy html players
        'url': 'https://trojka.polskieradio.pl/artykul/2589163,Czy-wciaz-otrzymujemy-zdjecia-z-sond-Voyager',
        'info_dict': {
            'id': '2589163',
            'title': 'Czy wciąż otrzymujemy zdjęcia z sond Voyager?',
            'description': 'md5:cf1a7f348d63a2db9c0d7a63d1669473',
        },
        'playlist': [{
            'info_dict': {
                'id': '2577880',
                'ext': 'mp3',
                'title': 'md5:a57d10a0c02abd34dd675cb33707ad5a',
                'duration': 321,
            },
        }],
    }, {
        # data, legacy
        'url': 'https://radiokierowcow.pl/artykul/2694529',
        'info_dict': {
            'id': '2694529',
            'title': 'Zielona fala reliktem przeszłości?',
            'description': 'md5:f20a9a7ed9cb58916c54add94eae3bc0',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://trojka.polskieradio.pl/artykul/1632955',
        'only_matching': True,
    }, {
        # with mp4 video
        'url': 'https://trojka.polskieradio.pl/artykul/1634903',
        'only_matching': True,
    }, {
        'url': 'https://jedynka.polskieradio.pl/artykul/3042436,Polityka-wschodnia-ojca-i-syna-Wladyslawa-Lokietka-i-Kazimierza-Wielkiego',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        article_data = traverse_obj(
            self._search_nextjs_data(webpage, playlist_id), (
                'props', 'pageProps', (('data', 'articleData'), 'post', 'data')), get_all=False)

        title = strip_or_none(article_data['title'])

        description = strip_or_none(article_data.get('lead'))

        entries = [{
            'url': entry['file'],
            'ext': determine_ext(entry.get('fileName')),
            'id': self._search_regex(
                r'([a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12})', entry['file'], 'entry id'),
            'title': strip_or_none(entry.get('description')) or title,
        } for entry in article_data.get('attachments') or () if entry.get('fileType') in ('Audio', )]

        if not entries:
            # some legacy articles have no json attachments, but players in body
            entries = self._extract_webpage_player_entries(article_data['content'], playlist_id, {
                'title': title,
            })

        return self.playlist_result(entries, playlist_id, title, description)


class PolskieRadioAuditionIE(InfoExtractor):
    # new next.js sites
    IE_NAME = 'polskieradio:audition'
    _VALID_URL = r'https?://(?:[^/]+\.)?polskieradio\.pl/audycj[ae]/(?P<id>\d+)'
    _TESTS = [{
        # articles, PR1
        'url': 'https://jedynka.polskieradio.pl/audycje/5102',
        'info_dict': {
            'id': '5102',
            'title': 'Historia żywa',
            'thumbnail': r're:https://static\.prsa\.pl/images/.+',
        },
        'playlist_mincount': 38,
    }, {
        # episodes, PR1
        'url': 'https://jedynka.polskieradio.pl/audycje/4417',
        'info_dict': {
            'id': '4417',
            'title': '100 sekund polszczyzny',
            'thumbnail': r're:https://static\.prsa\.pl/images/.+',
        },
        'playlist_mincount': 400,
    }]

    def _call_lp3(self, path, query, video_id, note):
        return self._download_json(
            f'https://lp3test.polskieradio.pl/{path}', video_id, note,
            query=query, headers={'x-api-key': '9bf6c5a2-a7d0-4980-9ed7-a3f7291f2a81'})

    def _entries(self, playlist_id, has_episodes, has_articles):
        for i in itertools.count(0) if has_episodes else []:
            page = self._call_lp3(
                'AudioArticle/GetListByCategoryId', {
                    'categoryId': playlist_id,
                    'PageSize': 10,
                    'skip': i,
                    'format': 400,
                }, playlist_id, f'Downloading episode list page {i + 1}')
            if not traverse_obj(page, 'data'):
                break
            for episode in page['data']:
                yield {
                    'id': str(episode['id']),
                    'url': episode['file'],
                    'title': episode.get('title'),
                    'duration': int_or_none(episode.get('duration')),
                    'timestamp': parse_iso8601(episode.get('datePublic')),
                }

        for i in itertools.count(0) if has_articles else []:
            page = self._call_lp3(
                'Article/GetListByCategoryId', {
                    'categoryId': playlist_id,
                    'PageSize': 9,
                    'skip': i,
                    'format': 400,
                }, playlist_id, f'Downloading article list page {i + 1}')
            if not traverse_obj(page, 'data'):
                break
            for article in page['data']:
                yield {
                    '_type': 'url_transparent',
                    'id': str(article['id']),
                    'url': article['url'],
                    'title': article.get('shortTitle'),
                    'description': traverse_obj(article, ('description', 'lead')),
                    'timestamp': parse_iso8601(article.get('datePublic')),
                }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        page_props = traverse_obj(
            self._search_nextjs_data(self._download_webpage(url, playlist_id), playlist_id),
            ('props', 'pageProps', ('data', None)), get_all=False)

        has_episodes = bool(traverse_obj(page_props, 'episodes', 'audios'))
        has_articles = bool(traverse_obj(page_props, 'articles'))

        return self.playlist_result(
            self._entries(playlist_id, has_episodes, has_articles), playlist_id,
            title=traverse_obj(page_props, ('details', 'name')),
            description=traverse_obj(page_props, ('details', 'description', 'lead')),
            thumbnail=traverse_obj(page_props, ('details', 'photo')))


class PolskieRadioCategoryIE(InfoExtractor):
    # legacy sites
    IE_NAME = 'polskieradio:category'
    _VALID_URL = r'https?://(?:www\.)?polskieradio\.pl/(?:\d+(?:,[^/]+)?/|[^/]+/Tag)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.polskieradio.pl/37,RedakcjaKatolicka/4143,Kierunek-Krakow',
        'info_dict': {
            'id': '4143',
            'title': 'Kierunek Kraków - Redakcja Programów Katolickich',
        },
        'playlist_mincount': 61,
    }, {
        'url': 'https://www.polskieradio.pl/10,czworka/214,muzyka',
        'info_dict': {
            'id': '214',
            'title': 'Muzyka - Czwórka',
        },
        'playlist_mincount': 61,
    }, {
        # billennium tabs
        'url': 'https://www.polskieradio.pl/8/2385',
        'info_dict': {
            'id': '2385',
            'title': 'Droga przez mąkę - Dwójka',
        },
        'playlist_mincount': 90,
    }, {
        'url': 'https://www.polskieradio.pl/10/4930',
        'info_dict': {
            'id': '4930',
            'title': 'Teraz K-pop! - Czwórka',
        },
        'playlist_mincount': 392,
    }, {
        # post back pages, audio content directly without articles
        'url': 'https://www.polskieradio.pl/8,dwojka/7376,nowa-mowa',
        'info_dict': {
            'id': '7376',
            'title': 'Nowa mowa - Dwójka',
        },
        'playlist_mincount': 244,
    }, {
        'url': 'https://www.polskieradio.pl/Krzysztof-Dziuba/Tag175458',
        'info_dict': {
            'id': '175458',
            'title': 'Krzysztof Dziuba w PolskieRadio.pl',
        },
        'playlist_mincount': 330,
    }, {
        'url': 'https://www.polskieradio.pl/8,Dwojka/196,Publicystyka',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if PolskieRadioLegacyIE.suitable(url) else super().suitable(url)

    def _entries(self, url, page, category_id):
        content = page
        is_billennium_tabs = 'onclick="TB_LoadTab(' in page
        is_post_back = 'onclick="__doPostBack(' in page
        pagination = page if is_billennium_tabs else None
        for page_num in itertools.count(2):
            for a_entry, entry_id in re.findall(
                    r'(?s)<article[^>]+>.*?(<a[^>]+href=["\'](?:(?:https?)?://[^/]+)?/\d+/\d+/Artykul/(\d+)[^>]+>).*?</article>',
                    content):
                entry = extract_attributes(a_entry)
                if entry.get('href'):
                    yield self.url_result(
                        urljoin(url, entry['href']), PolskieRadioLegacyIE, entry_id, entry.get('title'))
            for a_entry in re.findall(r'<span data-media=({[^ ]+})', content):
                yield traverse_obj(self._parse_json(a_entry, category_id), {
                    'url': 'file',
                    'id': 'uid',
                    'duration': 'length',
                    'title': ('title', {urllib.parse.unquote}),
                    'description': ('desc', {urllib.parse.unquote}),
                })
            if is_billennium_tabs:
                params = self._search_json(
                    r'<div[^>]+class=["\']next["\'][^>]*>\s*<a[^>]+onclick=["\']TB_LoadTab\(',
                    pagination, 'next page params', category_id, default=None, close_objects=1,
                    contains_pattern='.+', transform_source=lambda x: f'[{js_to_json(unescapeHTML(x))}')
                if not params:
                    break
                tab_content = self._download_json(
                    'https://www.polskieradio.pl/CMS/TemplateBoxesManagement/TemplateBoxTabContent.aspx/GetTabContent',
                    category_id, f'Downloading page {page_num}', headers={'content-type': 'application/json'},
                    data=json.dumps(dict(zip((  # noqa: B905
                        'boxInstanceId', 'tabId', 'categoryType', 'sectionId', 'categoryId', 'pagerMode',
                        'subjectIds', 'tagIndexId', 'queryString', 'name', 'openArticlesInParentTemplate',
                        'idSectionFromUrl', 'maxDocumentAge', 'showCategoryForArticle', 'pageNumber',
                    ), params))).encode())['d']
                content, pagination = tab_content['Content'], tab_content.get('PagerContent')
            elif is_post_back:
                target = self._search_regex(
                    r'onclick=(?:["\'])__doPostBack\((?P<q1>["\'])(?P<target>[\w$]+)(?P=q1)\s*,\s*(?P<q2>["\'])Next(?P=q2)',
                    content, 'pagination postback target', group='target', default=None)
                if not target:
                    break
                content = self._download_webpage(
                    url, category_id, f'Downloading page {page_num}',
                    data=urllib.parse.urlencode({
                        **self._hidden_inputs(content),
                        '__EVENTTARGET': target,
                        '__EVENTARGUMENT': 'Next',
                    }).encode())
            else:
                next_url = urljoin(url, self._search_regex(
                    r'<div[^>]+class=["\']next["\'][^>]*>\s*<a[^>]+href=(["\'])(?P<url>(?:(?!\1).)+)\1',
                    content, 'next page url', group='url', default=None))
                if not next_url:
                    break
                content = self._download_webpage(next_url, category_id, f'Downloading page {page_num}')

    def _real_extract(self, url):
        category_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, category_id)
        if PolskieRadioAuditionIE.suitable(urlh.url):
            return self.url_result(urlh.url, PolskieRadioAuditionIE, category_id)
        title = self._og_search_title(webpage)
        return self.playlist_result(
            self._entries(url, webpage, category_id),
            category_id, title)


class PolskieRadioPlayerIE(InfoExtractor):
    IE_NAME = 'polskieradio:player'
    _VALID_URL = r'https?://(?:www\.)?player\.polskieradio\.pl/anteny/(?P<id>[^/]+)'

    _BASE_URL = 'https://player.polskieradio.pl'
    _PLAYER_URL = 'https://player.polskieradio.pl/main.bundle.js'
    _STATIONS_API_URL = 'https://apipr.polskieradio.pl/api/stacje'

    _TESTS = [{
        'url': 'https://player.polskieradio.pl/anteny/trojka',
        'info_dict': {
            'id': '3',
            'ext': 'm4a',
            'title': r're:^Trójka \d{4}-(?:1[0-2]|0\d)-[0-3]\d [0-2]\d:[0-6]\d$',
            'display_id': 'trojka',
            'live_status': 'is_live',
            'thumbnail': 'https://player.polskieradio.pl/images/trojka-color-logo.png',
        },
        'params': {
            'format': 'bestaudio',
            'skip_download': 'endless stream',
        },
    }]

    def _get_channel_list(self, channel_url='no_channel'):
        player_code = self._download_webpage(
            self._PLAYER_URL, channel_url,
            note='Downloading js player')
        channel_list = js_to_json(self._search_regex(
            r';var n="anteny",o=(\[.+?\])},', player_code, 'channel list'))
        return self._parse_json(channel_list, channel_url)

    def _real_extract(self, url):
        channel_url = self._match_id(url)
        channel_list = self._get_channel_list(channel_url)

        channel = next((c for c in channel_list if c.get('url') == channel_url), None)

        if not channel:
            raise ExtractorError('Channel not found')

        station_list = self._download_json(self._STATIONS_API_URL, channel_url,
                                           note='Downloading stream url list',
                                           headers={
                                               'Accept': 'application/json',
                                               'Referer': url,
                                               'Origin': self._BASE_URL,
                                           })
        station = next((s for s in station_list
                        if s.get('Name') == (channel.get('streamName') or channel.get('name'))), None)
        if not station:
            raise ExtractorError('Station not found even though we extracted channel')

        formats = []
        for stream_url in station['Streams']:
            stream_url = self._proto_relative_url(stream_url)
            stream_url = urllib.parse.urlparse(stream_url)._replace(scheme='https').geturl()
            if stream_url.endswith('/playlist.m3u8'):
                formats.extend(self._extract_m3u8_formats(stream_url, channel_url, live=True))

        return {
            'id': str(channel['id']),
            'formats': formats,
            'title': channel.get('name') or channel.get('streamName'),
            'display_id': channel_url,
            'thumbnail': f'{self._BASE_URL}/images/{channel_url}-color-logo.png',
            'is_live': True,
        }


class PolskieRadioPodcastBaseIE(InfoExtractor):
    _API_BASE = 'https://static.prsa.pl'
    _BASE_URL = 'https://podcasty.polskieradio.pl'

    def _parse_episode(self, webpage, podcast_id):
        return {
            'id': podcast_id,
            'url': f'{self._API_BASE}/{podcast_id}.mp3',
            'ext': 'mp3',
            'title': self._og_search_title(webpage),
            # `default` is empty to avoid printing bug warning; episodes may not have descriptions
            'description': self._og_search_description(webpage, default=''),
            'thumbnail': url_or_none(self._og_search_thumbnail(webpage)),
            'series': self._html_search_meta('author', webpage),
            'episode': self._og_search_title(webpage),
        }


class PolskieRadioPodcastListIE(PolskieRadioPodcastBaseIE):
    IE_NAME = 'polskieradio:podcast:list'
    _VALID_URL = r'https?://(?:www\.)?podcasty\.polskieradio\.pl(?:/.+)+,(?P<id>\d+)(?=(\?page=\d+)?$)'
    _TESTS = [{
        'url': 'https://podcasty.polskieradio.pl/podcast/szalenstwa-panny-ewy-czii-kornel-makuszynski,642?page=2',
        'info_dict': {
            'id': '642',
            'title': 'Szaleństwa Panny Ewy cz.II - Kornel Makuszyński',
            'description': '"Szaleństwa panny Ewy" - także dzięki wspaniałemu serialowi telewizyjnemu z 1985 r. - to jedna z najsłynniejszych powieści Makuszyńskiego. Powstawała w czasie II wojny światowej, jako remedium na mrok i okrucieństwa niemieckiej okupacji. Ukazała się dopiero w 1957 r. Tytułowa bohaterka to 16-letnia Ewa Tyszowska, córka znanego profesora mikrobiologii, która na swojej drodze spotyka mnóstwo beznadziejnych spraw, do ich rozwiązania przyczynia się dzięki swojemu urokowi i sprytowi.',
            'thumbnail': 'https://static.prsa.pl/images/b7d258e6-07b4-413a-b7fe-276cc663ce55.jpg',
            'series': 'Szaleństwa Panny Ewy cz.II - Kornel Makuszyński',
        },
        'playlist_mincount': 18,
    }, {
        'url': 'https://podcasty.polskieradio.pl/dla-zagranicy-west/podcasty/fakebusters-with-polish-radio-,519',
        'info_dict': {
            'id': '519',
            'title': 'Fakebusters with Polish Radio ',
            'description': 'Fakebusters with Polish Radio is our weekly program focusing on disinformation and cybersecurity in the modern world. Tune in to learn how to debunk fake news, explore the history of media propaganda, and discover strategies to combat Internet noise.',
            'thumbnail': 'https://static.prsa.pl/images/35eb56d6-a151-4c22-a084-ed0dab47540f.jpg',
            'series': 'Fakebusters with Polish Radio ',
        },
        'playlist_mincount': 45,
    }, {
        'url': 'https://www.podcasty.polskieradio.pl/jedynka/podcasty/polityka-w-skrocie-jacka-czarneckiego,706',
        'info_dict': {
            'id': '706',
            'title': 'Polityka w skrócie Jacka Czarneckiego',
            'description': 'Polska, świat, polityka. Bieżące komentarze o tym, co najważniejsze. W poniedziałki, środy i piątki zawsze po godz. 8.40. Zaprasza Jacek Czarnecki.',
            'thumbnail': 'https://static.prsa.pl/images/eeb4cff9-8cf5-48c5-b525-6dbad75b441d.jpg',
            'series': 'Polityka w skrócie Jacka Czarneckiego',
        },
        'playlist_mincount': 16,
    }, {
        'url': 'https://www.podcasty.polskieradio.pl/trojka/audycje/cos-mi-swita,10648',
        'info_dict': {
            'id': '10648',
            'title': 'Coś Mi Świta - Trójka - Program Trzeci Polskiego Radia',
            'description': '.',
            'thumbnail': 'https://static.prsa.pl/images/b25aa587-40eb-4ae9-b742-88731683721e.file?format=700',
            'series': 'Coś Mi Świta - Trójka - Program Trzeci Polskiego Radia',
        },
        'playlist_mincount': 160,
    }]
    _PAGE_SIZE = 10

    def _real_extract(self, url):
        def get_page_episodes(page_num):
            page_data = self._download_webpage(page_url := f'{url}?page={page_num + 1}', page_url)
            episode_urls = re.findall(r'(?<=<a href=\")(?P<url>/[^<>]+odcinek/[^<>]+,(?P<id>[a-f\d]{8}(?:-[a-f\d]{4}){4}[a-f\d]{8}))(?=\">)', page_data)
            yield from (self._parse_episode(self._download_webpage(parsed_url := f'{self._BASE_URL}{ep_url}', parsed_url), ep_id)
                        for ep_url, ep_id in episode_urls)

        list_id = self._match_id(url)
        url = url.split('?page=')[0]
        webpage = self._download_webpage(url, url)
        return {
            '_type': 'playlist',
            'id': list_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=''),
            'thumbnail': url_or_none(self._og_search_thumbnail(webpage)),
            'series': self._og_search_title(webpage),
            'entries': OnDemandPagedList(
                get_page_episodes, self._PAGE_SIZE),
        }


class PolskieRadioPodcastIE(PolskieRadioPodcastBaseIE):
    IE_NAME = 'polskieradio:podcast'
    _VALID_URL = r'https?://(?:www\.)?(?:podcasty\.)?polskieradio\.pl/.+,(?P<id>[a-f\d]{8}(?:-[a-f\d]{4}){4}[a-f\d]{8})$'
    _TESTS = [{
        'url': 'https://podcasty.polskieradio.pl/dwojka/audycje/natura-poezji,11604/odcinek/swiat-po-porannym-deszczu-i-granice-jabloni,0cdee2d7-b022-4564-9bc1-a9a02c48516a',
        'info_dict': {
            'id': '0cdee2d7-b022-4564-9bc1-a9a02c48516a',
            'title': 'Natura poezji - Dwojka - Program Drugi Polskiego Radia - Świat po porannym deszczu i granice jabłoni',
            'description': 'Natura poezji - Dzika, wielojęzyczna, zmysłowa, niezrozumiała - jaka jest natura poezji? W cyklu pod takim właśnie tytułem poszukamy jej wspólnie z Julią Fiedorczuk - poetką, tłumaczką, proziczką, eseistką i profesorką literaturoznawstwa . Podstawowym tropem w tej wyprawie będą czytane z bliska wiersze, w których odbija się świat przyrody. Przyjrzymy się dopływom do polszczyzny, mającym źródła w literaturze anglosaskiej - sięgając między innymi po tomy Gary\'ego Snydera, Forresta Grandera i Alice Oswald, ale z też z kultur antycznych i rdzennych.\r\nZapraszam co drugą niedzielę o 14.00 - Katarzyna Hagmajer-Kwiatek',
            'ext': 'mp3',
            'thumbnail': 'https://static.prsa.pl/images/df79c8a9-849e-406c-a19c-bbcf05f66a87.file?format=700',
            'series': 'Natura poezji',
            'episode': 'Natura poezji - Dwojka - Program Drugi Polskiego Radia - Świat po porannym deszczu i granice jabłoni',
        },
    }, {
        'url': 'https://podcasty.polskieradio.pl/podcast/teatr-polskiego-radia-dramat,464/odcinek/kazdy-czlowiek-jest-wymyslony-malgorzaty-sikorskiej-miszczuk-w-rezyserii-katarzyny-leckiej,6bc0e4d8-68a0-4350-a5ff-4370f374f3ab',
        'info_dict': {
            'id': '6bc0e4d8-68a0-4350-a5ff-4370f374f3ab',
            'title': '"Każdy człowiek jest wymyślony" Małgorzaty Sikorskiej-Miszczuk w reżyserii Katarzyny Łęckiej',
            'description': 'Adam i Ida mają po czterdzieści kilka lat. Kiedyś byli parą. Po ich związku zostały wspomnienia, kilka niezabliźnionych ran i... suka rasy Akita, która do dziś przypomina im o tym, co było. Choć od rozstania minęło już sporo czasu, oboje wciąż noszą w sobie przekonanie, że to, co ich łączyło, było czymś wyjątkowym. Teraz spotykają się przypadkiem. Adam, lekarz, wykonuje testy na Covid. Ida, chora, trafia właśnie do niego. Od tej chwili zaczynają rozmawiać codziennie. Oficjalnie, jako pacjentka i jej lekarz rodzinny. Nieoficjalnie, jako ludzie, którzy kiedyś byli sobie bardzo bliscy. I może wciąż są. Reżyseria: Katarzyna Łęcka. Reżyseria dźwięku: Andrzej Brzoska. Muzyka: Szymon Burnos. Kierownictwo produkcji: Beata Jankowska. Obsada: Grażyna Wolszczak i Bartosz Opania',
            'ext': 'mp3',
            'thumbnail': 'https://static.prsa.pl/images/3cc73086-57f6-46c8-9ebb-714834723a35.jpg',
            'series': 'Teatr Polskiego Radia: Najnowsze produkcje',
            'episode': '"Każdy człowiek jest wymyślony" Małgorzaty Sikorskiej-Miszczuk w reżyserii Katarzyny Łęckiej',
        },
    }, {
        'url': 'https://www.polskieradio.pl/dwojka/podcasty/rachunek-mysli,380/odcinek/losy-marka-aureliusza-gdy-mysliciel-zostaje-cesarzem-gosc-dr-hab-krzysztof-lapinski,04676fde-48e9-48ab-bb84-68a37e568898',
        'info_dict': {
            'id': '04676fde-48e9-48ab-bb84-68a37e568898',
            'title': 'Losy Marka Aureliusza: gdy myśliciel zostaje cesarzem. Gość: dr hab. Krzysztof Łapiński',
            'description': 'Choć kochał los, ten obszedł się z nim wyjątkowo okrutnie. Sprawił, że został cesarzem. Czy był także filozofem? Co rodzi się z mariażu władzy i stoicyzmu?',
            'ext': 'mp3',
            'thumbnail': 'https://static.prsa.pl/images/f63945f3-1a74-4461-8c54-15e6807f51d3.jpg',
            'series': 'Rachunek myśli',
            'episode': 'Losy Marka Aureliusza: gdy myśliciel zostaje cesarzem. Gość: dr hab. Krzysztof Łapiński',
        },
    }, {
        'url': 'https://www.polskieradio.pl/dwojka/audycje/rachunek-mysli,5534/odcinek/losy-marka-aureliusza-gdy-mysliciel-zostaje-cesarzem-gosc-dr-hab-krzysztof-lapinski,04676fde-48e9-48ab-bb84-68a37e568898',
        'info_dict': {
            'id': '04676fde-48e9-48ab-bb84-68a37e568898',
            'title': 'Rachunek myśli - Dwojka - Program Drugi Polskiego Radia - Losy Marka Aureliusza: gdy myśliciel zostaje cesarzem. Gość: dr hab. Krzysztof Łapiński',
            'description': 'Rachunek myśli - Wieczorne spotkanie z filozofią i psychoanalizą.',
            'ext': 'mp3',
            'thumbnail': 'https://static.prsa.pl/images/c1235b65-154e-4603-bd32-103a74d9c99d.file?format=700',
            'series': 'Rachunek myśli',
            'episode': 'Rachunek myśli - Dwojka - Program Drugi Polskiego Radia - Losy Marka Aureliusza: gdy myśliciel zostaje cesarzem. Gość: dr hab. Krzysztof Łapiński',
        },
    }]

    def _real_extract(self, url):
        podcast_id = self._match_id(url)
        return self._parse_episode(self._download_webpage(url, url), podcast_id)

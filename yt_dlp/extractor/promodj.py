import datetime
import functools
import re
import urllib.parse

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    OnDemandPagedList,
    clean_html,
    extract_attributes,
    ExtractorError,
    get_element_by_class,
    get_elements_html_by_class,
    int_or_none,
    parse_duration,
    traverse_obj,
    urlencode_postdata,
    url_or_none,
)

# promodj.com

# Playlist types:
# /:login/:media_type - default
# /:login/groups/:id/:slug - user defined (groups). Can contain audios and/or videos

# A single media by default is attached to default playlist
# But it can be reattached to a user playlist (group), and no longer appears in the default one

# User pages
# /:login - all non-empty playlists
# /:login/music - all non-empty playlists with at least one audio (shows 10 audios per playlist max)
# /:login/video - all non-empty playlists with at least one video (shows 10 videos per playlist max)
# /:login/pages - a list of user pages
# /:login/:page_name - a single user page
# /:login/blog - a list of blog posts
# /:login/blog/:id/:slug - a single blog post

# If default playlist is empty, it redirects to the user's page
# Pages and blog posts can contain: audios, videos, youtube videos

# Tracks and remixes can be paid. See /shop page


class PromoDJBaseIE(InfoExtractor):
    _MEDIA_TYPES = [
        'tracks',
        'remixes',
        'mixes',
        'promos',
        'lives',
        'podcasts',
        'radioshows',
        'tools',
        'realtones',  # doesn't appear on the site menu but still exists
        'acapellas',  # redirects to /tools, creates default playlist
        'samples',    # redirects to /tools, doesn't create default playlist
        'videos',
    ]
    _PAGES = ['featured', 'shop', *_MEDIA_TYPES]

    _BASE_URL_RE = r'https?://(?:www\.)?promodj\.com'
    _MEDIA_TYPES_RE = '|'.join(_MEDIA_TYPES)
    _NOT_PAGE_RE = '|'.join(['radio', *_PAGES])
    _LOGIN_RE = rf'(?:(?!{_NOT_PAGE_RE}).)[\w.-]+'

    def _set_url_page(self, url, page):
        parsed_url = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed_url.query)
        qs['page'] = page
        return parsed_url._replace(query=urllib.parse.urlencode(qs, doseq=True)).geturl()

    def _fetch_page(self, url, allowed_media_cats, playlist_id, page):
        page_url = self._set_url_page(url, page + 1)
        html = self._download_webpage(page_url, f'{playlist_id}-page-{page + 1}')
        if self._get_current_page(html) != page + 1:
            return

        for a in get_elements_html_by_class('player_standard_tool__play', html):
            url = traverse_obj(extract_attributes(a), ('href', {url_or_none}))
            if not url:
                continue
            url = url.replace('?play=1', '')
            is_video = '/videos/' in url
            if is_video and 'video' in allowed_media_cats or not is_video and 'music' in allowed_media_cats:
                yield self.url_result(url, PromoDJIE)

    def _parse_playlist_links(self, html):
        PLAYLISTS_RE = r'<a class=\"files_group_title\" href=\"([^\"]+)\">'
        DEFAULT_VIDEO_PLAYLIST_RE = r'<h5><a href=\"https://promodj\.com/([\w.-]+)/video\">Видео</a></h5>'

        playlist_links = []

        for playlist_url in re.findall(PLAYLISTS_RE, html):
            playlist_links.append(playlist_url)

        login = self._search_regex(
            DEFAULT_VIDEO_PLAYLIST_RE, html, 'video playlist url', None)
        if login:
            playlist_links.append(f'https://promodj.com/{login}/videos')

        return playlist_links

    def _parse_page_content(self, html):
        for id in re.findall(r'CORE\.Player\(\'[^\']+\', \'(?:standalone|cover)\.big\', (\d+),', html):
            yield self.url_result(f'https://promodj.com/embed/{id}/big', PromoDJEmbedIE, id)

        for iframe_url in re.findall(r'<iframe[^>]+src=\"([^\"]+)\"', html):
            if YoutubeIE.suitable(iframe_url):
                yield self.url_result(iframe_url, YoutubeIE)

    def _get_playlist_page_size(self, url):
        is_default_playlist = '/groups/' not in url
        return 30 if is_default_playlist else 20

    def _get_current_page(self, html):
        return int(clean_html(get_element_by_class('NavigatorCurrentPage', html)) or '1')

    def _fetch_media_data(self, ids, video_id):
        data = {}
        for i, id in enumerate(ids):
            data[f'multi[{i}][method]'] = 'players/config'
            data[f'multi[{i}][params][kind]'] = 'standalone.big'
            data[f'multi[{i}][params][fileID]'] = id
        return self._download_json(
            'https://promodj.com/api/multi.json', video_id, data=urlencode_postdata(data),
            headers={'Content-Type': 'application/x-www-form-urlencoded'})


class PromoDJPageIE(PromoDJBaseIE):
    _PAGES_RE = '|'.join(PromoDJBaseIE._PAGES)

    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<id>{_PAGES_RE})'
    _TESTS = [{
        'url': 'https://promodj.com/featured',
        'only_matching': True,
    }, {
        # second page
        'url': 'https://promodj.com/featured/rap?download=1&page=2',
        'only_matching': True,
    }, {
        # filtered
        'url': 'https://promodj.com/remixes?top=1',
        'only_matching': True,
    }, {
        # with genre
        'url': 'https://promodj.com/tracks/hip_hop',
        'only_matching': True,
    }, {
        # with search
        'url': 'https://promodj.com/mixes?kind=mixes&styleID=&searchfor=dance',
        'only_matching': True,
    }, {
        # no download button
        'url': 'https://promodj.com/shop',
        'only_matching': True,
    }]

    _PAGE_SIZE = 20

    def _real_extract(self, url):
        page_type = self._match_id(url)
        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(self._fetch_page, url, ['music', 'video'], page_type),
                self._PAGE_SIZE),
            playlist_id=page_type)


class PromoDJUserIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})$'
    _TESTS = [{
        'url': 'https://promodj.com/djperetse',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/dj-trojan',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        login = self._match_valid_url(url).group('login')
        html = self._download_webpage(url, login)

        def entries():
            for playlist_url in self._parse_playlist_links(html):
                yield self.url_result(playlist_url, PromoDJPlaylistIE)

        return self.playlist_result(entries(), playlist_id=login)


class PromoDJUserMediaIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<type>music|video)$'
    _TESTS = [{
        'url': 'https://promodj.com/feel/music',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/djmikis/video',
        'only_matching': True,
    }, {
        # a user without any videos
        'url': 'https://promodj.com/worobyev/video',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        login, type = self._match_valid_url(url).groups()
        page_id = f'{login}-{type}'
        html = self._download_webpage(url, page_id)

        def entries():
            for playlist_url in self._parse_playlist_links(html):
                ie = PromoDJMusicPlaylistIE if type == 'music' else PromoDJVideoPlaylistIE
                yield self.url_result(playlist_url, ie)

        return self.playlist_result(entries(), playlist_id=page_id)


class PromoDJUserPagesIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<type>pages|blog)$'
    _TESTS = [{
        'url': 'https://promodj.com/djperetse/pages',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/golub/blog',
        'only_matching': True,
    }]

    _PAGE_SIZE = 10

    def _parse_pages(self, url, playlist_id):
        html = self._download_webpage(url, playlist_id)
        content_html = get_element_by_class('dj_universal', get_element_by_class('dj_bblock', html))
        for page_url, page_title in re.findall(r'<a href=\"([^\"]+)\">([^<]+)</a>', content_html):
            yield self.url_result(page_url, PromoDJUserPageIE, video_title=page_title)

    def _fetch_blogs_page(self, url, playlist_id, page):
        page_url = self._set_url_page(url, page + 1)
        html = self._download_webpage(page_url, f'{playlist_id}-page-{page + 1}')
        if self._get_current_page(html) != page + 1:
            return

        for a in get_elements_html_by_class('post_title_moderated', html):
            if url := traverse_obj(extract_attributes(a), ('href', {url_or_none})):
                yield self.url_result(url, PromoDJBlogPageIE)

    def _real_extract(self, url):
        login, type = self._match_valid_url(url).groups()
        playlist_id = f'{login}-{type}'
        if type == 'pages':
            entries = self._parse_pages(url, playlist_id)
        elif type == 'blog':
            entries = OnDemandPagedList(
                functools.partial(self._fetch_blogs_page, url, playlist_id),
                self._PAGE_SIZE)
        return self.playlist_result(entries, playlist_id)


class PromoDJUserPageIE(PromoDJBaseIE):
    _USER_PAGES = [
        'pages',
        'music',
        'video',
        'foto',
        'avisha',
        'blog',
        'feedback',
        'contact',
        *PromoDJBaseIE._MEDIA_TYPES,
    ]
    _NOT_USER_PAGE_RE = '|'.join(_USER_PAGES)
    _USER_PAGE_RE = rf'(?:(?!{_NOT_USER_PAGE_RE}).)[\w-]+'

    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<slug>{_USER_PAGE_RE})$'
    _TESTS = [{
        'url': 'https://promodj.com/djperetse/MaxMixes',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        login, slug = self._match_valid_url(url).groups()
        page_id = f'{login}-{slug}'
        html = self._download_webpage(url, page_id)
        content_html = get_element_by_class('perfect', html)
        return self.playlist_result(
            self._parse_page_content(content_html), playlist_id=page_id)


class PromoDJBlogPageIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/blog/(?P<id>\d+)(?:/(?P<slug>\w+))?'
    _TESTS = [{
        # with small and big audio players and youtube video
        'url': 'https://promodj.com/golub/blog/1163895/DJ_Andrey_Golubev_To_Depeche_Mode_with_love_part_9_special_dj_edits_mix',
        'only_matching': True,
    }, {
        # with audio and video
        'url': 'https://promodj.com/svetmusic/blog/1101958/SVET_I_Like_It_Extra_Sound_Recordings',
        'only_matching': True,
    }, {
        # without any media
        'url': 'https://promodj.com/svetmusic/blog/915878/DJ_SVET_pobeditel_konkursa_Burn_City_Sound',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        login, id, slug = self._match_valid_url(url).groups()
        page_id = f'{login}-blog-{id}-{slug}'
        html = self._download_webpage(url, page_id)
        content_html = get_element_by_class('post_body', html)
        return self.playlist_result(
            self._parse_page_content(content_html), playlist_id=page_id)


class PromoDJPlaylistIE(PromoDJBaseIE):
    _VALID_URL = [
        rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<type>{PromoDJBaseIE._MEDIA_TYPES_RE})$',
        rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<type>groups)/(?P<id>\d+)(?:/(?P<slug>\w+))?',
    ]
    _TESTS = [{
        # default playlist: tracks (audio)
        'url': 'https://promodj.com/gluk/tracks',
        'only_matching': True,
    }, {
        # default playlist: video
        'url': 'https://promodj.com/djperetse/videos',
        'only_matching': True,
    }, {
        # user playlist: audio
        'url': 'https://promodj.com/fonarev/groups/608158/Digital_Emotions_Night',
        'only_matching': True,
    }, {
        # two pages
        'url': 'https://promodj.com/lavrov/groups/677132/VINYL',
        'only_matching': True,
    }, {
        # user playlist: video
        'url': 'https://promodj.com/deeplecture/groups/672782/LAROCCA_TV',
        'only_matching': True,
    }, {
        # user playlist: audio and video
        'url': 'https://promodj.com/djperetse/groups/637358/Russkie_treki',
        'only_matching': True,
    }, {
        # 900+ items
        'url': 'https://promodj.com/fonarev/groups/17350/Digital_Emotions_Podcast',
        'only_matching': True,
    }]

    _ALLOWED_MEDIA_CATS = ['music', 'video']

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        login = match.group('login')
        type = match.group('type')
        playlist_id = f'{login}-{type}' if len(match.groups()) == 2 else f'{login}-{type}-{match.group("id")}'
        page_size = self._get_playlist_page_size(url)

        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, url, self._ALLOWED_MEDIA_CATS, playlist_id),
            page_size)
        return self.playlist_result(entries, playlist_id=playlist_id)


class PromoDJMusicPlaylistIE(PromoDJPlaylistIE):
    _ALLOWED_MEDIA_CATS = ['music']


class PromoDJVideoPlaylistIE(PromoDJPlaylistIE):
    _ALLOWED_MEDIA_CATS = ['video']


class PromoDJIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/{PromoDJBaseIE._LOGIN_RE}/(?P<type>{PromoDJBaseIE._MEDIA_TYPES_RE})/(?P<id>\d+)(?:/\w+)?',
    _TESTS = [{
        'url': 'https://promodj.com/antonpavlovsky/remixes/6259208/David_Usher_Black_Black_Heart_Anton_Pavlovsky_Cover',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/j-factory/samples/7560171/Amedici_BW1_Intro',
        'only_matching': True,
    }, {
        # music: no download links in html
        'url': 'https://promodj.com/gluk/tracks/4713922/DJ_Glyuk_Folk_ing_DJ_Steven_Smile_Remix_2005',
        'only_matching': True,
    }, {
        # video: no download link in html
        'url': 'https://promodj.com/psywanderer/videos/7559147/Chu_de_sa',
        'only_matching': True,
    }, {
        # no player
        'url': 'https://promodj.com/gluk/tracks/420310/IMpulse_Zakat',
        'only_matching': True,
    }, {
        # without slug
        'url': 'https://promodj.com/djlykov/tracks/7551590',
        'only_matching': True,
    }, {
        # lossless
        'url': 'https://promodj.com/modi-glu/tracks/6081339/Modi_Glyu_Anabel',
        'only_matching': True,
    }, {
        # paid audio
        'url': 'https://promodj.com/boyko/tracks/1435682/Dj_Boyko_Katy_Queen_Nad_Oblakami',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/sergeyfedotov306/videos/7457627/V_Matrice_Sboy',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/djperetse/videos/5868236/Fatalist_Project_feat_DJ_Peretse_Den_pobedi_Videoklip',
        'only_matching': True,
    }, {
        # avi
        'url': 'https://promodj.com/djmikis/videos/5311597/Mikis_Live_SDJ_Show',
        'only_matching': True,
    }, {
        # asf
        'url': 'https://promodj.com/gigsiphonic/videos/7559341/Gigsiphonic_PODCAST_309_Extended_video_version',
        'only_matching': True,
    }, {
        # not valid html
        'url': 'https://promodj.com/martin.sehnal/videos/7555841/Martin_Sehnal_CII_33_Plus_CII_32_Clothes_on_the_peg_2_020_2_024_02_01th',
        'only_matching': True,
    }]

    _IS_PAID_RE = r'<b>Цена:</b>'
    # examples: MP3, 320 Кбит | MP4, 20157 Кбит | WAV, 1412 Кбит | AVI, 1731 Кбит | ASF, 6905 Кбит
    _FORMATS_RE = r'<a\s+href=\"(?P<url>[^\"]+)\">\s*(?P<format>\w+), (?P<bitrate>\d+) Кбит\s*</a>'
    _VIEW_COUNT_RE = r'<b>(?:Прослушиваний|Просмотров):</b>\s*(\d+)'
    # examples: 0:21 | 1:07 | 74:38
    _DURATION_RE = r'<b>Продолжительность:</b>\s*(\d+:\d{2})'
    # examples: 818.4 Кб | 12.9 Мб | 4 Гб | 1.76 Гб | 1001.5 Мб
    _SIZE_RE = r'<b>Размер:</b>\s*(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>Кб|Мб|Гб)'
    # examples: сегодня 2:55 | вчера 23:17 | 1 июня 2016 3:46
    _TIMESTAMP_RE = r'<b>Публикация:</b>\s*(?P<day>вчера|сегодня|\d{1,2})(?: (?P<month>[а-я]+) (?P<year>\d{4}))?\s*(?P<hours>\d{1,2}):(?P<minutes>\d{2})'
    _TAGS_RE = r'<span\s+class=\"styles\">([^\n]+)</span>'

    # https://regex101.com/r/2ZkUmW/1
    _MUSIC_DATA_REGEX = r'({\"no_preroll\":false,\"seekAny\":true,\"sources\":[^\n]+)\);'
    # https://regex101.com/r/b9utBf/1
    _VIDEO_DATA_REGEX = r'({\"video\":true,\"config\":[^\n]+)\);'

    def _parse_ru_date(self, raw_date):
        RU_MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        day, month, year, hours, minutes = raw_date
        if day == 'сегодня':
            d = datetime.date.today()
            day = d.day
            month = d.month
            year = d.year
        elif day == 'вчера':
            d = datetime.date.today() - datetime.timedelta(days=1)
            day = d.day
            month = d.month
            year = d.year
        else:
            day = int(day)
            month = RU_MONTHS.index(month) + 1
            year = int(year)
        return datetime.datetime(year, month, day, int(hours), int(minutes)).timestamp()

    def _parse_ru_size(self, raw_size):
        RU_SIZE_UNITS = ['Б', 'Кб', 'Мб', 'Гб']
        size, size_unit = raw_size
        return int(float(size) * pow(1024, RU_SIZE_UNITS.index(size_unit)))

    def _parse_media(self, html, id, type):
        # html can be invalid
        try:
            meta_html = get_elements_html_by_class('dj_universal', html)[1]
        except Exception:
            meta_html = html

        formats_from_html = re.findall(self._FORMATS_RE, meta_html)
        has_formats = len(formats_from_html) != 0
        is_paid = re.search(self._IS_PAID_RE, meta_html)

        if not has_formats and type == 'videos':
            media_data_raw = self._search_regex(self._VIDEO_DATA_REGEX, html, 'media data')
            media_data = self._parse_json(media_data_raw, id)
            video_config = self._parse_json(media_data['config'], id)
            video = traverse_obj(video_config, ('playlist', 'item', 0))
            formats = [{
                'url': traverse_obj(video, ('play', '@url', {url_or_none})),
            }]
        elif not has_formats or is_paid:
            media_data_raw = self._search_regex(self._MUSIC_DATA_REGEX, html, 'media data')
            media_data = self._parse_json(media_data_raw, id)
            formats = [{
                'url': source.get('URL'),
                'size': int_or_none(source.get('size')),
            } for source in traverse_obj(media_data, ('sources')) if url_or_none(source.get('URL'))]
        else:
            formats = [{
                'url': url,
                'format': format.lower(),
                'tbr': int(bitrate),
            } for url, format, bitrate in formats_from_html if url_or_none(url)]
            # size field describes best quality. best quality always comes first
            formats[0]['size'] = self._parse_ru_size(re.findall(self._SIZE_RE, meta_html)[0])

        return {
            'id': id,
            'title': clean_html(get_element_by_class('file_title', html)),
            'formats': formats,
            'view_count': int_or_none(self._search_regex(self._VIEW_COUNT_RE, meta_html, 'view_count', default=None)),
            'duration': parse_duration(self._search_regex(self._DURATION_RE, meta_html, 'duration')),
            'timestamp': self._parse_ru_date(re.findall(self._TIMESTAMP_RE, meta_html)[0]),
            'tags': self._html_search_regex(self._TAGS_RE, meta_html, 'tags').split(', '),
        }

    def _real_extract(self, url):
        type, id = self._match_valid_url(url).groups()
        html = self._download_webpage(url, id)
        return self._parse_media(html, id, type)


class PromoDJEmbedIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/embed/(?P<id>\d+)/(?P<type>cover|big)'
    _TESTS = [{
        'url': 'https://promodj.com/embed/7555440/cover',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/embed/7540163/big',
        'only_matching': True,
    }, {
        # video (can be only big)
        'url': 'https://promodj.com/embed/3922099/big',
        'only_matching': True,
    }, {
        # blocked
        'url': 'https://promodj.com/embed/5586967/big',
        'only_matching': True,
    }, {
        # deleted
        'url': 'https://promodj.com/embed/5606804/big',
        'only_matching': True,
    }]

    def _get_full_url(self, media_data, id):
        if player_error := media_data.get('player_error'):
            raise ExtractorError(player_error, expected=True)

        if media_data.get('video'):
            video_config = self._parse_json(media_data['config'], id)
            video = traverse_obj(video_config, ('playlist', 'item', 0))
            return traverse_obj(video, ('title', '@ico_url'))
        else:
            return media_data.get('titleURL')

    def _real_extract(self, url):
        id = self._match_id(url)
        url = self._get_full_url(self._fetch_media_data([id], id)[0], id)
        return self.url_result(url, PromoDJIE, id)


class PromoDJShortIE(PromoDJBaseIE):
    _VALID_URL = r'https://pdj.cc/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://pdj.cc/fv8VD',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        html = self._download_webpage(url, id)
        return self.url_result(self._og_search_url(html), PromoDJIE, id)


class PromoDJRadioIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/radio#(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://promodj.com/radio#dubstep',
        'only_matching': True,
    }, {
        'url': 'https://promodj.com/radio#oldschool',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        return {
            'id': id,
            'formats': [{
                'url': f'https://radio.promodj.com/{id}-192',
                'abr': 192,
            }],
            'is_live': True,
        }

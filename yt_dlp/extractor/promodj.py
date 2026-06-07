import datetime
import functools
import re
import urllib.parse

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    dict_get,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    get_elements_html_by_class,
    int_or_none,
    js_to_json,
    merge_dicts,
    parse_duration,
    str_or_none,
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
    _NOT_LOGIN_LIST = '|'.join(['radio', 'embed', *_PAGES])
    _LOGIN_RE = rf'(?!(?:{_NOT_LOGIN_LIST})(?:/|$))[\w.-]+'

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

        for a in get_elements_html_by_class('player_standard_tool__comments', html):
            url = traverse_obj(extract_attributes(a), ('href', {url_or_none}))
            if not url:
                continue
            url = url.replace('#comments', '')
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

    def _get_current_page(self, html):
        return int(clean_html(get_element_by_class('NavigatorCurrentPage', html)) or '1')

    def _fetch_media_data(self, id):
        data = {
            'multi[0][method]': 'players/config',
            'multi[0][params][kind]': 'cover.big',
            'multi[0][params][fileID]': id,
        }
        return self._download_json(
            'https://promodj.com/api/multi.json', id, data=urlencode_postdata(data),
            headers={'Content-Type': 'application/x-www-form-urlencoded'})[0]

    def _parse_media_data(self, media_data, id):
        if player_error := media_data.get('player_error'):
            raise ExtractorError(player_error, expected=True)

        if media_data.get('video'):
            video = traverse_obj(
                self._parse_json(media_data['config'], id), ('playlist', 'item', 0))
            formats = [{
                'format_id': 'web',
                'url': traverse_obj(video, ('play', '@url')).replace('?returnurl=1', ''),
            }]
            return {
                'id': id,
                'formats': formats,
                **traverse_obj(video, {
                    'title': ('title', 'line', 1, 0, '$', {str_or_none}),
                    'webpage_url': ('title', '@ico_url', {url_or_none}),
                    'duration': ('play', '@duration', {int_or_none}),
                    'thumbnail': ('background', '@url', {url_or_none}),
                    'channel': ('title', 'line', 0, 0, '$', {str_or_none}),
                    'channel_url': ('title', 'line', 0, 0, '@url', {url_or_none}),
                })
            }

        formats = [{
            'format_id': 'lossy',
            'url': traverse_obj(source, ('URL', {url_or_none})),
            'size': traverse_obj(source, ('size', {int_or_none})),
            'acodec': 'mp3',
            'vcodec': 'none',
        } for source in traverse_obj(media_data, ('sources'))]
        thumbnails = [{
            'url': url,
        } for url in traverse_obj(media_data, ('coverURL', ('600', '1200', '2000'))) if url_or_none(url)]
        return {
            'id': id,
            'title': clean_html(dict_get(media_data, ('title_html', 'title'))),
            'formats': formats,
            'thumbnails': thumbnails,
            'webpage_url': traverse_obj(media_data, ('titleURL', {url_or_none}))
        }


class PromoDJPageIE(PromoDJBaseIE):
    _PAGES_LIST = '|'.join(PromoDJBaseIE._PAGES)

    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<id>{_PAGES_LIST})'
    _TESTS = [{
        'url': 'https://promodj.com/featured',
        'info_dict': {
            'id': 'featured',
        },
        'playlist_count': 40,
        'params': {
            'playlistend': 40,
        },
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
        # shop
        'url': 'https://promodj.com/shop',
        'info_dict': {
            'id': 'shop',
        },
        'playlist_count': 20,
        'params': {
            'playlistend': 20,
        },
    }, {
        # videos
        'url': 'https://promodj.com/videos',
        'info_dict': {
            'id': 'videos',
        },
        'playlist_count': 20,
        'params': {
            'playlistend': 20,
        },
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
        'url': 'https://promodj.com/dj-trojan',
        'info_dict': {
            'id': 'dj-trojan',
        },
        'playlist_mincount': 89,
    }, {
        # with default video playlist
        'url': 'https://promodj.com/djperetse',
        'info_dict': {
            'id': 'djperetse',
        },
        'playlist_mincount': 15,
    }, {
        # without any playlists
        'url': 'https://promodj.com/slim96',
        'info_dict': {
            'id': 'slim96',
        },
        'playlist_count': 0,
    }, {
        # login starts with page name
        'url': 'https://promodj.com/radio.remix',
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
        'url': 'https://promodj.com/worobyev/music',
        'info_dict': {
            'id': 'worobyev-music',
        },
        'playlist_mincount': 11,
    }, {
        # no music
        'url': 'https://promodj.com/xsev71/music',
        'info_dict': {
            'id': 'xsev71-music',
        },
        'playlist_count': 0,
    }, {
        'url': 'https://promodj.com/cosmonaut/video',
        'info_dict': {
            'id': 'cosmonaut-video',
        },
        'playlist_mincount': 2,
    }, {
        # no video
        'url': 'https://promodj.com/worobyev/video',
        'info_dict': {
            'id': 'worobyev-video',
        },
        'playlist_count': 0,
    }, {
        # login starts with page name
        'url': 'https://promodj.com/radio.remix/music',
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
        'info_dict': {
            'id': 'djperetse-pages',
        },
        'playlist_count': 10,
    }, {
        # no pages
        'url': 'https://promodj.com/djlosev/pages',
        'info_dict': {
            'id': 'djlosev-pages',
        },
        'playlist_count': 0,
    }, {
        'url': 'https://promodj.com/ivanroudyk/blog',
        'info_dict': {
            'id': 'ivanroudyk-blog',
        },
        'playlist_mincount': 37,
    }, {
        # no blog
        'url': 'https://promodj.com/worobyev/blog',
        'info_dict': {
            'id': 'worobyev-blog',
        },
        'playlist_count': 0,
    }]

    _PAGE_SIZE = 10

    def _parse_pages(self, url, playlist_id):
        html = self._download_webpage(url, playlist_id)
        content_html = get_element_by_class('dj_content ', html)
        if pages_html := get_element_by_class('dj_universal', content_html):
            for page_url, page_title in re.findall(r'<a href=\"([^\"]+)\">([^<]+)</a>', pages_html):
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
    _USER_PATHS = [
        'pages',
        'music',
        'video',
        'foto',
        'avisha',
        'blog',
        'feedback',
        'contact',
        'uenno',
        *PromoDJBaseIE._MEDIA_TYPES,
    ]
    _NOT_USER_PAGE_LIST = '|'.join(_USER_PATHS)

    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<slug>(?!(?:{_NOT_USER_PAGE_LIST})$)[\w-]+$)'
    _TESTS = [{
        'url': 'https://promodj.com/djperetse/MaxMixes',
        'info_dict': {
            'id': 'djperetse-MaxMixes',
        },
        'playlist_count': 5,
    }, {
        # user page starts with media type (not a real link)
        'url': 'https://promodj.com/djperetse/remixes-best',
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
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/blog/(?P<id>\d+)(?:/\w+)?'
    _TESTS = [{
        # with small and big audio players and youtube video
        'url': 'https://promodj.com/golub/blog/1163895/DJ_Andrey_Golubev_To_Depeche_Mode_with_love_part_9_special_dj_edits_mix',
        'info_dict': {
            'id': 'golub-blog-1163895',
        },
        'playlist_count': 13,
    }, {
        # with audio and video
        'url': 'https://promodj.com/svetmusic/blog/1101958/SVET_I_Like_It_Extra_Sound_Recordings',
        'info_dict': {
            'id': 'svetmusic-blog-1101958',
        },
        'playlist_count': 5,
    }, {
        # without any media
        'url': 'https://promodj.com/svetmusic/blog/915878/DJ_SVET_pobeditel_konkursa_Burn_City_Sound',
        'info_dict': {
            'id': 'svetmusic-blog-915878',
        },
        'playlist_count': 0,
    }, {
        # with deleted and blocked music
        'url': 'https://promodj.com/djperetse/blog/1048739/DJ_Peretse_i_Coca_Cola_obyavlyayut_MEGAMIX_BATTLE_2015',
        'info_dict': {
            'id': 'djperetse-blog-1048739',
        },
        'playlist_count': 29,
    }]

    def _real_extract(self, url):
        login, id = self._match_valid_url(url).groups()
        page_id = f'{login}-blog-{id}'
        html = self._download_webpage(url, page_id)
        content_html = get_element_by_class('post_body', html)
        return self.playlist_result(
            self._parse_page_content(content_html), playlist_id=page_id)


class PromoDJPlaylistIE(PromoDJBaseIE):
    _PLAYLIST_TYPES_LIST = '|'.join(['uenno', *PromoDJBaseIE._MEDIA_TYPES])

    _VALID_URL = [
        rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<type>{_PLAYLIST_TYPES_LIST})$',
        rf'{PromoDJBaseIE._BASE_URL_RE}/(?P<login>{PromoDJBaseIE._LOGIN_RE})/(?P<type>groups)/(?P<id>\d+)(?:/\w+)?',
    ]
    _TESTS = [{
        # default playlist: music (with songs without player)
        'url': 'https://promodj.com/gluk/tracks',
        'info_dict': {
            'id': 'gluk-tracks',
        },
        'playlist_mincount': 29,
    }, {
        # default playlist: with pagination
        'url': 'https://promodj.com/gluk/mixes',
        'info_dict': {
            'id': 'gluk-mixes',
        },
        'playlist_count': 60,
        'params': {
            'playlistend': 60,
        },
    }, {
        # default playlist: video
        'url': 'https://promodj.com/djperetse/videos',
        'info_dict': {
            'id': 'djperetse-videos',
        },
        'playlist_mincount': 6,
    }, {
        # user playlist: audio
        'url': 'https://promodj.com/fonarev/groups/608158/Digital_Emotions_Night',
        'info_dict': {
            'id': 'fonarev-groups-608158',
        },
        'playlist_mincount': 9,
    }, {
        # user playlist: with pagination
        'url': 'https://promodj.com/lavrov/groups/677132/VINYL',
        'info_dict': {
            'id': 'lavrov-groups-677132',
        },
        'playlist_mincount': 33,
    }, {
        # user playlist: video
        'url': 'https://promodj.com/deeplecture/groups/672782/LAROCCA_TV',
        'info_dict': {
            'id': 'deeplecture-groups-672782',
        },
        'playlist_mincount': 4,
    }, {
        # user playlist: audio and video
        'url': 'https://promodj.com/djperetse/groups/637358/Russkie_treki',
        'info_dict': {
            'id': 'djperetse-groups-637358',
        },
        'playlist_mincount': 17,
    }, {
        # 900+ items
        'url': 'https://promodj.com/fonarev/groups/17350/Digital_Emotions_Podcast',
        'only_matching': True,
    }, {
        # user's best music and video
        'url': 'https://promodj.com/djbaribyn/uenno',
        'info_dict': {
            'id': 'djbaribyn-uenno',
        },
        'playlist_count': 15,
        'params': {
            'playlistend': 15,
        }
    }]

    _ALLOWED_MEDIA_CATS = ['music', 'video']

    def _get_page_size(self, type):
        if type == 'uenno':
            return 15
        if type == 'groups':
            return 20
        return 30

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        login = match.group('login')
        type = match.group('type')
        playlist_id = f'{login}-{type}' if len(match.groups()) == 2 else f'{login}-{type}-{match.group("id")}'

        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, url, self._ALLOWED_MEDIA_CATS, playlist_id),
            self._get_page_size(type))
        return self.playlist_result(entries, playlist_id=playlist_id)


class PromoDJMusicPlaylistIE(PromoDJPlaylistIE):
    _VALID_URL = []
    _ALLOWED_MEDIA_CATS = ['music']


class PromoDJVideoPlaylistIE(PromoDJPlaylistIE):
    _VALID_URL = []
    _ALLOWED_MEDIA_CATS = ['video']


class PromoDJIE(PromoDJBaseIE):
    _MEDIA_TYPES_LIST = '|'.join(PromoDJBaseIE._MEDIA_TYPES)

    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/{PromoDJBaseIE._LOGIN_RE}/(?P<type>{_MEDIA_TYPES_LIST})/(?P<id>\d+)(?:/\w+)?',
    _TESTS = [{
        'url': 'https://promodj.com/antonpavlovsky/remixes/6259208/David_Usher_Black_Black_Heart_Anton_Pavlovsky_Cover',
        'info_dict': {
            'id': '6259208',
            'ext': 'mp3',
            'title': 'David Usher - Black Black Heart (Anton Pavlovsky Cover)',
            'tags': ['Lounge', 'Deep House'],
            'upload_date': '20170323',
            'timestamp': 1490258400.0,
            'duration': 173.0,
            'size': 7654604,
            'view_count': int,
        },
    }, {
        # samples type
        'url': 'https://promodj.com/j-factory/samples/7560171/Amedici_BW1_Intro',
        'only_matching': True,
    }, {
        # acapellas type
        'url': 'https://promodj.com/cosmonaut/acapellas/200970/Kosmonavt_golosovoe_ID',
        'only_matching': True,
    }, {
        # realtones type
        'url': 'https://promodj.com/plashstringer/realtones/965489/bomba_bomba',
        'only_matching': True,
    }, {
        # music: no download links in html
        'url': 'https://promodj.com/gluk/tracks/4713922/DJ_Glyuk_Folk_ing_DJ_Steven_Smile_Remix_2005',
        'info_dict': {
            'id': '4713922',
            'ext': 'mp3',
            'title': 'DJ Глюк - Folk\'ing [DJ Steven Smile Remix] (2005)',
            'tags': ['Pumping House', 'Hard House'],
            'upload_date': '20140404',
            'timestamp': 1396605480.0,
            'duration': 299.0,
            'size': 12058624,
            'view_count': int,
        },
    }, {
        # video: no download link in html
        'url': 'https://promodj.com/psywanderer/videos/7559147/Chu_de_sa',
        'info_dict': {
            'id': '7559147',
            'ext': 'mp4',
            'title': 'Чу де са',
            'tags': ['Jazz-Rap', 'Jazzstep'],
            'thumbnail': r're:^https?://',
            'upload_date': '20240210',
            'timestamp': 1707533820.0,
            'duration': 388720,
            'view_count': int,
            'channel': 'PsyWanderer',
            'channel_url': 'https://promodj.com/psywanderer',
        },
    }, {
        # no player (external link)
        'url': 'https://promodj.com/gluk/tracks/420310/IMpulse_Zakat',
        'info_dict': {
            'id': '420310',
            'ext': 'mp3',
            'title': 'IMpulse - Закат',
            'tags': ['House', 'Electro House'],
            'thumbnail': r're:^https?://',
            'upload_date': '20081024',
            'timestamp': 1224846120.0,
            'duration': 133.0,
            'size': 1048576,
            'view_count': int,
        },
        'params': {
            'skip_download': 'Link is broken',
        },
    }, {
        # no player (the link from html is broken but the link from API is ok)
        'url': 'https://promodj.com/scratchin/remixes/374580/Katya_First_Perestala_DJ_Ivan_Scratchin_Mix',
        'only_matching': True,
    }, {
        # without slug
        'url': 'https://promodj.com/djlykov/tracks/7551590',
        'info_dict': {
            'id': '7551590',
            'ext': 'mp3',
            'title': 'Lykov - Benjamin (Radio Edit) [MOUSE-P]',
            'tags': ['Dance Pop', 'Eurodance'],
            'upload_date': '20240122',
            'timestamp': 1705919280.0,
            'duration': 233.0,
            'size': 9332326,
            'view_count': int,
        },
    }, {
        # lossless wav
        'url': 'https://promodj.com/modi-glu/tracks/6081339/Modi_Glyu_Anabel',
        'info_dict': {
            'id': '6081339',
            'ext': 'wav',
            'title': 'Моди Глю " Анабель"',
            'tags': ['Chillout', 'Downtempo'],
            'upload_date': '20161029',
            'timestamp': 1477767780.0,
            'duration': 236.0,
            'size': 42257612,
            'view_count': int,
        },
    }, {
        # lossless flac
        'url': 'https://promodj.com/sashaorbeat/mixes/7422493/Sasha_Orbeat_Pure_Love_3',
        'info_dict': {
            'id': '7422493',
            'ext': 'flac',
            'title': 'Sasha Orbeat — Pure Love 3',
            'tags': ['Lo-Fi', 'Downtempo'],
            'upload_date': '20230213',
            'timestamp': 1676306160.0,
            'duration': 3631.0,
            'size': 685139558,
            'view_count': int,
        },
    }, {
        # paid lossless
        'url': 'https://promodj.com/boyko/tracks/1435682/Dj_Boyko_Katy_Queen_Nad_Oblakami',
        'info_dict': {
            'id': '1435682',
            'ext': 'mp3',
            'title': 'Dj Boyko & Katy Queen - Над Облаками',
            'tags': ['House', 'Trance'],
            'upload_date': '20100404',
            'timestamp': 1270376700.0,
            'duration': 321.0,
            'size': 5128821,
            'view_count': int,
        },
    }, {
        # paid lossy
        'url': 'https://promodj.com/tesla/tracks/342938/Library_Of_Bugs',
        'info_dict': {
            'id': '342938',
            'ext': 'mp3',
            'title': 'Library Of Bugs',
            'tags': ['Minimal Techno', 'Tech House'],
            'upload_date': '20080827',
            'timestamp': 1219841220.0,
            'duration': 64.0,
            'size': 1014431,
            'view_count': int,
        },
    }, {
        # mp4
        'url': 'https://promodj.com/djperetse/videos/5868236/Fatalist_Project_feat_DJ_Peretse_Den_pobedi_Videoklip',
        'info_dict': {
            'id': '5868236',
            'ext': 'mp4',
            'title': 'Fatalist Project feat. DJ Peretse - День победы (Видеоклип)',
            'tags': ['House', 'Progressive House'],
            'thumbnail': r're:^https?://',
            'upload_date': '20160505',
            'timestamp': 1462419720.0,
            'duration': 265045,
            'size': 165465292,
            'view_count': int,
            'channel': 'DJ Peretse',
            'channel_url': 'https://promodj.com/djperetse',
        },
    }, {
        # avi
        'url': 'https://promodj.com/djmikis/videos/5311597/Mikis_Live_SDJ_Show',
        'info_dict': {
            'id': '5311597',
            'ext': 'avi',
            'title': 'Mikis Live @ SDJ Show',
            'tags': ['Club House'],
            'thumbnail': r're:^https?://',
            'upload_date': '20150409',
            'timestamp': 1428579840.0,
            'duration': 1716240,
            'size': 371195904,
            'view_count': int,
            'channel': 'MIKIS',
            'channel_url': 'https://promodj.com/djmikis',
        },
    }, {
        # asf
        'url': 'https://promodj.com/gigsiphonic/videos/7559341/Gigsiphonic_PODCAST_309_Extended_video_version',
        'info_dict': {
            'id': '7559341',
            'ext': 'asf',
            'title': 'Gigsiphonic - PODCAST 309 (Extended video version)',
            'tags': ['Synthwave', 'Synth-Pop'],
            'thumbnail': r're:^https?://',
            'upload_date': '20240210',
            'timestamp': 1707580080.0,
            'duration': 4309200,
            'size': 3715146711,
            'view_count': int,
            'channel': 'Gigsiphonic',
            'channel_url': 'https://promodj.com/gigsiphonic',
        },
    }, {
        # not valid html
        'url': 'https://promodj.com/martin.sehnal/videos/7555841/Martin_Sehnal_CII_33_Plus_CII_32_Clothes_on_the_peg_2_020_2_024_02_01th',
        'info_dict': {
            'id': '7555841',
            'ext': 'avi',
            'title': 'Martin Sehnal - CII 33 ( Plus CII 32 ) Clothes on the peg 2 020 ( 2 024 02. 01th ) )',
            'tags': ['Easy Listening', 'Drum & Bass'],
            'thumbnail': r're:^https?://',
            'upload_date': '20240201',
            'timestamp': 1706827560.0,
            'duration': 30000,
            'size': 2340757176,
            'view_count': int,
            'channel_url': 'https://promodj.com/martin.sehnal',
            'channel': 'Martin Sehnal',
        },
    }]

    # examples: MP3, 320 Кбит | MP4, 20157 Кбит | WAV, 1412 Кбит | AVI, 1731 Кбит | ASF, 6905 Кбит | FLAC, 1509 Кбит
    # https://regex101.com/r/2AuaxB/1
    _FORMATS_RE = r'(?:<a\s+href=\"(?P<url>[^\"]+)\">)?\s*(?P<format>\w+), (?P<bitrate>\d+) Кбит'
    _VIEW_COUNT_RE = r'<b>(?:Прослушиваний|Просмотров):</b>\s*(\d+)'
    # examples: 0:21 | 1:07 | 74:38
    _DURATION_RE = r'<b>Продолжительность:</b>\s*(\d+:\d{2})'
    # examples: 818.4 Кб | 12.9 Мб | 4 Гб | 1.76 Гб | 1001.5 Мб
    _SIZE_RE = r'<b>Размер:</b>\s*(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>Б|Кб|Мб|Гб|Тб)'
    # examples: сегодня 2:55 | вчера 23:17 | 1 июня 2016 3:46
    _TIMESTAMP_RE = r'<b>Публикация:</b>\s*(?P<day>вчера|сегодня|\d{1,2})(?: (?P<month>[а-я]+) (?P<year>\d{4}))?\s*(?P<hours>\d{1,2}):(?P<minutes>\d{2})'
    _TAGS_RE = r'<span\s+class=\"styles\">([^\n]+)</span>'

    # https://regex101.com/r/2ZkUmW/1
    _MUSIC_DATA_RE = r'({\"no_preroll\":false,\"seekAny\":true,\"sources\":[^\n]+)\);'
    # https://regex101.com/r/b9utBf/1
    _VIDEO_DATA_RE = r'({\"video\":true,\"config\":[^\n]+)\);'

    def _parse_ru_date(self, day, month, year, hours, minutes):
        RU_MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
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

    def _parse_ru_size(self, size, unit):
        RU_SIZE_UNITS = ['Б', 'Кб', 'Мб', 'Гб', 'Тб']
        return int(float(size) * pow(1024, RU_SIZE_UNITS.index(unit)))

    # music: always have lossy format (mp3), sometimes have lossless (wav or flac) format
    # video: sometimes have source format (mp4, avi, asf), always have converted for web format (mp4)
    def _real_extract(self, url):
        type, id = self._match_valid_url(url).groups()
        html = self._download_webpage(url, id)

        # always returns only one format: lossy mp3 for music or converted mp4 for video
        media_data = self._search_json(
            '', html, 'media data', id,
            contains_pattern=self._VIDEO_DATA_RE if type == 'videos' else self._MUSIC_DATA_RE,
            transform_source=js_to_json, fatal=False, default=None)
        if not media_data:
            media_data = self._fetch_media_data(id)
        metadata = self._parse_media_data(media_data, id)

        # html can be invalid
        try:
            meta_html = get_elements_html_by_class('dj_universal', html)[1]
        except Exception:
            meta_html = html

        # music: lossy format or lossless and lossy formats
        # video: source format
        # download links can be missing
        # best quality format always comes first
        formats_from_html = re.findall(self._FORMATS_RE, meta_html)
        is_paid = '<b>Цена:</b>' in meta_html
        # size field describes best quality
        size = self._parse_ru_size(*re.search(self._SIZE_RE, meta_html).groups())
        if type == 'videos':
            for url, format, bitrate in formats_from_html:
                if url_or_none(url):
                    metadata['formats'].append({
                        'format_id': 'source',
                        'url': url,
                        'tbr': int(bitrate),
                        'size': size,
                        'container': format.lower(),
                        'quality': 1,
                    })
        elif not is_paid:
            for i, match in enumerate(formats_from_html):
                url, format, bitrate = match
                is_last = i == len(formats_from_html) - 1
                if is_last:
                    metadata['formats'][0]['abr'] = int(bitrate)
                elif url_or_none(url):
                    metadata['formats'].append({
                        'format_id': 'lossless',
                        'url': url,
                        'abr': int(bitrate),
                        'acodec': format.lower(),
                        'vcodec': 'none',
                    })
            metadata['formats'][-1]['size'] = size

        return merge_dicts(metadata, {
            'title': clean_html(get_element_by_class('file_title', html)),
            'view_count': int_or_none(self._search_regex(self._VIEW_COUNT_RE, meta_html, 'view_count', default=None)),
            'duration': parse_duration(self._search_regex(self._DURATION_RE, meta_html, 'duration')),
            'timestamp': self._parse_ru_date(*re.search(self._TIMESTAMP_RE, meta_html).groups()),
            'tags': self._html_search_regex(self._TAGS_RE, meta_html, 'tags').split(', '),
        })


class PromoDJEmbedIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/embed/(?P<id>\d+)/(?:cover|big)'
    _TESTS = [{
        'url': 'https://promodj.com/embed/7555440/cover',
        'info_dict': {
            'id': '7555440',
            'ext': 'mp3',
            'title': 'Kolya Funk - Exclusive Mix (February 2024)',
            'tags': ['House', 'Indie Dance'],
            'upload_date': '20240131',
            'timestamp': 1706738400.0,
            'duration': 3697.0,
            'size': 148478361,
            'view_count': int,
        },
    }, {
        'url': 'https://promodj.com/embed/7540163/big',
        'info_dict': {
            'id': '7540163',
            'ext': 'mp3',
            'title': 'Khalif - Amore (Akif Pro Remix)',
            'tags': ['Deep House', 'Slap House'],
            'upload_date': '20231224',
            'timestamp': 1703418600.0,
            'duration': 157.0,
            'size': 8178892,
            'view_count': int,
        },
    }, {
        # video (can be only big)
        'url': 'https://promodj.com/embed/3922099/big',
        'info_dict': {
            'id': '3922099',
            'ext': 'mp4',
            'title': 'Will I Am & Britney Spears - Scream & Shout (DJ Nejtrino & DJ Stranger Remix) Video Full HD',
            'tags': ['Club House', 'Vocal House'],
            'thumbnail': r're:^https?://',
            'upload_date': '20130211',
            'timestamp': 1360583760.0,
            'duration': 234560,
            'size': 309644492,
            'view_count': int,
            'channel_url': 'https://promodj.com/dj-stranger',
            'channel': 'DJ Stranger',
        },
    }, {
        # blocked
        'url': 'https://promodj.com/embed/5586967/big',
        'only_matching': True,
    }, {
        # deleted
        'url': 'https://promodj.com/embed/5606804/big',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        metadata = self._parse_media_data(
            self._fetch_media_data(id), id)
        return self.url_result(metadata['webpage_url'], PromoDJIE, id)


class PromoDJShortIE(PromoDJBaseIE):
    _VALID_URL = r'https://(?:www\\.)?pdj.cc/(?P<id>\w+)'
    _TESTS = [{
        # music
        'url': 'https://pdj.cc/fv8VD',
        'info_dict': {
            'id': '7422493',
            'ext': 'flac',
            'title': 'Sasha Orbeat — Pure Love 3',
            'tags': ['Lo-Fi', 'Downtempo'],
            'upload_date': '20230213',
            'timestamp': 1676306160.0,
            'duration': 3631.0,
            'size': 685139558,
            'view_count': int,
        },
    }, {
        # video
        'url': 'https://pdj.cc/fvcpX',
        'info_dict': {
            'id': '7435905',
            'ext': 'mp4',
            'title': 'JULIA - DEBRI FM (guest mix 18.03.23)',
            'tags': ['Drum & Bass'],
            'thumbnail': r're:^https?://',
            'upload_date': '20230321',
            'timestamp': 1679441100.0,
            'duration': 2329640,
            'size': 2952790016,
            'view_count': int,
            'channel': 'JULIA',
            'channel_url': 'https://promodj.com/julia-breaks',
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        html = self._download_webpage(url, id)
        try:
            url = self._og_search_url(html)
        except Exception:
            raise ExtractorError('Unable to extract full URL')
        return self.url_result(url, PromoDJIE, id)


class PromoDJRadioIE(PromoDJBaseIE):
    _VALID_URL = rf'{PromoDJBaseIE._BASE_URL_RE}/radio#(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://promodj.com/radio#dubstep',
        'info_dict': {
            'id': 'dubstep',
            'ext': 'mp3',
            'title': r're:^Dubstep ',
            'description': 'Всё лучше под дабстеп',
            'thumbnail': r're:^https?://',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://promodj.com/radio#oldschool',
        'info_dict': {
            'id': 'oldschool',
            'ext': 'mp3',
            'title': r're:^Old-School ',
            'description': 'То самое доброе, старое, вечное',
            'thumbnail': r're:^https?://',
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        html = self._download_webpage(url, slug)
        radio_span = get_element_html_by_id(f'radio_{slug}', html)
        if not radio_span:
            raise ExtractorError('Radio channel is offline or not exists', expected=True)
        id = self._search_regex(r'amba="radio:(\d+)"', radio_span, 'id')
        tooltip_html = self._download_webpage(
            f'https://promodj.com/ajax/tooltip.html?wtf=radio:{id}', slug,
            note='Downloading tooltip webpage')
        title = clean_html(self._search_regex(
            r'<h1[^>]*><b>([^<]+)</b></h1>', tooltip_html, 'title', default=None))
        description = clean_html(self._search_regex(
            r'<div>([^<]+)</div>', tooltip_html, 'description', default=None))
        thumbnail = self._search_regex(
            rf'#radio_{slug}:after {{ background-image: url\(([^)]+)\); }}',
            html, 'thumbnail', default=None)

        return {
            'id': slug,
            'title': title,
            'description': description,
            'thumbnail': url_or_none(thumbnail),
            'formats': [{
                'url': f'https://radio.promodj.com/{slug}-192',
                'abr': 192,
                'ext': 'mp3',
                'acodec': 'mp3',
                'vcodec': 'none',
            }],
            'is_live': True,
        }

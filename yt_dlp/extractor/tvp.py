import itertools
import random
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    dict_get,
    ExtractorError,
    int_or_none,
    js_to_json,
    str_or_none,
    strip_or_none,
    traverse_obj,
    try_get,
    url_or_none,
)


class TVPIE(InfoExtractor):
    IE_NAME = 'tvp'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:tvp(?:parlament)?\.(?:pl|info)|tvpworld\.com|swipeto\.pl)/(?:(?!\d+/)[^/]+/)*(?P<id>\d+)'

    _TESTS = [{
        # TVPlayer 2 in js wrapper
        'url': 'https://swipeto.pl/64095316/uliczny-foxtrot-wypozyczalnia-kaset-kto-pamieta-dvdvideo',
        'info_dict': {
            'id': '64095316',
            'ext': 'mp4',
            'title': 'Uliczny Foxtrot — Wypożyczalnia kaset. Kto pamięta DVD-Video?',
            'age_limit': 0,
            'duration': 374,
            'thumbnail': r're:https://.+',
        },
        'expected_warnings': [
            'Failed to download ISM manifest: HTTP Error 404: Not Found',
            'Failed to download m3u8 information: HTTP Error 404: Not Found',
        ],
    }, {
        # TVPlayer legacy
        'url': 'https://www.tvp.pl/polska-press-video-uploader/wideo/62042351',
        'info_dict': {
            'id': '62042351',
            'ext': 'mp4',
            'title': 'Wideo',
            'description': 'Wideo Kamera',
            'duration': 24,
            'age_limit': 0,
            'thumbnail': r're:https://.+',
        },
    }, {
        # TVPlayer 2 in iframe
        'url': 'https://wiadomosci.tvp.pl/50725617/dzieci-na-sprzedaz-dla-homoseksualistow',
        'info_dict': {
            'id': '50725617',
            'ext': 'mp4',
            'title': 'Dzieci na sprzedaż dla homoseksualistów',
            'description': 'md5:7d318eef04e55ddd9f87a8488ac7d590',
            'age_limit': 12,
            'duration': 259,
            'thumbnail': r're:https://.+',
        },
    }, {
        # TVPlayer 2 in client-side rendered website (regional; window.__newsData)
        'url': 'https://warszawa.tvp.pl/25804446/studio-yayo',
        'info_dict': {
            'id': '25804446',
            'ext': 'mp4',
            'title': 'Studio Yayo',
            'upload_date': '20160616',
            'timestamp': 1466075700,
            'age_limit': 0,
            'duration': 20,
            'thumbnail': r're:https://.+',
        },
        'skip': 'Geo-blocked outside PL',
    }, {
        # TVPlayer 2 in client-side rendered website (tvp.info; window.__videoData)
        'url': 'https://www.tvp.info/52880236/09042021-0800',
        'info_dict': {
            'id': '52880236',
            'ext': 'mp4',
            'title': '09.04.2021, 08:00',
            'age_limit': 0,
            'thumbnail': r're:https://.+',
        },
        'skip': 'Geo-blocked outside PL',
    }, {
        # client-side rendered (regional) program (playlist) page
        'url': 'https://opole.tvp.pl/9660819/rozmowa-dnia',
        'info_dict': {
            'id': '9660819',
            'description': 'Od poniedziałku do piątku o 18:55',
            'title': 'Rozmowa dnia',
        },
        'playlist_mincount': 1800,
        'params': {
            'skip_download': True,
        }
    }, {
        # ABC-specific video embeding
        # moved to https://bajkowakraina.tvp.pl/wideo/50981130,teleranek,51027049,zubr,51116450
        'url': 'https://abc.tvp.pl/48636269/zubry-odc-124',
        'info_dict': {
            'id': '48320456',
            'ext': 'mp4',
            'title': 'Teleranek, Żubr',
        },
        'skip': 'unavailable',
    }, {
        # yet another vue page
        'url': 'https://jp2.tvp.pl/46925618/filmy',
        'info_dict': {
            'id': '46925618',
            'title': 'Filmy',
        },
        'playlist_mincount': 19,
    }, {
        'url': 'http://vod.tvp.pl/seriale/obyczajowe/na-sygnale/sezon-2-27-/odc-39/17834272',
        'only_matching': True,
    }, {
        'url': 'http://wiadomosci.tvp.pl/25169746/24052016-1200',
        'only_matching': True,
    }, {
        'url': 'http://krakow.tvp.pl/25511623/25lecie-mck-wyjatkowe-miejsce-na-mapie-krakowa',
        'only_matching': True,
    }, {
        'url': 'http://teleexpress.tvp.pl/25522307/wierni-wzieli-udzial-w-procesjach',
        'only_matching': True,
    }, {
        'url': 'http://sport.tvp.pl/25522165/krychowiak-uspokaja-w-sprawie-kontuzji-dwa-tygodnie-to-maksimum',
        'only_matching': True,
    }, {
        'url': 'http://www.tvp.info/25511919/trwa-rewolucja-wladza-zdecydowala-sie-na-pogwalcenie-konstytucji',
        'only_matching': True,
    }, {
        'url': 'https://tvp.info/49193823/teczowe-flagi-na-pomnikach-prokuratura-wszczela-postepowanie-wieszwiecej',
        'only_matching': True,
    }, {
        'url': 'https://www.tvpparlament.pl/retransmisje-vod/inne/wizyta-premiera-mateusza-morawieckiego-w-firmie-berotu-sp-z-oo/48857277',
        'only_matching': True,
    }, {
        'url': 'https://tvpworld.com/48583640/tescos-polish-business-bought-by-danish-chain-netto',
        'only_matching': True,
    }]

    def _parse_vue_website_data(self, webpage, page_id):
        website_data = self._search_regex([
            # website - regiony, tvp.info
            # directory - jp2.tvp.pl
            r'window\.__(?:website|directory)Data\s*=\s*({(?:.|\s)+?});',
        ], webpage, 'website data')
        if not website_data:
            return None
        return self._parse_json(website_data, page_id, transform_source=js_to_json)

    def _extract_vue_video(self, video_data, page_id=None):
        if isinstance(video_data, str):
            video_data = self._parse_json(video_data, page_id, transform_source=js_to_json)
        thumbnails = []
        image = video_data.get('image')
        if image:
            for thumb in (image if isinstance(image, list) else [image]):
                thmb_url = str_or_none(thumb.get('url'))
                if thmb_url:
                    thumbnails.append({
                        'url': thmb_url,
                    })
        is_website = video_data.get('type') == 'website'
        if is_website:
            url = video_data['url']
        else:
            url = 'tvp:' + str_or_none(video_data.get('_id') or page_id)
        return {
            '_type': 'url_transparent',
            'id': str_or_none(video_data.get('_id') or page_id),
            'url': url,
            'ie_key': (TVPIE if is_website else TVPEmbedIE).ie_key(),
            'title': str_or_none(video_data.get('title')),
            'description': str_or_none(video_data.get('lead')),
            'timestamp': int_or_none(video_data.get('release_date_long')),
            'duration': int_or_none(video_data.get('duration')),
            'thumbnails': thumbnails,
        }

    def _handle_vuejs_page(self, url, webpage, page_id):
        # vue client-side rendered sites (all regional pages + tvp.info)
        video_data = self._search_regex([
            r'window\.__(?:news|video)Data\s*=\s*({(?:.|\s)+?})\s*;',
        ], webpage, 'video data', default=None)
        if video_data:
            return self._extract_vue_video(video_data, page_id=page_id)
        # paged playlists
        website_data = self._parse_vue_website_data(webpage, page_id)
        if website_data:
            entries = self._vuejs_entries(url, website_data, page_id)

            return {
                '_type': 'playlist',
                'id': page_id,
                'title': str_or_none(website_data.get('title')),
                'description': str_or_none(website_data.get('lead')),
                'entries': entries,
            }
        raise ExtractorError('Could not extract video/website data')

    def _vuejs_entries(self, url, website_data, page_id):

        def extract_videos(wd):
            if wd.get('latestVideo'):
                yield self._extract_vue_video(wd['latestVideo'])
            for video in wd.get('videos') or []:
                yield self._extract_vue_video(video)
            for video in wd.get('items') or []:
                yield self._extract_vue_video(video)

        yield from extract_videos(website_data)

        if website_data.get('items_total_count') > website_data.get('items_per_page'):
            for page in itertools.count(2):
                page_website_data = self._parse_vue_website_data(
                    self._download_webpage(url, page_id, note='Downloading page #%d' % page,
                                           query={'page': page}),
                    page_id)
                if not page_website_data.get('videos') and not page_website_data.get('items'):
                    break
                yield from extract_videos(page_website_data)

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, page_id)

        # The URL may redirect to a VOD
        # example: https://vod.tvp.pl/48463890/wadowickie-spotkania-z-janem-pawlem-ii
        for ie_cls in (TVPVODSeriesIE, TVPVODVideoIE):
            if ie_cls.suitable(urlh.url):
                return self.url_result(urlh.url, ie=ie_cls.ie_key(), video_id=page_id)

        if re.search(
                r'window\.__(?:video|news|website|directory)Data\s*=',
                webpage):
            return self._handle_vuejs_page(url, webpage, page_id)

        # classic server-side rendered sites
        video_id = self._search_regex([
            r'<iframe[^>]+src="[^"]*?embed\.php\?(?:[^&]+&)*ID=(\d+)',
            r'<iframe[^>]+src="[^"]*?object_id=(\d+)',
            r"object_id\s*:\s*'(\d+)'",
            r'data-video-id="(\d+)"',

            # abc.tvp.pl - somehow there are more than one video IDs that seem to be the same video?
            # the first one is referenced to as "copyid", and seems to be unused by the website
            r'<script>\s*tvpabc\.video\.init\(\s*\d+,\s*(\d+)\s*\)\s*</script>',
        ], webpage, 'video id', default=page_id)
        return {
            '_type': 'url_transparent',
            'url': 'tvp:' + video_id,
            'description': self._og_search_description(
                webpage, default=None) or (self._html_search_meta(
                    'description', webpage, default=None)
                    if '//s.tvp.pl/files/portal/v' in webpage else None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'ie_key': 'TVPEmbed',
        }


class TVPStreamIE(InfoExtractor):
    IE_NAME = 'tvp:stream'
    _VALID_URL = r'(?:tvpstream:|https?://(?:tvpstream\.vod|stream)\.tvp\.pl/(?:\?(?:[^&]+[&;])*channel_id=)?)(?P<id>\d*)'
    _TESTS = [{
        'url': 'https://stream.tvp.pl/?channel_id=56969941',
        'only_matching': True,
    }, {
        # untestable as "video" id changes many times across a day
        'url': 'https://tvpstream.vod.tvp.pl/?channel_id=1455',
        'only_matching': True,
    }, {
        'url': 'tvpstream:39821455',
        'only_matching': True,
    }, {
        # the default stream when you provide no channel_id, most probably TVP Info
        'url': 'tvpstream:',
        'only_matching': True,
    }, {
        'url': 'https://tvpstream.vod.tvp.pl/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel_url = self._proto_relative_url('//stream.tvp.pl/?channel_id=%s' % channel_id or 'default')
        webpage = self._download_webpage(channel_url, channel_id or 'default', 'Downloading channel webpage')
        channels = self._search_json(
            r'window\.__channels\s*=', webpage, 'channel list', channel_id,
            contains_pattern=r'\[\s*{(?s:.+)}\s*]')
        channel = traverse_obj(channels, (lambda _, v: channel_id == str(v['id'])), get_all=False) if channel_id else channels[0]
        audition = traverse_obj(channel, ('items', lambda _, v: v['is_live'] is True), get_all=False)
        return {
            '_type': 'url_transparent',
            'id': channel_id or channel['id'],
            'url': 'tvp:%s' % audition['video_id'],
            'title': audition.get('title'),
            'alt_title': channel.get('title'),
            'is_live': True,
            'ie_key': 'TVPEmbed',
        }


class TVPEmbedIE(InfoExtractor):
    IE_NAME = 'tvp:embed'
    IE_DESC = 'Telewizja Polska'
    _GEO_BYPASS = False
    _VALID_URL = r'''(?x)
        (?:
            tvp:
            |https?://
                (?:[^/]+\.)?
                (?:tvp(?:parlament)?\.pl|tvp\.info|tvpworld\.com|swipeto\.pl)/
                (?:sess/
                        (?:tvplayer\.php\?.*?object_id
                        |TVPlayer2/(?:embed|api)\.php\?.*[Ii][Dd])
                    |shared/details\.php\?.*?object_id)
                =)
        (?P<id>\d+)
    '''
    _EMBED_REGEX = [rf'(?x)<iframe[^>]+?src=(["\'])(?P<url>{_VALID_URL[4:]})']

    _TESTS = [{
        'url': 'tvp:194536',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'md5:76649d2014f65c99477be17f23a4dead',
            'age_limit': 12,
            'duration': 2652,
            'series': 'Czas honoru',
            'episode': 'Episode 13',
            'episode_number': 13,
            'season': 'sezon 1',
            'thumbnail': r're:https://.+',
        },
    }, {
        'url': 'https://www.tvp.pl/sess/tvplayer.php?object_id=51247504&amp;autoplay=false',
        'info_dict': {
            'id': '51247504',
            'ext': 'mp4',
            'title': 'Razmova 091220',
            'duration': 876,
            'age_limit': 0,
            'thumbnail': r're:https://.+',
        },
    }, {
        # TVPlayer2 embed URL
        'url': 'https://tvp.info/sess/TVPlayer2/embed.php?ID=50595757',
        'only_matching': True,
    }, {
        'url': 'https://wiadomosci.tvp.pl/sess/TVPlayer2/api.php?id=51233452',
        'only_matching': True,
    }, {
        # pulsembed on dziennik.pl
        'url': 'https://www.tvp.pl/shared/details.php?copy_id=52205981&object_id=52204505&autoplay=false&is_muted=false&allowfullscreen=true&template=external-embed/video/iframe-video.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # it could be anything that is a valid JS function name
        callback = random.choice((
            'jebac_pis',
            'jebacpis',
            'ziobro',
            'sasin70',
            'sasin_przejebal_70_milionow_PLN',
            'tvp_is_a_state_propaganda_service',
        ))

        webpage = self._download_webpage(
            ('https://www.tvp.pl/sess/TVPlayer2/api.php?id=%s'
             + '&@method=getTvpConfig&@callback=%s') % (video_id, callback), video_id)

        # stripping JSONP padding
        datastr = webpage[15 + len(callback):-3]
        if datastr.startswith('null,'):
            error = self._parse_json(datastr[5:], video_id, fatal=False)
            error_desc = traverse_obj(error, (0, 'desc'))

            if error_desc == 'Obiekt wymaga płatności':
                raise ExtractorError('Video requires payment and log-in, but log-in is not implemented')

            raise ExtractorError(error_desc or 'unexpected JSON error')

        content = self._parse_json(datastr, video_id)['content']
        info = content['info']
        is_live = try_get(info, lambda x: x['isLive'], bool)

        if info.get('isGeoBlocked'):
            # actual country list is not provided, we just assume it's always available in PL
            self.raise_geo_restricted(countries=['PL'])

        formats = []
        for file in content['files']:
            video_url = url_or_none(file.get('url'))
            if not video_url:
                continue
            ext = determine_ext(video_url, None)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(video_url, video_id, m3u8_id='hls', fatal=False, live=is_live))
            elif ext == 'mpd':
                if is_live:
                    # doesn't work with either ffmpeg or native downloader
                    continue
                formats.extend(self._extract_mpd_formats(video_url, video_id, mpd_id='dash', fatal=False))
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(video_url, video_id, f4m_id='hds', fatal=False))
            elif video_url.endswith('.ism/manifest'):
                formats.extend(self._extract_ism_formats(video_url, video_id, ism_id='mss', fatal=False))
            else:
                formats.append({
                    'format_id': 'direct',
                    'url': video_url,
                    'ext': ext or file.get('type'),
                    'fps': int_or_none(traverse_obj(file, ('quality', 'fps'))),
                    'tbr': int_or_none(traverse_obj(file, ('quality', 'bitrate')), scale=1000),
                    'width': int_or_none(traverse_obj(file, ('quality', 'width'))),
                    'height': int_or_none(traverse_obj(file, ('quality', 'height'))),
                })

        title = dict_get(info, ('subtitle', 'title', 'seoTitle'))
        description = dict_get(info, ('description', 'seoDescription'))
        thumbnails = []
        for thumb in content.get('posters') or ():
            thumb_url = thumb.get('src')
            if not thumb_url or '{width}' in thumb_url or '{height}' in thumb_url:
                continue
            thumbnails.append({
                'url': thumb.get('src'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
            })
        age_limit = try_get(info, lambda x: x['ageGroup']['minAge'], int)
        if age_limit == 1:
            age_limit = 0
        duration = try_get(info, lambda x: x['duration'], int) if not is_live else None

        subtitles = {}
        for sub in content.get('subtitles') or []:
            if not sub.get('url'):
                continue
            subtitles.setdefault(sub['lang'], []).append({
                'url': sub['url'],
                'ext': sub.get('type'),
            })

        info_dict = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'age_limit': age_limit,
            'is_live': is_live,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
        }

        # vod.tvp.pl
        if info.get('vortalName') == 'vod':
            info_dict.update({
                'title': '%s, %s' % (info.get('title'), info.get('subtitle')),
                'series': info.get('title'),
                'season': info.get('season'),
                'episode_number': info.get('episode'),
            })

        return info_dict


class TVPVODBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://vod.tvp.pl/api/products'

    def _call_api(self, resource, video_id, **kwargs):
        return self._download_json(
            f'{self._API_BASE_URL}/{resource}', video_id,
            query={'lang': 'pl', 'platform': 'BROWSER'}, **kwargs)

    def _parse_video(self, video):
        return {
            '_type': 'url',
            'url': 'tvp:' + video['externalUid'],
            'ie_key': TVPEmbedIE.ie_key(),
            'title': video.get('title'),
            'description': traverse_obj(video, ('lead', 'description')),
            'age_limit': int_or_none(video.get('rating')),
            'duration': int_or_none(video.get('duration')),
        }


class TVPVODVideoIE(TVPVODBaseIE):
    IE_NAME = 'tvp:vod'
    _VALID_URL = r'https?://vod\.tvp\.pl/[a-z\d-]+,\d+/[a-z\d-]+(?<!-odcinki)(?:-odcinki,\d+/odcinek-\d+,S\d+E\d+)?,(?P<id>\d+)(?:\?[^#]+)?(?:#.+)?$'

    _TESTS = [{
        'url': 'https://vod.tvp.pl/dla-dzieci,24/laboratorium-alchemika-odcinki,309338/odcinek-24,S01E24,311357',
        'info_dict': {
            'id': '60468609',
            'ext': 'mp4',
            'title': 'Laboratorium alchemika, Tusze termiczne. Jak zobaczyć niewidoczne. Odcinek 24',
            'description': 'md5:1d4098d3e537092ccbac1abf49b7cd4c',
            'duration': 300,
            'episode_number': 24,
            'episode': 'Episode 24',
            'age_limit': 0,
            'series': 'Laboratorium alchemika',
            'thumbnail': 're:https://.+',
        },
    }, {
        'url': 'https://vod.tvp.pl/filmy-dokumentalne,163/ukrainski-sluga-narodu,339667',
        'info_dict': {
            'id': '51640077',
            'ext': 'mp4',
            'title': 'Ukraiński sługa narodu, Ukraiński sługa narodu',
            'series': 'Ukraiński sługa narodu',
            'description': 'md5:b7940c0a8e439b0c81653a986f544ef3',
            'age_limit': 12,
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 3051,
            'thumbnail': 're:https://.+',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return self._parse_video(self._call_api(f'vods/{video_id}', video_id))


class TVPVODSeriesIE(TVPVODBaseIE):
    IE_NAME = 'tvp:vod:series'
    _VALID_URL = r'https?://vod\.tvp\.pl/[a-z\d-]+,\d+/[a-z\d-]+-odcinki,(?P<id>\d+)(?:\?[^#]+)?(?:#.+)?$'

    _TESTS = [{
        'url': 'https://vod.tvp.pl/seriale,18/ranczo-odcinki,316445',
        'info_dict': {
            'id': '316445',
            'title': 'Ranczo',
            'age_limit': 12,
            'categories': ['seriale'],
        },
        'playlist_count': 129,
    }, {
        'url': 'https://vod.tvp.pl/programy,88/rolnik-szuka-zony-odcinki,284514',
        'only_matching': True,
    }, {
        'url': 'https://vod.tvp.pl/dla-dzieci,24/laboratorium-alchemika-odcinki,309338',
        'only_matching': True,
    }]

    def _entries(self, seasons, playlist_id):
        for season in seasons:
            episodes = self._call_api(
                f'vods/serials/{playlist_id}/seasons/{season["id"]}/episodes', playlist_id,
                note=f'Downloading episode list for {season["title"]}')
            yield from map(self._parse_video, episodes)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        metadata = self._call_api(
            f'vods/serials/{playlist_id}', playlist_id,
            note='Downloading serial metadata')
        seasons = self._call_api(
            f'vods/serials/{playlist_id}/seasons', playlist_id,
            note='Downloading season list')
        return self.playlist_result(
            self._entries(seasons, playlist_id), playlist_id, strip_or_none(metadata.get('title')),
            clean_html(traverse_obj(metadata, ('description', 'lead'), expected_type=strip_or_none)),
            categories=[traverse_obj(metadata, ('mainCategory', 'name'))],
            age_limit=int_or_none(metadata.get('rating')),
        )

import itertools
import random

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    dict_get,
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
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:tvp(?:parlament)?\.(?:pl|info)|tvpworld\.com|belsat\.eu)/(?:(?!\d+/)[^/]+/)*(?P<id>\d+)(?:[/?#]|$)'

    _TESTS = [{
        # TVPlayer 3
        'url': 'https://wilno.tvp.pl/75865949/rozmowa-tygodnia-z-andriusem-vainysem-o-wizycie-s-holowni',
        'info_dict': {
            'id': '75866176',
            'ext': 'mp4',
            'title': 'Rozmowa tygodnia z Andriusem Vaišnysem o wizycie S. Hołowni',
            'alt_title': 'md5:51cc9faf4623ba33aa5191bb83f3f76a',
            'duration': 169,
            'age_limit': 0,
            'release_timestamp': 1707591120,
            'release_date': '20240210',
            'thumbnail': r're:https://.+',
        },
    }, {
        # TVPlayer 2 (JSON)
        'url': 'https://jp2.tvp.pl/48566934/o-suwerennosci-narodu-i-upadku-totalitaryzmu-przemowienie-powitalne',
        'info_dict': {
            'id': '48566934',
            'ext': 'mp4',
            'title': 'O suwerenności narodu i upadku totalitaryzmu. Przemówienie powitalne',
            'duration': 527,
            'age_limit': 0,
            'release_timestamp': 1592388480,
            'release_date': '20200617',
            'thumbnail': r're:https://.+',
        },
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
        # client-side rendered (regional) program (playlist) page
        'url': 'https://opole.tvp.pl/9660819/rozmowa-dnia',
        'info_dict': {
            'id': '9660819',
            'description': 'Od poniedziałku do piątku o 19:00.',
            'title': 'Rozmowa dnia',
        },
        'playlist_mincount': 1800,
        'params': {
            'skip_download': True,
        },
    }, {
        # yet another vue page
        'url': 'https://jp2.tvp.pl/46925618/filmy',
        'info_dict': {
            'id': '46925618',
            'title': 'Filmy',
        },
        'playlist_mincount': 27,
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
        'url': 'https://tvpworld.com/48583640/tescos-polish-business-bought-by-danish-chain-netto',
        'only_matching': True,
    }, {
        'url': 'https://belsat.eu/83193018/vybary-jak-castka-hibrydnaj-vajny',
        'only_matching': True,
    }]

    def _parse_video(self, url, video_data, page_id):
        video_id = str(video_data.get('_id'))
        return {
            '_type': 'url_transparent',
            'url': f'tvp:{video_id}',
            'ie_key': TVPEmbedIE.ie_key(),
            'id': video_id,
            **traverse_obj(video_data, {
                'title': 'title',
                'duration': 'duration',
                'is_live': 'is_live',
                'release_timestamp': ('release_date', {int_or_none(scale=1000)}),
            }),
        }

    def _parse_news(self, url, news_data, page_id):
        videos = [self._parse_video(url, video_data, page_id) for video_data in traverse_obj(news_data, ('video', 'items'))]
        info_dict = {
            'id': str_or_none(news_data.get('id')) or page_id,
            'title': news_data['title'],
            'alt_title': news_data.get('lead'),
            'description': news_data.get('description'),
        }
        if len(videos) == 1:
            return {**info_dict, **videos[0]}
        return {
            **info_dict,
            '_type': 'playlist',
            'entries': videos,
        }

    def _get_website_entries(self, url, website_data, page_id, data_type='website'):
        parser = self._parse_video
        if data_type == 'directory':
            parser = self._parse_directory_website

        def extract_videos(wd):
            if wd.get('latestVideo'):
                yield parser(url, wd['latestVideo'], page_id)
            for video in wd.get('videos') or []:
                yield parser(url, video, page_id)
            for video in wd.get('items') or []:
                yield parser(url, video, page_id)

        yield from extract_videos(website_data)

        if website_data.get('items_total_count') > website_data.get('items_per_page'):
            for page in itertools.count(2):
                page_website_data = self._find_data(data_type, self._download_webpage(
                    url, page_id, note=f'Downloading {data_type} page #{page}',
                    query={'page': page}), page_id)
                if not page_website_data.get('videos') and not page_website_data.get('items'):
                    break
                yield from extract_videos(page_website_data)

    def _parse_website(self, url, website_data, page_id):
        return {
            '_type': 'playlist',
            'entries': self._get_website_entries(url, website_data, page_id),
            'id': page_id,
            'title': website_data.get('title'),
            'description': website_data.get('lead'),
        }

    def _parse_directory_website(self, url, website_data, page_id):
        website_id = str_or_none(website_data.get('_id'))
        return {
            '_type': 'url_transparent',
            'url': website_data['url'],
            'id': website_id,
            'title': website_data.get('title'),
            'description': website_data.get('lead'),
        }

    def _parse_directory(self, url, directory_data, page_id):
        return {
            '_type': 'playlist',
            'entries': self._get_website_entries(url, directory_data, page_id, data_type='directory'),
            'id': page_id,
            'title': directory_data.get('title'),
            'description': directory_data.get('lead'),
        }

    def _find_data(self, data_type, webpage, video_id, **kwargs):
        return self._search_json(
            rf'window\.__{data_type}Data\s*=', webpage, f'{data_type} data', video_id,
            transform_source=js_to_json, **kwargs)

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, page_id)

        # The URL may redirect to a VOD
        # example: https://vod.tvp.pl/48463890/wadowickie-spotkania-z-janem-pawlem-ii
        for ie_cls in (TVPVODSeriesIE, TVPVODVideoIE):
            if ie_cls.suitable(urlh.url):
                return self.url_result(urlh.url, ie=ie_cls.ie_key(), video_id=page_id)

        for (dt, parse) in (
            ('news', self._parse_news),
            ('video', self._parse_video),
            ('website', self._parse_website),
            ('directory', self._parse_directory),
        ):
            data = self._find_data(dt, webpage, page_id, default=None)
            if data:
                return parse(url, data, page_id)

        # classic server-side rendered sites
        video_id = self._search_regex([
            r'<iframe[^>]+src="[^"]*?embed\.php\?(?:[^&]+&)*ID=(\d+)',
            r'<iframe[^>]+src="[^"]*?object_id=(\d+)',
            r"object_id\s*:\s*'(\d+)'",
            r'data-video-id="(\d+)"',
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
        channel_url = self._proto_relative_url(f'//stream.tvp.pl/?channel_id={channel_id}' or 'default')
        webpage = self._download_webpage(channel_url, channel_id or 'default', 'Downloading channel webpage')
        channels = self._search_json(
            r'window\.__channels\s*=', webpage, 'channel list', channel_id,
            contains_pattern=r'\[\s*{(?s:.+)}\s*]')
        channel = traverse_obj(channels, (lambda _, v: channel_id == str(v['id'])), get_all=False) if channel_id else channels[0]
        audition = traverse_obj(channel, ('items', lambda _, v: v['is_live'] is True), get_all=False)
        return {
            '_type': 'url_transparent',
            'id': channel_id or channel['id'],
            'url': 'tvp:{}'.format(audition['video_id']),
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
            f'https://www.tvp.pl/sess/TVPlayer2/api.php?id={video_id}&@method=getTvpConfig&@callback={callback}', video_id)

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
                'title': '{}, {}'.format(info.get('title'), info.get('subtitle')),
                'series': info.get('title'),
                'season': info.get('season'),
                'episode_number': info.get('episode'),
            })

        return info_dict


class TVPVODBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://vod.tvp.pl/api/products'

    def _call_api(self, resource, video_id, query={}, **kwargs):
        is_valid = lambda x: 200 <= x < 300
        document, urlh = self._download_json_handle(
            f'{self._API_BASE_URL}/{resource}', video_id,
            query={'lang': 'pl', 'platform': 'BROWSER', **query},
            expected_status=lambda x: is_valid(x) or 400 <= x < 500, **kwargs)
        if is_valid(urlh.status):
            return document
        raise ExtractorError(f'Woronicza said: {document.get("code")} (HTTP {urlh.status})')

    def _parse_video(self, video, with_url=True):
        info_dict = traverse_obj(video, {
            'id': ('id', {str_or_none}),
            'title': 'title',
            'age_limit': ('rating', {int_or_none}),
            'duration': ('duration', {int_or_none}),
            'episode_number': ('number', {int_or_none}),
            'series': ('season', 'serial', 'title', {str_or_none}),
            'thumbnails': ('images', ..., ..., {'url': ('url', {url_or_none})}),
        })
        info_dict['description'] = clean_html(dict_get(video, ('lead', 'description')))
        if with_url:
            info_dict.update({
                '_type': 'url',
                'url': video['webUrl'],
                'ie_key': TVPVODVideoIE.ie_key(),
            })
        return info_dict


class TVPVODVideoIE(TVPVODBaseIE):
    IE_NAME = 'tvp:vod'
    _VALID_URL = r'https?://vod\.tvp\.pl/(?P<category>[a-z\d-]+,\d+)/[a-z\d-]+(?<!-odcinki)(?:-odcinki,\d+/odcinek-\d+,S\d+E\d+)?,(?P<id>\d+)/?(?:[?#]|$)'

    _TESTS = [{
        'url': 'https://vod.tvp.pl/dla-dzieci,24/laboratorium-alchemika-odcinki,309338/odcinek-24,S01E24,311357',
        'info_dict': {
            'id': '311357',
            'ext': 'mp4',
            'title': 'Tusze termiczne. Jak zobaczyć niewidoczne. Odcinek 24',
            'description': 'md5:1d4098d3e537092ccbac1abf49b7cd4c',
            'duration': 300,
            'episode_number': 24,
            'episode': 'Episode 24',
            'age_limit': 0,
            'series': 'Laboratorium alchemika',
            'thumbnail': 're:https?://.+',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://vod.tvp.pl/filmy-dokumentalne,163/ukrainski-sluga-narodu,339667',
        'info_dict': {
            'id': '339667',
            'ext': 'mp4',
            'title': 'Ukraiński sługa narodu',
            'description': 'md5:b7940c0a8e439b0c81653a986f544ef3',
            'age_limit': 12,
            'duration': 3051,
            'thumbnail': 're:https?://.+',
            'subtitles': 'count:2',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'embed fails with "payment required"',
        'url': 'https://vod.tvp.pl/seriale,18/polowanie-na-cmy-odcinki,390116/odcinek-7,S01E07,398869',
        'info_dict': {
            'id': '398869',
            'ext': 'mp4',
            'title': 'odc. 7',
            'description': 'md5:dd2bb33f023dc5c2fbaddfbe4cb5dba0',
            'duration': 2750,
            'age_limit': 16,
            'series': 'Polowanie na ćmy',
            'episode_number': 7,
            'episode': 'Episode 7',
            'thumbnail': 're:https?://.+',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://vod.tvp.pl/live,1/tvp-world,399731',
        'info_dict': {
            'id': '399731',
            'ext': 'mp4',
            'title': r're:TVP WORLD \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'live_status': 'is_live',
            'thumbnail': 're:https?://.+',
        },
    }]

    def _real_extract(self, url):
        category, video_id = self._match_valid_url(url).group('category', 'id')

        is_live = category == 'live,1'
        entity = 'lives' if is_live else 'vods'
        info_dict = self._parse_video(self._call_api(f'{entity}/{video_id}', video_id), with_url=False)

        playlist = self._call_api(f'{video_id}/videos/playlist', video_id, query={'videoType': 'MOVIE'})

        info_dict['formats'] = []
        for manifest_url in traverse_obj(playlist, ('sources', 'HLS', ..., 'src')):
            info_dict['formats'].extend(self._extract_m3u8_formats(manifest_url, video_id, fatal=False))
        for manifest_url in traverse_obj(playlist, ('sources', 'DASH', ..., 'src')):
            info_dict['formats'].extend(self._extract_mpd_formats(manifest_url, video_id, fatal=False))

        info_dict['subtitles'] = {}
        for sub in playlist.get('subtitles') or []:
            info_dict['subtitles'].setdefault(sub.get('language') or 'und', []).append({
                'url': sub['url'],
                'ext': 'ttml',
            })

        info_dict['is_live'] = is_live

        return info_dict


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
        'playlist_count': 130,
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

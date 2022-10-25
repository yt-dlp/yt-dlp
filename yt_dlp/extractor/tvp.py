import itertools
import random
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    dict_get,
    ExtractorError,
    int_or_none,
    js_to_json,
    orderedSet,
    str_or_none,
    try_get,
)


class TVPIE(InfoExtractor):
    IE_NAME = 'tvp'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:tvp(?:parlament)?\.(?:pl|info)|polandin\.com)/(?:video/(?:[^,\s]*,)*|(?:(?!\d+/)[^/]+/)*)(?P<id>\d+)'

    _TESTS = [{
        # TVPlayer 2 in js wrapper
        'url': 'https://vod.tvp.pl/video/czas-honoru,i-seria-odc-13,194536',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'md5:437f48b93558370b031740546b696e24',
            'age_limit': 12,
        },
    }, {
        # TVPlayer legacy
        'url': 'http://www.tvp.pl/there-can-be-anything-so-i-shortened-it/17916176',
        'info_dict': {
            'id': '17916176',
            'ext': 'mp4',
            'title': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
            'description': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
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
        }
    }, {
        # TVPlayer 2 in client-side rendered website (tvp.info; window.__videoData)
        'url': 'https://www.tvp.info/52880236/09042021-0800',
        'info_dict': {
            'id': '52880236',
            'ext': 'mp4',
            'title': '09.04.2021, 08:00',
        },
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
        'url': 'https://polandin.com/47942651/pln-10-billion-in-subsidies-transferred-to-companies-pm',
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
            fucked_up_url_parts = re.match(r'https?://vod\.tvp\.pl/(\d+)/([^/?#]+)', url)
            if fucked_up_url_parts:
                url = f'https://vod.tvp.pl/website/{fucked_up_url_parts.group(2)},{fucked_up_url_parts.group(1)}'
        else:
            url = 'tvp:' + str_or_none(video_data.get('_id') or page_id)
        return {
            '_type': 'url_transparent',
            'id': str_or_none(video_data.get('_id') or page_id),
            'url': url,
            'ie_key': 'TVPEmbed' if not is_website else 'TVPWebsite',
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
        if TVPWebsiteIE.suitable(urlh.url):
            return self.url_result(urlh.url, ie=TVPWebsiteIE.ie_key(), video_id=page_id)

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
    _VALID_URL = r'(?:tvpstream:|https?://tvpstream\.vod\.tvp\.pl/(?:\?(?:[^&]+[&;])*channel_id=)?)(?P<id>\d*)'
    _TESTS = [{
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

    _PLAYER_BOX_RE = r'<div\s[^>]*id\s*=\s*["\']?tvp_player_box["\']?[^>]+data-%s-id\s*=\s*["\']?(\d+)'
    _BUTTON_RE = r'<div\s[^>]*data-channel-id=["\']?%s["\']?[^>]*\sdata-title=(?:"([^"]*)"|\'([^\']*)\')[^>]*\sdata-stationname=(?:"([^"]*)"|\'([^\']*)\')'

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel_url = self._proto_relative_url('//tvpstream.vod.tvp.pl/?channel_id=%s' % channel_id or 'default')
        webpage = self._download_webpage(channel_url, channel_id, 'Downloading channel webpage')
        if not channel_id:
            channel_id = self._search_regex(self._PLAYER_BOX_RE % 'channel',
                                            webpage, 'default channel id')
        video_id = self._search_regex(self._PLAYER_BOX_RE % 'video',
                                      webpage, 'video id')
        audition_title, station_name = self._search_regex(
            self._BUTTON_RE % (re.escape(channel_id)), webpage,
            'audition title and station name',
            group=(1, 2))
        return {
            '_type': 'url_transparent',
            'id': channel_id,
            'url': 'tvp:%s' % video_id,
            'title': audition_title,
            'alt_title': station_name,
            'is_live': True,
            'ie_key': 'TVPEmbed',
        }


class TVPEmbedIE(InfoExtractor):
    IE_NAME = 'tvp:embed'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'''(?x)
        (?:
            tvp:
            |https?://
                (?:[^/]+\.)?
                (?:tvp(?:parlament)?\.pl|tvp\.info|polandin\.com)/
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
        },
    }, {
        'url': 'https://www.tvp.pl/sess/tvplayer.php?object_id=51247504&amp;autoplay=false',
        'info_dict': {
            'id': '51247504',
            'ext': 'mp4',
            'title': 'Razmova 091220',
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
            error = self._parse_json(datastr[5:], video_id)
            raise ExtractorError(error[0]['desc'])

        content = self._parse_json(datastr, video_id)['content']
        info = content['info']
        is_live = try_get(info, lambda x: x['isLive'], bool)

        formats = []
        for file in content['files']:
            video_url = file.get('url')
            if not video_url:
                continue
            if video_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(video_url, video_id, m3u8_id='hls', fatal=False, live=is_live))
            elif video_url.endswith('.mpd'):
                if is_live:
                    # doesn't work with either ffmpeg or native downloader
                    continue
                formats.extend(self._extract_mpd_formats(video_url, video_id, mpd_id='dash', fatal=False))
            elif video_url.endswith('.f4m'):
                formats.extend(self._extract_f4m_formats(video_url, video_id, f4m_id='hds', fatal=False))
            elif video_url.endswith('.ism/manifest'):
                formats.extend(self._extract_ism_formats(video_url, video_id, ism_id='mss', fatal=False))
            else:
                # mp4, wmv or something
                quality = file.get('quality', {})
                formats.append({
                    'format_id': 'direct',
                    'url': video_url,
                    'ext': determine_ext(video_url, file['type']),
                    'fps': int_or_none(quality.get('fps')),
                    'tbr': int_or_none(quality.get('bitrate')),
                    'width': int_or_none(quality.get('width')),
                    'height': int_or_none(quality.get('height')),
                })

        self._sort_formats(formats)

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


class TVPWebsiteIE(InfoExtractor):
    IE_NAME = 'tvp:series'
    _VALID_URL = r'https?://vod\.tvp\.pl/website/(?P<display_id>[^,]+),(?P<id>\d+)'

    _TESTS = [{
        # series
        'url': 'https://vod.tvp.pl/website/wspaniale-stulecie,17069012/video',
        'info_dict': {
            'id': '17069012',
        },
        'playlist_count': 312,
    }, {
        # film
        'url': 'https://vod.tvp.pl/website/krzysztof-krawczyk-cale-moje-zycie,51374466',
        'info_dict': {
            'id': '51374509',
            'ext': 'mp4',
            'title': 'Krzysztof Krawczyk – całe moje życie, Krzysztof Krawczyk – całe moje życie',
            'description': 'md5:2e80823f00f5fc263555482f76f8fa42',
            'age_limit': 12,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['TVPEmbed'],
    }, {
        'url': 'https://vod.tvp.pl/website/lzy-cennet,38678312',
        'only_matching': True,
    }]

    def _entries(self, display_id, playlist_id):
        url = 'https://vod.tvp.pl/website/%s,%s/video' % (display_id, playlist_id)
        for page_num in itertools.count(1):
            page = self._download_webpage(
                url, display_id, 'Downloading page %d' % page_num,
                query={'page': page_num})

            video_ids = orderedSet(re.findall(
                r'<a[^>]+\bhref=["\']/video/%s,[^,]+,(\d+)' % display_id,
                page))

            if not video_ids:
                break

            for video_id in video_ids:
                yield self.url_result(
                    'tvp:%s' % video_id, ie=TVPEmbedIE.ie_key(),
                    video_id=video_id)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id, playlist_id = mobj.group('display_id', 'id')
        return self.playlist_result(
            self._entries(display_id, playlist_id), playlist_id)

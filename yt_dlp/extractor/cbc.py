import functools
import re
import time
import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    js_to_json,
    jwt_decode_hs256,
    mimetype2ext,
    orderedSet,
    parse_age_limit,
    parse_iso8601,
    replace_extension,
    smuggle_url,
    strip_or_none,
    try_get,
    unified_timestamp,
    update_url,
    url_basename,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import require, traverse_obj, trim_str


class CBCIE(InfoExtractor):
    IE_NAME = 'cbc.ca'
    _VALID_URL = r'https?://(?:www\.)?cbc\.ca/(?!player/)(?:[^/]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        # with mediaId
        'url': 'http://www.cbc.ca/22minutes/videos/clips-season-23/don-cherry-play-offs',
        'md5': '97e24d09672fc4cf56256d6faa6c25bc',
        'info_dict': {
            'id': '2682904050',
            'ext': 'mp4',
            'title': 'Don Cherry – All-Stars',
            'description': 'Don Cherry has a bee in his bonnet about AHL player John Scott because that guy’s got heart.',
            'timestamp': 1454463000,
            'upload_date': '20160203',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada',
    }, {
        # with clipId, feed available via tpfeed.cbc.ca and feed.theplatform.com
        'url': 'http://www.cbc.ca/22minutes/videos/22-minutes-update/22-minutes-update-episode-4',
        'md5': '162adfa070274b144f4fdc3c3b8207db',
        'info_dict': {
            'id': '2414435309',
            'ext': 'mp4',
            'title': '22 Minutes Update: What Not To Wear Quebec',
            'description': "This week's latest Canadian top political story is What Not To Wear Quebec.",
            'upload_date': '20131025',
            'uploader': 'CBCC-NEW',
            'timestamp': 1382717907,
        },
        'skip': 'No longer available',
    }, {
        # with clipId, feed only available via tpfeed.cbc.ca
        'url': 'http://www.cbc.ca/archives/entry/1978-robin-williams-freestyles-on-90-minutes-live',
        'md5': '0274a90b51a9b4971fe005c63f592f12',
        'info_dict': {
            'id': '2487345465',
            'ext': 'mp4',
            'title': 'Robin Williams freestyles on 90 Minutes Live',
            'description': 'Wacky American comedian Robin Williams shows off his infamous "freestyle" comedic talents while being interviewed on CBC\'s 90 Minutes Live.',
            'upload_date': '19780210',
            'uploader': 'CBCC-NEW',
            'timestamp': 255977160,
        },
        'skip': '404 Not Found',
    }, {
        # multiple iframes
        'url': 'http://www.cbc.ca/natureofthings/blog/birds-eye-view-from-vancouvers-burrard-street-bridge-how-we-got-the-shot',
        'playlist': [{
            'md5': '377572d0b49c4ce0c9ad77470e0b96b4',
            'info_dict': {
                'id': '2680832926',
                'ext': 'mp4',
                'title': 'An Eagle\'s-Eye View Off Burrard Bridge',
                'description': 'Hercules the eagle flies from Vancouver\'s Burrard Bridge down to a nearby park with a mini-camera strapped to his back.',
                'upload_date': '20160201',
                'timestamp': 1454342820,
                'uploader': 'CBCC-NEW',
            },
        }, {
            'md5': '415a0e3f586113894174dfb31aa5bb1a',
            'info_dict': {
                'id': '2658915080',
                'ext': 'mp4',
                'title': 'Fly like an eagle!',
                'description': 'Eagle equipped with a mini camera flies from the world\'s tallest tower',
                'upload_date': '20150315',
                'timestamp': 1426443984,
                'uploader': 'CBCC-NEW',
            },
        }],
        'skip': 'Geo-restricted to Canada',
    }, {
        # multiple CBC.APP.Caffeine.initInstance(...)
        'url': 'http://www.cbc.ca/news/canada/calgary/dog-indoor-exercise-winter-1.3928238',
        'info_dict': {
            'title': 'Keep Rover active during the deep freeze with doggie pushups and other fun indoor tasks',  # FIXME: actual title includes " | CBC News"
            'id': 'dog-indoor-exercise-winter-1.3928238',
            'description': 'md5:c18552e41726ee95bd75210d1ca9194c',
        },
        'playlist_mincount': 6,
    }]

    @classmethod
    def suitable(cls, url):
        return False if CBCPlayerIE.suitable(url) else super().suitable(url)

    def _extract_player_init(self, player_init, display_id):
        player_info = self._parse_json(player_init, display_id, js_to_json)
        media_id = player_info.get('mediaId')
        if not media_id:
            clip_id = player_info['clipId']
            feed = self._download_json(
                f'http://tpfeed.cbc.ca/f/ExhSPC/vms_5akSXx4Ng_Zn?byCustomValue={{:mpsReleases}}{{{clip_id}}}',
                clip_id, fatal=False)
            if feed:
                media_id = try_get(feed, lambda x: x['entries'][0]['guid'], str)
            if not media_id:
                media_id = self._download_json(
                    'http://feed.theplatform.com/f/h9dtGB/punlNGjMlc1F?fields=id&byContent=byReleases%3DbyId%253D' + clip_id,
                    clip_id)['entries'][0]['id'].split('/')[-1]
        return self.url_result(f'cbcplayer:{media_id}', 'CBCPlayer', media_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        title = (self._og_search_title(webpage, default=None)
                 or self._html_search_meta('twitter:title', webpage, 'title', default=None)
                 or self._html_extract_title(webpage))
        entries = [
            self._extract_player_init(player_init, display_id)
            for player_init in re.findall(r'CBC\.APP\.Caffeine\.initInstance\(({.+?})\);', webpage)]
        media_ids = []
        for media_id_re in (
                r'<iframe[^>]+src="[^"]+?mediaId=(\d+)"',
                r'<div[^>]+\bid=["\']player-(\d+)',
                r'guid["\']\s*:\s*["\'](\d+)'):
            media_ids.extend(re.findall(media_id_re, webpage))
        entries.extend([
            self.url_result(f'cbcplayer:{media_id}', 'CBCPlayer', media_id)
            for media_id in orderedSet(media_ids)])
        return self.playlist_result(
            entries, display_id, strip_or_none(title),
            self._og_search_description(webpage))


class CBCPlayerIE(InfoExtractor):
    IE_NAME = 'cbc.ca:player'
    _VALID_URL = r'(?:cbcplayer:|https?://(?:www\.)?cbc\.ca/(?:player/play/(?:video/)?|i/caffeine/syndicate/\?mediaId=))(?P<id>(?:\d\.)?\d+)'
    _GEO_COUNTRIES = ['CA']
    _TESTS = [{
        'url': 'http://www.cbc.ca/player/play/2683190193',
        'md5': '64d25f841ddf4ddb28a235338af32e2c',
        'info_dict': {
            'id': '2683190193',
            'ext': 'mp4',
            'title': 'Gerry Runs a Sweat Shop',
            'description': 'md5:b457e1c01e8ff408d9d801c1c2cd29b0',
            'timestamp': 1455071400,
            'upload_date': '20160210',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada and no longer available',
    }, {
        'url': 'http://www.cbc.ca/i/caffeine/syndicate/?mediaId=2657631896',
        'md5': 'e5e708c34ae6fca156aafe17c43e8b75',
        'info_dict': {
            'id': '2657631896',
            'ext': 'mp3',
            'title': 'CBC Montreal is organizing its first ever community hackathon!',
            'description': 'md5:dd3b692f0a139b0369943150bd1c46a9',
            'timestamp': 1425704400,
            'upload_date': '20150307',
            'thumbnail': 'https://i.cbc.ca/ais/1.2985700,1717262248558/full/max/0/default.jpg',
            'chapters': [],
            'duration': 494.811,
            'categories': ['All in a Weekend Montreal'],
            'tags': 'count:11',
            'location': 'Quebec',
            'series': 'All in a Weekend Montreal',
            'season': 'Season 2015',
            'season_number': 2015,
            'media_type': 'Excerpt',
            'genres': ['Other'],
        },
    }, {
        'url': 'http://www.cbc.ca/i/caffeine/syndicate/?mediaId=2164402062',
        'info_dict': {
            'id': '2164402062',
            'ext': 'mp4',
            'title': 'Cancer survivor four times over',
            'description': 'Tim Mayer has beaten three different forms of cancer four times in five years.',
            'timestamp': 1320410746,
            'upload_date': '20111104',
            'thumbnail': 'https://i.cbc.ca/ais/1.1711287,1717139372111/full/max/0/default.jpg',
            'chapters': [],
            'duration': 186.867,
            'series': 'CBC News: Windsor at 6:00',
            'categories': ['Windsor'],
            'location': 'Windsor',
            'tags': ['Cancer', 'News/Canada/Windsor', 'Windsor'],
            'media_type': 'Excerpt',
            'genres': ['News'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Redirected from http://www.cbc.ca/player/AudioMobile/All%20in%20a%20Weekend%20Montreal/ID/2657632011/
        'url': 'https://www.cbc.ca/player/play/1.2985700',
        'md5': 'e5e708c34ae6fca156aafe17c43e8b75',
        'info_dict': {
            'id': '1.2985700',
            'ext': 'mp3',
            'title': 'CBC Montreal is organizing its first ever community hackathon!',
            'description': 'The modern technology we tend to depend on so heavily, is never without it\'s share of hiccups and headaches. Next weekend - CBC Montreal will be getting members of the public for its first Hackathon.',
            'timestamp': 1425704400,
            'upload_date': '20150307',
            'thumbnail': 'https://i.cbc.ca/ais/1.2985700,1717262248558/full/max/0/default.jpg',
            'chapters': [],
            'duration': 494.811,
            'categories': ['All in a Weekend Montreal'],
            'tags': 'count:11',
            'location': 'Quebec',
            'series': 'All in a Weekend Montreal',
            'season': 'Season 2015',
            'season_number': 2015,
            'media_type': 'Excerpt',
            'genres': ['Other'],
        },
    }, {
        'url': 'https://www.cbc.ca/player/play/1.1711287',
        'info_dict': {
            'id': '1.1711287',
            'ext': 'mp4',
            'title': 'Cancer survivor four times over',
            'description': 'Tim Mayer has beaten three different forms of cancer four times in five years.',
            'timestamp': 1320410746,
            'upload_date': '20111104',
            'thumbnail': 'https://i.cbc.ca/ais/1.1711287,1717139372111/full/max/0/default.jpg',
            'chapters': [],
            'duration': 186.867,
            'series': 'CBC News: Windsor at 6:00',
            'categories': ['Windsor'],
            'location': 'Windsor',
            'tags': ['Cancer', 'News/Canada/Windsor', 'Windsor'],
            'media_type': 'Excerpt',
            'genres': ['News'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Has subtitles
        # These broadcasts expire after ~1 month, can find new test URL here:
        # https://www.cbc.ca/player/news/TV%20Shows/The%20National/Latest%20Broadcast
        'url': 'https://www.cbc.ca/player/play/video/9.6424403',
        'md5': '8025909eaffcf0adf59922904def9a5e',
        'info_dict': {
            'id': '9.6424403',
            'ext': 'mp4',
            'title': 'The National | N.W.T. wildfire emergency',
            'description': 'md5:ada33d36d1df69347ed575905bfd496c',
            'timestamp': 1718589600,
            'duration': 2692.833,
            'subtitles': {
                'en-US': [{
                    'name': 'English Captions',
                    'url': 'https://cbchls.akamaized.net/delivery/news-shows/2024/06/17/NAT_JUN16-00-55-00/NAT_JUN16_cc.vtt',
                }],
            },
            'thumbnail': 'https://i.cbc.ca/ais/6272b5c6-5e78-4c05-915d-0e36672e33d1,1714756287822/full/max/0/default.jpg',
            'chapters': 'count:5',
            'upload_date': '20240617',
            'categories': ['News', 'The National', 'The National Latest Broadcasts'],
            'series': 'The National - Full Show',
            'tags': ['The National'],
            'location': 'Canada',
            'media_type': 'Full Program',
            'genres': ['News'],
        },
    }, {
        'url': 'https://www.cbc.ca/player/play/video/1.7194274',
        'md5': '188b96cf6bdcb2540e178a6caa957128',
        'info_dict': {
            'id': '1.7194274',
            'ext': 'mp4',
            'title': '#TheMoment a rare white spirit moose was spotted in Alberta',
            'description': 'md5:18ae269a2d0265c5b0bbe4b2e1ac61a3',
            'timestamp': 1714788791,
            'duration': 77.678,
            'subtitles': {'eng': [{'ext': 'vtt', 'protocol': 'm3u8_native'}]},
            'thumbnail': 'https://i.cbc.ca/ais/1.7194274,1717224990425/full/max/0/default.jpg',
            'chapters': [],
            'categories': 'count:3',
            'series': 'The National',
            'tags': 'count:17',
            'location': 'Canada',
            'media_type': 'Excerpt',
            'upload_date': '20240504',
            'genres': ['News'],
        },
    }, {
        'url': 'https://www.cbc.ca/player/play/video/9.6427282',
        'info_dict': {
            'id': '9.6427282',
            'ext': 'mp4',
            'title': 'Men\'s Soccer - Argentina vs Morocco',
            'description': 'Argentina faces Morocco on the football pitch at Saint Etienne Stadium.',
            'series': 'CBC Sports',
            'media_type': 'Event Coverage',
            'thumbnail': 'https://i.cbc.ca/ais/a4c5c0c2-99fa-4bd3-8061-5a63879c1b33,1718828053500/full/max/0/default.jpg',
            'timestamp': 1721825400.0,
            'upload_date': '20240724',
            'duration': 10568.0,
            'chapters': [],
            'genres': [],
            'tags': ['2024 Paris Olympic Games'],
            'categories': ['Olympics Summer Soccer', 'Summer Olympics Replays', 'Summer Olympics Soccer Replays'],
            'location': 'Canada',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.cbc.ca/player/play/video/9.6459530',
        'md5': '6c1bb76693ab321a2e99c347a1d5ecbc',
        'info_dict': {
            'id': '9.6459530',
            'ext': 'mp4',
            'title': 'Parts of Jasper incinerated as wildfire rages',
            'description': 'md5:6f1caa8d128ad3f629257ef5fecf0962',
            'series': 'The National',
            'media_type': 'Excerpt',
            'thumbnail': 'https://i.cbc.ca/ais/507c0086-31a2-494d-96e4-bffb1048d045,1721953984375/full/max/0/default.jpg',
            'timestamp': 1721964091.012,
            'upload_date': '20240726',
            'duration': 952.285,
            'chapters': [],
            'genres': [],
            'tags': 'count:23',
            'categories': ['News (FAST)', 'News', 'The National', 'TV News Shows', 'The National '],
        },
    }, {
        'url': 'https://www.cbc.ca/player/play/video/9.6420651',
        'md5': '71a850c2c6ee5e912de169f5311bb533',
        'info_dict': {
            'id': '9.6420651',
            'ext': 'mp4',
            'title': 'Is it a breath of fresh air? Measuring air quality in Edmonton',
            'description': 'md5:3922b92cc8b69212d739bd9dd095b1c3',
            'series': 'CBC News Edmonton',
            'media_type': 'Excerpt',
            'thumbnail': 'https://i.cbc.ca/ais/73c4ab9c-7ad4-46ee-bb9b-020fdc01c745,1718214547576/full/max/0/default.jpg',
            'timestamp': 1718220065.768,
            'upload_date': '20240612',
            'duration': 286.086,
            'chapters': [],
            'genres': ['News'],
            'categories': ['News', 'Edmonton'],
            'tags': 'count:7',
            'location': 'Edmonton',
        },
    }, {
        'url': 'cbcplayer:1.7159484',
        'only_matching': True,
    }, {
        'url': 'cbcplayer:2164402062',
        'only_matching': True,
    }, {
        'url': 'http://www.cbc.ca/player/play/2657631896',
        'only_matching': True,
    }]

    def _parse_param(self, asset_data, name):
        return traverse_obj(asset_data, ('params', lambda _, v: v['name'] == name, 'value', {str}, any))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://www.cbc.ca/player/play/{video_id}', video_id)
        data = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', video_id)['video']['currentClip']
        assets = traverse_obj(
            data, ('media', 'assets', lambda _, v: url_or_none(v['key']) and v['type']))

        if not assets and (media_id := traverse_obj(data, ('mediaId', {str}))):
            # XXX: Deprecated; CBC is migrating off of ThePlatform
            return {
                '_type': 'url_transparent',
                'ie_key': 'ThePlatform',
                'url': smuggle_url(
                    f'http://link.theplatform.com/s/ExhSPC/media/guid/2655402169/{media_id}?mbr=true&formats=MPEG4,FLV,MP3', {
                        'force_smil_url': True,
                    }),
                'id': media_id,
                '_format_sort_fields': ('res', 'proto'),  # Prioritize direct http formats over HLS
            }

        is_live = traverse_obj(data, ('media', 'streamType', {str})) == 'Live'
        formats, subtitles = [], {}

        for sub in traverse_obj(data, ('media', 'textTracks', lambda _, v: url_or_none(v['src']))):
            subtitles.setdefault(sub.get('language') or 'und', []).append({
                'url': sub['src'],
                'name': sub.get('label'),
            })

        for asset in assets:
            asset_key = asset['key']
            asset_type = asset['type']
            if asset_type != 'medianet':
                self.report_warning(f'Skipping unsupported asset type "{asset_type}": {asset_key}')
                continue
            asset_data = self._download_json(asset_key, video_id, f'Downloading {asset_type} JSON')
            ext = mimetype2ext(self._parse_param(asset_data, 'contentType'))
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    asset_data['url'], video_id, 'mp4', m3u8_id='hls', live=is_live)
                formats.extend(fmts)
                # Avoid slow/error-prone webvtt-over-m3u8 if direct https vtt is available
                if not subtitles:
                    self._merge_subtitles(subs, target=subtitles)
                if is_live or not fmts:
                    continue
                # Check for direct https mp4 format
                best_video_fmt = traverse_obj(fmts, (
                    lambda _, v: v.get('vcodec') != 'none' and v['tbr'], all,
                    {functools.partial(sorted, key=lambda x: x['tbr'])}, -1, {dict})) or {}
                base_url = self._search_regex(
                    r'(https?://[^?#]+?/)hdntl=', best_video_fmt.get('url'), 'base url', default=None)
                if not base_url or '/live/' in base_url:
                    continue
                mp4_url = base_url + replace_extension(url_basename(best_video_fmt['url']), 'mp4')
                if self._request_webpage(
                        HEADRequest(mp4_url), video_id, 'Checking for https format',
                        errnote=False, fatal=False):
                    formats.append({
                        **best_video_fmt,
                        'url': mp4_url,
                        'format_id': 'https-mp4',
                        'protocol': 'https',
                        'manifest_url': None,
                        'acodec': None,
                    })
            else:
                formats.append({
                    'url': asset_data['url'],
                    'ext': ext,
                    'vcodec': 'none' if self._parse_param(asset_data, 'mediaType') == 'audio' else None,
                })

        chapters = traverse_obj(data, (
            'media', 'chapters', lambda _, v: float(v['startTime']) is not None, {
                'start_time': ('startTime', {float_or_none(scale=1000)}),
                'end_time': ('endTime', {float_or_none(scale=1000)}),
                'title': ('name', {str}),
            }))
        # Filter out pointless single chapters with start_time==0 and no end_time
        if len(chapters) == 1 and not (chapters[0].get('start_time') or chapters[0].get('end_time')):
            chapters = []

        return {
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str.strip}),
                'thumbnail': ('image', 'url', {url_or_none}, {update_url(query=None)}),
                'timestamp': ('publishedAt', {float_or_none(scale=1000)}),
                'media_type': ('media', 'clipType', {str}),
                'series': ('showName', {str}),
                'season_number': ('media', 'season', {int_or_none}),
                'duration': ('media', 'duration', {float_or_none}, {lambda x: None if is_live else x}),
                'location': ('media', 'region', {str}),
                'tags': ('tags', ..., 'name', {str}),
                'genres': ('media', 'genre', all),
                'categories': ('categories', ..., 'name', {str}),
            }),
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'chapters': chapters,
            'is_live': is_live,
        }


class CBCPlayerPlaylistIE(InfoExtractor):
    IE_NAME = 'cbc.ca:player:playlist'
    _VALID_URL = r'https?://(?:www\.)?cbc\.ca/(?:player/)(?!play/)(?P<id>[^?#]+)'
    _TESTS = [{
        'url': 'https://www.cbc.ca/player/news/TV%20Shows/The%20National/Latest%20Broadcast',
        'playlist_mincount': 25,
        'info_dict': {
            'id': 'news/tv shows/the national/latest broadcast',
        },
    }, {
        'url': 'https://www.cbc.ca/player/news/Canada/North',
        'playlist_mincount': 25,
        'info_dict': {
            'id': 'news/canada/north',
        },
    }]

    def _real_extract(self, url):
        playlist_id = urllib.parse.unquote(self._match_id(url)).lower()
        webpage = self._download_webpage(url, playlist_id)
        json_content = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', playlist_id)

        def entries():
            for video_id in traverse_obj(json_content, (
                'video', 'clipsByCategory', lambda k, _: k.lower() == playlist_id, 'items', ..., 'id',
            )):
                yield self.url_result(f'https://www.cbc.ca/player/play/{video_id}', CBCPlayerIE)

        return self.playlist_result(entries(), playlist_id)


class CBCGemBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'cbcgem'
    _GEO_COUNTRIES = ['CA']

    def _call_show_api(self, item_id, display_id=None):
        return self._download_json(
            f'https://services.radio-canada.ca/ott/catalog/v2/gem/show/{item_id}',
            display_id or item_id, query={'device': 'web'})

    def _extract_item_info(self, item_info):
        episode_number = None
        title = traverse_obj(item_info, ('title', {str}))
        if title and (mobj := re.match(r'(?P<episode>\d+)\. (?P<title>.+)', title)):
            episode_number = int_or_none(mobj.group('episode'))
            title = mobj.group('title')

        return {
            'episode_number': episode_number,
            **traverse_obj(item_info, {
                'id': ('url', {str}),
                'episode_id': ('url', {str}),
                'description': ('description', {str}),
                'thumbnail': ('images', 'card', 'url', {url_or_none}, {update_url(query=None)}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'duration': ('metadata', 'duration', {int_or_none}),
                'release_timestamp': ('metadata', 'airDate', {unified_timestamp}),
                'timestamp': ('metadata', 'availabilityDate', {unified_timestamp}),
                'age_limit': ('metadata', 'rating', {trim_str(start='C')}, {parse_age_limit}),
            }),
            'episode': title,
            'title': title,
        }


class CBCGemIE(CBCGemBaseIE):
    IE_NAME = 'gem.cbc.ca'
    _VALID_URL = r'https?://gem\.cbc\.ca/(?:media/)?(?P<id>[0-9a-z-]+/s(?P<season>[0-9]+)[a-z][0-9]+)'
    _TESTS = [{
        # This is a normal, public, TV show video
        'url': 'https://gem.cbc.ca/media/schitts-creek/s06e01',
        'info_dict': {
            'id': 'schitts-creek/s06e01',
            'ext': 'mp4',
            'title': 'Smoke Signals',
            'description': 'md5:929868d20021c924020641769eb3e7f1',
            'thumbnail': r're:https://images\.radio-canada\.ca/[^#?]+/cbc_schitts_creek_season_06e01_thumbnail_v01\.jpg',
            'duration': 1324,
            'genres': ['Comédie et humour'],
            'series': 'Schitt\'s Creek',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Smoke Signals',
            'episode_number': 1,
            'episode_id': 'schitts-creek/s06e01',
            'upload_date': '20210618',
            'timestamp': 1623974400,
            'release_date': '20200107',
            'release_timestamp': 1578355200,
            'age_limit': 14,
        },
        'params': {'format': 'bv'},
    }, {
        # This video requires an account in the browser, but works fine in yt-dlp
        'url': 'https://gem.cbc.ca/media/schitts-creek/s01e01',
        'info_dict': {
            'id': 'schitts-creek/s01e01',
            'ext': 'mp4',
            'title': 'The Cup Runneth Over',
            'description': 'md5:9bca14ea49ab808097530eb05a29e797',
            'thumbnail': r're:https://images\.radio-canada\.ca/[^#?]+/cbc_schitts_creek_season_01e01_thumbnail_v01\.jpg',
            'series': 'Schitt\'s Creek',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'The Cup Runneth Over',
            'episode_id': 'schitts-creek/s01e01',
            'duration': 1308,
            'genres': ['Comédie et humour'],
            'upload_date': '20210617',
            'timestamp': 1623888000,
            'release_date': '20151123',
            'release_timestamp': 1448236800,
            'age_limit': 14,
        },
        'params': {'format': 'bv'},
    }, {
        'url': 'https://gem.cbc.ca/nadiyas-family-favourites/s01e01',
        'only_matching': True,
    }]

    _CLIENT_ID = 'fc05b0ee-3865-4400-a3cc-3da82c330c23'
    _refresh_token = None
    _access_token = None
    _claims_token = None

    @functools.cached_property
    def _ropc_settings(self):
        return self._download_json(
            'https://services.radio-canada.ca/ott/catalog/v1/gem/settings', None,
            'Downloading site settings', query={'device': 'web'})['identityManagement']['ropc']

    def _is_jwt_expired(self, token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def _call_oauth_api(self, oauth_data, note='Refreshing access token'):
        response = self._download_json(
            self._ropc_settings['url'], None, note, data=urlencode_postdata({
                'client_id': self._CLIENT_ID,
                **oauth_data,
                'scope': self._ropc_settings['scopes'],
            }))
        self._refresh_token = response['refresh_token']
        self._access_token = response['access_token']
        self.cache.store(self._NETRC_MACHINE, 'token_data', [self._refresh_token, self._access_token])

    def _perform_login(self, username, password):
        if not self._refresh_token:
            self._refresh_token, self._access_token = self.cache.load(
                self._NETRC_MACHINE, 'token_data', default=[None, None])

        if self._refresh_token and self._access_token:
            self.write_debug('Using cached refresh token')
            if not self._claims_token:
                self._claims_token = self.cache.load(self._NETRC_MACHINE, 'claims_token')
            return

        try:
            self._call_oauth_api({
                'grant_type': 'password',
                'username': username,
                'password': password,
            }, note='Logging in')
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError('Invalid username and/or password', expected=True)
            raise

    def _fetch_access_token(self):
        if self._is_jwt_expired(self._access_token):
            try:
                self._call_oauth_api({
                    'grant_type': 'refresh_token',
                    'refresh_token': self._refresh_token,
                })
            except ExtractorError:
                self._refresh_token, self._access_token = None, None
                self.cache.store(self._NETRC_MACHINE, 'token_data', [None, None])
                self.report_warning('Refresh token has been invalidated; retrying with credentials')
                self._perform_login(*self._get_login_info())

        return self._access_token

    def _fetch_claims_token(self):
        if not self._get_login_info()[0]:
            return None

        if not self._claims_token or self._is_jwt_expired(self._claims_token):
            self._claims_token = self._download_json(
                'https://services.radio-canada.ca/ott/subscription/v2/gem/Subscriber/profile',
                None, 'Downloading claims token', query={'device': 'web'},
                headers={'Authorization': f'Bearer {self._fetch_access_token()}'})['claimsToken']
            self.cache.store(self._NETRC_MACHINE, 'claims_token', self._claims_token)
        else:
            self.write_debug('Using cached claims token')

        return self._claims_token

    def _real_extract(self, url):
        video_id, season_number = self._match_valid_url(url).group('id', 'season')
        video_info = self._call_show_api(video_id)
        item_info = traverse_obj(video_info, (
            'content', ..., 'lineups', ..., 'items',
            lambda _, v: v['url'] == video_id, any, {require('item info')}))

        headers = {}
        if claims_token := self._fetch_claims_token():
            headers['x-claims-token'] = claims_token

        m3u8_info = self._download_json(
            'https://services.radio-canada.ca/media/validation/v2/',
            video_id, headers=headers, query={
                'appCode': 'gem',
                'connectionType': 'hd',
                'deviceType': 'ipad',
                'multibitrate': 'true',
                'output': 'json',
                'tech': 'hls',
                'manifestVersion': '2',
                'manifestType': 'desktop',
                'idMedia': item_info['idMedia'],
            })

        if m3u8_info.get('errorCode') == 1:
            self.raise_geo_restricted(countries=['CA'])
        elif m3u8_info.get('errorCode') == 35:
            self.raise_login_required(method='password')
        elif m3u8_info.get('errorCode') != 0:
            raise ExtractorError(f'{self.IE_NAME} said: {m3u8_info.get("errorCode")} - {m3u8_info.get("message")}')

        formats = self._extract_m3u8_formats(
            m3u8_info['url'], video_id, 'mp4', m3u8_id='hls', query={'manifestType': ''})
        self._remove_duplicate_formats(formats)

        for fmt in formats:
            if fmt.get('vcodec') == 'none':
                if fmt.get('ext') is None:
                    fmt['ext'] = 'm4a'
                if fmt.get('acodec') is None:
                    fmt['acodec'] = 'mp4a.40.2'

                # Put described audio at the beginning of the list, so that it
                # isn't chosen by default, as most people won't want it.
                if 'descriptive' in fmt['format_id'].lower():
                    fmt['preference'] = -2

        return {
            'season_number': int_or_none(season_number),
            **traverse_obj(video_info, {
                'series': ('title', {str}),
                'season_number': ('structuredMetadata', 'partofSeason', 'seasonNumber', {int_or_none}),
                'genres': ('structuredMetadata', 'genre', ..., {str}),
            }),
            **self._extract_item_info(item_info),
            'id': video_id,
            'episode_id': video_id,
            'formats': formats,
        }


class CBCGemPlaylistIE(CBCGemBaseIE):
    IE_NAME = 'gem.cbc.ca:playlist'
    _VALID_URL = r'https?://gem\.cbc\.ca/(?:media/)?(?P<id>(?P<show>[0-9a-z-]+)/s(?P<season>[0-9]+))/?(?:[?#]|$)'
    _TESTS = [{
        # TV show playlist, all public videos
        'url': 'https://gem.cbc.ca/media/schitts-creek/s06',
        'playlist_count': 16,
        'info_dict': {
            'id': 'schitts-creek/s06',
            'title': 'Season 6',
            'series': 'Schitt\'s Creek',
            'season_number': 6,
            'season': 'Season 6',
        },
    }, {
        'url': 'https://gem.cbc.ca/schitts-creek/s06',
        'only_matching': True,
    }]

    def _entries(self, season_info):
        for episode in traverse_obj(season_info, ('items', lambda _, v: v['url'])):
            yield self.url_result(
                f'https://gem.cbc.ca/media/{episode["url"]}', CBCGemIE,
                **self._extract_item_info(episode))

    def _real_extract(self, url):
        season_id, show, season = self._match_valid_url(url).group('id', 'show', 'season')
        show_info = self._call_show_api(show, display_id=season_id)
        season_info = traverse_obj(show_info, (
            'content', ..., 'lineups',
            lambda _, v: v['seasonNumber'] == int(season), any, {require('season info')}))

        return self.playlist_result(
            self._entries(season_info), season_id,
            **traverse_obj(season_info, {
                'title': ('title', {str}),
                'season': ('title', {str}),
                'season_number': ('seasonNumber', {int_or_none}),
            }), series=traverse_obj(show_info, ('title', {str})))


class CBCGemLiveIE(InfoExtractor):
    IE_NAME = 'gem.cbc.ca:live'
    _VALID_URL = r'https?://gem\.cbc\.ca/live(?:-event)?/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://gem.cbc.ca/live/920604739687',
            'info_dict': {
                'title': 'Ottawa',
                'description': 'The live TV channel and local programming from Ottawa',
                'thumbnail': 'https://thumbnails.cbc.ca/maven_legacy/thumbnails/CBC_OTT_VMS/Live_Channel_Static_Images/Ottawa_2880x1620.jpg',
                'live_status': 'is_live',
                'id': 'AyqZwxRqh8EH',
                'ext': 'mp4',
                'release_timestamp': 1492106160,
                'release_date': '20170413',
                'uploader': 'CBCC-NEW',
            },
            'skip': 'Live might have ended',
        },
        {
            'url': 'https://gem.cbc.ca/live/44',
            'info_dict': {
                'id': '44',
                'ext': 'mp4',
                'is_live': True,
                'title': r're:^Ottawa [0-9\-: ]+',
                'description': 'The live TV channel and local programming from Ottawa',
                'live_status': 'is_live',
                'thumbnail': r're:https://images.gem.cbc.ca/v1/cbc-gem/live/.*',
            },
            'params': {'skip_download': True},
            'skip': 'Live might have ended',
        },
        {
            'url': 'https://gem.cbc.ca/live-event/10835',
            'info_dict': {
                'id': '10835',
                'ext': 'mp4',
                'is_live': True,
                'title': r're:^The National \| Biden’s trip wraps up, Paltrow testifies, Bird flu [0-9\-: ]+',
                'description': 'March 24, 2023 | President Biden’s Ottawa visit ends with big pledges from both countries. Plus, Gwyneth Paltrow testifies in her ski collision trial.',
                'live_status': 'is_live',
                'thumbnail': r're:https://images.gem.cbc.ca/v1/cbc-gem/live/.*',
                'release_timestamp': 1679706000,
                'release_date': '20230325',
            },
            'params': {'skip_download': True},
            'skip': 'Live might have ended',
        },
        {   # event replay (medianetlive)
            'url': 'https://gem.cbc.ca/live-event/42314',
            'md5': '297a9600f554f2258aed01514226a697',
            'info_dict': {
                'id': '42314',
                'ext': 'mp4',
                'live_status': 'was_live',
                'title': 'Women\'s Soccer - Canada vs New Zealand',
                'description': 'md5:36200e5f1a70982277b5a6ecea86155d',
                'thumbnail': r're:https://.+default\.jpg',
                'release_timestamp': 1721917200,
                'release_date': '20240725',
            },
            'params': {'skip_download': True},
            'skip': 'Replay might no longer be available',
        },
        {   # event replay (medianetlive)
            'url': 'https://gem.cbc.ca/live-event/43273',
            'only_matching': True,
        },
    ]
    _GEO_COUNTRIES = ['CA']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_info = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['data']

        # Three types of video_info JSON: info in root, freeTv stream/item, event replay
        if not video_info.get('formattedIdMedia'):
            if traverse_obj(video_info, ('event', 'key')) == video_id:
                video_info = video_info['event']
            else:
                video_info = traverse_obj(video_info, (
                    ('freeTv', ('streams', ...)), 'items',
                    lambda _, v: v['key'].partition('-')[0] == video_id, any)) or {}

        video_stream_id = video_info.get('formattedIdMedia')
        if not video_stream_id:
            raise ExtractorError(
                'Couldn\'t find video metadata, maybe this livestream is now offline', expected=True)

        live_status = 'was_live' if video_info.get('isVodEnabled') else 'is_live'
        release_timestamp = traverse_obj(video_info, ('airDate', {parse_iso8601}))

        if live_status == 'is_live' and release_timestamp and release_timestamp > time.time():
            formats = []
            live_status = 'is_upcoming'
            self.raise_no_formats('This livestream has not yet started', expected=True)
        else:
            stream_data = self._download_json(
                'https://services.radio-canada.ca/media/validation/v2/', video_id, query={
                    'appCode': 'medianetlive',
                    'connectionType': 'hd',
                    'deviceType': 'ipad',
                    'idMedia': video_stream_id,
                    'multibitrate': 'true',
                    'output': 'json',
                    'tech': 'hls',
                    'manifestType': 'desktop',
                })
            formats = self._extract_m3u8_formats(
                stream_data['url'], video_id, 'mp4', live=live_status == 'is_live')

        return {
            'id': video_id,
            'formats': formats,
            'live_status': live_status,
            'release_timestamp': release_timestamp,
            **traverse_obj(video_info, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('images', 'card', 'url'),
            }),
        }

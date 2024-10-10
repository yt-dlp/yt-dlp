import json
import random
import re
import urllib.parse

from yt_dlp.utils.traversal import traverse_obj

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    merge_dicts,
    orderedSet,
    str_or_none,
    try_call,
    unified_timestamp,
    url_or_none,
)


class NPOIE(InfoExtractor):
    IE_NAME = 'npo'
    IE_DESC = 'npo.nl and ntr.nl'
    _VALID_URL = r'''(?x)
                    (?:
                        npo:|
                        https?://
                            (?:www\.)?
                            (?:
                                (?:ntr|npostart)\.nl/(?:[^/]+/){2,}|
                                omroepwnl\.nl/video/fragment/[^/]+__|
                                (?:zapp|npo3)\.nl/(?:[^/]+/){2,}
                            )
                        )
                        (?P<id>[^/?#]+)
                '''

    _TESTS = [{
        'url': 'http://www.ntr.nl/Aap-Poot-Pies/27/detail/Aap-poot-pies/VPWON_1233944',
        'info_dict': {
            'id': 'VPWON_1233944',
            'ext': 'mp4',
            'title': 'Aap, poot, pies',
            'description': 'md5:4b46b1b9553b4c036a04d2a532a137e6',
            'upload_date': '20150508',
            'duration': 599,
            'episode': 'Aap, poot, pies',
            'thumbnail': 'https://images.poms.omroep.nl/image/s1280/c1280x720/608118.jpg',
            'timestamp': 1431064200,
            'series': 'Aap, poot, pies',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://npo.nl/npo3/3onderzoekt/16-09-2015/VPWON_1239870',
        'only_matching': True,
    }, {
        'url': 'https://npo.nl/npo3/the-genius/21-11-2022/VPWON_1341105',
        'info_dict': {
            'id': 'VPWON_1341105',
            'ext': 'mp4',
            'duration': 2658,
            'series': 'The Genius',
            'description': 'md5:db02f1456939ca63f7c408f858044e94',
            'title': 'The Genius',
            'timestamp': 1669062000,
            'creator': 'NED3',
            'episode': 'The Genius',
            'thumbnail': 'https://images.npo.nl/tile/1280x720/1827650.jpg',
            'episode_number': 8,
            'upload_date': '20221121',
        },
        'params': {
            'skip_download': True,
        },
    }]

    @classmethod
    def suitable(cls, url):
        return (False if any(ie.suitable(url)
                for ie in (NPOStartIE, NPORadioIE, NPORadioFragmentIE))
                else super().suitable(url))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if urllib.parse.urlparse(url).netloc in ['www.ntr.nl', 'ntr.nl']:
            player = self._download_json(
                f'https://www.ntr.nl/ajax/player/embed/{video_id}', video_id,
                'Downloading player JSON', query={
                    'parameters[elementId]': f'npo{random.randint(0, 999)}',
                    'parameters[sterReferralUrl]': url,
                    'parameters[autoplay]': 0,
                })
        else:
            # token = self._download_json(
            #     'https://rs.vpro.nl/v3/api/npoplayer/token', video_id,
            #     'Downloading token', headers={
            #        'Content-Type': 'application/json',
            #     }, data=json.dumps({
            #         'mid': video_id,
            #     }).encode())['token']
            player = self._download_json(
                'https://prod.npoplayer.nl/stream-link', video_id,
                'Downloading player JSON', data=json.dumps({
                    'profileName': 'dash',
                    'drmType': 'fairplay',
                    'referrerUrl': 'https://www.vpro.nl/programmas/droomdorp.html',
                    'ster': {
                        'identifier': 'npo-app-desktop',
                        'deviceType': 1,
                        'player': 'web',
                    },
                }), headers={
                    'x-xsrf-token': try_call(lambda: urllib.parse.unquote(
                        self._get_cookies('https://www.npostart.nl')['XSRF-TOKEN'].value)),
                })

        player_token = player['token']

        drm = False
        format_urls = set()
        formats = []
        for profile in ('hls', 'dash-widevine', 'dash-playready', 'smooth'):
            streams = self._download_json(
                f'https://start-player.npo.nl/video/{video_id}/streams',
                video_id, f'Downloading {profile} profile JSON', fatal=False,
                query={
                    'profile': profile,
                    'quality': 'npoplus',
                    'tokenId': player_token,
                    'streamType': 'broadcast',
                }, data=b'')  # endpoint requires POST
            if not streams:
                continue
            stream = streams.get('stream')
            if not isinstance(stream, dict):
                continue
            stream_url = url_or_none(stream.get('src'))
            if not stream_url or stream_url in format_urls:
                continue
            format_urls.add(stream_url)
            if stream.get('protection') is not None or stream.get('keySystemOptions') is not None:
                drm = True
                continue
            stream_type = stream.get('type')
            stream_ext = determine_ext(stream_url)
            if stream_type == 'application/dash+xml' or stream_ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    stream_url, video_id, mpd_id='dash', fatal=False))
            elif stream_type == 'application/vnd.apple.mpegurl' or stream_ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    stream_url, video_id, ext='mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', fatal=False))
            elif re.search(r'\.isml?/Manifest', stream_url):
                formats.extend(self._extract_ism_formats(
                    stream_url, video_id, ism_id='mss', fatal=False))
            else:
                formats.append({
                    'url': stream_url,
                })

        if not formats:
            if not self.get_param('allow_unplayable_formats') and drm:
                self.report_drm(video_id)

        info = {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }

        embed_url = url_or_none(player.get('embedUrl'))
        if embed_url:
            webpage = self._download_webpage(
                embed_url, video_id, 'Downloading embed page', fatal=False)
            if webpage:
                video = self._parse_json(
                    self._search_regex(
                        r'\bvideo\s*=\s*({.+?})\s*;', webpage, 'video',
                        default='{}'), video_id)
                if video:
                    title = video.get('episodeTitle')
                    subtitles = {}
                    subtitles_list = video.get('subtitles')
                    if isinstance(subtitles_list, list):
                        for cc in subtitles_list:
                            cc_url = url_or_none(cc.get('src'))
                            if not cc_url:
                                continue
                            lang = str_or_none(cc.get('language')) or 'nl'
                            subtitles.setdefault(lang, []).append({
                                'url': cc_url,
                            })
                    return merge_dicts({
                        'title': title,
                        'description': video.get('description'),
                        'thumbnail': url_or_none(
                            video.get('still_image_url') or video.get('orig_image_url')),
                        'duration': int_or_none(video.get('duration')),
                        'timestamp': unified_timestamp(video.get('broadcastDate')),
                        'creator': video.get('channel'),
                        'series': video.get('title'),
                        'episode': title,
                        'episode_number': int_or_none(video.get('episodeNumber')),
                        'subtitles': subtitles,
                    }, info)

        return info


class NPOStartIE(InfoExtractor):
    IE_NAME = 'npo.nl:start'
    _VALID_URL = r'https?://(?:www\.)?npo\.nl/start/serie/(?:(?:[a-z]|-|\d)+/){2}(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://npo.nl/start/serie/vpro-tegenlicht/seizoen-11/zwart-geld-de-toekomst-komt-uit-afrika/afspelen',
        'md5': '8c30593a81ac80d65b531eaf2a92ac02',
        'info_dict': {
            'id': 'VPWON_1169289',
            'ext': 'mp4',
            'title': 'Zwart geld: de toekomst komt uit Afrika',
            'description': 'md5:d6476bceb17a8c103c76c3b708f05dd1',
            'duration': 3000,
            'uploader_id': 'NED2',
            'series': 'VPRO Tegenlicht',
            'timestamp': 1361822340,
            'thumbnail': 'https://assets-start.npo.nl/resources/2023/06/30/d9879593-1944-4249-990c-1561dac14d8e.jpg',
            'episode': 'Zwart geld: de toekomst komt uit Afrika',
            'episode_number': 18,
            'channel_id': 'NED2',
            'genres': [],
            'release_date': '20130225',
            'release_timestamp': 1361822340,
            'season': 'Season 11',
            'season_id': 'df5e2334-e07a-4301-b3d3-8e224d8c1f07',
            'season_number': 11,
            'series_id': '6727dcdf-4bd2-477c-bf96-1ead69fad6c9',
            'upload_date': '20130225',
        },
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        metadata = self._download_json(f'https://npo.nl/start/api/domain/program-detail?slug={slug}', video_id=slug, note='Downloading program details JSON')
        video_id = metadata['productId']
        thumbnails = []
        for image in metadata.get('images'):
            thumbnails.append({
                'id': image.get('guid'),
                'url': image.get('url'),
            })
            break
        data = {
            'id': video_id,
            'title': metadata.get('title') or slug,
            'episode': metadata.get('title') or slug,
            'episode_number': int_or_none(metadata.get('programKey')),
            'duration': int_or_none(metadata.get('durationInSeconds')),
            'description': traverse_obj(metadata, ('synopsis', 'long')) or traverse_obj(metadata, ('synopsis', 'short')) or traverse_obj(metadata, ('synopsis', 'brief')),
            'thumbnails': thumbnails,
            'genres': metadata.get('genres'),
            'series': traverse_obj(metadata, ('series', 'title')),
            'series_id': traverse_obj(metadata, ('series', 'guid')),
            'season_number': int_or_none(traverse_obj(metadata, ('season', 'seasonKey'))),
            'season_id': traverse_obj(metadata, ('season', 'guid')),
            'release_timestamp': metadata.get('firstBroadcastDate'),
            'timestamp': metadata.get('publishedDateTime'),
        }
        token = self._download_json(
            f'https://npo.nl/start/api/domain/player-token?productId={video_id}', video_id,
            'Downloading token')['token']
        formats = []
        subtitles = {}
        for profile_name in ('dash', 'hls', 'smooth'):
            profile = self._download_json(
                'https://prod.npoplayer.nl/stream-link',
                video_id,
                f'Downloading profile {profile_name} JSON',
                data=json.dumps({'profileName': profile_name}).encode(),
                headers={'Authorization': token},
                fatal=False,
            )
            metadata = profile.get('metadata')
            if metadata is not None:
                data['channel_id'] = metadata.get('channel')
                data['uploader_id'] = metadata.get('channel')
            raw_subtitles = traverse_obj(profile, ('assets', 'subtitles'))
            stream_url = traverse_obj(profile, ('stream', 'streamURL'))
            stream_ext = determine_ext(stream_url)
            if stream_ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    stream_url, video_id=video_id, mpd_id='dash', fatal=False))
            elif stream_ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    stream_url, video_id=video_id, ext='mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', fatal=False))
            elif re.search(r'\.isml?/Manifest', stream_url):
                formats.extend(self._extract_ism_formats(
                    stream_url, video_id=video_id, ism_id='mss', fatal=False))
            else:
                formats.append({
                    'url': stream_url,
                })
            for subtitle in raw_subtitles:
                tag = subtitle.get('iso')
                if tag not in subtitles:
                    subtitles[tag] = []
                if not any(sub['url'] == subtitle['location'] for sub in subtitles[tag]):
                    subtitles[tag].append({
                        'url': subtitle.get('location'),
                        'name': subtitle.get('name'),
                    })
        data['formats'] = formats
        data['subtitles'] = subtitles
        return data


class NPORadioIE(InfoExtractor):
    IE_NAME = 'npo.nl:radio'
    _VALID_URL = r'https?://(?:www\.)?npo\.nl/radio/(?P<id>[^/]+)'

    _TEST = {
        'url': 'http://www.npo.nl/radio/radio-1',
        'info_dict': {
            'id': 'radio-1',
            'ext': 'mp3',
            'title': 're:^NPO Radio 1 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }

    @classmethod
    def suitable(cls, url):
        return False if NPORadioFragmentIE.suitable(url) else super().suitable(url)

    @staticmethod
    def _html_get_attribute_regex(attribute):
        return rf'{attribute}\s*=\s*\'([^\']+)\''

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            self._html_get_attribute_regex('data-channel'), webpage, 'title')

        stream = self._parse_json(
            self._html_search_regex(self._html_get_attribute_regex('data-streams'), webpage, 'data-streams'),
            video_id)

        codec = stream.get('codec')

        return {
            'id': video_id,
            'url': stream['url'],
            'title': title,
            'acodec': codec,
            'ext': codec,
            'is_live': True,
        }


class NPORadioFragmentIE(InfoExtractor):
    IE_NAME = 'npo.nl:radio:fragment'
    _VALID_URL = r'https?://(?:www\.)?npo\.nl/radio/[^/]+/fragment/(?P<id>\d+)'

    _TEST = {
        'url': 'http://www.npo.nl/radio/radio-5/fragment/174356',
        'md5': 'dd8cc470dad764d0fdc70a9a1e2d18c2',
        'info_dict': {
            'id': '174356',
            'ext': 'mp3',
            'title': 'Jubileumconcert Willeke Alberti',
        },
    }

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        webpage = self._download_webpage(url, audio_id)

        title = self._html_search_regex(
            rf'href="/radio/[^/]+/fragment/{audio_id}" title="([^"]+)"',
            webpage, 'title')

        audio_url = self._search_regex(
            r"data-streams='([^']+)'", webpage, 'audio url')

        return {
            'id': audio_id,
            'url': audio_url,
            'title': title,
        }


class NPODataMidEmbedIE(InfoExtractor):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(
            r'data-mid=(["\'])(?P<id>(?:(?!\1).)+)\1', webpage, 'video_id', group='id')
        return {
            '_type': 'url_transparent',
            'ie_key': 'NPO',
            'url': f'npo:{video_id}',
            'display_id': display_id,
        }


class SchoolTVIE(NPODataMidEmbedIE):
    IE_NAME = 'schooltv'
    _VALID_URL = r'https?://(?:www\.)?schooltv\.nl/video/(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'http://www.schooltv.nl/video/ademhaling-de-hele-dag-haal-je-adem-maar-wat-gebeurt-er-dan-eigenlijk-in-je-lichaam/',
        'info_dict': {
            'id': 'WO_NTR_429477',
            'display_id': 'ademhaling-de-hele-dag-haal-je-adem-maar-wat-gebeurt-er-dan-eigenlijk-in-je-lichaam',
            'title': 'Ademhaling: De hele dag haal je adem. Maar wat gebeurt er dan eigenlijk in je lichaam?',
            'ext': 'mp4',
            'description': 'md5:abfa0ff690adb73fd0297fd033aaa631',
        },
        'params': {
            # Skip because of m3u8 download
            'skip_download': True,
        },
    }


class HetKlokhuisIE(NPODataMidEmbedIE):
    IE_NAME = 'hetklokhuis'
    _VALID_URL = r'https?://(?:www\.)?hetklokhuis\.nl/[^/]+/\d+/(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'http://hetklokhuis.nl/tv-uitzending/3471/Zwaartekrachtsgolven',
        'info_dict': {
            'id': 'VPWON_1260528',
            'display_id': 'Zwaartekrachtsgolven',
            'ext': 'm4v',
            'title': 'Het Klokhuis: Zwaartekrachtsgolven',
            'description': 'md5:c94f31fb930d76c2efa4a4a71651dd48',
            'upload_date': '20170223',
        },
        'params': {
            'skip_download': True,
        },
    }


class NPOPlaylistBaseIE(NPOIE):  # XXX: Do not subclass from concrete IE
    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        entries = [
            self.url_result(f'npo:{video_id}' if not video_id.startswith('http') else video_id)
            for video_id in orderedSet(re.findall(self._PLAYLIST_ENTRY_RE, webpage))
        ]

        playlist_title = self._html_search_regex(
            self._PLAYLIST_TITLE_RE, webpage, 'playlist title',
            default=None) or self._og_search_title(webpage)

        return self.playlist_result(entries, playlist_id, playlist_title)


class VPROIE(NPOPlaylistBaseIE):
    IE_NAME = 'vpro'
    _VALID_URL = r'https?://(?:www\.)?(?:(?:tegenlicht\.)?vpro|2doc)\.nl/(?:[^/]+/)*(?P<id>[^/]+)\.html'
    _PLAYLIST_TITLE_RE = (r'<h1[^>]+class=["\'].*?\bmedia-platform-title\b.*?["\'][^>]*>([^<]+)',
                          r'<h5[^>]+class=["\'].*?\bmedia-platform-subtitle\b.*?["\'][^>]*>([^<]+)')
    _PLAYLIST_ENTRY_RE = r'data-media-id="([^"]+)"'

    _TESTS = [
        {
            'url': 'http://tegenlicht.vpro.nl/afleveringen/2012-2013/de-toekomst-komt-uit-afrika.html',
            'md5': 'f8065e4e5a7824068ed3c7e783178f2c',
            'info_dict': {
                'id': 'VPWON_1169289',
                'ext': 'm4v',
                'title': 'De toekomst komt uit Afrika',
                'description': 'md5:52cf4eefbc96fffcbdc06d024147abea',
                'upload_date': '20130225',
            },
            'skip': 'Video gone',
        },
        {
            'url': 'http://www.vpro.nl/programmas/2doc/2015/sergio-herman.html',
            'info_dict': {
                'id': 'sergio-herman',
                'title': 'sergio herman: fucking perfect',
            },
            'playlist_count': 2,
        },
        {
            # playlist with youtube embed
            'url': 'http://www.vpro.nl/programmas/2doc/2015/education-education.html',
            'info_dict': {
                'id': 'education-education',
                'title': 'education education',
            },
            'playlist_count': 2,
        },
        {
            'url': 'http://www.2doc.nl/documentaires/series/2doc/2015/oktober/de-tegenprestatie.html',
            'info_dict': {
                'id': 'de-tegenprestatie',
                'title': 'De Tegenprestatie',
            },
            'playlist_count': 2,
        }, {
            'url': 'http://www.2doc.nl/speel~VARA_101375237~mh17-het-verdriet-van-nederland~.html',
            'info_dict': {
                'id': 'VARA_101375237',
                'ext': 'm4v',
                'title': 'MH17: Het verdriet van Nederland',
                'description': 'md5:09e1a37c1fdb144621e22479691a9f18',
                'upload_date': '20150716',
            },
            'params': {
                # Skip because of m3u8 download
                'skip_download': True,
            },
        },
    ]


class WNLIE(NPOPlaylistBaseIE):
    IE_NAME = 'wnl'
    _VALID_URL = r'https?://(?:www\.)?omroepwnl\.nl/video/detail/(?P<id>[^/]+)__\d+'
    _PLAYLIST_TITLE_RE = r'(?s)<h1[^>]+class="subject"[^>]*>(.+?)</h1>'
    _PLAYLIST_ENTRY_RE = r'<a[^>]+href="([^"]+)"[^>]+class="js-mid"[^>]*>Deel \d+'

    _TESTS = [{
        'url': 'http://www.omroepwnl.nl/video/detail/vandaag-de-dag-6-mei__060515',
        'info_dict': {
            'id': 'vandaag-de-dag-6-mei',
            'title': 'Vandaag de Dag 6 mei',
        },
        'playlist_count': 4,
    }]


class AndereTijdenIE(NPOPlaylistBaseIE):
    IE_NAME = 'anderetijden'
    _VALID_URL = r'https?://(?:www\.)?anderetijden\.nl/programma/(?:[^/]+/)+(?P<id>[^/?#&]+)'
    _PLAYLIST_TITLE_RE = r'(?s)<h1[^>]+class=["\'].*?\bpage-title\b.*?["\'][^>]*>(.+?)</h1>'
    _PLAYLIST_ENTRY_RE = r'<figure[^>]+class=["\']episode-container episode-page["\'][^>]+data-prid=["\'](.+?)["\']'

    _TESTS = [{
        'url': 'http://anderetijden.nl/programma/1/Andere-Tijden/aflevering/676/Duitse-soldaten-over-de-Slag-bij-Arnhem',
        'info_dict': {
            'id': 'Duitse-soldaten-over-de-Slag-bij-Arnhem',
            'title': 'Duitse soldaten over de Slag bij Arnhem',
        },
        'playlist_count': 3,
    }]

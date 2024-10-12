import json
import re

from yt_dlp.utils._utils import ExtractorError
from yt_dlp.utils.traversal import traverse_obj

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    orderedSet,
)


class NPOBaseIE(InfoExtractor):
    def _extract_product_id_information(self, product_id):
        token = self._download_json(
            f'https://npo.nl/start/api/domain/player-token?productId={product_id}', product_id,
            'Downloading token')['token']
        return self._extract_info_from_token(product_id, token)

    def _extract_info_from_token(self, video_id, token):
        data = {
            'id': video_id,
        }
        formats = []
        thumbnails = []
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
                duration = metadata.get('duration')
                thumbnail = metadata.get('poster')
                data['title'] = metadata.get('title')
                data['description'] = metadata.get('description')
                data['channel_id'] = metadata.get('channel')
                data['uploader_id'] = metadata.get('channel')
                data['genres'] = metadata.get('genres')
                if duration:
                    data['duration'] = duration / 1000
                if thumbnail and not any(thumb['url'] == thumbnail for thumb in thumbnails):
                    thumbnails.append({
                        'url': thumbnail,
                    })
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
            if (raw_subtitles):
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
        data['thumbnails'] = thumbnails
        return data


class NPOStartIE(NPOBaseIE):
    IE_NAME = 'npo.nl:start'
    _VALID_URL = r'https?://(?:www\.)?npo\.nl/start/serie/(?:[^/]+/){2}(?P<id>[^/?#&]+)'

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
        data = self._extract_product_id_information(video_id)
        thumbnails = []
        for image in metadata.get('images'):
            thumbnails.append({
                'id': image.get('guid'),
                'url': image.get('url'),
            })
            break

        data['title'] = metadata.get('title') or data.get('title')
        data['episode'] = metadata.get('title') or data.get('title')
        data['episode_number'] = int_or_none(metadata.get('programKey'))
        data['duration'] = int_or_none(metadata.get('durationInSeconds'), default=data.get('duration'))
        data['description'] = traverse_obj(metadata, ('synopsis', 'long')) or traverse_obj(metadata, ('synopsis', 'short')) or traverse_obj(metadata, ('synopsis', 'brief')) or data.get('description')
        data['thumbnails'] = thumbnails
        data['genres'] = metadata.get('genres') or data.get('genres')
        data['series'] = traverse_obj(metadata, ('series', 'title'))
        data['series_id'] = traverse_obj(metadata, ('series', 'guid'))
        data['season_number'] = int_or_none(traverse_obj(metadata, ('season', 'seasonKey')))
        data['season_id'] = traverse_obj(metadata, ('season', 'guid'))
        data['release_timestamp'] = int_or_none(metadata.get('firstBroadcastDate'))
        data['timestamp'] = int_or_none(metadata.get('publishedDateTime'))
        return data


class NPORadioIE(NPOBaseIE):
    IE_NAME = 'npo.nl:radio'
    _VALID_URL = r'https?://(?:www\.)?nporadio(?P<n>\d)\.nl(?:/[^/]+)*/(?P<id>[^/]+)?'

    _TESTS = [{
        'url': 'https://www.nporadio1.nl/',
        'info_dict': {
            'id': 'live',
            'ext': 'mp4',
            'title': r're:^NPO Radio 1 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'live_status': 'is_live',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'Live programmering',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    },
        {
        'url': 'https://www.nporadio1.nl/nieuws/binnenland/15bcad75-22c5-4226-a3fe-d54a76175da3/utrecht-zet-rolmodellen-in-voor-bewustwording-mentale-gezondheid',
        'md5': '8ad04123febc07716f45e324d7fb792d',
        'info_dict': {
            'id': 'utrecht-zet-rolmodellen-in-voor-bewustwording-mentale-gezondheid',
            'ext': 'mp4',
            'duration': 262,
            'channel_id': 'RAD1',
            'description': 'md5:7d36b72407e757e6c748a6cdf27c7628',
            'title': 'Utrecht zet rolmodellen in voor bewustzijn mentale gezondheid ',
            'genres': ['Informatief'],
            'uploader_id': 'RAD1',
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/2217026',
        },
    },
        {
        'url': 'https://www.nporadio2.nl/fragmenten/janwillemstartop/9d35b8fb-a07b-41f9-9cc5-a9c89dd60dbb/2024-10-10-nancy-zet-zich-in-voor-daklozen-voor-mij-was-het-op-het-randje',
        'md5': '432b0e106082ffaa0e31c4549db09b0c',
        'info_dict': {
            'id': '2024-10-10-nancy-zet-zich-in-voor-daklozen-voor-mij-was-het-op-het-randje',
            'ext': 'mp4',
            'genres': ['Muziek'],
            'title': 'Nancy zet zich in voor daklozen: "Voor mij was het op het randje" ',
            'duration': 235,
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/2216783',
            'description': 'md5:26925e8bd2c715b160cc864efa731583',
            'uploader_id': 'RAD2',
            'channel_id': 'RAD2',
        },
    },
        {
        'url': 'https://www.nporadio2.nl/uitzendingen/dit-is-tannaz/9bc1ab7e-77f6-4444-986b-1cd7c25ff4bf/2024-10-11-dit-is-tannaz',
        'md5': 'a1212f4d2fe361aafcced5bcd3cf939b',
        'info_dict': {
            'id': '2024-10-11-dit-is-tannaz',
            'ext': 'mp3',
            'uploader_id': 'RAD2',
            'genres': ['Muziek'],
            'title': 'Dit is Tannaz',
            'channel_id': 'RAD2',
            'description': 'md5:3f2b5dad3e965ae7915a5f9a5a2decc5',
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/2190854',
            'duration': 7200.026,
        },
    }]

    def _real_extract(self, url):
        parsed = self._match_valid_url(url)
        video_id = parsed.group('id') or 'live'

        if video_id == 'live':
            radio_number = parsed.group('n')
            token_url = self._download_json(f'https://www.nporadio{radio_number}.nl/api/player/npo-radio-{radio_number}', video_id)['tokenUrl']
        else:
            props = self._search_nextjs_data(self._download_webpage(url, video_id), video_id)['props']['pageProps']
            token_url = traverse_obj(props, ('article', 'content', 0, 'value', 'player', 'tokenUrl')) or traverse_obj(props, ('fragmentDetail', 'bodyContent', 0, 'payload', 'player', 'tokenUrl')) or traverse_obj(props, ('radioBroadcast', 'showAssets', 0, 'player', 'tokenUrl'))
        if token_url is None:
            raise ExtractorError('Token url not found')
        data = self._extract_info_from_token(video_id, self._download_json(token_url, video_id, 'Downloading token JSON')['playerToken'])
        data['is_live'] = video_id == 'live'
        return data


class NPO3IE(NPOBaseIE):
    IE_NAME = 'npo.nl:npo3'
    _VALID_URL = r'https?://(?:www\.)?npo\.nl/npo3/(?:[^/]+/){2}(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'https://npo.nl/npo3/vlees-smakelijk/11-10-2024/WO_KN_20222563',
        'md5': 'e0cd5b96c712edea2e7f0700d348bc98',
        'info_dict': {
            'id': 'WO_KN_20222563',
            'ext': 'mp4',
            'description': 'md5:31f5ffff8c70af1635cbb93a8205e0c4',
            'duration': 1021.994,
            'title': 'Vlees smakelijk',
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/2215940',
            'genres': ['Human Interest', 'Reality TV'],
        },
    }

    def _real_extract(self, url):
        return self._extract_product_id_information(self._match_id(url))


class SchoolTVIE(NPOBaseIE):
    IE_NAME = 'schooltv'
    _VALID_URL = r'https?://(?:www\.)?schooltv\.nl/video-item/(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'https://schooltv.nl/video-item/ademhaling-de-hele-dag-haal-je-adem-maar-wat-gebeurt-er-dan-eigenlijk-in-je-lichaam',
        'info_dict': {
            'id': 'WO_NTR_429477',
            'ext': 'mp4',
            'duration': 51.0,
            'genres': ['Jeugd'],
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/242560',
            'title': 'Ademhaling',
            'description': 'md5:db41d874d9ebe597686dda69e892ba49',
        },
    }

    def _real_extract(self, url):
        video_id = self._search_regex(r'id=([a-zA-Z0-9_]+)', self._html_search_meta(('og:video', 'og:video:secure_url'), self._download_webpage(url, self._match_id(url))), 'video id')
        return self._extract_info_from_token(video_id, self._download_json(f'https://api3.schooltv.nl/player/{video_id}', video_id, 'Downloading token JSON')['data']['token'])


class HetKlokhuisIE(NPOBaseIE):
    IE_NAME = 'hetklokhuis'
    _VALID_URL = r'https?://(?:www\.)?hetklokhuis\.nl/(?:[^/]+/)*(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'https://hetklokhuis.nl/dossier/142/zoek-het-uit/tv-uitzending/2987/aliens',
        'md5': '679d610017689ecc798b316b8daa34e7',
        'info_dict': {
            'id': 'VPWON_1225126',
            'ext': 'mp4',
            'duration': 852.27,
            'channel_id': 'NED3',
            'description': 'md5:17681c9644521344a0573e04c78912d7',
            'title': 'Aliens',
            'genres': ['Jeugd', 'Informatief'],
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/624824',
            'uploader_id': 'NED3',
            'series': 'Zoek Het Uit!',
        },
    }

    def _real_extract(self, url):
        webpage = self._download_webpage(url, self._match_id(url))
        series, title = self._og_search_title(webpage).split(' - ')
        video_id = self._html_search_regex(r'data-mid="([a-zA-Z0-9_]+)"', webpage, 'video id')
        data = self._extract_info_from_token(video_id, self._download_json(f'https://api3.schooltv.nl/player/{video_id}', video_id, 'Downloading token JSON')['data']['token'])
        data['series'] = series
        data['title'] = title
        return data


class ZappIE(NPOBaseIE):
    IE_NAME = 'zapp.nl'
    _VALID_URL = r'https?://(?:www\.)?zapp\.nl/programmas/(?:[^/]+/){2}(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'https://www.zapp.nl/programmas/zappsport/gemist/POMS_AT_811523',
        'md5': 'faf6811abea03ba8a52298c97bd0146b',
        'info_dict': {
            'id': 'POMS_AT_811523',
            'ext': 'mp4',
            'genres': [],
            'uploader_id': 'NED3',
            'description': 'Kindersportprogramma waarin alle takken van sport voorbijkomen.',
            'channel_id': 'NED3',
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/586056',
            'duration': 900.0,
            'title': 'Running Team 2015 - aflevering 1',
        },
    }

    def _real_extract(self, url):
        return self._extract_product_id_information(self._match_id(url))


class NPOPlaylistBaseIE(NPOBaseIE):
    def _mid_result(self, mid, title, url):
        token = self._download_token(mid, url)
        data = self._extract_info_from_token(mid, token)
        # The API returns the same title for every video so overwrite it with the video title
        data['title'] = title
        return data

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        playlist_title = self._html_search_regex(
            self._PLAYLIST_TITLE_RE, webpage, 'playlist title',
            default=None) or self._og_search_title(webpage)

        entries = [
            self._mid_result(video_id, playlist_title, url)
            for video_id in orderedSet(re.findall(self._PLAYLIST_ENTRY_RE, webpage))
        ]

        return self.playlist_result(entries, playlist_id, playlist_title)


class VPROIE(NPOPlaylistBaseIE):
    IE_NAME = 'vpro'
    _VALID_URL = r'https?://(?:www\.)?(?:vpro|2doc)\.nl/(?:[^/]+/)*(?P<id>[^/.]+)'
    _PLAYLIST_TITLE_RE = (r'<h1[^>]+class=["\'].*?\bmedia-platform-title\b.*?["\'][^>]*>([^<]+)')
    _PLAYLIST_ENTRY_RE = r'data-media-id="([^"]+)"'

    _TESTS = [
        {
            'url': 'https://www.vpro.nl/programmas/3doc/2015/sergio-herman.html',
            'info_dict': {
                'id': 'sergio-herman',
                'title': 'Sergio Herman: Fucking Perfect',
            },
            'playlist_count': 2,
        },
        {
            'url': 'http://www.2doc.nl/documentaires/series/2doc/2015/oktober/de-tegenprestatie.html',
            'md5': '87a4cc5a62da942ca9270e4da1d2b8b5',
            'info_dict': {
                'id': 'VPWON_1223413',
                'ext': 'mp4',
                'title': 'De Tegenprestatie',
                'duration': 2992.45,
                'genres': ['Documentaire'],
                'channel_id': 'NED2',
                'description': 'Er wordt van burgers steeds meer eigen verantwoordelijkheid en zelfredzaamheid gevraagd.',
                'uploader_id': 'NED2',
                'thumbnail': 'https://images.poms.omroep.nl/image/s1080/663342',
            },
        }, {
            'url': 'https://www.2doc.nl/documentaires/2018/07/het-verdriet-van-nederland.html',
            'md5': '9ae67f6bdcb16a62f99e01198674fe10',
            'info_dict': {
                'id': 'VARA_101375237',
                'ext': 'mp4',
                'uploader_id': 'NED1',
                'channel_id': 'NED1',
                'thumbnail': 'https://images.poms.omroep.nl/image/s1080/1608566',
                'duration': 4259.63,
                'genres': ['Documentaire'],
                'title': 'Het verdriet van Nederland',
                'description': 'md5:d19b745af196f6cb98daf50ac7cb01fc',
            },
        },
    ]

    def _download_token(self, mid, url):
        return self._download_json('https://rs.vpro.nl/v3/api/npoplayer/token', mid, 'Downloading token JSON', data=json.dumps({'mid': mid}).encode(), headers={
            'Content-Type': 'application/json',
            'Referer': url,
        })['token']


class NTRIE(NPOPlaylistBaseIE):
    IE_NAME = 'ntr'
    _VALID_URL = r'https?://(?:www\.)?ntr\.nl/(?:[^/]+/)+(?P<id>[^/?#&]+)'
    _PLAYLIST_TITLE_RE = r'<h2[^>]*>\s*(.+)\s*</h2>'
    _PLAYLIST_ENTRY_RE = r'<div[^>]+class=["\']npo_wrapper["\'][^>]+data-mid=["\'](.+?)["\']'

    _TESTS = [{
        'url': 'https://ntr.nl/Aap-Poot-Pies/27/detail/Aap-poot-pies/VPWON_1233944',
        'md5': '5b7b45c15750c9a74f8b70ea69f0b55a',
        'info_dict': {
            'id': 'VPWON_1233944',
            'ext': 'mp4',
            'duration': 599.98,
            'channel_id': 'NED3',
            'genres': ['Jeugd', 'Serie'],
            'description': 'Appie en Aisia mogen beurtelings mee met hun vader Luc, die in de dierentuin werkt.',
            'uploader_id': 'NED3',
            'title': 'Aap, poot, pies',
            'thumbnail': 'https://images.poms.omroep.nl/image/s1080/608116',
        },
    }]

    def _download_token(self, mid, url):
        return self._download_json(f'https://ntr.nl/ajax/player/embed/{mid}', mid, 'Downloading token JSON')['jwt']


class AndereTijdenIE(NTRIE):
    IE_NAME = 'anderetijden'
    _VALID_URL = r'https?://(?:www\.)?anderetijden\.nl/programma/(?:[^/]+/)+(?P<id>[^/?#&]+)'
    _PLAYLIST_TITLE_RE = r'(?s)<h1[^>]+class=["\'].*?\bpage-title\b.*?["\'][^>]*>(.+?)</h1>'
    _PLAYLIST_ENTRY_RE = r'<figure[^>]+class=["\']episode-container\s+episode-page["\'][^>]+data-mid=["\'](.+?)["\']'

    _TESTS = [{
        'url': 'http://anderetijden.nl/programma/1/Andere-Tijden/aflevering/676/Duitse-soldaten-over-de-Slag-bij-Arnhem',
        'info_dict': {
            'id': 'Duitse-soldaten-over-de-Slag-bij-Arnhem',
            'title': 'Duitse soldaten over de Slag bij Arnhem',
        },
        'playlist_count': 3,
    }]

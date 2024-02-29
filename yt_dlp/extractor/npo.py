import json
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    orderedSet,
    url_or_none,
)


class NPOIE(InfoExtractor):
    IE_NAME = 'npo'
    IE_DESC = 'npo.nl, ntr.nl, omroepwnl.nl, zapp.nl and npo3.nl'
    _VALID_URL = r'''(?x)
                    (?:
                        npo:|
                        https?://
                            (?:www\.)?
                            (?:
                                npo\.nl/(?:[^/]+/)*|
                                (?:ntr|npostart)\.nl/(?:[^/]+/){2,}|
                                omroepwnl\.nl/video/fragment/[^/]+__|
                                (?:zapp|npo3)\.nl/(?:[^/]+/){2,}
                            )
                        )
                        (?P<id>[^/?#]+)
                '''

    _TESTS = [{
        'url': 'http://www.npo.nl/tegenlicht/25-02-2013/VPWON_1169289',
        'md5': '8c30593a81ac80d65b531eaf2a92ac02',
        'info_dict': {
            'id': 'VPWON_1169289',
            'ext': 'mp4',
            'title': 'VPWON_1169289',
        },
    }, {
        'url': 'http://www.npo.nl/de-nieuwe-mens-deel-1/21-07-2010/WO_VPRO_043706',
        'info_dict': {
            'id': 'WO_VPRO_043706',
            'ext': 'mp4',
            'title': 'WO_VPRO_043706',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.ntr.nl/Aap-Poot-Pies/27/detail/Aap-poot-pies/VPWON_1233944#content',
        'info_dict': {
            'id': 'VPWON_1233944',
            'ext': 'mp4',
            'title': 'VPWON_1233944',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.zapp.nl/programmas/de-bzt-show/gemist/KN_1687547',
        'info_dict': {
            'id': 'KN_1687547',
            'ext': 'mp4',
            'title': 'KN_1687547',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.zapp.nl/de-bzt-show/filmpjes/POMS_KN_7315118',
        'only_matching': True,
    }, {
        'url': 'http://www.zapp.nl/beste-vrienden-quiz/extra-video-s/WO_NTR_1067990',
        'only_matching': True,
    }, {
        'url': 'https://www.npo3.nl/3onderzoekt/16-09-2015/VPWON_1239870',
        'only_matching': True,
    }, {
        # live stream
        'url': 'npo:LI_NL1_4188102',
        'only_matching': True,
    }, {
        'url': 'http://www.npo.nl/radio-gaga/13-06-2017/BNN_101383373',
        'only_matching': True,
    }, {
        'url': 'https://www.zapp.nl/1803-skelterlab/instructie-video-s/740-instructievideo-s/POMS_AT_11736927',
        'only_matching': True,
    }, {
        'url': 'https://www.npostart.nl/broodje-gezond-ei/28-05-2018/KN_1698996',
        'only_matching': True,
    }, {
        'url': 'https://npo.nl/KN_1698996',
        'only_matching': True,
    }, {
        'url': 'https://www.npo3.nl/the-genius/21-11-2022/VPWON_1341105',
        'info_dict': {
            'id': 'VPWON_1341105',
            'title': 'VPWON_1341105',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://npo.nl/npo3/de-braboneger-basht-jaaroverzicht/29-12-2017/POMS_AT_12271940',
        'md5': '4f2eab9f002007c66fe25c2f7cdacaf1',
        'info_dict': {
            'id': 'POMS_AT_12271940',
            'title': 'POMS_AT_12271940',
            'ext': 'mp4',
        },
    }]

    @classmethod
    def suitable(cls, url):
        return (False if any(ie.suitable(url)
                for ie in (NPOLiveIE, NPORadioIE, NPORadioFragmentIE))
                else super(NPOIE, cls).suitable(url))

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if video_id == 'afspelen':
            self.raise_no_formats('This URL format is not supported yet', expected=True)

        player_token_data = self._download_json(
            f'https://npo.nl/start/api/domain/player-token?productId={video_id}', video_id,
            'Downloading player JSON')

        player_token = player_token_data['token']

        drm = False
        allow_unplayable = self.get_param('allow_unplayable_formats')
        format_urls = set()
        formats = []
        for profile in ('hls', 'dash'):
            streams = self._download_json(
                'https://prod.npoplayer.nl/stream-link',
                '',
                'Downloading stream-link JSON',
                data=json.dumps({
                    'referrerUrl': url,
                    # widevine, playready or fairplay
                    'drmType': '',
                    # dash or hls
                    'profileName': profile,
                }).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': player_token,
                }
            )

            if not streams:
                continue
            stream = streams.get('stream')
            if not isinstance(stream, dict):
                continue
            stream_url = url_or_none(stream.get('streamURL'))
            if not stream_url or stream_url in format_urls:
                continue
            format_urls.add(stream_url)
            if stream.get('drmToken') and not allow_unplayable:
                drm = True
                continue
            stream_ext = determine_ext(stream_url)
            if stream_ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    stream_url, video_id, mpd_id='dash', fatal=False))
            elif stream_ext == 'm3u8':
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

        # If no suitable formats and at least one DRM stream is found, report DRM
        if not formats and drm:
            self.report_drm(video_id)

        info = {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }

        return info


class NPOLiveIE(InfoExtractor):
    IE_NAME = 'npo.nl:live'
    _VALID_URL = r'https?://(?:www\.)?npo(?:start)?\.nl/live(?:/(?P<id>[^/?#&]+))?'

    _TESTS = [{
        'url': 'http://www.npo.nl/live/npo-1',
        'info_dict': {
            'id': 'LI_NL1_4188102',
            'display_id': 'npo-1',
            'ext': 'mp4',
            'title': 're:^NPO 1 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://www.npo.nl/live',
        'only_matching': True,
    }, {
        'url': 'https://www.npostart.nl/live/npo-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url) or 'npo-1'

        webpage = self._download_webpage(url, display_id)

        live_id = self._search_regex(
            [r'media-id="([^"]+)"', r'data-prid="([^"]+)"'], webpage, 'live id')

        return {
            '_type': 'url_transparent',
            'url': 'npo:%s' % live_id,
            'ie_key': NPOIE.ie_key(),
            'id': live_id,
            'display_id': display_id,
        }


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
        }
    }

    @classmethod
    def suitable(cls, url):
        return False if NPORadioFragmentIE.suitable(url) else super(NPORadioIE, cls).suitable(url)

    @staticmethod
    def _html_get_attribute_regex(attribute):
        return r'{0}\s*=\s*\'([^\']+)\''.format(attribute)

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
            r'href="/radio/[^/]+/fragment/%s" title="([^"]+)"' % audio_id,
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
            'url': 'npo:%s' % video_id,
            'display_id': display_id
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
            'description': 'md5:abfa0ff690adb73fd0297fd033aaa631'
        },
        'params': {
            # Skip because of m3u8 download
            'skip_download': True
        }
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
            'skip_download': True
        }
    }


class NPOPlaylistBaseIE(NPOIE):  # XXX: Do not subclass from concrete IE
    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        entries = [
            self.url_result('npo:%s' % video_id if not video_id.startswith('http') else video_id)
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
                'skip_download': True
            },
        }
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

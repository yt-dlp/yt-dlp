import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    fix_xml_ampersands,
    int_or_none,
    merge_dicts,
    orderedSet,
    parse_duration,
    qualities,
    str_or_none,
    strip_jsonp,
    unified_strdate,
    unified_timestamp,
    url_or_none,
    urlencode_postdata,
)


class NPOBaseIE(InfoExtractor):
    def _get_token(self, video_id):
        return self._download_json(
            'http://ida.omroep.nl/app.php/auth', video_id,
            note='Downloading token')['token']


class NPOIE(NPOBaseIE):
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
        'url': 'http://www.npo.nl/nieuwsuur/22-06-2014/VPWON_1220719',
        'md5': '4b3f9c429157ec4775f2c9cb7b911016',
        'info_dict': {
            'id': 'VPWON_1220719',
            'ext': 'm4v',
            'title': 'Nieuwsuur',
            'description': 'Dagelijks tussen tien en elf: nieuws, sport en achtergronden.',
            'upload_date': '20140622',
        },
    }, {
        'url': 'http://www.npo.nl/de-mega-mike-mega-thomas-show/27-02-2009/VARA_101191800',
        'md5': 'da50a5787dbfc1603c4ad80f31c5120b',
        'info_dict': {
            'id': 'VARA_101191800',
            'ext': 'm4v',
            'title': 'De Mega Mike & Mega Thomas show: The best of.',
            'description': 'md5:3b74c97fc9d6901d5a665aac0e5400f4',
            'upload_date': '20090227',
            'duration': 2400,
        },
    }, {
        'url': 'http://www.npo.nl/tegenlicht/25-02-2013/VPWON_1169289',
        'md5': 'f8065e4e5a7824068ed3c7e783178f2c',
        'info_dict': {
            'id': 'VPWON_1169289',
            'ext': 'm4v',
            'title': 'Tegenlicht: Zwart geld. De toekomst komt uit Afrika',
            'description': 'md5:52cf4eefbc96fffcbdc06d024147abea',
            'upload_date': '20130225',
            'duration': 3000,
        },
    }, {
        'url': 'http://www.npo.nl/de-nieuwe-mens-deel-1/21-07-2010/WO_VPRO_043706',
        'info_dict': {
            'id': 'WO_VPRO_043706',
            'ext': 'm4v',
            'title': 'De nieuwe mens - Deel 1',
            'description': 'md5:518ae51ba1293ffb80d8d8ce90b74e4b',
            'duration': 4680,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # non asf in streams
        'url': 'http://www.npo.nl/hoe-gaat-europa-verder-na-parijs/10-01-2015/WO_NOS_762771',
        'info_dict': {
            'id': 'WO_NOS_762771',
            'ext': 'mp4',
            'title': 'Hoe gaat Europa verder na Parijs?',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://www.ntr.nl/Aap-Poot-Pies/27/detail/Aap-poot-pies/VPWON_1233944#content',
        'info_dict': {
            'id': 'VPWON_1233944',
            'ext': 'm4v',
            'title': 'Aap, poot, pies',
            'description': 'md5:c9c8005d1869ae65b858e82c01a91fde',
            'upload_date': '20150508',
            'duration': 599,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://www.omroepwnl.nl/video/fragment/vandaag-de-dag-verkiezingen__POMS_WNL_853698',
        'info_dict': {
            'id': 'POW_00996502',
            'ext': 'm4v',
            'title': '''"Dit is wel een 'landslide'..."''',
            'description': 'md5:f8d66d537dfb641380226e31ca57b8e8',
            'upload_date': '20150508',
            'duration': 462,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # audio
        'url': 'http://www.npo.nl/jouw-stad-rotterdam/29-01-2017/RBX_FUNX_6683215/RBX_FUNX_7601437',
        'info_dict': {
            'id': 'RBX_FUNX_6683215',
            'ext': 'mp3',
            'title': 'Jouw Stad Rotterdam',
            'description': 'md5:db251505244f097717ec59fabc372d9f',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://www.zapp.nl/de-bzt-show/gemist/KN_1687547',
        'only_matching': True,
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
    }]

    @classmethod
    def suitable(cls, url):
        return (False if any(ie.suitable(url)
                for ie in (NPOLiveIE, NPORadioIE, NPORadioFragmentIE))
                else super(NPOIE, cls).suitable(url))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._get_info(url, video_id) or self._get_old_info(video_id)

    def _get_info(self, url, video_id):
        token = self._download_json(
            'https://www.npostart.nl/api/token', video_id,
            'Downloading token', headers={
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest',
            })['token']

        player = self._download_json(
            'https://www.npostart.nl/player/%s' % video_id, video_id,
            'Downloading player JSON', data=urlencode_postdata({
                'autoplay': 0,
                'share': 1,
                'pageUrl': url,
                'hasAdConsent': 0,
                '_token': token,
            }))

        player_token = player['token']

        drm = False
        format_urls = set()
        formats = []
        for profile in ('hls', 'dash-widevine', 'dash-playready', 'smooth'):
            streams = self._download_json(
                'https://start-player.npo.nl/video/%s/streams' % video_id,
                video_id, 'Downloading %s profile JSON' % profile, fatal=False,
                query={
                    'profile': profile,
                    'quality': 'npo',
                    'tokenId': player_token,
                    'streamType': 'broadcast',
                })
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

        self._sort_formats(formats)

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

    def _get_old_info(self, video_id):
        metadata = self._download_json(
            'http://e.omroep.nl/metadata/%s' % video_id,
            video_id,
            # We have to remove the javascript callback
            transform_source=strip_jsonp,
        )

        error = metadata.get('error')
        if error:
            raise ExtractorError(error, expected=True)

        # For some videos actual video id (prid) is different (e.g. for
        # http://www.omroepwnl.nl/video/fragment/vandaag-de-dag-verkiezingen__POMS_WNL_853698
        # video id is POMS_WNL_853698 but prid is POW_00996502)
        video_id = metadata.get('prid') or video_id

        # titel is too generic in some cases so utilize aflevering_titel as well
        # when available (e.g. http://tegenlicht.vpro.nl/afleveringen/2014-2015/access-to-africa.html)
        title = metadata['titel']
        sub_title = metadata.get('aflevering_titel')
        if sub_title and sub_title != title:
            title += ': %s' % sub_title

        token = self._get_token(video_id)

        formats = []
        urls = set()

        def is_legal_url(format_url):
            return format_url and format_url not in urls and re.match(
                r'^(?:https?:)?//', format_url)

        QUALITY_LABELS = ('Laag', 'Normaal', 'Hoog')
        QUALITY_FORMATS = ('adaptive', 'wmv_sb', 'h264_sb', 'wmv_bb', 'h264_bb', 'wvc1_std', 'h264_std')

        quality_from_label = qualities(QUALITY_LABELS)
        quality_from_format_id = qualities(QUALITY_FORMATS)
        items = self._download_json(
            'http://ida.omroep.nl/app.php/%s' % video_id, video_id,
            'Downloading formats JSON', query={
                'adaptive': 'yes',
                'token': token,
            })['items'][0]
        for num, item in enumerate(items):
            item_url = item.get('url')
            if not is_legal_url(item_url):
                continue
            urls.add(item_url)
            format_id = self._search_regex(
                r'video/ida/([^/]+)', item_url, 'format id',
                default=None)

            item_label = item.get('label')

            def add_format_url(format_url):
                width = int_or_none(self._search_regex(
                    r'(\d+)[xX]\d+', format_url, 'width', default=None))
                height = int_or_none(self._search_regex(
                    r'\d+[xX](\d+)', format_url, 'height', default=None))
                if item_label in QUALITY_LABELS:
                    quality = quality_from_label(item_label)
                    f_id = item_label
                elif item_label in QUALITY_FORMATS:
                    quality = quality_from_format_id(format_id)
                    f_id = format_id
                else:
                    quality, f_id = [None] * 2
                formats.append({
                    'url': format_url,
                    'format_id': f_id,
                    'width': width,
                    'height': height,
                    'quality': quality,
                })

            # Example: http://www.npo.nl/de-nieuwe-mens-deel-1/21-07-2010/WO_VPRO_043706
            if item.get('contentType') in ('url', 'audio'):
                add_format_url(item_url)
                continue

            try:
                stream_info = self._download_json(
                    item_url + '&type=json', video_id,
                    'Downloading %s stream JSON'
                    % item_label or item.get('format') or format_id or num)
            except ExtractorError as ee:
                if isinstance(ee.cause, compat_HTTPError) and ee.cause.code == 404:
                    error = (self._parse_json(
                        ee.cause.read().decode(), video_id,
                        fatal=False) or {}).get('errorstring')
                    if error:
                        raise ExtractorError(error, expected=True)
                raise
            # Stream URL instead of JSON, example: npo:LI_NL1_4188102
            if isinstance(stream_info, compat_str):
                if not stream_info.startswith('http'):
                    continue
                video_url = stream_info
            # JSON
            else:
                video_url = stream_info.get('url')
            if not video_url or 'vodnotavailable.' in video_url or video_url in urls:
                continue
            urls.add(video_url)
            if determine_ext(video_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    video_url, video_id, ext='mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', fatal=False))
            else:
                add_format_url(video_url)

        is_live = metadata.get('medium') == 'live'

        if not is_live:
            for num, stream in enumerate(metadata.get('streams', [])):
                stream_url = stream.get('url')
                if not is_legal_url(stream_url):
                    continue
                urls.add(stream_url)
                # smooth streaming is not supported
                stream_type = stream.get('type', '').lower()
                if stream_type in ['ss', 'ms']:
                    continue
                if stream_type == 'hds':
                    f4m_formats = self._extract_f4m_formats(
                        stream_url, video_id, fatal=False)
                    # f4m downloader downloads only piece of live stream
                    for f4m_format in f4m_formats:
                        f4m_format['preference'] = -5
                    formats.extend(f4m_formats)
                elif stream_type == 'hls':
                    formats.extend(self._extract_m3u8_formats(
                        stream_url, video_id, ext='mp4', fatal=False))
                # Example: http://www.npo.nl/de-nieuwe-mens-deel-1/21-07-2010/WO_VPRO_043706
                elif '.asf' in stream_url:
                    asx = self._download_xml(
                        stream_url, video_id,
                        'Downloading stream %d ASX playlist' % num,
                        transform_source=fix_xml_ampersands, fatal=False)
                    if not asx:
                        continue
                    ref = asx.find('./ENTRY/Ref')
                    if ref is None:
                        continue
                    video_url = ref.get('href')
                    if not video_url or video_url in urls:
                        continue
                    urls.add(video_url)
                    formats.append({
                        'url': video_url,
                        'ext': stream.get('formaat', 'asf'),
                        'quality': stream.get('kwaliteit'),
                        'preference': -10,
                    })
                else:
                    formats.append({
                        'url': stream_url,
                        'quality': stream.get('kwaliteit'),
                    })

        self._sort_formats(formats)

        subtitles = {}
        if metadata.get('tt888') == 'ja':
            subtitles['nl'] = [{
                'ext': 'vtt',
                'url': 'http://tt888.omroep.nl/tt888/%s' % video_id,
            }]

        return {
            'id': video_id,
            'title': title,
            'description': metadata.get('info'),
            'thumbnail': metadata.get('images', [{'url': None}])[-1]['url'],
            'upload_date': unified_strdate(metadata.get('gidsdatum')),
            'duration': parse_duration(metadata.get('tijdsduur')),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
        }


class NPOLiveIE(NPOBaseIE):
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


class NPODataMidEmbedIE(InfoExtractor):
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


class NPOPlaylistBaseIE(NPOIE):
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

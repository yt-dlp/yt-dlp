from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    qualities,
    try_get,
)


class SRGSSRIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    (?:srgssr:|urn:)
                    (?:swisstxt:(?P<type>video|audio):)?
                    (?P<bu>srf|rts|rsi|rtr|swi):
                    (?:(?P<type_2>video|audio):)?
                    (?P<id>[0-9a-f\-]{36}|\d+)
                    '''
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['CH']

    _ERRORS = {
        'AGERATING12': 'To protect children under the age of 12, this video is only available between 8 p.m. and 6 a.m.',
        'AGERATING18': 'To protect children under the age of 18, this video is only available between 11 p.m. and 5 a.m.',
        # 'ENDDATE': 'For legal reasons, this video was only available for a specified period of time.',
        'GEOBLOCK': 'For legal reasons, this video is only available in Switzerland.',
        'LEGAL': 'The video cannot be transmitted for legal reasons.',
        'STARTDATE': 'This video is not yet available. Please try again later.',
    }
    _DEFAULT_LANGUAGE_CODES = {
        'srf': 'de',
        'rts': 'fr',
        'rsi': 'it',
        'rtr': 'rm',
        'swi': 'en',
    }

    def _get_tokenized_src(self, url, video_id, format_id):
        token = self._download_json(
            'http://tp.srgssr.ch/akahd/token?acl=*',
            video_id, f'Downloading {format_id} token', fatal=False) or {}
        auth_params = try_get(token, lambda x: x['token']['authparams'])
        if auth_params:
            url += ('?' if '?' not in url else '&') + auth_params
        return url

    def _get_media_data(self, bu, media_type, media_id, is_swisstxt=False):
        query = {'onlyChapters': True} if media_type == 'video' else {}

        # For swisstxt URNs, use the byUrn endpoint
        if is_swisstxt:
            urn = f'urn:swisstxt:{media_type}:{bu}:{media_id}'
            full_media_data = self._download_json(
                f'https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/{urn}.json',
                media_id, query=query)['chapterList']
            # For swisstxt URNs, match by the URN itself
            urn_match = f'urn:swisstxt:{media_type}:{bu}:{media_id}'
        else:
            # For UUIDs, use the standard endpoint
            full_media_data = self._download_json(
                f'https://il.srgssr.ch/integrationlayer/2.0/{bu}/mediaComposition/{media_type}/{media_id}.json',
                media_id, query=query)['chapterList']
            urn_match = None

        try:
            if urn_match:
                media_data = next(
                    x for x in full_media_data if x.get('urn') == urn_match or x.get('id') == media_id)
            else:
                media_data = next(
                    x for x in full_media_data if x.get('id') == media_id)
        except StopIteration:
            raise ExtractorError('No media information found')

        block_reason = media_data.get('blockReason')
        if block_reason and block_reason in self._ERRORS:
            message = self._ERRORS[block_reason]
            if block_reason == 'GEOBLOCK':
                self.raise_geo_restricted(
                    msg=message, countries=self._GEO_COUNTRIES)
            raise ExtractorError(
                f'{self.IE_NAME} said: {message}', expected=True)

        return media_data

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        bu = mobj.group('bu')
        media_type = mobj.group('type') or mobj.group('type_2')
        media_id = mobj.group('id')
        # Check if this is a swisstxt URN based on the regex match
        is_swisstxt = mobj.group('type') is not None
        media_data = self._get_media_data(bu, media_type, media_id, is_swisstxt)
        title = media_data['title']

        formats = []
        subtitles = {}
        q = qualities(['SD', 'HD'])
        for source in (media_data.get('resourceList') or []):
            format_url = source.get('url')
            if not format_url:
                continue
            protocol = source.get('protocol')
            quality = source.get('quality')
            format_id = join_nonempty(protocol, source.get('encoding'), quality)

            if protocol in ('HDS', 'HLS'):
                if source.get('tokenType') == 'AKAMAI':
                    format_url = self._get_tokenized_src(
                        format_url, media_id, format_id)
                    fmts, subs = self._extract_akamai_formats_and_subtitles(
                        format_url, media_id)
                    formats.extend(fmts)
                    subtitles = self._merge_subtitles(subtitles, subs)
                elif protocol == 'HLS':
                    m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                        format_url, media_id, 'mp4', 'm3u8_native',
                        m3u8_id=format_id, fatal=False)
                    formats.extend(m3u8_fmts)
                    subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif protocol in ('HTTP', 'HTTPS'):
                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'quality': q(quality),
                })

        # This is needed because for audio medias the podcast url is usually
        # always included, even if is only an audio segment and not the
        # whole episode.
        if int_or_none(media_data.get('position')) == 0:
            for p in ('S', 'H'):
                podcast_url = media_data.get(f'podcast{p}dUrl')
                if not podcast_url:
                    continue
                quality = p + 'D'
                formats.append({
                    'format_id': 'PODCAST-' + quality,
                    'url': podcast_url,
                    'quality': q(quality),
                })

        if media_type == 'video':
            for sub in (media_data.get('subtitleList') or []):
                sub_url = sub.get('url')
                if not sub_url:
                    continue
                lang = sub.get('locale') or self._DEFAULT_LANGUAGE_CODES[bu]
                subtitles.setdefault(lang, []).append({
                    'url': sub_url,
                })

        return {
            'id': media_id,
            'title': title,
            'description': media_data.get('description'),
            'timestamp': parse_iso8601(media_data.get('date')),
            'thumbnail': media_data.get('imageUrl'),
            'duration': float_or_none(media_data.get('duration'), 1000),
            'subtitles': subtitles,
            'formats': formats,
        }


class SRGSSRArticleIE(InfoExtractor):
    IE_DESC = 'Articles on srf.ch, rts.ch, rsi.ch, and rtr.ch with embedded media, see tests for examples'
    _VALID_URL = r'https?://(?:www\.)?(?P<bu>srf|rts|rsi|rtr)\.ch/(?!play/)(?:[^#?]+)'

    _TESTS = [{
        # Article from /news section with audio embed
        'url': 'https://www.srf.ch/news/international/groesste-anerkannte-minderheit-deutsche-minderheit-in-polen-nimmt-ab-die-gruende',
        'info_dict': {
            'id': '591cbc89-0ef2-4d54-9d68-8aa89f19e9ae',
            'ext': 'mp3',
            'title': 'Polen: Wie steht es um die anerkannte deutsche Minderheit?',
            'upload_date': '20251202',
            'timestamp': 1764670020,
            'duration': 283.716,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Article from /sport section with video embed
        'url': 'https://www.srf.ch/sport/ski-alpin/weltcup-maenner/riesenslalom-in-beaver-creek-luecke-geschlossen-odermatt-gewinnt-riesen-in-beaver-creek',
        'info_dict': {
            'id': '9e6a95fa-9fdb-4682-8285-57999f7934b9',
            'ext': 'mp4',
            'title': 'Odermatt mit einer taktischen Meisterleistung',
            'description': 'md5:bd2db64de40260c8dd15927553f25261',
            'upload_date': '20251207',
            'timestamp': 1765145748,
            'duration': 153.72,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # /audio URL with id parameter
        'url': 'https://www.srf.ch/audio/100-sekunden-wissen/ehrenamt-freiwilligenarbeit?id=AUDI20251205_RS_0097',
        'info_dict': {
            'id': '5620aba2-a9b5-312b-90c2-5ff6f3ae2ccf',
            'ext': 'mp3',
            'title': 'Ehrenamt / Freiwilligenarbeit',
            'upload_date': '20251205',
            'timestamp': 1764914040,
            'duration': 163.584,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # /audio URL with partId parameter (segment of a longer show)
        'url': 'https://www.srf.ch/audio/echo-der-zeit/polizei-geht-gegen-kriminelle-webshops-vor?partId=50b20dc8-f05b-4972-bf03-e438ff2833eb',
        'info_dict': {
            'id': '50b20dc8-f05b-4972-bf03-e438ff2833eb',
            'ext': 'mp3',
            'title': 'Polizei geht gegen kriminelle Webshops vor',
            'description': 'md5:c22e394a96484e154945cb043c36edcf',
            'upload_date': '20210223',
            'timestamp': 1614099600,
            'duration': 238.08,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # RTR /novitads article with audio embed
        'url': 'https://www.rtr.ch/novitads/il-di/novitads-dals-07-12-2025-legalisaziun-da-cannabis-en-svizra-vesan-partidas-fitg-different',
        'info_dict': {
            'id': 'df13a8b1-0fd3-3db3-a326-07beae5a5df9',
            'ext': 'mp3',
            'title': 'Co legalisar il Cannabis en Svizra divida las partidas',
            'upload_date': '20251207',
            'timestamp': 1765125000,
            'duration': 143.184,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # RTR /audio URL
        'url': 'https://www.rtr.ch/audio/actualitad/rimnar-films-e-fotografias-veglias-ch-en-en-surchombras-privats?id=AUDI20251207_NR_0054',
        'info_dict': {
            'id': '3afd546b-9a71-3bb7-9ea5-9dda1d72c339',
            'ext': 'mp3',
            'title': r"Rimnar films e fotografias veglias ch'èn en surchombras privats",
            'upload_date': '20251207',
            'timestamp': 1765099860,
            'duration': 222.096,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        article_id = self._generic_id(url)

        webpage = self._download_webpage(url, article_id)

        # Look for embedded URN in the page
        urn = self._search_regex(
            r'(urn:(?:srf|rts|rsi|rtr|swi):(?:video|audio):[a-f0-9-]+)',
            webpage, 'media URN', default=None)

        if urn:
            # Pass the URN directly to SRGSSR extractor
            return self.url_result(urn, 'SRGSSR')

        # Fallback: no URN found
        raise ExtractorError('No video or audio found in article')


class SRGSSRPlayIE(InfoExtractor):
    IE_DESC = 'srf.ch, rts.ch, rsi.ch, rtr.ch and swissinfo.ch play sites'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:(?:www|play)\.)?
                        (?P<bu>srf|rts|rsi|rtr|swissinfo)\.ch/play/(?:tv|radio)/
                        (?:
                            [^/]+/(?P<type>video|audio)/[^?]+|
                            popup(?P<type_2>video|audio)player
                        )
                        \?.*?\b(?:id=|urn=urn:(?:[^:]+:)+(?:video|audio):(?:[^:]+:)?)(?P<id>[0-9a-f\-]{36}|\d+)
                    '''

    _TESTS = [{
        'url': 'http://www.srf.ch/play/tv/10vor10/video/snowden-beantragt-asyl-in-russland?id=28e1a57d-5b76-4399-8ab3-9097f071e6c5',
        'md5': '81c6ad90d774c46e3c54ea2f01a94db3',
        'info_dict': {
            'id': '28e1a57d-5b76-4399-8ab3-9097f071e6c5',
            'ext': 'mp4',
            'upload_date': '20130701',
            'title': 'Snowden beantragt Asyl in Russland',
            'timestamp': 1372708215,
            'duration': 113.827,
            'thumbnail': r're:^https?://.*\.png$',
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'http://www.rtr.ch/play/radio/actualitad/audio/saira-tujetsch-tuttina-cuntinuar-cun-sedrun-muster-turissem?id=63cb0778-27f8-49af-9284-8c7a8c6d15fc',
        'info_dict': {
            'id': '63cb0778-27f8-49af-9284-8c7a8c6d15fc',
            'ext': 'mp3',
            'upload_date': '20151013',
            'title': 'Saira: Tujetsch - tuttina cuntinuar cun Sedrun Mustér Turissem',
            'timestamp': 1444709160,
            'duration': 336.816,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': 'Audio no longer available',
    }, {
        'url': 'https://www.rtr.ch/play/radio/_/audio/_?id=63cb0778-27f8-49af-9284-8c7a8c6d15fc&urn=urn:rtr:audio:63cb0778-27f8-49af-9284-8c7a8c6d15fc',
        'only_matching': True,
    }, {
        'url': 'https://www.rts.ch/play/tv/19h30/video/le-19h30?urn=urn:rts:video:6348260',
        'md5': '67a2a9ae4e8e62a68d0e9820cc9782df',
        'info_dict': {
            'id': '6348260',
            'display_id': '6348260',
            'ext': 'mp4',
            'duration': 1796.76,
            'title': 'Le 19h30',
            'upload_date': '20141201',
            'timestamp': 1417458600,
            'thumbnail': r're:^https?://.*\.image',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.rts.ch/play/tv/-/video/le-19h30?id=6348260',
        'only_matching': True,
    }, {
        'url': 'http://play.swissinfo.ch/play/tv/business/video/why-people-were-against-tax-reforms?id=42960270',
        'info_dict': {
            'id': '42960270',
            'ext': 'mp4',
            'title': 'Why people were against tax reforms',
            'description': 'md5:7ac442c558e9630e947427469c4b824d',
            'duration': 94.0,
            'upload_date': '20170215',
            'timestamp': 1487173560,
            'thumbnail': r're:https?://www\.swissinfo\.ch/srgscalableimage/42961964',
            'subtitles': 'count:9',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Video no longer available, site discontinued',
    }, {
        'url': 'https://www.srf.ch/play/tv/popupvideoplayer?id=c4dba0ca-e75b-43b2-a34f-f708a4932e01',
        'only_matching': True,
    }, {
        'url': 'https://www.srf.ch/play/tv/10vor10/video/snowden-beantragt-asyl-in-russland?urn=urn:srf:video:28e1a57d-5b76-4399-8ab3-9097f071e6c5',
        'only_matching': True,
    }, {
        # RTS video with swisstxt numeric ID
        'url': 'https://www.rts.ch/play/tv/19h30/video/le-19h30?urn=urn:rts:video:6348260',
        'md5': '67a2a9ae4e8e62a68d0e9820cc9782df',
        'info_dict': {
            'id': '6348260',
            'display_id': '6348260',
            'ext': 'mp4',
            'duration': 1796.76,
            'title': 'Le 19h30',
            'upload_date': '20141201',
            'timestamp': 1417458600,
            'thumbnail': r're:^https?://.*\.image',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # RTS video with UUID
        'url': 'https://www.rts.ch/play/tv/mise-au-point/video/le-business-des-films-de-nol?urn=urn:rts:video:67e97e4c-3967-339a-8f56-7b34be37f583',
        'info_dict': {
            'id': '67e97e4c-3967-339a-8f56-7b34be37f583',
            'ext': 'mp4',
            'title': 'Le business des films de Noël',
            'description': 'md5:9843edf847b7fbed8890632c01786072',
            'upload_date': '20251205',
            'timestamp': 1764946800,
            'duration': 803.0,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # SRF video with UUID
        'url': 'https://www.srf.ch/play/tv/einstein/video/ki-im-kopf---machen-uns-chatgpt-und-co--dumm?urn=urn:srf:video:c4db64a2-67cf-4bec-93bd-4a6747a077b7',
        'info_dict': {
            'id': 'c4db64a2-67cf-4bec-93bd-4a6747a077b7',
            'ext': 'mp4',
            'title': 'KI im Kopf – Machen uns ChatGPT und Co. dumm?',
            'description': 'md5:b89602f94f7c345fbd3d5fc4992b1337',
            'upload_date': '20251204',
            'timestamp': 1764878700,
            'duration': 2231.96,
            'thumbnail': r're:^https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # audio segment, has podcastSdUrl of the full episode
        'url': 'https://www.srf.ch/play/radio/popupaudioplayer?id=50b20dc8-f05b-4972-bf03-e438ff2833eb',
        'only_matching': True,
    }, {
        'url': 'https://www.srf.ch/play/tv/-/video/formel-1-gp-abu-dhabi?urn=urn:swisstxt:video:srf:1818188',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        bu = mobj.group('bu')
        media_type = mobj.group('type') or mobj.group('type_2')
        media_id = mobj.group('id')

        # Check if this is a swisstxt URN (numeric ID)
        if media_id.isdigit() and 'urn=urn:swisstxt:' in url:
            # Pass the swisstxt URN format directly to SRGSSR
            return self.url_result(f'urn:swisstxt:{media_type}:{bu[:3]}:{media_id}', 'SRGSSR')

        return self.url_result(f'srgssr:{bu[:3]}:{media_type}:{media_id}', 'SRGSSR')

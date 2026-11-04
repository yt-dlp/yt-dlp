import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    ISO639Utils,
    UnsupportedError,
    base_url,
    filter_dict,
    float_or_none,
    parse_age_limit,
    parse_qs,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class CeskaTelevizeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:
            (?:www\.)?ceskatelevize\.cz/(?:ivysilani(?!/(?:kategorie|vypis)\b)|porady|zive)|
            (?:sport\.ceskatelevize\.cz|ct24\.ceskatelevize\.cz/video)(?=/zive-vysilani(?:[/?#]|$))
        )/(?:[^/?#&]+/)*(?P<id>[^/#?]+)'''
    _API_BASE = 'https://api.ceskatelevize.cz/video/v1'
    _TESTS = [{
        'url': 'https://www.ceskatelevize.cz/porady/10441294653-hyde-park-civilizace/bonus/45890/',
        'info_dict': {
            'id': 'BO-45890',
            'ext': 'mp4',
            'title': 'Interview with Walter Villadei - Hyde Park Civilizace',
            'description': 'Interview with astronaut Walter Villadei',
            'display_id': '45890',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2295.0,
        },
        'params': {'skip_download': 'dash'},
    }, {
        # live stream
        'url': 'https://www.ceskatelevize.cz/zive/ct1/',
        'info_dict': {
            'id': '102',
            'ext': 'mp4',
            'title': r're:^ČT1 - živé vysílání online',
            'description': r're:^Sledujte živé vysílání kanálu ČT1',
            'display_id': 'ct1',
            'thumbnail': r're:^https?://.*',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'livestream'},
    }, {
        'url': 'https://www.ceskatelevize.cz/zive/ct2/',
        'only_matching': True,
    }, {
        # /zive/sport/ redirects here
        'url': 'https://sport.ceskatelevize.cz/zive-vysilani',
        'info_dict': {
            'id': '402',
            'ext': 'mp4',
            'title': r're:^Živé vysílání — ČT sport',
            'display_id': 'zive-vysilani',
            'thumbnail': r're:^https?://.*',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'livestream'},
    }, {
        # /zive/ct24/ redirects here
        'url': 'https://ct24.ceskatelevize.cz/video/zive-vysilani',
        'info_dict': {
            'id': '2402',
            'ext': 'mp4',
            'title': r're:.+ČT24',
            'description': str,
            'display_id': 'zive-vysilani',
            'thumbnail': r're:^https?://.*',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'livestream'},
    }, {
        # old embed player, IDEC is taken from the URL
        'url': 'https://www.ceskatelevize.cz/ivysilani/embed/iFramePlayer.php?hash=d6a3e1370d2e4fa76296b90bad4dfc19673b641e&IDEC=217 562 22150/0004&channelID=1&width=100%25',
        'info_dict': {
            'id': '217562221500004',
            'ext': 'mp4',
            'title': 'Toulavá kamera 2017 | Toulavá kamera | 4',
            'thumbnail': r're:^https?://.*',
            'duration': 1750.04,
            'subtitles': {'cs': 'count:2'},
        },
        'params': {'skip_download': 'dash'},
    }, {
        # 18+ age restriction
        'url': 'https://www.ceskatelevize.cz/porady/10520528904-queer/215562210900007-bogotart/',
        'info_dict': {
            'id': '215562210900007',
            'ext': 'mp4',
            'title': 'Bogotart - Queer',
            'description': 'Hlavní město Kolumbie v doprovodu queer umělců. Vroucí svět plný vášně, sebevědomí, ale i násilí a bolesti',
            'display_id': '215562210900007-bogotart',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 1556.0,
            'age_limit': 18,
        },
        'params': {'skip_download': 'dash'},
    }, {
        'url': 'https://www.ceskatelevize.cz/porady/10614999031-neviditelni/21251212048/',
        'only_matching': True,
    }, {
        'url': 'https://www.ceskatelevize.cz/ivysilani/10520528904-queer/215562210900007-bogotart/',
        'only_matching': True,
    }, {
        # series page, extracts the episode its play button opens
        'url': 'https://www.ceskatelevize.cz/porady/10195164142-vypravej/',
        'info_dict': {
            'id': '208522161400001',
            'ext': 'mp4',
            'title': 'Vyprávěj | Od začátku | 1',
            'series': 'Vyprávěj',
            'display_id': '10195164142-vypravej',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 3124.24,
            'subtitles': {'cs': 'count:2'},
        },
        'params': {'skip_download': 'dash'},
    }, {
        # has an audio description track
        'url': 'https://www.ceskatelevize.cz/porady/10213309156-cirkus-havel/',
        'info_dict': {
            'id': '409235100021004',
            'ext': 'm4a',
            'title': 'Cirkus Havel',
            'description': r're:^Václav Havel, prezident, filozof',
            'display_id': '10213309156-cirkus-havel',
            'thumbnail': r're:^https?://.*',
            'duration': 3384.92,
            'format_note': 'Audio description',
            'subtitles': {'cs': 'count:2'},
        },
        'params': {
            'format': 'ba[format_note="Audio description"]',
            'skip_download': 'dash',
        },
    }, {
        # programme split into several parts
        'url': 'https://www.ceskatelevize.cz/ivysilani/embed/iFramePlayer.php?IDEC=217 543 11205/0027',
        'info_dict': {
            'id': '217543112050027',
            'title': 'Wifina | Wifina | 27',
            'thumbnail': r're:^https?://.*',
        },
        'playlist': [{
            'info_dict': {
                'id': '217543112050027-1',
                'ext': 'mp4',
                'title': 'Wifina | Wifina | 27',
                'thumbnail': r're:^https?://.*',
                'duration': 977.0,
            },
        }, {
            'info_dict': {
                'id': '217543112050027-2',
                'ext': 'mp4',
                'title': 'Wifina | Wifina | 27',
                'thumbnail': r're:^https?://.*',
                'duration': 539.0,
            },
        }],
        'params': {'skip_download': 'dash'},
    }]

    def _call_api(self, path, video_id, stream_type):
        data = self._download_json(
            f'{self._API_BASE}/{path}', video_id, f'Downloading {stream_type.upper()} stream data',
            query={'canPlayDrm': 'false', 'streamType': stream_type},
            expected_status=lambda status: 400 <= status < 500)
        if not data.get('error'):
            return data

        status = traverse_obj(data, ('message', 'status', 'name', {str}))
        message = (
            traverse_obj(data, ('message', 'labels', ('textLong', 'textShort'), {str}, filter, any))
            or traverse_obj(data, ('error', (None, 'type'), {str}, any)))
        if status == 'UNSUPPORTED_GEOLOCATION':
            self.raise_geo_restricted(message, countries=['CZ'])
        if status == 'UNSUPPORTED_DRM':
            self.report_drm(video_id)
        raise ExtractorError(f'{self.IE_NAME} said: {message}', expected=True)

    def _extract_vod(self, path, video_id, extra_info):
        # Programmes with parts cut out (e.g. for licensing reasons) are split into several streams
        parts = []
        for stream_type in ('dash', 'hls'):
            data = self._call_api(f'playlist-vod/v1/stream-data/{path}', video_id, stream_type)
            streams = traverse_obj(data, ('streams', lambda _, v: url_or_none(v['url'])))
            for idx, stream in enumerate(streams):
                if idx == len(parts):
                    parts.append({
                        'formats': [],
                        'subtitles': self._parse_subtitles(stream),
                        'duration': float_or_none(stream.get('duration')),
                    })
                for key, format_id in (('url', stream_type), ('audioDescriptionUrl', f'{stream_type}-ad')):
                    manifest_url = url_or_none(stream.get(key))
                    if not manifest_url:
                        continue
                    if stream_type == 'dash':
                        fmts, subs = self._extract_mpd_formats_from_location(manifest_url, video_id, format_id)
                    else:
                        fmts, subs = self._extract_m3u8_formats_and_subtitles(
                            manifest_url, video_id, 'mp4', m3u8_id=format_id, fatal=False)
                    if key == 'audioDescriptionUrl':
                        # The DASH manifest repeats the main video as a separate video-only format; drop it.
                        # HLS has no codec info, so its variants (video muxed with the narration) are kept
                        fmts = [{
                            **f,
                            'format_note': 'Audio description',
                            'language_preference': -10,
                        } for f in fmts if f.get('acodec') != 'none']
                    parts[idx]['formats'].extend(fmts)
                    self._merge_subtitles(subs, target=parts[idx]['subtitles'])

        info = {
            **traverse_obj(data, {
                'title': ('title', {str}),
                'thumbnail': ('previewImageUrl', {url_or_none}),
                'age_limit': ('labeling', ..., 'text', {parse_age_limit}, any),
            }),
            **filter_dict(extra_info),
        }
        if len(parts) == 1:
            return {'id': video_id, **info, **parts[0]}
        return self.playlist_result(
            [{'id': f'{video_id}-{idx}', **info, **part} for idx, part in enumerate(parts, 1)],
            video_id, multi_video=True, **info)

    def _extract_mpd_formats_from_location(self, mpd_url, video_id, mpd_id):
        res = self._download_xml_handle(mpd_url, video_id, 'Downloading MPD manifest', fatal=False)
        if not res or res[0] is None:
            return [], {}
        mpd_doc, urlh = res
        # ffmpeg can't read the chunked manifest served by the tokenized URL, so use the MPD's own Location
        mpd_url = url_or_none(mpd_doc.findtext('{urn:mpeg:dash:schema:mpd:2011}Location')) or urlh.url
        return self._parse_mpd_formats_and_subtitles(mpd_doc, mpd_id, base_url(mpd_url), mpd_url)

    @staticmethod
    def _parse_subtitles(stream):
        subtitles = {}
        for sub in traverse_obj(stream, ('subtitles', lambda _, v: v['files'])):
            lang = ISO639Utils.long2short(sub.get('language')) or sub.get('language') or 'cs'
            for sub_file in traverse_obj(sub, (
                    'files', lambda _, v: url_or_none(v['url']) and v['format'] in ('vtt', 'ttml'))):
                subtitles.setdefault(lang, []).append({
                    'url': sub_file['url'],
                    'ext': sub_file['format'],
                })
        return subtitles

    def _extract_live(self, channel, video_id, extra_info):
        data = self._call_api(f'playlist-live/v1/stream-data/channel/{channel}', video_id, 'hls')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            data['streamUrls']['main'], video_id, 'mp4', m3u8_id='hls', live=True)
        return {
            'id': str_or_none(data.get('id')) or video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'thumbnail': ('previewImageUrl', {url_or_none}),
            }),
            **filter_dict(extra_info),
        }

    @staticmethod
    def _clean_idec(idec):
        # IDECs are often written with separators, e.g. "217 562 22150/0004"
        return re.sub(r'\D', '', idec)

    def _real_extract(self, url):
        display_id = self._match_id(url)

        # The old iFramePlayer.php embed is gone, but its URL still contains the IDEC
        if idec := traverse_obj(parse_qs(url), ('IDEC', -1, {self._clean_idec})):
            return self._extract_vod(f'media/external/{idec}', idec, {})

        webpage, urlh = self._download_webpage_handle(url, display_id)
        # e.g. /zive/ct4/ redirects to the /ivysilani/ homepage
        if not self.suitable(urlh.url):
            raise UnsupportedError(urlh.url)

        title = self._og_search_title(webpage, default='').replace('\xa0', ' ')
        site_name = self._og_search_property('site_name', webpage, default='Česká televize')
        description = self._html_search_meta(['og:description', 'description'], webpage, default='')
        page_info = {
            'display_id': display_id,
            'title': re.split(rf'\s+[—|-]\s+(?:iVysílání|{re.escape(site_name)})', title, maxsplit=1)[0] or None,
            'description': description.replace('\xa0', ' ') or None,
        }

        next_data = self._search_nextjs_data(webpage, display_id)
        page_data = traverse_obj(next_data, ('props', 'pageProps', 'data', {dict})) or {}

        # Live pages of the main site, ČT sport and ČT24
        if live_data := traverse_obj(next_data, (
                'props', 'pageProps', (('data', 'liveBroadcast'), 'liveData', 'videoModel'), {dict}, any)):
            # current is null while the channel is off air, but the id is still the encoder
            encoder = traverse_obj(live_data, ((('current', 'encoder'), 'id'), {str}, any))
            if not encoder:
                raise ExtractorError('Unable to extract live channel')
            return self._extract_live(encoder, display_id, page_info)

        if bonus_id := traverse_obj(page_data, ('videobonusDetail', 'bonusId', {str_or_none})):
            bonus_id = f'BO-{bonus_id}'
            return self._extract_vod(f'bonus/{bonus_id}', bonus_id, page_info)

        if idec := traverse_obj(page_data, ('mediaMeta', 'idec', {str}, {self._clean_idec}, filter)):
            return self._extract_vod(f'media/external/{idec}', idec, page_info)

        # Series pages describe the show; extract the episode their play button opens
        # (the first one, or the latest one for running shows) with its own metadata
        if idec := traverse_obj(page_data, ('show', 'actionButton', 'idec', {str}, {self._clean_idec}, filter)):
            return self._extract_vod(f'media/external/{idec}', idec, {
                'display_id': display_id,
                'series': traverse_obj(page_data, ('show', 'title', {str})),
            })

        # Pages of single programmes, e.g. films
        idec = traverse_obj(page_data, ('show', 'idec', {str}, {self._clean_idec}, filter))
        if not idec:
            raise ExtractorError('Unable to extract IDEC')
        return self._extract_vod(f'media/external/{idec}', idec, page_info)

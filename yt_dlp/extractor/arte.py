import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    GeoRestrictedError,
    ExtractorError,
    int_or_none,
    parse_iso8601,
    parse_qs,
    strip_or_none,
    try_get,
    url_or_none,
)


class ArteTVBaseIE(InfoExtractor):
    _ARTE_LANGUAGES = 'fr|de|en|es|it|pl'
    _API_BASE = 'https://api.arte.tv/api/player/v2'


class ArteTVIE(ArteTVBaseIE):
    _VALID_URL = r'''(?x)
                    (?:https?://
                        (?:
                            (?:www\.)?arte\.tv/(?P<lang>%(langs)s)/videos|
                            api\.arte\.tv/api/player/v\d+/config/(?P<lang_2>%(langs)s)
                        )
                    |arte://program)
                        /(?P<id>\d{6}-\d{3}-[AF]|LIVE)
                    ''' % {'langs': ArteTVBaseIE._ARTE_LANGUAGES}
    _TESTS = [{
        'url': 'https://www.arte.tv/en/videos/088501-000-A/mexico-stealing-petrol-to-survive/',
        'info_dict': {
            'id': '088501-000-A',
            'title': 'Mexico: Stealing Petrol to Survive',
            'alt_title': 'ARTE Reportage',
            'description': 'md5:35ec9baaa8ad0b2456447c7972ba3ca0',
            'duration': 1428,
            'thumbnail': 'https://api-cdn.arte.tv/api/mami/v1/program/en/088501-000-A/940x530?ts=1626083168',
            'upload_date': '20190628',
            'timestamp': 1561759200,
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.arte.tv/pl/videos/100103-000-A/usa-dyskryminacja-na-porodowce/',
        'info_dict': {
            'id': '100103-000-A',
            'title': 'USA: Dyskryminacja na porodówce',
            'description': 'md5:242017b7cce59ffae340a54baefcafb1',
            'alt_title': 'ARTE Reportage',
            'upload_date': '20201103',
            'duration': 554,
            'thumbnail': 'https://api-cdn.arte.tv/api/mami/v1/program/pl/100103-000-A/940x530?ts=1625425425',
            'timestamp': 1604417980,
            'ext': 'mp4',
        },
    }, {
        'url': 'https://api.arte.tv/api/player/v2/config/de/100605-013-A',
        'only_matching': True,
    }, {
        'url': 'https://api.arte.tv/api/player/v2/config/de/LIVE',
        'only_matching': True,
    }]

    _GEO_BYPASS = True

    # Reference formerly available at: section 6.8 of
    # <https://www.arte.tv/sites/en/corporate/files/complete-technical-guidelines-arte-geie-v1-07-1.pdf>

    __LANG_MAP = {       # the RHS are not ISO codes, but French abbreviations
        'fr': 'F',       # françois
        'de': 'A',       # allemand
        'en': 'E[ANG]',  # européen(?) [anglais]
        'es': 'E[ESP]',  # européen(?) [espagnol]
        'it': 'E[ITA]',  # européen(?) [italien]
        'pl': 'E[POL]',  # européen(?) [polonais]

        # XXX: probably means mixed; <https://www.arte.tv/en/videos/107710-029-A/dispatches-from-ukraine-local-journalists-report/>
        # uses this code for audio that happens to be in Ukrainian, but the manifest uses the ISO code 'mul' (mixed)
        'mul': 'EU',
    }

    __VERSION_CODE_RE = re.compile(r'''(?x)
        V
        (?P<vo>O?)                           # original voice track
        (?P<vlang>[FA]|E\[[A-Z]+\]|EU)?      # language of voice track
        (?P<vaud>AUD|)                       # audio description
        (?:
            (?P<st>-ST)                      # subtitles
            (?P<stm>M?)                      # subtitles for the hard of hearing
            (?P<stlang>[FA]|E\[[A-Z]+\]|EU)  # subtitle language
        )?
    ''')

    # all obtained by exhaustive testing
    __GEO_COUNTRIES = {
        'DE_FR': frozenset((
            'BL', 'DE', 'FR', 'GF', 'GP', 'MF', 'MQ', 'NC',
            'PF', 'PM', 'RE', 'WF', 'YT',
        )),
        # with both of the below 'BE' sometimes works, sometimes doesn't
        'EUR_DE_FR': frozenset((
            'AT', 'BL', 'CH', 'DE', 'FR', 'GF', 'GP', 'LI',
            'MC', 'MF', 'MQ', 'NC', 'PF', 'PM', 'RE', 'WF',
            'YT',
        )),
        'SAT': frozenset((
            'AD', 'AT', 'AX', 'BG', 'BL', 'CH', 'CY', 'CZ',
            'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GF',
            'GR', 'HR', 'HU', 'IE', 'IS', 'IT', 'KN', 'LI',
            'LT', 'LU', 'LV', 'MC', 'MF', 'MQ', 'MT', 'NC',
            'NL', 'NO', 'PF', 'PL', 'PM', 'PT', 'RE', 'RO',
            'SE', 'SI', 'SK', 'SM', 'VA', 'WF', 'YT',
        )),
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        lang = mobj.group('lang') or mobj.group('lang_2')

        config = self._download_json(
            f'{self._API_BASE}/config/{lang}/{video_id}', video_id)

        # XXX: config['data']['attributes']['restriction']
        # is sometimes null for videos that are not available
        # at all (any more?)

        restriction = config['data']['attributes']['restriction'] or {}
        geoblocking = restriction.get('geoblocking') or {}
        if geoblocking.get('restrictedArea'):
            raise GeoRestrictedError(
                f'Video restricted to {geoblocking["code"]!r}',
                countries=self.__GEO_COUNTRIES.get(geoblocking['code'], ('DE', 'FR')))

        rights = config['data']['attributes']['rights']

        # e.g. <https://www.arte.tv/de/videos/097407-215-A/28-minuten/>
        # e.g. <https://www.arte.tv/es/videos/104351-002-A/serviteur-du-peuple-1-23/>
        # (videos that are completely nonexistent return HTTP 404)

        if rights is None:
            raise ExtractorError('Video is not available in this language edition of Arte or broadcast rights expired', expected=True)

        metadata = config['data']['attributes']['metadata']

        formats = []
        subtitles = {}

        for stream in config['data']['attributes']['streams']:
            # official player contains code like `e.get("versions")[0].eStat.ml5`,
            # which blindly assumes this structure, so I feel emboldened to do as well
            stream_version = stream['versions'][0]
            stream_version_code = stream_version['eStat']['ml5']

            lang_pref = -1
            m = self.__VERSION_CODE_RE.match(stream_version_code)
            if m:
                lc = self.__LANG_MAP.get(lang)
                lang_pref = sum(
                    pref << i
                    for i, pref in enumerate(reversed((
                        m.group('vlang') == lc,   # we prefer voice in the requested language
                        not m.group('vaud'),      # and not the audio description version
                        bool(m.group('vo')),      # but if voice is not in the requested language, at least choose the original voice
                        m.group('stlang') == lc,  # if subtitles are present, we prefer them in the requested language
                        not m.group('st'),        # but we prefer no subtitles otherwise
                        not m.group('stm'),       # and we prefer not the hard-of-hearing subtitles if there are subtitles
                    )))
                )

            # XXX: probably not worth warning about if no match

            if stream['protocol'].startswith('HLS'):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    stream['url'], video_id=video_id, ext='mp4',
                    m3u8_id=stream_version_code, fatal=False,
                )

                for fmt in fmts:
                    fmt.update({
                        'format_note': f'{stream_version.get("label", "unknown")} [{stream_version.get("shortLabel", "?")}]',
                        'language_preference': lang_pref,
                    })

                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
                continue

            if stream['protocol'] in ('HTTPS', 'RTMP'):
                formats.append({
                    'format_id': f'{stream["protocol"]}-{stream_version_code}',
                    'url': stream['url'],
                    'format_note': f'{stream_version.get("label", "unknown")} [{stream_version.get("shortLabel", "?")}]',
                    'language_preference': lang_pref,
                    # 'ext': 'mp4',  # XXX: may or may not be necessary, at least for HTTPS
                })
                continue

            self.report_warning(
                f'Skipping stream with unknown protocol {stream["protocol"]}')

            # XXX: chapters from stream['segments']?
            # the JS also apparently looks for chapters in
            # config['data']['attributes']['chapters'], but
            # I am yet to find a video having those

        self._sort_formats(formats)

        thumbnails = []
        for image in metadata['images']:
            thumbnails.append({
                'url': image['url'],
                'description': image['caption'],
            })

        return {
            'id': metadata['providerId'],
            'webpage_url': metadata.get('link', {}).get('url'),
            'title': metadata['title'],
            'alt_title': metadata.get('subtitle'),
            'description': metadata.get('description'),
            'duration': metadata.get('duration', {}).get('seconds'),
            'language': metadata.get('language'),
            # XXX: nominally different, but seems to contain the information we want
            'timestamp': parse_iso8601(rights.get('begin')),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': config['data']['attributes'].get('live', False),
        }


class ArteTVEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?arte\.tv/player/v\d+/index\.php\?.*?\bjson_url=.+'
    _TESTS = [{
        'url': 'https://www.arte.tv/player/v5/index.php?json_url=https%3A%2F%2Fapi.arte.tv%2Fapi%2Fplayer%2Fv2%2Fconfig%2Fde%2F100605-013-A&lang=de&autoplay=true&mute=0100605-013-A',
        'only_matching': True,
    }, {
        'url': 'https://www.arte.tv/player/v3/index.php?json_url=https://api.arte.tv/api/player/v2/config/de/100605-013-A',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [url for _, url in re.findall(
            r'<(?:iframe|script)[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?arte\.tv/player/v\d+/index\.php\?.*?\bjson_url=.+?)\1',
            webpage)]

    def _real_extract(self, url):
        qs = parse_qs(url)
        json_url = qs['json_url'][0]
        video_id = ArteTVIE._match_id(json_url)
        return self.url_result(
            json_url, ie=ArteTVIE.ie_key(), video_id=video_id)


class ArteTVPlaylistIE(ArteTVBaseIE):
    _VALID_URL = r'https?://(?:www\.)?arte\.tv/(?P<lang>%s)/videos/(?P<id>RC-\d{6})' % ArteTVBaseIE._ARTE_LANGUAGES
    _TESTS = [{
        'url': 'https://www.arte.tv/en/videos/RC-016954/earn-a-living/',
        'only_matching': True,
    }, {
        'url': 'https://www.arte.tv/pl/videos/RC-014123/arte-reportage/',
        'playlist_mincount': 100,
        'info_dict': {
            'description': 'md5:84e7bf1feda248bc325ebfac818c476e',
            'id': 'RC-014123',
            'title': 'ARTE Reportage - najlepsze reportaże',
        },
    }]

    def _real_extract(self, url):
        lang, playlist_id = self._match_valid_url(url).groups()
        playlist = self._download_json(
            f'{self._API_BASE}/playlist/{lang}/{playlist_id}', playlist_id)
        metadata = playlist['data']['attributes']['metadata']
        entries = []
        for video in playlist['data']['attributes']['items']:
            if not isinstance(video, dict):
                continue
            video_url = video['config']['url']
            if not video_url:
                continue
            video_id = video.get('providerId')
            entries.append({
                '_type': 'url_transparent',
                'url': video_url,
                'id': video_id,
                'title': video.get('title'),
                'alt_title': video.get('subtitle'),
                'thumbnail': url_or_none(try_get(video, lambda x: x['mainImage']['url'], compat_str)),
                'duration': int_or_none(video.get('duration', {}).get('seconds')),
                'ie_key': ArteTVIE.ie_key(),
            })
        title = metadata.get('title')
        description = metadata.get('description')
        return self.playlist_result(entries, playlist_id, title, description)


class ArteTVCategoryIE(ArteTVBaseIE):
    _VALID_URL = r'https?://(?:www\.)?arte\.tv/(?P<lang>%s)/videos/(?P<id>[\w-]+(?:/[\w-]+)*)/?\s*$' % ArteTVBaseIE._ARTE_LANGUAGES
    _TESTS = [{
        'url': 'https://www.arte.tv/en/videos/politics-and-society/',
        'info_dict': {
            'id': 'politics-and-society',
            'title': 'Politics and society',
            'description': 'Investigative documentary series, geopolitical analysis, and international commentary',
        },
        'playlist_mincount': 13,
    }]

    @classmethod
    def suitable(cls, url):
        return (
            not any(ie.suitable(url) for ie in (ArteTVIE, ArteTVPlaylistIE, ))
            and super(ArteTVCategoryIE, cls).suitable(url))

    def _real_extract(self, url):
        lang, playlist_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, playlist_id)

        items = []
        for video in re.finditer(
                r'<a\b[^>]*?href\s*=\s*(?P<q>"|\'|\b)(?P<url>https?://www\.arte\.tv/%s/videos/[\w/-]+)(?P=q)' % lang,
                webpage):
            video = video.group('url')
            if video == url:
                continue
            if any(ie.suitable(video) for ie in (ArteTVIE, ArteTVPlaylistIE, )):
                items.append(video)

        title = (self._og_search_title(webpage, default=None)
                 or self._html_search_regex(r'<title\b[^>]*>([^<]+)</title>', default=None))
        title = strip_or_none(title.rsplit('|', 1)[0]) or self._generic_title(url)

        return self.playlist_from_matches(items, playlist_id=playlist_id, playlist_title=title,
                                          description=self._og_search_description(webpage, default=None))

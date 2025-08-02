import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    parse_qs,
    strip_or_none,
    traverse_obj,
    url_or_none,
)


class ArteTVBaseIE(InfoExtractor):
    _ARTE_LANGUAGES = 'fr|de|en|es|it|pl'
    _API_BASE = 'https://api.arte.tv/api/player/v2'


class ArteTVIE(ArteTVBaseIE):
    _VALID_URL = rf'''(?x)
                    (?:https?://
                        (?:
                            (?:www\.)?arte\.tv/(?P<lang>{ArteTVBaseIE._ARTE_LANGUAGES})/videos|
                            api\.arte\.tv/api/player/v\d+/config/(?P<lang_2>{ArteTVBaseIE._ARTE_LANGUAGES})
                        )
                    |arte://program)
                        /(?P<id>\d{{6}}-\d{{3}}-[AF]|LIVE)
                    '''
    _TESTS = [{
        'url': 'https://www.arte.tv/en/videos/088501-000-A/mexico-stealing-petrol-to-survive/',
        'only_matching': True,
    }, {
        'note': 'No alt_title',
        'url': 'https://www.arte.tv/fr/videos/110371-000-A/la-chaleur-supplice-des-arbres-de-rue/',
        'only_matching': True,
    }, {
        'url': 'https://api.arte.tv/api/player/v2/config/de/100605-013-A',
        'only_matching': True,
    }, {
        'url': 'https://api.arte.tv/api/player/v2/config/de/LIVE',
        'only_matching': True,
    }, {
        'url': 'https://www.arte.tv/de/videos/110203-006-A/zaz/',
        'only_matching': True,
    }, {
        'url': 'https://www.arte.tv/fr/videos/109067-000-A/la-loi-de-teheran/',
        'info_dict': {
            'id': '109067-000-A',
            'ext': 'mp4',
            'description': 'md5:d2ca367b8ecee028dddaa8bd1aebc739',
            'thumbnail': r're:https?://api-cdn\.arte\.tv/img/v2/image/.+',
            'timestamp': 1713927600,
            'duration': 7599,
            'title': 'La loi de Téhéran',
            'upload_date': '20240424',
            'subtitles': {
                'fr': 'mincount:1',
                'fr-acc': 'mincount:1',
                'fr-forced': 'mincount:1',
            },
        },
        'skip': 'Invalid URL',
    }, {
        'note': 'age-restricted',
        'url': 'https://www.arte.tv/de/videos/006785-000-A/the-element-of-crime/',
        'info_dict': {
            'id': '006785-000-A',
            'description': 'md5:c2f94fdfefc8a280e4dab68ab96ab0ba',
            'title': 'The Element of Crime',
            'thumbnail': r're:https?://api-cdn\.arte\.tv/img/v2/image/.+',
            'timestamp': 1696111200,
            'duration': 5849,
            'upload_date': '20230930',
            'ext': 'mp4',
        },
        'skip': '404 Not Found',
    }]

    _GEO_BYPASS = True

    _LANG_MAP = {  # ISO639 -> French abbreviations
        'fr': 'F',
        'de': 'A',
        'en': 'E[ANG]',
        'es': 'E[ESP]',
        'it': 'E[ITA]',
        'pl': 'E[POL]',
        # XXX: probably means mixed; <https://www.arte.tv/en/videos/107710-029-A/dispatches-from-ukraine-local-journalists-report/>
        # uses this code for audio that happens to be in Ukrainian, but the manifest uses the ISO code 'mul' (mixed)
        'mul': 'EU',
    }

    _VERSION_CODE_RE = re.compile(r'''(?x)
        V
        (?P<original_voice>O?)
        (?P<vlang>[FA]|E\[[A-Z]+\]|EU)?
        (?P<audio_desc>AUD|)
        (?:
            (?P<has_sub>-ST)
            (?P<sdh_sub>M?)
            (?P<sub_lang>[FA]|E\[[A-Z]+\]|EU)
        )?
    ''')

    # all obtained by exhaustive testing
    _COUNTRIES_MAP = {
        'DE_FR': (
            'BL', 'DE', 'FR', 'GF', 'GP', 'MF', 'MQ', 'NC',
            'PF', 'PM', 'RE', 'WF', 'YT',
        ),
        # with both of the below 'BE' sometimes works, sometimes doesn't
        'EUR_DE_FR': (
            'AT', 'BL', 'CH', 'DE', 'FR', 'GF', 'GP', 'LI',
            'MC', 'MF', 'MQ', 'NC', 'PF', 'PM', 'RE', 'WF',
            'YT',
        ),
        'SAT': (
            'AD', 'AT', 'AX', 'BG', 'BL', 'CH', 'CY', 'CZ',
            'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GF',
            'GR', 'HR', 'HU', 'IE', 'IS', 'IT', 'KN', 'LI',
            'LT', 'LU', 'LV', 'MC', 'MF', 'MQ', 'MT', 'NC',
            'NL', 'NO', 'PF', 'PL', 'PM', 'PT', 'RE', 'RO',
            'SE', 'SI', 'SK', 'SM', 'VA', 'WF', 'YT',
        ),
    }

    @staticmethod
    def _fix_accessible_subs_locale(subs):
        updated_subs = {}
        for lang, sub_formats in subs.items():
            for fmt in sub_formats:
                url = fmt.get('url') or ''
                suffix = ('acc' if url.endswith('-MAL.m3u8')
                          else 'forced' if '_VO' not in url
                          else None)
                updated_subs.setdefault(join_nonempty(lang, suffix), []).append(fmt)
        return updated_subs

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        lang = mobj.group('lang') or mobj.group('lang_2')
        language_code = self._LANG_MAP.get(lang)

        config = self._download_json(f'{self._API_BASE}/config/{lang}/{video_id}', video_id, headers={
            'x-validated-age': '18',
        })

        geoblocking = traverse_obj(config, ('data', 'attributes', 'restriction', 'geoblocking')) or {}
        if geoblocking.get('restrictedArea'):
            raise GeoRestrictedError(f'Video restricted to {geoblocking["code"]!r}',
                                     countries=self._COUNTRIES_MAP.get(geoblocking['code'], ('DE', 'FR')))

        if not traverse_obj(config, ('data', 'attributes', 'rights')):
            # Eg: https://www.arte.tv/de/videos/097407-215-A/28-minuten
            # Eg: https://www.arte.tv/es/videos/104351-002-A/serviteur-du-peuple-1-23
            raise ExtractorError(
                'Video is not available in this language edition of Arte or broadcast rights expired', expected=True)

        formats, subtitles = [], {}
        secondary_formats = []
        for stream in config['data']['attributes']['streams']:
            # official player contains code like `e.get("versions")[0].eStat.ml5`
            stream_version = stream['versions'][0]
            stream_version_code = stream_version['eStat']['ml5']

            lang_pref = -1
            m = self._VERSION_CODE_RE.match(stream_version_code)
            if m:
                lang_pref = int(''.join('01'[x] for x in (
                    m.group('vlang') == language_code,      # we prefer voice in the requested language
                    not m.group('audio_desc'),              # and not the audio description version
                    bool(m.group('original_voice')),        # but if voice is not in the requested language, at least choose the original voice
                    m.group('sub_lang') == language_code,   # if subtitles are present, we prefer them in the requested language
                    not m.group('has_sub'),                 # but we prefer no subtitles otherwise
                    not m.group('sdh_sub'),                 # and we prefer not the hard-of-hearing subtitles if there are subtitles
                )))

            short_label = traverse_obj(stream_version, 'shortLabel', expected_type=str, default='?')
            if 'HLS' in stream['protocol']:
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    stream['url'], video_id=video_id, ext='mp4', m3u8_id=stream_version_code, fatal=False)
                for fmt in fmts:
                    fmt.update({
                        'format_note': f'{stream_version.get("label", "unknown")} [{short_label}]',
                        'language_preference': lang_pref,
                    })
                if any(map(short_label.startswith, ('cc', 'OGsub'))):
                    secondary_formats.extend(fmts)
                else:
                    formats.extend(fmts)
                subs = self._fix_accessible_subs_locale(subs)
                self._merge_subtitles(subs, target=subtitles)

            elif stream['protocol'] in ('HTTPS', 'RTMP'):
                formats.append({
                    'format_id': f'{stream["protocol"]}-{stream_version_code}',
                    'url': stream['url'],
                    'format_note': f'{stream_version.get("label", "unknown")} [{short_label}]',
                    'language_preference': lang_pref,
                    # 'ext': 'mp4',  # XXX: may or may not be necessary, at least for HTTPS
                })

            else:
                self.report_warning(f'Skipping stream with unknown protocol {stream["protocol"]}')

        formats.extend(secondary_formats)
        self._remove_duplicate_formats(formats)

        metadata = config['data']['attributes']['metadata']

        return {
            'id': metadata['providerId'],
            'webpage_url': traverse_obj(metadata, ('link', 'url')),
            'title': traverse_obj(metadata, 'subtitle', 'title'),
            'alt_title': metadata.get('subtitle') and metadata.get('title'),
            'description': metadata.get('description'),
            'duration': traverse_obj(metadata, ('duration', 'seconds')),
            'language': metadata.get('language'),
            'timestamp': traverse_obj(config, ('data', 'attributes', 'rights', 'begin'), expected_type=parse_iso8601),
            'is_live': config['data']['attributes'].get('live', False),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [
                {'url': image['url'], 'id': image.get('caption')}
                for image in metadata.get('images') or [] if url_or_none(image.get('url'))
            ],
            # TODO: chapters may also be in stream['segments']?
            'chapters': traverse_obj(config, ('data', 'attributes', 'chapters', 'elements', ..., {
                'start_time': 'startTime',
                'title': 'title',
            })) or None,
        }


class ArteTVEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?arte\.tv/player/v\d+/index\.php\?.*?\bjson_url=.+'
    _EMBED_REGEX = [r'<(?:iframe|script)[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?arte\.tv/player/v\d+/index\.php\?.*?\bjson_url=.+?)\1']
    _TESTS = [{
        'url': 'https://www.arte.tv/player/v5/index.php?json_url=https%3A%2F%2Fapi.arte.tv%2Fapi%2Fplayer%2Fv2%2Fconfig%2Fde%2F100605-013-A&lang=de&autoplay=true&mute=0100605-013-A',
        'info_dict': {
            'id': '100605-013-A',
            'ext': 'mp4',
            'title': 'United we Stream November Lockdown Edition #13',
            'description': 'md5:be40b667f45189632b78c1425c7c2ce1',
            'upload_date': '20201116',
        },
        'skip': 'No video available',
    }, {
        'url': 'https://www.arte.tv/player/v3/index.php?json_url=https://api.arte.tv/api/player/v2/config/de/100605-013-A',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # FIXME: Embed detection
        'url': 'https://timesofmalta.com/article/watch-sunken-warships-north-sea-arte.1108358',
        'info_dict': {
            'id': '110288-000-A',
            'ext': 'mp4',
            'title': 'Danger on the Seabed',
            'alt_title': 'Sunken Warships in the North Sea',
            'description': 'md5:a2c84cbad37d280bddb6484087120add',
            'duration': 3148,
            'thumbnail': r're:https?://api-cdn\.arte\.tv/img/v2/image/.+',
            'timestamp': 1741686820,
            'upload_date': '20250311',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # FIXME: Embed detection
        'url': 'https://www.eurockeennes.fr/en-live/',
        'info_dict': {
            'id': 'en-live',
            'title': 'Les Eurocks en live | Les Eurockéennes de Belfort – 3-4-5-6 juillet 2025 sur la Presqu&#039;Île du Malsaucy',
        },
        'playlist_count': 4,
    }]

    def _real_extract(self, url):
        qs = parse_qs(url)
        json_url = qs['json_url'][0]
        video_id = ArteTVIE._match_id(json_url)
        return self.url_result(
            json_url, ie=ArteTVIE.ie_key(), video_id=video_id)


class ArteTVPlaylistIE(ArteTVBaseIE):
    _VALID_URL = rf'https?://(?:www\.)?arte\.tv/(?P<lang>{ArteTVBaseIE._ARTE_LANGUAGES})/videos/(?P<id>RC-\d{{6}})'
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
        lang, playlist_id = self._match_valid_url(url).group('lang', 'id')
        playlist = self._download_json(
            f'{self._API_BASE}/playlist/{lang}/{playlist_id}', playlist_id)['data']['attributes']

        entries = [{
            '_type': 'url_transparent',
            'url': video['config']['url'],
            'ie_key': ArteTVIE.ie_key(),
            'id': video.get('providerId'),
            'title': video.get('title'),
            'alt_title': video.get('subtitle'),
            'thumbnail': url_or_none(traverse_obj(video, ('mainImage', 'url'))),
            'duration': int_or_none(traverse_obj(video, ('duration', 'seconds'))),
        } for video in traverse_obj(playlist, ('items', lambda _, v: v['config']['url']))]

        return self.playlist_result(entries, playlist_id,
                                    traverse_obj(playlist, ('metadata', 'title')),
                                    traverse_obj(playlist, ('metadata', 'description')))


class ArteTVCategoryIE(ArteTVBaseIE):
    _VALID_URL = rf'https?://(?:www\.)?arte\.tv/(?P<lang>{ArteTVBaseIE._ARTE_LANGUAGES})/videos/(?P<id>[\w-]+(?:/[\w-]+)*)/?\s*$'
    _TESTS = [{
        'url': 'https://www.arte.tv/en/videos/politics-and-society/',
        'info_dict': {
            'id': 'politics-and-society',
            'title': 'Politics and society',
            'description': 'Watch documentaries and reportage about politics, society and current affairs.',
        },
        'playlist_mincount': 3,
    }]

    @classmethod
    def suitable(cls, url):
        return (
            not any(ie.suitable(url) for ie in (ArteTVIE, ArteTVPlaylistIE))
            and super().suitable(url))

    def _real_extract(self, url):
        lang, playlist_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, playlist_id)

        items = []
        for video in re.finditer(
                rf'<a\b[^>]*?href\s*=\s*(?P<q>"|\'|\b)(?P<url>https?://www\.arte\.tv/{lang}/videos/[\w/-]+)(?P=q)',
                webpage):
            video = video.group('url')
            if video == url:
                continue
            if any(ie.suitable(video) for ie in (ArteTVIE, ArteTVPlaylistIE)):
                items.append(video)

        title = strip_or_none(self._generic_title('', webpage, default='').rsplit('|', 1)[0]) or None

        return self.playlist_from_matches(items, playlist_id=playlist_id, playlist_title=title,
                                          description=self._og_search_description(webpage, default=None))

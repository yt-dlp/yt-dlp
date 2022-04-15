import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
)


class IviIE(InfoExtractor):
    IE_DESC = 'ivi.ru'
    IE_NAME = 'ivi'
    _VALID_URL = r'https?://(?:www\.)?ivi\.(?:ru|tv)/(?:watch/(?:[^/]+/)?|video/player\?.*?videoId=)(?P<id>\d+)'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['RU']
    _LIGHT_KEY = b'\xf1\x02\x32\xb7\xbc\x5c\x7a\xe8\xf7\x96\xc1\x33\x2b\x27\xa1\x8c'
    _LIGHT_URL = 'https://api.ivi.ru/light/'

    _TESTS = [
        # Single movie
        {
            'url': 'http://www.ivi.ru/watch/53141',
            'md5': '6ff5be2254e796ed346251d117196cf4',
            'info_dict': {
                'id': '53141',
                'ext': 'mp4',
                'title': 'Иван Васильевич меняет профессию',
                'description': 'md5:b924063ea1677c8fe343d8a72ac2195f',
                'duration': 5498,
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'skip': 'Only works from Russia',
        },
        # Serial's series
        {
            'url': 'http://www.ivi.ru/watch/dvoe_iz_lartsa/9549',
            'md5': '221f56b35e3ed815fde2df71032f4b3e',
            'info_dict': {
                'id': '9549',
                'ext': 'mp4',
                'title': 'Двое из ларца - Дело Гольдберга (1 часть)',
                'series': 'Двое из ларца',
                'season': 'Сезон 1',
                'season_number': 1,
                'episode': 'Дело Гольдберга (1 часть)',
                'episode_number': 1,
                'duration': 2655,
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'skip': 'Only works from Russia',
        },
        {
            # with MP4-HD720 format
            'url': 'http://www.ivi.ru/watch/146500',
            'md5': 'd63d35cdbfa1ea61a5eafec7cc523e1e',
            'info_dict': {
                'id': '146500',
                'ext': 'mp4',
                'title': 'Кукла',
                'description': 'md5:ffca9372399976a2d260a407cc74cce6',
                'duration': 5599,
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'skip': 'Only works from Russia',
        },
        {
            'url': 'https://www.ivi.tv/watch/33560/',
            'only_matching': True,
        },
    ]

    # Sorted by quality
    _KNOWN_FORMATS = (
        'MP4-low-mobile', 'MP4-mobile', 'FLV-lo', 'MP4-lo', 'FLV-hi', 'MP4-hi',
        'MP4-SHQ', 'MP4-HD720', 'MP4-HD1080')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = json.dumps({
            'method': 'da.content.get',
            'params': [
                video_id, {
                    'site': 's%d',
                    'referrer': 'http://www.ivi.ru/watch/%s' % video_id,
                    'contentid': video_id
                }
            ]
        })

        for site in (353, 183):
            content_data = (data % site).encode()
            if site == 353:
                try:
                    from Cryptodome.Cipher import Blowfish
                    from Cryptodome.Hash import CMAC
                    pycryptodome_found = True
                except ImportError:
                    try:
                        from Crypto.Cipher import Blowfish
                        from Crypto.Hash import CMAC
                        pycryptodome_found = True
                    except ImportError:
                        pycryptodome_found = False
                        continue

                timestamp = (self._download_json(
                    self._LIGHT_URL, video_id,
                    'Downloading timestamp JSON', data=json.dumps({
                        'method': 'da.timestamp.get',
                        'params': []
                    }).encode(), fatal=False) or {}).get('result')
                if not timestamp:
                    continue

                query = {
                    'ts': timestamp,
                    'sign': CMAC.new(self._LIGHT_KEY, timestamp.encode() + content_data, Blowfish).hexdigest(),
                }
            else:
                query = {}

            video_json = self._download_json(
                self._LIGHT_URL, video_id,
                'Downloading video JSON', data=content_data, query=query)

            error = video_json.get('error')
            if error:
                origin = error.get('origin')
                message = error.get('message') or error.get('user_message')
                extractor_msg = 'Unable to download video %s'
                if origin == 'NotAllowedForLocation':
                    self.raise_geo_restricted(message, self._GEO_COUNTRIES)
                elif origin == 'NoRedisValidData':
                    extractor_msg = 'Video %s does not exist'
                elif site == 353:
                    continue
                elif not pycryptodome_found:
                    raise ExtractorError('pycryptodomex not found. Please install', expected=True)
                elif message:
                    extractor_msg += ': ' + message
                raise ExtractorError(extractor_msg % video_id, expected=True)
            else:
                break

        result = video_json['result']
        title = result['title']

        quality = qualities(self._KNOWN_FORMATS)

        formats = []
        for f in result.get('files', []):
            f_url = f.get('url')
            content_format = f.get('content_format')
            if not f_url:
                continue
            if (not self.get_param('allow_unplayable_formats')
                    and ('-MDRM-' in content_format or '-FPS-' in content_format)):
                continue
            formats.append({
                'url': f_url,
                'format_id': content_format,
                'quality': quality(content_format),
                'filesize': int_or_none(f.get('size_in_bytes')),
            })
        self._sort_formats(formats)

        compilation = result.get('compilation')
        episode = title if compilation else None

        title = '%s - %s' % (compilation, title) if compilation is not None else title

        thumbnails = [{
            'url': preview['url'],
            'id': preview.get('content_format'),
        } for preview in result.get('preview', []) if preview.get('url')]

        webpage = self._download_webpage(url, video_id)

        season = self._search_regex(
            r'<li[^>]+class="season active"[^>]*><a[^>]+>([^<]+)',
            webpage, 'season', default=None)
        season_number = int_or_none(self._search_regex(
            r'<li[^>]+class="season active"[^>]*><a[^>]+data-season(?:-index)?="(\d+)"',
            webpage, 'season number', default=None))

        episode_number = int_or_none(self._search_regex(
            r'[^>]+itemprop="episode"[^>]*>\s*<meta[^>]+itemprop="episodeNumber"[^>]+content="(\d+)',
            webpage, 'episode number', default=None))

        description = self._og_search_description(webpage, default=None) or self._html_search_meta(
            'description', webpage, 'description', default=None)

        return {
            'id': video_id,
            'title': title,
            'series': compilation,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'thumbnails': thumbnails,
            'description': description,
            'duration': int_or_none(result.get('duration')),
            'formats': formats,
        }


class IviCompilationIE(InfoExtractor):
    IE_DESC = 'ivi.ru compilations'
    IE_NAME = 'ivi:compilation'
    _VALID_URL = r'https?://(?:www\.)?ivi\.ru/watch/(?!\d+)(?P<compilationid>[a-z\d_-]+)(?:/season(?P<seasonid>\d+))?$'
    _TESTS = [{
        'url': 'http://www.ivi.ru/watch/dvoe_iz_lartsa',
        'info_dict': {
            'id': 'dvoe_iz_lartsa',
            'title': 'Двое из ларца (2006 - 2008)',
        },
        'playlist_mincount': 24,
    }, {
        'url': 'http://www.ivi.ru/watch/dvoe_iz_lartsa/season1',
        'info_dict': {
            'id': 'dvoe_iz_lartsa/season1',
            'title': 'Двое из ларца (2006 - 2008) 1 сезон',
        },
        'playlist_mincount': 12,
    }]

    def _extract_entries(self, html, compilation_id):
        return [
            self.url_result(
                'http://www.ivi.ru/watch/%s/%s' % (compilation_id, serie), IviIE.ie_key())
            for serie in re.findall(
                r'<a\b[^>]+\bhref=["\']/watch/%s/(\d+)["\']' % compilation_id, html)]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        compilation_id = mobj.group('compilationid')
        season_id = mobj.group('seasonid')

        if season_id is not None:  # Season link
            season_page = self._download_webpage(
                url, compilation_id, 'Downloading season %s web page' % season_id)
            playlist_id = '%s/season%s' % (compilation_id, season_id)
            playlist_title = self._html_search_meta('title', season_page, 'title')
            entries = self._extract_entries(season_page, compilation_id)
        else:  # Compilation link
            compilation_page = self._download_webpage(url, compilation_id, 'Downloading compilation web page')
            playlist_id = compilation_id
            playlist_title = self._html_search_meta('title', compilation_page, 'title')
            seasons = re.findall(
                r'<a href="/watch/%s/season(\d+)' % compilation_id, compilation_page)
            if not seasons:  # No seasons in this compilation
                entries = self._extract_entries(compilation_page, compilation_id)
            else:
                entries = []
                for season_id in seasons:
                    season_page = self._download_webpage(
                        'http://www.ivi.ru/watch/%s/season%s' % (compilation_id, season_id),
                        compilation_id, 'Downloading season %s web page' % season_id)
                    entries.extend(self._extract_entries(season_page, compilation_id))

        return self.playlist_result(entries, playlist_id, playlist_title)

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    get_element_by_id,
    int_or_none,
    parse_iso8601,
    parse_duration,
    str_or_none,
    try_get,
    update_url_query,
    urljoin,
)


class TVNowBaseIE(InfoExtractor):
    _VIDEO_FIELDS = (
        'id', 'title', 'free', 'geoblocked', 'articleLong', 'articleShort',
        'broadcastStartDate', 'isDrm', 'duration', 'season', 'episode',
        'manifest.dashclear', 'manifest.hlsclear', 'manifest.smoothclear',
        'format.title', 'format.defaultImage169Format', 'format.defaultImage169Logo')

    def _call_api(self, path, video_id, query):
        return self._download_json(
            'https://api.tvnow.de/v3/' + path, video_id, query=query)

    def _extract_video(self, info, display_id):
        video_id = compat_str(info['id'])
        title = info['title']

        paths = []
        for manifest_url in (info.get('manifest') or {}).values():
            if not manifest_url:
                continue
            manifest_url = update_url_query(manifest_url, {'filter': ''})
            path = self._search_regex(r'https?://[^/]+/(.+?)\.ism/', manifest_url, 'path')
            if path in paths:
                continue
            paths.append(path)

            def url_repl(proto, suffix):
                return re.sub(
                    r'(?:hls|dash|hss)([.-])', proto + r'\1', re.sub(
                        r'\.ism/(?:[^.]*\.(?:m3u8|mpd)|[Mm]anifest)',
                        '.ism/' + suffix, manifest_url))

            def make_urls(proto, suffix):
                urls = [url_repl(proto, suffix)]
                hd_url = urls[0].replace('/manifest/', '/ngvod/')
                if hd_url != urls[0]:
                    urls.append(hd_url)
                return urls

            for man_url in make_urls('dash', '.mpd'):
                formats = self._extract_mpd_formats(
                    man_url, video_id, mpd_id='dash', fatal=False)
            for man_url in make_urls('hss', 'Manifest'):
                formats.extend(self._extract_ism_formats(
                    man_url, video_id, ism_id='mss', fatal=False))
            for man_url in make_urls('hls', '.m3u8'):
                formats.extend(self._extract_m3u8_formats(
                    man_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls',
                    fatal=False))
            if formats:
                break
        else:
            if not self.get_param('allow_unplayable_formats') and info.get('isDrm'):
                raise ExtractorError(
                    'Video %s is DRM protected' % video_id, expected=True)
            if info.get('geoblocked'):
                raise self.raise_geo_restricted()
            if not info.get('free', True):
                raise ExtractorError(
                    'Video %s is not available for free' % video_id, expected=True)
        self._sort_formats(formats)

        description = info.get('articleLong') or info.get('articleShort')
        timestamp = parse_iso8601(info.get('broadcastStartDate'), ' ')
        duration = parse_duration(info.get('duration'))

        f = info.get('format', {})

        thumbnails = [{
            'url': 'https://aistvnow-a.akamaihd.net/tvnow/movie/%s' % video_id,
        }]
        thumbnail = f.get('defaultImage169Format') or f.get('defaultImage169Logo')
        if thumbnail:
            thumbnails.append({
                'url': thumbnail,
            })

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'duration': duration,
            'series': f.get('title'),
            'season_number': int_or_none(info.get('season')),
            'episode_number': int_or_none(info.get('episode')),
            'episode': title,
            'formats': formats,
        }


class TVNowIE(TVNowBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?tvnow\.(?:de|at|ch)/(?P<station>[^/]+)/
                        (?P<show_id>[^/]+)/
                        (?!(?:list|jahr)(?:/|$))(?P<id>[^/?\#&]+)
                    '''

    @classmethod
    def suitable(cls, url):
        return (False if TVNowNewIE.suitable(url) or TVNowSeasonIE.suitable(url) or TVNowAnnualIE.suitable(url) or TVNowShowIE.suitable(url)
                else super(TVNowIE, cls).suitable(url))

    _TESTS = [{
        'url': 'https://www.tvnow.de/rtl2/grip-das-motormagazin/der-neue-porsche-911-gt-3/player',
        'info_dict': {
            'id': '331082',
            'display_id': 'grip-das-motormagazin/der-neue-porsche-911-gt-3',
            'ext': 'mp4',
            'title': 'Der neue Porsche 911 GT 3',
            'description': 'md5:6143220c661f9b0aae73b245e5d898bb',
            'timestamp': 1495994400,
            'upload_date': '20170528',
            'duration': 5283,
            'series': 'GRIP - Das Motormagazin',
            'season_number': 14,
            'episode_number': 405,
            'episode': 'Der neue Porsche 911 GT 3',
        },
    }, {
        # rtl2
        'url': 'https://www.tvnow.de/rtl2/armes-deutschland/episode-0008/player',
        'only_matching': True,
    }, {
        # rtlnitro
        'url': 'https://www.tvnow.de/nitro/alarm-fuer-cobra-11-die-autobahnpolizei/auf-eigene-faust-pilot/player',
        'only_matching': True,
    }, {
        # superrtl
        'url': 'https://www.tvnow.de/superrtl/die-lustigsten-schlamassel-der-welt/u-a-ketchup-effekt/player',
        'only_matching': True,
    }, {
        # ntv
        'url': 'https://www.tvnow.de/ntv/startup-news/goetter-in-weiss/player',
        'only_matching': True,
    }, {
        # vox
        'url': 'https://www.tvnow.de/vox/auto-mobil/neues-vom-automobilmarkt-2017-11-19-17-00-00/player',
        'only_matching': True,
    }, {
        # rtlplus
        'url': 'https://www.tvnow.de/rtlplus/op-ruft-dr-bruckner/die-vernaehte-frau/player',
        'only_matching': True,
    }, {
        'url': 'https://www.tvnow.de/rtl2/grip-das-motormagazin/der-neue-porsche-911-gt-3',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = '%s/%s' % mobj.group(2, 3)

        info = self._call_api(
            'movies/' + display_id, display_id, query={
                'fields': ','.join(self._VIDEO_FIELDS),
            })

        return self._extract_video(info, display_id)


class TVNowNewIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    (?P<base_url>https?://
                        (?:www\.)?tvnow\.(?:de|at|ch)/
                        (?:shows|serien))/
                        (?P<show>[^/]+)-\d+/
                        [^/]+/
                        episode-\d+-(?P<episode>[^/?$&]+)-(?P<id>\d+)
                    '''

    _TESTS = [{
        'url': 'https://www.tvnow.de/shows/grip-das-motormagazin-1669/2017-05/episode-405-der-neue-porsche-911-gt-3-331082',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        base_url = re.sub(r'(?:shows|serien)', '_', mobj.group('base_url'))
        show, episode = mobj.group('show', 'episode')
        return self.url_result(
            # Rewrite new URLs to the old format and use extraction via old API
            # at api.tvnow.de as a loophole for bypassing premium content checks
            '%s/%s/%s' % (base_url, show, episode),
            ie=TVNowIE.ie_key(), video_id=mobj.group('id'))


class TVNowFilmIE(TVNowBaseIE):
    _VALID_URL = r'''(?x)
                    (?P<base_url>https?://
                        (?:www\.)?tvnow\.(?:de|at|ch)/
                        (?:filme))/
                        (?P<title>[^/?$&]+)-(?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://www.tvnow.de/filme/lord-of-war-haendler-des-todes-7959',
        'info_dict': {
            'id': '1426690',
            'display_id': 'lord-of-war-haendler-des-todes',
            'ext': 'mp4',
            'title': 'Lord of War',
            'description': 'md5:5eda15c0d5b8cb70dac724c8a0ff89a9',
            'timestamp': 1550010000,
            'upload_date': '20190212',
            'duration': 7016,
        },
    }, {
        'url': 'https://www.tvnow.de/filme/the-machinist-12157',
        'info_dict': {
            'id': '328160',
            'display_id': 'the-machinist',
            'ext': 'mp4',
            'title': 'The Machinist',
            'description': 'md5:9a0e363fdd74b3a9e1cdd9e21d0ecc28',
            'timestamp': 1496469720,
            'upload_date': '20170603',
            'duration': 5836,
        },
    }, {
        'url': 'https://www.tvnow.de/filme/horst-schlaemmer-isch-kandidiere-17777',
        'only_matching': True,  # DRM protected
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('title')

        webpage = self._download_webpage(url, display_id, fatal=False)
        if not webpage:
            raise ExtractorError('Cannot download "%s"' % url, expected=True)

        json_text = get_element_by_id('now-web-state', webpage)
        if not json_text:
            raise ExtractorError('Cannot read video data', expected=True)

        json_data = self._parse_json(
            json_text,
            display_id,
            transform_source=lambda x: x.replace('&q;', '"'),
            fatal=False)
        if not json_data:
            raise ExtractorError('Cannot read video data', expected=True)

        player_key = next(
            (key for key in json_data.keys() if 'module/player' in key),
            None)
        page_key = next(
            (key for key in json_data.keys() if 'page/filme' in key),
            None)
        movie_id = try_get(
            json_data,
            [
                lambda x: x[player_key]['body']['id'],
                lambda x: x[page_key]['body']['modules'][0]['id'],
                lambda x: x[page_key]['body']['modules'][1]['id']],
            int)
        if not movie_id:
            raise ExtractorError('Cannot extract movie ID', expected=True)

        info = self._call_api(
            'movies/%d' % movie_id,
            display_id,
            query={'fields': ','.join(self._VIDEO_FIELDS)})

        return self._extract_video(info, display_id)


class TVNowNewBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, query={}):
        result = self._download_json(
            'https://apigw.tvnow.de/module/' + path, video_id, query=query)
        error = result.get('error')
        if error:
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, error), expected=True)
        return result


r"""
TODO: new apigw.tvnow.de based version of TVNowIE. Replace old TVNowIE with it
when api.tvnow.de is shut down. This version can't bypass premium checks though.
class TVNowIE(TVNowNewBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?tvnow\.(?:de|at|ch)/
                        (?:shows|serien)/[^/]+/
                        (?:[^/]+/)+
                        (?P<display_id>[^/?$&]+)-(?P<id>\d+)
                    '''

    _TESTS = [{
        # episode with annual navigation
        'url': 'https://www.tvnow.de/shows/grip-das-motormagazin-1669/2017-05/episode-405-der-neue-porsche-911-gt-3-331082',
        'info_dict': {
            'id': '331082',
            'display_id': 'grip-das-motormagazin/der-neue-porsche-911-gt-3',
            'ext': 'mp4',
            'title': 'Der neue Porsche 911 GT 3',
            'description': 'md5:6143220c661f9b0aae73b245e5d898bb',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1495994400,
            'upload_date': '20170528',
            'duration': 5283,
            'series': 'GRIP - Das Motormagazin',
            'season_number': 14,
            'episode_number': 405,
            'episode': 'Der neue Porsche 911 GT 3',
        },
    }, {
        # rtl2, episode with season navigation
        'url': 'https://www.tvnow.de/shows/armes-deutschland-11471/staffel-3/episode-14-bernd-steht-seit-der-trennung-von-seiner-frau-allein-da-526124',
        'only_matching': True,
    }, {
        # rtlnitro
        'url': 'https://www.tvnow.de/serien/alarm-fuer-cobra-11-die-autobahnpolizei-1815/staffel-13/episode-5-auf-eigene-faust-pilot-366822',
        'only_matching': True,
    }, {
        # superrtl
        'url': 'https://www.tvnow.de/shows/die-lustigsten-schlamassel-der-welt-1221/staffel-2/episode-14-u-a-ketchup-effekt-364120',
        'only_matching': True,
    }, {
        # ntv
        'url': 'https://www.tvnow.de/shows/startup-news-10674/staffel-2/episode-39-goetter-in-weiss-387630',
        'only_matching': True,
    }, {
        # vox
        'url': 'https://www.tvnow.de/shows/auto-mobil-174/2017-11/episode-46-neues-vom-automobilmarkt-2017-11-19-17-00-00-380072',
        'only_matching': True,
    }, {
        'url': 'https://www.tvnow.de/shows/grip-das-motormagazin-1669/2017-05/episode-405-der-neue-porsche-911-gt-3-331082',
        'only_matching': True,
    }]

    def _extract_video(self, info, url, display_id):
        config = info['config']
        source = config['source']

        video_id = compat_str(info.get('id') or source['videoId'])
        title = source['title'].strip()

        paths = []
        for manifest_url in (info.get('manifest') or {}).values():
            if not manifest_url:
                continue
            manifest_url = update_url_query(manifest_url, {'filter': ''})
            path = self._search_regex(r'https?://[^/]+/(.+?)\.ism/', manifest_url, 'path')
            if path in paths:
                continue
            paths.append(path)

            def url_repl(proto, suffix):
                return re.sub(
                    r'(?:hls|dash|hss)([.-])', proto + r'\1', re.sub(
                        r'\.ism/(?:[^.]*\.(?:m3u8|mpd)|[Mm]anifest)',
                        '.ism/' + suffix, manifest_url))

            formats = self._extract_mpd_formats(
                url_repl('dash', '.mpd'), video_id,
                mpd_id='dash', fatal=False)
            formats.extend(self._extract_ism_formats(
                url_repl('hss', 'Manifest'),
                video_id, ism_id='mss', fatal=False))
            formats.extend(self._extract_m3u8_formats(
                url_repl('hls', '.m3u8'), video_id, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False))
            if formats:
                break
        else:
            if try_get(info, lambda x: x['rights']['isDrm']):
                raise ExtractorError(
                    'Video %s is DRM protected' % video_id, expected=True)
            if try_get(config, lambda x: x['boards']['geoBlocking']['block']):
                raise self.raise_geo_restricted()
            if not info.get('free', True):
                raise ExtractorError(
                    'Video %s is not available for free' % video_id, expected=True)
        self._sort_formats(formats)

        description = source.get('description')
        thumbnail = url_or_none(source.get('poster'))
        timestamp = unified_timestamp(source.get('previewStart'))
        duration = parse_duration(source.get('length'))

        series = source.get('format')
        season_number = int_or_none(self._search_regex(
            r'staffel-(\d+)', url, 'season number', default=None))
        episode_number = int_or_none(self._search_regex(
            r'episode-(\d+)', url, 'episode number', default=None))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'series': series,
            'season_number': season_number,
            'episode_number': episode_number,
            'episode': title,
            'formats': formats,
        }

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()
        info = self._call_api('player/' + video_id, video_id)
        return self._extract_video(info, video_id, display_id)


class TVNowFilmIE(TVNowIE):
    _VALID_URL = r'''(?x)
                    (?P<base_url>https?://
                        (?:www\.)?tvnow\.(?:de|at|ch)/
                        (?:filme))/
                        (?P<title>[^/?$&]+)-(?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://www.tvnow.de/filme/lord-of-war-haendler-des-todes-7959',
        'info_dict': {
            'id': '1426690',
            'display_id': 'lord-of-war-haendler-des-todes',
            'ext': 'mp4',
            'title': 'Lord of War',
            'description': 'md5:5eda15c0d5b8cb70dac724c8a0ff89a9',
            'timestamp': 1550010000,
            'upload_date': '20190212',
            'duration': 7016,
        },
    }, {
        'url': 'https://www.tvnow.de/filme/the-machinist-12157',
        'info_dict': {
            'id': '328160',
            'display_id': 'the-machinist',
            'ext': 'mp4',
            'title': 'The Machinist',
            'description': 'md5:9a0e363fdd74b3a9e1cdd9e21d0ecc28',
            'timestamp': 1496469720,
            'upload_date': '20170603',
            'duration': 5836,
        },
    }, {
        'url': 'https://www.tvnow.de/filme/horst-schlaemmer-isch-kandidiere-17777',
        'only_matching': True,  # DRM protected
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('title')

        webpage = self._download_webpage(url, display_id, fatal=False)
        if not webpage:
            raise ExtractorError('Cannot download "%s"' % url, expected=True)

        json_text = get_element_by_id('now-web-state', webpage)
        if not json_text:
            raise ExtractorError('Cannot read video data', expected=True)

        json_data = self._parse_json(
            json_text,
            display_id,
            transform_source=lambda x: x.replace('&q;', '"'),
            fatal=False)
        if not json_data:
            raise ExtractorError('Cannot read video data', expected=True)

        player_key = next(
            (key for key in json_data.keys() if 'module/player' in key),
            None)
        page_key = next(
            (key for key in json_data.keys() if 'page/filme' in key),
            None)
        movie_id = try_get(
            json_data,
            [
                lambda x: x[player_key]['body']['id'],
                lambda x: x[page_key]['body']['modules'][0]['id'],
                lambda x: x[page_key]['body']['modules'][1]['id']],
            int)
        if not movie_id:
            raise ExtractorError('Cannot extract movie ID', expected=True)

        info = self._call_api('player/%d' % movie_id, display_id)
        return self._extract_video(info, url, display_id)
"""


class TVNowListBaseIE(TVNowNewBaseIE):
    _SHOW_VALID_URL = r'''(?x)
                    (?P<base_url>
                        https?://
                            (?:www\.)?tvnow\.(?:de|at|ch)/(?:shows|serien)/
                            [^/?#&]+-(?P<show_id>\d+)
                    )
                    '''

    @classmethod
    def suitable(cls, url):
        return (False if TVNowNewIE.suitable(url)
                else super(TVNowListBaseIE, cls).suitable(url))

    def _extract_items(self, url, show_id, list_id, query):
        items = self._call_api(
            'teaserrow/format/episode/' + show_id, list_id,
            query=query)['items']

        entries = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_url = urljoin(url, item.get('url'))
            if not item_url:
                continue
            video_id = str_or_none(item.get('id') or item.get('videoId'))
            item_title = item.get('subheadline') or item.get('text')
            entries.append(self.url_result(
                item_url, ie=TVNowNewIE.ie_key(), video_id=video_id,
                video_title=item_title))

        return self.playlist_result(entries, '%s/%s' % (show_id, list_id))


class TVNowSeasonIE(TVNowListBaseIE):
    _VALID_URL = r'%s/staffel-(?P<id>\d+)' % TVNowListBaseIE._SHOW_VALID_URL
    _TESTS = [{
        'url': 'https://www.tvnow.de/serien/alarm-fuer-cobra-11-die-autobahnpolizei-1815/staffel-13',
        'info_dict': {
            'id': '1815/13',
        },
        'playlist_mincount': 22,
    }]

    def _real_extract(self, url):
        _, show_id, season_id = self._match_valid_url(url).groups()
        return self._extract_items(
            url, show_id, season_id, {'season': season_id})


class TVNowAnnualIE(TVNowListBaseIE):
    _VALID_URL = r'%s/(?P<year>\d{4})-(?P<month>\d{2})' % TVNowListBaseIE._SHOW_VALID_URL
    _TESTS = [{
        'url': 'https://www.tvnow.de/shows/grip-das-motormagazin-1669/2017-05',
        'info_dict': {
            'id': '1669/2017-05',
        },
        'playlist_mincount': 2,
    }]

    def _real_extract(self, url):
        _, show_id, year, month = self._match_valid_url(url).groups()
        return self._extract_items(
            url, show_id, '%s-%s' % (year, month), {
                'year': int(year),
                'month': int(month),
            })


class TVNowShowIE(TVNowListBaseIE):
    _VALID_URL = TVNowListBaseIE._SHOW_VALID_URL
    _TESTS = [{
        # annual navigationType
        'url': 'https://www.tvnow.de/shows/grip-das-motormagazin-1669',
        'info_dict': {
            'id': '1669',
        },
        'playlist_mincount': 73,
    }, {
        # season navigationType
        'url': 'https://www.tvnow.de/shows/armes-deutschland-11471',
        'info_dict': {
            'id': '11471',
        },
        'playlist_mincount': 3,
    }]

    @classmethod
    def suitable(cls, url):
        return (False if TVNowNewIE.suitable(url) or TVNowSeasonIE.suitable(url) or TVNowAnnualIE.suitable(url)
                else super(TVNowShowIE, cls).suitable(url))

    def _real_extract(self, url):
        base_url, show_id = self._match_valid_url(url).groups()

        result = self._call_api(
            'teaserrow/format/navigation/' + show_id, show_id)

        items = result['items']

        entries = []
        navigation = result.get('navigationType')
        if navigation == 'annual':
            for item in items:
                if not isinstance(item, dict):
                    continue
                year = int_or_none(item.get('year'))
                if year is None:
                    continue
                months = item.get('months')
                if not isinstance(months, list):
                    continue
                for month_dict in months:
                    if not isinstance(month_dict, dict) or not month_dict:
                        continue
                    month_number = int_or_none(list(month_dict.keys())[0])
                    if month_number is None:
                        continue
                    entries.append(self.url_result(
                        '%s/%04d-%02d' % (base_url, year, month_number),
                        ie=TVNowAnnualIE.ie_key()))
        elif navigation == 'season':
            for item in items:
                if not isinstance(item, dict):
                    continue
                season_number = int_or_none(item.get('season'))
                if season_number is None:
                    continue
                entries.append(self.url_result(
                    '%s/staffel-%d' % (base_url, season_number),
                    ie=TVNowSeasonIE.ie_key()))
        else:
            raise ExtractorError('Unknown navigationType')

        return self.playlist_result(entries, show_id)

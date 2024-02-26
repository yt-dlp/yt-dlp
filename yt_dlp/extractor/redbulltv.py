from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    get_element_by_class,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    parse_duration,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class RedBullBaseIE(InfoExtractor):
    _INT_FALLBACK_LIST = ['de', 'en', 'es', 'fr']
    _LAT_FALLBACK_MAP = ['ar', 'bo', 'car', 'cl', 'co', 'mx', 'pe']
    _SCHEMAS = {
        'page_config': 'v1:pageConfig',
        'structured_data': 'v1:structuredData',
        'video_hero': 'v1:videoHero',
    }

    def _get_locale(self, region, lang):
        regions = [region.upper()]
        if region != 'int':
            if region in self._LAT_FALLBACK_MAP:
                regions.append('LAT')
            if lang in self._INT_FALLBACK_LIST:
                regions.append('INT')
        return '>'.join(['%s-%s' % (lang, reg) for reg in regions])

    def _call_api(self, schema, type, slug, region, lang):
        locale = self._get_locale(region, lang)
        res = self._download_json(
            'https://www.redbull.com/v3/api/graphql/v1/v3/query/' + locale,
            video_id=slug, note=f'Downloading {type[:-1]} metadata', query={
                'filter[type]': type,
                'filter[uriSlug]': slug,
                'disableUsageRestrictions': 'true',
                'rb3Schema': schema,
            })
        data = res['data']
        if schema == self._SCHEMAS['structured_data']:
            if len(data) == 0:
                raise ExtractorError(f'{type[:-1]} not found', expected=True)
            return data[0]
        return data

    def _get_video_resource(self, rrn_id):
        return self._download_json(
            'https://api-player.redbull.com/rbcom/videoresource',
            video_id=rrn_id, note='Downloading video resource metadata', query={
                'videoId': rrn_id,
            })

    def _extract_video_resource(self, rrn_id):
        video_resource = self._get_video_resource(rrn_id)

        playability_errors = traverse_obj(video_resource, ('playabilityErrors'))
        if 'GEO_BLOCKED' in playability_errors:
            raise ExtractorError('Geo-restricted', expected=True)
        if playability_errors:
            raise ExtractorError('Playability error', expected=True)

        video_id = traverse_obj(video_resource, ('assetId', {str})) or rrn_id.split(':')[3]
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_resource['videoUrl'], video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'aspect_ratio': traverse_obj(video_resource, ('aspectRatio', {float_or_none})),
        }


class RedBullTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?redbull(?:\.tv|\.com(?:/[^/]+)?(?:/tv)?)(?:/events/[^/]+)?/(?:videos?|live|(?:film|episode)s)/(?P<id>AP-\w+)'
    _TESTS = [{
        'url': 'https://www.redbull.tv/video/AP-1PMHKJFCW1W11',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/tv/video/AP-1UWHCAR9S1W11/rob-meets-sam-gaze?playlist=playlists::3f81040a-2f31-4832-8e2e-545b1d39d173',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/us-en/events/AP-1XV2K61Q51W11/live/AP-1XUJ86FDH1W11',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/films/AP-1ZSMAW8FH2111',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/episodes/AP-1TQWK7XE11W11',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        html = self._download_webpage(url, video_id)
        try:
            return self.url_result(self._og_search_url(html), RedBullIE, video_id)
        except Exception:
            raise ExtractorError('Failed to extract video URL', expected=True)


class RedBullEmbedIE(RedBullBaseIE):
    _VALID_URL = r'https?://(?:www\.)?redbull\.com/embed/(?P<id>rrn:content:[^:]+:[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}:[a-z]{2}-[A-Z]{2,3})'
    _TESTS = [{
        'url': 'https://www.redbull.com/embed/rrn:content:episode-videos:f3021f4f-3ed4-51ac-915a-11987126e405:en-INT',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/embed/rrn:content:videos:0c1d4526-2dfc-4491-bc24-239560dbdfff:en-INT',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        rrn_id = self._match_id(url)
        video_resource = self._get_video_resource(rrn_id)
        return self.url_result(
            video_resource['url'], RedBullIE,
            video_resource['assetId'], video_resource['title'])


class RedBullTVRrnContentIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?redbull\.com/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})/tv/(?:video|live|film)/(?P<id>rrn:content:[^:]+:[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://www.redbull.com/int-en/tv/video/rrn:content:live-videos:e3e6feb4-e95f-50b7-962a-c70f8fd13c73/mens-dh-finals-fort-william',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/tv/video/rrn:content:videos:a36a0f36-ff1b-5db8-a69d-ee11a14bf48b/tn-ts-style?playlist=rrn:content:event-profiles:83f05926-5de8-5389-b5e4-9bb312d715e8:extras',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/tv/film/rrn:content:films:d1f4d00e-4c04-5d19-b510-a805ffa2ab83/follow-me',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        region, lang, rrn_id = self._match_valid_url(url).groups()
        rrn_id += ':%s-%s' % (lang, region.upper())
        return self.url_result(
            'https://www.redbull.com/embed/' + rrn_id,
            RedBullEmbedIE, rrn_id)


class RedBullIE(RedBullBaseIE):
    _VALID_URL = r'https?:\/\/(?:www\.)?redbull\.com\/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})\/(?P<type>videos|films|episodes|live|recap-videos|trailer-videos)\/(?P<slug>[a-z0-9-_]+)'
    _TESTS = [{
        'url': 'https://www.redbull.com/int-en/videos/metal-on-streif-dominik-paris-in-kitzbuhel',
        'info_dict': {
            'id': 'AAMU3BN1Z0J04IFZVPJ1',
            'ext': 'mp4',
            'title': 'Metal on Streif: Dominik Paris in Kitzbühel',
            'description': 'md5:b140b299dca20f5d7b3ca561fe5a5d24',
            'upload_date': '20240209',
            'timestamp': 1707472608,
            'duration': 1977.0,
            'thumbnail': r're:^https?://',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.redbull.com/int-en/videos/swatch-nines-2023-best-performers?playlistId=rrn:content:videos:22c7c969-85b9-4d30-9b60-a7eda2432c06:en-INT',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/films/moto-maverick',
        'info_dict': {
            'id': 'AA-21YW2JS5S1W12',
            'ext': 'mp4',
            'title': 'Moto Maverick',
            'description': 'Ryan Sipes examines the current state of motocross racing through a stylised and cinematic lens.',
            'upload_date': '20211224',
            'timestamp': 1640332802,
            'duration': 1425,
            'thumbnail': r're:^https?://',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.redbull.com/int-en/films/in-the-wings?autoplay=true',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/episodes/more-than-a-dive-s1-e6',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/episodes/grime-hashtags-s02-e04',
        'info_dict': {
            'id': 'AA-1MT8DQWA91W14',
            'ext': 'mp4',
            'title': 'Grime',
            'description': 'Evolving from hip-hop, electronic, and dancehall, grime is a murky musical movement full of passion.',
            'upload_date': '20170221',
            'timestamp': 1487660400,
            'duration': 904.0,
            'thumbnail': r're:^https?://',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.redbull.com/int-en/live/mondo-classic-2024',
        'only_matching': True,
    }, {
        # as a part of a playlist
        'url': 'https://www.redbull.com/int-en/live/laax-open-2024-freeski-slopestyle',
        'md5': 'cc5e51240689add2f39560ea7c4a4e91',
        'info_dict': {
            'id': 'AA2FV4NQNYSNBJXIEXPT',
            'ext': 'mp4',
            'title': 'Freeski Slopestyle',
            'description': 'md5:86f51cb9624d359438e8988449b4621e',
            'upload_date': '20231222',
            'timestamp': 1703251679,
            'thumbnail': r're:^https?://',
        },
    }, {
        'url': 'https://www.redbull.com/int-en/live/laax-open-2024-snowboard-slopestyle?playlistId=rrn:content:live-videos:c4c1b1c8-445a-4bcb-9fb8-d8c510ed69bc:en-INT',
        'only_matching': True,
    }, {
        # only available on the int-en website so a fallback is need for the API
        # https://www.redbull.com/v3/api/graphql/v1/v3/query/en-GB>en-INT?filter[uriSlug]=fia-wrc-saturday-recap-estonia&rb3Schema=v1:videoHero
        'url': 'https://www.redbull.com/gb-en/live/fia-wrc-saturday-recap-estonia',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/recap-videos/uci-mountain-bike-world-cup-2017-mens-xco-finals-from-vallnord',
        'info_dict': {
            'id': 'AA-1UM6YNYX92112',
            'ext': 'mp4',
            'title': 'Men\'s XCO finals from Vallnord',
            'description': 'The world’s best men take on the gruelling cross-country course in Vallnord, Andorra.',
            'upload_date': '20180201',
            'timestamp': 1517468400,
            'duration': 6761.0,
            'thumbnail': r're:^https?://',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.redbull.com/int-en/trailer-videos/kings-of-content',
        'info_dict': {
            'id': 'AA-1PRQ4VRAW1W12',
            'ext': 'mp4',
            'title': 'Kings of Content',
            'description': 'md5:4af0f7d9938aef4db22115d3b56f02dd',
            'upload_date': '20170411',
            'timestamp': 1491901200,
            'duration': 45.0,
            'thumbnail': r're:^https?://',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        region, lang, type, slug = self._match_valid_url(url).groups()
        if type == 'episodes':
            type = 'episode-videos'
        if type == 'live':
            type = 'live-videos'

        video_object = self._call_api(
            self._SCHEMAS['structured_data'], type, slug, region, lang)
        if type == 'films' or type == 'episode-videos':
            video_object = video_object['associatedMedia']

        rrn_id = video_object['embedUrl'].replace('https://www.redbull.com/embed/', '')

        return {
            **self._extract_video_resource(rrn_id),
            **traverse_obj(video_object, {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'duration': ('duration', {parse_duration}),
                'timestamp': ('uploadDate', {parse_iso8601}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
            }),
        }


class RedBullChannelIE(RedBullBaseIE):
    _VALID_URL = r'https?:\/\/(?:www\.)?redbull\.com\/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})\/channels\/(?P<slug>[a-z0-9-_]+)'
    _TESTS = [{
        'url': 'https://www.redbull.com/int-en/channels/best-of-red-bull-stream',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        region, lang, slug = self._match_valid_url(url).groups()
        # structured_data is not available for channels
        video_hero = self._call_api(
            self._SCHEMAS['video_hero'], 'video-channels', slug, region, lang)
        return {
            **self._extract_video_resource(video_hero['id']),
            'title': traverse_obj(video_hero, ('title', {str})),
            'is_live': True,
        }


class RedBullEventIE(RedBullBaseIE):
    _VALID_URL = r'https?:\/\/(?:www\.)?redbull\.com\/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})\/events\/(?P<slug>[a-z0-9-_]+)'
    _TESTS = [{
        # one replay
        'url': 'https://www.redbull.com/int-en/events/mondo-classic',
        'md5': 'ca8ed1669b71907c68b00cce216cb506',
        'info_dict': {
            'id': 'AA3YMCCKHF7JGGUY8HY7',
            'ext': 'mp4',
            'title': 'Livestream',
            'description': 'md5:deff294a59c0e692acfa51e2d02d4b5c',
            'upload_date': '20240125',
            'timestamp': 1706191087,
            'thumbnail': r're:^https?://',
        },
    }, {
        # multiple replays
        'url': 'https://www.redbull.com/int-en/events/laax-open',
        'info_dict': {
            'id': 'laax-open',
            'title': 'Laax Open',
        },
        'playlist_mincount': 5,
    }, {
        # no replays
        'url': 'https://www.redbull.com/int-en/events/hahnenkamm-rennen',
        'only_matching': True,
    }]

    def _get_livestream_slug(self, html):
        livestream_div = get_element_html_by_class('playable-livestream__media', html)
        if not livestream_div:
            raise ExtractorError('Livestream not found', expected=True)
        _, livestream_a = get_element_text_and_html_by_tag('a', livestream_div)
        return extract_attributes(livestream_a)['href'].split('/')[3]

    def _real_extract(self, url):
        region, lang, slug = self._match_valid_url(url).groups()
        html = self._download_webpage(url, slug)

        livestream_slug = self._get_livestream_slug(html)
        video_hero = self._call_api(
            self._SCHEMAS['video_hero'], 'live-videos', livestream_slug, region, lang)

        sidebar_items = traverse_obj(video_hero, ('sidebar', 'tabs', 0, 'items'))
        if not sidebar_items:
            return self.url_result(
                'https://www.redbull.com/embed/' + video_hero['id'],
                RedBullEmbedIE, livestream_slug)

        title = clean_html(get_element_by_class('event-hero-view__title', html))

        def entries():
            for video in sidebar_items:
                url = 'https://www.redbull.com/embed/' + video['id']
                yield self.url_result(url, RedBullEmbedIE, video['id'])

        return self.playlist_result(entries(), slug, title)


class RedBullShowIE(RedBullBaseIE):
    _VALID_URL = r'https?:\/\/(?:www\.)?redbull\.com\/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})\/shows\/(?P<slug>[a-z0-9-_]+)'
    _TESTS = [{
        # one season
        'url': 'https://www.redbull.com/int-en/shows/in-the-dust',
        'info_dict': {
            'id': 'in-the-dust',
            'title': 'Dakar: In the Dust',
        },
        'playlist_mincount': 8,
    }, {
        # multiple seasons
        'url': 'https://www.redbull.com/int-en/shows/fia-world-rally-raid-championship',
        'info_dict': {
            'id': 'fia-world-rally-raid-championship',
            'title': 'FIA World Rally-Raid Championship',
        },
        'playlist_mincount': 9,
    }]

    def _real_extract(self, url):
        region, lang, slug = self._match_valid_url(url).groups()
        tv_series = self._call_api(
            self._SCHEMAS['structured_data'], 'shows', slug, region, lang)

        def entries():
            for season in tv_series['containsSeason']:
                for episode in season['episode']:
                    url = episode['associatedMedia']['url']
                    episode_id = url.split('/')[5]
                    yield self.url_result(url, RedBullIE, episode_id)

        return self.playlist_result(entries(), slug, tv_series['name'])

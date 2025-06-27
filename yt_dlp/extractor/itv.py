import json

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    JSON_LD_RE,
    ExtractorError,
    base_url,
    clean_html,
    determine_ext,
    extract_attributes,
    get_element_by_class,
    merge_dicts,
    parse_duration,
    smuggle_url,
    try_get,
    url_basename,
    url_or_none,
    urljoin,
)


class ITVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?itv\.com/hub/[^/]+/(?P<id>[0-9a-zA-Z]+)'
    _GEO_COUNTRIES = ['GB']
    _TESTS = [{
        'url': 'https://www.itv.com/hub/plebs/2a1873a0002',
        'info_dict': {
            'id': '2a1873a0002',
            'ext': 'mp4',
            'title': 'Plebs - The Orgy',
            'description': 'md5:4d7159af53ebd5b36e8b3ec82a41fdb4',
            'series': 'Plebs',
            'season_number': 1,
            'episode_number': 1,
            'thumbnail': r're:https?://hubimages\.itv\.com/episode/2_1873_0002',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.itv.com/hub/the-jonathan-ross-show/2a1166a0209',
        'info_dict': {
            'id': '2a1166a0209',
            'ext': 'mp4',
            'title': 'The Jonathan Ross Show - Series 17 - Episode 8',
            'description': 'md5:3023dcdd375db1bc9967186cdb3f1399',
            'series': 'The Jonathan Ross Show',
            'episode_number': 8,
            'season_number': 17,
            'thumbnail': r're:https?://hubimages\.itv\.com/episode/2_1873_0002',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # unavailable via data-playlist-url
        'url': 'https://www.itv.com/hub/through-the-keyhole/2a2271a0033',
        'only_matching': True,
    }, {
        # InvalidVodcrid
        'url': 'https://www.itv.com/hub/james-martins-saturday-morning/2a5159a0034',
        'only_matching': True,
    }, {
        # ContentUnavailable
        'url': 'https://www.itv.com/hub/whos-doing-the-dishes/2a2898a0024',
        'only_matching': True,
    }]

    def _generate_api_headers(self, hmac):
        return merge_dicts({
            'Accept': 'application/vnd.itv.vod.playlist.v2+json',
            'Content-Type': 'application/json',
            'hmac': hmac.upper(),
        }, self.geo_verification_headers())

    def _call_api(self, video_id, playlist_url, headers, platform_tag, featureset, fatal=True):
        return self._download_json(
            playlist_url, video_id, data=json.dumps({
                'user': {
                    'itvUserId': '',
                    'entitlements': [],
                    'token': '',
                },
                'device': {
                    'manufacturer': 'Safari',
                    'model': '5',
                    'os': {
                        'name': 'Windows NT',
                        'version': '6.1',
                        'type': 'desktop',
                    },
                },
                'client': {
                    'version': '4.1',
                    'id': 'browser',
                },
                'variantAvailability': {
                    'featureset': {
                        'min': featureset,
                        'max': featureset,
                    },
                    'platformTag': platform_tag,
                },
            }).encode(), headers=headers, fatal=fatal)

    def _get_subtitles(self, video_id, variants, ios_playlist_url, headers, *args, **kwargs):
        subtitles = {}
        # Prefer last matching featureset
        # See: https://github.com/yt-dlp/yt-dlp/issues/986
        platform_tag_subs, featureset_subs = next(
            ((platform_tag, featureset)
             for platform_tag, featuresets in reversed(list(variants.items())) for featureset in featuresets
             if try_get(featureset, lambda x: x[2]) == 'outband-webvtt'),
            (None, None))

        if platform_tag_subs and featureset_subs:
            subs_playlist = self._call_api(
                video_id, ios_playlist_url, headers, platform_tag_subs, featureset_subs, fatal=False)
            subs = try_get(subs_playlist, lambda x: x['Playlist']['Video']['Subtitles'], list) or []
            for sub in subs:
                if not isinstance(sub, dict):
                    continue
                href = url_or_none(sub.get('Href'))
                if not href:
                    continue
                subtitles.setdefault('en', []).append({'url': href})
        return subtitles

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        params = extract_attributes(self._search_regex(
            r'(?s)(<[^>]+id="video"[^>]*>)', webpage, 'params'))
        variants = self._parse_json(
            try_get(params, lambda x: x['data-video-variants'], str) or '{}',
            video_id, fatal=False)
        # Prefer last matching featureset
        # See: https://github.com/yt-dlp/yt-dlp/issues/986
        platform_tag_video, featureset_video = next(
            ((platform_tag, featureset)
             for platform_tag, featuresets in reversed(list(variants.items())) for featureset in featuresets
             if set(try_get(featureset, lambda x: x[:2]) or []) == {'aes', 'hls'}),
            (None, None))
        if not platform_tag_video or not featureset_video:
            raise ExtractorError('No downloads available', expected=True, video_id=video_id)

        ios_playlist_url = params.get('data-video-playlist') or params['data-video-id']
        headers = self._generate_api_headers(params['data-video-hmac'])
        ios_playlist = self._call_api(
            video_id, ios_playlist_url, headers, platform_tag_video, featureset_video)

        video_data = try_get(ios_playlist, lambda x: x['Playlist']['Video'], dict) or {}
        ios_base_url = video_data.get('Base')
        formats = []
        for media_file in (video_data.get('MediaFiles') or []):
            href = media_file.get('Href')
            if not href:
                continue
            if ios_base_url:
                href = ios_base_url + href
            ext = determine_ext(href)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    href, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': href,
                })
        info = self._search_json_ld(webpage, video_id, default={})
        if not info:
            json_ld = self._parse_json(self._search_regex(
                JSON_LD_RE, webpage, 'JSON-LD', '{}',
                group='json_ld'), video_id, fatal=False)
            if json_ld and json_ld.get('@type') == 'BreadcrumbList':
                for ile in (json_ld.get('itemListElement:') or []):
                    item = ile.get('item:') or {}
                    if item.get('@type') == 'TVEpisode':
                        item['@context'] = 'http://schema.org'
                        info = self._json_ld(item, video_id, fatal=False) or {}
                        break

        thumbnails = []
        thumbnail_url = try_get(params, lambda x: x['data-video-posterframe'], str)
        if thumbnail_url:
            thumbnails.extend([{
                'url': thumbnail_url.format(width=1920, height=1080, quality=100, blur=0, bg='false'),
                'width': 1920,
                'height': 1080,
            }, {
                'url': urljoin(base_url(thumbnail_url), url_basename(thumbnail_url)),
                'preference': -2,
            }])

        thumbnail_url = self._html_search_meta(['og:image', 'twitter:image'], webpage, default=None)
        if thumbnail_url:
            thumbnails.append({
                'url': thumbnail_url,
            })
        self._remove_duplicate_formats(thumbnails)

        return merge_dicts({
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'formats': formats,
            'subtitles': self.extract_subtitles(video_id, variants, ios_playlist_url, headers),
            'duration': parse_duration(video_data.get('Duration')),
            'description': clean_html(get_element_by_class('episode-info__synopsis', webpage)),
            'thumbnails': thumbnails,
        }, info)


class ITVBTCCIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?itv\.com/(?:news|btcc)/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.itv.com/btcc/articles/btcc-2019-brands-hatch-gp-race-action',
        'info_dict': {
            'id': 'btcc-2019-brands-hatch-gp-race-action',
            'title': 'BTCC 2019: Brands Hatch GP race action',
        },
        'playlist_count': 12,
    }, {
        'url': 'https://www.itv.com/news/2021-10-27/i-have-to-protect-the-country-says-rishi-sunak-as-uk-faces-interest-rate-hike',
        'info_dict': {
            'id': 'i-have-to-protect-the-country-says-rishi-sunak-as-uk-faces-interest-rate-hike',
            'title': 'md5:6ef054dd9f069330db3dcc66cb772d32',
        },
        'playlist_count': 4,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        json_map = try_get(
            self._search_nextjs_data(webpage, playlist_id),
            lambda x: x['props']['pageProps']['article']['body']['content']) or []

        entries = []
        for video in json_map:
            if not any(video['data'].get(attr) == 'Brightcove' for attr in ('name', 'type')):
                continue
            video_id = video['data']['id']
            account_id = video['data']['accountId']
            player_id = video['data']['playerId']
            entries.append(self.url_result(
                smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % (account_id, player_id, video_id), {
                    # ITV does not like some GB IP ranges, so here are some
                    # IP blocks it accepts
                    'geo_ip_blocks': [
                        '193.113.0.0/16', '54.36.162.0/23', '159.65.16.0/21',
                    ],
                    'referrer': url,
                }),
                ie=BrightcoveNewIE.ie_key(), video_id=video_id))

        title = self._og_search_title(webpage, fatal=False)

        return self.playlist_result(entries, playlist_id, title)

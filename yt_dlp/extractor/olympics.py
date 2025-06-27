from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    parse_qs,
    try_get,
    update_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class OlympicsReplayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?olympics\.com/[a-z]{2}/(?:paris-2024/)?(?:replay|videos?|original-series/episode)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://olympics.com/fr/video/men-s-109kg-group-a-weightlifting-tokyo-2020-replays',
        'info_dict': {
            'id': 'f6a0753c-8e6f-4b7d-a435-027054a4f8e9',
            'ext': 'mp4',
            'title': '+109kg (H) Groupe A - Haltérophilie | Replay de Tokyo 2020',
            'upload_date': '20210801',
            'timestamp': 1627797600,
            'description': 'md5:c66af4a5bc7429dbcc43d15845ff03b3',
            'thumbnail': 'https://img.olympics.com/images/image/private/t_1-1_1280/primary/nua4o7zwyaznoaejpbk2',
            'duration': 7017.0,
        },
    }, {
        'url': 'https://olympics.com/en/original-series/episode/b-boys-and-b-girls-take-the-spotlight-breaking-life-road-to-paris-2024',
        'info_dict': {
            'id': '32633650-c5ee-4280-8b94-fb6defb6a9b5',
            'ext': 'mp4',
            'title': 'B-girl Nicka - Breaking Life, Road to Paris 2024 | Episode 1',
            'upload_date': '20240517',
            'timestamp': 1715948200,
            'description': 'md5:f63d728a41270ec628f6ac33ce471bb1',
            'thumbnail': 'https://img.olympics.com/images/image/private/t_1-1_1280/primary/a3j96l7j6so3vyfijby1',
            'duration': 1321.0,
        },
    }, {
        'url': 'https://olympics.com/en/paris-2024/videos/men-s-preliminaries-gbr-esp-ned-rsa-hockey-olympic-games-paris-2024',
        'info_dict': {
            'id': '3d96db23-8eee-4b7c-8ef5-488a0361026c',
            'ext': 'mp4',
            'title': 'Men\'s Preliminaries GBR-ESP & NED-RSA | Hockey | Olympic Games Paris 2024',
            'upload_date': '20240727',
            'timestamp': 1722066600,
        },
        'skip': 'Geo-restricted to RU, BR, BT, NP, TM, BD, TL',
    }, {
        'url': 'https://olympics.com/en/paris-2024/videos/dnp-suni-lee-i-have-goals-and-i-have-expectations-for-myself-but-i-also-am-trying-to-give-myself-grace',
        'info_dict': {
            'id': 'a42f37ab-8a74-41d0-a7d9-af27b7b02a90',
            'ext': 'mp4',
            'title': 'md5:c7cfbc9918636a98e66400a812e4d407',
            'upload_date': '20240729',
            'timestamp': 1722288600,
        },
    }]
    _GEO_BYPASS = False

    def _extract_from_nextjs_data(self, webpage, video_id):
        data = traverse_obj(self._search_nextjs_data(webpage, video_id, default={}), (
            'props', 'pageProps', 'page', 'items',
            lambda _, v: v['name'] == 'videoPlaylist', 'data', 'currentVideo', {dict}, any))
        if not data:
            return None

        geo_countries = traverse_obj(data, ('countries', ..., {str}))
        if traverse_obj(data, ('geoRestrictedVideo', {bool})):
            self.raise_geo_restricted(countries=geo_countries)

        is_live = traverse_obj(data, ('streamingStatus', {str})) == 'LIVE'
        m3u8_url = traverse_obj(data, ('videoUrl', {url_or_none})) or data['streamUrl']
        tokenized_url = self._tokenize_url(m3u8_url, data['jwtToken'], is_live, video_id)

        try:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                tokenized_url, video_id, 'mp4', m3u8_id='hls')
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and 'georestricted' in e.cause.msg:
                self.raise_geo_restricted(countries=geo_countries)
            raise

        return {
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            **traverse_obj(data, {
                'id': ('videoID', {str}),
                'title': ('title', {str}),
                'timestamp': ('contentDate', {parse_iso8601}),
            }),
        }

    def _tokenize_url(self, url, token, is_live, video_id):
        return self._download_json(
            'https://metering.olympics.com/tokengenerator', video_id,
            'Downloading tokenized m3u8 url', query={
                **parse_qs(url),
                'url': update_url(url, query=None),
                'service-id': 'live' if is_live else 'vod',
                'user-auth': token,
            })['data']['url']

    def _legacy_tokenize_url(self, url, video_id):
        return self._download_json(
            'https://olympics.com/tokenGenerator', video_id,
            'Downloading legacy tokenized m3u8 url', query={'url': url})

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if info := self._extract_from_nextjs_data(webpage, video_id):
            return info

        title = self._html_search_meta(('title', 'og:title', 'twitter:title'), webpage)
        video_uuid = self._html_search_meta('episode_uid', webpage)
        m3u8_url = self._html_search_meta('video_url', webpage)
        json_ld = self._search_json_ld(webpage, video_uuid)
        thumbnails_list = json_ld.get('image')
        if not thumbnails_list:
            thumbnails_list = self._html_search_regex(
                r'["\']image["\']:\s*["\']([^"\']+)["\']', webpage, 'images', default='')
            thumbnails_list = thumbnails_list.replace('[', '').replace(']', '').split(',')
            thumbnails_list = [thumbnail.strip() for thumbnail in thumbnails_list]
        thumbnails = []
        for thumbnail in thumbnails_list:
            width_a, height_a, width = self._search_regex(
                r'/images/image/private/t_(?P<width_a>\d+)-(?P<height_a>\d+)_(?P<width>\d+)/primary/[\W\w\d]+',
                thumbnail, 'thumb', group=(1, 2, 3), default=(None, None, None))
            width_a, height_a, width = int_or_none(width_a), int_or_none(height_a), int_or_none(width)
            thumbnails.append({
                'url': thumbnail,
                'width': width,
                'height': int_or_none(try_get(width, lambda x: x * height_a / width_a)),
            })

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            self._legacy_tokenize_url(m3u8_url, video_uuid), video_uuid, 'mp4', m3u8_id='hls')

        return {
            'id': video_uuid,
            'title': title,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            **json_ld,
        }

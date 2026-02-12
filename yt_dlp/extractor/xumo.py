import datetime as dt
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    mimetype2ext,
    parse_age_limit,
    parse_iso8601,
    parse_resolution,
    str_or_none,
    unified_timestamp,
    url_basename,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class XumoBaseIE(InfoExtractor):
    _API_BASE = 'https://valencia-app-mds.xumo.com/v2'
    _GEO_COUNTRIES = ['US']

    def _extract_thumbnails(self, webpage, video_id=None):
        video_id = re.escape(video_id) if video_id else r''

        thumbnails = []
        data_srcset = self._search_regex(
            rf'<img[^>]+data-srcset\s*=\s*["\']([^"\']*{video_id}[^"\']+)',
            webpage, 'data srcset', default='')
        for data in data_srcset.split(','):
            if clean_data := clean_html(data):
                thumbnail_url = clean_data.split()[0]
                thumbnails.append({
                    'url': thumbnail_url,
                    **parse_resolution(url_basename(thumbnail_url)),
                })

        return thumbnails

    def _extract_formats_and_subtitles(self, item, video_id, caption_key='file'):
        formats, subtitles = [], {}
        for source in traverse_obj(item, (
            'providers', ..., 'sources', lambda _, v: url_or_none(v['uri']),
        )):
            ext = mimetype2ext(source['produces'])
            manifest_url = source['uri']
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    manifest_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    manifest_url, video_id, mpd_id='dash', fatal=False)
            else:
                self.report_warning(f'Unsupported stream type: {ext}')
                continue
            if source.get('drm'):
                for f in fmts:
                    f['has_drm'] = True

            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        self._remove_duplicate_formats(formats)

        for caption in traverse_obj(item, (
            'providers', ..., 'captions', lambda _, v: url_or_none(v[caption_key]),
        )):
            lang = traverse_obj(caption, ('lang', {clean_html}, filter)) or 'und'
            caption_url = caption[caption_key]
            subtitles.setdefault(lang, []).append({
                'ext': determine_ext(caption_url),
                'url': caption_url,
            })

        return formats, subtitles

    def _parse_metadata(self, webpage, item_id, slug):
        nextjs_data = self._search_nextjs_data(webpage, item_id)
        entity = traverse_obj(nextjs_data, (
            'props', 'pageProps', 'page', 'entity', {dict}))
        formats, subtitles = self._extract_formats_and_subtitles(entity, item_id)

        return {
            'id': item_id,
            'alt_title': slug,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': self._extract_thumbnails(webpage),
            **traverse_obj(entity, {
                'title': ('title', {clean_html}, filter),
                'age_limit': ('rating', {parse_age_limit}),
                'description': ('description', {clean_html}, filter),
                'duration': ('duration', {int_or_none}),
                'episode_number': ('episode', {int_or_none}),
                'release_year': ('year', {int_or_none}),
                'season_number': ('season', {int_or_none}),
                'timestamp': ('uploadDate', {parse_iso8601}),
            }),
        }


class XumoIE(XumoBaseIE):
    _VALID_URL = [
        r'https?://play\.xumo\.com/free-movies/(?P<slug>[\w-]+)/(?P<id>[0-9A-Z]+)',
        r'https?://play\.xumo\.com/networks/(?P<slug>[\w-]+)(?:/\d+/(?P<id>[0-9A-Z]+))?/\d+',
    ]
    _TESTS = [{
        'url': 'https://play.xumo.com/free-movies/lone-star-shark/XM08RIB78GYPVR',
        'info_dict': {
            'id': 'XM08RIB78GYPVR',
            'ext': 'mp4',
            'title': 'Lone Star Shark',
            'age_limit': 14,
            'alt_title': 'lone-star-shark',
            'description': 'md5:8062c5f5265882d31232bbaa8c8065a0',
            'duration': 3915,
            'release_year': 2025,
            'thumbnail': r're:https?://.+\.webp',
            'timestamp': 1738386000,
            'upload_date': '20250201',
        },
    }, {
        'url': 'https://play.xumo.com/networks/outdoor-america/99991374/XM09CDP4IRREOU/33877',
        'info_dict': {
            'id': 'XM09CDP4IRREOU',
            'ext': 'mp4',
            'title': 'Starting Strong',
            'age_limit': 0,
            'alt_title': 'outdoor-america',
            'description': 'md5:3a26a087847cef9d2e4decdd796c1e7e',
            'display_id': '33877',
            'duration': 1343,
            'thumbnail': r're:https?://.+\.webp',
            'timestamp': 1614639648,
            'upload_date': '20210301',
        },
    }, {
        'url': 'https://play.xumo.com/networks/ufc/99951134',
        'info_dict': {
            'id': 'XMKXM2NI2VFN7O',
            'ext': 'mp4',
            'title': str,
            'alt_title': 'ufc',
            'description': 'md5:a8a0d893c8538efb7aa0a54d331d53d9',
            'display_id': '99951134',
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+\.webp',
            'timestamp': int,
            'upload_date': r're:\d{8}',
        },
        'params': {'skip_download': 'Livestream'},
    }]

    def _real_extract(self, url):
        slug, video_id = self._match_valid_url(url).group('slug', 'id')
        display_id = url_basename(url)
        webpage = self._download_webpage(url, video_id or display_id)

        if not video_id:
            nextjs_data = self._search_nextjs_data(webpage, display_id)
            onnow = traverse_obj(nextjs_data, (
                'props', 'pageProps', 'page', 'onnownext', 'onnow', {dict}))
            video_id = onnow['id']
            timestamp = traverse_obj(onnow, ('start', {int_or_none}))

            broadcast = self._download_json(
                f'{self._API_BASE}/channels/channel/{display_id}/broadcast.json',
                video_id, query={'hour': dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).hour})
            m3u8_url = traverse_obj(broadcast, ('ssaiStreamUrl', {url_or_none}, {require('m3u8 URL')}))
            formats, _ = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4')

            return {
                'id': video_id,
                'alt_title': slug,
                'display_id': display_id,
                'formats': formats,
                'is_live': True,
                'thumbnails': self._extract_thumbnails(webpage),
                'timestamp': timestamp,
                **traverse_obj(onnow, {
                    'title': ('title', {clean_html}, filter),
                    'description': ('description', {clean_html}, filter),
                }),
            }

        return {
            'display_id': display_id,
            **self._parse_metadata(webpage, video_id, slug),
        }


class XumoTVShowsIE(XumoBaseIE):
    _VALID_URL = r'https?://play\.xumo\.com/tv-shows/(?P<series_id>[\w-]+)/(?P<id>[0-9A-Z]+)(?:/(?P<video_id>[0-9A-Z]+))?'
    _TESTS = [{
        'url': 'https://play.xumo.com/tv-shows/heartland/XM0CQEPINO0083/XM0KKHJH55ZOT8',
        'info_dict': {
            'id': 'XM0KKHJH55ZOT8',
            'ext': 'mp4',
            'title': 'Leaving a Legacy',
            'age_limit': 12,
            'description': 'md5:40cdacec9ce1e0c686bbb7829e343f60',
            'display_id': 'XM0CQEPINO0083',
            'duration': 2643,
            'episode': 'Leaving a Legacy',
            'episode_id': 'XM0KKHJH55ZOT8',
            'episode_number': 10,
            'genres': ['Drama'],
            'release_year': 2021,
            'season': 'Season 15',
            'season_number': 15,
            'series': 'Heartland',
            'series_id': 'heartland',
            'tags': 'count:14',
            'thumbnail': r're:https?://.+\.webp',
            'timestamp': 1759968895,
            'upload_date': '20251009',
        },
    }, {
        'url': 'https://play.xumo.com/tv-shows/the-grill-next-door/XM0WX5N36XS5FX',
        'info_dict': {
            'id': 'the-grill-next-door',
            'title': 'The Grill Next Door',
        },
        'playlist_count': 8,
    }, {
        'url': 'https://play.xumo.com/tv-shows/strays/XM05G17JOCDVFA',
        'info_dict': {
            'id': 'strays',
            'title': 'Strays',
        },
        'playlist_count': 20,
    }]

    def _entries(self, webpage, series_id, series_url):
        nextjs_data = self._search_nextjs_data(webpage, series_id)
        for video_id in traverse_obj(nextjs_data, (
            'props', 'pageProps', 'page', 'entity',
            'seasons', ..., 'cards', ..., 'id', {str_or_none},
        )):
            yield self.url_result(f'{series_url}/{video_id}', XumoTVShowsIE)

    def _real_extract(self, url):
        series_id, display_id, video_id = self._match_valid_url(url).group('series_id', 'id', 'video_id')
        series_url = f'https://play.xumo.com/tv-shows/{series_id}/{display_id}'
        webpage = self._download_webpage(series_url, series_id)
        series = self._og_search_title(webpage)

        if video_id:
            query = [
                'availableSince', 'descriptions', 'episode',
                'genres', 'keywords', 'originalReleaseYear',
                'providers', 'ratings', 'runtime', 'season', 'title',
            ]
            asset = self._download_json(
                f'{self._API_BASE}/assets/asset/{video_id}.json', video_id, query={'f': query})
            formats, subtitles = self._extract_formats_and_subtitles(asset, video_id, caption_key='url')

            return {
                'id': video_id,
                'display_id': display_id,
                'episode_id': video_id,
                'formats': formats,
                'series': series,
                'series_id': series_id,
                'subtitles': subtitles,
                'thumbnail': f'https://image.xumo.com/v1/assets/asset/{video_id}/800x450.webp',
                **traverse_obj(asset, {
                    'title': ('title', {clean_html}, filter),
                    'age_limit': ('ratings', ..., 'code', {parse_age_limit}, any),
                    'description': ('descriptions', ('large', 'medium', 'small', 'tiny'), {clean_html}, filter, any),
                    'duration': ('runtime', {int_or_none}),
                    'episode': ('title', {clean_html}, filter),
                    'episode_number': ('episode', {int_or_none}),
                    'genres': ('genres', ..., 'value', {clean_html}, filter),
                    'release_year': ('originalReleaseYear', {int_or_none}),
                    'season_number': ('season', {int_or_none}),
                    'tags': ('keywords', ..., {clean_html}, filter),
                    'timestamp': ('availableSince', {unified_timestamp}),
                }),
            }

        return self.playlist_result(
            self._entries(webpage, series_id, series_url), series_id, series)

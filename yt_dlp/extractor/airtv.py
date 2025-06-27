from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    determine_ext,
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    traverse_obj,
)


class AirTVIE(InfoExtractor):
    _VALID_URL = r'https?://www\.air\.tv/watch\?v=(?P<id>\w+)'
    _TESTS = [{
        # without youtube_id
        'url': 'https://www.air.tv/watch?v=W87jcWleSn2hXZN47zJZsQ',
        'info_dict': {
            'id': 'W87jcWleSn2hXZN47zJZsQ',
            'ext': 'mp4',
            'release_date': '20221003',
            'release_timestamp': 1664792603,
            'channel_id': 'vgfManQlRQKgoFQ8i8peFQ',
            'title': 'md5:c12d49ed367c3dadaa67659aff43494c',
            'upload_date': '20221003',
            'duration': 151,
            'view_count': int,
            'thumbnail': 'https://cdn-sp-gcs.air.tv/videos/W/8/W87jcWleSn2hXZN47zJZsQ/b13fc56464f47d9d62a36d110b9b5a72-4096x2160_9.jpg',
            'timestamp': 1664792603,
        },
    }, {
        # with youtube_id
        'url': 'https://www.air.tv/watch?v=sv57EC8tRXG6h8dNXFUU1Q',
        'info_dict': {
            'id': '2ZTqmpee-bQ',
            'ext': 'mp4',
            'comment_count': int,
            'tags': 'count:11',
            'channel_follower_count': int,
            'like_count': int,
            'uploader': 'Newsflare',
            'thumbnail': 'https://i.ytimg.com/vi_webp/2ZTqmpee-bQ/maxresdefault.webp',
            'availability': 'public',
            'title': 'Geese Chase Alligator Across Golf Course',
            'uploader_id': 'NewsflareBreaking',
            'channel_url': 'https://www.youtube.com/channel/UCzSSoloGEz10HALUAbYhngQ',
            'description': 'md5:99b21d9cea59330149efbd9706e208f5',
            'age_limit': 0,
            'channel_id': 'UCzSSoloGEz10HALUAbYhngQ',
            'uploader_url': 'http://www.youtube.com/user/NewsflareBreaking',
            'view_count': int,
            'categories': ['News & Politics'],
            'live_status': 'not_live',
            'playable_in_embed': True,
            'channel': 'Newsflare',
            'duration': 37,
            'upload_date': '20180511',
        },
    }]

    def _get_formats_and_subtitle(self, json_data, video_id):
        formats, subtitles = [], {}
        for source in traverse_obj(json_data, 'sources', 'sources_desktop', ...):
            ext = determine_ext(source.get('src'), mimetype2ext(source.get('type')))
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(source.get('src'), video_id)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({'url': source.get('src'), 'ext': ext})
        return formats, subtitles

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['initialState']['videos'][display_id]
        if nextjs_json.get('youtube_id'):
            return self.url_result(
                f'https://www.youtube.com/watch?v={nextjs_json.get("youtube_id")}', YoutubeIE)

        formats, subtitles = self._get_formats_and_subtitle(nextjs_json, display_id)
        return {
            'id': display_id,
            'title': nextjs_json.get('title') or self._html_search_meta('og:title', webpage),
            'formats': formats,
            'subtitles': subtitles,
            'description': nextjs_json.get('description') or None,
            'duration': int_or_none(nextjs_json.get('duration')),
            'thumbnails': [
                {'url': thumbnail}
                for thumbnail in traverse_obj(nextjs_json, ('default_thumbnails', ...))],
            'channel_id': traverse_obj(nextjs_json, 'channel', 'channel_slug'),
            'timestamp': parse_iso8601(nextjs_json.get('created')),
            'release_timestamp': parse_iso8601(nextjs_json.get('published')),
            'view_count': int_or_none(nextjs_json.get('views')),
        }

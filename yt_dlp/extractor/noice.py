from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    parse_iso8601,
    traverse_obj
)


class NoicePodcastIE(InfoExtractor):
    _VALID_URL = r'https?://open\.noice\.id/content/(?P<id>[a-fA-F0-9-]+)'
    _TESTS = [{
        'url': 'https://open.noice.id/content/7694bb04-ff0f-40fa-a60b-5b39f29584b2',
        'info_dict': {
            'id': '7694bb04-ff0f-40fa-a60b-5b39f29584b2',
            'ext': 'mp3',
            'season': 'Season 1',
            'description': 'md5:58d1274e6857b6fbbecf47075885380d',
            'release_date': '20221115',
            'timestamp': 1668496642,
            'season_number': 1,
            'upload_date': '20221115',
            'release_timestamp': 1668496642,
            'title': 'Eps 1. Belajar dari Wishnutama: Kreatif Bukan Followers! (bersama Wishnutama)',
            'modified_date': '20221121',
            'duration': 3567,
            'modified_timestamp': 1669030647,
            'thumbnail': 'https://images.noiceid.cc/catalog/content-1668496302560',
        }
    }]

    def _get_formats_and_subtitles(self, media_url, video_id):
        formats, subtitles = [], {}
        if isinstance(media_url, str):
            media_url = [media_url]
        for url in media_url:
            ext = determine_ext(url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(url, video_id)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': url,
                    'ext': 'mp3',
                })
        return formats, subtitles

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        nextjs_data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['contentDetails']

        media_url_list = traverse_obj(nextjs_data, (('rawContentUrl', 'url'), ))
        formats, subtitles = self._get_formats_and_subtitles(media_url_list, display_id)

        return {
            'id': nextjs_data.get('id') or display_id,
            'title': nextjs_data.get('title') or self._html_search_meta('og:title', webpage),
            'formats': formats,
            'subtitles': subtitles,
            'description': (nextjs_data.get('description') or clean_html(nextjs_data.get('htmlDescription'))
                            or self._html_search_meta(['description', 'og:title', ''], webpage)),
            'thumbnail': nextjs_data.get('image') or self._html_search_meta('og:image', webpage),
            'timestamp': parse_iso8601(nextjs_data.get('createdAt')),
            'release_timestamp': parse_iso8601(nextjs_data.get('publishedAt')),
            'modified_timestamp': parse_iso8601(
                nextjs_data.get('updatedAt') or self._html_search_meta('og:updated_time', webpage)),
            'duration': int_or_none(nextjs_data.get('duration')),
            'season': nextjs_data.get('seasonName'),
            'season_number': int_or_none(nextjs_data.get('seasonNumber')),
        }

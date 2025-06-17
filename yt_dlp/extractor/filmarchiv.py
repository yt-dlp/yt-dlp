from .common import InfoExtractor
from ..utils import determine_ext


class FilmArchivIE(InfoExtractor):
    IE_NAME = 'FILMARCHIV ON'
    _VALID_URL = r'https?://(?:www\.)?filmarchiv\.at/(?:de|en)/filmarchiv-on/video/(?P<id>[0-9a-zA-Z_]+)'
    _TESTS = [{
        'url': 'https://www.filmarchiv.at/de/filmarchiv-on/video/f_0305p7xKrXUPBwoNE9x6mh',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': 'f_0305p7xKrXUPBwoNE9x6mh',
            'ext': 'mkv',
            'title': 'Der Wurstelprater zur Kaiserzeit',
            'description': 'md5:9843f92df5cc9a4975cee7aabcf6e3b2',
            'thumbnail': 'https://img.filmarchiv.at/unsafe/1024x1024/videostatic/f_0305/p7xKrXUPBwoNE9x6mh_v1/poster.jpg',
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)

        title = self._html_search_regex(
            r'<title-div [^>]+>\s*(.+?)\s*</title-div>',
            webpage, 'title')

        description = self._html_search_regex(
            r'<div class="(?:.+?)?border-base-content[^"]*">\s*<div class="(?:.+?)?prose[^"]*">\s*<p>\s*(.+?)\s*</p>',
            webpage, 'description')

        bucket, video_id, version = self._html_search_regex(
            r'<meta property="og:image" content="https://.+?videostatic/(?P<bucket>[^/]+)/(?P<video_id>[^_]+)_(?P<version>[^/]+)/poster.jpg[^"]+">',
            webpage, 'bucket, video_id, version', group=('bucket', 'video_id', 'version'))

        playlist_url = f'https://cdn.filmarchiv.at/{bucket}/{video_id}_{version}_sv1/playlist.m3u8'
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(playlist_url, id, fatal=False)

        return {
            'id': id,
            'title': title,
            'description': description,
            'thumbnail': f'https://img.filmarchiv.at/unsafe/1024x1024/videostatic/{bucket}/{video_id}/poster.jpg',
            'formats': formats,
            'subtitles': subtitles,
        }

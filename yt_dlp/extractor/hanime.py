from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    parse_filesize,
    float_or_none,
    int_or_none,
    parse_iso8601,
    unified_strdate,
    str_or_none,
    sanitize_url,
    compat_str,
)


class HanimeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hanime\.tv/videos/hentai/' + \
                 r'(?P<id>.+)(?:\?playlist_id=.+)?'
    _TESTS = [{
        'url': 'https://hanime.tv/videos/hentai/kuroinu-1',
        'info_dict': {
            'id': '33964',
            'display_id': 'kuroinu-1',
            'title': 'Kuroinu 1',
            'description': 'md5:37d5bb20d4a0834bd147bc1bac588a0b',
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_date': '20120127',
            'upload_date': '20140509',
            'timestamp': 1399624976,
            'creator': 'Magin Label',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'tags': list,
            'ext': 'mp4',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_slug = self._match_id(url)
        webpage = self._download_webpage(url, video_slug)
        page_json = self._html_search_regex(r'__NUXT__=({[\s\S]+});<\/script>',
                                            webpage,
                                            'Inline JSON')
        # remove delimiters
        page_json = ''.join(c for c in page_json if ord(c) >= 32)
        page_json = self._parse_json(page_json,
                                     video_slug)
        video_info = page_json['state']['data']['video']
        hentai_video = video_info['hentai_video']
        servers = video_info['videos_manifest']['servers']
        tags = []
        for tag in hentai_video.get('hentai_tags', []):
            t = tag.get('text')
            if t:
                tags.append(t)
        thumbnails = []
        if '/covers/' in hentai_video.get('poster_url'):
            poster = hentai_video.get('poster_url')
            if poster:
                thumbnails.append({'preference': 0,
                                   'id': 'Poster',
                                   'url': poster})
        elif '/posters/' in hentai_video.get('poster_url'):
            cover = hentai_video.get('cover_url')
            if cover:
                thumbnails.append({'preference': 1,
                                   'id': 'Cover',
                                   'url': cover})
        else:
            thumbnails = None
        formats = []
        video_id = None
        for server in servers:
            for stream in server['streams']:
                if stream.get('compatibility') != 'all':
                    continue
                if not video_id:
                    video_id = compat_str(stream.get('id'))
                item_url = sanitize_url(stream.get('url', ''))
                if not item_url:
                    # premium format
                    continue
                width = int_or_none(stream.get('width'))
                height = int_or_none(stream.get('height'))
                format = {
                    'width': width,
                    'height': height,
                    'filesize_approx': float_or_none(
                        parse_filesize('%sMb' % stream.get('filesize_mbs'))),
                    'duration': float_or_none(
                        stream.get('duration_in_ms', 0) / 1000),
                    'protocol': 'm3u8',
                    'format_id': 'mp4-%sp' % stream.get('height'),
                    'ext': 'mp4',
                    'url': item_url,
                }
                formats.append(format)
        formats.reverse()

        release_date = unified_strdate(hentai_video.get('released_at')
                                       or compat_str(
                                           hentai_video.get(
                                               'released_at_unix')))
        upload_date = unified_strdate(hentai_video.get('created_at')
                                      or compat_str(
                                          hentai_video.get('created_at_unix')))
        timestamp = int_or_none(hentai_video.get('created_at_unix')
                                or parse_iso8601(
                                    hentai_video.get('created_at')))
        duration = float_or_none((hentai_video.get('duration_in_ms')
                                  or servers[0].get('streams', [{}])[0].get(
                                      'duration_in_ms',
                                      0)) / 1000)
        return {
            'id': video_id or hentai_video.get('id') or video_slug,
            'display_id': video_slug,
            'title': hentai_video.get('name') or video_slug.replace('-', ' '),
            'description': clean_html(hentai_video.get('description')),
            'thumbnails': thumbnails,
            'release_date': release_date,
            'upload_date': upload_date,
            'timestamp': timestamp,
            'creator': str_or_none(hentai_video.get('brand')),
            'view_count': int_or_none(hentai_video.get('views')),
            'like_count': int_or_none(hentai_video.get('likes')),
            'dislike_count': int_or_none(hentai_video.get('dislikes')),
            'duration': duration,
            'tags': tags,
            'formats': formats,
            'age_limit': 18,
        }

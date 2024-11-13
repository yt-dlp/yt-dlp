import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    parse_filesize,
    parse_resolution,
    unified_timestamp,
    urljoin,
)


class AlphaPornoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?alphaporno\.com/videos/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://www.alphaporno.com/videos/sensual-striptease-porn-with-samantha-alexandra/',
        'md5': '7e6a1cdd48fa67362a5a11d7039164e7',
        'info_dict': {
            'id': '258807',
            'display_id': 'sensual-striptease-porn-with-samantha-alexandra',
            'ext': 'mp4',
            'title': 'Sensual striptease porn with Samantha Alexandra',
            'description': 'md5:3c6d31008980654acaeb11451454a62c',
            'thumbnail': r're:https?://.*\.jpg$',
            'timestamp': 1418701811,
            'upload_date': '20141216',
            'duration': 387,
            'categories': list,
            'age_limit': 18,
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, display_id)

        info = {
            'display_id': display_id,
        }
        video_id = self._search_regex(
            r"video_id\s*:\s*'([^']+)'", webpage, 'video id', default=None)
        if video_id:
            info['url'] = self._search_regex(
                r"video_url\s*:\s*'([^']+)'", webpage, 'video url')
            info['ext'] = self._html_search_meta(
                'encodingFormat', webpage, 'ext', default='.mp4')[1:]
        else:
            video_id = self._search_regex(
                r'video_id=(\d+)\b', webpage, 'video id')
            formats = []
            joined_url = urljoin(urlh.url, rf'/get_file/\d.+?/{video_id}/{video_id}_(\w+)\..+?')
            for video_url, res in re.findall(rf'''({joined_url})(?:'|"|\b)\s''', webpage):
                fmt = {
                    'format_id': f'f{res}',
                    'url': video_url,
                }
                fmt.update(parse_resolution(res) or {})
                formats.append(fmt)
            info['formats'] = formats

        title = (
            self._html_search_regex(r'<title[^>]*>([^<]+?)(?:\s*-\s*Alpha\s*Porno\s*)?<', webpage, 'title', default=None)
            or self._og_search_title(webpage, default=None)
            or self._search_regex(
                (r'<meta content="([^"]+)" itemprop="description">',
                 r'class="title" itemprop="name">([^<]+)<'),
                webpage, 'title')
        )
        description = (
            self._og_search_description(webpage)
            or self._search_regex(
                r'<meta content="([^"]+)" itemprop="description">',
                webpage, 'description')
        )
        thumbnail = (
            self._og_search_thumbnail(webpage)
            or self._html_search_meta('thumbnail', webpage, 'thumbnail')
        )
        timestamp = unified_timestamp(self._og_search_property('video:release_date', webpage)
                                      or self._html_search_meta('uploadDate', webpage, 'upload date'))
        duration = parse_duration(self._og_search_property('video:duration', webpage)
                                  or self._html_search_meta('duration', webpage, 'duration'))
        filesize_approx = parse_filesize(self._html_search_meta(
            'contentSize', webpage, 'file size', default=None))
        bitrate = int_or_none(self._html_search_meta(
            'bitrate', webpage, 'bitrate', default=None))
        categories = re.split(
            r'\s*,\s*',
            self._html_search_meta(
                'keywords', webpage, 'categories', default=''))

        age_limit = self._rta_search(webpage)

        info.update({
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'filesize_approx': filesize_approx,
            'tbr': bitrate,
            'categories': categories,
            'age_limit': age_limit,
        })
        return info

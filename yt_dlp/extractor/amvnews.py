import re
from collections import defaultdict

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    float_or_none,
    parse_duration,
    unescapeHTML,
    urljoin,
)


class AMVNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?amvnews\.ru/(?:index.php)?\?go=Files&in=view&id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://amvnews.ru/index.php?go=Files&in=view&id=12345',
        'info_dict': {
            'id': '12345',
            'ext': 'mp4',
            'description': 'md5:3c1391ce952f2125ce615b43081de1d0',
            'title': 'Jadeite | Music: Jai Wolf - Lost',
            'duration': 113,
            'creator': 'Leafa',
            'formats': [
                {
                    'url': 'https://amvnews.ru/index.php?go=Files&file=down&id=12345&alt=4',
                    'ext': 'mp4',
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'width': 640,
                    'height': 360,
                    'fps': 23.98,
                },
                {
                    'url': 'https://amvnews.ru/index.php?go=Files&file=down&id=12345',
                    'ext': 'mp4',
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'width': 1920,
                    'height': 1080,
                    'fps': 23.98,
                },
                {
                    'url': 'https://amvnews.ru/index.php?go=Files&file=down&id=12345&alt=1',
                    'ext': 'mp4',
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'width': 3840,
                    'height': 2160,
                    'fps': 23.98,
                }
            ],
        }
    }]

    def _real_extract(self, html_url):
        video_id = self._match_id(html_url)
        webpage = self._download_webpage(html_url, video_id)

        formats = []
        subtitles = defaultdict(list)

        for link, info, name in re.findall(
                r'<a href="(?P<link>[^"]+)"[^>]*?(?:overlib\(\'(?P<info>[^\']*)\'[^>]*)?>Download *(?P<name>[^<]*)</a>',
                webpage, flags=re.IGNORECASE):

            url = urljoin('https://amvnews.ru/', unescapeHTML(link))

            clean_name = clean_html(name)

            if 'subtitle' in clean_name.lower():
                # there are usually only english and russian subtitles (en, ru)
                subtitles[clean_name.lower()[0:2]].append({
                    'url': url,
                    'ext': self._search_regex(r'<b>type</b>: (\w+)', info.lower(), 'ext', default='srt'),
                    'name': clean_name,
                })
            elif '<b>resolution</b>: ' in info.lower():
                formats.append({
                    'url': url,
                    'ext': 'mp4',
                    'format_note': clean_name,
                    'vcodec': self._search_regex(r'<b>Codecs</b>: (\w+)', info, 'vcodec', fatal=False, flags=re.IGNORECASE),
                    'acodec': self._search_regex(r'<b>Codecs</b>: \w+(?:\s*\([^\)]*\))*\/(\w+)', info, 'acodec',
                                                 fatal=False, flags=re.IGNORECASE),
                    'width': int_or_none(self._search_regex(r'<b>Resolution</b>: (\d+)', info, 'width',
                                                            fatal=False, flags=re.IGNORECASE)),
                    'height': int_or_none(self._search_regex(r'<b>Resolution</b>: \d+x(\d+)', info, 'height',
                                                             fatal=False, flags=re.IGNORECASE)),
                    'fps': float_or_none(self._search_regex(r'<b>Resolution</b>: \d+x\d+\@([\d\.]+)', info, 'fps',
                                                            fatal=False, flags=re.IGNORECASE)),
                    'duration': parse_duration(self._search_regex(r'<b>Duration</b>: ([ \w]+)', info, 'duration',
                                                                  fatal=False, flags=re.IGNORECASE)),
                })

        title = self._html_extract_title(webpage)
        if title:
            title = title.removeprefix('AMV | Videos | ')

        url = None
        if not formats:  # use "url" field instead
            formats = None
            url = 'https://amvnews.ru/index.php?go=Files&file=down&id=' + str(video_id)

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_regex(r'<div itemprop="description">(.*?)</div>', webpage, 'description',
                                                   fatal=False, flags=re.DOTALL | re.IGNORECASE),
            'creator': self._html_search_regex(r'<span itemprop="name">(.*?)</span>', webpage, 'creator',
                                               fatal=False, flags=re.IGNORECASE),
            'url': url,
            'formats': formats,
            'subtitles': subtitles,
        }

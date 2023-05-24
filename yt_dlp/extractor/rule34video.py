import re

from ..utils import parse_duration
from .common import InfoExtractor


class Rule34VideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/videos/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://rule34video.com/videos/3065157/shot-it-mmd-hmv/',
            'md5': 'ffccac2c23799dabbd192621ae4d04f3',
            'info_dict': {
                'id': '3065157',
                'ext': 'mp4',
                'title': 'Shot It-(mmd hmv)',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065157/preview.jpg',
                'duration': 347.0,
                'age_limit': 18,
                'tags': ["ahegao", "cum in mouth", "cum in urethra", "chest", "animation", "music", "sex sounds", "sound", "iwara", "3d", "compilation", "pmv", "straight", "mmd"]
            }
        },
        {
            'url': 'https://rule34video.com/videos/3065296/lara-in-trouble-ep-7-wildeerstudio/',
            'md5': '6bb5169f9f6b38cd70882bf2e64f6b86',
            'info_dict': {
                'id': '3065296',
                'ext': 'mp4',
                'title': 'Lara in Trouble Ep. 7 [WildeerStudio]',
                'thumbnail': 'https://rule34video.com/contents/videos_screenshots/3065000/3065296/preview.jpg',
                'duration': 938.0,
                'age_limit': 18,
                'tags': ["lara croft (tomb raider)", "2girls", "milking", "breast sucking", "finger sucking", "nipple sucking", "lesbian", "big breasts", "breast milk", "cum on stomach", "on stomach", "strapon", "sex slave", "sex toy", "blowjob", "deepthroat", "throat bulge", "slave", "bdsm", "bondage", "vaginal penetration", "anal", "anal creampie", "deep rimming", "rimming", "anilingus", "butt plug", "ahegao", "creampie", "cum inside", "cum dripping", "from behind", "cum inflation", "cum explosion", "fingering", "facefuck", "gagged", "sound", "rape", "arms tied", "hands tied", "tied", "tied arms", "tied down", "tied hands", "tied up", "bound", "bound hands", "bound wrists", "straight"]
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []

        for mobj in re.finditer(r'<a[^>]+href="(?P<video_url>[^"]+download=true[^"]+)".*>(?P<ext>[^\s]+) (?P<quality>[^<]+)p</a>', webpage):
            url, ext, quality = mobj.groups()
            formats.append({
                'url': url,
                'ext': ext.lower(),
                'quality': quality,
            })

        title = self._html_extract_title(webpage)
        thumbnail = self._html_search_regex(r'preview_url:\s+\'([^\']+)\'', webpage, 'thumbnail', default=None)
        duration = self._html_search_regex(r'"icon-clock"></i>\s+<span>((?:\d+:?)+)', webpage, 'duration', default=None)
        tags = []
        for match in re.finditer(r'<a class=\"tag_item\"\s+href=\"https://rule34video\.com/tags/\d+/\".*>(?P<tag>.*)</a>', webpage):
            tag = match.group('tag')
            if tag:
                tags.append(tag.strip())

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
            'duration': parse_duration(duration),
            'age_limit': 18,
            'tags': tags
        }

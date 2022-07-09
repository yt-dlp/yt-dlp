# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

import re

from ..utils import (
    clean_html,
    determine_ext,
    get_element_by_class,
    urljoin,
    parse_qs as compat_parse_qs,
    ExtractorError)


class WikimediaIE(InfoExtractor):
    IE_NAME = 'wikimedia.org'
    _NETRC_MACHINE = 'wikimediaorg'
    _API_BASE_URL = 'https://commons.wikimedia.org/'
    _VALID_URL = 'https://commons.wikimedia.org/wiki/File:(?P<id>[^/]+)'

    _TEST = {
        'url': 'https://commons.wikimedia.org/wiki/File:Die_Temperaturkurve_der_Erde_(ZDF,_Terra_X)_720p_HD_50FPS.webm',
        'info_dict': {
            'description': 'md5:7cd84f76e7081f1be033d0b155b4a460',
            'ext': 'webm', 'id': 'Die_Temperaturkurve_der_Erde_(ZDF,_Terra_X)_720p_HD_50FPS',
            'title': 'Die Temperaturkurve der Erde (ZDF, Terra X) 720p HD 50FPS.webm - Wikimedia Commons',
            'license': 'md5:62907cddf705a9f7ae7076c15407a977',
            'author': None, 'subtitles': {'de': [{'ext': 'srt',
                                                  'url': 'https?://commons.wikimedia.org/w/api.php'}],
                                          'en-gb': [{'ext': 'srt',
                                                     'url': 'https?://commons.wikimedia.org/w/api.php'}],
                                          'nl': [{'ext': 'srt',
                                                  'url': 'https?://commons.wikimedia.org/w/api.php'}],
                                          'en': [{'ext': 'srt',
                                                  'url': 're:https?://commons.wikimedia.org/w/api.php'}]}}
    }


    def _real_extract(self, url):
        video_id = self._match_id(url)
        ext = determine_ext(url, None)
        if ext is None:
            raise ExtractorError('invalid video url', expected=True)
        webpage = self._download_webpage(url, video_id)
        self.report_extraction(video_id)
        video_url = self._html_search_regex('<source [^>]*src="([^"]+)"', webpage,
                                            'video URL')
        license = get_element_by_class('layouttemplate licensetpl mw-content-ltr', webpage)
        license = clean_html(license)

        description = get_element_by_class('description', webpage)
        author = self._html_search_regex(r'>\s*Author\s*</td>\s*<td\b[^>]*>\s*([^<]+?)\s*</td>',
                                         webpage, 'video author', default=None)
        info = {'url': video_url, 'description': clean_html(description), 'ext': ext,
                'id': video_id.replace('.' + ext, ''), 'title': self._og_search_title(webpage).replace('File:', ''),
                'license': license, 'author': author}

        subtitles = {}
        for sub in re.findall(r'''\bsrc\s*=\s*[\"\'](\/w\/api(.*?)[\s\"])\b''', webpage):
            sub = sub[0].replace('"', '''''')
            sub = urljoin('https://commons.wikimedia.org', sub)
            qs = compat_parse_qs(sub)
            lang = qs.get('lang', [None])[-1]
            if not lang:
                continue
            subtitles[lang] = [{'ext': 'srt', 'url': sub}]
        info['subtitles'] = subtitles
        return info

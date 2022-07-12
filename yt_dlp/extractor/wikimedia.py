from .common import InfoExtractor

import re

from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    get_element_by_class,
    parse_qs,
    urljoin)


class WikimediaIE(InfoExtractor):
    IE_NAME = 'wikimedia.org'
    _API_BASE_URL = 'https://commons.wikimedia.org/'
    _VALID_URL = 'https://commons.wikimedia.org/wiki/File:(?P<id>[^/]+)'
    _TEST = {
        'url': 'https://commons.wikimedia.org/wiki/File:Die_Temperaturkurve_der_Erde_(ZDF,_Terra_X)_720p_HD_50FPS.webm',
        'info_dict': {
            'url': 'https://upload.wikimedia.org/wikipedia/commons/transcoded/d/d7/Die_Temperaturkurve_der_Erde_%28ZDF%2C_Terra_X%29_720p_HD_50FPS.webm/Die_Temperaturkurve_der_Erde_%28ZDF%2C_Terra_X%29_720p_HD_50FPS.webm.480p.vp9.webm',
            'description': 'Deutsch:  Beschreibung auf der Seite: "Im Verlauf der Erdgeschichte glich das Klima einer Achterbahnfahrt. Die „Fieberkurve“ unseres Planeten zeigt die globalen Temperaturschwankungen bis heute – rekonstruiert anhand von historischen Klimadaten."\nZu Wikimedia Commons hochgeladen von: PantheraLeo1359531.\nHinweise zur Weiterverwendung: https://www.zdf.de/dokumentation/terra-x/terra-x-creative-commons-cc-100.html.\nVereinfachender Verlauf in der Geschichte der Erde, für die Zukunft spätestens ab dem Jahr 2050 mit spekulativem Verlauf in der Prognose (ausgeprägtes Global-warming-Szenario ist dargestellt).English:  Climate change, Temperature in history of Earth, Video of Terra X.',
            'ext': 'webm',
            'id': 'Die_Temperaturkurve_der_Erde_(ZDF,_Terra_X)_720p_HD_50FPS',
            'title': 'Die Temperaturkurve der Erde (ZDF, Terra X) 720p HD 50FPS.webm - Wikimedia Commons',
            'license': 'This file is licensed under the Creative Commons Attribution 4.0 International license. You are free: to share – to copy, distribute and transmit the work to remix – to adapt the work Under the following conditions: attribution – You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use. https://creativecommons.org/licenses/by/4.0CC BY 4.0 Creative Commons Attribution 4.0 truetrue',
            'author': 'ZDF/Terra X/Gruppe 5/Luise Wagner, Jonas Sichert, Andreas Hougardy',
            'subtitles': {
                'de': [{
                    'ext': 'vtt',
                    'url': 'https://commons.wikimedia.org/w/api.php?action=timedtext&title=File%3ADie_Temperaturkurve_der_Erde_%28ZDF%2C_Terra_X%29_720p_HD_50FPS.webm&lang=de&trackformat=vtt'
                }],
                'en-gb': [{
                    'ext': 'vtt',
                    'url': 'https://commons.wikimedia.org/w/api.php?action=timedtext&title=File%3ADie_Temperaturkurve_der_Erde_%28ZDF%2C_Terra_X%29_720p_HD_50FPS.webm&lang=en-gb&trackformat=vtt'
                }],
                'nl': [{
                    'ext': 'vtt',
                    'url': 'https://commons.wikimedia.org/w/api.php?action=timedtext&title=File%3ADie_Temperaturkurve_der_Erde_%28ZDF%2C_Terra_X%29_720p_HD_50FPS.webm&lang=nl&trackformat=vtt'
                }],
                'en': [{
                    'ext': 'vtt',
                    'url': 'https://commons.wikimedia.org/w/api.php?action=timedtext&title=File%3ADie_Temperaturkurve_der_Erde_%28ZDF%2C_Terra_X%29_720p_HD_50FPS_-_redub_NL.webm&lang=en&trackformat=vtt'
                }]
            }}}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        ext = determine_ext(url, None)
        if not ext:
            raise ExtractorError('The URL does not contain a video', expected=True)
        webpage = self._download_webpage(url, video_id)
        video_url = self._html_search_regex('<source [^>]*src="([^"]+)"', webpage, 'video URL')
        license = get_element_by_class('layouttemplate licensetpl mw-content-ltr', webpage)
        license = clean_html(license)
        description = get_element_by_class('description', webpage)
        description = clean_html(description)
        author = self._html_search_regex(r'>\s*Author\s*</td>\s*<td\b[^>]*>\s*([^<]+)\s*</td>', webpage, 'video author',
                                         default=None)
        video_id = video_id.replace('.' + ext, '')

        subtitles = {}
        for sub in re.findall(r"\bsrc\s*=\s*[\"\'](\/w\/api(.*?)[\s\"])\b", webpage):
            sub = sub[0].replace('"', '')
            sub = urljoin('https://commons.wikimedia.org', sub).replace('amp;', '').strip()
            qs = parse_qs(sub)
            lang = qs.get('lang', [None])[-1]
            sub_ext = qs.get('trackformat', [None])[-1]
            if not lang or not sub_ext:
                continue
            subtitles.setdefault(lang, []).append({'ext': sub_ext, 'url': sub})

        return {'url': video_url,
                'description': description,
                'ext': ext,
                'id': video_id,
                'title': self._og_search_title(webpage).replace('File:', ''),
                'license': license,
                'author': author,
                'subtitles': subtitles
                }

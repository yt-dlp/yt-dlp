# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    orderedSet,
    parse_duration,
    parse_qs,
    qualities,
    unified_strdate,
    xpath_text
)


class EuropaIE(InfoExtractor):
    _VALID_URL = r'https?://ec\.europa\.eu/avservices/(?:video/player|audio/audioDetails)\.cfm\?.*?\bref=(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?ref=I107758',
        'md5': '574f080699ddd1e19a675b0ddf010371',
        'info_dict': {
            'id': 'I107758',
            'ext': 'mp4',
            'title': 'TRADE - Wikileaks on TTIP',
            'description': 'NEW  LIVE EC Midday press briefing of 11/08/2015',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150811',
            'duration': 34,
            'view_count': int,
            'formats': 'mincount:3',
        }
    }, {
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?sitelang=en&ref=I107786',
        'only_matching': True,
    }, {
        'url': 'http://ec.europa.eu/avservices/audio/audioDetails.cfm?ref=I-109295&sitelang=en',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        playlist = self._download_xml(
            'http://ec.europa.eu/avservices/video/player/playlist.cfm?ID=%s' % video_id, video_id)

        def get_item(type_, preference):
            items = {}
            for item in playlist.findall('./info/%s/item' % type_):
                lang, label = xpath_text(item, 'lg', default=None), xpath_text(item, 'label', default=None)
                if lang and label:
                    items[lang] = label.strip()
            for p in preference:
                if items.get(p):
                    return items[p]

        query = parse_qs(url)
        preferred_lang = query.get('sitelang', ('en', ))[0]

        preferred_langs = orderedSet((preferred_lang, 'en', 'int'))

        title = get_item('title', preferred_langs) or video_id
        description = get_item('description', preferred_langs)
        thumbnail = xpath_text(playlist, './info/thumburl', 'thumbnail')
        upload_date = unified_strdate(xpath_text(playlist, './info/date', 'upload date'))
        duration = parse_duration(xpath_text(playlist, './info/duration', 'duration'))
        view_count = int_or_none(xpath_text(playlist, './info/views', 'views'))

        language_preference = qualities(preferred_langs[::-1])

        formats = []
        for file_ in playlist.findall('./files/file'):
            video_url = xpath_text(file_, './url')
            if not video_url:
                continue
            lang = xpath_text(file_, './lg')
            formats.append({
                'url': video_url,
                'format_id': lang,
                'format_note': xpath_text(file_, './lglabel'),
                'language_preference': language_preference(lang)
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'formats': formats
        }

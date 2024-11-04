import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    join_nonempty,
    js_to_json,
    mimetype2ext,
    unified_strdate,
    url_or_none,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    traverse_obj,
)


class BpbIE(InfoExtractor):
    IE_DESC = 'Bundeszentrale für politische Bildung'
    _VALID_URL = r'https?://(?:www\.|m\.)?bpb\.de/(?:[^/?#]+/)*(?P<id>\d+)(?:[/?#]|$)'

    _TESTS = [{
        'url': 'http://www.bpb.de/mediathek/297/joachim-gauck-zu-1989-und-die-erinnerung-an-die-ddr',
        'info_dict': {
            'id': '297',
            'ext': 'mp4',
            'creators': ['Kooperative Berlin'],
            'description': r're:Joachim Gauck, .*\n\nKamera: .*',
            'release_date': '20150716',
            'series': 'Interview auf dem Geschichtsforum 1989 | 2009',
            'tags': [],
            'thumbnail': r're:https?://www\.bpb\.de/cache/images/7/297_teaser_16x9_1240\.jpg.*',
            'title': 'Joachim Gauck zu 1989 und die Erinnerung an die DDR',
            'uploader': 'Bundeszentrale für politische Bildung',
        },
    }, {
        'url': 'https://www.bpb.de/mediathek/video/522184/krieg-flucht-und-falschmeldungen-wirstattdesinformation-2/',
        'info_dict': {
            'id': '522184',
            'ext': 'mp4',
            'creators': ['Institute for Strategic Dialogue Germany gGmbH (ISD)'],
            'description': 'md5:f83c795ff8f825a69456a9e51fc15903',
            'release_date': '20230621',
            'series': 'Narrative über den Krieg Russlands gegen die Ukraine (NUK)',
            'tags': [],
            'thumbnail': r're:https://www\.bpb\.de/cache/images/4/522184_teaser_16x9_1240\.png.*',
            'title': 'md5:9b01ccdbf58dbf9e5c9f6e771a803b1c',
            'uploader': 'Bundeszentrale für politische Bildung',
        },
    }, {
        'url': 'https://www.bpb.de/lernen/bewegtbild-und-politische-bildung/webvideo/518789/krieg-flucht-und-falschmeldungen-wirstattdesinformation-1/',
        'info_dict': {
            'id': '518789',
            'ext': 'mp4',
            'creators': ['Institute for Strategic Dialogue Germany gGmbH (ISD)'],
            'description': 'md5:85228aed433e84ff0ff9bc582abd4ea8',
            'release_date': '20230302',
            'series': 'Narrative über den Krieg Russlands gegen die Ukraine (NUK)',
            'tags': [],
            'thumbnail': r're:https://www\.bpb\.de/cache/images/9/518789_teaser_16x9_1240\.jpeg.*',
            'title': 'md5:3e956f264bb501f6383f10495a401da4',
            'uploader': 'Bundeszentrale für politische Bildung',
        },
    }, {
        'url': 'https://www.bpb.de/mediathek/podcasts/apuz-podcast/539727/apuz-20-china/',
        'only_matching': True,
    }, {
        'url': 'https://www.bpb.de/mediathek/audio/315813/folge-1-eine-einfuehrung/',
        'info_dict': {
            'id': '315813',
            'ext': 'mp3',
            'creators': ['Axel Schröder'],
            'description': 'md5:eda9d1af34e5912efef5baf54fba4427',
            'release_date': '20200921',
            'series': 'Auf Endlagersuche. Der deutsche Weg zu einem sicheren Atommülllager',
            'tags': ['Atomenergie', 'Endlager', 'hoch-radioaktiver Abfall', 'Endlagersuche', 'Atommüll', 'Atomendlager', 'Gorleben', 'Deutschland'],
            'thumbnail': r're:https://www\.bpb\.de/cache/images/3/315813_teaser_16x9_1240\.png.*',
            'title': 'Folge 1: Eine Einführung',
            'uploader': 'Bundeszentrale für politische Bildung',
        },
    }, {
        'url': 'https://www.bpb.de/517806/die-weltanschauung-der-neuen-rechten/',
        'info_dict': {
            'id': '517806',
            'ext': 'mp3',
            'creators': ['Bundeszentrale für politische Bildung'],
            'description': 'md5:594689600e919912aade0b2871cc3fed',
            'release_date': '20230127',
            'series': 'Vorträge des Fachtags "Modernisierer. Grenzgänger. Anstifter. Sechs Jahrzehnte \'Neue Rechte\'"',
            'tags': ['Rechtsextremismus', 'Konservatismus', 'Konservativismus', 'neue Rechte', 'Rechtspopulismus', 'Schnellroda', 'Deutschland'],
            'thumbnail': r're:https://www\.bpb\.de/cache/images/6/517806_teaser_16x9_1240\.png.*',
            'title': 'Die Weltanschauung der "Neuen Rechten"',
            'uploader': 'Bundeszentrale für politische Bildung',
        },
    }, {
        'url': 'https://www.bpb.de/mediathek/reihen/zahlen-und-fakten-soziale-situation-filme/520153/zahlen-und-fakten-die-soziale-situation-in-deutschland-migration/',
        'only_matching': True,
    }]

    _TITLE_RE = re.compile('(?P<title>[^<]*)<[^>]+>(?P<series>[^<]*)')

    def _parse_vue_attributes(self, name, string, video_id):
        attributes = extract_attributes(self._search_regex(rf'(<{name}(?:"[^"]*?"|[^>])*>)', string, name))

        for key, value in attributes.items():
            if key.startswith(':'):
                attributes[key] = self._parse_json(value, video_id, transform_source=js_to_json, fatal=False)

        return attributes

    @staticmethod
    def _process_source(source):
        url = url_or_none(source['src'])
        if not url:
            return None

        source_type = source.get('type', '')
        extension = mimetype2ext(source_type)
        is_video = source_type.startswith('video')
        note = url.rpartition('.')[0].rpartition('_')[2] if is_video else None

        return {
            'url': url,
            'ext': extension,
            'vcodec': None if is_video else 'none',
            'quality': 10 if note == 'high' else 0,
            'format_note': note,
            'format_id': join_nonempty(extension, note),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title_result = traverse_obj(webpage, ({find_element(cls='opening-header__title')}, {self._TITLE_RE.match}))
        json_lds = list(self._yield_json_ld(webpage, video_id, fatal=False))

        return {
            'id': video_id,
            'title': traverse_obj(title_result, ('title', {str.strip})) or None,
            # This metadata could be interpreted otherwise, but it fits "series" the most
            'series': traverse_obj(title_result, ('series', {str.strip})) or None,
            'description': join_nonempty(*traverse_obj(webpage, [(
                {find_element(cls='opening-intro')},
                [{find_element(tag='bpb-accordion-item')}, {find_element(cls='text-content')}],
            ), {clean_html}]), delim='\n\n') or None,
            'creators': traverse_obj(self._html_search_meta('author', webpage), all),
            'uploader': self._html_search_meta('publisher', webpage),
            'release_date': unified_strdate(self._html_search_meta('date', webpage)),
            'tags': traverse_obj(json_lds, (..., 'keywords', {lambda x: x.split(',')}, ...)),
            **traverse_obj(self._parse_vue_attributes('bpb-player', webpage, video_id), {
                'formats': (':sources', ..., {self._process_source}),
                'thumbnail': ('poster', {urljoin(url)}),
            }),
        }

from .common import InfoExtractor
from ..utils import ExtractorError


class VimpIE(InfoExtractor):
    _INSTANCES_RE = r'''(?:
        campus\.demo\.vimp\.com|
        corporate\.demo\.vimp\.com|
        dancehalldatabase\.com|
        educhannel\.hs-gesundheit\.de|
        globale-evolution\.net|
        media\.cmslegal\.com|
        media\.hs-furtwangen\.de|
        media\.hwr-berlin\.de|
        mediathek\.dkfz\.de|
        mediathek\.htw-berlin\.de|
        mediathek\.polizei-bw\.de|
        medien\.hs-merseburg\.de|
        mportal\.europa-uni\.de|
        pacific\.demo\.vimp\.com|
        slctv\.com|
        tube\.isbonline\.cn|
        univideo\.uni-kassel\.de|
        v\.agrarumweltpaedagogik\.at|
        video\.eplay-tv\.de|
        video\.fh-dortmund\.de|
        video\.hs-offenburg\.de|
        video\.hs-pforzheim\.de|
        video\.hspv\.nrw\.de|
        video\.irtshdf\.fr|
        video\.pareygo\.de|
        video\.tu-freiberg\.de|
        videocampus\.sachsen\.de|
        videoportal\.uni-freiburg\.de|
        videos\.duoc\.cl|
        videos\.uni-paderborn\.de|
        vimp-bemus\.udk-berlin\.de|
        vimp\.aekwl\.de|
        vimp\.oth-regensburg\.de|
        vimp\.ph-heidelberg\.de|
        vimp\.sma-events\.com|
        webtv\.univ-montp3\.fr|
        www2\.univ-sba\.dz|
        www\.bigcitytv\.de|
        www\.fh-bielefeld\.de/medienportal|
        www\.orvovideo\.com|
        www\.rwe\.tv|
        www\.wenglor-media\.com
    )'''
    _VALID_URL = r'''(?x)https?://(?P<host>%s)/(?:
        m/(?P<tmp_id>[0-9a-f]+)|
        (?:category/)?video/(?P<display_id>[\w-]+)/(?P<id>[0-9a-f]{32})|
        media/embed\?key=(?P<embed_id>[0-9a-f]{32})
    )''' % (_INSTANCES_RE)

    _TESTS = [
        {
            'url': 'https://videocampus.sachsen.de/m/e0d6c8ce6e394c188f1342f1ab7c50ed6fc4490b808699801def5cb2e46d76ca7367f622a9f516c542ffb805b24d6b643bd7c81f385acaac4c59081b87a2767b',
            'info_dict': {
                'id': 'e6b9349905c1628631f175712250f2a1',
                'title': 'Konstruktiver Entwicklungsprozess Vorlesung 7',
                'description': 'Konstruktiver Entwicklungsprozess Vorlesung 7',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/video/Was-ist-selbstgesteuertes-Lernen/fc99c527e4205b121cb7c74433469262',
            'info_dict': {
                'id': 'fc99c527e4205b121cb7c74433469262',
                'title': 'Was ist selbstgesteuertes Lernen?',
                'description': 'Ein Erkl&auml;rvideo zur Definition des selbstgesteuerten Lernens. Kursleiterin Jana m&ouml;chte in ihrem Kurs einen gr&ouml;&szlig;eren Anteil selbstgesteuerter Elemente realisieren. Experte Jonas ber&auml;t sie bei der Kursplanung. Das Video ist im Projekt &quot;Weiterbildung selbstorganisiert&quot; der Professur Bildungstechnologie an der TU Dresden entstanden. Es verweist auf folgende Webseite: https://methodenkoffer-sgl.de/',
                'display_id': 'Was-ist-selbstgesteuertes-Lernen',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/category/video/Tutorial-zur-Nutzung-von-Adobe-Connect-aus-Veranstalter-Sicht/09d4ed029002eb1bdda610f1103dd54c/100',
            'info_dict': {
                'id': '09d4ed029002eb1bdda610f1103dd54c',
                'title': 'Tutorial zur Nutzung von Adobe Connect aus Veranstalter-Sicht',
                'description': '&lt;p&gt; Lernen Sie die wichtigsten Funktionen von Adobe Connect kennen, mit denen Sie selbst eine Online-Veranstaltung als Veranstalter durchf&uuml;hren k&ouml;nnen.&lt;/p&gt;',
                'display_id': 'Tutorial-zur-Nutzung-von-Adobe-Connect-aus-Veranstalter-Sicht',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www2.univ-sba.dz/video/Presentation-de-la-Faculte-de-droit-et-des-sciences-politiques-Journee-portes-ouvertes-202122/0183356e41af7bfb83d7667b20d9b6a3',
            'info_dict': {
                'url': 'https://www2.univ-sba.dz/getMedium/0183356e41af7bfb83d7667b20d9b6a3.mp4',
                'id': '0183356e41af7bfb83d7667b20d9b6a3',
                'title': 'Présentation de la Faculté de droit et des sciences politiques - Journée portes ouvertes 2021/22',
                'description': 'Pr&eacute;sentation de la Facult&eacute; de droit et des sciences politiques - Journ&eacute;e portes ouvertes 2021/22',
                'display_id': 'Presentation-de-la-Faculte-de-droit-et-des-sciences-politiques-Journee-portes-ouvertes-202122',
                'ext': 'mp4',
            }
        },
        {
            'url': 'https://videocampus.sachsen.de/media/embed?key=fc99c527e4205b121cb7c74433469262',
            'info_dict': {
                'id': 'fc99c527e4205b121cb7c74433469262',
                'title': 'Was ist selbstgesteuertes Lernen?',
                'ext': 'mp4',
            },
        }
    ]

    def _real_extract(self, url):
        host, video_id, tmp_id, display_id, embed_id = self._match_valid_url(url).group('host', 'id', 'tmp_id', 'display_id', 'embed_id')
        webpage = self._download_webpage(url, video_id or tmp_id, fatal=False) or ''

        if not video_id:
            video_id = embed_id or self._html_search_regex(
                rf'src="https?://{host}/media/embed\?key=([0-9a-f]+)&',
                webpage, 'video_id')

        # Title, description from page meta wouldn't be correct if the video is embedded
        # so separating normal and embedded extraction
        if not (display_id or tmp_id):
            title = self._html_search_regex(r'<img[^>]*title="([^"<]+)"', webpage, 'title', fatal=False)
            description = None
        else:
            title = self._html_search_meta(('og:title', 'twitter:title', 'title'), webpage, default=None)
            description = self._html_search_meta(('og:description', 'twitter:description', 'description'), webpage, default=None)

        # Try extraction of HLS first since it usually has multiple formats plus possibly subtitles
        formats = subtitles = None
        try:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://{host}/media/hlsMedium/key/{video_id}/format/auto/ext/mp4/learning/0/path/m3u8',
                video_id, 'mp4', 'm3u8_native', m3u8_id='hls')
            self._sort_formats(formats)
        except ExtractorError:
            pass

        # Formats may be empty
        if formats:
            return {
                'id': video_id,
                'title': title,
                'description': description,
                'display_id': display_id,
                'formats': formats,
                'subtitles': subtitles
            }
        else:
            return {
                'url': f'https://{host}/getMedium/{video_id}.mp4',
                'id': video_id,
                'title': title,
                'description': description,
                'display_id': display_id
            }

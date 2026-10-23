import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class MediaKlikkIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?
                        (?:mediaklikk|m4sport|hirado)\.hu/.*?(?:videok?|cikk)/
                        (?:(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/)?
                        (?P<id>[^/#?_]+)'''

    _TESTS = [{
        # mediaklikk
        'url': 'https://mediaklikk.hu/ajanlo/video/2025/08/04/heviz-dzsungel-a-viz-alatt-ajanlo-08-10/',
        'info_dict': {
            'id': '8573769',
            'title': 'Hévíz - dzsungel a víz alatt – Ajánló (08.10.)',
            'display_id': 'heviz-dzsungel-a-viz-alatt-ajanlo-08-10',
            'ext': 'mp4',
            'upload_date': '20250804',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2025/08/vlcsnap-2025-08-04-13h48m24s336.jpg',
        },
    }, {
        # mediaklikk - date in html
        'url': 'https://mediaklikk.hu/video/hazajaro-bilo-hegyseg-verocei-barangolas-a-drava-menten/',
        'info_dict': {
            'id': '8482167',
            'title': 'Hazajáró, Bilo-hegység - Verőcei barangolás a Dráva mentén',
            'display_id': 'hazajaro-bilo-hegyseg-verocei-barangolas-a-drava-menten',
            'ext': 'mp4',
            'upload_date': '20250703',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2025/07/2024-000307-M0010-01_3700_cover_01.jpg',
        },
    }, {
        # m4sport
        'url': 'https://m4sport.hu/video/2025/08/07/holnap-kezdodik-a-12-vilagjatekok/',
        'info_dict': {
            'id': '8581887',
            'title': 'Holnap kezdődik a 12. Világjátékok',
            'display_id': 'holnap-kezdodik-a-12-vilagjatekok',
            'ext': 'mp4',
            'upload_date': '20250807',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2025/08/vlcsnap-2025-08-06-20h30m48s817.jpg',
        },
    }, {
        # hirado
        'url': 'https://hirado.hu/video/2025/08/09/idojaras-jelentes-2025-augusztus-9-2230',
        'info_dict': {
            'id': '8592033',
            'title': 'Időjárás-jelentés, 2025. augusztus 9. 22:30',
            'display_id': 'idojaras-jelentes-2025-augusztus-9-2230',
            'ext': 'mp4',
            'upload_date': '20250809',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2025/08/Idojaras-jelentes-35-1.jpg',
        },
    }, {
        # hirado - subcategory
        'url': 'https://hirado.hu/belfold/video/2025/08/09/nyitott-porta-napok-2025/',
        'info_dict': {
            'id': '8590581',
            'title': 'Nyitott Porta Napok 2025',
            'display_id': 'nyitott-porta-napok-2025',
            'ext': 'mp4',
            'upload_date': '20250809',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2025/08/vlcsnap-2025-08-09-10h35m01s887.jpg',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        webpage = self._download_webpage(url, display_id)

        player_data = self._search_json(
            r'loadPlayer\((?:\s*["\'][^"\']+["\']\s*,)?', webpage, 'player data', mobj)
        video_id = str(player_data['contentId'])
        title = player_data.get('title') or self._og_search_title(webpage, fatal=False) or \
            self._html_search_regex(r'<h\d+\b[^>]+\bclass="article_title">([^<]+)<', webpage, 'title')

        upload_date = unified_strdate(
            '{}-{}-{}'.format(mobj.group('year'), mobj.group('month'), mobj.group('day')))
        if not upload_date:
            upload_date = unified_strdate(self._html_search_regex(
                r'<p+\b[^>]+\bclass="article_date">([^<]+)<', webpage, 'upload date', default=None))

        player_data['video'] = urllib.parse.unquote(player_data.pop('token'))
        player_page = self._download_webpage(
            'https://player.mediaklikk.hu/playernew/player.php', video_id,
            query=player_data, headers={'Referer': url})
        player_json = self._search_json(
            r'\bpl\.setup\s*\(', player_page, 'player json', video_id, end_pattern=r'\);')
        playlist_url = traverse_obj(
            player_json, ('playlist', lambda _, v: v['type'] == 'hls', 'file', {url_or_none}), get_all=False)
        if not playlist_url:
            raise ExtractorError('Unable to extract playlist url')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(playlist_url, video_id)

        return {
            'id': video_id,
            'title': title,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'upload_date': upload_date,
            'thumbnail': player_data.get('bgImage') or self._og_search_thumbnail(webpage),
        }

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
                        (?:mediaklikk|m4sport|hirado|petofilive)\.hu/.*?(?:videok?|cikk)/
                        (?:(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/)?
                        (?P<id>[^/#?_]+)'''

    _TESTS = [{
        'url': 'https://mediaklikk.hu/filmajanlo/cikk/az-ajto/',
        'info_dict': {
            'id': '668177',
            'title': 'Az ajtó',
            'display_id': 'az-ajto',
            'ext': 'mp4',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2016/01/vlcsnap-2023-07-31-14h18m52s111.jpg',
        },
    }, {
        # (old) mediaklikk. date in html.
        'url': 'https://mediaklikk.hu/video/hazajaro-delnyugat-bacska-a-duna-menten-palankatol-doroszloig/',
        'info_dict': {
            'id': '4754129',
            'title': 'Hazajáró, DÉLNYUGAT-BÁCSKA – A Duna mentén Palánkától Doroszlóig',
            'ext': 'mp4',
            'upload_date': '20210901',
            'thumbnail': 'http://mediaklikk.hu/wp-content/uploads/sites/4/2014/02/hazajarouj_JO.jpg',
        },
        'skip': 'Webpage redirects to 404 page',
    }, {
        # mediaklikk. date in html.
        'url': 'https://mediaklikk.hu/video/hazajaro-fabova-hegyseg-kishont-koronaja/',
        'info_dict': {
            'id': '6696133',
            'title': 'Hazajáró, Fabova-hegység - Kishont koronája',
            'display_id': 'hazajaro-fabova-hegyseg-kishont-koronaja',
            'ext': 'mp4',
            'upload_date': '20230903',
            'thumbnail': 'https://mediaklikk.hu/wp-content/uploads/sites/4/2014/02/hazajarouj_JO.jpg',
        },
        'skip': 'Webpage redirects to 404 page',
    }, {
        # (old) m4sport
        'url': 'https://m4sport.hu/video/2021/08/30/gyemant-liga-parizs/',
        'info_dict': {
            'id': '4754999',
            'title': 'Gyémánt Liga, Párizs',
            'ext': 'mp4',
            'upload_date': '20210830',
            'thumbnail': 'http://m4sport.hu/wp-content/uploads/sites/4/2021/08/vlcsnap-2021-08-30-18h21m20s10-1024x576.jpg',
        },
        'skip': 'Webpage redirects to 404 page',
    }, {
        # m4sport
        'url': 'https://m4sport.hu/sportkozvetitesek/video/2023/09/08/atletika-gyemant-liga-brusszel/',
        'info_dict': {
            'id': '6711136',
            'title': 'Atlétika – Gyémánt Liga, Brüsszel',
            'display_id': 'atletika-gyemant-liga-brusszel',
            'ext': 'mp4',
            'upload_date': '20230908',
            'thumbnail': 'https://m4sport.hu/wp-content/uploads/sites/4/2023/09/vlcsnap-2023-09-08-22h43m18s691.jpg',
        },
        'skip': 'Webpage redirects to 404 page',
    }, {
        # m4sport with *video/ url and no date
        'url': 'https://m4sport.hu/bl-video/real-madrid-chelsea-1-1/',
        'info_dict': {
            'id': '4492099',
            'title': 'Real Madrid - Chelsea 1-1',
            'display_id': 'real-madrid-chelsea-1-1',
            'ext': 'mp4',
            'thumbnail': 'https://m4sport.hu/wp-content/uploads/sites/4/2021/04/Sequence-01.Still001-1024x576.png',
        },
        'skip': 'Webpage redirects to 404 page',
    }, {
        # (old) hirado
        'url': 'https://hirado.hu/videok/felteteleket-szabott-a-fovaros/',
        'info_dict': {
            'id': '4760120',
            'title': 'Feltételeket szabott a főváros',
            'ext': 'mp4',
            'thumbnail': 'http://hirado.hu/wp-content/uploads/sites/4/2021/09/vlcsnap-2021-09-01-20h20m37s165.jpg',
        },
        'skip': 'Webpage redirects to video list page',
    }, {
        # hirado
        'url': 'https://hirado.hu/belfold/video/2023/09/11/marad-az-eves-elszamolas-a-napelemekre-beruhazo-csaladoknal',
        'info_dict': {
            'id': '6716068',
            'title': 'Marad az éves elszámolás a napelemekre beruházó családoknál',
            'display_id': 'marad-az-eves-elszamolas-a-napelemekre-beruhazo-csaladoknal',
            'ext': 'mp4',
            'upload_date': '20230911',
            'thumbnail': 'https://hirado.hu/wp-content/uploads/sites/4/2023/09/vlcsnap-2023-09-11-09h16m09s882.jpg',
        },
        'skip': 'Webpage redirects to video list page',
    }, {
        # (old) petofilive
        'url': 'https://petofilive.hu/video/2021/06/07/tha-shudras-az-akusztikban/',
        'info_dict': {
            'id': '4571948',
            'title': 'Tha Shudras az Akusztikban',
            'ext': 'mp4',
            'upload_date': '20210607',
            'thumbnail': 'http://petofilive.hu/wp-content/uploads/sites/4/2021/06/vlcsnap-2021-06-07-22h14m23s915-1024x576.jpg',
        },
        'skip': 'Webpage redirects to empty page',
    }, {
        # petofilive
        'url': 'https://petofilive.hu/video/2023/09/09/futball-fesztival-a-margitszigeten/',
        'info_dict': {
            'id': '6713233',
            'title': 'Futball Fesztivál a Margitszigeten',
            'display_id': 'futball-fesztival-a-margitszigeten',
            'ext': 'mp4',
            'upload_date': '20230909',
            'thumbnail': 'https://petofilive.hu/wp-content/uploads/sites/4/2023/09/Clipboard11-2.jpg',
        },
        'skip': 'Webpage redirects to video list page',
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        webpage = self._download_webpage(url, display_id)

        player_data_str = self._html_search_regex(
            r'mtva_player_manager\.player\(document.getElementById\(.*\),\s?(\{.*\}).*\);', webpage, 'player data')
        player_data = self._parse_json(player_data_str, display_id, urllib.parse.unquote)
        video_id = str(player_data['contentId'])
        title = player_data.get('title') or self._og_search_title(webpage, fatal=False) or \
            self._html_search_regex(r'<h\d+\b[^>]+\bclass="article_title">([^<]+)<', webpage, 'title')

        upload_date = unified_strdate(
            '{}-{}-{}'.format(mobj.group('year'), mobj.group('month'), mobj.group('day')))
        if not upload_date:
            upload_date = unified_strdate(self._html_search_regex(
                r'<p+\b[^>]+\bclass="article_date">([^<]+)<', webpage, 'upload date', default=None))

        player_data['video'] = player_data.pop('token')
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

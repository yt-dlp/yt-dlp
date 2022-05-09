from ..utils import (
    unified_strdate
)
from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_unquote,
    compat_str
)


class MediaKlikkIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?
                        (?:mediaklikk|m4sport|hirado|petofilive)\.hu/.*?(?:videok?|cikk)/
                        (?:(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/)?
                        (?P<id>[^/#?_]+)'''

    _TESTS = [{
        # mediaklikk. date in html.
        'url': 'https://mediaklikk.hu/video/hazajaro-delnyugat-bacska-a-duna-menten-palankatol-doroszloig/',
        'info_dict': {
            'id': '4754129',
            'title': 'Hazajáró, DÉLNYUGAT-BÁCSKA – A Duna mentén Palánkától Doroszlóig',
            'ext': 'mp4',
            'upload_date': '20210901',
            'thumbnail': 'http://mediaklikk.hu/wp-content/uploads/sites/4/2014/02/hazajarouj_JO.jpg'
        }
    }, {
        # m4sport
        'url': 'https://m4sport.hu/video/2021/08/30/gyemant-liga-parizs/',
        'info_dict': {
            'id': '4754999',
            'title': 'Gyémánt Liga, Párizs',
            'ext': 'mp4',
            'upload_date': '20210830',
            'thumbnail': 'http://m4sport.hu/wp-content/uploads/sites/4/2021/08/vlcsnap-2021-08-30-18h21m20s10-1024x576.jpg'
        }
    }, {
        # m4sport with *video/ url and no date
        'url': 'https://m4sport.hu/bl-video/real-madrid-chelsea-1-1/',
        'info_dict': {
            'id': '4492099',
            'title': 'Real Madrid - Chelsea 1-1',
            'ext': 'mp4',
            'thumbnail': 'http://m4sport.hu/wp-content/uploads/sites/4/2021/04/Sequence-01.Still001-1024x576.png'
        }
    }, {
        # hirado
        'url': 'https://hirado.hu/videok/felteteleket-szabott-a-fovaros/',
        'info_dict': {
            'id': '4760120',
            'title': 'Feltételeket szabott a főváros',
            'ext': 'mp4',
            'thumbnail': 'http://hirado.hu/wp-content/uploads/sites/4/2021/09/vlcsnap-2021-09-01-20h20m37s165.jpg'
        }
    }, {
        # petofilive
        'url': 'https://petofilive.hu/video/2021/06/07/tha-shudras-az-akusztikban/',
        'info_dict': {
            'id': '4571948',
            'title': 'Tha Shudras az Akusztikban',
            'ext': 'mp4',
            'upload_date': '20210607',
            'thumbnail': 'http://petofilive.hu/wp-content/uploads/sites/4/2021/06/vlcsnap-2021-06-07-22h14m23s915-1024x576.jpg'
        }
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        webpage = self._download_webpage(url, display_id)

        player_data_str = self._html_search_regex(
            r'mtva_player_manager\.player\(document.getElementById\(.*\),\s?(\{.*\}).*\);', webpage, 'player data')
        player_data = self._parse_json(player_data_str, display_id, compat_urllib_parse_unquote)
        video_id = compat_str(player_data['contentId'])
        title = player_data.get('title') or self._og_search_title(webpage, fatal=False) or \
            self._html_search_regex(r'<h\d+\b[^>]+\bclass="article_title">([^<]+)<', webpage, 'title')

        upload_date = unified_strdate(
            '%s-%s-%s' % (mobj.group('year'), mobj.group('month'), mobj.group('day')))
        if not upload_date:
            upload_date = unified_strdate(self._html_search_regex(
                r'<p+\b[^>]+\bclass="article_date">([^<]+)<', webpage, 'upload date', default=None))

        player_data['video'] = player_data.pop('token')
        player_page = self._download_webpage('https://player.mediaklikk.hu/playernew/player.php', video_id, query=player_data)
        playlist_url = self._proto_relative_url(compat_urllib_parse_unquote(
            self._html_search_regex(r'\"file\":\s*\"(\\?/\\?/.*playlist\.m3u8)\"', player_page, 'playlist_url')).replace('\\/', '/'))

        formats = self._extract_wowza_formats(
            playlist_url, video_id, skip_protocols=['f4m', 'smil', 'dash'])
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'display_id': display_id,
            'formats': formats,
            'upload_date': upload_date,
            'thumbnail': player_data.get('bgImage') or self._og_search_thumbnail(webpage)
        }

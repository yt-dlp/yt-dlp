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
                        (?:[^/]+/)*(?P<id>[^/#?]+)'''

    _TESTS = [{
        # mediaklikk - link has SRT subtitle track available
        'url': 'https://mediaklikk.hu/sorozat-0/video/2026/01/28/sorozat/koronas-sas-3-evad-396-resz',
        'info_dict': {
            'id': '9308421',
            'title': 'Koronás sas 3. évad, 396. rész',
            'display_id': 'koronas-sas-3-evad-396-resz',
            'ext': 'mp4',
            'upload_date': '20260128',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2026/01/2021-010143-M0151-02_3700_cover_09.jpg',
            'episode_id': '2021-010143-M0151',
        },
    }, {
        # mediaklikk
        'url': 'https://mediaklikk.hu/ismeretterjeszto/video/2026/01/18/ismeretterjeszto/hazajaro-juliai-alpok-szeles-az-isonzo-vize/',
        'info_dict': {
            'id': '9275589',
            'title': 'Hazajáró, JÚLIAI-ALPOK – Széles az Isonzó vize',
            'display_id': 'hazajaro-juliai-alpok-szeles-az-isonzo-vize',
            'ext': 'mp4',
            'upload_date': '20260118',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2026/01/2026-000492-M0002-01_3700_cover_01.jpg',
            'episode_id': '2026-000492-M0002',
        },
    }, {
        # m4sport
        'url': 'https://m4sport.hu/video/2026/01/28/szalai-gabor-nehez-meccs-lesz-de-keszen-allunk-2',
        'info_dict': {
            'id': '9316011',
            'title': 'Szalai Gábor: Nehéz meccs lesz, de készen állunk',
            'display_id': 'szalai-gabor-nehez-meccs-lesz-de-keszen-allunk-2',
            'ext': 'mp4',
            'upload_date': '20260128',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2026/01/vlcsnap-2026-01-28-13h34m15s032.jpg',
        },
    }, {
        # hirado
        'url': 'https://hirado.hu/video/2021/02/15/a-magyar-faust-mikrofilm/',
        'info_dict': {
            'id': '4352602',
            'title': 'A magyar Faust - Mikrofilm',
            'display_id': 'a-magyar-faust-mikrofilm',
            'ext': 'mp4',
            'upload_date': '20210215',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2021/02/vlcsnap-2021-02-15-18h02m40s081-1024x581.jpg',
        },
    }, {
        # hirado - subcategory
        'url': 'https://hirado.hu/belfold/video/2026/01/27/fidesz-kdnp-botranyos-bulihajok-a-fovarosban-a-hatterben-kartell-gyanus-cegekkel-2',
        'info_dict': {
            'id': '9312042',
            'title': 'Fidesz-KDNP: Botrányos bulihajók a fővárosban, a háttérben kartell gyanús cégekkel',
            'display_id': 'fidesz-kdnp-botranyos-bulihajok-a-fovarosban-a-hatterben-kartell-gyanus-cegekkel-2',
            'ext': 'mp4',
            'upload_date': '20260127',
            'thumbnail': 'https://cdn.cms.mtv.hu/wp-content/uploads/sites/4/2026/01/vlcsnap-2026-01-27-13h47m04s569.jpg',
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
        playlist_item = traverse_obj(
            player_json, ('playlist', lambda _, v: v['type'] == 'hls'), get_all=False)
        playlist_url = traverse_obj(playlist_item, ('file', {url_or_none}))
        if not playlist_url:
            raise ExtractorError('Unable to extract playlist url')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(playlist_url, video_id)
        for track in traverse_obj(playlist_item, ('tracks', lambda _, v: v.get('kind') == 'captions')) or []:
            sub_url = traverse_obj(track, ('file', {url_or_none}))
            if sub_url:
                subtitles.setdefault('hu', []).append({
                    'url': sub_url,
                    'ext': 'srt',
                })

        return {
            'id': video_id,
            'title': title,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'upload_date': upload_date,
            'thumbnail': player_data.get('bgImage') or self._og_search_thumbnail(webpage),
        }

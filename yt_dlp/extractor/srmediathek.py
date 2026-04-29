from .ard import ARDMediathekBaseIE
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    parse_duration,
    parse_qs,
    unified_strdate,
)
from ..utils.traversal import (
    find_element,
    require,
    traverse_obj,
)


class SRMediathekIE(ARDMediathekBaseIE):
    IE_NAME = 'sr:mediathek'
    IE_DESC = 'Saarländischer Rundfunk'

    _CLS_COMMON = 'teaser__image__caption__text teaser__image__caption__text--'
    _VALID_URL = r'https?://(?:www\.)?sr-mediathek\.de/index\.php\?.*?&id=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.sr-mediathek.de/index.php?seite=7&id=141317',
        'info_dict': {
            'id': '141317',
            'ext': 'mp4',
            'title': 'Kärnten, da will ich hin!',
            'channel': 'SR Fernsehen',
            'description': 'md5:7732e71e803379a499732864a572a456',
            'duration': 1788.0,
            'release_date': '20250525',
            'series': 'da will ich hin!',
            'series_id': 'DWIH',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.sr-mediathek.de/index.php?seite=7&id=153853',
        'info_dict': {
            'id': '153853',
            'ext': 'mp3',
            'title': 'Kappes, Klöße, Kokosmilch: Bruschetta mit Nduja',
            'channel': 'SR 3',
            'description': 'md5:3935798de3562b10c4070b408a15e225',
            'duration': 139.0,
            'release_date': '20250523',
            'series': 'Kappes, Klöße, Kokosmilch',
            'series_id': 'SR3_KKK_A',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.sr-mediathek.de/index.php?seite=7&id=31406&pnr=&tbl=pf',
        'info_dict': {
            'id': '31406',
            'ext': 'mp3',
            'title': 'Das Leben schwer nehmen, ist einfach zu anstrengend',
            'channel': 'SR 1',
            'description': 'md5:3e03fd556af831ad984d0add7175fb0c',
            'duration': 1769.0,
            'release_date': '20230717',
            'series': 'Abendrot',
            'series_id': 'SR1_AB_P',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        description = self._og_search_description(webpage)

        if description == 'Der gewünschte Beitrag ist leider nicht mehr vorhanden.':
            raise ExtractorError(f'Video {video_id} is no longer available', expected=True)

        player_url = traverse_obj(webpage, (
            {find_element(tag='div', id=f'player{video_id}', html=True)},
            {extract_attributes}, 'data-mediacollection-ardplayer',
            {self._proto_relative_url}, {require('player URL')}))
        article = traverse_obj(webpage, (
            {find_element(cls='article__content')},
            {find_element(tag='p')}, {clean_html}))

        return {
            **self._extract_media_info(player_url, webpage, video_id),
            'id': video_id,
            'title': traverse_obj(webpage, (
                {find_element(cls='ardplayer-title')}, {clean_html})),
            'channel': traverse_obj(webpage, (
                {find_element(cls=f'{self._CLS_COMMON}subheadline')},
                {lambda x: x.split('|')[0]}, {clean_html})),
            'description': description,
            'duration': parse_duration(self._search_regex(
                r'(\d{2}:\d{2}:\d{2})', article, 'duration')),
            'release_date': unified_strdate(self._search_regex(
                r'(\d{2}\.\d{2}\.\d{4})', article, 'release_date')),
            'series': traverse_obj(webpage, (
                {find_element(cls=f'{self._CLS_COMMON}headline')}, {clean_html})),
            'series_id': traverse_obj(webpage, (
                {find_element(cls='teaser__link', html=True)},
                {extract_attributes}, 'href', {parse_qs}, 'sen', ..., {str}, any)),
            'thumbnail': self._og_search_thumbnail(webpage),
        }

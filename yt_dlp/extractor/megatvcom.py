import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    parse_qs,
    unescapeHTML,
    unified_timestamp,
)


class MegaTVComBaseIE(InfoExtractor):
    _PLAYER_DIV_ID = 'player_div_id'

    def _extract_player_attrs(self, webpage):
        player_el = get_element_html_by_id(self._PLAYER_DIV_ID, webpage)
        return {
            re.sub(r'^data-(?:kwik_)?', '', k): v
            for k, v in extract_attributes(player_el).items()
            if k not in ('id',)
        }


class MegaTVComIE(MegaTVComBaseIE):
    IE_NAME = 'megatvcom'
    IE_DESC = 'megatv.com videos'
    _VALID_URL = r'https?://(?:www\.)?megatv\.com/(?:\d{4}/\d{2}/\d{2}|[^/]+/(?P<id>\d+))/(?P<slug>[^/]+)'
    _TESTS = [{
        # FIXME: Unable to extract article id
        'url': 'https://www.megatv.com/2021/10/23/egkainia-gia-ti-nea-skini-omega-tou-dimotikou-theatrou-peiraia/',
        'info_dict': {
            'id': '520979',
            'ext': 'mp4',
            'title': 'md5:70eef71a9cd2c1ecff7ee428354dded2',
            'description': 'md5:0209fa8d318128569c0d256a5c404db1',
            'timestamp': 1634975747,
            'upload_date': '20211023',
            'display_id': 'egkainia-gia-ti-nea-skini-omega-tou-dimotikou-theatrou-peiraia',
            'thumbnail': r're:https?://www\.megatv\.com/wp-content/uploads/.+\.jpg',
        },
    }, {
        'url': 'https://www.megatv.com/tvshows/527800/epeisodio-65-12/',
        'info_dict': {
            'id': '527800',
            'ext': 'mp4',
            'title': 'Η Γη της Ελιάς: Επεισόδιο 65 - A\' ΚΥΚΛΟΣ ',
            'description': 'md5:b2b7ed3690a78f2a0156eb790fdc00df',
            'timestamp': 1636048859,
            'upload_date': '20211104',
            'display_id': 'epeisodio-65-12',
            'thumbnail': r're:https?://www\.megatv\.com/wp-content/uploads/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'slug')
        _is_article = video_id is None
        webpage = self._download_webpage(url, video_id or display_id)
        if _is_article:
            video_id = self._search_regex(
                r'<article[^>]*\sid=["\']Article_(\d+)["\']', webpage, 'article id')
        player_attrs = self._extract_player_attrs(webpage)
        title = player_attrs.get('label') or self._og_search_title(webpage)
        description = get_element_by_class(
            'article-wrapper' if _is_article else 'story_content',
            webpage)
        description = clean_html(re.sub(r'<script[^>]*>[^<]+</script>', '', description))
        if not description:
            description = self._og_search_description(webpage)
        thumbnail = player_attrs.get('image') or self._og_search_thumbnail(webpage)
        timestamp = unified_timestamp(self._html_search_meta(
            'article:published_time', webpage))
        source = player_attrs.get('source')
        if not source:
            raise ExtractorError('No source found', video_id=video_id)
        if determine_ext(source) == 'm3u8':
            formats, subs = self._extract_m3u8_formats_and_subtitles(source, video_id, 'mp4')
        else:
            formats, subs = [{'url': source}], {}
        if player_attrs.get('subs'):
            self._merge_subtitles({'und': [{'url': player_attrs['subs']}]}, target=subs)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'formats': formats,
            'subtitles': subs,
        }


class MegaTVComEmbedIE(MegaTVComBaseIE):
    IE_NAME = 'megatvcom:embed'
    IE_DESC = 'megatv.com embedded videos'
    _VALID_URL = r'(?:https?:)?//(?:www\.)?megatv\.com/embed/?\?p=(?P<id>\d+)'
    _EMBED_REGEX = [rf'''<iframe[^>]+?src=(?P<_q1>["'])(?P<url>{_VALID_URL})(?P=_q1)''']
    _TESTS = [{
        # FIXME: Unable to extract article id
        'url': 'https://www.megatv.com/embed/?p=2020520979',
        'md5': '6546a1a37fff0dd51c9dce5f490b7d7d',
        'info_dict': {
            'id': '520979',
            'ext': 'mp4',
            'title': 'md5:70eef71a9cd2c1ecff7ee428354dded2',
            'description': 'md5:0209fa8d318128569c0d256a5c404db1',
            'timestamp': 1634975747,
            'upload_date': '20211023',
            'display_id': 'egkainia-gia-ti-nea-skini-omega-tou-dimotikou-theatrou-peiraia',
            'thumbnail': 'https://www.megatv.com/wp-content/uploads/2021/10/ΠΕΙΡΑΙΑΣ-1024x450.jpg',
        },
    }, {
        # FIXME: Unable to extract article id
        'url': 'https://www.megatv.com/embed/?p=2020534081',
        'md5': '6ac8b3ce4dc6120c802f780a1e6b3812',
        'info_dict': {
            'id': '534081',
            'ext': 'mp4',
            'title': 'md5:062e9d5976ef854d8bdc1f5724d9b2d0',
            'description': 'md5:36dbe4c3762d2ede9513eea8d07f6d52',
            'timestamp': 1636376351,
            'upload_date': '20211108',
            'display_id': 'neo-rekor-stin-timi-tou-ilektrikou-reymatos-pano-apo-ta-200e-i-xondriki-timi-tou-ilektrikou',
            'thumbnail': 'https://www.megatv.com/wp-content/uploads/2021/11/Capture-266.jpg',
        },
    }]
    _WEBPAGE_TESTS = [{
        # FIXME: Unable to extract article id
        'url': 'https://www.in.gr/2021/12/18/greece/apokalypsi-mega-poios-parelave-tin-ereyna-tsiodra-ek-merous-tis-kyvernisis-o-prothypourgos-telika-gnorize/',
        'info_dict': {
            'id': 'apokalypsi-mega-poios-parelave-tin-ereyna-tsiodra-ek-merous-tis-kyvernisis-o-prothypourgos-telika-gnorize',
            'title': 'md5:5e569cf996ec111057c2764ec272848f',
        },
        'playlist_count': 2,
    }]

    def _match_canonical_url(self, webpage):
        LINK_RE = r'''(?x)
        <link(?:
            rel=(?P<_q1>["'])(?P<canonical>canonical)(?P=_q1)|
            href=(?P<_q2>["'])(?P<href>(?:(?!(?P=_q2)).)+)(?P=_q2)|
            [^>]*?
        )+>
        '''
        for mobj in re.finditer(LINK_RE, webpage):
            canonical, href = mobj.group('canonical', 'href')
            if canonical and href:
                return unescapeHTML(href)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_attrs = self._extract_player_attrs(webpage)
        canonical_url = player_attrs.get('share_url') or self._match_canonical_url(webpage)
        if not canonical_url:
            raise ExtractorError('canonical URL not found')
        video_id = parse_qs(canonical_url)['p'][0]

        # Defer to megatvcom as the metadata extracted from the embeddable page some
        # times are slightly different, for the same video
        canonical_url = self._request_webpage(
            HEADRequest(canonical_url), video_id,
            note='Resolve canonical URL',
            errnote='Could not resolve canonical URL').url
        return self.url_result(canonical_url, MegaTVComIE.ie_key(), video_id)

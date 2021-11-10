# coding: utf-8
from __future__ import unicode_literals

import re
from urllib.parse import (
    parse_qs,
    urlparse,
)

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    extract_attributes,
    get_element_by_class,
    HEADRequest,
    unescapeHTML,
    unified_timestamp,
)


class MegaTVComBaseIE(InfoExtractor):
    _PLAYER_DIV_ID = 'player_div_id'

    def _extract_player_attrs(self, webpage):
        PLAYER_DIV_RE = r'''(?x)
        <div(?:
            id=(?P<_q1>["'])(?P<%(pdi)s>%(pdi)s)(?P=_q1)|
            [^>]*?
        )+>
        ''' % {'pdi': self._PLAYER_DIV_ID}
        for mobj in re.finditer(PLAYER_DIV_RE, webpage):
            if mobj.group(self._PLAYER_DIV_ID):
                player_el = mobj.group(0)
                break
        else:
            raise ExtractorError('no <div id="%s"> element found in webpage' %
                                 self._PLAYER_DIV_ID)
        return {
            re.sub(r'^data-(?:kwik_)?', '', k): v
            for k, v in extract_attributes(player_el).items()
            if k not in ('id',)
        }


class MegaTVComIE(MegaTVComBaseIE):
    IE_NAME = 'megatvcom'
    IE_DESC = 'megatv.com videos'
    _VALID_URL = r'https?://(?:www\.)?megatv\.com/(?:(?!\d{4})[^/]+/(?P<id>\d+)/[^/]+|\d{4}/\d{2}/\d{2}/.+)'

    _TESTS = [{
        'url': 'https://www.megatv.com/2021/10/23/egkainia-gia-ti-nea-skini-omega-tou-dimotikou-theatrou-peiraia/',
        'md5': '2ebe96661cb81854889053cebb661068',
        'info_dict': {
            'id': '520979',
            'ext': 'mp4',
            'title': 'md5:70eef71a9cd2c1ecff7ee428354dded2',
            'description': 'md5:0209fa8d318128569c0d256a5c404db1',
            'timestamp': 1634975747,
            'upload_date': '20211023',
        },
    }, {
        'url': 'https://www.megatv.com/tvshows/527800/epeisodio-65-12/',
        'md5': '8ab0c9d664cea11678670202b87bb2b1',
        'info_dict': {
            'id': '527800',
            'ext': 'mp4',
            'title': 'md5:fc322cb51f682eecfe2f54cd5ab3a157',
            'description': 'md5:b2b7ed3690a78f2a0156eb790fdc00df',
            'timestamp': 1636048859,
            'upload_date': '20211104',
        },
    }]

    def _match_article_id(self, webpage):
        ART_RE = r'''(?x)
        <article(?:
            id=(?P<_q2>["'])Article_(?P<article>\d+)(?P=_q2)|
            [^>]*?
        )+>
        '''
        return compat_str(self._search_regex(ART_RE, webpage, 'article_id',
                                             group='article'))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        _is_article = video_id == 'None'
        webpage = self._download_webpage(url,
                                         'N/A' if _is_article else
                                         video_id)
        if _is_article:
            video_id = self._match_article_id(webpage)
        player_attrs = self._extract_player_attrs(webpage)
        title = player_attrs.get('label') or self._og_search_title(webpage)
        description = clean_html(get_element_by_class(
            'article-wrapper' if _is_article else 'story_content',
            webpage))
        if not description:
            description = self._og_search_description(webpage)
        thumbnail = player_attrs.get('image') or \
            self._og_search_thumbnail(webpage)
        timestamp = unified_timestamp(self._html_search_meta(
            'article:published_time', webpage))
        try:
            source = player_attrs['source']
        except KeyError:
            raise ExtractorError('no source found for %s' % video_id)
        formats = self._extract_m3u8_formats(source, video_id, 'mp4') \
            if determine_ext(source) == 'm3u8' else [source]
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'formats': formats,
        }


class MegaTVComEmbedIE(MegaTVComBaseIE):
    IE_NAME = 'megatvcom:embed'
    IE_DESC = 'megatv.com embedded videos'
    _VALID_URL = r'https?://(?:www\.)?megatv\.com/embed/?\?p=\d+'

    _TESTS = [{
        'url': 'https://www.megatv.com/embed/?p=2020520979',
        'md5': '2ebe96661cb81854889053cebb661068',
        'info_dict': {
            'id': '520979',
            'ext': 'mp4',
            'title': 'md5:70eef71a9cd2c1ecff7ee428354dded2',
            'description': 'md5:0209fa8d318128569c0d256a5c404db1',
            'timestamp': 1634975747,
            'upload_date': '20211023',
        },
    }, {
        'url': 'https://www.megatv.com/embed/?p=2020534081',
        'md5': 'f9a15e315acbf01b128e8efa3f75aab3',
        'info_dict': {
            'id': '534081',
            'ext': 'mp4',
            'title': 'md5:062e9d5976ef854d8bdc1f5724d9b2d0',
            'description': 'md5:36dbe4c3762d2ede9513eea8d07f6d52',
            'timestamp': 1636376351,
            'upload_date': '20211108',
        },
    }]

    @classmethod
    def _extract_urls(cls, webpage, origin_url=None):
        # make the scheme in _VALID_URL optional
        _URL_RE = r'(?:https?:)?//' + cls._VALID_URL.split('://', 1)[1]
        EMBED_RE = r'''(?x)
            <iframe[^>]+?src=(?P<_q1>%(quot_re)s)
                (?P<url>%(url_re)s)(?P=_q1)
        ''' % {'quot_re': r'["\']', 'url_re': _URL_RE}
        for mobj in re.finditer(EMBED_RE, webpage):
            url = unescapeHTML(mobj.group('url'))
            if url.startswith('//'):
                scheme = urlparse(origin_url).scheme if origin_url else 'https'
                url = '%s:%s' % (scheme, url)
            yield url

    def _match_canonical_url(self, webpage):
        LINK_RE = r'''(?x)
        <link(?:
            rel=(?P<_q1>%(quot_re)s)(?P<canonical>canonical)(?P=_q1)|
            href=(?P<_q2>%(quot_re)s)(?P<href>(?:(?!(?P=_q2)).)+)(?P=_q2)|
            [^>]*?
        )+>
        ''' % {'quot_re': r'["\']'}
        for mobj in re.finditer(LINK_RE, webpage):
            canonical, href = mobj.group('canonical', 'href')
            if canonical and href:
                return unescapeHTML(href)

    def _real_extract(self, url):
        webpage = self._download_webpage(url, 'N/A')
        player_attrs = self._extract_player_attrs(webpage)
        canonical_url = player_attrs.get('share_url') or \
            self._match_canonical_url(webpage)
        if not canonical_url:
            raise ExtractorError('canonical URL not found')
        video_id = parse_qs(urlparse(canonical_url).query)['p'][0]

        # Resolve the canonical URL, following redirects, and defer to
        # megatvcom, as the metadata extracted from the embeddable page some
        # times are slightly different, for the same video
        canonical_url = self._request_webpage(
            HEADRequest(canonical_url), video_id,
            note='Resolve canonical URL',
            errnote='Could not resolve canonical URL').geturl()
        return self.url_result(
            canonical_url,
            MegaTVComIE.ie_key(),
            video_id
        )

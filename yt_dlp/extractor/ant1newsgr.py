# coding: utf-8
from __future__ import unicode_literals

import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    HEADRequest,
    ExtractorError,
    determine_ext,
    smuggle_url,
    unsmuggle_url,
    unescapeHTML,
)


class Ant1NewsGrBaseIE(InfoExtractor):
    @staticmethod
    def _smuggle_parent_info(url, **info_dict):
        return smuggle_url(url, {'parent_info': info_dict})

    @staticmethod
    def _unsmuggle_parent_info(url):
        unsmuggled_url, data = unsmuggle_url(url, default={'parent_info': {}})
        return unsmuggled_url, data['parent_info']

    def _download_api_data(self, netloc, cid, scheme='https'):
        url_parts = (scheme, netloc, self._API_PATH, None, None, None)
        url = urllib.parse.urlunparse(url_parts)
        query = {'cid': cid}
        return self._download_json(
            url, cid,
            'Downloading JSON',
            'Unable to download JSON',
            query=query)

    def _download_and_extract_api_data(self, video_id, *args, **kwargs):
        info = self._download_api_data(*args, **kwargs)
        try:
            source = info['url']
        except KeyError:
            raise ExtractorError('no source found for %s' % video_id)
        formats, subs = self._extract_m3u8_formats_and_subtitles(
            source, video_id, 'mp4') \
            if determine_ext(source) == 'm3u8' else ([source], {})
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': info['title'],
            'thumbnail': info['thumb'],
            'formats': formats,
            'subtitles': subs,
        }


class Ant1NewsGrWatchIE(Ant1NewsGrBaseIE):
    IE_NAME = 'ant1newsgr:watch'
    IE_DESC = 'ant1news.gr videos'
    _VALID_URL = r'https?://(?:www\.)?ant1news\.gr/watch/(?P<id>\d+)/'
    _API_PATH = '/templates/data/player'

    _TEST = {
        'url': 'https://www.ant1news.gr/watch/1506168/ant1-news-09112021-stis-18-45',
        'md5': '95925e6b32106754235f2417e0d2dfab',
        'info_dict': {
            'id': '1506168',
            'ext': 'mp4',
            'title': 'md5:0ad00fa66ecf8aa233d26ab0dba7514a',
            'description': 'md5:18665af715a6dcfeac1d6153a44f16b0',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        scheme, netloc, _, _, _, _ = urllib.parse.urlparse(url)
        info = self._download_and_extract_api_data(
            video_id, netloc, video_id, scheme=scheme)
        info['description'] = self._og_search_description(webpage)
        return info


class Ant1NewsGrArticleIE(Ant1NewsGrBaseIE):
    IE_NAME = 'ant1newsgr:article'
    IE_DESC = 'ant1news.gr articles'
    _VALID_URL = r'https?://(?:www\.)?ant1news\.gr/[^/]+/article/(?P<id>\d+)/'

    _TESTS = [{
        'url': 'https://www.ant1news.gr/afieromata/article/549468/o-tzeims-mpont-sta-meteora-oi-apeiles-kai-o-xesikomos-ton-kalogeron',
        'md5': '294f18331bb516539d72d85a82887dcc',
        'info_dict': {
            'id': '_xvg/m_cmbatw=',
            'ext': 'mp4',
            'title': 'md5:a93e8ecf2e4073bfdffcb38f59945411',
            'timestamp': 1603092840,
            'upload_date': '20201019',
            'thumbnail': 'https://ant1media.azureedge.net/imgHandler/1920/756206d2-d640-40e2-b201-3555abdfc0db.jpg',
        },
    }, {
        'url': 'https://ant1news.gr/Society/article/620286/symmoria-anilikon-dikigoros-thymaton-ithelan-na-toys-apoteleiosoyn',
        'info_dict': {
            'id': '620286',
            'title': 'md5:91fe569e952e4d146485740ae927662b',
        },
        'playlist_mincount': 2,
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info = self._search_json_ld(webpage, video_id, expected_type='NewsArticle')
        embed_urls = list(Ant1NewsGrEmbedIE._extract_urls(webpage, url, **info))
        if not embed_urls:
            raise ExtractorError('no videos found for %s' % video_id)
        if len(embed_urls) == 1:
            return self.url_result(embed_urls[0], ie=Ant1NewsGrEmbedIE.ie_key(),
                                   video_title=info['title'])
        return self.playlist_from_matches(
            embed_urls, video_id, info['title'], ie=Ant1NewsGrEmbedIE.ie_key())


class Ant1NewsGrEmbedIE(Ant1NewsGrBaseIE):
    IE_NAME = 'ant1newsgr:embed'
    IE_DESC = 'ant1news.gr embedded videos'
    _VALID_URL = r'''(?x)https?://(?:[a-zA-Z0-9\-]+\.)?
        (?:antenna|ant1news)\.gr/templates/pages/player
        \?(?:(?:cid=(?P<id>[^&#]+)|[^&=#]+=[^&#]+)&?)+'''
    _API_PATH = '/news/templates/data/jsonPlayer'

    _TEST = {
        'url': 'https://www.antenna.gr/templates/pages/player?cid=3f_li_c_az_jw_y_u=&w=670&h=377',
        'md5': '12872b12af18b5dbf76528786728de8c',
        'info_dict': {
            'id': '3f_li_c_az_jw_y_u=',
            'ext': 'mp4',
            'title': 'md5:a30c93332455f53e1e84ae0724f0adf7',
        },
    }

    @classmethod
    def _extract_urls(cls, webpage, origin_url=None, **parent_info):
        # make the scheme in _VALID_URL optional
        _URL_RE = r'(?:https?:)?//' + cls._VALID_URL.split('://', 1)[1]
        # simplify the query string part of _VALID_URL; after extracting iframe
        # src, the URL will be matched again
        _URL_RE = _URL_RE.split(r'\?', 1)[0] + r'\?(?:(?!(?P=_q1)).)+'
        EMBED_RE = r'''(?x)
            <iframe[^>]+?src=(?P<_q1>%(quot_re)s)(?P<url>%(url_re)s)(?P=_q1)
        ''' % {'quot_re': r'["\']', 'url_re': _URL_RE}
        for mobj in re.finditer(EMBED_RE, webpage):
            url = unescapeHTML(mobj.group('url'))
            if url.startswith('//'):
                scheme = urllib.parse.urlparse(origin_url).scheme if origin_url else 'https'
                url = '%s:%s' % (scheme, url)
            if not cls.suitable(url):
                continue
            yield cls._smuggle_parent_info(url, **parent_info)

    def _real_extract(self, url):
        url, parent_info = type(self)._unsmuggle_parent_info(url)
        video_id = self._match_id(url)

        # resolve any redirects, to derive the proper base URL for the API query
        canonical_url = self._request_webpage(
            HEADRequest(url), video_id,
            note='Resolve canonical player URL',
            errnote='Could not resolve canonical player URL').geturl()
        scheme, netloc, _, _, query, _ = urllib.parse.urlparse(canonical_url)
        query = urllib.parse.parse_qs(query)
        cid = query['cid'][0]

        info = self._download_and_extract_api_data(
            video_id, netloc, cid, scheme=scheme)
        if 'timestamp' not in info and 'timestamp' in parent_info:
            info['timestamp'] = parent_info['timestamp']
        return info

import re
from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    unified_strdate,
)


class GaskrankIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gaskrank\.tv/tv/(?P<categories>[^/]+)/(?P<id>[^/]+)\.htm'
    _TESTS = [{
        'url': 'http://www.gaskrank.tv/tv/motorrad-fun/strike-einparken-durch-anfaenger-crash-mit-groesserem-flurschaden.htm',
        'md5': '1ae88dbac97887d85ebd1157a95fc4f9',
        'info_dict': {
            'id': '201601/26955',
            'ext': 'mp4',
            'title': 'Strike! Einparken können nur Männer - Flurschaden hält sich in Grenzen *lol*',
            'thumbnail': r're:^https?://.*\.jpg$',
            'categories': ['motorrad-fun'],
            'display_id': 'strike-einparken-durch-anfaenger-crash-mit-groesserem-flurschaden',
            'uploader_id': 'Bikefun',
            'upload_date': '20170110',
            'uploader_url': None,
        }
    }, {
        'url': 'http://www.gaskrank.tv/tv/racing/isle-of-man-tt-2011-michael-du-15920.htm',
        'md5': 'c33ee32c711bc6c8224bfcbe62b23095',
        'info_dict': {
            'id': '201106/15920',
            'ext': 'mp4',
            'title': 'Isle of Man - Michael Dunlop vs Guy Martin - schwindelig kucken',
            'thumbnail': r're:^https?://.*\.jpg$',
            'categories': ['racing'],
            'display_id': 'isle-of-man-tt-2011-michael-du-15920',
            'uploader_id': 'IOM',
            'upload_date': '20170523',
            'uploader_url': 'www.iomtt.com',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        title = self._og_search_title(
            webpage, default=None) or self._html_search_meta(
            'title', webpage, fatal=True)

        categories = [self._match_valid_url(url).group('categories')]

        mobj = re.search(
            r'Video von:\s*(?P<uploader_id>[^|]*?)\s*\|\s*vom:\s*(?P<upload_date>[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9])',
            webpage)
        if mobj is not None:
            uploader_id = mobj.groupdict().get('uploader_id')
            upload_date = unified_strdate(mobj.groupdict().get('upload_date'))

        uploader_url = self._search_regex(
            r'Homepage:\s*<[^>]*>(?P<uploader_url>[^<]*)',
            webpage, 'uploader_url', default=None)
        tags = re.findall(
            r'/tv/tags/[^/]+/"\s*>(?P<tag>[^<]*?)<',
            webpage)

        view_count = self._search_regex(
            r'class\s*=\s*"gkRight"(?:[^>]*>\s*<[^>]*)*icon-eye-open(?:[^>]*>\s*<[^>]*)*>\s*(?P<view_count>[0-9\.]*)',
            webpage, 'view_count', default=None)
        if view_count:
            view_count = int_or_none(view_count.replace('.', ''))

        average_rating = self._search_regex(
            r'itemprop\s*=\s*"ratingValue"[^>]*>\s*(?P<average_rating>[0-9,]+)',
            webpage, 'average_rating')
        if average_rating:
            average_rating = float_or_none(average_rating.replace(',', '.'))

        video_id = self._search_regex(
            r'https?://movies\.gaskrank\.tv/([^-]*?)(-[^\.]*)?\.mp4',
            webpage, 'video id', default=display_id)

        entry = self._parse_html5_media_entries(url, webpage, video_id)[0]
        entry.update({
            'id': video_id,
            'title': title,
            'categories': categories,
            'display_id': display_id,
            'uploader_id': uploader_id,
            'upload_date': upload_date,
            'uploader_url': uploader_url,
            'tags': tags,
            'view_count': view_count,
            'average_rating': average_rating,
        })
        self._sort_formats(entry['formats'])

        return entry

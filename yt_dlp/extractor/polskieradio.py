# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_unquote,
    compat_urlparse
)
from ..utils import (
    extract_attributes,
    int_or_none,
    strip_or_none,
    unified_timestamp,
)


class PolskieRadioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polskieradio\.pl/\d+/\d+/Artykul/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.polskieradio.pl/7/5102/Artykul/1587943,Prof-Andrzej-Nowak-o-historii-nie-da-sie-myslec-beznamietnie',
        'info_dict': {
            'id': '1587943',
            'title': 'Prof. Andrzej Nowak: o historii nie da się myśleć beznamiętnie',
            'description': 'md5:12f954edbf3120c5e7075e17bf9fc5c5',
        },
        'playlist': [{
            'md5': '2984ee6ce9046d91fc233bc1a864a09a',
            'info_dict': {
                'id': '1540576',
                'ext': 'mp3',
                'title': 'md5:d4623290d4ac983bf924061c75c23a0d',
                'timestamp': 1456594200,
                'upload_date': '20160227',
                'duration': 2364,
                'thumbnail': r're:^https?://static\.prsa\.pl/images/.*\.jpg$'
            },
        }],
    }, {
        'url': 'http://www.polskieradio.pl/265/5217/Artykul/1635803,Euro-2016-nie-ma-miejsca-na-blad-Polacy-graja-ze-Szwajcaria-o-cwiercfinal',
        'info_dict': {
            'id': '1635803',
            'title': 'Euro 2016: nie ma miejsca na błąd. Polacy grają ze Szwajcarią o ćwierćfinał',
            'description': 'md5:01cb7d0cad58664095d72b51a1ebada2',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'http://polskieradio.pl/9/305/Artykul/1632955,Bardzo-popularne-slowo-remis',
        'only_matching': True,
    }, {
        'url': 'http://www.polskieradio.pl/7/5102/Artykul/1587943',
        'only_matching': True,
    }, {
        # with mp4 video
        'url': 'http://www.polskieradio.pl/9/299/Artykul/1634903,Brexit-Leszek-Miller-swiat-sie-nie-zawali-Europa-bedzie-trwac-dalej',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        content = self._search_regex(
            r'(?s)<div[^>]+class="\s*this-article\s*"[^>]*>(.+?)<div[^>]+class="tags"[^>]*>',
            webpage, 'content')

        timestamp = unified_timestamp(self._html_search_regex(
            r'(?s)<span[^>]+id="datetime2"[^>]*>(.+?)</span>',
            webpage, 'timestamp', fatal=False))

        thumbnail_url = self._og_search_thumbnail(webpage)

        entries = []

        media_urls = set()

        for data_media in re.findall(r'<[^>]+data-media=({[^>]+})', content):
            media = self._parse_json(data_media, playlist_id, fatal=False)
            if not media.get('file') or not media.get('desc'):
                continue
            media_url = self._proto_relative_url(media['file'], 'http:')
            if media_url in media_urls:
                continue
            media_urls.add(media_url)
            entries.append({
                'id': compat_str(media['id']),
                'url': media_url,
                'title': compat_urllib_parse_unquote(media['desc']),
                'duration': int_or_none(media.get('length')),
                'vcodec': 'none' if media.get('provider') == 'audio' else None,
                'timestamp': timestamp,
                'thumbnail': thumbnail_url
            })

        title = self._og_search_title(webpage).strip()
        description = strip_or_none(self._og_search_description(webpage))

        return self.playlist_result(entries, playlist_id, title, description)


class PolskieRadioCategoryIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polskieradio\.pl/\d+(?:,[^/]+)?/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.polskieradio.pl/7/5102,HISTORIA-ZYWA',
        'info_dict': {
            'id': '5102',
            'title': 'HISTORIA ŻYWA',
        },
        'playlist_mincount': 38,
    }, {
        'url': 'http://www.polskieradio.pl/7/4807',
        'info_dict': {
            'id': '4807',
            'title': 'Vademecum 1050. rocznicy Chrztu Polski'
        },
        'playlist_mincount': 5
    }, {
        'url': 'http://www.polskieradio.pl/7/129,Sygnaly-dnia?ref=source',
        'only_matching': True
    }, {
        'url': 'http://www.polskieradio.pl/37,RedakcjaKatolicka/4143,Kierunek-Krakow',
        'info_dict': {
            'id': '4143',
            'title': 'Kierunek Kraków',
        },
        'playlist_mincount': 61
    }, {
        'url': 'http://www.polskieradio.pl/10,czworka/214,muzyka',
        'info_dict': {
            'id': '214',
            'title': 'Muzyka',
        },
        'playlist_mincount': 61
    }, {
        'url': 'http://www.polskieradio.pl/7,Jedynka/5102,HISTORIA-ZYWA',
        'only_matching': True,
    }, {
        'url': 'http://www.polskieradio.pl/8,Dwojka/196,Publicystyka',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if PolskieRadioIE.suitable(url) else super(PolskieRadioCategoryIE, cls).suitable(url)

    def _entries(self, url, page, category_id):
        content = page
        for page_num in itertools.count(2):
            for a_entry, entry_id in re.findall(
                    r'(?s)<article[^>]+>.*?(<a[^>]+href=["\']/\d+/\d+/Artykul/(\d+)[^>]+>).*?</article>',
                    content):
                entry = extract_attributes(a_entry)
                href = entry.get('href')
                if not href:
                    continue
                yield self.url_result(
                    compat_urlparse.urljoin(url, href), PolskieRadioIE.ie_key(),
                    entry_id, entry.get('title'))
            mobj = re.search(
                r'<div[^>]+class=["\']next["\'][^>]*>\s*<a[^>]+href=(["\'])(?P<url>(?:(?!\1).)+)\1',
                content)
            if not mobj:
                break
            next_url = compat_urlparse.urljoin(url, mobj.group('url'))
            content = self._download_webpage(
                next_url, category_id, 'Downloading page %s' % page_num)

    def _real_extract(self, url):
        category_id = self._match_id(url)
        webpage = self._download_webpage(url, category_id)
        title = self._html_search_regex(
            r'<title>([^<]+) - [^<]+ - [^<]+</title>',
            webpage, 'title', fatal=False)
        return self.playlist_result(
            self._entries(url, webpage, category_id),
            category_id, title)

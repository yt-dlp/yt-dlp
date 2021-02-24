# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    xpath_text,
)


class WebcasterIE(InfoExtractor):
    _VALID_URL = r'https?://bl\.webcaster\.pro/(?:quote|media)/start/free_(?P<id>[^/]+)'
    _TESTS = [{
        # http://video.khl.ru/quotes/393859
        'url': 'http://bl.webcaster.pro/quote/start/free_c8cefd240aa593681c8d068cff59f407_hd/q393859/eb173f99dd5f558674dae55f4ba6806d/1480289104?sr%3D105%26fa%3D1%26type_id%3D18',
        'md5': '0c162f67443f30916ff1c89425dcd4cd',
        'info_dict': {
            'id': 'c8cefd240aa593681c8d068cff59f407_hd',
            'ext': 'mp4',
            'title': 'Сибирь - Нефтехимик. Лучшие моменты первого периода',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'http://bl.webcaster.pro/media/start/free_6246c7a4453ac4c42b4398f840d13100_hd/2_2991109016/e8d0d82587ef435480118f9f9c41db41/4635726126',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_xml(url, video_id)

        title = xpath_text(video, './/event_name', 'event name', fatal=True)

        def make_id(parts, separator):
            return separator.join(filter(None, parts))

        formats = []
        for format_id in (None, 'noise'):
            track_tag = make_id(('track', format_id), '_')
            for track in video.findall('.//iphone/%s' % track_tag):
                track_url = track.text
                if not track_url:
                    continue
                if determine_ext(track_url) == 'm3u8':
                    m3u8_formats = self._extract_m3u8_formats(
                        track_url, video_id, 'mp4',
                        entry_protocol='m3u8_native',
                        m3u8_id=make_id(('hls', format_id), '-'), fatal=False)
                    for f in m3u8_formats:
                        f.update({
                            'source_preference': 0 if format_id == 'noise' else 1,
                            'format_note': track.get('title'),
                        })
                    formats.extend(m3u8_formats)
        self._sort_formats(formats)

        thumbnail = xpath_text(video, './/image', 'thumbnail')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }


class WebcasterFeedIE(InfoExtractor):
    _VALID_URL = r'https?://bl\.webcaster\.pro/feed/start/free_(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://bl.webcaster.pro/feed/start/free_c8cefd240aa593681c8d068cff59f407_hd/q393859/eb173f99dd5f558674dae55f4ba6806d/1480289104',
        'only_matching': True,
    }

    @staticmethod
    def _extract_url(ie, webpage):
        mobj = re.search(
            r'<(?:object|a[^>]+class=["\']webcaster-player["\'])[^>]+data(?:-config)?=(["\']).*?config=(?P<url>https?://bl\.webcaster\.pro/feed/start/free_.*?)(?:[?&]|\1)',
            webpage)
        if mobj:
            return mobj.group('url')
        for secure in (True, False):
            video_url = ie._og_search_video_url(
                webpage, secure=secure, default=None)
            if video_url:
                mobj = re.search(
                    r'config=(?P<url>https?://bl\.webcaster\.pro/feed/start/free_[^?&=]+)',
                    video_url)
                if mobj:
                    return mobj.group('url')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        feed = self._download_xml(url, video_id)

        video_url = xpath_text(
            feed, ('video_hd', 'video'), 'video url', fatal=True)

        return self.url_result(video_url, WebcasterIE.ie_key())

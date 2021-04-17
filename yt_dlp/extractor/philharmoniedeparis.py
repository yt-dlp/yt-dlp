# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    try_get,
    urljoin,
)


class PhilharmonieDeParisIE(InfoExtractor):
    IE_DESC = 'Philharmonie de Paris'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            live\.philharmoniedeparis\.fr/(?:[Cc]oncert/|embed(?:app)?/|misc/Playlist\.ashx\?id=)|
                            pad\.philharmoniedeparis\.fr/doc/CIMU/
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'http://pad.philharmoniedeparis.fr/doc/CIMU/1086697/jazz-a-la-villette-knower',
        'md5': 'a0a4b195f544645073631cbec166a2c2',
        'info_dict': {
            'id': '1086697',
            'ext': 'mp4',
            'title': 'Jazz à la Villette : Knower',
        },
    }, {
        'url': 'http://live.philharmoniedeparis.fr/concert/1032066.html',
        'info_dict': {
            'id': '1032066',
            'title': 'md5:0a031b81807b3593cffa3c9a87a167a0',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'http://live.philharmoniedeparis.fr/Concert/1030324.html',
        'only_matching': True,
    }, {
        'url': 'http://live.philharmoniedeparis.fr/misc/Playlist.ashx?id=1030324&track=&lang=fr',
        'only_matching': True,
    }, {
        'url': 'https://live.philharmoniedeparis.fr/embedapp/1098406/berlioz-fantastique-lelio-les-siecles-national-youth-choir-of.html?lang=fr-FR',
        'only_matching': True,
    }, {
        'url': 'https://live.philharmoniedeparis.fr/embed/1098406/berlioz-fantastique-lelio-les-siecles-national-youth-choir-of.html?lang=fr-FR',
        'only_matching': True,
    }]
    _LIVE_URL = 'https://live.philharmoniedeparis.fr'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        config = self._download_json(
            '%s/otoPlayer/config.ashx' % self._LIVE_URL, video_id, query={
                'id': video_id,
                'lang': 'fr-FR',
            })

        def extract_entry(source):
            if not isinstance(source, dict):
                return
            title = source.get('title')
            if not title:
                return
            files = source.get('files')
            if not isinstance(files, dict):
                return
            format_urls = set()
            formats = []
            for format_id in ('mobile', 'desktop'):
                format_url = try_get(
                    files, lambda x: x[format_id]['file'], compat_str)
                if not format_url or format_url in format_urls:
                    continue
                format_urls.add(format_url)
                m3u8_url = urljoin(self._LIVE_URL, format_url)
                formats.extend(self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            if not formats and not self._downloader.params.get('ignore_no_formats'):
                return
            self._sort_formats(formats)
            return {
                'title': title,
                'formats': formats,
            }

        thumbnail = urljoin(self._LIVE_URL, config.get('image'))

        info = extract_entry(config)
        if info:
            info.update({
                'id': video_id,
                'thumbnail': thumbnail,
            })
            return info

        entries = []
        for num, chapter in enumerate(config['chapters'], start=1):
            entry = extract_entry(chapter)
            entry['id'] = '%s-%d' % (video_id, num)
            entries.append(entry)

        return self.playlist_result(entries, video_id, config.get('title'))

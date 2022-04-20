import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    int_or_none,
    js_to_json,
    parse_duration,
)


class NTVDeIE(InfoExtractor):
    IE_NAME = 'n-tv.de'
    _VALID_URL = r'https?://(?:www\.)?n-tv\.de/mediathek/videos/[^/?#]+/[^/?#]+-article(?P<id>.+)\.html'

    _TESTS = [{
        'url': 'http://www.n-tv.de/mediathek/videos/panorama/Schnee-und-Glaette-fuehren-zu-zahlreichen-Unfaellen-und-Staus-article14438086.html',
        'md5': '6ef2514d4b1e8e03ca24b49e2f167153',
        'info_dict': {
            'id': '14438086',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Schnee und Glätte führen zu zahlreichen Unfällen und Staus',
            'alt_title': 'Winterchaos auf deutschen Straßen',
            'description': 'Schnee und Glätte sorgen deutschlandweit für einen chaotischen Start in die Woche: Auf den Straßen kommt es zu kilometerlangen Staus und Dutzenden Glätteunfällen. In Düsseldorf und München wirbelt der Schnee zudem den Flugplan durcheinander. Dutzende Flüge landen zu spät, einige fallen ganz aus.',
            'duration': 4020,
            'timestamp': 1422892797,
            'upload_date': '20150202',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        info = self._parse_json(self._search_regex(
            r'(?s)ntv\.pageInfo\.article\s*=\s*(\{.*?\});', webpage, 'info'),
            video_id, transform_source=js_to_json)
        timestamp = int_or_none(info.get('publishedDateAsUnixTimeStamp'))
        vdata = self._parse_json(self._search_regex(
            r'(?s)\$\(\s*"\#player"\s*\)\s*\.data\(\s*"player",\s*(\{.*?\})\);',
            webpage, 'player data'), video_id,
            transform_source=lambda s: js_to_json(re.sub(r'advertising:\s*{[^}]+},', '', s)))
        duration = parse_duration(vdata.get('duration'))

        formats = []
        if vdata.get('video'):
            formats.append({
                'format_id': 'flash',
                'url': 'rtmp://fms.n-tv.de/%s' % vdata['video'],
            })
        if vdata.get('videoMp4'):
            formats.append({
                'format_id': 'mobile',
                'url': compat_urlparse.urljoin('http://video.n-tv.de', vdata['videoMp4']),
                'tbr': 400,  # estimation
            })
        if vdata.get('videoM3u8'):
            m3u8_url = compat_urlparse.urljoin('http://video.n-tv.de', vdata['videoM3u8'])
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', entry_protocol='m3u8_native',
                quality=1, m3u8_id='hls', fatal=False))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': info['headline'],
            'description': info.get('intro'),
            'alt_title': info.get('kicker'),
            'timestamp': timestamp,
            'thumbnail': vdata.get('html5VideoPoster'),
            'duration': duration,
            'formats': formats,
        }

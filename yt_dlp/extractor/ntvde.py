import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    traverse_obj,
)


class NTVDeIE(InfoExtractor):
    IE_NAME = 'n-tv.de'
    _VALID_URL = r'https?://(?:www\.)?n-tv\.de/mediathek/videos/[^/?#]+/[^/?#]+-article(?P<id>.+)\.html'

    _TESTS = [{
        'url': 'http://www.n-tv.de/mediathek/videos/panorama/Schnee-und-Glaette-fuehren-zu-zahlreichen-Unfaellen-und-Staus-article14438086.html',
        'md5': '6bcf2a6638cb83f45d5561659a1cb498',
        'info_dict': {
            'id': '14438086',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Schnee und Glätte führen zu zahlreichen Unfällen und Staus',
            'alt_title': 'Winterchaos auf deutschen Straßen',
            'description': 'Schnee und Glätte sorgen deutschlandweit für einen chaotischen Start in die Woche: Auf den Straßen kommt es zu kilometerlangen Staus und Dutzenden Glätteunfällen. In Düsseldorf und München wirbelt der Schnee zudem den Flugplan durcheinander. Dutzende Flüge landen zu spät, einige fallen ganz aus.',
            'duration': 67,
            'timestamp': 1422892797,
            'upload_date': '20150202',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        info = self._parse_json(self._search_regex(
            r'(?s)article:\s*(\{.+?\})', webpage, 'info'),
            video_id, transform_source=js_to_json)
        timestamp = int_or_none(info.get('publishedDateAsUnixTimeStamp'))

        player_data = self._parse_json(self._search_regex(
            r'(?s)\$\(\s*"\#playerwrapper"\s*\)\s*\.data\(\s*"player",\s*(\{.*?\})\);',
            webpage, 'player data'), video_id,
            transform_source=lambda s: js_to_json(re.sub(r'ivw:\s*.+', '', s)))
        vdata = traverse_obj(player_data, ('setup', 'source'))
        duration = int_or_none(vdata.get('length'))

        formats = []
        if vdata.get('progressive'):
            formats.append({
                'format_id': 'mp4-0',
                'url': vdata['progressive'],
            })
        if vdata.get('hls'):
            formats.extend(self._extract_m3u8_formats(
                vdata['hls'], video_id, ext='mp4', entry_protocol='m3u8_native',
                quality=1, m3u8_id='hls', fatal=False))
        if vdata.get('dash'):
            formats.extend(self._extract_mpd_formats(vdata['dash'], video_id, fatal=False))
        return {
            'id': video_id,
            'title': info['headline'],
            'description': info.get('intro'),
            'alt_title': info.get('kicker'),
            'timestamp': timestamp,
            'thumbnail': vdata.get('poster'),
            'duration': duration,
            'formats': formats,
        }

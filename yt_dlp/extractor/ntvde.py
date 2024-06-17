import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class NTVDeIE(InfoExtractor):
    IE_NAME = 'n-tv.de'
    _VALID_URL = r'https?://(?:www\.)?n-tv\.de/mediathek/(?:videos|magazine)/[^/?#]+/[^/?#]+-article(?P<id>[^/?#]+)\.html'

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
    }, {
        'url': 'https://www.n-tv.de/mediathek/magazine/auslandsreport/Juedische-Siedler-wollten-Rache-die-wollten-nur-toeten-article24523089.html',
        'md5': 'c5c6014c014ccc3359470e1d34472bfd',
        'info_dict': {
            'id': '24523089',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Jüdische Siedler "wollten Rache, die wollten nur töten"',
            'alt_title': 'Israelische Gewalt fern von Gaza',
            'description': 'Vier Tage nach dem Massaker der Hamas greifen jüdische Siedler das Haus einer palästinensischen Familie im Westjordanland an. Die Überlebenden berichten, sie waren unbewaffnet, die Angreifer seien nur auf "Rache und Töten" aus gewesen. Als die Toten beerdigt werden sollen, eröffnen die Siedler erneut das Feuer.',
            'duration': 326,
            'timestamp': 1699688294,
            'upload_date': '20231111',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        info = self._search_json(
            r'article:', webpage, 'info', video_id, transform_source=js_to_json)

        vdata = self._search_json(
            r'\$\(\s*"#playerwrapper"\s*\)\s*\.data\(\s*"player",',
            webpage, 'player data', video_id,
            transform_source=lambda s: js_to_json(re.sub(r'ivw:[^},]+', '', s)))['setup']['source']

        formats = []
        if vdata.get('progressive'):
            formats.append({
                'format_id': 'http',
                'url': vdata['progressive'],
            })
        if vdata.get('hls'):
            formats.extend(self._extract_m3u8_formats(
                vdata['hls'], video_id, 'mp4', m3u8_id='hls', fatal=False))
        if vdata.get('dash'):
            formats.extend(self._extract_mpd_formats(vdata['dash'], video_id, fatal=False, mpd_id='dash'))

        return {
            'id': video_id,
            **traverse_obj(info, {
                'title': 'headline',
                'description': 'intro',
                'alt_title': 'kicker',
                'timestamp': ('publishedDateAsUnixTimeStamp', {int_or_none}),
            }),
            **traverse_obj(vdata, {
                'thumbnail': ('poster', {url_or_none}),
                'duration': ('length', {int_or_none}),
            }),
            'formats': formats,
        }

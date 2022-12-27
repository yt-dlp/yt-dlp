import json
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    remove_start,
    extract_attributes,
)

class RozhlasIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?prehravac\.rozhlas\.cz/audio/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://prehravac.rozhlas.cz/audio/3421320',
        'md5': '504c902dbc9e9a1fd50326eccf02a7e2',
        'info_dict': {
            'id': '3421320',
            'ext': 'mp3',
            'title': 'Echo Pavla Klusáka (30.06.2015 21:00)',
            'description': 'Osmdesátiny Terryho Rileyho jsou skvělou příležitostí proletět se elektronickými i akustickými díly zakladatatele minimalismu, který je aktivní už přes padesát let'
        }
    }, {
        'url': 'http://prehravac.rozhlas.cz/audio/3421320/embed',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://prehravac.rozhlas.cz/audio/%s' % audio_id, audio_id)

        title = self._html_search_regex(
            r'<h3>(.+?)</h3>\s*<p[^>]*>.*?</p>\s*<div[^>]+id=["\']player-track',
            webpage, 'title', default=None) or remove_start(
            self._og_search_title(webpage), 'Radio Wave - ')
        description = self._html_search_regex(
            r'<p[^>]+title=(["\'])(?P<url>(?:(?!\1).)+)\1[^>]*>.*?</p>\s*<div[^>]+id=["\']player-track',
            webpage, 'description', fatal=False, group='url')
        duration = int_or_none(self._search_regex(
            r'data-duration=["\'](\d+)', webpage, 'duration', default=None))

        return {
            'id': audio_id,
            'url': 'http://media.rozhlas.cz/_audio/%s.mp3' % audio_id,
            'title': title,
            'description': description,
            'duration': duration,
            'vcodec': 'none',
        }

class RozhlasVltavaIE(InfoExtractor):
    _VALID_URL = r'https?://(vltava|wave)\.rozhlas\.cz/[a-z|-]*-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://vltava.rozhlas.cz/henry-miller-obratnik-raka-8876625/1',
        'md5': '504c902dbc9e9a1fd50326eccf02a7e2',
        'info_dict': {
            'id': '8876625',
            'ext': 'mp3',
            'title': 'Henry Miller: Obratník Raka',
            'description': 'Nelítostný útok na konvence v klíčovém románu 20. století. Mladý spisovatel Henry Miller chce v Paříži třicátých let „vypsat celou pravdu o životě“. Připravila Petra Hynčíková. V režii Lukáše Kopeckého účinkuje Petr Kubes. Natočeno v brněnském studiu Českého rozhlasu v roce 2022. Premiéru poslouchejte on-line po dobu čtyř týdnů po odvysílání. Pořad není vhodný pro děti a mladistvé.'
        }
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        
        playerDiv = ''
        for k, line in enumerate(webpage.split("\n")) :
            if line.find('mujRozhlasPlayer') != -1 :
                playerDiv = line.strip()
        
        jsonString = extract_attributes(playerDiv)['data-player']
        jsonData = json.loads(jsonString)

        entries = []
        for entry in jsonData["data"]['playlist']:
            format = {
                'url': entry["audioLinks"][0]['url'],
                'ext': entry["audioLinks"][0]['variant'],
                'format_id': entry["audioLinks"][0]['variant'],
                'abr': entry["audioLinks"][0]['bitrate'],
                'acodec': entry["audioLinks"][0]['variant'],
                'vcodec': 'none',
            }
            temp = {
                'id': entry["meta"]['ga']['contentId'],
                'title': entry["title"],
                'description': entry["meta"]['ga']['contentEvent'],
                'duration': entry["duration"],
                'formats': [format],
            }
            entries.append(temp)

        return {
            '_type': 'playlist',
            'id': jsonData["data"]['embedId'],
            'title': jsonData["data"]['series']['title'],
            'entries': entries,
        }

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
    _VALID_URL = r'https?://((vltava|wave|radiozurnal|dvojka|plus|sport|d-dur|jazz|junior|pohoda)\.rozhlas|english\.radio)\.cz/[a-z|-]*-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://wave.rozhlas.cz/papej-masicko-porcujeme-a-bilancujeme-filmy-a-serialy-ktere-letos-zabily-8891337',
        'md5': 'ba2fdbc1242fc16771c7695d271ec355',
        'info_dict': {
            'id': '8891337',
            'ext': 'mp3',
            'title': 'Máte po celé sezóně poslouchání Čelistí právo na wellness, nebo můžete být rádi, že jste vůbec naživu? Poslechněte si filmově kritickou bilanci všeho, co v uplynulých měsících stálo za vidění',
            'description': '8888928: Vánoce s Radiem Wave | 7702992: Český rozhlas má nadílku pro každého',
            'duration': 1574
        }
    }]

    def find_element(self, webpage):
        # Use utils.get_element_text_and_html_by_tag() instead when it accepts less strict html.

        playerDiv = ''
        for k, line in enumerate(webpage.split("\n")):
            if line.find('mujRozhlasPlayer') != -1:
                playerDiv = line.strip()
                break

        if playerDiv.count('<div') > 1:
            for k, element in enumerate(playerDiv.split('<div')):
                if element.count('mujRozhlasPlayer') == 1:
                    playerDiv = '<div' + element
                    break

        return playerDiv

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)

        playerDiv = self.find_element(webpage)

        jsonString = extract_attributes(playerDiv).get('data-player')
        jsonData = json.loads(jsonString)

        entries = []
        for entry in jsonData.get("data").get('playlist'):
            entry0 = entry.get('audioLinks')[0]
            format = {
                'url': entry0.get('url'),
                'ext': entry0.get('variant'),
                'format_id': entry0.get('variant'),
                'abr': entry0.get('bitrate'),
                'acodec': entry0.get('variant'),
                'vcodec': 'none',
            }
            temp = {
                'id': self._match_id(url),  # Prefering to user entry.get('meta').get('ga').get('contentId') for id. Using this because of tests.
                'title': entry.get('title'),
                'description': entry.get('meta').get('ga').get('contentEvent'),
                'duration': entry.get('duration'),
                'formats': [format],
            }
            entries.append(temp)

        return {
            '_type': 'playlist',
            'id': jsonData.get('data').get('embedId'),
            'title': jsonData.get('data').get('series').get('title'),
            'entries': entries,
        }

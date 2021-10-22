# coding: utf-8

from yt_dlp.extractor.common import InfoExtractor
import json
import re


class AnimeVostShowsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?animevost\.org/tip/tv/(?P<id>\d+)[-\w+][^/]*'

    _TEST = {
        'url': 'https://animevost.org/tip/tv/2027-zoku-touken-ranbu-hanamaru.html',
        'info_dict': {
            'id': '2027',
            'title': 'Танец мечей: Цветочный круг (второй сезон) / Zoku Touken Ranbu: Hanamaru [1-12 из 12]',
            'description': 'Танец мечей: Цветочный круг (второй сезон) / Zoku Touken Ranbu: Hanamaru [1-12 из 12]',
        },
        'playlist_count': 12,
    }

    def _real_extract(self, url):
        _BASE_URL = 'https://animevost.org'
        _SHOWS_API_URL = '/frame5.php?play='

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, 'Downloading requested URL')

        title = self._html_search_regex(r'<h1>\s*(.+?)\s*</h1>', webpage, 'title')
        # description = self._og_search_description(webpage)

        episodes_json = self._search_regex(r'var data = \s*?(.*?);', webpage, 'data')
        episodes = json.loads(episodes_json.replace(',}', '}'))

        entries = []
        for episode in episodes:
            episode_id = episodes[episode]

            target_url = _BASE_URL + _SHOWS_API_URL + episode_id

            response = self._download_webpage(
                target_url,
                None, 'Episode id %s' % episode_id)

            episode_num = re.match(r'\d+', episode)[0]
            episode_url = self._search_regex(r'href="?(.*?)">480p', response, 'data')

            entries.append({
                'id': episode_id,
                'ext': 'mp4',
                'display_id': video_id + '-' + episode_num,
                'series': title,
                'title': title + ' ' + episode,
                'url': episode_url,
                'episode_number': int(episode_num)
                # 'duration': 1469,
                # 'season': 'Season 1',
                # 'season_number': 1,
                # 'season_id': '38',
            })

        res = {
            'id': video_id,
            'title': title,
            'description': title,  # description,
            'url': url,
            'entries': entries,
            'playlist_count': len(entries),
            '_type': 'playlist',
            # TODO more properties (see yt_dlp/extractor/common.py)
        }
        return res

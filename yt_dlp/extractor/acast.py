from .common import InfoExtractor
from ..utils import (
    clean_html,
    clean_podcast_url,
    int_or_none,
    parse_iso8601,
)


class ACastBaseIE(InfoExtractor):
    def _extract_episode(self, episode, show_info):
        title = episode['title']
        info = {
            'id': episode['id'],
            'display_id': episode.get('episodeUrl'),
            'url': clean_podcast_url(episode['url']),
            'title': title,
            'description': clean_html(episode.get('description') or episode.get('summary')),
            'thumbnail': episode.get('image'),
            'timestamp': parse_iso8601(episode.get('publishDate')),
            'duration': int_or_none(episode.get('duration')),
            'filesize': int_or_none(episode.get('contentLength')),
            'season_number': int_or_none(episode.get('season')),
            'episode': title,
            'episode_number': int_or_none(episode.get('episode')),
        }
        info.update(show_info)
        return info

    def _extract_show_info(self, show):
        return {
            'creator': show.get('author'),
            'series': show.get('title'),
        }

    def _call_api(self, path, video_id, query=None):
        return self._download_json(
            'https://feeder.acast.com/api/v1/shows/' + path, video_id, query=query)


class ACastIE(ACastBaseIE):
    IE_NAME = 'acast'
    _VALID_URL = r'''(?x:
                    https?://
                        (?:
                            (?:(?:embed|www)\.)?acast\.com/|
                            play\.acast\.com/s/
                        )
                        (?P<channel>[^/]+)/(?P<id>[^/#?"]+)
                    )'''
    _EMBED_REGEX = [rf'(?x)<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://www.acast.com/sparpodcast/2.raggarmordet-rosterurdetforflutna',
        'info_dict': {
            'id': '2a92b283-1a75-4ad8-8396-499c641de0d9',
            'ext': 'mp3',
            'title': '2. Raggarmordet - Röster ur det förflutna',
            'description': 'md5:013959207e05011ad14a222cf22278cc',
            'timestamp': 1477346700,
            'upload_date': '20161024',
            'duration': 2766,
            'creator': 'Third Ear Studio',
            'series': 'Spår',
            'episode': '2. Raggarmordet - Röster ur det förflutna',
            'thumbnail': 'https://assets.pippa.io/shows/616ebe1886d7b1398620b943/616ebe33c7e6e70013cae7da.jpg',
            'episode_number': 2,
            'display_id': '2.raggarmordet-rosterurdetforflutna',
            'season_number': 4,
            'season': 'Season 4',
        },
    }, {
        'url': 'http://embed.acast.com/adambuxton/ep.12-adam-joeschristmaspodcast2015',
        'only_matching': True,
    }, {
        'url': 'https://play.acast.com/s/rattegangspodden/s04e09styckmordetihelenelund-del2-2',
        'only_matching': True,
    }, {
        'url': 'https://play.acast.com/s/sparpodcast/2a92b283-1a75-4ad8-8396-499c641de0d9',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://ausi.anu.edu.au/news/democracy-sausage-episode-can-labor-be-long-form-government',
        'info_dict': {
            'id': '646c68fb21fbf20011e9c651',
            'ext': 'mp3',
            'creator': 'The Australian National University',
            'display_id': 'can-labor-be-a-long-form-government',
            'duration': 2618,
            'thumbnail': 'https://assets.pippa.io/shows/6113e8578b4903809f16f7e5/1684821529295-515b9520db9ce53275b995eb302f941c.jpeg',
            'title': 'Can Labor be a long-form government?',
            'episode': 'Can Labor be a long-form government?',
            'upload_date': '20230523',
            'series': 'Democracy Sausage with Mark Kenny',
            'timestamp': 1684826362,
            'description': 'md5:feabe1fc5004c78ee59c84a46bf4ba16',
        },
    }]

    def _real_extract(self, url):
        channel, display_id = self._match_valid_url(url).groups()
        episode = self._call_api(
            f'{channel}/episodes/{display_id}',
            display_id, {'showInfo': 'true'})
        return self._extract_episode(
            episode, self._extract_show_info(episode.get('show') or {}))


class ACastChannelIE(ACastBaseIE):
    IE_NAME = 'acast:channel'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?acast\.com/|
                            play\.acast\.com/s/
                        )
                        (?P<id>[^/#?]+)
                    '''
    _TESTS = [{
        'url': 'https://www.acast.com/todayinfocus',
        'info_dict': {
            'id': '4efc5294-5385-4847-98bd-519799ce5786',
            'title': 'Today in Focus',
            'description': 'md5:c09ce28c91002ce4ffce71d6504abaae',
        },
        'playlist_mincount': 200,
    }, {
        'url': 'http://play.acast.com/s/ft-banking-weekly',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ACastIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        show_slug = self._match_id(url)
        show = self._call_api(show_slug, show_slug)
        show_info = self._extract_show_info(show)
        entries = []
        for episode in (show.get('episodes') or []):
            entries.append(self._extract_episode(episode, show_info))
        return self.playlist_result(
            entries, show.get('id'), show.get('title'), show.get('description'))

from .common import InfoExtractor
from ..utils import (
    clean_html,
    clean_podcast_url,
    int_or_none,
    str_or_none,
)


class IHeartRadioBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, fatal=True, query=None):
        return self._download_json(
            'https://api.iheart.com/api/v3/podcast/' + path,
            video_id, fatal=fatal, query=query)

    def _extract_episode(self, episode):
        return {
            'thumbnail': episode.get('imageUrl'),
            'description': clean_html(episode.get('description')),
            'timestamp': int_or_none(episode.get('startDate'), 1000),
            'duration': int_or_none(episode.get('duration')),
        }


class IHeartRadioIE(IHeartRadioBaseIE):
    IENAME = 'iheartradio'
    _VALID_URL = r'(?:https?://(?:www\.)?iheart\.com/podcast/[^/]+/episode/(?P<display_id>[^/?&#]+)-|iheartradio:)(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.iheart.com/podcast/105-behind-the-bastards-29236323/episode/part-one-alexander-lukashenko-the-dictator-70346499/?embed=true',
        'md5': 'c8609c92c8688dcb69d8541042b8abca',
        'info_dict': {
            'id': '70346499',
            'ext': 'mp3',
            'title': 'Part One: Alexander Lukashenko: The Dictator of Belarus',
            'description': 'md5:96cc7297b3a5a9ebae28643801c96fae',
            'timestamp': 1597741200,
            'upload_date': '20200818',
        }
    }

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        episode = self._call_api(
            'episodes/' + episode_id, episode_id)['episode']
        info = self._extract_episode(episode)
        info.update({
            'id': episode_id,
            'title': episode['title'],
            'url': clean_podcast_url(episode['mediaUrl']),
        })
        return info


class IHeartRadioPodcastIE(IHeartRadioBaseIE):
    IE_NAME = 'iheartradio:podcast'
    _VALID_URL = r'https?://(?:www\.)?iheart(?:podcastnetwork)?\.com/podcast/[^/?&#]+-(?P<id>\d+)/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'https://www.iheart.com/podcast/1119-it-could-happen-here-30717896/',
        'info_dict': {
            'id': '30717896',
            'title': 'It Could Happen Here',
            'description': 'md5:5842117412a967eb0b01f8088eb663e2',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://www.iheartpodcastnetwork.com/podcast/105-stuff-you-should-know-26940277',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        podcast_id = self._match_id(url)
        path = 'podcasts/' + podcast_id
        episodes = self._call_api(
            path + '/episodes', podcast_id, query={'limit': 1000000000})['data']

        entries = []
        for episode in episodes:
            episode_id = str_or_none(episode.get('id'))
            if not episode_id:
                continue
            info = self._extract_episode(episode)
            info.update({
                '_type': 'url',
                'id': episode_id,
                'title': episode.get('title'),
                'url': 'iheartradio:' + episode_id,
                'ie_key': IHeartRadioIE.ie_key(),
            })
            entries.append(info)

        podcast = self._call_api(path, podcast_id, False) or {}

        return self.playlist_result(
            entries, podcast_id, podcast.get('title'), podcast.get('description'))

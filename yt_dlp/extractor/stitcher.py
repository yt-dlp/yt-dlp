from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    clean_podcast_url,
    int_or_none,
    str_or_none,
    try_get,
    url_or_none,
)


class StitcherBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?stitcher\.com/(?:podcast|show)/'

    def _call_api(self, path, video_id, query):
        resp = self._download_json(
            'https://api.prod.stitcher.com/' + path,
            video_id, query=query)
        error_massage = try_get(resp, lambda x: x['errors'][0]['message'])
        if error_massage:
            raise ExtractorError(error_massage, expected=True)
        return resp['data']

    def _extract_description(self, data):
        return clean_html(data.get('html_description') or data.get('description'))

    def _extract_audio_url(self, episode):
        return url_or_none(episode.get('audio_url') or episode.get('guid'))

    def _extract_show_info(self, show):
        return {
            'thumbnail': show.get('image_base_url'),
            'series': show.get('title'),
        }

    def _extract_episode(self, episode, audio_url, show_info):
        info = {
            'id': str(episode['id']),
            'display_id': episode.get('slug'),
            'title': episode['title'].strip(),
            'description': self._extract_description(episode),
            'duration': int_or_none(episode.get('duration')),
            'url': clean_podcast_url(audio_url),
            'vcodec': 'none',
            'timestamp': int_or_none(episode.get('date_published')),
            'season_number': int_or_none(episode.get('season')),
            'season_id': str_or_none(episode.get('season_id')),
        }
        info.update(show_info)
        return info


class StitcherIE(StitcherBaseIE):
    _VALID_URL = StitcherBaseIE._VALID_URL_BASE + r'(?:[^/]+/)+e(?:pisode)?/(?:[^/#?&]+-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.stitcher.com/podcast/the-talking-machines/e/40789481?autoplay=true',
        'md5': 'e9635098e0da10b21a0e2b85585530f6',
        'info_dict': {
            'id': '40789481',
            'ext': 'mp3',
            'title': 'Machine Learning Mastery and Cancer Clusters',
            'description': 'md5:547adb4081864be114ae3831b4c2b42f',
            'duration': 1604,
            'thumbnail': r're:^https?://.*\.jpg',
            'upload_date': '20151008',
            'timestamp': 1444285800,
            'series': 'Talking Machines',
        },
    }, {
        'url': 'http://www.stitcher.com/podcast/panoply/vulture-tv/e/the-rare-hourlong-comedy-plus-40846275?autoplay=true',
        'info_dict': {
            'id': '40846275',
            'display_id': 'the-rare-hourlong-comedy-plus',
            'ext': 'mp3',
            'title': "The CW's 'Crazy Ex-Girlfriend'",
            'description': 'md5:04f1e2f98eb3f5cbb094cea0f9e19b17',
            'duration': 2235,
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Page Not Found',
    }, {
        # escaped title
        'url': 'http://www.stitcher.com/podcast/marketplace-on-stitcher/e/40910226?autoplay=true',
        'only_matching': True,
    }, {
        'url': 'http://www.stitcher.com/podcast/panoply/getting-in/e/episode-2a-how-many-extracurriculars-should-i-have-40876278?autoplay=true',
        'only_matching': True,
    }, {
        'url': 'https://www.stitcher.com/show/threedom/episode/circles-on-a-stick-200212584',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        data = self._call_api(
            'shows/episodes', audio_id, {'episode_ids': audio_id})
        episode = data['episodes'][0]
        audio_url = self._extract_audio_url(episode)
        if not audio_url:
            self.raise_login_required()
        show = try_get(data, lambda x: x['shows'][0], dict) or {}
        return self._extract_episode(
            episode, audio_url, self._extract_show_info(show))


class StitcherShowIE(StitcherBaseIE):
    _VALID_URL = StitcherBaseIE._VALID_URL_BASE + r'(?P<id>[^/#?&]+)/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'http://www.stitcher.com/podcast/the-talking-machines',
        'info_dict': {
            'id': 'the-talking-machines',
            'title': 'Talking Machines',
            'description': 'md5:831f0995e40f26c10231af39cf1ebf0b',
        },
        'playlist_mincount': 106,
    }, {
        'url': 'https://www.stitcher.com/show/the-talking-machines',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        show_slug = self._match_id(url)
        data = self._call_api(
            f'search/show/{show_slug}/allEpisodes', show_slug, {'count': 10000})
        show = try_get(data, lambda x: x['shows'][0], dict) or {}
        show_info = self._extract_show_info(show)

        entries = []
        for episode in (data.get('episodes') or []):
            audio_url = self._extract_audio_url(episode)
            if not audio_url:
                continue
            entries.append(self._extract_episode(episode, audio_url, show_info))

        return self.playlist_result(
            entries, show_slug, show.get('title'),
            self._extract_description(show))

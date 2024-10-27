from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import traverse_obj


class DiscogsReleasePlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?discogs\.com/(?P<type>release|master)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.discogs.com/release/1-The-Persuader-Stockholm',
        'info_dict': {
            'id': 'release1',
            'title': 'Stockholm',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://www.discogs.com/master/113-Vince-Watson-Moments-In-Time',
        'info_dict': {
            'id': 'master113',
            'title': 'Moments In Time',
        },
        'playlist_mincount': 53,
    }]

    def _real_extract(self, url):
        playlist_id, playlist_type = self._match_valid_url(url).group('id', 'type')

        display_id = f'{playlist_type}{playlist_id}'
        response = self._download_json(
            f'https://api.discogs.com/{playlist_type}s/{playlist_id}', display_id)

        entries = [
            self.url_result(video['uri'], YoutubeIE, video_title=video.get('title'))
            for video in traverse_obj(response, ('videos', lambda _, v: YoutubeIE.suitable(v['uri'])))]

        return self.playlist_result(entries, display_id, response.get('title'))

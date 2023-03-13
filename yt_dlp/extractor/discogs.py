from .common import InfoExtractor


class DiscogsReleasePlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?discogs\.com/(?P<type>(release|master))/(?P<id>\d+)'
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
        mobj = self._match_valid_url(url)
        playlist_id, playlist_type = mobj.group('id', 'type')

        api = f'https://api.discogs.com/{playlist_type}s/{playlist_id}'
        display_id = f'{playlist_type}{playlist_id}'
        response = self._download_json(api, display_id)

        playlist_title = response.get('title')
        entries = [
            self.url_result(video.get('uri'), video_title=video.get('title'))
            for video in response.get('videos')
        ]

        return self.playlist_result(entries, display_id, playlist_title)
